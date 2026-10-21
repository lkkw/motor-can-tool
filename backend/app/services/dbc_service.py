from pathlib import Path
import tempfile
import cantools
import cantools.database

from app.schemas.dbc import DbcParseResponse, MessageSchema, SignalSchema

# In-memory store for the currently loaded DB
_current_db: cantools.database.Database | None = None
_current_filename: str = ""
_current_response: DbcParseResponse | None = None


def get_current_db() -> cantools.database.Database | None:
    return _current_db


def get_current_response() -> DbcParseResponse | None:
    """Parse result of the currently loaded DBC, for clients that reload the page."""
    return _current_response


def parse_dbc(file_content: bytes, filename: str) -> DbcParseResponse:
    global _current_db, _current_filename, _current_response

    # Write to a temp path so cantools can detect encoding properly
    tmp = Path(tempfile.gettempdir()) / filename
    tmp.write_bytes(file_content)

    db = cantools.database.load_file(str(tmp))
    _current_db = db
    _current_filename = filename

    messages: list[MessageSchema] = []
    for msg in db.messages:
        signals: list[SignalSchema] = []
        for sig in msg.signals:
            choices: dict[str, str] | None = None
            if sig.choices:
                choices = {str(k): str(v) for k, v in sig.choices.items()}

            signals.append(
                SignalSchema(
                    name=sig.name,
                    start_bit=sig.start,
                    length=sig.length,
                    byte_order="little_endian" if sig.byte_order == "little_endian" else "big_endian",
                    is_signed=sig.is_signed,
                    scale=float(sig.scale) if sig.scale is not None else 1.0,
                    offset=float(sig.offset) if sig.offset is not None else 0.0,
                    minimum=float(sig.minimum) if sig.minimum is not None else None,
                    maximum=float(sig.maximum) if sig.maximum is not None else None,
                    unit=sig.unit or "",
                    choices=choices,
                )
            )

        messages.append(
            MessageSchema(
                id=msg.frame_id,
                id_hex=f"0x{msg.frame_id:08X}",
                name=msg.name,
                length=msg.length,
                is_extended_id=msg.is_extended_frame,
                signals=signals,
            )
        )

    _current_response = DbcParseResponse(
        filename=filename,
        message_count=len(messages),
        messages=messages,
    )
    return _current_response


def decode_frame(frame_id: int, data: bytes) -> dict[str, float | str]:
    """Decode raw CAN frame bytes to signal physical values."""
    if _current_db is None:
        return {}
    try:
        msg = _current_db.get_message_by_frame_id(frame_id)
        decoded = msg.decode(data, decode_choices=True)
        return {k: (str(v) if not isinstance(v, (int, float)) else float(v)) for k, v in decoded.items()}
    except Exception:
        return {}


def encode_frame(message_id: int, signals: dict[str, float]) -> bytes:
    """Encode signal physical values to raw CAN frame bytes."""
    if _current_db is None:
        raise ValueError("No DBC database loaded")
    msg = _current_db.get_message_by_frame_id(message_id)
    return msg.encode(signals)


def get_message_name(frame_id: int) -> str | None:
    if _current_db is None:
        return None
    try:
        return _current_db.get_message_by_frame_id(frame_id).name
    except Exception:
        return None
