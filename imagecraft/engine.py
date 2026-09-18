"""BackendEngine — the ``js_api`` bridge between the web UI and OpenCV.

Design notes
------------
* Every method is **synchronous** and JSON-safe (no numpy in return values).
  pywebview runs each ``js_api`` call on its own HTTP-server thread, so heavy
  operations never block the JS main thread; progress is pushed to the UI via
  ``bridge.evaluate_js`` dispatching ``CustomEvent('backend:...')`` events.
* The ``bridge`` is a small protocol (``UIBridge``) so the engine is fully
  testable headlessly with a fake bridge — the GUI window is only referenced
  through the bridge.
* Editing is **cumulative with history**: ``apply`` runs on the current active
  state and pushes an undo snapshot, so transformations and augmentations chain
  and are individually undoable.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
import json
import logging
import os
import platform
import threading
import time
from pathlib import Path
from typing import Any, Protocol

import cv2

from imagecraft.io import downscale, to_data_url
from imagecraft.models.image_collection import ImageCollection
from imagecraft.models.transformation import (
    AugmentParams,
    ImageArray,
    TransformParams,
    resize_image,
    run_augment_pipeline,
    run_transform_pipeline,
)
from imagecraft.settings import Settings

logger = logging.getLogger(__name__)

MAX_PREVIEW_SIDE = 1920
MAX_OP_HISTORY = 20

@dataclass
class OperationRecord:
    """One undoable operation touching one or more images."""
    kind: str
    params: dict[str, Any]
    target: str  # "current" | "all"
    image_indices: list[int]
    previous_states: dict[int, ImageArray | None]  # None == original/unmodified

PERFORMANCE_PREVIEW_SIZES: dict[str, int] = {
    "low": 720,
    "medium": 1920,
}


class UIBridge(Protocol):
    """Whatever the engine needs from the host window (swappable in tests)."""

    def evaluate_js(self, code: str) -> None: ...

    def open_file_dialog(
        self, allow_multiple: bool = False, file_types: tuple[str, ...] = ()
    ) -> list[str] | None: ...

    def open_folder_dialog(self) -> str | None: ...

    def save_file_dialog(
        self, save_as: str, file_types: tuple[str, ...] = ()
    ) -> str | None: ...

    def move_window(self, x: int, y: int) -> None: ...

    def minimize_window(self) -> None: ...

    def toggle_maximize(self) -> None: ...

    def close_window(self) -> None: ...


class BackendEngine:
    """All application logic exposed to the frontend as ``js_api``."""

    def __init__(
        self,
        bridge: UIBridge | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._bridge = bridge
        self._settings = settings if settings is not None else Settings()
        self._collection = ImageCollection()
        self._lock = threading.RLock()
        self._cancel = threading.Event()
        self._op_history: list[OperationRecord] = []
        self._op_redo: list[OperationRecord] = []
        self._apply_performance_mode()

    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------

    def attach_bridge(self, bridge: UIBridge | None) -> None:
        """Attach the host-window adapter (called after the window exists)."""
        self._bridge = bridge

    def _clear_history(self) -> None:
        """Reset the global undo/redo log."""
        self._op_history.clear()
        self._op_redo.clear()

    def _push_operation(self, kind: str, params: dict[str, Any], indices: list[int], previous_states: dict[int, ImageArray | None]) -> None:
        """Record one undoable operation."""
        target = "all" if len(indices) > 1 else "current"
        self._op_history.append(OperationRecord(kind, dict(params), target, list(indices), previous_states))
        if len(self._op_history) > MAX_OP_HISTORY:
            self._op_history.pop(0)
        self._op_redo.clear()

    # ------------------------------------------------------------------
    # Settings / capabilities
    # ------------------------------------------------------------------

    def get_config(self) -> dict[str, Any]:
        return self._settings.as_dict()

    def set_config(self, key: str, value: Any) -> dict[str, Any]:
        if key == "performance_mode":
            value = self._normalize_mode(str(value))
        self._settings.set(key, value)
        if key == "performance_mode":
            self._apply_performance_mode()
        return {"ok": True}

    def get_capabilities(self) -> dict[str, Any]:
        """Report the *real* detected hardware plus the active profile.

        Everything here is queried live from OpenCV/the OS, so the About
        dialog never has to invent a synthetic "GPU: available" line: if
        ``gpu`` is ``None`` there is genuinely no usable OpenCL device.
        """
        mode = self._normalize_mode(str(self._settings.get("performance_mode", "medium")))
        try:
            have_opencl = bool(cv2.ocl.haveOpenCL())
        except Exception:  # pragma: no cover - defensive
            have_opencl = False
        try:
            using_opencl = bool(cv2.ocl.useOpenCL())
        except Exception:  # pragma: no cover - defensive
            using_opencl = False
        try:
            threads = int(cv2.getNumThreads()) or (os.cpu_count() or 1)
        except Exception:  # pragma: no cover - defensive
            threads = os.cpu_count() or 1
        gpu = self._gpu_info() if have_opencl else None
        return {
            "cv_version": cv2.__version__,
            "opencl": have_opencl,
            "opencl_in_use": using_opencl,
            "cores": os.cpu_count() or 1,
            "threads": threads,
            "cpu_name": _cpu_name(),
            "gpu": gpu,
            "performance_mode": mode,
            "preview_max": self._resolve_preview_max(),
            "backend": "GPU + CPU" if using_opencl else "CPU only",
        }

    def _gpu_info(self) -> dict[str, Any] | None:
        """Describe the default OpenCL device, or ``None`` if unavailable."""
        try:
            device = cv2.ocl.Device.getDefault()
        except Exception:  # pragma: no cover - defensive
            return None
        if device is None:
            return None

        def call(method: str) -> str:
            try:
                return str(getattr(device, method)())
            except Exception:  # pragma: no cover - defensive
                return ""

        if call("available").lower() in ("", "false"):
            return None
        try:
            dtype = int(device.type())
        except Exception:  # pragma: no cover - defensive
            dtype = 0
        if dtype & cv2.ocl.DEVICE_TYPE_GPU:
            kind = "GPU"
        elif dtype & cv2.ocl.DEVICE_TYPE_CPU:
            kind = "CPU"
        else:
            kind = "Accelerator"
        return {
            "name": call("name"),
            "vendor": call("vendorName"),
            "driver": call("driverVersion"),
            "version": call("version") or call("OpenCLVersion"),
            "type": kind,
        }

    def get_app_info(self) -> dict[str, str]:
        """Return application metadata for the About dialog."""
        from imagecraft import __version__
        return {"name": "ImageCraft", "version": __version__, "author": "Saeed Sameeh Abualnaaj"}

    # ------------------------------------------------------------------
    # Image loading / navigation
    # ------------------------------------------------------------------

    def open_image_dialog(self) -> dict[str, Any]:
        if self._bridge is None:
            return {"error": "No UI bridge available"}
        paths = self._bridge.open_file_dialog(
            file_types=(
                "Image files (*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.tif)",
                "All files (*.*)",
            )
        )
        if not paths:
            return {"ok": False, "message": "No file selected"}
        return self._load_single(Path(paths[0]))

    def open_folder_dialog(self) -> dict[str, Any]:
        if self._bridge is None:
            return {"error": "No UI bridge available"}
        directory = self._bridge.open_folder_dialog()
        if not directory:
            return {"ok": False, "message": "No folder selected"}
        return self._load_folder(Path(directory))

    def get_images(self) -> list[dict[str, Any]]:
        with self._lock:
            return self._image_metas()

    def navigate(self, delta: int) -> dict[str, Any]:
        """Move the cursor by *delta* (can be any magnitude; clamped at ends)."""
        with self._lock:
            direction = 1 if delta > 0 else (-1 if delta < 0 else 0)
            for _ in range(abs(delta)):
                if direction > 0:
                    if not self._collection.next():
                        break
                elif direction < 0:
                    if not self._collection.previous():
                        break
                else:
                    break
            return self._state_payload()

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            return self._state_payload()

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def get_preview(self, max_size: int | None = None) -> dict[str, Any]:
        """Base64 data URL of the current display image (downscaled).

        ``max_size`` defaults to the active performance profile's limit, so
        Low profile genuinely sends smaller previews to the UI.
        """
        if max_size is None:
            max_size = self._resolve_preview_max()
        with self._lock:
            item = self._collection.current
            if item is None:
                return {"dataUrl": None, "w": 0, "h": 0}
            img = downscale(item.active, max_size)
            h, w = img.shape[:2]
            return {"dataUrl": to_data_url(img), "w": w, "h": h}

    def get_compare(self, max_size: int | None = None) -> dict[str, Any]:
        """Original + processed images for the before/after comparison."""
        if max_size is None:
            max_size = self._resolve_preview_max()
        with self._lock:
            item = self._collection.current
            if item is None:
                return {"original": None, "processed": None, "w": 0, "h": 0}
            orig = downscale(item.original, max_size)
            proc = downscale(item.active, max_size)
            h, w = proc.shape[:2]
            return {
                "original": to_data_url(orig),
                "processed": to_data_url(proc),
                "w": w,
                "h": h,
            }

    # ------------------------------------------------------------------
    # Editing
    # ------------------------------------------------------------------

    def preview(self, kind: str, params: dict[str, Any]) -> dict[str, Any]:
        """Live preview of *params* against the current active image.

        Runs on a downscaled working copy (sized by the active performance
        mode) for responsiveness and reports the measured latency.
        """
        with self._lock:
            item = self._collection.current
            if item is None:
                return {"error": "No image loaded"}
            t0 = time.perf_counter()
            working = downscale(item.active, self._resolve_preview_max())
            try:
                if kind == "transform":
                    result = self._preview_transform(item, params, working)
                else:
                    result = self._run(kind, params, working)
            except ValueError as exc:
                return {"error": str(exc)}
            latency_ms = (time.perf_counter() - t0) * 1000.0
            h, w = result.shape[:2]
            return {
                "dataUrl": to_data_url(result),
                "w": w,
                "h": h,
                "latency_ms": round(latency_ms),
            }

    def apply(self, kind: str, params: dict[str, Any]) -> dict[str, Any]:
        """Apply *params* at full resolution and push an undo snapshot."""
        with self._lock:
            item = self._collection.current
            if item is None:
                return {"error": "No image loaded"}
            idx = self._collection.current_index
            prev = None if item.modified is None else item.modified.copy()
            try:
                result = self._run(kind, params, item.active)
            except ValueError as exc:
                return {"error": str(exc)}
            item.apply(result)
            self._push_operation(kind, params, [idx], {idx: prev})
            logger.info("Applied %s to %s", kind, item.path.name)
            return self._state_payload()

    def apply_all(self, kind: str, params: dict[str, Any]) -> dict[str, Any]:
        """Apply the same params to every loaded image, with progress + cancel."""
        with self._lock:
            items = list(self._collection.iter_all())
        self._cancel.clear()
        applied = 0
        total = len(items)
        applied_entries: list[tuple[int, ImageArray | None]] = []
        for idx, (_, item) in enumerate(items):
            if self._cancel.is_set():
                break
            prev = None if item.modified is None else item.modified.copy()
            try:
                result = self._run(kind, params, item.active)
            except ValueError as exc:
                logger.warning("apply_all skipped %s: %s", item.path.name, exc)
                continue
            item.apply(result)
            applied += 1
            applied_entries.append((idx, prev))
            self._emit_progress(
                int((idx + 1) / max(total, 1) * 100),
                f"{item.path.name}",
                "apply_all",
            )
        cancelled = self._cancel.is_set()
        self._emit_progress(100, "Done", "apply_all", cancelled=cancelled)
        self._emit("operation-done", {"operation": "apply_all", "cancelled": cancelled})
        with self._lock:
            if applied_entries:
                self._push_operation(
                    kind,
                    params,
                    [i for i, _ in applied_entries],
                    {i: p for i, p in applied_entries},
                )
            return {**self._state_payload(), "applied": applied, "cancelled": cancelled}

    # ------------------------------------------------------------------
    # History / reset
    # ------------------------------------------------------------------

    def undo(self) -> dict[str, Any]:
        with self._lock:
            if not self._op_history:
                return self._state_payload()
            op = self._op_history.pop()
            for idx in op.image_indices:
                item = self._collection.get(idx)
                if item is not None:
                    item.modified = op.previous_states.get(idx)
            self._op_redo.append(op)
            return self._state_payload()

    def redo(self) -> dict[str, Any]:
        with self._lock:
            if not self._op_redo:
                return self._state_payload()
            op = self._op_redo.pop()
            for idx in op.image_indices:
                item = self._collection.get(idx)
                if item is not None:
                    item.apply(self._run(op.kind, op.params, item.active))
            self._op_history.append(op)
            return self._state_payload()

    def reset_current(self) -> dict[str, Any]:
        with self._lock:
            item = self._collection.current
            if item is None:
                return self._state_payload()
            item.reset()
            self._clear_history()
            return self._state_payload()

    def reset_all(self) -> dict[str, Any]:
        with self._lock:
            self._collection.reset_all()
            self._clear_history()
            return self._state_payload()

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def save_image(self) -> dict[str, Any]:
        if self._bridge is None:
            return {"error": "No UI bridge available"}
        with self._lock:
            item = self._collection.current
            if item is None:
                return {"error": "No image loaded"}
            img = item.active
            suggested = str(item.path.with_name(item.path.stem + "_edited.png"))
        path = self._bridge.save_file_dialog(
            save_as=suggested,
            file_types=(
                "Image files (*.png;*.jpg;*.jpeg;*.bmp;*.tiff)",
                "All files (*.*)",
            ),
        )
        if not path:
            return {"ok": False, "message": "Cancelled"}
        ok, message = self._write_image(img, Path(path))
        return {"ok": ok, "message": message}

    def save_all(self, prefix: str = "", postfix: str = "") -> dict[str, Any]:
        """Save every modified image with *prefix*/*postfix* filename options."""
        if self._bridge is None:
            return {"error": "No UI bridge available"}
        with self._lock:
            modified = [(i, item) for i, item in self._collection.iter_all() if item.is_modified]
            if not modified:
                return {"ok": False, "message": "No modified images to save"}
        directory = self._bridge.open_folder_dialog()
        if not directory:
            return {"ok": False, "message": "Cancelled"}
        out_dir = Path(directory)
        self._cancel.clear()
        saved = 0
        total = len(modified)
        for idx, (_, item) in enumerate(modified):
            if self._cancel.is_set():
                break
            name = f"{prefix}{item.path.stem}{postfix}{item.path.suffix}"
            try:
                ok, message = self._write_image(item.active, out_dir / name)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("save_all failed for %s: %s", name, exc)
                ok = False
            if ok:
                saved += 1
            self._emit_progress(
                int((idx + 1) / max(total, 1) * 100), name, "save_all"
            )
        cancelled = self._cancel.is_set()
        self._emit_progress(100, "Done", "save_all", cancelled=cancelled)
        self._emit("operation-done", {"operation": "save_all", "cancelled": cancelled})
        return {
            "ok": True,
            "saved": saved,
            "total": total,
            "cancelled": cancelled,
            "message": f"Saved {saved} of {total} images",
        }

    def cancel(self) -> None:
        """Request cancellation of the current batch operation."""
        self._cancel.set()

    def save_session(self, prefix: str = "", postfix: str = "") -> dict[str, Any]:
        """Save **every** image in the session, edited or untouched alike.

        Unlike :meth:`save_all` (modified-only), this writes one file per
        loaded image using its current active state — the original pixels for
        unedited images.  The user picks the destination folder; ``prefix`` and
        ``postfix`` are filename options so originals can be preserved.
        """
        if self._bridge is None:
            return {"error": "No UI bridge available"}
        with self._lock:
            items = list(self._collection.iter_all())
            if not items:
                return {"ok": False, "message": "No images loaded"}
        directory = self._bridge.open_folder_dialog()
        if not directory:
            return {"ok": False, "message": "Cancelled"}
        out_dir = Path(directory)
        self._cancel.clear()
        saved = 0
        total = len(items)
        for idx, (_, item) in enumerate(items):
            if self._cancel.is_set():
                break
            name = f"{prefix}{item.path.stem}{postfix}{item.path.suffix}"
            try:
                ok, _ = self._write_image(item.active, out_dir / name)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("save_session failed for %s: %s", name, exc)
                ok = False
            if ok:
                saved += 1
            self._emit_progress(int((idx + 1) / max(total, 1) * 100), name, "save_session")
        cancelled = self._cancel.is_set()
        self._emit_progress(100, "Done", "save_session", cancelled=cancelled)
        self._emit("operation-done", {"operation": "save_session", "cancelled": cancelled})
        return {
            "ok": True,
            "saved": saved,
            "total": total,
            "cancelled": cancelled,
            "message": f"Saved {saved} of {total} images",
        }

    # ------------------------------------------------------------------
    # Window control (delegated to the UI bridge)
    # ------------------------------------------------------------------

    def move_window(self, x: int, y: int) -> None:
        if self._bridge is not None:
            self._bridge.move_window(int(x), int(y))

    def minimize_window(self) -> None:
        if self._bridge is not None:
            self._bridge.minimize_window()

    def toggle_maximize(self) -> None:
        if self._bridge is not None:
            self._bridge.toggle_maximize()

    def close_window(self) -> None:
        if self._bridge is not None:
            self._bridge.close_window()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load_single(self, path: Path) -> dict[str, Any]:
        try:
            self._collection.load_single(path)
        except FileNotFoundError as exc:
            return {"ok": False, "message": str(exc)}
        self._clear_history()
        return self._state_payload()

    def _load_folder(self, directory: Path) -> dict[str, Any]:
        self._cancel.clear()
        self._collection.load_folder(directory, progress_callback=self._folder_progress)
        if self._collection.is_empty:
            return {"ok": False, "message": "No supported images found"}
        self._clear_history()
        return self._state_payload()

    def _folder_progress(self, done: int, total: int, name: str) -> bool:
        self._emit_progress(int(done / max(total, 1) * 100), name, "open_folder")
        return not self._cancel.is_set()

    def _preview_transform(self, item: Any, params: dict[str, Any], working: ImageArray) -> ImageArray:
        """Build a TransformParams for the preview working copy.

        Frontend params are in *full-resolution* coordinates while the working
        copy is downscaled.  We start from image-aware identity defaults, merge
        caller-supplied values, then scale pixel-coordinate fields by the
        downscale factor so the preview is correct for any image size.
        """
        # Reference the ACTIVE image, not the on-disk original.  ``working`` is
        # downscaled from ``item.active``, so the scale factor has to be derived
        # from the same source.  Using ``item.width/height`` (original metadata)
        # made every preview after the first crop scale by the wrong ratio,
        # which is why the free-crop overlay rendered an unrelated region.
        oh, ow = item.active.shape[:2]
        wh, ww = working.shape[:2]
        kx = ww / max(1, ow)
        ky = wh / max(1, oh)

        # Image-aware identity defaults.
        base = {
            "tl_x": 0, "tl_y": 0,
            "tr_x": ow, "tr_y": 0,
            "br_x": ow, "br_y": oh,
            "bl_x": 0, "bl_y": oh,
            "translate_x": 0, "translate_y": 0,
            "rotation": 0, "scale": 100,
            "crop_top": 0, "crop_bottom": 0, "crop_left": 0, "crop_right": 0,
            "crop_x": -1, "crop_y": -1, "crop_w": -1, "crop_h": -1,
        }
        merged = {**base, **{key: val for key, val in params.items() if val is not None}}

        # Fields whose pixel values must be scaled to the working-copy size,
        # split by axis so a non-square rounding in ``downscale`` cannot drift.
        x_fields = {
            "tl_x", "tr_x", "br_x", "bl_x", "translate_x",
            "crop_left", "crop_right", "crop_x", "crop_w",
        }
        y_fields = {
            "tl_y", "tr_y", "br_y", "bl_y", "translate_y",
            "crop_top", "crop_bottom", "crop_y", "crop_h",
        }
        # Sentinel values (-1 == "no free-crop rect") must survive scaling.
        passthrough = {-1}

        defaults = TransformParams()
        scaled: dict[str, Any] = {}
        for field in dataclasses.fields(TransformParams):
            name = field.name
            value = merged.get(name, getattr(defaults, name))
            if name in x_fields or name in y_fields:
                if value in passthrough:
                    scaled[name] = int(value)
                else:
                    factor = kx if name in x_fields else ky
                    scaled[name] = int(round(value * factor))
            else:
                scaled[name] = value

        tp = TransformParams(**scaled)
        return run_transform_pipeline(working, tp)

    def _run(self, kind: str, params: dict[str, Any], img: ImageArray) -> ImageArray:
        """Dispatch a pipeline kind to the matching CV function."""
        if kind == "transform":
            tp = _as_dataclass(TransformParams, params)
            return run_transform_pipeline(img, tp)
        if kind == "augment":
            ap = _as_dataclass(AugmentParams, params)
            return run_augment_pipeline(img, ap)
        if kind == "resize":
            width = int(params.get("width", 0))
            height = int(params.get("height", 0))
            result = resize_image(img, width, height)
            return downscale(result, MAX_PREVIEW_SIDE)
        raise ValueError(f"Unknown pipeline kind: {kind}")

    def _state_payload(self) -> dict[str, Any]:
        item = self._collection.current
        return {
            "images": self._image_metas(),
            "current_index": self._collection.current_index,
            "count": self._collection.count,
            "current_path": item.path.name if item else None,
            "defaults": self._defaults_for_current(),
            "history": {
                "can_undo": bool(self._op_history),
                "can_redo": bool(self._op_redo),
            },
        }

    def _image_metas(self) -> list[dict[str, Any]]:
        metas = []
        for _, item in self._collection.iter_all():
            ah, aw = item.active.shape[:2]
            metas.append({
                "path": str(item.path),
                "name": item.path.name,
                # ``w``/``h`` describe the image currently on canvas.  The
                # free-crop overlay maps its rectangle against these, so they
                # must track ``active`` rather than the on-disk original.
                "w": aw,
                "h": ah,
                "orig_w": item.width,
                "orig_h": item.height,
                "modified": item.is_modified,
            })
        return metas

    def _defaults_for_current(self) -> dict[str, Any]:
        item = self._collection.current
        if item is None:
            return {"transform": _as_dict(TransformParams()), "augment": _as_dict(AugmentParams())}
        # Derive from the ACTIVE image.  Using the original dimensions left the
        # perspective corners describing a rectangle larger than the current
        # image after any crop, so the next preview warped the frame out to
        # stale bounds and mirrored it into the margin.
        h, w = item.active.shape[:2]
        # crop defaults are all 0 (no trimming); the free-crop rect is unset
        tp = TransformParams(
            tr_x=w, tr_y=0, br_x=w, br_y=h, bl_x=0, bl_y=h,
        )
        return {"transform": _as_dict(tp), "augment": _as_dict(AugmentParams())}

    # ------------------------------------------------------------------
    # Performance profiles
    # ------------------------------------------------------------------

    def _normalize_mode(self, mode: str) -> str:
        """Normalize legacy/unknown mode names to a supported value."""
        if mode == "low":
            return "low"
        return "medium"

    def _apply_performance_mode(self) -> None:
        """Configure OpenCL and thread count based on the current performance mode."""
        mode = self._normalize_mode(self._settings.get("performance_mode", "medium"))
        try:
            if mode == "low":
                # CPU only, single-threaded, small previews.
                cv2.ocl.setUseOpenCL(False)
                cv2.setNumThreads(1)
            else:
                # GPU (OpenCL) when available and OpenCV's full thread pool.
                # NB: setNumThreads(0) *disables* threading; -1 restores the
                # system default (all logical cores).
                cv2.ocl.setUseOpenCL(bool(cv2.ocl.haveOpenCL()))
                cv2.setNumThreads(-1)
        except Exception:  # pragma: no cover - OpenCL API absent on some builds
            cv2.setNumThreads(-1)

    def _resolve_preview_max(self) -> int:
        mode = self._normalize_mode(str(self._settings.get("performance_mode", "medium")))
        return PERFORMANCE_PREVIEW_SIZES.get(mode, MAX_PREVIEW_SIDE)

    # ------------------------------------------------------------------
    # Event emission
    # ------------------------------------------------------------------

    def _emit(self, event: str, payload: dict[str, Any]) -> None:
        if self._bridge is None:
            return
        code = (
            "window.dispatchEvent(new CustomEvent("
            f"'backend:{event}', {{detail: {json.dumps(payload)}}}))"
        )
        try:
            self._bridge.evaluate_js(code)
        except Exception:  # pragma: no cover - defensive
            logger.warning("Failed to emit backend:%s event", event)

    def _emit_progress(
        self, percent: int, message: str, operation: str, cancelled: bool = False
    ) -> None:
        self._emit("progress", {
            "operation": operation,
            "percent": min(100, max(0, int(percent))),
            "message": message,
            "cancelled": cancelled,
        })

    @staticmethod
    def _write_image(img: ImageArray, path: Path) -> tuple[bool, str]:
        bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        ok = cv2.imwrite(str(path), bgr)
        return (True, f"Saved to {path.name}") if ok else (False, f"Failed to save {path.name}")


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


def _cpu_name() -> str:
    """Best-effort human-readable CPU model name (cross-platform)."""
    if platform.system() == "Windows":  # pragma: no cover - platform specific
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            if name:
                return str(name).strip()
        except Exception:
            pass
    name = platform.processor() or platform.machine()
    return name.strip() or "Unknown CPU"


def _as_dataclass(cls: type[Any], data: dict[str, Any]) -> Any:
    """Build a dataclass instance from a JSON dict, ignoring unknown keys."""
    known = {f.name for f in dataclasses.fields(cls)}
    kwargs = {k: v for k, v in data.items() if k in known}
    return cls(**kwargs)


def _as_dict(obj: Any) -> dict[str, Any]:
    """JSON-safe dict of a dataclass instance."""
    return {f.name: getattr(obj, f.name) for f in dataclasses.fields(obj)}
