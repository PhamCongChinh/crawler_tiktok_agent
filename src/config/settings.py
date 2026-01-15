from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DEBUG: bool = False
    DELAY: int = 5
    SLEEP: int = 60
    GPM_API: str
    PROFILE_ID: str

    API: str = "http://localhost:8000"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
