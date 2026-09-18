"""Contract tests: every engine method the web UI calls must exist and return
the shapes ``app.js`` expects. Guards against JS/Python drift."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from imagecraft.engine import BackendEngine
from imagecraft.settings import Settings

from tests.test_engine import FakeBridge, make_engine


@pytest.fixture
def image_file(tmp_path: Path) -> Path:
    img = np.zeros((60, 100, 3), dtype=np.uint8)
    img[:, :50] = (200, 40, 40)
    img[:, 50:] = (40, 200, 40)
    path = tmp_path / "img.png"
    cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return path


@pytest.fixture
def folder(tmp_path: Path) -> Path:
    for i in range(3):
        img = np.full((40, 40, 3), 30 + i * 20, dtype=np.uint8)
        cv2.imwrite(str(tmp_path / f"img{i}.png"), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return tmp_path


def loaded_engine(image_file: Path, bridge: FakeBridge | None = None) -> BackendEngine:
    engine = make_engine(bridge or FakeBridge())
    engine._collection.load_single(image_file)  # load without a dialog
    return engine


def test_config_and_capabilities(image_file):
    engine = make_engine(FakeBridge(open_path=image_file))
    cfg = engine.get_config()
    assert "theme" in cfg and "sidebar_location" in cfg and "performance_mode" in cfg
    caps = engine.get_capabilities()
    assert caps["cv_version"] and caps["cores"] >= 1
    assert isinstance(caps["opencl"], bool)
    # Extended hardware fields consumed by the About dialog.
    assert isinstance(caps["opencl_in_use"], bool)
    assert isinstance(caps["cpu_name"], str) and caps["cpu_name"]
    assert isinstance(caps["gpu"], (dict, type(None)))
    assert caps["backend"] in ("GPU + CPU", "CPU only")

    ok = engine.set_config("performance_mode", "medium")
    assert ok.get("ok") is True
    assert engine.get_config()["performance_mode"] == "medium"


def test_get_app_info(image_file):
    engine = loaded_engine(image_file, FakeBridge())
    info = engine.get_app_info()
    assert set(info) == {"name", "version", "author"}
    assert info["name"] == "ImageCraft"
    assert info["version"] == "2.0.0"


def test_get_state_shapes(image_file):
    engine = loaded_engine(image_file, FakeBridge())
    s = engine.get_state()
    assert s["count"] == 1
    assert s["current_index"] == 0
    assert s["current_path"] == "img.png"
    assert isinstance(s["images"], list) and "name" in s["images"][0]
    assert set(s["history"]) == {"can_undo", "can_redo"}
    assert set(s["defaults"]) == {"transform", "augment"}


def test_preview_and_compare_shapes(image_file):
    engine = loaded_engine(image_file, FakeBridge())
    p = engine.preview("transform", {"rotation": 10})
    assert set(p) == {"dataUrl", "w", "h", "latency_ms"}
    c = engine.get_compare()
    assert c["original"].startswith("data:image/") and c["processed"].startswith("data:image/")
    gp = engine.get_preview()
    assert gp["w"] > 0 and gp["dataUrl"].startswith("data:image/")


def test_apply_undo_redo_reset_flow(image_file):
    engine = loaded_engine(image_file, FakeBridge())
    r = engine.apply("augment", {"white_balance": 40})
    assert r["history"] == {"can_undo": True, "can_redo": False}
    assert r["images"][0]["modified"] is True

    u = engine.undo()
    assert u["history"]["can_undo"] is False
    assert u["images"][0]["modified"] is False

    re = engine.redo()
    assert re["history"]["can_redo"] is False
    assert re["images"][0]["modified"] is True

    rc = engine.reset_current()
    assert rc["images"][0]["modified"] is False
    assert rc["history"] == {"can_undo": False, "can_redo": False}


def test_apply_all_reset_all_navigate(folder):
    bridge = FakeBridge(folder_path=folder)
    engine = make_engine(bridge)
    engine.open_folder_dialog()
    assert engine.get_state()["count"] == 3

    r = engine.apply_all("augment", {"noise": 30})
    assert r["count"] == 3
    assert all(m["modified"] for m in r["images"])

    # Global undo reverts all images at once.
    u = engine.undo()
    assert all(not m["modified"] for m in u["images"])
    assert u["history"] == {"can_undo": False, "can_redo": True}

    # Redo re-applies to all.
    re = engine.redo()
    assert all(m["modified"] for m in re["images"])

    assert engine.navigate(1)["current_index"] == 1
    assert engine.navigate(-1)["current_index"] == 0

    rr = engine.reset_all()
    assert all(not m["modified"] for m in rr["images"])


def test_save_via_bridge(image_file, tmp_path):
    dest = tmp_path / "out.png"
    bridge = FakeBridge(open_path=image_file, save_path=str(dest))
    engine = loaded_engine(image_file, bridge)
    engine.apply("transform", {"scale": 120})
    res = engine.save_image()
    assert res["ok"] is True
    assert dest.is_file()


def test_resize_preview_and_apply(image_file):
    engine = loaded_engine(image_file, FakeBridge())
    p = engine.preview("resize", {"width": 50, "height": 40})
    assert set(p) == {"dataUrl", "w", "h", "latency_ms"}
    assert p["w"] == 50 and p["h"] == 40
    r = engine.apply("resize", {"width": 80, "height": 40})
    assert r["images"][0]["modified"] is True
    assert r["images"][0]["w"] == 80 and r["images"][0]["h"] == 40


def test_save_all_prefix_postfix(folder, tmp_path):
    dest = tmp_path / "out"
    dest.mkdir()
    bridge = FakeBridge(folder_path=str(dest))
    engine = make_engine(bridge)
    engine._collection.load_folder(folder)
    engine.apply_all("augment", {"noise": 10})  # mark every image modified
    res = engine.save_all("pre_", "_post")
    assert res["ok"] is True and res["saved"] == 3
    names = sorted(p.name for p in dest.iterdir())
    assert names == ["pre_img0_post.png", "pre_img1_post.png", "pre_img2_post.png"]


def test_save_session_writes_unmodified_images(folder, tmp_path):
    dest = tmp_path / "session"
    dest.mkdir()
    bridge = FakeBridge(folder_path=str(dest))
    engine = make_engine(bridge)
    engine._collection.load_folder(folder)
    # No edits at all: save_session must still export every original.
    res = engine.save_session("pre_", "_post")
    assert res["ok"] is True and res["saved"] == 3 and res["total"] == 3
    names = sorted(p.name for p in dest.iterdir())
    assert names == ["pre_img0_post.png", "pre_img1_post.png", "pre_img2_post.png"]


def test_window_and_progress_bridge_calls(folder):
    bridge = FakeBridge(folder_path=folder)
    engine = make_engine(bridge)
    engine.open_folder_dialog()
    for fn in (lambda: engine.move_window(0, 0), engine.minimize_window,
               engine.toggle_maximize, engine.close_window):
        assert fn() is None

    # Cancellation is exposed for the UI's stop button.
    assert callable(engine.cancel)

    # Batch operations push progress events through the bridge.
    bridge.events.clear()
    engine.apply_all("augment", {"noise": 20})
    assert any("backend:progress" in code for code in bridge.events)
    assert any("backend:operation-done" in code for code in bridge.events)
