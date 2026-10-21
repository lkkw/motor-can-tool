from pydantic import BaseModel, ConfigDict


class SignalSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    start_bit: int
    length: int
    byte_order: str  # "little_endian" | "big_endian"
    is_signed: bool
    scale: float
    offset: float
    minimum: float | None
    maximum: float | None
    unit: str
    choices: dict[str, str] | None  # value -> label


class MessageSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    id_hex: str  # e.g. "0x18FF5001"
    name: str
    length: int  # bytes
    is_extended_id: bool
    signals: list[SignalSchema]


class DbcParseResponse(BaseModel):
    filename: str
    message_count: int
    messages: list[MessageSchema]
