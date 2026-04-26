from pymongo import MongoClient
from src.config.settings import settings


class MongoDB:
    _client = None

    @classmethod
    def get_client(cls) -> MongoClient:
        if cls._client is None:
            cls._client = MongoClient(
                settings.MONGO_URI,
                maxPoolSize=20,
                serverSelectionTimeoutMS=5000,
            )
        return cls._client

    @classmethod
    def get_db(cls):
        return cls.get_client()[settings.MONGO_DB]
