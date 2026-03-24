"""
DeerFlow 负载测试脚本

功能:
- 模拟多用户并发请求
- 测试系统吞吐量和响应时间
- 生成性能报告

依赖:
    pip install locust faker

使用方法:
    # Web UI 模式
    locust -f scripts/load_test.py --host=http://localhost:2026
    
    # 命令行模式
    locust -f scripts/load_test.py --host=http://localhost:2026 \\
        --users 1000 --spawn-rate 10 --run-time 10m --headless

参数说明:
    --users: 模拟用户数 (例如: 1000)
    --spawn-rate: 每秒启动用户数 (例如: 10)
    --run-time: 测试运行时间 (例如: 10m)
    --headless: 无 Web UI 模式
"""

import random
import time
import uuid
from typing import Any

from faker import Faker
from locust import HttpUser, TaskSet, between, task

fake = Faker("zh_CN")


class ChatBehavior(TaskSet):
    """用户聊天行为模拟"""

    def on_start(self):
        """每个用户启动时执行"""
        # 创建新的会话
        self.thread_id = str(uuid.uuid4())
        self.message_count = 0
        self.session_start = time.time()
        
        print(f"[User] Started session: {self.thread_id}")

    @task(10)
    def send_simple_message(self):
        """发送简单消息 (权重 10)"""
        messages = [
            "你好",
            "帮我写一个 Python 函数",
            "今天天气怎么样?",
            "给我讲个笑话",
            "1+1等于几?",
            f"我的名字是{fake.name()}",
            "解释一下什么是AI",
            "推荐几本好书",
        ]
        
        message = random.choice(messages)
        self._send_message(message)

    @task(5)
    def send_complex_message(self):
        """发送复杂消息 (权重 5)"""
        messages = [
            "帮我分析一下这段代码的性能瓶颈:\n```python\ndef slow_func():\n    result = []\n    for i in range(10000):\n        result.append(i ** 2)\n    return result\n```",
            "写一个完整的 FastAPI 应用,包含用户认证、数据库操作和 CRUD 接口",
            "设计一个秒杀系统的架构方案,要考虑高并发和超卖问题",
            "用 React 和 TypeScript 实现一个待办事项应用",
        ]
        
        message = random.choice(messages)
        self._send_message(message)

    @task(2)
    def send_code_execution_request(self):
        """请求代码执行 (权重 2)"""
        messages = [
            "用 Python 生成一个随机密码",
            "帮我下载 https://example.com 的内容",
            "运行这段代码: print('Hello, World!')",
            "读取当前目录下的所有文件",
        ]
        
        message = random.choice(messages)
        self._send_message(message)

    @task(1)
    def list_threads(self):
        """获取会话列表 (权重 1)"""
        with self.client.get(
            "/threads",
            name="/threads [List]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    @task(1)
    def get_thread_history(self):
        """获取会话历史 (权重 1)"""
        with self.client.get(
            f"/threads/{self.thread_id}/history",
            name="/threads/{id}/history [Get]",
            catch_response=True,
        ) as response:
            if response.status_code in (200, 404):  # 404 是正常的 (新会话)
                response.success()
            else:
                response.failure(f"Status: {response.status_code}")

    def _send_message(self, message: str):
        """发送消息到 LangGraph API"""
        self.message_count += 1
        
        payload = {
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": message,
                    }
                ]
            },
            "config": {
                "configurable": {
                    "thread_id": self.thread_id,
                }
            },
        }
        
        with self.client.post(
            f"/threads/{self.thread_id}/runs/stream",
            json=payload,
            name="/threads/{id}/runs/stream [POST]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
                print(f"[User {self.thread_id[:8]}] Message {self.message_count}: OK")
            else:
                response.failure(f"Status: {response.status_code}")
                print(f"[User {self.thread_id[:8]}] Message {self.message_count}: FAILED")

    def on_stop(self):
        """用户停止时执行"""
        duration = time.time() - self.session_start
        print(f"[User] Session ended: {self.thread_id[:8]}, Duration: {duration:.2f}s, Messages: {self.message_count}")


class WebsiteUser(HttpUser):
    """模拟用户类"""
    
    tasks = [ChatBehavior]
    
    # 用户等待时间 (秒)
    wait_time = between(1, 5)  # 1-5秒
    
    # 权重 (可以定义多个用户类型)
    weight = 1
    
    def on_start(self):
        """所有用户启动时执行一次"""
        print(f"[System] User spawned")


class HeavyUser(HttpUser):
    """重度用户 (发送消息更频繁)"""
    
    tasks = [ChatBehavior]
    wait_time = between(0.5, 2)  # 0.5-2秒
    weight = 1  # 与普通用户 1:1


# 自定义性能监控
class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.response_times = []
        self.errors = []
    
    def record_response(self, response_time: float, success: bool):
        """记录响应"""
        self.response_times.append(response_time)
        if not success:
            self.errors.append(response_time)
    
    def get_stats(self) -> dict[str, Any]:
        """获取统计数据"""
        if not self.response_times:
            return {}
        
        sorted_times = sorted(self.response_times)
        count = len(sorted_times)
        
        return {
            "total_requests": count,
            "errors": len(self.errors),
            "error_rate": len(self.errors) / count if count > 0 else 0,
            "avg_response_time": sum(sorted_times) / count,
            "min_response_time": sorted_times[0],
            "max_response_time": sorted_times[-1],
            "p50_response_time": sorted_times[int(count * 0.5)],
            "p95_response_time": sorted_times[int(count * 0.95)],
            "p99_response_time": sorted_times[int(count * 0.99)],
        }


# Locust Web UI 事件监听
from locust import events


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时"""
    print("\n" + "=" * 60)
    print("DeerFlow 负载测试开始")
    print("=" * 60)
    print(f"目标主机: {environment.host}")
    print()


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时"""
    print("\n" + "=" * 60)
    print("DeerFlow 负载测试完成")
    print("=" * 60)
    
    # 打印统计摘要
    stats = environment.stats
    print(f"\n总请求数: {stats.total.num_requests}")
    print(f"失败数: {stats.total.num_failures}")
    print(f"失败率: {stats.total.fail_ratio * 100:.2f}%")
    print(f"\n平均响应时间: {stats.total.avg_response_time:.2f}ms")
    print(f"中位数响应时间: {stats.total.median_response_time:.2f}ms")
    print(f"95%响应时间: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"99%响应时间: {stats.total.get_response_time_percentile(0.99):.2f}ms")
    print(f"\nRPS: {stats.total.total_rps:.2f}")
    print()


if __name__ == "__main__":
    print("""
使用方法:
    1. 启动 Web UI:
       locust -f scripts/load_test.py --host=http://localhost:2026
       
    2. 命令行模式:
       locust -f scripts/load_test.py --host=http://localhost:2026 \\
           --users 100 --spawn-rate 10 --run-time 5m --headless
       
    3. 模拟 1万用户:
       locust -f scripts/load_test.py --host=http://localhost:2026 \\
           --users 10000 --spawn-rate 100 --run-time 30m --headless

访问 http://localhost:8089 查看 Web UI
""")
