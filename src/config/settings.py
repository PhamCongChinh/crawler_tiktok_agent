from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DEBUG: bool = False
    BOT_NAME: str
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "test_db"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
