import os
import mysql.connector


def _get_bool_env(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int_env(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_float_env(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


class Config:
    def __init__(self):
        self.SECRET_KEY = os.getenv("APP_SECRET_KEY", "your_secret_key")
        self.DEBUG = _get_bool_env("APP_DEBUG", True)
        self.HOST = os.getenv("APP_HOST", "0.0.0.0")
        self.PORT = _get_int_env("APP_PORT", 5000)

        # MySQL primary database settings
        self.db_config = {
            "host": os.getenv("DB_HOST", "127.0.0.1"),
            "port": _get_int_env("DB_PORT", 3306),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", "crc20020820"),
            "database": os.getenv("DB_NAME", "guan_egg_game"),
        }

        # Redis settings for cache / optional writeback queue
        self.redis_config = {
            "host": os.getenv("REDIS_HOST", "127.0.0.1"),
            "port": _get_int_env("REDIS_PORT", 6379),
            "db": _get_int_env("REDIS_DB", 0),
            "password": os.getenv("REDIS_PASSWORD") or None,
            "socket_timeout": _get_float_env("REDIS_TIMEOUT_SECONDS", 0.5),
        }

    def get_db_connection(self):
        conn = mysql.connector.connect(**self.db_config)
        return conn


config = Config()


def get_db_connection():
    conn = mysql.connector.connect(**config.db_config)
    return conn
