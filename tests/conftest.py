import pytest
import redis
import os
import time
import subprocess


class RedisServer:
    """管理 Redis 服务器生命周期"""
    
    def __init__(self, redis_server_path="/usr/local/bin/redis-server"):
        self.redis_server_path = redis_server_path
        self.process = None
        self.port = 6379
        self.password = "testpassword123"
        
    def start(self, config_file=None):
        """启动 Redis 实例"""
        cmd = [self.redis_server_path, "--port", str(self.port)]
        
        if config_file and os.path.exists(config_file):
            cmd = [self.redis_server_path, config_file]
        else:
            # 基础配置
            cmd.extend([
                "--requirepass", self.password,
                "--maxmemory", "256mb",
                "--maxmemory-policy", "allkeys-lru",
                "--appendonly", "yes",
                "--dir", "/tmp/redis-test"
            ])
            
        os.makedirs("/tmp/redis-test", exist_ok=True)
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 等待启动
        time.sleep(1)
        
        # 验证连接
        client = self.get_client()
        try:
            client.ping()
        except redis.ConnectionError:
            self.stop()
            raise RuntimeError("Redis server failed to start")
            
        return self
    
    def stop(self):
        """停止 Redis 实例"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            
    def get_client(self, db=0):
        """获取 Redis 客户端"""
        return redis.Redis(
            host="localhost",
            port=self.port,
            password=self.password,
            db=db,
            decode_responses=True,
            socket_connect_timeout=5
        )


@pytest.fixture(scope="session")
def redis_server():
    """Session 级别的 Redis 服务器"""
    server = RedisServer().start()
    yield server
    server.stop()


@pytest.fixture
def redis_client(redis_server):
    """每个测试用例的 Redis 客户端"""
    client = redis_server.get_client()
    client.flushall()
    yield client
