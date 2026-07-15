from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "LocalHub API"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///./local_hub.db"
    OPENAI_API_KEY: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()