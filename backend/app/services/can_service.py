import asyncio
import threading
import time
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import can

from app.config import settings
from app.schemas.can import CanConnectRequest, CanFrameEvent, CanStatusResponse, PeriodicTaskInfo
from app.services import dbc_service

# ── State ────────────────────────────────────────────────────────────────────

_bus: can.BusABC | None = None
_bus_lock = threading.Lock()

_rx_count = 0
_tx_count = 0
_error_count = 0

_connected_cfg: CanConnectRequest | None = None

# Channel index used for TX / RX filtering on multi-channel cards (zlgcan); None = single-channel bus
_tx_channel: int | None = None

# SSE subscriber queues (one per connected frontend client)
_sse_queues: list[asyncio.Queue[CanFrameEvent]] = []
_sse_lock = threading.Lock()

# Periodic send tasks  {task_id: (stop event, worker thread)}
_periodic_tasks: dict[str, tuple[threading.Event, threading.Thread]] = {}
_periodic_meta: dict[str, PeriodicTaskInfo] = {}

# Background RX thread handle
_rx_thread: threading.Thread | None = None
_rx_stop_event = threading.Event()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _push_event(event: CanFrameEvent) -> None:
    """Push a CAN frame event to all SSE subscriber queues (thread-safe)."""
    with _sse_lock:
        queues = list(_sse_queues)
    for q in queues:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass  # drop if consumer is too slow


def _frame_to_event(msg: can.Message, direction: str) -> CanFrameEvent:
    name = dbc_service.get_message_name(msg.arbitration_id)
    signals = dbc_service.decode_frame(msg.arbitration_id, bytes(msg.data))
    return CanFrameEvent(
        timestamp=msg.timestamp,
        id=msg.arbitration_id,
        id_hex=f"0x{msg.arbitration_id:08X}",
        name=name,
        length=msg.dlc,
        raw_hex=msg.data.hex().upper(),
        signals=signals,
        direction=direction,
    )


# ── RX background thread ─────────────────────────────────────────────────────

def _rx_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _rx_count, _error_count
    while not _rx_stop_event.is_set():
        with _bus_lock:
            bus = _bus
        if bus is None:
            time.sleep(0.1)
            continue
        try:
            msg = bus.recv(timeout=0.1)
            if msg is None:
                continue
            # Multi-channel cards report frames from every opened channel; keep only the selected one
            if _tx_channel is not None and msg.channel is not None and msg.channel != _tx_channel:
                continue
            _rx_count += 1
            event = _frame_to_event(msg, "rx")
            loop.call_soon_threadsafe(_push_event, event)
        except can.CanError:
            _error_count += 1
        except Exception:
            _error_count += 1


def _open_zlgcan(cfg: CanConnectRequest) -> can.BusABC:
    """Open a ZLG card via the zlgcan plugin (https://github.com/jesses2025smith/zlgcan-driver)."""
    libpath = Path(cfg.libpath or settings.zlg_libpath)
    if not (libpath / "bitrate.cfg.yaml").is_file():
        raise RuntimeError(
            f"ZLG library folder not found or incomplete: {libpath} "
            "(needs bitrate.cfg.yaml and windows/x86_64/zlgcan.dll + kerneldlls)"
        )
    # The plugin opens channels by list position, so CAN2 needs configs for both CAN1 and CAN2.
    # USBCAN-I/II bitrates are looked up in bitrate.cfg.yaml (timing0/timing1).
    # filter must be explicit: the driver defaults it to 0xFF, which it then rejects as
    # "parameter not supported". 0 = dual filter; with the default acc_mask 0xFFFFFFFF it accepts all frames.
    configs = [
        {"bitrate": cfg.bitrate, "resistance": int(cfg.resistance), "filter": 0}
        for _ in range(cfg.channel_index + 1)
    ]
    return can.Bus(
        interface="zlgcan",
        device_type=cfg.device_type,
        device_index=cfg.device_index,
        libpath=str(libpath),
        configs=configs,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def connect(cfg: CanConnectRequest) -> None:
    global _bus, _connected_cfg, _tx_channel, _rx_thread, _rx_stop_event, _rx_count, _tx_count, _error_count

    disconnect()  # clean up existing connection

    _rx_count = 0
    _tx_count = 0
    _error_count = 0

    with _bus_lock:
        if cfg.interface == "zlgcan":
            _bus = _open_zlgcan(cfg)
            _tx_channel = cfg.channel_index
        else:
            _bus = can.interface.Bus(
                interface=cfg.interface,
                channel=cfg.channel,
                bitrate=cfg.bitrate,
            )
            _tx_channel = None
    _connected_cfg = cfg

    loop = asyncio.get_event_loop()
    _rx_stop_event = threading.Event()
    _rx_thread = threading.Thread(target=_rx_loop, args=(loop,), daemon=True)
    _rx_thread.start()


def disconnect() -> None:
    global _bus, _connected_cfg, _tx_channel, _rx_thread

    # Stop RX thread
    _rx_stop_event.set()
    if _rx_thread and _rx_thread.is_alive():
        _rx_thread.join(timeout=2.0)
    _rx_thread = None

    # Stop all periodic tasks and wait for them to exit before shutting down the bus
    tasks = list(_periodic_tasks.values())
    for stop_ev, _ in tasks:
        stop_ev.set()
    for _, t in tasks:
        t.join(timeout=2.0)
    _periodic_tasks.clear()
    _periodic_meta.clear()

    with _bus_lock:
        if _bus is not None:
            _bus.shutdown()
            _bus = None
    _connected_cfg = None
    _tx_channel = None


def get_status() -> CanStatusResponse:
    cfg = _connected_cfg
    channel = None
    if cfg:
        channel = f"CAN{cfg.channel_index + 1}" if cfg.interface == "zlgcan" else cfg.channel
    return CanStatusResponse(
        connected=_bus is not None,
        interface=cfg.interface if cfg else None,
        channel=channel,
        bitrate=cfg.bitrate if cfg else None,
        rx_count=_rx_count,
        tx_count=_tx_count,
        error_count=_error_count,
    )


def send_once(message_id: int, is_extended_id: bool, signals: dict[str, float]) -> None:
    global _tx_count, _error_count
    with _bus_lock:
        if _bus is None:
            raise RuntimeError("CAN bus not connected")
        data = dbc_service.encode_frame(message_id, signals)
        msg = can.Message(
            arbitration_id=message_id,
            is_extended_id=is_extended_id,
            data=data,
            channel=_tx_channel,
        )
        _bus.send(msg)
        _tx_count += 1

    # Echo to SSE as TX event
    event = _frame_to_event(
        can.Message(arbitration_id=message_id, is_extended_id=is_extended_id, data=data, timestamp=time.time()),
        "tx",
    )
    _push_event(event)


def start_periodic(message_id: int, is_extended_id: bool, signals: dict[str, float], interval_ms: int) -> str:
    global _tx_count

    task_id = str(uuid.uuid4())[:8]
    stop_ev = threading.Event()

    name = dbc_service.get_message_name(message_id)
    _periodic_meta[task_id] = PeriodicTaskInfo(
        task_id=task_id,
        message_id=message_id,
        message_name=name,
        interval_ms=interval_ms,
    )

    loop = asyncio.get_event_loop()

    def _run() -> None:
        global _tx_count, _error_count
        while not stop_ev.is_set():
            try:
                # Hold the lock while sending so disconnect() cannot shut the bus down mid-send
                with _bus_lock:
                    if _bus is None:
                        break
                    data = dbc_service.encode_frame(message_id, signals)
                    msg = can.Message(
                        arbitration_id=message_id,
                        is_extended_id=is_extended_id,
                        data=data,
                        timestamp=time.time(),
                        channel=_tx_channel,
                    )
                    _bus.send(msg)
                    _tx_count += 1
                event = _frame_to_event(msg, "tx")
                loop.call_soon_threadsafe(_push_event, event)
            except Exception:
                _error_count += 1
            stop_ev.wait(timeout=interval_ms / 1000.0)

    t = threading.Thread(target=_run, daemon=True)
    _periodic_tasks[task_id] = (stop_ev, t)
    t.start()
    return task_id


def stop_periodic(task_id: str) -> bool:
    task = _periodic_tasks.pop(task_id, None)
    _periodic_meta.pop(task_id, None)
    if task:
        stop_ev, t = task
        stop_ev.set()
        t.join(timeout=2.0)
        return True
    return False


def list_periodic_tasks() -> list[PeriodicTaskInfo]:
    return list(_periodic_meta.values())


# ── SSE subscription ──────────────────────────────────────────────────────────

async def subscribe_sse() -> AsyncGenerator[CanFrameEvent, None]:
    """Async generator: yields CAN frame events pushed from the CAN RX/TX threads."""
    q: asyncio.Queue[CanFrameEvent] = asyncio.Queue(maxsize=500)
    with _sse_lock:
        _sse_queues.append(q)
    try:
        while True:
            event = await q.get()
            yield event
    finally:
        with _sse_lock:
            _sse_queues.remove(q)
