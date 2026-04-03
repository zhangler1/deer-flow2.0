# 记忆系统文档索引

欢迎使用 DeerFlow 记忆系统！本目录包含完整的文档和示例。

---

## 📖 文档列表

### 快速入门（推荐从这里开始）

| 文档 | 语言 | 说明 | 适合人群 |
|------|------|------|----------|
| [记忆系统使用指南.md](./记忆系统使用指南.md) | 中文 | 📌 **从这里开始**！完整的入门和使用指南 | 所有用户 |
| [MEMORY_QUICK_REFERENCE.md](./MEMORY_QUICK_REFERENCE.md) | English | 快速参考卡片 | 有经验的开发者 |

### 完整文档

| 文档 | 语言 | 说明 | 适合人群 |
|------|------|------|----------|
| [MEMORY_SYSTEM.md](./MEMORY_SYSTEM.md) | 中文 | 完整的系统文档，包含所有技术细节 | 深度用户、系统管理员 |
| [MEMORY_API.md](./MEMORY_API.md) | 中文 | API 接口参考和集成示例 | 开发者、集成工程师 |

### 技术改进文档

| 文档 | 语言 | 说明 | 适合人群 |
|------|------|------|----------|
| [MEMORY_IMPROVEMENTS_SUMMARY.md](./MEMORY_IMPROVEMENTS_SUMMARY.md) | 中文 | 技术改进总结 | 技术人员 |
| [MEMORY_IMPROVEMENTS.md](./MEMORY_IMPROVEMENTS.md) | English | 详细的技术改进文档（TF-IDF、tiktoken） | 核心开发者 |

---

## 💡 如何选择文档？

### 我是新手，想快速上手
👉 阅读 [记忆系统使用指南.md](./记忆系统使用指南.md)

包含：
- ✅ 什么是记忆系统
- ✅ 快速开始（3行代码）
- ✅ 存储结构详解
- ✅ 配置选项
- ✅ 常见场景
- ✅ 常见问题

### 我需要快速查找 API
👉 查看 [MEMORY_QUICK_REFERENCE.md](./MEMORY_QUICK_REFERENCE.md)

包含：
- ✅ 核心 API 一览表
- ✅ Facts 类别速查
- ✅ 置信度指南
- ✅ 最佳实践清单

### 我要深入了解系统架构
👉 阅读 [MEMORY_SYSTEM.md](./MEMORY_SYSTEM.md)

包含：
- ✅ 完整的系统概述
- ✅ 详细的存储结构
- ✅ 更新流程详解
- ✅ 注入机制原理
- ✅ 配置选项详解

### 我要集成到外部系统
👉 参考 [MEMORY_API.md](./MEMORY_API.md)

包含：
- ✅ Python SDK 接口
- ✅ REST API 设计（如果已实现）
- ✅ 完整的集成示例
- ✅ CRM 集成示例
- ✅ Slack 集成示例
- ✅ 数据仓库导出示例

### 我想了解最新的技术改进
👉 阅读 [MEMORY_IMPROVEMENTS_SUMMARY.md](./MEMORY_IMPROVEMENTS_SUMMARY.md)

包含：
- ✅ TF-IDF 相似度召回
- ✅ tiktoken 精确 token 计算
- ✅ 动态系统提示词
- ✅ 多轮对话上下文

---

## 🚀 示例代码

### 运行示例脚本

```bash
cd backend
python examples/memory_integration_example.py
```

这个脚本展示了：
- ✅ 读取记忆数据
- ✅ 更新记忆（演示代码）
- ✅ 使用异步队列
- ✅ 格式化用于注入
- ✅ 查询和过滤 facts
- ✅ 查看配置
- ✅ 手动构建记忆
- ✅ Per-agent 记忆

### 快速示例

```python
from src.agents.memory import get_memory_data, update_memory_from_conversation
from langchain_core.messages import HumanMessage, AIMessage

# 1️⃣ 读取记忆
memory = get_memory_data()
print(f"工作背景: {memory['user']['workContext']['summary']}")
print(f"共有 {len(memory['facts'])} 条事实")

# 2️⃣ 更新记忆
messages = [
    HumanMessage(content="我正在学习 LangGraph"),
    AIMessage(content="很好！LangGraph 是一个强大的框架...")
]
success = update_memory_from_conversation(messages, thread_id="demo_001")

# 3️⃣ 格式化注入
from src.agents.memory import format_memory_for_injection
memory_text = format_memory_for_injection(memory, max_tokens=2000)
```

---

## 📊 文档结构

```
backend/docs/
├── MEMORY_README.md                      # 📍 你在这里
├── 记忆系统使用指南.md                    # 中文完整指南
├── MEMORY_QUICK_REFERENCE.md             # 英文快速参考
├── MEMORY_SYSTEM.md                      # 完整系统文档
├── MEMORY_API.md                         # API 参考
├── MEMORY_IMPROVEMENTS_SUMMARY.md        # 改进总结（中文）
└── MEMORY_IMPROVEMENTS.md                # 改进详情（英文）

backend/examples/
└── memory_integration_example.py         # 集成示例脚本

backend/src/agents/memory/
├── __init__.py                           # 模块导出
├── prompt.py                             # 提示词和格式化
├── updater.py                            # 记忆更新逻辑
└── queue.py                              # 异步队列

backend/src/agents/middlewares/
└── memory_middleware.py                  # Agent 中间件

backend/src/config/
└── memory_config.py                      # 配置管理
```

---

## 🎯 核心概念速览

### 什么是记忆系统？

一个**全局的长期记忆机制**，能够：
- 📝 自动记录用户的背景、偏好和对话历史
- 🧠 智能提取关键事实和知识点
- 🎯 动态注入相关记忆到系统提示词
- 🔄 持续更新和完善记忆内容

### 记忆存储在哪里？

- **全局记忆**：`{base_dir}/memory.json`
- **Per-agent 记忆**：`{base_dir}/.deer-flow/memory/{agent_name}.json`

### 记忆何时更新？

每次 Agent 执行完成后：
1. 对话消息添加到队列
2. 等待 30 秒（防抖）
3. 批量调用 LLM 分析
4. 提取 facts，更新 user/history 部分
5. 保存到 JSON 文件

### 记忆如何注入？

在 LLM 调用前：
1. 提取最近 3 轮对话
2. 基于 TF-IDF 计算相似度
3. 选择最相关的记忆（相似度 60% + 置信度 40%）
4. 格式化注入到 `<memory>` 标签

---

## ⚙️ 配置快速参考

```yaml
memory:
  enabled: true                      # 启用/禁用
  debounce_seconds: 30               # 防抖延迟
  max_facts: 100                     # 最大 facts 数
  fact_confidence_threshold: 0.7     # 置信度阈值
  max_injection_tokens: 2000         # 最大注入 tokens
```

---

## 🔗 相关链接

### 代码文件
- [`src/agents/memory/`](../src/agents/memory/) - 核心实现
- [`src/agents/middlewares/memory_middleware.py`](../src/agents/middlewares/memory_middleware.py) - 中间件集成
- [`src/config/memory_config.py`](../src/config/memory_config.py) - 配置管理

### 配置文件
- [`config.example.yaml`](../../config.example.yaml) - 配置示例
- [`config.production.yaml`](../../config.production.yaml) - 生产配置

### 测试文件
- [`tests/test_memory_upload_filtering.py`](../tests/test_memory_upload_filtering.py) - 测试用例

---

## 💬 获取帮助

### 常见问题

查看各文档的 "常见问题" 部分：
- [记忆系统使用指南 - 常见问题](./记忆系统使用指南.md#-常见问题)
- [MEMORY_SYSTEM - 常见问题](./MEMORY_SYSTEM.md#常见问题)

### 运行示例

```bash
cd backend
python examples/memory_integration_example.py
```

### 查看记忆内容

```bash
# 查看记忆文件
cat /path/to/memory.json | jq .

# 统计 facts
cat /path/to/memory.json | jq '.facts | length'

# 查看高置信度 facts
cat /path/to/memory.json | jq '.facts[] | select(.confidence > 0.9)'
```

---

## 🚧 未来规划

- [ ] 向量数据库集成（Pinecone、Weaviate）
- [ ] 语义搜索（基于 embedding）
- [ ] 记忆分层（短期、中期、长期）
- [ ] 自动压缩和归纳
- [ ] 隐私控制和权限管理
- [ ] 团队记忆共享

---

## 📝 贡献

如果发现文档问题或有改进建议，欢迎：
1. 提交 Issue
2. 发起 Pull Request
3. 联系维护团队

---

**最后更新**：2026-04-03  
**维护者**：DeerFlow Team
