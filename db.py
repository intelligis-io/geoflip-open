import os
import redis

# detect testing environment
is_testing = os.getenv("FLASK_ENV") == "testing"

# construct redis url
redis_host = "localhost" if is_testing else os.getenv("REDIS_HOST")
redis_port = os.getenv("REDIS_PORT")
redis_db = os.getenv("REDIS_DB")
redis_password = os.getenv("REDIS_PASSWORD")
redis_ssl = os.getenv("REDIS_SSL")

redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
if redis_ssl == "True":
    redis_url = f"rediss://:{redis_password}@{redis_host}:{redis_port}/{redis_db}?ssl_cert_reqs=optional"

# setup redis connection
redis_client = redis.StrictRedis.from_url(redis_url, decode_responses=True)
