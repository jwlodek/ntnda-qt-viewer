"""Tests for the frame simulator."""

from __future__ import annotations

import numpy as np
import pytest

from ntnda_qt_viewer._sim import SIM_PATTERNS, FrameSimulator


@pytest.mark.parametrize("pattern", SIM_PATTERNS)
@pytest.mark.parametrize("color", [False, True])
def test_simulator_frames(pattern: str, color: bool) -> None:
    sim = FrameSimulator(pattern, (12, 16), color=color)
    first = sim.next_frame()
    second = sim.next_frame()
    if color:
        assert first.shape == (12, 16, 3)
        assert first.dtype == np.uint8
    else:
        assert first.shape == (12, 16)
        assert first.dtype == np.uint16
    assert second.shape == first.shape


def test_simulator_invalid() -> None:
    with pytest.raises(ValueError):
        FrameSimulator("bogus", (4, 4))
    with pytest.raises(ValueError):
        FrameSimulator("noise", (0, 4))
