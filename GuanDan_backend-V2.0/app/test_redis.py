from flask import Flask, jsonify
import redis
import time
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)  # 全局允许跨域请求

# 连接到本地的 Redis 服务器
# decode_responses=True 会自动把 Redis 返回的字节(bytes)转成字符串(string)，避免遇到 b'123' 这种格式
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# ==========================================
# 场景 1：利用 Redis 做高并发计数器
# ==========================================
@app.route('/')
def home():
    # INCR 命令：每次访问，把 'site_visits' 这个 key 的值加 1。
    # 如果 key 不存在，Redis 会自动创建并从 1 开始。这个操作是绝对原子性、极快的。
    visits = r.incr('site_visits')
    return f"<h1>欢迎来到我的站点！</h1><p>你是第 <b>{visits}</b> 位访客 (由 Redis 实时统计)</p>"


# ==========================================
# 场景 2：利用 Redis 缓存“慢速”的数据库查询
# ==========================================
@app.route('/article/<int:article_id>')
def get_article(article_id):
    # 1. 定义一个规范的 Cache Key（缓存键名）
    cache_key = f"article:{article_id}:content"
    
    # 2. 【读缓存】先去 Redis 里找数据
    cached_content = r.get(cache_key)
    
    if cached_content:
        # 如果 Redis 里有数据，直接秒回给前端（缓存命中 ⚡）
        return jsonify({
            "source": "Redis 缓存 ⚡ (耗时 < 1ms)",
            "article_id": article_id,
            "content": cached_content
        })

    # 3. 【查数据库】如果 Redis 里没有数据（缓存未命中）
    # 这里我们用 time.sleep 模拟 MySQL 复杂的联表查询，假装它很慢，需要耗时 2 秒
    time.sleep(2) 
    
    # 假装这是从 MySQL 查出来的数据
    db_content = f"这是文章 {article_id} 的正文内容。这里可能包含了上万字的干货..."

    # 4. 【写缓存】查到数据后，把它塞回 Redis 存起来，方便下次别人查。
    # setex (set with expiration)：存入数据的同时，设置 60 秒后自动过期删除。
    r.setex(cache_key, 10, db_content)

    return jsonify({
        "source": "MySQL 数据库 🐢 (耗时 2000ms)",
        "article_id": article_id,
        "content": db_content
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)