from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DEBUG: bool = False
    BOT_NAME: str
    DELAY: int = 5
    SLEEP: int = 60
    GPM_API: str
    PROFILE_ID: str

    API: str = "http://localhost:8000"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB: str = "test_db"

    class Config:
        env_file = ".env"

settings = Settings()
