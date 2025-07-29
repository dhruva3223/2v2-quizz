from configparser import ConfigParser
from pathlib import Path
import os

path = Path(__file__)
dir_path = path.parent.absolute()


class Config(object):
    def __init__(self) -> None:
        env = os.environ.get("APP_ENV")
        config = self.getConfig(env)
        self.ENV = env
        self.DATABASE_URL = config.get("DATABASE_URL")
        self.REDIS_URL = config.get("REDIS_URL")
        self.SECRET_KEY = config.get("SECRET_KEY")
        self.ALGORITHM = config.get("ALGORITHM")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = config.get("ACCESS_TOKEN_EXPIRE_MINUTES")
        self.GAME_DURATION = config.get("GAME_DURATION")
        self.MAX_TEAM_SIZE = config.get("MAX_TEAM_SIZE")
        self.MATCHMAKING_TIMEOUT = config.get("MATCHMAKING_TIMEOUT")
        self.DATABASE_USER = config.get("MATCHMAKING_TIMEOUT")
        self.DATABASE_PASSWORD = config.get("DATABASE_PASSWORD")
        self.DATABASE_HOST = config.get("DATABASE_HOST")
        self.DATABASE_NAME = config.get("DATABASE_NAME")

    def getConfig(self, env: str):
        config_parser = ConfigParser()
        config_parser.read(os.path.join(dir_path, f"{env}.ini"))
        return config_parser["config"]
    
