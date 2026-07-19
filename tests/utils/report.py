import json
import os
from datetime import datetime


class TestReport:
    """生成测试报告"""
    
    def __init__(self, output_dir="/tmp/test-reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def generate_summary(self, test_results):
        """生成测试摘要"""
        summary = {
            "test_time": datetime.now().isoformat(),
            "total": test_results.get("total", 0),
            "passed": test_results.get("passed", 0),
            "failed": test_results.get("failed", 0),
            "skipped": test_results.get("skipped", 0),
            "duration": test_results.get("duration", 0),
            "redis_version": test_results.get("redis_version", "unknown"),
            "build_version": test_results.get("build_version", "unknown")
        }
        
        summary_file = os.path.join(self.output_dir, "test-summary.json")
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
            
        return summary_file
        
    def generate_html_report(self, pytest_html_path):
        """生成 HTML 报告（基于 pytest-html 输出）"""
        if os.path.exists(pytest_html_path):
            # 可以在这里添加自定义样式或内容
            return pytest_html_path
        return None
