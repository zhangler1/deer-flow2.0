# 记忆系统详细文档

## 目录

1. [系统概述](#系统概述)
2. [记忆存储结构](#记忆存储结构)
3. [记忆更新流程](#记忆更新流程)
4. [记忆注入机制](#记忆注入机制)
5. [外部接口调用](#外部接口调用)
6. [配置选项](#配置选项)
7. [API 参考](#api-参考)
8. [最佳实践](#最佳实践)

---

## 系统概述

DeerFlow 的记忆系统是一个全局的长期记忆机制，能够：

- 📝 **自动记录**用户的上下文、偏好和对话历史
- 🧠 **智能提取**关键事实和知识点
- 🎯 **动态注入**相关记忆到系统提示词中
- 🔄 **持续更新**基于新的对话内容

### 核心特性

1. **异步更新**：使用队列和防抖机制，避免频繁更新
2. **智能选择**：基于 TF-IDF 相似度选择相关的记忆片段
3. **精确计算**：使用 tiktoken 进行准确的 token 计数
4. **支持多租户**：可选的 per-agent 记忆隔离

---

## 记忆存储结构

### 文件位置

- **全局记忆**：`{base_dir}/memory.json`（默认）
- **Per-agent 记忆**：`{base_dir}/.deer-flow/memory/{agent_name}.json`

可通过配置自定义存储路径（支持绝对路径和相对路径）。

### JSON 结构

```json
{
  "version": "1.0",
  "lastUpdated": "2026-04-03T10:30:00.000Z",
  
  "user": {
    "workContext": {
      "summary": "核心贡献者，主要项目 DeerFlow (16k+ stars)，技术栈：Python, TypeScript, LangGraph",
      "updatedAt": "2026-04-03T10:30:00.000Z"
    },
    "personalContext": {
      "summary": "双语能力（中文/英文），专注于 AI Agent 开发和工作流自动化",
      "updatedAt": "2026-04-03T10:25:00.000Z"
    },
    "topOfMind": {
      "summary": "正在优化记忆系统的相似度召回算法；调研 LangGraph 的最新特性；探索多模态 Agent 的实现方案",
      "updatedAt": "2026-04-03T10:30:00.000Z"
    }
  },
  
  "history": {
    "recentMonths": {
      "summary": "过去3个月主要工作：实现了文件上传功能、优化了记忆系统的 token 计算、添加了 MCP 服务器支持。探索了多个 LLM 提供商的集成（OpenAI、Anthropic、DeepSeek）。",
      "updatedAt": "2026-04-03T10:20:00.000Z"
    },
    "earlierContext": {
      "summary": "3-12个月前的活动：建立了项目的基础架构、实现了 LangGraph 集成、开发了技能系统。",
      "updatedAt": "2026-03-15T08:00:00.000Z"
    },
    "longTermBackground": {
      "summary": "资深 AI 开发者，多年 Python 和 TypeScript 经验，专注于构建生产级 AI Agent 系统。",
      "updatedAt": "2026-02-01T12:00:00.000Z"
    }
  },
  
  "facts": [
    {
      "id": "fact_a1b2c3d4",
      "content": "偏好使用 pytest 进行 Python 测试",
      "category": "preference",
      "confidence": 0.95,
      "createdAt": "2026-03-20T14:30:00.000Z",
      "source": "thread_abc123"
    },
    {
      "id": "fact_e5f6g7h8",
      "content": "精通 LangGraph 和 LangChain 框架",
      "category": "knowledge",
      "confidence": 0.98,
      "createdAt": "2026-03-22T09:15:00.000Z",
      "source": "thread_def456"
    },
    {
      "id": "fact_i9j0k1l2",
      "content": "目标：构建一个可扩展到 10,000+ 用户的 AI Agent 平台",
      "category": "goal",
      "confidence": 0.92,
      "createdAt": "2026-03-25T16:45:00.000Z",
      "source": "thread_ghi789"
    }
  ]
}
```

### 字段说明

#### 1. User 部分（用户上下文）

| 字段 | 说明 | 长度建议 |
|------|------|----------|
| `workContext` | 工作背景：职位、公司、主要项目、技术栈 | 2-3 句话 |
| `personalContext` | 个人背景：语言能力、沟通偏好、兴趣 | 1-2 句话 |
| `topOfMind` | 当前关注点：**多个**并行进行的任务和兴趣 | 3-5 句话（详细段落） |

#### 2. History 部分（历史上下文）

| 字段 | 说明 | 时间范围 | 长度建议 |
|------|------|----------|----------|
| `recentMonths` | 最近活动的详细总结 | 1-3 个月 | 4-6 句话或 1-2 段 |
| `earlierContext` | 早期活动的模式和要点 | 3-12 个月 | 3-5 句话或 1 段 |
| `longTermBackground` | 长期背景和基础信息 | 持久性信息 | 2-4 句话 |

#### 3. Facts 部分（事实列表）

每个 fact 包含：

- **id**：唯一标识符（`fact_` + 8位随机字符）
- **content**：具体的事实内容（应该详细、可量化）
- **category**：分类
  - `preference`：偏好（工具、风格、方法）
  - `knowledge`：知识和专长
  - `context`：背景信息（职位、项目、位置、语言）
  - `behavior`：行为模式
  - `goal`：目标和愿望
- **confidence**：置信度（0.0 - 1.0）
  - `0.9-1.0`：明确陈述的事实
  - `0.7-0.8`：从行为中强烈暗示
  - `0.5-0.6`：推断的模式（谨慎使用）
- **createdAt**：创建时间戳
- **source**：来源线程 ID

---

## 记忆更新流程

### 1. 触发时机

记忆更新在每次 Agent 执行完成后自动触发（通过 `MemoryMiddleware.after_agent`）。

```python
# src/agents/middlewares/memory_middleware.py

class MemoryMiddleware(AgentMiddleware[MemoryMiddlewareState]):
    def after_agent(self, state: MemoryMiddlewareState, runtime: Runtime) -> dict | None:
        # 1. 检查配置是否启用
        # 2. 获取 thread_id
        # 3. 过滤消息（只保留用户输入和最终回复）
        # 4. 添加到更新队列
        queue = get_memory_queue()
        queue.add(thread_id=thread_id, messages=filtered_messages, agent_name=self._agent_name)
```

### 2. 消息过滤

在添加到队列前，会过滤掉中间步骤：

```python
def _filter_messages_for_memory(messages: list[Any]) -> list[Any]:
    """
    保留：
    - Human 消息（用户输入，去除 <uploaded_files> 标签）
    - AI 消息但无 tool_calls（最终回复）
    
    过滤：
    - Tool 消息（工具调用结果）
    - 带 tool_calls 的 AI 消息（中间步骤）
    - 纯文件上传消息（没有实际用户问题）
    """
```

**为什么要过滤？**

- ✅ 保持记忆内容简洁，只记录有意义的对话
- ✅ 避免记录临时的文件上传路径（会话级别的信息）
- ✅ 减少 token 消耗，提高记忆质量

### 3. 队列和防抖

使用 `MemoryUpdateQueue` 管理更新：

```python
class MemoryUpdateQueue:
    def add(self, thread_id: str, messages: list[Any], agent_name: str | None = None):
        # 1. 检查队列中是否已有同一 thread 的待更新项
        # 2. 如果有，替换为最新的（保证每个 thread 只有一个待处理项）
        # 3. 重置防抖定时器
        
    def _reset_timer(self):
        # 取消现有定时器，启动新的定时器
        # 默认 30 秒后执行批量更新
        
    def _process_queue(self):
        # 1. 复制队列内容并清空队列
        # 2. 依次处理每个对话
        # 3. 调用 MemoryUpdater.update_memory()
```

**防抖机制**：

- 默认 30 秒等待期（可配置）
- 在等待期内新增的更新会重置定时器
- 批量处理多个更新，减少 LLM 调用

### 4. LLM 驱动的更新

```python
class MemoryUpdater:
    def update_memory(self, messages: list[Any], thread_id: str | None, agent_name: str | None):
        # 1. 获取当前记忆数据
        current_memory = get_memory_data(agent_name)
        
        # 2. 格式化对话内容
        conversation_text = format_conversation_for_update(messages)
        
        # 3. 构建提示词
        prompt = MEMORY_UPDATE_PROMPT.format(
            current_memory=json.dumps(current_memory, indent=2),
            conversation=conversation_text
        )
        
        # 4. 调用 LLM 分析
        model = create_chat_model(name=config.model_name)
        response = model.invoke(prompt)
        
        # 5. 解析 JSON 响应
        update_data = json.loads(response_text)
        
        # 6. 应用更新
        updated_memory = self._apply_updates(current_memory, update_data, thread_id)
        
        # 7. 过滤文件上传相关内容
        updated_memory = _strip_upload_mentions_from_memory(updated_memory)
        
        # 8. 保存到文件
        _save_memory_to_file(updated_memory, agent_name)
```

### 5. 应用更新逻辑

```python
def _apply_updates(current_memory, update_data, thread_id):
    # 1. 更新 user 部分（如果 shouldUpdate=true）
    for section in ["workContext", "personalContext", "topOfMind"]:
        if update_data["user"][section]["shouldUpdate"]:
            current_memory["user"][section] = {
                "summary": update_data["user"][section]["summary"],
                "updatedAt": now
            }
    
    # 2. 更新 history 部分
    for section in ["recentMonths", "earlierContext", "longTermBackground"]:
        if update_data["history"][section]["shouldUpdate"]:
            current_memory["history"][section] = {...}
    
    # 3. 删除过时的 facts
    facts_to_remove = update_data.get("factsToRemove", [])
    current_memory["facts"] = [f for f in current_memory["facts"] 
                                if f["id"] not in facts_to_remove]
    
    # 4. 添加新 facts（只保留置信度 >= threshold 的）
    for fact in update_data.get("newFacts", []):
        if fact["confidence"] >= config.fact_confidence_threshold:
            current_memory["facts"].append({
                "id": f"fact_{uuid.uuid4().hex[:8]}",
                "content": fact["content"],
                "category": fact["category"],
                "confidence": fact["confidence"],
                "createdAt": now,
                "source": thread_id
            })
    
    # 5. 限制 facts 数量（保留置信度最高的）
    if len(current_memory["facts"]) > config.max_facts:
        current_memory["facts"] = sorted(
            current_memory["facts"], 
            key=lambda f: f["confidence"], 
            reverse=True
        )[:config.max_facts]
```

### 6. 文件上传内容过滤

```python
def _strip_upload_mentions_from_memory(memory_data):
    """
    移除所有关于文件上传事件的句子和 facts。
    
    原因：上传的文件是会话级别的，路径在未来会话中无效，
    记录上传事件会导致 Agent 尝试访问不存在的文件。
    """
    # 使用正则表达式匹配上传相关的句子
    # 从所有 summary 和 facts 中移除
```

---

## 记忆注入机制

### 注入时机和方式

**早期方案（已废弃）**：使用 `before_model` middleware 动态注入 SystemMessage

**当前方案**：通过 LangGraph 的动态系统提示词函数

虽然文档中提到了 `before_model` 方案，但实际实现可能使用动态系统提示词。

### 相关内容选择（TF-IDF）

```python
def format_memory_for_injection(memory_data: dict, max_tokens: int = 2000) -> str:
    """
    1. 提取所有记忆片段（user context, history）
    2. 格式化为文本
    3. 使用 tiktoken 精确计算 token 数
    4. 如果超出限制，截断并添加 "..."
    """
    sections = []
    
    # User Context
    if user_data:
        sections.append("User Context:\n- Work: ...\n- Personal: ...\n- Current Focus: ...")
    
    # History
    if history_data:
        sections.append("History:\n- Recent: ...\n- Earlier: ...")
    
    result = "\n\n".join(sections)
    
    # 精确的 token 计数
    token_count = _count_tokens(result)  # 使用 tiktoken
    if token_count > max_tokens:
        # 截断到目标长度
        ...
    
    return result
```

**高级特性**（如果启用相似度召回）：

可以传入 `current_context` 参数，使用 TF-IDF 计算相似度，选择最相关的 facts：

```python
# 提取最近 3 轮对话作为上下文
conversation_context = _extract_conversation_context(messages, max_turns=3)

# 使用上下文进行智能选择
memory_content = format_memory_for_injection(
    memory_data,
    max_tokens=2000,
    current_context=conversation_context  # 可选参数
)
```

综合评分公式：
```
final_score = (similarity × 0.6) + (confidence × 0.4)
```

---

## 外部接口调用

### Python API

#### 1. 获取记忆数据

```python
from src.agents.memory import get_memory_data, reload_memory_data

# 获取全局记忆（使用缓存）
memory = get_memory_data()

# 获取特定 agent 的记忆
agent_memory = get_memory_data(agent_name="my_agent")

# 强制重新加载（跳过缓存）
fresh_memory = reload_memory_data()
fresh_agent_memory = reload_memory_data(agent_name="my_agent")
```

#### 2. 手动更新记忆

```python
from src.agents.memory import update_memory_from_conversation

# 从对话消息更新记忆
messages = [
    HumanMessage(content="我正在学习 LangGraph"),
    AIMessage(content="很好！LangGraph 是一个强大的框架...")
]

success = update_memory_from_conversation(
    messages=messages,
    thread_id="thread_abc123",  # 可选
    agent_name=None  # None = 全局记忆
)
```

#### 3. 手动触发记忆格式化

```python
from src.agents.memory import format_memory_for_injection

memory_data = get_memory_data()

# 基础格式化
memory_text = format_memory_for_injection(memory_data, max_tokens=2000)

# 带上下文的智能选择（如果实现了）
memory_text = format_memory_for_injection(
    memory_data,
    max_tokens=2000,
    current_context="用户正在询问 Python 测试相关的问题"
)
```

#### 4. 队列管理

```python
from src.agents.memory import get_memory_queue

queue = get_memory_queue()

# 添加到队列
queue.add(
    thread_id="thread_123",
    messages=[...],
    agent_name=None
)

# 查看队列状态
print(f"待处理数量: {queue.pending_count}")
print(f"正在处理: {queue.is_processing}")

# 立即处理队列（跳过防抖）
queue.flush()

# 清空队列（测试用）
queue.clear()
```

### REST API（如果已实现）

如果项目提供了 HTTP API，可能包含以下端点：

```bash
# 获取记忆数据
GET /api/memory
GET /api/memory/{agent_name}

# 手动触发更新
POST /api/memory/update
{
  "thread_id": "thread_123",
  "messages": [...],
  "agent_name": "optional"
}

# 清除记忆
DELETE /api/memory
DELETE /api/memory/{agent_name}
```

**注意**：需要检查实际的 API 路由实现。

### 直接文件操作

```python
from pathlib import Path
import json

# 读取记忆文件
memory_file = Path("/path/to/base_dir/memory.json")
with open(memory_file, "r", encoding="utf-8") as f:
    memory_data = json.load(f)

# 修改记忆
memory_data["user"]["workContext"]["summary"] = "新的工作背景..."

# 保存记忆
with open(memory_file, "w", encoding="utf-8") as f:
    json.dump(memory_data, f, indent=2, ensure_ascii=False)
```

**警告**：直接修改文件会绕过缓存机制，建议使用 `reload_memory_data()` 刷新缓存。

---

## 配置选项

### 配置文件（config.yaml）

```yaml
memory:
  # 是否启用记忆机制
  enabled: true
  
  # 存储路径（空字符串 = 默认路径）
  # 支持绝对路径和相对路径（相对于 base_dir）
  storage_path: ""
  
  # 防抖延迟（秒）
  debounce_seconds: 30
  
  # 用于记忆更新的模型（None = 使用默认模型）
  model_name: null
  
  # 最大 facts 数量
  max_facts: 100
  
  # Facts 置信度阈值（低于此值的不保存）
  fact_confidence_threshold: 0.7
  
  # 是否启用记忆注入
  injection_enabled: true
  
  # 记忆注入的最大 token 数
  max_injection_tokens: 2000
```

### Python 配置

```python
from src.config.memory_config import get_memory_config, set_memory_config, MemoryConfig

# 获取当前配置
config = get_memory_config()
print(config.enabled)
print(config.max_facts)

# 修改配置
new_config = MemoryConfig(
    enabled=True,
    debounce_seconds=60,
    max_facts=150,
    fact_confidence_threshold=0.8
)
set_memory_config(new_config)

# 从字典加载配置
from src.config.memory_config import load_memory_config_from_dict

load_memory_config_from_dict({
    "enabled": True,
    "max_facts": 200,
    "debounce_seconds": 45
})
```

### 配置字段详解

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | true | 是否启用记忆功能 |
| `storage_path` | str | "" | 存储路径（空=默认） |
| `debounce_seconds` | int | 30 | 防抖延迟（1-300秒） |
| `model_name` | str\|None | null | 更新用的模型名称 |
| `max_facts` | int | 100 | 最大 facts 数量（10-500） |
| `fact_confidence_threshold` | float | 0.7 | 置信度阈值（0.0-1.0） |
| `injection_enabled` | bool | true | 是否注入到提示词 |
| `max_injection_tokens` | int | 2000 | 注入的最大 token 数（100-8000） |

---

## API 参考

### 核心函数

#### get_memory_data()

```python
def get_memory_data(agent_name: str | None = None) -> dict[str, Any]
```

获取记忆数据（带缓存）。

**参数**：
- `agent_name`：可选，指定 agent 名称获取 per-agent 记忆

**返回**：记忆数据字典

**示例**：
```python
memory = get_memory_data()
facts = memory.get("facts", [])
work_context = memory["user"]["workContext"]["summary"]
```

#### reload_memory_data()

```python
def reload_memory_data(agent_name: str | None = None) -> dict[str, Any]
```

强制重新加载记忆数据，刷新缓存。

#### update_memory_from_conversation()

```python
def update_memory_from_conversation(
    messages: list[Any],
    thread_id: str | None = None,
    agent_name: str | None = None
) -> bool
```

从对话消息更新记忆。

**参数**：
- `messages`：对话消息列表
- `thread_id`：可选的线程 ID
- `agent_name`：可选的 agent 名称

**返回**：成功返回 True，失败返回 False

#### format_memory_for_injection()

```python
def format_memory_for_injection(
    memory_data: dict[str, Any],
    max_tokens: int = 2000,
    current_context: str | None = None
) -> str
```

格式化记忆用于注入到提示词。

**参数**：
- `memory_data`：记忆数据字典
- `max_tokens`：最大 token 数
- `current_context`：可选的当前对话上下文（用于相似度计算）

**返回**：格式化的记忆文本

#### format_conversation_for_update()

```python
def format_conversation_for_update(messages: list[Any]) -> str
```

格式化对话消息用于记忆更新提示词。

### 队列管理

#### get_memory_queue()

```python
def get_memory_queue() -> MemoryUpdateQueue
```

获取全局单例队列实例。

#### MemoryUpdateQueue 方法

```python
queue = get_memory_queue()

# 添加更新任务
queue.add(thread_id: str, messages: list[Any], agent_name: str | None = None)

# 查看队列状态
queue.pending_count  # 待处理数量
queue.is_processing  # 是否正在处理

# 立即处理
queue.flush()

# 清空队列
queue.clear()
```

### 配置管理

```python
from src.config.memory_config import (
    get_memory_config,
    set_memory_config,
    load_memory_config_from_dict,
    MemoryConfig
)

# 获取配置
config = get_memory_config()

# 设置配置
new_config = MemoryConfig(enabled=True, max_facts=200)
set_memory_config(new_config)

# 从字典加载
load_memory_config_from_dict({"enabled": True, "max_facts": 150})
```

---

## 最佳实践

### 1. 记忆内容质量

**✅ 好的做法**：
- 记录具体、可量化的信息（"16k+ GitHub stars"）
- 保留专有名词和技术术语（"LangGraph", "FastAPI"）
- 使用原始语言（中文项目名保留中文）
- 设置合理的置信度（明确陈述 0.9+，推断 0.7-0.8）

**❌ 避免**：
- 记录临时信息（文件上传路径、会话 ID）
- 模糊的描述（"用户喜欢编程"）
- 过低置信度的推测（< 0.7）
- 记录文件上传事件

### 2. 性能优化

**调整防抖时间**：
- 频繁对话：增加 `debounce_seconds`（减少 LLM 调用）
- 需要快速更新：减少 `debounce_seconds`

**控制 facts 数量**：
- 根据实际需求调整 `max_facts`（默认 100）
- 定期清理低置信度的 facts

**Token 管理**：
- 根据模型上下文窗口调整 `max_injection_tokens`
- 监控注入的记忆长度

### 3. 多 Agent 场景

**使用 per-agent 记忆**：
```python
# 在 middleware 中指定 agent_name
middleware = MemoryMiddleware(agent_name="code_assistant")

# 获取特定 agent 的记忆
agent_memory = get_memory_data(agent_name="code_assistant")
```

**好处**：
- 不同 agent 有独立的记忆空间
- 避免记忆混淆
- 可针对不同 agent 优化记忆内容

### 4. 调试和监控

**启用日志**：
```python
# 队列会输出日志
# "Memory update queued for thread xxx, queue size: 1"
# "Processing 2 queued memory updates"
# "Memory updated successfully for thread xxx"
```

**手动检查记忆文件**：
```bash
# 查看记忆文件
cat /path/to/base_dir/memory.json | jq .

# 查看 facts 数量
cat /path/to/base_dir/memory.json | jq '.facts | length'

# 查看高置信度 facts
cat /path/to/base_dir/memory.json | jq '.facts[] | select(.confidence > 0.9)'
```

### 5. 集成外部系统

**从外部系统导入记忆**：
```python
# 1. 准备记忆数据
external_memory = {
    "version": "1.0",
    "lastUpdated": "2026-04-03T10:00:00.000Z",
    "user": {...},
    "history": {...},
    "facts": [...]
}

# 2. 保存到文件
import json
from pathlib import Path
from src.config.paths import get_paths

memory_file = get_paths().memory_file
with open(memory_file, "w", encoding="utf-8") as f:
    json.dump(external_memory, f, indent=2, ensure_ascii=False)

# 3. 刷新缓存
from src.agents.memory import reload_memory_data
reload_memory_data()
```

**导出记忆到外部系统**：
```python
from src.agents.memory import get_memory_data
import requests

memory = get_memory_data()

# 发送到外部 API
response = requests.post(
    "https://external-system.com/api/memory",
    json=memory,
    headers={"Authorization": "Bearer xxx"}
)
```

### 6. 测试建议

**单元测试**：
```python
from src.agents.memory import (
    get_memory_data,
    update_memory_from_conversation,
    reset_memory_queue
)

def test_memory_update():
    # 重置队列
    reset_memory_queue()
    
    # 准备测试消息
    messages = [...]
    
    # 更新记忆
    success = update_memory_from_conversation(messages, thread_id="test_123")
    assert success
    
    # 验证记忆内容
    memory = get_memory_data()
    assert len(memory["facts"]) > 0
```

**集成测试**：
```python
def test_end_to_end_memory():
    # 1. 发起对话
    # 2. 等待防抖时间
    # 3. 检查记忆是否更新
    # 4. 验证下次对话能访问到记忆
```

---

## 常见问题

### Q1: 记忆什么时候更新？

A: 每次 Agent 执行完成后，会将对话添加到更新队列。默认等待 30 秒（防抖），然后批量处理。可以调用 `queue.flush()` 立即处理。

### Q2: 如何清空记忆？

A: 删除记忆文件即可：
```bash
rm /path/to/base_dir/memory.json
```
或者覆盖为空记忆：
```python
from src.agents.memory.updater import _create_empty_memory, _save_memory_to_file

empty_memory = _create_empty_memory()
_save_memory_to_file(empty_memory)
```

### Q3: 记忆注入会消耗多少 token？

A: 默认最多 2000 tokens（可配置）。实际消耗取决于记忆内容的丰富程度。使用 tiktoken 精确计算。

### Q4: 支持向量数据库吗？

A: 当前版本使用 JSON 文件存储。未来可以扩展支持向量数据库（如 Pinecone、Weaviate）进行更高级的语义检索。

### Q5: 如何避免记录敏感信息？

A: 
- 在 LLM 更新记忆前，可以添加隐私过滤逻辑
- 调整提示词，指示 LLM 不记录敏感信息
- 定期审查 memory.json 文件

### Q6: 多个实例会冲突吗？

A: 会的。当前实现使用文件锁不足。如果多个进程同时写入，可能导致数据丢失。建议：
- 单实例部署
- 或实现文件锁机制
- 或迁移到数据库存储

---

## 相关文档

- [MEMORY_IMPROVEMENTS.md](./MEMORY_IMPROVEMENTS.md) - 记忆系统的技术改进详情
- [MEMORY_IMPROVEMENTS_SUMMARY.md](./MEMORY_IMPROVEMENTS_SUMMARY.md) - 改进总结（中文）
- [CONFIGURATION.md](./CONFIGURATION.md) - 完整配置指南

---

## 未来规划

1. **向量数据库集成**：支持 Pinecone、Weaviate 等
2. **语义搜索**：基于 embedding 的高级检索
3. **记忆分层**：短期、中期、长期记忆分离
4. **记忆压缩**：自动归纳和压缩历史记忆
5. **隐私控制**：用户可选择哪些信息可以被记录
6. **记忆分享**：团队成员间共享记忆（权限控制）

---

**最后更新**：2026-04-03
