"""p4p-based NTNDArray subscription provider."""

from __future__ import annotations

import logging

import numpy as np
from p4p.client.thread import Context, Disconnected
from qtpy.QtCore import QObject, Signal

__all__ = ["NTNDProvider"]

logger = logging.getLogger(__name__)


class NTNDProvider(QObject):
    """Subscribes to an NTNDArray PV via p4p and emits frames as numpy arrays.

    The p4p monitor callback runs in a worker thread. Received images are
    forwarded to the Qt main thread through the ``new_frame`` signal.

    p4p auto-unwraps NTNDArray values into ``ntndarray`` objects, which are
    already shaped numpy arrays with the correct dtype.
    """

    new_frame = Signal(object)
    disconnected = Signal()

    def __init__(self, channel_name: str = "13SIM1:Pva1:Image") -> None:
        super().__init__()
        self._channel_name = channel_name
        self._ctxt: Context | None = None
        self._subscription = None

    @property
    def channel_name(self) -> str:
        return self._channel_name

    @channel_name.setter
    def channel_name(self, name: str) -> None:
        was_running = self._subscription is not None
        if was_running:
            self.stop()
        self._channel_name = name
        if was_running:
            self.start()

    def start(self) -> None:
        """Start monitoring the NTNDArray PV."""
        if self._subscription is not None:
            return
        self._ctxt = Context("pva")
        self._subscription = self._ctxt.monitor(
            self._channel_name,
            self._monitor_callback,
            notify_disconnect=True,
        )
        logger.info("Subscribed to %s", self._channel_name)

    def stop(self) -> None:
        """Stop monitoring and clean up."""
        if self._subscription is not None:
            self._subscription.close()
            self._subscription = None
        if self._ctxt is not None:
            self._ctxt.close()
            self._ctxt = None
        logger.info("Unsubscribed from %s", self._channel_name)

    def _monitor_callback(self, value: object) -> None:
        """Called from a p4p worker thread on each PV update."""
        try:
            if isinstance(value, Disconnected):
                logger.warning("Channel %s disconnected", self._channel_name)
                self.disconnected.emit()
                return
            if isinstance(value, Exception):
                logger.error("Monitor error on %s: %s", self._channel_name, value)
                return

            # p4p auto-unwraps NTNDArray into ntndarray (a shaped numpy array).
            # Copy the data so it outlives the callback — p4p may reuse its buffer.
            image = np.array(value, copy=True)
            if image.size == 0:
                return

            self.new_frame.emit(image)
        except Exception:
            logger.exception(
                "Unhandled error in monitor callback for %s", self._channel_name
            )
