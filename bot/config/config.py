from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    API_ID: int
    API_HASH: str

    START_DELAY: list[int] = [5, 15]
    SLEEP_TIME: list[int] = [7200, 10800]
    AUTO_TASK: bool = True
    JOIN_TG_CHANNELS: bool = False
    REF_ID: str = '2MSH0'
    STAKING: bool = True
    STAKE_ALL: bool = False
    MIN_STAKING_BALANCE: float = 200.0

    USE_PROXY_FROM_FILE: bool = False


settings = Settings()
