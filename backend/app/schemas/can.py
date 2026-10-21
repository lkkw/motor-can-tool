from pydantic import BaseModel, ConfigDict


class CanConnectRequest(BaseModel):
    interface: str = "virtual"
    channel: str = "vcan0"
    bitrate: int = 500000

    # Vendor cards: interface="zlgcan" (周立功) or "chuangxin" (创芯)
    device_type: int = 4  # zlgcan only, ZCANDeviceType: 3 = USBCAN-I, 4 = USBCAN-II
    device_index: int = 0  # which card, when several of the same type are plugged in
    channel_index: int = 0  # 0 = CAN1, 1 = CAN2
    libpath: str | None = None  # driver folder; None = settings.zlg_libpath / settings.chuangxin_libpath
    resistance: bool = True  # zlgcan only: 120Ω terminal resistor (only on cards that support switching it)


class CanSendRequest(BaseModel):
    message_id: int
    is_extended_id: bool = False
    signals: dict[str, float]  # signal_name -> physical value
    interval_ms: int = 0  # 0 = once, >0 = periodic


class CanFrameEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: float
    id: int
    id_hex: str
    name: str | None
    length: int
    raw_hex: str
    signals: dict[str, float | str]
    direction: str  # "rx" | "tx"


class CanStatusResponse(BaseModel):
    connected: bool
    interface: str | None
    channel: str | None
    bitrate: int | None
    rx_count: int
    tx_count: int
    error_count: int


class PeriodicTaskInfo(BaseModel):
    task_id: str
    message_id: int
    message_name: str | None
    interval_ms: int
