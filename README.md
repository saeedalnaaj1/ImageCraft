# ImageCraft

**A non-destructive image transformation & augmentation workbench for preparing image datasets.**

ImageCraft is a desktop application that lets you load a single image or an entire folder, edit
each image through live, non-destructive previews, and batch-apply the same operation across the
whole set. Every change can be undone, and nothing is written to disk until you explicitly save.

Built with a Python/OpenCV backend and an offline web UI rendered by
[pywebview](https://pywebview.flowrl.com/) — no browser, no server, no internet required.

---

## Table of contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Saving & exporting](#saving--exporting)
- [Performance profiles](#performance-profiles)
- [Keyboard shortcuts](#keyboard-shortcuts)
- [Supported formats](#supported-formats)
- [Configuration](#configuration)
- [Project structure](#project-structure)
- [Development](#development)
- [License](#license)

---

## Features

- **Open a single image or a whole folder** — the folder becomes a navigable batch.
- **Transform panel** — perspective correction, translation, rotation, scale, flips and a
  drag-to-select **free crop**.
- **Augment panel** — white balance, HSV hue/saturation/brightness, exposure, Gaussian blur,
  softness, sharpen, oil paint, noise, salt & pepper, geometry (rotate/shift/scale/shear),
  flips and padding to a target size.
- **Resize panel** — exact output dimensions with an aspect-ratio lock.
- **Live preview** — every control renders a preview before you commit it.
- **Before / after compare** — a synchronized original-vs-processed view.
- **Apply to All** — run the current settings across the entire loaded folder.
- **Non-destructive editing** — the originals are kept in memory; edits are cumulative and
  globally undoable/redoable, including batch operations.
- **Flexible saving** — save the current image, all modified images, or every image in the
  session, with optional filename prefix/postfix.
- **Performance profiles** — High (GPU via OpenCL + all CPU cores) or Low (CPU-only,
  single-threaded) with automatic hardware detection shown in the About dialog.
- **Built-in guided tutorial** — a step-by-step walkthrough from the toolbar.
- **Quality-of-life** — dark/light themes, a dockable/collapsible sidebar, and keyboard shortcuts.

---

## Requirements

- **Python 3.11+**
- **Windows** is the primary target. pywebview also supports macOS and Linux (GTK/Qt backends).
- Dependencies are installed automatically: `opencv-python`, `numpy`, `pywebview`.

---

## Installation

```bash
git clone <your-repo-url>
cd ImageCraft

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e .
```

Run it with either:

```bash
imagecraft
# or
python -m imagecraft
```

---

## Usage

1. **Open** an image (`Ctrl+O`) or a **Folder** (`Ctrl+Shift+O`).
2. Choose a panel from the sidebar: **Transform**, **Augment**, **Resize** or **Export**.
3. Adjust the controls — the viewer updates with a live preview.
4. Click **Apply** to commit to the current image, or **Apply to All** for the whole batch.
5. **Save** your result (see below).

Use the floating viewer tools (or `Ctrl +/−`, **Fit**, **1:1**) to zoom, and press **A** / **D**
to move between images in a batch.

---

## Saving & exporting

| Action | What it writes | Toolbar | Shortcut |
| --- | --- | --- | --- |
| **Save** | the current image, to a path you choose | `Save` | `Ctrl+S` |
| **Save Modified** | every image you have edited | `Save Modified` | `Ctrl+Shift+S` |
| **Save All** | **every** image in the session (edited or not) | `Save All` | `Ctrl+Shift+A` |

The **Export** panel also exposes the same actions plus a filename **prefix** and **postfix**, so
batch output can be written alongside the originals without overwriting them (e.g.
`batch_photo_v2.png`).

> **Tip:** *Save All* writes one file per loaded image. Pick a different destination folder or set
> a prefix/postfix if you do not want to overwrite the source files.

---

## Performance profiles

Select a profile from the **Perf** menu in the toolbar. The **About** dialog reports exactly what
was detected on your machine (CPU model, cores/threads, OpenCL availability, GPU name and driver).

| Profile | Compute | Preview resolution | Best for |
| --- | --- | --- | --- |
| **High** (default) | GPU via OpenCL (when available) + all CPU cores | up to 1920 px | Most users, including machines with a dedicated GPU |
| **Low** | CPU only, single-threaded | up to 720 px | Machines without a usable GPU, or to reduce resource use |

If no OpenCL device is present, the High profile automatically falls back to CPU processing with
the full thread pool.

---

## Keyboard shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+O` | Open image |
| `Ctrl+Shift+O` | Open folder |
| `Ctrl+S` | Save current image |
| `Ctrl+Shift+S` | Save modified images |
| `Ctrl+Shift+A` | Save all images in the session |
| `Ctrl+Z` | Undo |
| `Ctrl+Y` / `Ctrl+Shift+Z` | Redo |
| `Ctrl+0` | Fit to window |
| `Ctrl++` / `Ctrl+-` | Zoom in / out |
| `1` / `2` / `3` / `4` | Switch to Transform / Augment / Resize / Export |
| `A` / `D` | Previous / next image |

---

## Supported formats

**Read & write:** PNG, JPEG (`.jpg`/`.jpeg`), BMP, TIFF (`.tif`/`.tiff`).

---

## Configuration

Settings are stored as JSON (on Windows: `%APPDATA%\ImageCraft\settings.json`) and include theme,
sidebar position/state, performance mode, live-preview toggle, export prefix/postfix and the last
browsed directory.

Set the `IMAGECRAFT_CONFIG` environment variable to store `settings.json` in a custom directory —
useful for a portable install.

---

## Project structure

```
ImageCraft/
├── pyproject.toml            # packaging, dependencies, tooling config
├── imagecraft/
│   ├── main.py               # pywebview window bootstrap / UI bridge
│   ├── engine.py             # BackendEngine — js_api: editing, history, save, capabilities
│   ├── io.py                 # base64 data URLs + preview downscaling
│   ├── settings.py           # persistent JSON settings
│   ├── logging_config.py
│   ├── models/               # ImageItem, ImageCollection, transformation + augmentation pipelines
│   └── ui/                   # offline web UI (served locally by pywebview)
│       ├── index.html
│       ├── css/theme.css
│       ├── assets/           # application icon
│       └── js/               # ES modules: app, viewer, sidebar, panels, tutorial, ...
└── tests/                    # pytest suite + UI/backend contract tests
```

---

## Development

Install the development extras and run the checks:

```bash
pip install -e ".[dev]"

pytest -q
mypy imagecraft
ruff check imagecraft
```

The engine is fully headless-testable through a fake `UIBridge`, and `tests/test_ui_contract.py`
guards against Python/JavaScript API drift.

---

## License

Released under the **MIT License**. See [LICENSE](LICENSE).

## Author

**Saeed Sameeh Abualnaaj**
