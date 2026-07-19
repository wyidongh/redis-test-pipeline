import pytest
import redis
import os
import time
import subprocess


class RedisServer:
    """管理 Redis 服务器生命周期"""
    
    def __init__(self, redis_server_path=None):
        # 从环境变量读取，或使用默认值
        self.redis_server_path = redis_server_path or os.environ.get(
            "REDIS_SERVER_PATH", 
            "/usr/local/bin/redis-server"
        )
        self.process = None
        self.port = 6379
        self.password = "testpassword123"
        self._client = None
        
    def start(self):
        """启动 Redis 实例"""
        if self.process is not None:
            return self
            
        # 验证二进制文件存在
        if not os.path.exists(self.redis_server_path):
            # 尝试找其他可能的位置
            alt_paths = [
                "/usr/local/redis/bin/redis-server",
                "/usr/bin/redis-server",
                "redis-server"
            ]
            for path in alt_paths:
                if os.path.exists(path):
                    self.redis_server_path = path
                    break
            else:
                raise RuntimeError(
                    f"Redis server not found. Tried: {self.redis_server_path}, {alt_paths}. "
                    f"Please set REDIS_SERVER_PATH environment variable."
                )
            
        cmd = [
            self.redis_server_path,
            "--port", str(self.port),
            "--requirepass", self.password,
            "--maxmemory", "256mb",
            "--maxmemory-policy", "allkeys-lru",
            "--appendonly", "yes",
            "--dir", "/tmp/redis-test",
            "--daemonize", "no",
            "--loglevel", "warning"
        ]
        
        os.makedirs("/tmp/redis-test", exist_ok=True)
        
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 等待启动
        time.sleep(2)
        
        # 验证进程还在运行
        if self.process.poll() is not None:
            stdout, stderr = self.process.communicate()
            raise RuntimeError(
                f"Redis server exited early. stdout: {stdout.decode()}, stderr: {stderr.decode()}"
            )
        
        # 验证连接
        try:
            client = self.get_client()
            client.ping()
        except Exception as e:
            self.stop()
            raise RuntimeError(f"Redis server failed to respond: {e}")
            
        return self
    
    def stop(self):
        """停止 Redis 实例"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.process = None
            self._client = None
            
    def get_client(self, db=0):
        """获取 Redis 客户端"""
        return redis.Redis(
            host="localhost",
            port=self.port,
            password=self.password,
            db=db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_connect_retry=3
        )


@pytest.fixture(scope="session")
def redis_server():
    """Session 级别的 Redis 服务器"""
    server = RedisServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def redis_client(redis_server):
    """每个测试用例的 Redis 客户端"""
    client = redis_server.get_client()
    client.flushall()
    yield client
