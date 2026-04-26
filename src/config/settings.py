from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_NAME: str
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "test_db"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
