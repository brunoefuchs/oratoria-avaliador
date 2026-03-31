from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_key: str = ""
    ml_worker_url: str = "http://localhost:7860"
    callback_secret: str = "dev-secret"
    log_level: str = "DEBUG"

    class Config:
        env_file = ".env"


settings = Settings()
