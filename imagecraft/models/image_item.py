"""Image item model — a single image and its processing state."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import numpy.typing as npt

logger = logging.getLogger(__name__)

ImageArray = npt.NDArray[np.uint8]
"""Type alias for a uint8 RGB image array (H × W × 3)."""


@dataclass
class ImageItem:
    """Represents one loaded image with its original data and any modifications.

    The ``original`` array is **never mutated** — all transforms and augmentations
    write to ``modified``, so the user can always reset back to the original.

    Undo/redo history is managed centrally by :class:`~imagecraft.engine.BackendEngine`,
    not per-image.

    Attributes:
        path: Filesystem path to the image file.
        original: The raw image as read from disk, converted to RGB.
        modified: The latest transformed/augmented version, or ``None`` if unchanged.
        zoom: Current zoom level for display (1.0 = 100%).
        lines: Horizontal line Y-positions drawn on the image (transform tab only).
    """

    path: Path
    original: ImageArray
    modified: ImageArray | None = None
    zoom: float = 1.0
    lines: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Sanity-check the image array."""
        if len(self.original.shape) != 3 or self.original.shape[2] != 3:
            raise ValueError(f"Expected an H×W×3 RGB array, got {self.original.shape}")

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def active(self) -> ImageArray:
        """Return the image to display: modified if available, else original."""
        return self.modified if self.modified is not None else self.original

    @property
    def is_modified(self) -> bool:
        """Whether this image has been transformed or augmented."""
        return self.modified is not None

    @property
    def height(self) -> int:
        return int(self.active.shape[0])

    @property
    def width(self) -> int:
        return int(self.active.shape[1])

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def apply(self, result: ImageArray) -> None:
        """Store a processing result as the new modified image."""
        self.modified = result

    def reset(self) -> None:
        """Discard modifications, zoom, and lines."""
        self.modified = None
        self.zoom = 1.0
        self.lines.clear()
