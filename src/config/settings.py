from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DELAY: int = 5
    SLEEP: int = 15

    class Config:
        env_file = ".env"

settings = Settings()
