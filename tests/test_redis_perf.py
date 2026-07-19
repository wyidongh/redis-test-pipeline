import pytest
import time
import concurrent.futures


class TestRedisPerformance:
    """Redis 性能测试"""
    
    def test_set_throughput(self, redis_client):
        """测试 SET 吞吐量"""
        count = 10000
        start = time.time()
        
        for i in range(count):
            redis_client.set(f"perf_key_{i}", f"value_{i}")
            
        duration = time.time() - start
        tps = count / duration
        
        print(f"\nSET TPS: {tps:.2f} ops/sec")
        assert tps > 5000, f"SET TPS too low: {tps}"
        
    def test_get_throughput(self, redis_client):
        """测试 GET 吞吐量"""
        # 预填充数据
        for i in range(10000):
            redis_client.set(f"perf_key_{i}", f"value_{i}")
            
        count = 10000
        start = time.time()
        
        for i in range(count):
            redis_client.get(f"perf_key_{i}")
            
        duration = time.time() - start
        tps = count / duration
        
        print(f"\nGET TPS: {tps:.2f} ops/sec")
        assert tps > 8000, f"GET TPS too low: {tps}"
        
    def test_concurrent_operations(self, redis_client):
        """测试并发操作"""
        def worker(thread_id, ops_count):
            client = redis_client  # 复用连接
            for i in range(ops_count):
                key = f"thread_{thread_id}_key_{i}"
                client.set(key, f"value_{i}")
                client.get(key)
            return thread_id
            
        threads = 10
        ops_per_thread = 1000
        
        start = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
            futures = [executor.submit(worker, i, ops_per_thread) for i in range(threads)]
            concurrent.futures.wait(futures)
            
        duration = time.time() - start
        total_ops = threads * ops_per_thread * 2  # set + get
        tps = total_ops / duration
        
        print(f"\nConcurrent TPS: {tps:.2f} ops/sec")
        assert tps > 10000, f"Concurrent TPS too low: {tps}"
        
    def test_large_value(self, redis_client):
        """测试大值操作"""
        large_value = "x" * (1024 * 1024)  # 1MB
        
        start = time.time()
        redis_client.set("large_key", large_value)
        duration = time.time() - start
        
        print(f"\nLarge value SET time: {duration:.3f}s")
        assert duration < 1.0, f"Large value SET too slow: {duration}s"
        
        # 验证读取
        result = redis_client.get("large_key")
        assert len(result) == len(large_value)
