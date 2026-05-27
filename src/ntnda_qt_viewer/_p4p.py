"""p4p-based NTNDArray subscription provider."""

from __future__ import annotations

import logging
import zlib

import importlib
from io import BytesIO

import numpy as np
from p4p.client.thread import Context, Disconnected
from qtpy.QtCore import QObject, Signal

__all__ = ["NTNDProvider"]

logger = logging.getLogger(__name__)

# areaDetector/ADCore maps NDDataType -> pv scalar code stored in codec.parameters
_SCALAR_CODE_TO_DTYPE: dict[int, np.dtype] = {
    1: np.dtype(np.int8),
    2: np.dtype(np.int16),
    3: np.dtype(np.int32),
    4: np.dtype(np.int64),
    5: np.dtype(np.uint8),
    6: np.dtype(np.uint16),
    7: np.dtype(np.uint32),
    8: np.dtype(np.uint64),
    9: np.dtype(np.float32),
    10: np.dtype(np.float64),
}


class NTNDProvider(QObject):
    """Subscribes to an NTNDArray PV via p4p and emits frames as numpy arrays.

    The p4p monitor callback runs in a worker thread. Received images are
    forwarded to the Qt main thread through the ``new_frame`` signal.

    p4p auto-unwraps NTNDArray values into ``ntndarray`` objects, which are
    already shaped numpy arrays with the correct dtype.
    """

    new_frame = Signal(object)
    disconnected = Signal()

    def __init__(self, channel_name: str = "DEV:XSPD1:Pva1:Image") -> None:
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
        # Disable automatic NT unwrapping so compressed NTNDArray payloads
        # are delivered as raw Value objects and can be decoded here.
        self._ctxt = Context("pva", nt=False)
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

            image = self._extract_image(value)
            if image.size == 0:
                return

            self.new_frame.emit(image)
        except Exception:
            logger.exception(
                "Unhandled error in monitor callback for %s", self._channel_name
            )

    def _extract_image(self, value: object) -> np.ndarray:
        """Extract uncompressed image data from an NTNDArray callback value."""
        raw = getattr(value, "raw", value)

        # Non-NTNDArray fallback
        if not hasattr(raw, "__getitem__"):
            return np.array(value, copy=True)

        codec_name = str(raw["codec.name"] or "").strip().lower()
        if not codec_name:
            return self._extract_uncompressed_ntndarray(raw)

        return self._decompress_ntndarray(raw, codec_name)

    def _extract_uncompressed_ntndarray(self, raw) -> np.ndarray:
        data = np.asarray(raw["value"])
        shape = self._shape_from_dimension(raw["dimension"])
        if shape:
            count = int(np.prod(shape))
            data = data[:count].reshape(shape)
        return np.array(data, copy=True)

    def _decompress_ntndarray(self, raw, codec_name: str) -> np.ndarray:
        compressed = int(raw["compressedSize"])
        uncompressed = int(raw["uncompressedSize"])
        payload = np.asarray(raw["value"])
        payload_bytes = payload.view(np.uint8).tobytes()[:compressed]

        dtype = self._dtype_from_codec_parameters(raw["codec.parameters"])
        shape = self._shape_from_dimension(raw["dimension"])
        n_elems = int(np.prod(shape)) if shape else 0

        # JPEG decode returns an image array directly in most libraries.
        if codec_name == "jpeg":
            image = self._decode_jpeg(payload_bytes, dtype)
            if shape and image.size == n_elems:
                return np.array(image.reshape(shape), copy=True)
            return np.array(image, copy=True)

        data_bytes = self._decompress_bytes(codec_name, payload_bytes, uncompressed)
        arr = np.frombuffer(data_bytes, dtype=dtype, count=n_elems)
        if shape:
            arr = arr.reshape(shape)
        return np.array(arr, copy=True)

    def _dtype_from_codec_parameters(self, parameters: object) -> np.dtype:
        try:
            code = int(parameters)
        except Exception:
            code = 0
        dtype = _SCALAR_CODE_TO_DTYPE.get(code)
        if dtype is None:
            raise ValueError(f"Unsupported codec parameter type code: {code}")
        return dtype

    def _shape_from_dimension(self, dimension: object) -> tuple[int, ...]:
        sizes = [int(d["size"]) for d in dimension]
        sizes.reverse()
        return tuple(sizes)

    def _decompress_bytes(self, codec_name: str, data: bytes, uncompressed: int) -> bytes:
        if codec_name == "zlib":
            return zlib.decompress(data)

        if codec_name == "blosc":
            try:
                blosc2 = importlib.import_module("blosc2")
                return blosc2.decompress(data)
            except ImportError:
                try:
                    blosc = importlib.import_module("blosc")
                    return blosc.decompress(data)
                except ImportError as exc:
                    raise RuntimeError(
                        "Codec 'blosc' requires Python package 'blosc2' or 'blosc'"
                    ) from exc

        if codec_name == "lz4":
            try:
                lz4_block = importlib.import_module("lz4.block")
                return lz4_block.decompress(data, uncompressed_size=uncompressed)
            except ImportError:
                pass

            try:
                imagecodecs = importlib.import_module("imagecodecs")

                if hasattr(imagecodecs, "lz4_decode"):
                    return bytes(imagecodecs.lz4_decode(data))
            except ImportError:
                pass

            raise RuntimeError("Codec 'lz4' requires Python package 'lz4' or 'imagecodecs'")

        if codec_name == "lz4hdf5":
            try:
                imagecodecs = importlib.import_module("imagecodecs")

                # Prefer the explicit lz4hdf5 API name when present.
                if hasattr(imagecodecs, "lz4hdf5_decode"):
                    return bytes(imagecodecs.lz4hdf5_decode(data))
                if hasattr(imagecodecs, "lz4h5_decode"):
                    return bytes(imagecodecs.lz4h5_decode(data))
            except ImportError:
                pass
            raise RuntimeError("Codec 'lz4hdf5' requires Python package 'imagecodecs'")

        if codec_name == "bslz4":
            try:
                imagecodecs = importlib.import_module("imagecodecs")

                if hasattr(imagecodecs, "bslz4_decode"):
                    return bytes(imagecodecs.bslz4_decode(data))
            except ImportError:
                pass
            raise RuntimeError("Codec 'bslz4' requires Python package 'imagecodecs'")

        raise RuntimeError(f"Unsupported codec: {codec_name}")

    def _decode_jpeg(self, data: bytes, dtype: np.dtype) -> np.ndarray:
        try:
            imagecodecs = importlib.import_module("imagecodecs")
            decoded = imagecodecs.jpeg_decode(data)
            return np.asarray(decoded, dtype=dtype)
        except ImportError:
            pass

        try:
            Image = importlib.import_module("PIL.Image")

            with Image.open(BytesIO(data)) as img:
                return np.asarray(img, dtype=dtype)
        except ImportError as exc:
            raise RuntimeError(
                "Codec 'jpeg' requires Python package 'imagecodecs' or 'Pillow'"
            ) from exc
