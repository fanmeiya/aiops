from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WALISSH_", env_file=".env", extra="ignore")
    database_url: str = "sqlite+aiosqlite:///./walissh.db"
    deepseek_api_key: SecretStr = SecretStr("")
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    deepseek_timeout_seconds: float = 120
    deepseek_max_retries: int = 3
    embedding_api_key: SecretStr = SecretStr("")
    embedding_base_url: str = ""
    embedding_model: str = ""
    knowledge_chunk_size: int = 800
    knowledge_chunk_overlap: int = 100
    knowledge_top_k: int = 6
    agent_max_steps: int = 50
    agent_max_tool_calls: int = 200
    secret_key: str = ""
    cors_origins: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


settings = Settings()
