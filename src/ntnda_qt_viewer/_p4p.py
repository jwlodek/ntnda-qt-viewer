"""p4p-based NTNDArray subscription provider."""

from __future__ import annotations

import asyncio
import importlib
import logging
import threading
import zlib
from collections.abc import Callable, Iterable, Mapping
from io import BytesIO
from typing import Protocol, cast

import numpy as np
from aioca import CANothing, camonitor
from p4p.client.thread import Context, Disconnected
from qtpy.QtCore import QObject, Signal

__all__ = ["NTNDAProvider"]

logger = logging.getLogger(__name__)


class _Subscription(Protocol):
    def close(self) -> None: ...


class _Indexable(Protocol):
    def __getitem__(self, key: str, /) -> object: ...


def _to_int(value: object, default: int) -> int:
    if isinstance(value, (int, float, str, np.integer, np.floating)):
        try:
            return int(value)
        except ValueError:
            return default
    return default


_ca_loop: asyncio.AbstractEventLoop | None = None
_ca_loop_lock = threading.Lock()


def _get_ca_loop() -> asyncio.AbstractEventLoop:
    """Return a shared asyncio loop, running in a daemon thread, for aioca."""
    global _ca_loop
    with _ca_loop_lock:
        if _ca_loop is None:
            loop = asyncio.new_event_loop()
            threading.Thread(target=loop.run_forever, name="aioca", daemon=True).start()
            _ca_loop = loop
        return _ca_loop


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


class NTNDAProvider(QObject):
    """Subscribes to an NTNDArray PV via p4p and emits frames as numpy arrays.

    The p4p monitor callback runs in a worker thread. Received images are
    forwarded to the Qt main thread through the ``new_frame`` signal.

    p4p auto-unwraps NTNDArray values into ``ntndarray`` objects, which are
    already shaped numpy arrays with the correct dtype.
    """

    new_frame = Signal(object)
    disconnected = Signal()

    def __init__(
        self,
        channel_name: str = "DEV:XSPD1:Pva1:Image",
        *,
        raw_waveform: bool = False,
        image_shape: tuple[int, int] | None = None,
        color: bool = False,
        use_ca: bool = False,
    ) -> None:
        super().__init__()
        if raw_waveform and image_shape is None:
            raise ValueError("image_shape is required when raw_waveform=True")
        if use_ca and not raw_waveform:
            raise ValueError("use_ca is only supported when raw_waveform=True")
        self._channel_name = channel_name
        self._raw_waveform = raw_waveform
        self._use_ca = use_ca
        # Only used for non-NTNDArray PVs, whose payload is a flat array.
        self._image_shape = image_shape
        self._color = color
        self._ctxt: Context | None = None
        self._subscription: _Subscription | None = None

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
        if self._use_ca:
            self._start_ca()
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

    def _start_ca(self) -> None:
        async def subscribe() -> _Subscription:
            # camonitor must be created from within the running loop.
            return camonitor(
                self._channel_name, self._monitor_callback, notify_disconnect=True
            )

        loop = _get_ca_loop()
        self._subscription = asyncio.run_coroutine_threadsafe(
            subscribe(), loop
        ).result()
        logger.info("Subscribed to %s via Channel Access", self._channel_name)

    def stop(self) -> None:
        """Stop monitoring and clean up."""
        if self._subscription is not None:
            if self._use_ca:
                subscription = self._subscription

                async def close() -> None:
                    subscription.close()

                # Wait so the close can't race aioca's atexit teardown.
                asyncio.run_coroutine_threadsafe(close(), _get_ca_loop()).result()
            else:
                self._subscription.close()
            self._subscription = None
        if self._ctxt is not None:
            self._ctxt.close()
            self._ctxt = None
        logger.info("Unsubscribed from %s", self._channel_name)

    def _monitor_callback(self, value: object) -> None:
        """Called from a p4p worker thread on each PV update."""
        try:
            if isinstance(value, (Disconnected, CANothing)):
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
        """Extract image data from an NTNDArray or a flat array PV."""
        if not self._raw_waveform or self._image_shape is None:
            return self._extract_ntndarray_image(value)
        return self._extract_raw_array_image(value, self._image_shape)

    def _extract_raw_array_image(
        self, value: object, shape: tuple[int, int]
    ) -> np.ndarray:
        raw: object = getattr(value, "raw", value)
        if self._has_key(raw, "value"):
            data = np.asarray(self._raw_get(raw, "value", []))
        else:
            data = np.asarray(value)

        rows, cols = shape
        target = (rows, cols, 3) if self._color else (rows, cols)
        count = int(np.prod(target))
        flat = data.reshape(-1)
        if flat.size < count:
            logger.warning(
                "Array from %s has %d elements, expected at least %d for shape %s",
                self._channel_name,
                flat.size,
                count,
                target,
            )
            return np.empty(0, dtype=data.dtype)
        return np.array(flat[:count].reshape(target), copy=True)

    def _extract_ntndarray_image(self, value: object) -> np.ndarray:
        """Extract uncompressed image data from an NTNDArray callback value."""
        raw: object = getattr(value, "raw", value)

        if not self._has_key(raw, "value"):
            return np.array(value, copy=True)

        codec_name = str(self._raw_get(raw, "codec.name", "") or "").strip().lower()
        if not codec_name:
            return self._extract_uncompressed_ntndarray(raw)

        return self._decompress_ntndarray(raw, codec_name)

    def _extract_uncompressed_ntndarray(self, raw: object) -> np.ndarray:
        data = np.asarray(self._raw_get(raw, "value", []))
        shape = self._shape_from_dimension(self._raw_get(raw, "dimension", []))
        if shape:
            count = int(np.prod(shape))
            data = data[:count].reshape(shape)
        return np.array(data, copy=True)

    def _decompress_ntndarray(self, raw: object, codec_name: str) -> np.ndarray:
        compressed = _to_int(self._raw_get(raw, "compressedSize", 0), 0)
        uncompressed = _to_int(self._raw_get(raw, "uncompressedSize", 0), 0)
        payload = np.asarray(self._raw_get(raw, "value", []))
        payload_bytes = payload.view(np.uint8).tobytes()[:compressed]

        dtype = self._dtype_from_codec_parameters(
            self._raw_get(raw, "codec.parameters", 0)
        )
        shape = self._shape_from_dimension(self._raw_get(raw, "dimension", []))
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
        code = _to_int(parameters, 0)
        dtype = _SCALAR_CODE_TO_DTYPE.get(code)
        if dtype is None:
            raise ValueError(f"Unsupported codec parameter type code: {code}")
        return dtype

    def _shape_from_dimension(self, dimension: object) -> tuple[int, ...]:
        if not isinstance(dimension, Iterable):
            return ()
        sizes: list[int] = []
        for d in dimension:
            size: object
            if isinstance(d, Mapping):
                size = cast(Mapping[str, object], d).get("size")
            else:
                size = getattr(d, "size", None)
            if size is None:
                continue
            sizes.append(_to_int(size, 0))
        sizes.reverse()
        return tuple(sizes)

    def _raw_get(self, raw: object, key: str, default: object = None) -> object:
        try:
            return cast(_Indexable, raw)[key]
        except Exception:
            getter: object = getattr(raw, "get", None)
            if callable(getter):
                try:
                    return cast(Callable[[str, object], object], getter)(key, default)
                except Exception:
                    pass
        return default

    def _has_key(self, raw: object, key: str) -> bool:
        try:
            value = cast(_Indexable, raw)[key]
        except Exception:
            return False
        return value is not None

    def _decompress_bytes(
        self, codec_name: str, data: bytes, uncompressed: int
    ) -> bytes:
        if codec_name == "zlib":
            return zlib.decompress(data)

        if codec_name == "blosc":
            try:
                blosc2 = importlib.import_module("blosc2")
                return bytes(blosc2.decompress(data))
            except ImportError:
                try:
                    blosc = importlib.import_module("blosc")
                    return bytes(blosc.decompress(data))
                except ImportError as exc:
                    raise RuntimeError(
                        "Codec 'blosc' requires Python package 'blosc2' or 'blosc'"
                    ) from exc

        if codec_name == "lz4":
            try:
                lz4_block = importlib.import_module("lz4.block")
                return bytes(lz4_block.decompress(data, uncompressed_size=uncompressed))
            except ImportError:
                pass

            try:
                imagecodecs = importlib.import_module("imagecodecs")

                if hasattr(imagecodecs, "lz4_decode"):
                    return bytes(imagecodecs.lz4_decode(data))
            except ImportError:
                pass

            raise RuntimeError(
                "Codec 'lz4' requires Python package 'lz4' or 'imagecodecs'"
            )

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
