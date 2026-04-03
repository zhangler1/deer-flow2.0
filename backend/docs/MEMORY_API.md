# 记忆系统外部接口调用指南

本文档提供调用 DeerFlow 记忆系统的完整接口示例和代码模板。

---

## 目录

1. [快速开始](#快速开始)
2. [Python SDK 接口](#python-sdk-接口)
3. [REST API 接口](#rest-api-接口)
4. [集成示例](#集成示例)
5. [常见场景](#常见场景)

---

## 快速开始

### 安装依赖

```bash
cd backend
uv sync
```

### 基础示例

```python
from src.agents.memory import get_memory_data, update_memory_from_conversation
from langchain_core.messages import HumanMessage, AIMessage

# 1. 获取当前记忆
memory = get_memory_data()
print(f"当前有 {len(memory['facts'])} 条事实")
print(f"工作背景: {memory['user']['workContext']['summary']}")

# 2. 更新记忆
messages = [
    HumanMessage(content="我正在学习 LangGraph"),
    AIMessage(content="很好！LangGraph 是构建 AI Agent 的强大框架...")
]

success = update_memory_from_conversation(messages, thread_id="thread_001")
if success:
    print("记忆更新成功！")
```

---

## Python SDK 接口

### 1. 读取记忆

#### 1.1 获取全局记忆

```python
from src.agents.memory import get_memory_data

# 获取全局记忆（带缓存）
memory = get_memory_data()

# 访问各个部分
user_context = memory.get("user", {})
work = user_context.get("workContext", {}).get("summary", "")
personal = user_context.get("personalContext", {}).get("summary", "")
top_of_mind = user_context.get("topOfMind", {}).get("summary", "")

history = memory.get("history", {})
recent = history.get("recentMonths", {}).get("summary", "")

facts = memory.get("facts", [])
print(f"共有 {len(facts)} 条事实")
for fact in facts[:5]:  # 打印前5条
    print(f"- [{fact['category']}] {fact['content']} (置信度: {fact['confidence']})")
```

#### 1.2 获取特定 Agent 的记忆

```python
# 获取特定 agent 的记忆
agent_memory = get_memory_data(agent_name="code_assistant")

# Per-agent 记忆独立存储在：
# {base_dir}/.deer-flow/memory/{agent_name}.json
```

#### 1.3 强制刷新缓存

```python
from src.agents.memory import reload_memory_data

# 如果记忆文件被外部修改，需要刷新缓存
fresh_memory = reload_memory_data()

# 或刷新特定 agent 的记忆
fresh_agent_memory = reload_memory_data(agent_name="code_assistant")
```

### 2. 更新记忆

#### 2.1 从对话更新

```python
from src.agents.memory import update_memory_from_conversation
from langchain_core.messages import HumanMessage, AIMessage

# 准备对话消息
messages = [
    HumanMessage(content="我喜欢用 pytest 写测试"),
    AIMessage(content="pytest 确实是很好的选择！它有很多优点..."),
    HumanMessage(content="我的项目主要用 FastAPI"),
    AIMessage(content="FastAPI 和 pytest 配合很好...")
]

# 更新记忆（同步调用 LLM）
success = update_memory_from_conversation(
    messages=messages,
    thread_id="thread_abc123",  # 可选：标识对话来源
    agent_name=None  # 可选：None=全局记忆，或指定 agent 名称
)

if success:
    print("✓ 记忆更新成功")
    # LLM 可能提取的事实：
    # - "偏好使用 pytest 进行测试" (category: preference)
    # - "项目使用 FastAPI 框架" (category: context)
else:
    print("✗ 记忆更新失败")
```

#### 2.2 使用队列异步更新（推荐）

```python
from src.agents.memory import get_memory_queue

queue = get_memory_queue()

# 添加到队列（异步处理，默认 30 秒防抖）
queue.add(
    thread_id="thread_123",
    messages=[...],
    agent_name=None
)

# 查看队列状态
print(f"队列中待处理: {queue.pending_count}")
print(f"正在处理中: {queue.is_processing}")

# 如果需要立即处理（跳过防抖）
queue.flush()
```

### 3. 格式化记忆用于注入

```python
from src.agents.memory import format_memory_for_injection, get_memory_data

memory = get_memory_data()

# 基础格式化（最多 2000 tokens）
memory_text = format_memory_for_injection(memory, max_tokens=2000)

print(memory_text)
# 输出示例：
# User Context:
# - Work: 核心贡献者，主要项目 DeerFlow...
# - Personal: 双语能力（中文/英文）...
# - Current Focus: 正在优化记忆系统...
# 
# History:
# - Recent: 过去3个月主要工作：实现了文件上传功能...
# - Earlier: 3-12个月前的活动：建立了项目的基础架构...

# 在系统提示词中使用
system_prompt = f"""你是一个智能助手。

<memory>
{memory_text}
</memory>

请根据用户的背景和偏好提供个性化的回复。"""
```

### 4. 高级：手动构建记忆数据

```python
import json
from datetime import datetime
from pathlib import Path
from src.config.paths import get_paths
from src.agents.memory import reload_memory_data

# 1. 手动构建记忆数据结构
custom_memory = {
    "version": "1.0",
    "lastUpdated": datetime.utcnow().isoformat() + "Z",
    "user": {
        "workContext": {
            "summary": "后端工程师，专注于 Python 和 AI 开发",
            "updatedAt": datetime.utcnow().isoformat() + "Z"
        },
        "personalContext": {
            "summary": "偏好简洁的代码风格，喜欢函数式编程",
            "updatedAt": datetime.utcnow().isoformat() + "Z"
        },
        "topOfMind": {
            "summary": "正在学习 LangGraph 和 Agent 开发",
            "updatedAt": datetime.utcnow().isoformat() + "Z"
        }
    },
    "history": {
        "recentMonths": {
            "summary": "最近在研究 AI Agent 框架，尝试了多个项目",
            "updatedAt": datetime.utcnow().isoformat() + "Z"
        },
        "earlierContext": {
            "summary": "",
            "updatedAt": ""
        },
        "longTermBackground": {
            "summary": "有5年 Python 开发经验",
            "updatedAt": datetime.utcnow().isoformat() + "Z"
        }
    },
    "facts": [
        {
            "id": "fact_custom01",
            "content": "偏好使用 pytest 进行单元测试",
            "category": "preference",
            "confidence": 0.95,
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "source": "manual_import"
        },
        {
            "id": "fact_custom02",
            "content": "精通 FastAPI 和 Django 框架",
            "category": "knowledge",
            "confidence": 0.9,
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "source": "manual_import"
        }
    ]
}

# 2. 保存到文件
memory_file = get_paths().memory_file
memory_file.parent.mkdir(parents=True, exist_ok=True)

with open(memory_file, "w", encoding="utf-8") as f:
    json.dump(custom_memory, f, indent=2, ensure_ascii=False)

print(f"✓ 记忆已保存到: {memory_file}")

# 3. 刷新缓存
reload_memory_data()
print("✓ 缓存已刷新")
```

### 5. 配置管理

```python
from src.config.memory_config import (
    get_memory_config,
    set_memory_config,
    load_memory_config_from_dict,
    MemoryConfig
)

# 获取当前配置
config = get_memory_config()
print(f"记忆功能已启用: {config.enabled}")
print(f"最大 facts 数量: {config.max_facts}")
print(f"防抖时间: {config.debounce_seconds} 秒")
print(f"置信度阈值: {config.fact_confidence_threshold}")

# 修改配置（方法1：创建新配置对象）
new_config = MemoryConfig(
    enabled=True,
    debounce_seconds=60,  # 改为 60 秒
    max_facts=200,  # 增加到 200 条
    fact_confidence_threshold=0.8,  # 提高阈值
    max_injection_tokens=3000  # 增加注入 token 数
)
set_memory_config(new_config)

# 修改配置（方法2：从字典加载）
load_memory_config_from_dict({
    "enabled": True,
    "debounce_seconds": 45,
    "max_facts": 150
})
```

---

## REST API 接口

### 前提条件

需要确认项目是否已实现 HTTP API 端点。以下是**建议的 API 设计**，实际可用性需要检查代码实现。

### 1. 获取记忆

```bash
# 获取全局记忆
curl -X GET http://localhost:8000/api/memory

# 获取特定 agent 的记忆
curl -X GET http://localhost:8000/api/memory/code_assistant
```

**响应示例**：

```json
{
  "version": "1.0",
  "lastUpdated": "2026-04-03T10:30:00.000Z",
  "user": {
    "workContext": {
      "summary": "...",
      "updatedAt": "..."
    },
    "personalContext": {...},
    "topOfMind": {...}
  },
  "history": {...},
  "facts": [...]
}
```

### 2. 更新记忆

```bash
curl -X POST http://localhost:8000/api/memory/update \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread_123",
    "messages": [
      {"type": "human", "content": "我正在学习 LangGraph"},
      {"type": "ai", "content": "很好！LangGraph 是..."}
    ],
    "agent_name": null
  }'
```

**响应**：

```json
{
  "success": true,
  "message": "Memory update queued"
}
```

### 3. 立即处理队列

```bash
curl -X POST http://localhost:8000/api/memory/flush
```

### 4. 清空记忆

```bash
# 清空全局记忆
curl -X DELETE http://localhost:8000/api/memory

# 清空特定 agent 的记忆
curl -X DELETE http://localhost:8000/api/memory/code_assistant
```

### 5. 获取记忆统计

```bash
curl -X GET http://localhost:8000/api/memory/stats
```

**响应**：

```json
{
  "total_facts": 47,
  "facts_by_category": {
    "preference": 12,
    "knowledge": 18,
    "context": 10,
    "behavior": 5,
    "goal": 2
  },
  "average_confidence": 0.87,
  "last_updated": "2026-04-03T10:30:00.000Z",
  "queue_pending": 2
}
```

---

## 集成示例

### 示例 1：外部 CRM 系统同步

```python
"""
场景：从外部 CRM 系统导入用户画像到记忆系统
"""

import requests
import json
from datetime import datetime
from src.agents.memory import reload_memory_data
from src.config.paths import get_paths

def import_user_profile_from_crm(user_id: str):
    # 1. 从 CRM 获取用户数据
    crm_response = requests.get(
        f"https://crm.example.com/api/users/{user_id}",
        headers={"Authorization": "Bearer YOUR_API_KEY"}
    )
    user_data = crm_response.json()
    
    # 2. 转换为记忆格式
    memory = {
        "version": "1.0",
        "lastUpdated": datetime.utcnow().isoformat() + "Z",
        "user": {
            "workContext": {
                "summary": f"{user_data['job_title']} at {user_data['company']}, "
                          f"主要项目: {', '.join(user_data['projects'])}",
                "updatedAt": datetime.utcnow().isoformat() + "Z"
            },
            "personalContext": {
                "summary": f"语言: {', '.join(user_data['languages'])}, "
                          f"兴趣: {', '.join(user_data['interests'])}",
                "updatedAt": datetime.utcnow().isoformat() + "Z"
            },
            "topOfMind": {
                "summary": user_data.get('current_focus', ''),
                "updatedAt": datetime.utcnow().isoformat() + "Z"
            }
        },
        "history": {
            "recentMonths": {"summary": "", "updatedAt": ""},
            "earlierContext": {"summary": "", "updatedAt": ""},
            "longTermBackground": {
                "summary": user_data.get('background', ''),
                "updatedAt": datetime.utcnow().isoformat() + "Z"
            }
        },
        "facts": []
    }
    
    # 3. 添加技能作为 facts
    for skill in user_data.get('skills', []):
        memory["facts"].append({
            "id": f"fact_skill_{skill['id']}",
            "content": f"掌握 {skill['name']} ({skill['level']} level)",
            "category": "knowledge",
            "confidence": 0.95,
            "createdAt": datetime.utcnow().isoformat() + "Z",
            "source": "crm_import"
        })
    
    # 4. 保存到记忆文件
    memory_file = get_paths().memory_file
    with open(memory_file, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)
    
    # 5. 刷新缓存
    reload_memory_data()
    
    print(f"✓ 用户 {user_id} 的画像已导入记忆系统")

# 使用示例
import_user_profile_from_crm("user_12345")
```

### 示例 2：定期导出记忆到数据仓库

```python
"""
场景：每天定时导出记忆数据到数据仓库进行分析
"""

import schedule
import time
from src.agents.memory import get_memory_data
import requests

def export_memory_to_warehouse():
    # 1. 获取当前记忆
    memory = get_memory_data()
    
    # 2. 准备分析数据
    analytics_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "user_profile": {
            "work_context": memory["user"]["workContext"]["summary"],
            "personal_context": memory["user"]["personalContext"]["summary"],
            "top_of_mind": memory["user"]["topOfMind"]["summary"]
        },
        "facts_summary": {
            "total": len(memory["facts"]),
            "by_category": {},
            "avg_confidence": 0
        },
        "facts_detail": memory["facts"]
    }
    
    # 统计 facts
    for fact in memory["facts"]:
        category = fact["category"]
        analytics_data["facts_summary"]["by_category"][category] = \
            analytics_data["facts_summary"]["by_category"].get(category, 0) + 1
        analytics_data["facts_summary"]["avg_confidence"] += fact["confidence"]
    
    if memory["facts"]:
        analytics_data["facts_summary"]["avg_confidence"] /= len(memory["facts"])
    
    # 3. 发送到数据仓库
    response = requests.post(
        "https://warehouse.example.com/api/memory_snapshots",
        json=analytics_data,
        headers={"Authorization": "Bearer YOUR_DW_TOKEN"}
    )
    
    if response.status_code == 200:
        print(f"✓ 记忆数据已导出到数据仓库 (facts: {len(memory['facts'])})")
    else:
        print(f"✗ 导出失败: {response.text}")

# 定时任务：每天凌晨 2 点执行
schedule.every().day.at("02:00").do(export_memory_to_warehouse)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 示例 3：与 Slack 集成

```python
"""
场景：用户通过 Slack 命令查看和管理记忆
"""

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from src.agents.memory import get_memory_data, update_memory_from_conversation
from langchain_core.messages import HumanMessage, AIMessage

slack_client = WebClient(token="YOUR_SLACK_BOT_TOKEN")

def handle_memory_command(channel_id: str, command: str, user_id: str):
    if command == "show":
        # 显示当前记忆摘要
        memory = get_memory_data()
        
        facts_count = len(memory["facts"])
        work = memory["user"]["workContext"]["summary"]
        top_of_mind = memory["user"]["topOfMind"]["summary"]
        
        message = f"""📚 *你的记忆摘要*
        
*工作背景*: {work}

*当前关注*: {top_of_mind}

*事实数量*: {facts_count} 条

使用 `/memory facts` 查看详细事实列表
"""
        
        slack_client.chat_postMessage(channel=channel_id, text=message)
    
    elif command == "facts":
        # 显示 facts 列表
        memory = get_memory_data()
        
        facts_text = "*你的知识库 (Top 10)*:\n\n"
        for i, fact in enumerate(memory["facts"][:10], 1):
            emoji = {
                "preference": "⭐",
                "knowledge": "🧠",
                "context": "📋",
                "behavior": "🎯",
                "goal": "🚀"
            }.get(fact["category"], "•")
            
            facts_text += f"{i}. {emoji} {fact['content']} "
            facts_text += f"_(置信度: {fact['confidence']:.0%})_\n"
        
        slack_client.chat_postMessage(channel=channel_id, text=facts_text)
    
    elif command.startswith("learn "):
        # 手动添加知识
        content = command[6:]  # 去掉 "learn "
        
        messages = [
            HumanMessage(content=content),
            AIMessage(content="我记住了！")
        ]
        
        success = update_memory_from_conversation(messages, thread_id=f"slack_{user_id}")
        
        if success:
            slack_client.chat_postMessage(
                channel=channel_id,
                text=f"✓ 已学习: {content}"
            )
        else:
            slack_client.chat_postMessage(
                channel=channel_id,
                text="✗ 学习失败，请稍后重试"
            )

# Slack 事件处理器
@slack_app.command("/memory")
def memory_command(ack, command, respond):
    ack()
    handle_memory_command(
        channel_id=command["channel_id"],
        command=command["text"],
        user_id=command["user_id"]
    )
```

---

## 常见场景

### 场景 1：个性化推荐

```python
from src.agents.memory import get_memory_data

def get_personalized_recommendations(user_query: str):
    memory = get_memory_data()
    
    # 提取用户偏好
    preferences = [
        fact["content"] 
        for fact in memory["facts"] 
        if fact["category"] == "preference" and fact["confidence"] > 0.8
    ]
    
    # 提取用户知识领域
    knowledge_areas = [
        fact["content"]
        for fact in memory["facts"]
        if fact["category"] == "knowledge"
    ]
    
    # 构建个性化提示词
    context = f"""
用户偏好:
{chr(10).join(f"- {p}" for p in preferences)}

用户知识领域:
{chr(10).join(f"- {k}" for k in knowledge_areas)}

当前关注: {memory["user"]["topOfMind"]["summary"]}
"""
    
    # 调用 LLM 生成推荐
    # ... (使用 context 增强推荐质量)
    
    return recommendations
```

### 场景 2：对话上下文保持

```python
from src.agents.memory import format_memory_for_injection, get_memory_data
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

def chat_with_memory(user_message: str):
    # 1. 获取并格式化记忆
    memory = get_memory_data()
    memory_text = format_memory_for_injection(memory, max_tokens=1500)
    
    # 2. 构建带记忆的系统提示词
    system_prompt = f"""你是一个智能助手，了解用户的背景和偏好。

<memory>
{memory_text}
</memory>

请基于用户的记忆提供个性化、有针对性的回复。"""
    
    # 3. 调用 LLM
    llm = ChatOpenAI(model="gpt-4")
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}")
    ])
    
    chain = prompt | llm
    response = chain.invoke({"input": user_message})
    
    return response.content

# 使用示例
response = chat_with_memory("我该如何写测试？")
# LLM 会基于记忆中 "偏好使用 pytest" 来回答
```

### 场景 3：批量导入历史对话

```python
from src.agents.memory import get_memory_queue
from langchain_core.messages import HumanMessage, AIMessage

def import_historical_conversations(conversations: list):
    """
    批量导入历史对话到记忆系统
    
    Args:
        conversations: 列表，每个元素是 (thread_id, messages) 元组
    """
    queue = get_memory_queue()
    
    for thread_id, messages in conversations:
        # 转换为 LangChain 消息格式
        lc_messages = []
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))
        
        # 添加到队列
        queue.add(thread_id=thread_id, messages=lc_messages)
        print(f"✓ 已导入对话 {thread_id}")
    
    print(f"\n共导入 {len(conversations)} 个对话，等待处理...")
    
    # 立即处理（可选）
    # queue.flush()

# 使用示例
historical_data = [
    ("thread_001", [
        {"role": "user", "content": "我是一名 Python 开发者"},
        {"role": "assistant", "content": "很高兴认识你！..."}
    ]),
    ("thread_002", [
        {"role": "user", "content": "我在研究 LangGraph"},
        {"role": "assistant", "content": "LangGraph 很强大..."}
    ])
]

import_historical_conversations(historical_data)
```

### 场景 4：记忆质量监控

```python
from src.agents.memory import get_memory_data
import json

def analyze_memory_quality():
    """分析记忆数据的质量指标"""
    
    memory = get_memory_data()
    facts = memory.get("facts", [])
    
    # 统计信息
    total_facts = len(facts)
    
    if total_facts == 0:
        print("记忆中没有事实数据")
        return
    
    # 按类别统计
    by_category = {}
    for fact in facts:
        cat = fact.get("category", "unknown")
        by_category[cat] = by_category.get(cat, 0) + 1
    
    # 置信度分布
    confidence_levels = {
        "high (>=0.9)": 0,
        "medium (0.7-0.9)": 0,
        "low (<0.7)": 0
    }
    
    total_confidence = 0
    for fact in facts:
        conf = fact.get("confidence", 0)
        total_confidence += conf
        
        if conf >= 0.9:
            confidence_levels["high (>=0.9)"] += 1
        elif conf >= 0.7:
            confidence_levels["medium (0.7-0.9)"] += 1
        else:
            confidence_levels["low (<0.7)"] += 1
    
    avg_confidence = total_confidence / total_facts
    
    # 生成报告
    report = f"""
📊 *记忆质量分析报告*

总事实数: {total_facts}
平均置信度: {avg_confidence:.2%}

**按类别分布**:
{json.dumps(by_category, indent=2, ensure_ascii=False)}

**置信度分布**:
{json.dumps(confidence_levels, indent=2)}

**用户上下文完整性**:
- 工作背景: {'✓' if memory['user']['workContext']['summary'] else '✗'}
- 个人背景: {'✓' if memory['user']['personalContext']['summary'] else '✗'}
- 当前关注: {'✓' if memory['user']['topOfMind']['summary'] else '✗'}

**历史上下文完整性**:
- 最近活动: {'✓' if memory['history']['recentMonths']['summary'] else '✗'}
- 早期活动: {'✓' if memory['history']['earlierContext']['summary'] else '✗'}
- 长期背景: {'✓' if memory['history']['longTermBackground']['summary'] else '✗'}
"""
    
    print(report)
    
    # 检查低质量 facts
    low_quality = [f for f in facts if f.get("confidence", 0) < 0.7]
    if low_quality:
        print(f"\n⚠️  发现 {len(low_quality)} 条低置信度事实，建议审查：")
        for fact in low_quality[:5]:
            print(f"  - {fact['content']} (置信度: {fact['confidence']:.0%})")

# 使用示例
analyze_memory_quality()
```

---

## 注意事项

### 1. 并发安全

当前实现使用文件存储，**不支持多进程并发写入**。如果多个实例同时更新记忆，可能导致数据丢失。

**解决方案**：
- 单实例部署
- 使用文件锁（`fcntl.flock` on Linux）
- 迁移到数据库存储（PostgreSQL、Redis 等）

### 2. 隐私和安全

记忆系统会自动记录对话内容，注意：
- ❌ 不要在对话中透露敏感信息（密码、API Key等）
- ✅ 定期审查 `memory.json` 文件内容
- ✅ 在生产环境中加密存储
- ✅ 实施访问控制（如果是多租户系统）

### 3. 性能考虑

- 记忆更新会调用 LLM，有延迟和成本
- 调整 `debounce_seconds` 平衡实时性和调用频率
- 大量 facts (>500) 会影响注入性能
- 考虑使用向量数据库进行语义检索

### 4. Token 消耗

- 记忆注入会占用上下文窗口
- 默认最多 2000 tokens
- 根据模型窗口大小调整 `max_injection_tokens`
- 监控实际消耗，优化记忆内容

---

## 相关文档

- [MEMORY_SYSTEM.md](./MEMORY_SYSTEM.md) - 记忆系统完整文档
- [MEMORY_IMPROVEMENTS.md](./MEMORY_IMPROVEMENTS.md) - 技术改进详情
- [CONFIGURATION.md](./CONFIGURATION.md) - 配置指南

---

**最后更新**：2026-04-03
