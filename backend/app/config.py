from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openrouter_api_key: str = ""
    database_path: str = "research.db"
    model: str = "claude-sonnet-4-6"
    host: str = "127.0.0.1"
    port: int = 8000
    frontend_dir: str = "../frontend/dist"

    model_config = {"env_prefix": "", "env_file": [".env", "../.env"]}


settings = Settings()
