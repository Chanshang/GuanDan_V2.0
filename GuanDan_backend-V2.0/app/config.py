import os
import mysql.connector
from contextlib import contextmanager

class Config:
    def __init__(self):
        self.SECRET_KEY = 'your_secret_key'
        self.DEBUG = True
        # MySQL 主库（业务真源）
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': 'crc20020820',
            'database': 'guan_egg_game'
        }
        # Redis 配置（用于读缓存/可选写回队列）
        self.redis_config = {
            'host': os.getenv('REDIS_HOST', '127.0.0.1'),
            'port': int(os.getenv('REDIS_PORT', '6379')),
            'db': int(os.getenv('REDIS_DB', '0')),
            'password': os.getenv('REDIS_PASSWORD') or None,
            'socket_timeout': float(os.getenv('REDIS_TIMEOUT_SECONDS', '0.5')),
        }
    
    def get_db_connection(self):
        conn = mysql.connector.connect(**self.db_config)
        return conn
    
config = Config()

# @contextmanager 是 Python 提供的装饰器，它能把一个“带 yield 的生成器函数”转化成上下文管理器（可 with 使用）,否则无法支持
# 用法：with get_db_connection() as conn:
# @contextmanager 
def get_db_connection():
    conn = mysql.connector.connect(**config.db_config)
    return conn