import os


class Config:
    DATABASE_URL = "sqlite:///./database.db"


class TestConfig(Config):
    DATABASE_URL = "sqlite:///./test.db"


def get_config():
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "testing":
        return TestConfig
    return Config
