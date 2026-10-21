from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
    )

    app_name: str = "Motor CAN Tool"
    debug: bool = True
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # CAN default settings
    can_interface: str = "virtual"
    can_channel: str = "vcan0"
    can_bitrate: int = 500000

    # ZLG zlgcan library folder (contains bitrate.cfg.yaml and windows/x86_64/zlgcan.dll)
    zlg_libpath: str = str(BASE_DIR / "library")


settings = Settings()
