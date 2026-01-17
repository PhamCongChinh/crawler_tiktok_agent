from pymongo import MongoClient
import os
from dotenv import load_dotenv
from src.config.settings import settings

load_dotenv()

MONGO_URI = settings.MONGO_URI
MONGO_DB = settings.MONGO_DB

class MongoDB:
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = MongoClient(
                MONGO_URI,
                maxPoolSize=20,
                serverSelectionTimeoutMS=5000
            )
        return cls._client

    @classmethod
    def get_db(cls):
        return cls.get_client()[MONGO_DB]
