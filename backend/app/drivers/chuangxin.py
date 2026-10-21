"""
python-can bus for 创芯科技 (Chuangxin) USB-CAN adapters (CANalyst-II, USBCAN-2A/2C, ...)
via the vendor's own ControlCAN.dll, so the vendor driver and tools keep working.

The DLL exposes the classic VCI API (VCI_OpenDevice / VCI_InitCAN / VCI_Transmit / ...).
Only the 64-bit DLL can be loaded from 64-bit Python.
"""
import ctypes
import os
import struct
import sys
import time
from collections import deque
from ctypes import POINTER, Structure, c_int, c_ubyte, c_uint
from pathlib import Path

from can import BusABC, CanInitializationError, CanOperationError, Message

VCI_USBCAN2 = 4  # device type used by 创芯 dual-channel adapters (CANalyst-II, USBCAN-2A/2C)

# SJA1000-style bit timing (16 MHz), same table the vendor documents: bitrate -> (Timing0, Timing1)
BIT_TIMING: dict[int, tuple[int, int]] = {
    5_000: (0xBF, 0xFF),
    10_000: (0x31, 0x1C),
    20_000: (0x18, 0x1C),
    40_000: (0x87, 0xFF),
    50_000: (0x09, 0x1C),
    80_000: (0x83, 0xFF),
    100_000: (0x04, 0x1C),
    125_000: (0x03, 0x1C),
    200_000: (0x81, 0xFA),
    250_000: (0x01, 0x1C),
    400_000: (0x80, 0xFA),
    500_000: (0x00, 0x1C),
    800_000: (0x00, 0x16),
    1_000_000: (0x00, 0x14),
}

RECV_BATCH = 2500  # max frames per VCI_Receive call, per the vendor docs


class VCI_INIT_CONFIG(Structure):
    _fields_ = [
        ("AccCode", c_uint),
        ("AccMask", c_uint),
        ("Reserved", c_uint),
        ("Filter", c_ubyte),
        ("Timing0", c_ubyte),
        ("Timing1", c_ubyte),
        ("Mode", c_ubyte),
    ]


class VCI_CAN_OBJ(Structure):
    _fields_ = [
        ("ID", c_uint),
        ("TimeStamp", c_uint),
        ("TimeFlag", c_ubyte),
        ("SendType", c_ubyte),
        ("RemoteFlag", c_ubyte),
        ("ExternFlag", c_ubyte),
        ("DataLen", c_ubyte),
        ("Data", c_ubyte * 8),
        ("Reserved", c_ubyte * 3),
    ]


def _pe_machine(path: Path) -> str:
    """Return 'x64', 'x86' or 'unknown' from a DLL's PE header."""
    with open(path, "rb") as f:
        head = f.read(4096)
    pe = struct.unpack_from("<I", head, 0x3C)[0]
    machine = struct.unpack_from("<H", head, pe + 4)[0]
    return {0x8664: "x64", 0x14C: "x86"}.get(machine, "unknown")


def load_controlcan(dll_path: str | Path):
    """Load ControlCAN.dll (a file or a folder containing it) and declare the VCI signatures."""
    path = Path(dll_path)
    if path.is_dir():
        path = path / "ControlCAN.dll"
    if not path.is_file():
        raise CanInitializationError(f"创芯 ControlCAN.dll not found: {path}")

    arch = _pe_machine(path)
    if sys.maxsize > 2**32 and arch != "x64":
        raise CanInitializationError(
            f"{path} is a {arch} DLL; 64-bit Python needs the 64-bit ControlCAN.dll from the 创芯 driver package"
        )

    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(str(path.parent))  # the DLL may load helpers from its own folder
    lib = ctypes.WinDLL(str(path)) if sys.platform == "win32" else ctypes.CDLL(str(path))

    # Return values are int: 1 = ok, 0 = fail, -1 = device not present / USB error
    for name in ("VCI_OpenDevice", "VCI_CloseDevice", "VCI_InitCAN", "VCI_StartCAN",
                 "VCI_ResetCAN", "VCI_ClearBuffer", "VCI_Transmit", "VCI_Receive", "VCI_GetReceiveNum"):
        getattr(lib, name).restype = c_int
    lib.VCI_OpenDevice.argtypes = [c_uint, c_uint, c_uint]
    lib.VCI_CloseDevice.argtypes = [c_uint, c_uint]
    lib.VCI_InitCAN.argtypes = [c_uint, c_uint, c_uint, POINTER(VCI_INIT_CONFIG)]
    lib.VCI_StartCAN.argtypes = [c_uint, c_uint, c_uint]
    lib.VCI_ResetCAN.argtypes = [c_uint, c_uint, c_uint]
    lib.VCI_ClearBuffer.argtypes = [c_uint, c_uint, c_uint]
    lib.VCI_Transmit.argtypes = [c_uint, c_uint, c_uint, POINTER(VCI_CAN_OBJ), c_uint]
    lib.VCI_Receive.argtypes = [c_uint, c_uint, c_uint, POINTER(VCI_CAN_OBJ), c_uint, c_int]
    lib.VCI_GetReceiveNum.argtypes = [c_uint, c_uint, c_uint]
    return lib


class ChuangxinBus(BusABC):
    """One channel of a 创芯 USB-CAN adapter."""

    def __init__(
        self,
        channel: int = 0,
        *,
        bitrate: int = 500_000,
        device_index: int = 0,
        device_type: int = VCI_USBCAN2,
        dll_path: str | Path,
        lib=None,  # pre-loaded library (tests)
        **kwargs,
    ):
        if bitrate not in BIT_TIMING:
            supported = ", ".join(f"{b // 1000}k" for b in BIT_TIMING)
            raise CanInitializationError(f"Unsupported bitrate {bitrate}; supported: {supported}")

        self._lib = lib or load_controlcan(dll_path)
        self._dev = (device_type, device_index)
        self._chl = int(channel)
        self._opened = False
        self._rx: deque[Message] = deque()
        self._rx_buf = (VCI_CAN_OBJ * RECV_BATCH)()
        self.channel_info = f"创芯 USB-CAN dev{device_index} CAN{self._chl + 1}"

        ret = self._lib.VCI_OpenDevice(*self._dev, 0)
        if ret != 1:
            raise CanInitializationError(
                "VCI_OpenDevice failed"
                + (": device not found (check USB, and close the vendor tool)" if ret == -1 else f" (ret={ret})")
            )
        self._opened = True
        try:
            timing0, timing1 = BIT_TIMING[bitrate]
            cfg = VCI_INIT_CONFIG(
                AccCode=0,
                AccMask=0xFFFFFFFF,
                Filter=1,  # vendor sample: 1 = receive all frames
                Timing0=timing0,
                Timing1=timing1,
                Mode=0,  # normal mode
            )
            if self._lib.VCI_InitCAN(*self._dev, self._chl, ctypes.byref(cfg)) != 1:
                raise CanInitializationError(f"VCI_InitCAN failed on CAN{self._chl + 1}")
            if self._lib.VCI_StartCAN(*self._dev, self._chl) != 1:
                raise CanInitializationError(f"VCI_StartCAN failed on CAN{self._chl + 1}")
            self._lib.VCI_ClearBuffer(*self._dev, self._chl)
        except Exception:
            # Close here: a half-initialised device stays open and blocks the next VCI_OpenDevice
            self._close_device()
            raise

        super().__init__(channel=self._chl, **kwargs)

    def _close_device(self) -> None:
        if self._opened:
            self._lib.VCI_CloseDevice(*self._dev)
            self._opened = False

    def send(self, msg: Message, timeout: float | None = None) -> None:
        obj = VCI_CAN_OBJ(
            ID=msg.arbitration_id,
            SendType=0,  # normal: retransmit until acked
            RemoteFlag=int(msg.is_remote_frame),
            ExternFlag=int(msg.is_extended_id),
            DataLen=msg.dlc,
        )
        obj.Data[: len(msg.data)] = bytes(msg.data)
        if self._lib.VCI_Transmit(*self._dev, self._chl, ctypes.byref(obj), 1) != 1:
            raise CanOperationError(f"VCI_Transmit failed on CAN{self._chl + 1}")

    def _poll(self) -> None:
        n = self._lib.VCI_Receive(*self._dev, self._chl, self._rx_buf, RECV_BATCH, 0)
        if n < 0:
            raise CanOperationError(f"VCI_Receive failed on CAN{self._chl + 1} (USB disconnected?)")
        now = time.time()
        for obj in self._rx_buf[:n]:
            self._rx.append(
                Message(
                    timestamp=now,
                    arbitration_id=obj.ID,
                    is_extended_id=bool(obj.ExternFlag),
                    is_remote_frame=bool(obj.RemoteFlag),
                    dlc=obj.DataLen,
                    data=bytes(obj.Data[: obj.DataLen]),
                    channel=self._chl,
                    is_rx=True,
                )
            )

    def _recv_internal(self, timeout: float | None) -> tuple[Message | None, bool]:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            if not self._rx:
                self._poll()
            if self._rx:
                return self._rx.popleft(), False
            if deadline is not None and time.monotonic() >= deadline:
                return None, False
            time.sleep(0.002)  # the DLL has no blocking wait; poll at ~500 Hz

    def shutdown(self) -> None:
        super().shutdown()
        self._close_device()


__all__ = ["ChuangxinBus", "BIT_TIMING", "VCI_USBCAN2", "VCI_CAN_OBJ", "VCI_INIT_CONFIG", "load_controlcan"]
