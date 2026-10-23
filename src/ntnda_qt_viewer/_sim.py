"""Synthetic frame generator for exercising the viewer without an IOC."""

from __future__ import annotations

import numpy as np

__all__ = ["SIM_PATTERNS", "FrameSimulator"]

SIM_PATTERNS = ("gradient", "noise", "spot", "checkerboard", "rings")


class FrameSimulator:
    """Produce animated test frames of a fixed shape and format.

    Parameters
    ----------
    pattern : str
        One of ``SIM_PATTERNS``.
    shape : tuple of int
        ``(rows, cols)`` of each frame.
    color : bool, optional
        Produce ``(rows, cols, 3)`` uint8 RGB frames instead of uint16 mono.
    """

    def __init__(
        self, pattern: str, shape: tuple[int, int], color: bool = False
    ) -> None:
        if pattern not in SIM_PATTERNS:
            raise ValueError(
                f"pattern must be one of {SIM_PATTERNS}, got {pattern!r}"
            )
        rows, cols = shape
        if rows <= 0 or cols <= 0:
            raise ValueError(f"shape must be positive, got {shape!r}")
        self._pattern = pattern
        self._rows, self._cols = rows, cols
        self._color = color
        self._yy, self._xx = np.mgrid[0:rows, 0:cols].astype(np.float32)
        self._rng = np.random.default_rng()
        self._frame = 0

    def next_frame(self) -> np.ndarray:
        """Return the next frame of the animation."""
        t = self._frame / 20.0
        self._frame += 1
        values = self._normalized(t)
        if self._color:
            rgb = np.stack(
                [values, np.roll(values, self._cols // 3, axis=1), 1.0 - values],
                axis=-1,
            )
            return (rgb * 255).astype(np.uint8)
        return (values * 65535).astype(np.uint16)

    def _normalized(self, t: float) -> np.ndarray:
        """Pattern values in [0, 1] at time ``t``."""
        rows, cols, yy, xx = self._rows, self._cols, self._yy, self._xx
        small = min(rows, cols)
        if self._pattern == "gradient":
            ramp = xx / max(cols - 1, 1) + yy / max(rows - 1, 1)
            return (ramp / 2 + 0.05 * t) % 1.0
        if self._pattern == "noise":
            return self._rng.random((rows, cols), dtype=np.float32)
        if self._pattern == "spot":
            cy = rows / 2 + rows / 4 * np.sin(t)
            cx = cols / 2 + cols / 4 * np.cos(t)
            sigma = max(small / 10, 1.0)
            spot = np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * sigma**2))
            noise = 0.05 * self._rng.random((rows, cols), dtype=np.float32)
            return np.clip(spot + noise, 0.0, 1.0)
        if self._pattern == "checkerboard":
            size = max(small // 8, 1)
            offset = int(t * size) % (2 * size)
            return (((xx + offset) // size + yy // size) % 2).astype(np.float32)
        # rings
        r = np.hypot(yy - rows / 2, xx - cols / 2)
        period = max(small / 10, 1.0)
        return 0.5 + 0.5 * np.sin(2 * np.pi * (r / period - t))
