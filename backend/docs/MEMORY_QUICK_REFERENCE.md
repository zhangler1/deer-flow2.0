# 记忆系统快速参考

## 一句话概述

DeerFlow 的记忆系统通过 LLM 自动提取和存储用户的上下文、偏好和知识，并在后续对话中智能注入相关记忆，实现个性化交互。

---

## 核心概念

### 存储位置
- **全局记忆**: `{base_dir}/memory.json`
- **Per-agent 记忆**: `{base_dir}/.deer-flow/memory/{agent_name}.json`

### 数据结构
```
memory.json
├── user (用户上下文)
│   ├── workContext      # 工作背景
│   ├── personalContext  # 个人背景
│   └── topOfMind        # 当前关注点
├── history (历史上下文)
│   ├── recentMonths     # 最近1-3个月
│   ├── earlierContext   # 3-12个月前
│   └── longTermBackground # 长期背景
└── facts[] (事实列表)
    └── {id, content, category, confidence, createdAt, source}
```

### 工作流程

```
对话完成 → 消息过滤 → 加入队列(30s防抖) → LLM分析 → 更新记忆 → 保存文件
                                                    ↓
下次对话 ← 格式化注入 ← 相似度选择(TF-IDF) ← 读取记忆
```

---

## 快速上手

### 安装
```bash
cd backend
uv sync
```

### 基础使用

```python
from src.agents.memory import get_memory_data, update_memory_from_conversation
from langchain_core.messages import HumanMessage, AIMessage

# 1️⃣ 读取记忆
memory = get_memory_data()
print(memory["user"]["workContext"]["summary"])
print(f"共有 {len(memory['facts'])} 条事实")

# 2️⃣ 更新记忆
messages = [
    HumanMessage(content="我喜欢用 pytest 写测试"),
    AIMessage(content="pytest 是很好的选择！...")
]
success = update_memory_from_conversation(messages, thread_id="thread_001")

# 3️⃣ 格式化用于注入
from src.agents.memory import format_memory_for_injection
memory_text = format_memory_for_injection(memory, max_tokens=2000)
```

---

## 配置 (config.yaml)

```yaml
memory:
  enabled: true                      # 启用记忆
  storage_path: ""                   # 存储路径（空=默认）
  debounce_seconds: 30               # 防抖延迟
  model_name: null                   # 更新用的模型
  max_facts: 100                     # 最大facts数量
  fact_confidence_threshold: 0.7     # 置信度阈值
  injection_enabled: true            # 启用注入
  max_injection_tokens: 2000         # 最大注入tokens
```

---

## 常用 API

| 功能 | 函数 | 示例 |
|------|------|------|
| 获取记忆 | `get_memory_data(agent_name=None)` | `memory = get_memory_data()` |
| 刷新缓存 | `reload_memory_data(agent_name=None)` | `memory = reload_memory_data()` |
| 更新记忆 | `update_memory_from_conversation(messages, thread_id, agent_name)` | `success = update_memory_from_conversation(msgs)` |
| 格式化注入 | `format_memory_for_injection(memory, max_tokens)` | `text = format_memory_for_injection(memory, 2000)` |
| 获取队列 | `get_memory_queue()` | `queue = get_memory_queue()` |
| 立即处理 | `queue.flush()` | `get_memory_queue().flush()` |

---

## Facts 类别

| 类别 | 说明 | 示例 |
|------|------|------|
| `preference` | 偏好 | "偏好使用 pytest 进行测试" |
| `knowledge` | 知识/专长 | "精通 LangGraph 框架" |
| `context` | 背景信息 | "在 ABC 公司担任后端工程师" |
| `behavior` | 行为模式 | "喜欢先写测试再写代码" |
| `goal` | 目标 | "计划学习 Rust 语言" |

---

## 置信度指南

| 范围 | 说明 | 何时使用 |
|------|------|----------|
| 0.9-1.0 | 明确陈述 | 用户直接说的事实 |
| 0.7-0.8 | 强烈暗示 | 从行为中明显推断 |
| 0.5-0.6 | 推测 | 谨慎使用，需要明确模式 |
| <0.5 | 不记录 | 低于阈值不保存 |

---

## 最佳实践

### ✅ 推荐
- 记录具体、可量化的信息（"16k+ stars"）
- 保留专有名词和技术术语
- 使用异步队列更新（默认）
- 定期审查记忆质量
- 使用 per-agent 记忆隔离不同场景

### ❌ 避免
- 记录文件上传路径（会话级信息）
- 记录临时、一次性的信息
- 使用过低的置信度（<0.7）
- 在多进程环境中并发写入
- 在对话中透露敏感信息

---

## 常见问题

**Q: 记忆何时更新？**  
A: Agent 执行完成后自动添加到队列，默认 30 秒后批量处理。

**Q: 如何立即更新？**  
A: 调用 `get_memory_queue().flush()` 跳过防抖。

**Q: 支持多进程吗？**  
A: 当前使用文件存储，不支持多进程并发写入。建议单实例或迁移到数据库。

**Q: 如何清空记忆？**  
A: 删除 `memory.json` 文件，或覆盖为空记忆结构。

**Q: 记忆会消耗多少 tokens？**  
A: 默认最多 2000 tokens（可配置），使用 tiktoken 精确计算。

**Q: 如何避免记录敏感信息？**  
A: 定期审查 memory.json，或在提示词中指示 LLM 不记录敏感内容。

---

## 技术特性

### 🎯 智能选择
- **TF-IDF 相似度**：基于对话上下文选择相关 facts
- **综合评分**：相似度(60%) + 置信度(40%)
- **上下文窗口**：提取最近 3 轮对话

### ⚡ 性能优化
- **缓存机制**：基于文件修改时间的智能缓存
- **防抖队列**：批量处理减少 LLM 调用
- **精确计数**：使用 tiktoken 准确计算 tokens
- **自动截断**：超出限制自动截断

### 🧹 数据清理
- **自动过滤**：移除文件上传相关内容
- **置信度阈值**：只保存高质量 facts
- **数量限制**：自动保留置信度最高的前 N 条

---

## 进阶功能

### 1. Per-Agent 记忆

```python
# 不同 agent 使用独立记忆
code_memory = get_memory_data(agent_name="code_assistant")
chat_memory = get_memory_data(agent_name="chat_bot")
```

### 2. 手动构建记忆

```python
import json
from pathlib import Path
from src.config.paths import get_paths

custom_memory = {
    "version": "1.0",
    "user": {...},
    "history": {...},
    "facts": [...]
}

memory_file = get_paths().memory_file
with open(memory_file, "w") as f:
    json.dump(custom_memory, f, indent=2, ensure_ascii=False)
```

### 3. 外部系统集成

```python
# 导入
import_from_crm(user_id) → memory.json

# 导出
export_to_warehouse() ← memory.json

# 实时同步
webhook → update_memory_from_conversation()
```

---

## 文件结构

```
backend/src/agents/memory/
├── __init__.py           # 模块导出
├── prompt.py             # 提示词模板和格式化
├── updater.py            # 记忆更新逻辑
└── queue.py              # 更新队列和防抖

backend/src/agents/middlewares/
└── memory_middleware.py  # Agent 中间件集成

backend/src/config/
└── memory_config.py      # 配置管理

{base_dir}/
├── memory.json           # 全局记忆文件
└── .deer-flow/memory/    # Per-agent 记忆目录
    ├── agent1.json
    └── agent2.json
```

---

## 相关文档

| 文档 | 用途 |
|------|------|
| [MEMORY_SYSTEM.md](./MEMORY_SYSTEM.md) | 完整系统文档 |
| [MEMORY_API.md](./MEMORY_API.md) | API 接口和示例 |
| [MEMORY_IMPROVEMENTS.md](./MEMORY_IMPROVEMENTS.md) | 技术改进详情 |
| [MEMORY_IMPROVEMENTS_SUMMARY.md](./MEMORY_IMPROVEMENTS_SUMMARY.md) | 改进总结（中文） |

---

## 示例代码

### 完整对话流程

```python
from src.agents.memory import (
    get_memory_data,
    format_memory_for_injection,
    update_memory_from_conversation
)
from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# 1. 获取记忆
memory = get_memory_data()
memory_text = format_memory_for_injection(memory, max_tokens=1500)

# 2. 构建系统提示词
system_prompt = f"""你是智能助手，了解用户背景。

<memory>
{memory_text}
</memory>

请提供个性化回复。"""

# 3. 对话
llm = ChatOpenAI(model="gpt-4")
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}")
])

chain = prompt | llm
user_input = "我该如何写测试？"
response = chain.invoke({"input": user_input})

# 4. 更新记忆
messages = [
    HumanMessage(content=user_input),
    AIMessage(content=response.content)
]
update_memory_from_conversation(messages, thread_id="demo_001")

print(f"AI: {response.content}")
print("✓ 记忆已更新（30秒后生效）")
```

---

**版本**: 1.0  
**最后更新**: 2026-04-03
