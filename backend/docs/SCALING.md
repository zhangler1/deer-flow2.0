# DeerFlow 扩展到1万用户架构指南

本文档详细说明如何将 DeerFlow 从单机开发环境扩展到支持 **1万+ 并发用户** 的生产环境。

## 📊 目录

- [当前架构分析](#当前架构分析)
- [性能瓶颈识别](#性能瓶颈识别)
- [扩展方案设计](#扩展方案设计)
- [实施步骤](#实施步骤)
- [容量规划](#容量规划)
- [监控与优化](#监控与优化)
- [成本估算](#成本估算)

---

## 当前架构分析

### 现有组件

DeerFlow 采用微服务架构:

```
┌─────────────┐
│   Nginx     │ :2026 (反向代理)
└──────┬──────┘
       │
       ├──────► Frontend (Next.js) :3000
       ├──────► Gateway (FastAPI) :8001
       └──────► LangGraph Server :2024
                      │
                      ├──► Checkpointer (SQLite/Postgres)
                      ├──► Sandbox (Local/Docker/K8s)
                      └──► LLM APIs
```

### 当前容量限制

| 组件 | 当前配置 | 瓶颈 |
|------|---------|------|
| **Frontend** | 单实例 | CPU密集型渲染 |
| **Gateway** | 单实例 | I/O等待 |
| **LangGraph** | 单实例 | 状态管理+计算 |
| **Checkpointer** | SQLite | **并发写入限制** ⚠️ |
| **Sandbox** | 3个并发 | **资源池太小** ⚠️ |

**预估当前容量**: ~100-200 并发用户

---

## 性能瓶颈识别

### 🔴 关键瓶颈

1. **SQLite 数据库**
   - 单文件锁,不支持并发写入
   - 写入速度: ~1000 TPS
   - 适合场景: 单机开发/小规模部署

2. **单实例部署**
   - 无法横向扩展
   - 单点故障风险
   - CPU/内存利用率受限

3. **沙箱资源池**
   - 默认仅3个并发沙箱
   - 队列等待时间长
   - 资源竞争激烈

### 🟡 次要瓶颈

4. **无缓存层**
   - 重复查询数据库
   - API响应慢

5. **无连接池**
   - 频繁建立连接
   - 资源浪费

---

## 扩展方案设计

### 阶段1: 数据库升级 (必需)

#### PostgreSQL 替代 SQLite

**为什么选择 PostgreSQL?**
- ✅ 支持高并发读写 (10,000+ TPS)
- ✅ ACID 事务保证
- ✅ 连接池管理
- ✅ 主从复制和读写分离
- ✅ 成熟的 HA 方案

**配置示例**:

```yaml
# config.yaml
checkpointer:
  type: postgres
  connection_string: postgresql://deerflow:${DB_PASSWORD}@postgres:5432/deerflow
  
  # 连接池配置 (适用于 SQLAlchemy/psycopg)
  pool_size: 20          # 每个进程保持20个连接
  max_overflow: 10       # 最多再创建10个临时连接
  pool_timeout: 30       # 获取连接超时时间
  pool_recycle: 3600     # 连接回收时间(秒)
```

**PostgreSQL 部署建议**:

```yaml
# docker-compose-production.yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: deerflow
      POSTGRES_USER: deerflow
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      # 性能优化
      POSTGRES_SHARED_BUFFERS: 256MB
      POSTGRES_EFFECTIVE_CACHE_SIZE: 1GB
      POSTGRES_MAX_CONNECTIONS: 200
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U deerflow"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**数据迁移脚本** (见下方 `scripts/migrate_sqlite_to_postgres.py`)

---

### 阶段2: 服务水平扩展

#### 多实例部署

**架构图**:

```
                  ┌─────────────┐
                  │ Load Balancer│
                  │   (Nginx)    │
                  └──────┬───────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │Gateway-1│    │Gateway-2│    │Gateway-3│
    └────┬────┘    └────┬────┘    └────┬────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                  ┌──────▼───────┐
                  │  PostgreSQL  │
                  │   + Redis    │
                  └──────────────┘
```

**Docker Compose 配置**:

```yaml
# docker-compose-production.yaml
services:
  # Redis 缓存层
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          memory: 2G

  # Gateway 服务 (5个实例)
  gateway:
    image: deer-flow-backend:latest
    command: |
      sh -c "cd backend && 
      uv run uvicorn src.gateway.app:app 
      --host 0.0.0.0 
      --port 8001 
      --workers 2
      --limit-concurrency 1000
      --timeout-keep-alive 5"
    environment:
      - DATABASE_URL=postgresql://deerflow:${DB_PASSWORD}@postgres:5432/deerflow
      - REDIS_URL=redis://redis:6379/0
      - WORKER_ID=${HOSTNAME}  # 实例唯一标识
    env_file:
      - .env
    deploy:
      replicas: 5  # 5个实例
      resources:
        limits:
          cpus: '2'
          memory: 4G
      restart_policy:
        condition: on-failure
        max_attempts: 3
    depends_on:
      - postgres
      - redis

  # LangGraph 服务 (5个实例)
  langgraph:
    image: deer-flow-backend:latest
    command: |
      sh -c "cd backend && 
      uv run langgraph dev 
      --host 0.0.0.0 
      --port 2024 
      --no-browser"
    environment:
      - DATABASE_URL=postgresql://deerflow:${DB_PASSWORD}@postgres:5432/deerflow
      - REDIS_URL=redis://redis:6379/1
    deploy:
      replicas: 5
      resources:
        limits:
          cpus: '2'
          memory: 4G
    depends_on:
      - postgres
      - redis

  # Frontend 服务 (3个实例)
  frontend:
    image: deer-flow-frontend:latest
    command: sh -c "cd frontend && pnpm run start"
    environment:
      - NODE_ENV=production
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 2G

  # Nginx 负载均衡器
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx-lb.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - gateway
      - langgraph
      - frontend
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 1G

volumes:
  postgres_data:
  redis_data:
```

---

### 阶段3: 负载均衡配置

#### Nginx 高级配置

创建 `nginx/nginx-lb.conf`:

```nginx
# 工作进程数 (根据 CPU 核心数调整)
worker_processes auto;

events {
    worker_connections 4096;  # 每个进程的最大连接数
    use epoll;                # Linux 高性能事件模型
}

http {
    # 日志配置
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # 性能优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript 
               application/json application/javascript application/xml+rss;

    # 限流配置
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=chat_limit:10m rate=5r/s;
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    # Gateway 上游服务器
    upstream gateway_backend {
        least_conn;  # 最少连接算法
        
        server gateway-1:8001 max_fails=3 fail_timeout=30s weight=1;
        server gateway-2:8001 max_fails=3 fail_timeout=30s weight=1;
        server gateway-3:8001 max_fails=3 fail_timeout=30s weight=1;
        server gateway-4:8001 max_fails=3 fail_timeout=30s weight=1;
        server gateway-5:8001 max_fails=3 fail_timeout=30s weight=1;
        
        # 健康检查 (需要 nginx-plus 或使用第三方模块)
        # health_check interval=10s fails=3 passes=2;
        
        # 长连接优化
        keepalive 32;
    }

    # LangGraph 上游服务器
    upstream langgraph_backend {
        least_conn;
        
        server langgraph-1:2024 max_fails=3 fail_timeout=30s;
        server langgraph-2:2024 max_fails=3 fail_timeout=30s;
        server langgraph-3:2024 max_fails=3 fail_timeout=30s;
        server langgraph-4:2024 max_fails=3 fail_timeout=30s;
        server langgraph-5:2024 max_fails=3 fail_timeout=30s;
        
        keepalive 32;
    }

    # Frontend 上游服务器
    upstream frontend_backend {
        least_conn;
        
        server frontend-1:3000 max_fails=3 fail_timeout=30s;
        server frontend-2:3000 max_fails=3 fail_timeout=30s;
        server frontend-3:3000 max_fails=3 fail_timeout=30s;
        
        keepalive 16;
    }

    # 主服务器配置
    server {
        listen 80;
        server_name _;

        # 客户端请求限制
        client_max_body_size 100M;
        client_body_timeout 60s;
        client_header_timeout 60s;

        # 全局限流
        limit_conn conn_limit 10;  # 每个IP最多10个并发连接

        # Frontend
        location / {
            proxy_pass http://frontend_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
            
            # 超时配置
            proxy_connect_timeout 10s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Gateway API
        location /api {
            # 限流: 每秒10个请求,突发允许20个
            limit_req zone=api_limit burst=20 nodelay;
            
            proxy_pass http://gateway_backend;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            
            # 超时配置
            proxy_connect_timeout 10s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # LangGraph Threads API
        location /threads {
            # 限流: 每秒5个请求 (聊天接口更严格)
            limit_req zone=chat_limit burst=10 nodelay;
            
            proxy_pass http://langgraph_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            
            # 长超时 (Agent 执行可能需要较长时间)
            proxy_connect_timeout 10s;
            proxy_send_timeout 300s;  # 5分钟
            proxy_read_timeout 300s;  # 5分钟
            
            # 禁用缓冲 (流式响应)
            proxy_buffering off;
        }

        # 健康检查端点
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }

        # Nginx 状态页面 (仅内部访问)
        location /nginx_status {
            stub_status on;
            access_log off;
            allow 127.0.0.1;
            allow 172.16.0.0/12;  # Docker 内部网络
            deny all;
        }
    }
}
```

---

### 阶段4: 沙箱扩展

#### 提升沙箱并发能力

**配置优化**:

```yaml
# config.yaml
sandbox:
  use: src.community.aio_sandbox:AioSandboxProvider
  
  # 大幅提升并发沙箱数量
  replicas: 100  # 从默认的3提升到100
  
  # 基础端口 (自动分配 8080-8179)
  port: 8080
  
  # 容器资源限制
  resources:
    cpu_limit: "1.0"      # 每个沙箱最多1核
    memory_limit: "1Gi"   # 每个沙箱最多1GB内存
    
  # 容器镜像
  image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest
  
  # 超时配置
  timeout_seconds: 300    # 单次命令超时5分钟
  idle_timeout: 600       # 空闲10分钟后回收
  
  # 环境变量注入
  environment:
    PYTHONUNBUFFERED: "1"
    NODE_ENV: production
```

**Kubernetes 模式 (推荐生产环境)**:

如果使用 K8s 集群,可获得更好的隔离和扩展性:

```yaml
# config.yaml
sandbox:
  use: src.community.aio_sandbox:AioSandboxProvider
  provisioner_url: http://provisioner:8002  # 使用 K8s Provisioner
  
  # K8s 特定配置
  namespace: deer-flow-sandbox
  pod_template:
    resources:
      requests:
        cpu: "500m"
        memory: "512Mi"
      limits:
        cpu: "1"
        memory: "1Gi"
    # 节点亲和性 (可选)
    nodeSelector:
      workload: sandbox
```

---

### 阶段5: Redis 缓存层

#### 引入缓存减少数据库压力

**应用场景**:
1. 用户会话缓存
2. 模型配置缓存
3. 技能元数据缓存
4. 频繁查询结果缓存

**示例代码** (见下方 `src/cache/redis_cache.py`)

---

### 阶段6: 监控与告警

#### Prometheus + Grafana 监控栈

```yaml
# docker-compose-monitoring.yaml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'

  grafana:
    image: grafana/grafana:latest
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false

  loki:
    image: grafana/loki:latest
    volumes:
      - loki_data:/loki
    ports:
      - "3100:3100"

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log
      - ./logs:/app/logs
      - ./monitoring/promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml

volumes:
  prometheus_data:
  grafana_data:
  loki_data:
```

**关键指标**:
- QPS (每秒查询数)
- 响应时间 (P50/P95/P99)
- 错误率
- 数据库连接池使用率
- 沙箱资源使用率
- Redis 命中率

---

## 实施步骤

### Week 1: 数据库迁移

**任务清单**:
- [ ] 部署 PostgreSQL 数据库
- [ ] 编写数据迁移脚本
- [ ] 迁移现有 SQLite 数据
- [ ] 测试数据完整性
- [ ] 更新 `config.yaml` 配置
- [ ] 压力测试验证

**迁移脚本**: 见 `scripts/migrate_sqlite_to_postgres.py`

### Week 2: 服务扩展

**任务清单**:
- [ ] 编写生产环境 Docker Compose 配置
- [ ] 配置 Nginx 负载均衡
- [ ] 部署多实例服务
- [ ] 配置健康检查
- [ ] 测试故障转移

### Week 3: 缓存与优化

**任务清单**:
- [ ] 部署 Redis 缓存
- [ ] 实现缓存逻辑
- [ ] 优化热点查询
- [ ] 配置连接池
- [ ] 性能基准测试

### Week 4: 监控与压测

**任务清单**:
- [ ] 部署监控栈
- [ ] 配置告警规则
- [ ] 编写压测脚本
- [ ] 执行负载测试
- [ ] 性能调优

---

## 容量规划

### 用户行为假设

- 总用户数: **10,000**
- 日活跃用户: **2,000** (20%)
- 高峰期在线: **1,000** (10%)
- 每用户每天消息数: **20**
- 每条消息处理时间: **2-5秒**

### 性能指标

| 指标 | 目标值 |
|------|--------|
| 峰值 QPS | 1,000 |
| 平均响应时间 | < 2s |
| P95 响应时间 | < 5s |
| P99 响应时间 | < 10s |
| 可用性 | 99.9% |

### 资源配置

#### 服务器配置 (推荐)

| 服务 | 实例数 | 规格 | 总资源 |
|------|--------|------|--------|
| **Gateway** | 5 | 2C4G | 10C20G |
| **LangGraph** | 5 | 2C4G | 10C20G |
| **Frontend** | 3 | 1C2G | 3C6G |
| **PostgreSQL** | 1 (主) + 1 (从) | 4C8G | 8C16G |
| **Redis** | 1 | 2C4G | 2C4G |
| **Nginx** | 2 | 2C2G | 4C4G |
| **监控** | 3 | 1C2G | 3C6G |

**总计**: ~40 CPU 核心, ~76GB 内存

#### 云服务器建议配置

**阿里云/腾讯云/AWS**:
- **计算实例**: 5台 8C16G (通用型)
- **数据库**: RDS PostgreSQL 高可用版 (4C8G)
- **缓存**: Redis 云服务 (2C4G)
- **负载均衡**: SLB/ALB
- **CDN**: 静态资源加速

**预估月成本**: ¥5,000 - ¥8,000 (不含 LLM API)

---

## 监控与优化

### 关键监控指标

#### 1. 应用层

```python
# 在 FastAPI 中添加 Prometheus 指标
from prometheus_client import Counter, Histogram

# 请求计数器
request_counter = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])

# 响应时间直方图
response_time = Histogram('http_response_time_seconds', 'HTTP response time', ['endpoint'])

# 在中间件中记录
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    response_time.labels(endpoint=request.url.path).observe(duration)
    request_counter.labels(
        method=request.method, 
        endpoint=request.url.path, 
        status=response.status_code
    ).inc()
    
    return response
```

#### 2. 数据库层

- 连接池使用率
- 慢查询日志
- 锁等待时间
- 查询 QPS

#### 3. 系统层

- CPU 使用率
- 内存使用率
- 磁盘 I/O
- 网络带宽

### 性能优化建议

#### 1. 数据库优化

```sql
-- 创建索引
CREATE INDEX idx_checkpoints_thread_id ON checkpoints(thread_id);
CREATE INDEX idx_checkpoints_created_at ON checkpoints(created_at);

-- 定期清理旧数据
DELETE FROM checkpoints WHERE created_at < NOW() - INTERVAL '30 days';

-- 分析表统计信息
ANALYZE checkpoints;
```

#### 2. 缓存策略

```python
# 缓存模型配置 (1小时)
@cache(ttl=3600)
def get_model_config(model_name: str):
    return load_model_config(model_name)

# 缓存技能列表 (5分钟)
@cache(ttl=300)
def list_available_skills():
    return scan_skills_directory()
```

#### 3. 异步处理

```python
# 使用后台任务处理耗时操作
from fastapi import BackgroundTasks

@app.post("/chat")
async def chat(message: str, background_tasks: BackgroundTasks):
    # 立即返回响应
    response = await quick_response(message)
    
    # 后台记录日志/分析
    background_tasks.add_task(log_interaction, message, response)
    
    return response
```

---

## 成本估算

### 云服务成本 (月)

#### 阿里云示例

| 资源 | 规格 | 数量 | 单价 | 小计 |
|------|------|------|------|------|
| ECS 实例 | 8C16G | 5 | ¥800 | ¥4,000 |
| RDS PostgreSQL | 4C8G | 1 | ¥1,200 | ¥1,200 |
| Redis | 2C4G | 1 | ¥300 | ¥300 |
| SLB | 标准版 | 1 | ¥200 | ¥200 |
| CDN | 100GB | - | ¥50 | ¥50 |
| 带宽 | 100Mbps | - | ¥500 | ¥500 |

**基础设施合计**: ¥6,250/月

#### LLM API 成本

根据使用量差异很大,以 GPT-4 为例:
- 10,000 用户 × 20 消息/天 × 30 天 = 600万条消息
- 平均每条消息 1,000 tokens
- GPT-4 价格: $0.03/1K tokens (输入) + $0.06/1K tokens (输出)
- 预估: **$180,000 - $270,000/月**

**优化建议**:
1. 使用更便宜的模型 (如 DeepSeek, Kimi)
2. 实现智能缓存避免重复请求
3. 使用混合模型策略 (简单任务用轻量模型)

### 总成本估算

| 项目 | 成本 (月) |
|------|----------|
| 基础设施 | ¥6,250 |
| LLM API (GPT-4) | ¥1,260,000 |
| LLM API (DeepSeek) | ¥20,000 |
| 运维人力 | ¥30,000 |

**使用 DeepSeek 总计**: ~¥56,000/月

**使用 GPT-4 总计**: ~¥1,296,000/月

---

## 故障处理

### 高可用架构

#### 1. 数据库主从复制

```yaml
# PostgreSQL 主从配置
services:
  postgres-primary:
    image: postgres:16-alpine
    environment:
      - POSTGRES_REPLICATION_MODE=master
      - POSTGRES_REPLICATION_USER=replicator
      - POSTGRES_REPLICATION_PASSWORD=${REPL_PASSWORD}
    volumes:
      - postgres_primary_data:/var/lib/postgresql/data

  postgres-replica:
    image: postgres:16-alpine
    environment:
      - POSTGRES_REPLICATION_MODE=slave
      - POSTGRES_MASTER_HOST=postgres-primary
      - POSTGRES_REPLICATION_USER=replicator
      - POSTGRES_REPLICATION_PASSWORD=${REPL_PASSWORD}
    volumes:
      - postgres_replica_data:/var/lib/postgresql/data
```

#### 2. 自动故障转移

使用 Kubernetes 的 StatefulSet 和 Operator (如 Patroni):

```yaml
# k8s/postgres-ha.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres-ha
spec:
  serviceName: postgres
  replicas: 3
  selector:
    matchLabels:
      app: postgres
  template:
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        # 使用 Patroni 实现自动故障转移
```

#### 3. 备份策略

```bash
# 每日全量备份
0 2 * * * pg_dump -h postgres -U deerflow deerflow | gzip > /backup/deerflow-$(date +\%Y\%m\%d).sql.gz

# WAL 归档 (增量备份)
archive_mode = on
archive_command = 'cp %p /backup/wal_archive/%f'
```

---

## 安全加固

### 1. API 限流

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/chat")
@limiter.limit("10/minute")  # 每分钟最多10次
async def chat(request: Request):
    pass
```

### 2. 身份验证

```python
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    # 验证 JWT token
    if not verify_jwt(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return token
```

### 3. HTTPS 加密

```nginx
server {
    listen 443 ssl http2;
    server_name deerflow.example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # ... 其他配置
}
```

---

## 附录

### A. 压测脚本

见 `scripts/load_test.py`

### B. 数据迁移脚本

见 `scripts/migrate_sqlite_to_postgres.py`

### C. Redis 缓存模块

见 `src/cache/redis_cache.py`

### D. Grafana 仪表板

见 `monitoring/grafana/dashboards/deerflow-dashboard.json`

---

## 参考资料

- [LangGraph 文档](https://langchain-ai.github.io/langgraph/)
- [PostgreSQL 性能优化](https://www.postgresql.org/docs/current/performance-tips.html)
- [Nginx 负载均衡](https://docs.nginx.com/nginx/admin-guide/load-balancer/)
- [Docker Swarm 部署](https://docs.docker.com/engine/swarm/)
- [Kubernetes 最佳实践](https://kubernetes.io/docs/concepts/cluster-administration/)

---

**文档版本**: 1.0  
**最后更新**: 2026-03-23  
**维护者**: DeerFlow Team
