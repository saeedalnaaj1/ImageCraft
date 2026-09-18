"""Headless tests for ``imagecraft.engine.BackendEngine`` using a fake bridge."""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np
import pytest

from imagecraft.engine import BackendEngine
from imagecraft.settings import Settings


class FakeBridge:
    """Records evaluate_js calls and returns canned dialog answers."""

    def __init__(
        self,
        open_path: Path | None = None,
        folder_path: Path | None = None,
        save_path: Path | None = None,
    ) -> None:
        self.open_path = str(open_path) if open_path else None
        self.folder_path = str(folder_path) if folder_path else None
        self.save_path = str(save_path) if save_path else None
        self.events: list[str] = []

    def evaluate_js(self, code: str) -> None:
        self.events.append(code)

    def open_file_dialog(self, allow_multiple: bool = False, file_types: tuple[str, ...] = ()):
        return [self.open_path] if self.open_path else None

    def open_folder_dialog(self) -> str | None:
        return self.folder_path

    def save_file_dialog(self, save_as: str, file_types: tuple[str, ...] = ()):
        return self.save_path

    def move_window(self, x: int, y: int) -> None: ...
    def minimize_window(self) -> None: ...
    def toggle_maximize(self) -> None: ...
    def close_window(self) -> None: ...


@pytest.fixture
def image_file(tmp_path: Path) -> Path:
    img = np.zeros((80, 120, 3), dtype=np.uint8)
    img[:, :60] = (200, 40, 40)
    img[:, 60:] = (40, 200, 40)
    img[20:60, 40:80] = (255, 255, 255)
    single = tmp_path / "single"
    single.mkdir(exist_ok=True)
    path = single / "sample.png"
    cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return path


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    for i in range(3):
        img = np.full((40, 40, 3), 30 + i * 20, dtype=np.uint8)
        cv2.imwrite(str(tmp_path / f"img{i}.png"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return tmp_path


def make_engine(bridge: FakeBridge) -> BackendEngine:
    settings = Settings(path=Path("/nonexistent/settings.json"))
    engine = BackendEngine(bridge=bridge, settings=settings)
    return engine


def test_open_image_dialog_loads_and_defaults_match_dims(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    state = engine.open_image_dialog()

    assert state.get("ok", True) is not False
    assert state["count"] == 1
    assert state["current_path"] == "sample.png"
    d = state["defaults"]["transform"]
    assert d["tr_x"] == 120 and d["br_y"] == 80
    assert d["crop_top"] == 0 and d["crop_bottom"] == 0
    assert d["crop_left"] == 0 and d["crop_right"] == 0


def test_open_folder_dialog_loads_all(image_file, folder):
    bridge = FakeBridge(folder_path=folder)
    engine = make_engine(bridge)
    state = engine.open_folder_dialog()
    assert state["count"] == 3
    assert len(state["images"]) == 3


def test_preview_transform_returns_data_url(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    result = engine.preview("transform", {"scale": 80, "rotation": 15})
    assert "error" not in result
    assert result["dataUrl"].startswith("data:image/png;base64,")
    assert result["latency_ms"] >= 0
    assert not result["dataUrl"].endswith(",")


def test_apply_transform_marks_modified_and_history(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    before = engine.get_state()
    assert before["history"] == {"can_undo": False, "can_redo": False}

    state = engine.apply("transform", {"rotation": 90, "scale": 100})
    assert state["images"][0]["modified"] is True
    assert state["history"]["can_undo"] is True

    # Undo returns to original.
    state = engine.undo()
    assert state["images"][0]["modified"] is False
    assert state["history"]["can_redo"] is True

    # Redo re-applies.
    state = engine.redo()
    assert state["images"][0]["modified"] is True


def test_apply_is_cumulative_with_history(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    engine.apply("augment", {"white_balance": 30})
    engine.apply("augment", {"sharpen": 50})
    state = engine.get_state()
    assert state["history"]["can_undo"] is True

    engine.undo()
    state = engine.get_state()
    assert state["images"][0]["modified"] is True  # one edit still applied


def test_apply_resize_changes_dims(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    state = engine.apply("resize", {"width": 60, "height": 40})
    meta = state["images"][0]
    assert (meta["w"], meta["h"]) == (60, 40)


def test_new_augment_fields_are_applied(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    result = engine.preview("augment", {
        "salt_pepper": 30, "gaussian_blur": 20, "softness": 20,
        "sharpen": 20, "oil": 10, "exposure": 0.5,
    })
    assert "error" not in result
    assert result["dataUrl"].startswith("data:image")


def test_unknown_params_are_ignored(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()
    result = engine.preview("transform", {"rotation": 30, "bogus_key": 123})
    assert "error" not in result


def test_apply_all_reports_progress_and_can_cancel(image_file, folder):
    bridge = FakeBridge(folder_path=folder)
    engine = make_engine(bridge)
    engine.open_folder_dialog()

    # Cancel immediately after the first progress event.
    original_emit = engine._emit_progress
    def cancel_after_emit(percent, message, operation, cancelled=False):
        original_emit(percent, message, operation, cancelled)
        engine.cancel()
    engine._emit_progress = cancel_after_emit  # type: ignore[method-assign]

    state = engine.apply_all("augment", {"exposure": 0.5})
    assert state["cancelled"] is True
    assert state["applied"] < 3  # cancelled mid-batch


def test_apply_all_no_cancel_applies_everything(image_file, folder):
    bridge = FakeBridge(folder_path=folder)
    engine = make_engine(bridge)
    engine.open_folder_dialog()

    state = engine.apply_all("augment", {"exposure": 0.5})
    assert state["cancelled"] is False
    assert state["applied"] == 3


def test_get_compare_returns_both_images(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    engine.apply("augment", {"exposure": 1.0})
    result = engine.get_compare(max_size=200)
    assert result["original"].startswith("data:image")
    assert result["processed"].startswith("data:image")
    assert result["w"] > 0 and result["h"] > 0


def test_save_all_respects_prefix_postfix(image_file, folder, tmp_path):
    bridge = FakeBridge(folder_path=folder)
    engine = make_engine(bridge)
    engine.open_folder_dialog()
    engine.apply_all("augment", {"exposure": 0.5})

    out_dir = tmp_path / "out"
    out_dir.mkdir(exist_ok=True)
    bridge.folder_path = str(out_dir)

    result = engine.save_all(prefix="a_", postfix="_b")
    assert result["ok"] is True
    assert result["saved"] == 3
    names = sorted(p.name for p in out_dir.iterdir())
    assert names == ["a_img0_b.png", "a_img1_b.png", "a_img2_b.png"]


def test_save_session_saves_every_image_even_unedited(folder, tmp_path):
    bridge = FakeBridge(folder_path=folder)
    engine = make_engine(bridge)
    engine.open_folder_dialog()
    # Edit only the first image; the rest must still be written.
    engine.apply("augment", {"exposure": 0.5})

    out_dir = tmp_path / "session_out"
    out_dir.mkdir()
    bridge.folder_path = str(out_dir)
    bridge.events.clear()

    result = engine.save_session(prefix="s_", postfix="_x")
    assert result["ok"] is True
    assert result["saved"] == 3
    assert result["total"] == 3
    names = sorted(p.name for p in out_dir.iterdir())
    assert names == ["s_img0_x.png", "s_img1_x.png", "s_img2_x.png"]
    assert any("save_session" in code for code in bridge.events)


def test_save_session_empty_collection_is_rejected(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    result = engine.save_session()
    assert result["ok"] is False
    assert "No images" in result["message"]


def test_save_image_with_bridge(image_file, tmp_path):
    bridge = FakeBridge(open_path=image_file, save_path=str(tmp_path / "out.png"))
    engine = make_engine(bridge)
    engine.open_image_dialog()
    engine.apply("augment", {"exposure": 0.5})

    result = engine.save_image()
    assert result["ok"] is True
    assert (tmp_path / "out.png").is_file()


def test_capabilities_and_config_roundtrip(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    caps = engine.get_capabilities()
    assert caps["cv_version"]
    assert caps["cores"] >= 1
    assert isinstance(caps["opencl"], bool)

    engine.set_config("performance_mode", "medium")
    assert engine.get_config()["performance_mode"] == "medium"


def test_performance_mode_controls_preview_max(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    engine.set_config("performance_mode", "low")
    assert engine._resolve_preview_max() == 720
    engine.set_config("performance_mode", "medium")
    assert engine._resolve_preview_max() == 1920
    # Legacy values normalize to medium
    engine.set_config("performance_mode", "high")
    assert engine._resolve_preview_max() == 1920
    engine.set_config("performance_mode", "auto")
    assert engine._resolve_preview_max() == 1920


def test_capabilities_report_real_hardware(image_file):
    engine = make_engine(FakeBridge(open_path=image_file))
    caps = engine.get_capabilities()
    for key in (
        "opencl_in_use",
        "threads",
        "cpu_name",
        "gpu",
        "performance_mode",
        "preview_max",
        "backend",
    ):
        assert key in caps
    assert isinstance(caps["opencl_in_use"], bool)
    assert isinstance(caps["threads"], int) and caps["threads"] >= 1
    assert caps["cpu_name"]
    assert caps["backend"] in ("GPU + CPU", "CPU only")
    assert caps["preview_max"] == 1920
    if caps["gpu"] is not None:
        assert caps["gpu"]["name"]
        assert caps["gpu"]["type"] in ("GPU", "CPU", "Accelerator")


def test_low_profile_is_cpu_only_single_thread(image_file):
    engine = make_engine(FakeBridge(open_path=image_file))
    engine.set_config("performance_mode", "low")
    caps = engine.get_capabilities()
    assert caps["threads"] == 1
    assert caps["opencl_in_use"] is False
    assert caps["preview_max"] == 720

    engine.set_config("performance_mode", "medium")
    caps = engine.get_capabilities()
    assert caps["opencl_in_use"] == caps["opencl"]
    assert caps["preview_max"] == 1920
    # High profile must restore parallel threads (not collapse to one).
    if (os.cpu_count() or 1) > 1:
        assert caps["threads"] > 1


def test_get_preview_honors_performance_profile(tmp_path):
    big = np.full((800, 1000, 3), 128, dtype=np.uint8)
    path = tmp_path / "big.png"
    cv2.imwrite(str(path), cv2.cvtColor(big, cv2.COLOR_RGB2BGR))
    engine = make_engine(FakeBridge(open_path=path))
    engine.open_image_dialog()

    engine.set_config("performance_mode", "low")
    low = engine.get_preview()
    assert low["w"] <= 720 and low["h"] <= 720

    engine.set_config("performance_mode", "medium")
    full = engine.get_preview()
    assert full["w"] == 1000

    # An explicit cap still wins over the profile.
    capped = engine.get_preview(max_size=100)
    assert capped["w"] == 100


def test_navigate_between_images(image_file, folder):
    bridge = FakeBridge(folder_path=folder)
    engine = make_engine(bridge)
    engine.open_folder_dialog()
    assert engine.get_state()["current_index"] == 0

    state = engine.navigate(1)
    assert state["current_index"] == 1
    state = engine.navigate(-1)
    assert state["current_index"] == 0
    # Past the end stays clamped.
    engine.navigate(5)
    assert engine.get_state()["current_index"] == 2


def test_reset_image_and_all(image_file, folder):
    bridge = FakeBridge(folder_path=folder)
    engine = make_engine(bridge)
    engine.open_folder_dialog()

    engine.apply_all("augment", {"exposure": 0.5})
    assert all(m["modified"] for m in engine.get_images())

    engine.reset_all()
    assert not any(m["modified"] for m in engine.get_images())


def test_window_control_delegates_without_crash():
    bridge = FakeBridge()
    engine = make_engine(bridge)
    engine.move_window(10, 20)
    engine.minimize_window()
    engine.toggle_maximize()
    engine.close_window()


@pytest.fixture
def large_image_file(tmp_path: Path) -> Path:
    img = np.full((2400, 3200, 3), 30, dtype=np.uint8)
    img[200:2200, 200:3000] = (200, 100, 50)
    single = tmp_path / "large"
    single.mkdir(exist_ok=True)
    path = single / "large.png"
    cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return path


def _data_url_to_image(data_url: str):
    import base64
    header, b64 = data_url.split(",", 1)
    raw = base64.b64decode(b64)
    arr = np.frombuffer(raw, dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def test_preview_transform_identity_on_large_image(large_image_file):
    bridge = FakeBridge(open_path=large_image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    result = engine.preview("transform", {})
    assert "error" not in result
    img = _data_url_to_image(result["dataUrl"])
    h, w = img.shape[:2]
    # Preview downscales to at most 1920 on the long side; aspect ratio ~4:3.
    assert w > 1800 and h > 1300
    # Nearly all pixels should be non-black (identity transform).
    nonblack = np.count_nonzero(img.sum(axis=2))
    frac = nonblack / (w * h)
    assert frac > 0.95


def test_preview_transform_rotation_on_large_image(large_image_file):
    bridge = FakeBridge(open_path=large_image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    result = engine.preview("transform", {"rotation": 30})
    assert "error" not in result
    img = _data_url_to_image(result["dataUrl"])
    h, w = img.shape[:2]
    assert w > 1800 and h > 1300
    nonblack = np.count_nonzero(img.sum(axis=2))
    frac = nonblack / (w * h)
    assert frac > 0.78  # rotation crops corners but most content is still present.


def test_preview_transform_with_bogus_key_on_large_image(large_image_file):
    bridge = FakeBridge(open_path=large_image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    result = engine.preview("transform", {"rotation": 15, "bogus_key": 999})
    assert "error" not in result
    assert result["dataUrl"].startswith("data:image/png;base64,")


# ---------------------------------------------------------------------------
# Global (batch) undo/redo tests
# ---------------------------------------------------------------------------


def test_apply_all_then_undo_reverts_everything(image_file, folder):
    bridge = FakeBridge(folder_path=folder)
    engine = make_engine(bridge)
    engine.open_folder_dialog()

    state = engine.apply_all("augment", {"exposure": 0.5})
    assert state["applied"] == 3
    assert all(m["modified"] for m in state["images"])

    # Single undo should revert ALL images.
    state = engine.undo()
    assert all(not m["modified"] for m in state["images"])
    assert state["history"]["can_undo"] is False
    assert state["history"]["can_redo"] is True

    # Redo should re-apply to ALL.
    state = engine.redo()
    assert all(m["modified"] for m in state["images"])


def test_undo_is_global_across_navigation(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    engine.apply("augment", {"white_balance": 30})
    engine.navigate(1)  # stays at 0 (only one image)
    state = engine.undo()
    assert state["images"][0]["modified"] is False


def test_new_apply_clears_redo_tail(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    engine.apply("augment", {"white_balance": 30})
    engine.undo()
    assert engine.get_state()["history"]["can_redo"] is True

    # New apply should clear redo.
    engine.apply("augment", {"sharpen": 50})
    assert engine.get_state()["history"]["can_redo"] is False


def test_history_log_capped(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    from imagecraft.engine import MAX_OP_HISTORY

    for i in range(MAX_OP_HISTORY + 5):
        engine.apply("augment", {"white_balance": i})
    assert len(engine._op_history) == MAX_OP_HISTORY


def test_loading_new_collection_clears_history(image_file):
    bridge = FakeBridge(open_path=image_file)
    engine = make_engine(bridge)
    engine.open_image_dialog()

    engine.apply("augment", {"white_balance": 30})
    assert engine.get_state()["history"]["can_undo"] is True

    engine._collection.load_single(image_file)
    engine._clear_history()
    state = engine.get_state()
    assert state["history"]["can_undo"] is False
    assert state["history"]["can_redo"] is False
