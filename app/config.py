from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WALISSH_", env_file=".env", extra="ignore")
    database_url: str = "sqlite+aiosqlite:///./walissh.db"
    agent_model: str = "claude-sonnet-4-5"
    secret_key: str = ""
    cors_origins: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
