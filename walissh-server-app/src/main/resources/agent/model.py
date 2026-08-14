"""DeepSeek client construction without a high-level model framework."""
from app.config import settings


def deepseek_client():
    from openai import AsyncOpenAI

    api_key = settings.deepseek_api_key.get_secret_value()
    if not api_key:
        raise RuntimeError("未配置 WALISSH_DEEPSEEK_API_KEY")
    return AsyncOpenAI(
        api_key=api_key,
        base_url=settings.deepseek_base_url.rstrip("/"),
        timeout=settings.deepseek_timeout_seconds,
        max_retries=settings.deepseek_max_retries,
    )
