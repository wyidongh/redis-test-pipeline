import pytest
import time


class TestRedisBasic:
    """Redis 基础功能测试"""
    
    def test_ping(self, redis_client):
        """测试连接"""
        assert redis_client.ping() is True
        
    def test_string_set_get(self, redis_client):
        """测试字符串操作"""
        redis_client.set("key1", "value1")
        assert redis_client.get("key1") == "value1"
        
    def test_string_expire(self, redis_client):
        """测试过期时间"""
        redis_client.setex("temp_key", 2, "temp_value")
        assert redis_client.get("temp_key") == "temp_value"
        time.sleep(3)
        assert redis_client.get("temp_key") is None
        
    def test_list_operations(self, redis_client):
        """测试列表操作"""
        redis_client.rpush("mylist", "a", "b", "c")
        assert redis_client.lrange("mylist", 0, -1) == ["a", "b", "c"]
        assert redis_client.lpop("mylist") == "a"
        
    def test_hash_operations(self, redis_client):
        """测试哈希操作"""
        redis_client.hset("user:1", mapping={"name": "zhangsan", "age": "25"})
        assert redis_client.hget("user:1", "name") == "zhangsan"
        assert redis_client.hgetall("user:1") == {"name": "zhangsan", "age": "25"}
        
    def test_set_operations(self, redis_client):
        """测试集合操作"""
        redis_client.sadd("tags", "python", "redis", "database")
        assert redis_client.sismember("tags", "redis") == 1
        assert redis_client.scard("tags") == 3
        
    def test_zset_operations(self, redis_client):
        """测试有序集合"""
        redis_client.zadd("leaderboard", {"player1": 100, "player2": 200, "player3": 150})
        assert redis_client.zrevrange("leaderboard", 0, 0) == ["player2"]
        assert redis_client.zrange("leaderboard", 0, -1, withscores=True) == [
            ("player1", 100.0), ("player3", 150.0), ("player2", 200.0)
        ]
        
    def test_transaction(self, redis_client):
        """测试事务"""
        pipe = redis_client.pipeline()
        pipe.multi()
        pipe.set("trans_key", "trans_value")
        pipe.get("trans_key")
        results = pipe.execute()
        assert results == [True, "trans_value"]
        
    def test_pubsub(self, redis_client):
        """测试发布订阅"""
        pubsub = redis_client.pubsub()
        pubsub.subscribe("test_channel")
        
        # 等待订阅就绪
        import time
        time.sleep(0.1)
        
        redis_client.publish("test_channel", "hello")
        
        # 接收消息
        for message in pubsub.listen():
            if message["type"] == "message":
                assert message["data"] == "hello"
                break
                
        pubsub.unsubscribe()
        pubsub.close()


class TestRedisPersistence:
    """持久化测试"""
    
    def test_rdb_save(self, redis_server, redis_client):
        """测试 RDB 保存"""
        redis_client.set("persist_key", "persist_value")
        assert redis_client.bgsave() is True
        
        # 等待保存完成
        time.sleep(2)
        
        # 检查 RDB 文件
        import os
        rdb_file = "/tmp/redis-test/dump.rdb"
        assert os.path.exists(rdb_file)
        
    def test_aof_rewrite(self, redis_client):
        """测试 AOF 重写"""
        redis_client.set("aof_key", "aof_value")
        assert redis_client.bgrewriteaof() is True
        time.sleep(2)
