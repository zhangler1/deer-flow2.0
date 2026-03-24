# DeerFlow Kubernetes 部署指南

本文档详细说明如何在 Kubernetes 环境中部署 DeerFlow,支持从本地开发到生产环境的各种场景。

## 📋 目录

- [架构概览](#架构概览)
- [支持的 K8s 环境](#支持的-k8s-环境)
- [快速开始](#快速开始)
- [生产环境部署](#生产环境部署)
- [配置说明](#配置说明)
- [故障排查](#故障排查)

---

## 架构概览

DeerFlow 在 Kubernetes 中运行时,采用以下架构:

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                       │
│                                                             │
│  ┌──────────────┐                                          │
│  │   Ingress    │ ← HTTPS (外部访问)                      │
│  └──────┬───────┘                                          │
│         │                                                   │
│  ┌──────▼───────┐                                          │
│  │   Frontend   │ (Next.js, 3 replicas)                    │
│  │  Deployment  │                                          │
│  └──────────────┘                                          │
│                                                             │
│  ┌──────────────┐     ┌──────────────┐                    │
│  │   Gateway    │ ←─► │  LangGraph   │                    │
│  │  Deployment  │     │  Deployment  │                    │
│  │ (5 replicas) │     │ (5 replicas) │                    │
│  └──────┬───────┘     └──────┬───────┘                    │
│         │                    │                             │
│         └────────┬───────────┘                             │
│                  │                                         │
│         ┌────────▼─────────┐                              │
│         │   PostgreSQL     │                              │
│         │   StatefulSet    │                              │
│         └──────────────────┘                              │
│                  │                                         │
│         ┌────────▼─────────┐                              │
│         │   Redis          │                              │
│         │   Deployment     │                              │
│         └──────────────────┘                              │
│                                                             │
│  ┌──────────────────────────────────────────────┐         │
│  │        Sandbox Provisioner (可选)            │         │
│  │  动态创建和管理 Sandbox Pods                  │         │
│  └──────┬───────────────────────────────────────┘         │
│         │                                                  │
│  ┌──────▼───────┐  ┌──────────┐  ┌──────────┐           │
│  │  Sandbox-1   │  │Sandbox-2 │  │Sandbox-N │  ...      │
│  │  Pod         │  │Pod       │  │Pod       │           │
│  │ (动态创建)    │  │          │  │          │           │
│  └──────────────┘  └──────────┘  └──────────┘           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

1. **Frontend (Next.js)**: 用户界面,3个副本提供高可用
2. **Gateway (FastAPI)**: REST API 网关,5个副本处理请求
3. **LangGraph**: Agent 核心引擎,5个副本
4. **PostgreSQL**: 持久化存储 (StatefulSet)
5. **Redis**: 缓存和会话管理
6. **Provisioner** (可选): 动态管理沙箱 Pods

---

## 支持的 K8s 环境

DeerFlow 支持以下 Kubernetes 环境:

### ✅ 本地开发环境

| 环境 | 支持 | 说明 |
|------|------|------|
| **Docker Desktop** | ✅ | macOS/Windows,内置 K8s |
| **OrbStack** | ✅ | macOS,更轻量的 Docker Desktop 替代 |
| **minikube** | ✅ | 跨平台本地集群 |
| **kind** | ✅ | Kubernetes in Docker |
| **k3s** | ✅ | 轻量级 K8s 发行版 |

### ✅ 云服务商

| 环境 | 支持 | 说明 |
|------|------|------|
| **阿里云 ACK** | ✅ | 阿里云容器服务 Kubernetes |
| **腾讯云 TKE** | ✅ | 腾讯云容器服务 |
| **AWS EKS** | ✅ | Amazon Elastic Kubernetes Service |
| **Google GKE** | ✅ | Google Kubernetes Engine |
| **Azure AKS** | ✅ | Azure Kubernetes Service |

---

## 快速开始

### 方式一: 使用 Provisioner 模式 (推荐开发环境)

这种方式将 DeerFlow 主服务运行在 Docker Compose 中,沙箱运行在 Kubernetes 中。

#### 1. 启用 Kubernetes

**Docker Desktop**:
```bash
# macOS/Windows
1. 打开 Docker Desktop 设置
2. 进入 "Kubernetes" 标签
3. 勾选 "Enable Kubernetes"
4. 点击 "Apply & Restart"
```

**OrbStack**:
```bash
# macOS
1. 打开 OrbStack 设置
2. 进入 "Kubernetes" 标签
3. 勾选 "Enable Kubernetes"
```

**minikube**:
```bash
# 跨平台
minikube start --cpus=4 --memory=8192 --driver=docker
```

#### 2. 验证 K8s 集群

```bash
# 检查集群状态
kubectl cluster-info

# 查看节点
kubectl get nodes

# 确认 kubeconfig 路径
echo $KUBECONFIG  # 通常是 ~/.kube/config
```

#### 3. 配置 DeerFlow

编辑 `config.yaml`:

```yaml
sandbox:
  use: src.community.aio_sandbox:AioSandboxProvider
  provisioner_url: http://provisioner:8002  # 启用 Provisioner 模式
  
  # 沙箱配置
  replicas: 50  # 最大并发沙箱数
  image: enterprise-public-cn-beijing.cr.volces.com/vefaas-public/all-in-one-sandbox:latest
```

#### 4. 设置环境变量

```bash
# 设置项目根目录的绝对路径
export DEER_FLOW_ROOT=$(pwd)

# 验证
echo $DEER_FLOW_ROOT
```

#### 5. 启动服务

```bash
# 使用 Docker Compose 启动 (自动检测 Provisioner 模式)
make docker-start

# 或直接使用 docker-compose
docker-compose -f docker/docker-compose-dev.yaml --profile provisioner up -d
```

#### 6. 验证部署

```bash
# 检查 Docker 容器
docker ps | grep deer-flow

# 检查 Provisioner
curl http://localhost:8002/health

# 检查 K8s 命名空间
kubectl get ns deer-flow

# 查看沙箱 Pods (使用后会动态创建)
kubectl get pods -n deer-flow
```

#### 7. 测试沙箱创建

访问 http://localhost:2026,发送一条需要代码执行的消息,例如:

```
用 Python 打印 Hello World
```

然后查看 K8s 中的沙箱 Pod:

```bash
kubectl get pods -n deer-flow -w
```

你会看到类似这样的输出:

```
NAME                          READY   STATUS    RESTARTS   AGE
sandbox-abc123-xyz456         1/1     Running   0          5s
```

---

### 方式二: 完全 K8s 部署 (推荐生产环境)

将所有 DeerFlow 组件都部署到 Kubernetes 中。

#### 1. 准备 Kubernetes 清单文件

创建 `k8s/` 目录并添加以下文件:

```bash
mkdir -p k8s
cd k8s
```

#### 2. 创建命名空间

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: deer-flow
  labels:
    name: deer-flow
    app.kubernetes.io/name: deer-flow
```

应用:
```bash
kubectl apply -f k8s/namespace.yaml
```

#### 3. 部署 PostgreSQL

```yaml
# k8s/postgres.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: deer-flow
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
  storageClassName: standard  # 根据云服务商调整
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: deer-flow
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        env:
        - name: POSTGRES_DB
          value: deerflow
        - name: POSTGRES_USER
          value: deerflow
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: deer-flow-secrets
              key: db-password
        ports:
        - containerPort: 5432
          name: postgres
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            cpu: 1
            memory: 2Gi
          limits:
            cpu: 2
            memory: 4Gi
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 20Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: deer-flow
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  clusterIP: None  # Headless service for StatefulSet
```

应用:
```bash
# 首先创建密钥
kubectl create secret generic deer-flow-secrets \
  -n deer-flow \
  --from-literal=db-password=your-secure-password

# 部署 PostgreSQL
kubectl apply -f k8s/postgres.yaml

# 等待 Pod 就绪
kubectl wait --for=condition=ready pod -l app=postgres -n deer-flow --timeout=300s
```

#### 4. 部署 Redis

```yaml
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: deer-flow
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command:
        - redis-server
        - --appendonly
        - "yes"
        - --maxmemory
        - "2gb"
        - --maxmemory-policy
        - allkeys-lru
        ports:
        - containerPort: 6379
          name: redis
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1
            memory: 2Gi
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: deer-flow
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

应用:
```bash
kubectl apply -f k8s/redis.yaml
```

#### 5. 部署 Gateway

```yaml
# k8s/gateway.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway
  namespace: deer-flow
spec:
  replicas: 5
  selector:
    matchLabels:
      app: gateway
  template:
    metadata:
      labels:
        app: gateway
    spec:
      containers:
      - name: gateway
        image: deer-flow-backend:latest  # 替换为你的镜像
        command:
        - sh
        - -c
        - |
          cd backend && 
          uv run uvicorn src.gateway.app:app 
          --host 0.0.0.0 
          --port 8001 
          --workers 2
        env:
        - name: DATABASE_URL
          value: postgresql://deerflow:$(DB_PASSWORD)@postgres:5432/deerflow
        - name: REDIS_URL
          value: redis://redis:6379/0
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: deer-flow-secrets
              key: db-password
        envFrom:
        - configMapRef:
            name: deer-flow-config
        ports:
        - containerPort: 8001
          name: http
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          requests:
            cpu: 1
            memory: 2Gi
          limits:
            cpu: 2
            memory: 4Gi
---
apiVersion: v1
kind: Service
metadata:
  name: gateway
  namespace: deer-flow
spec:
  selector:
    app: gateway
  ports:
  - port: 8001
    targetPort: 8001
```

#### 6. 部署 LangGraph

```yaml
# k8s/langgraph.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: langgraph
  namespace: deer-flow
spec:
  replicas: 5
  selector:
    matchLabels:
      app: langgraph
  template:
    metadata:
      labels:
        app: langgraph
    spec:
      containers:
      - name: langgraph
        image: deer-flow-backend:latest
        command:
        - sh
        - -c
        - |
          cd backend && 
          uv run langgraph dev 
          --host 0.0.0.0 
          --port 2024 
          --no-browser
        env:
        - name: DATABASE_URL
          value: postgresql://deerflow:$(DB_PASSWORD)@postgres:5432/deerflow
        - name: REDIS_URL
          value: redis://redis:6379/1
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: deer-flow-secrets
              key: db-password
        envFrom:
        - configMapRef:
            name: deer-flow-config
        ports:
        - containerPort: 2024
          name: http
        resources:
          requests:
            cpu: 1
            memory: 2Gi
          limits:
            cpu: 2
            memory: 4Gi
---
apiVersion: v1
kind: Service
metadata:
  name: langgraph
  namespace: deer-flow
spec:
  selector:
    app: langgraph
  ports:
  - port: 2024
    targetPort: 2024
```

#### 7. 部署 Frontend

```yaml
# k8s/frontend.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: deer-flow
spec:
  replicas: 3
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
      - name: frontend
        image: deer-flow-frontend:latest
        command:
        - sh
        - -c
        - cd frontend && pnpm run start
        env:
        - name: NODE_ENV
          value: production
        - name: PORT
          value: "3000"
        ports:
        - containerPort: 3000
          name: http
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1
            memory: 2Gi
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: deer-flow
spec:
  selector:
    app: frontend
  ports:
  - port: 3000
    targetPort: 3000
```

#### 8. 配置 Ingress (外部访问)

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: deer-flow
  namespace: deer-flow
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod  # 自动 HTTPS
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
spec:
  tls:
  - hosts:
    - deerflow.yourdomain.com
    secretName: deer-flow-tls
  rules:
  - host: deerflow.yourdomain.com
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: gateway
            port:
              number: 8001
      - path: /threads
        pathType: Prefix
        backend:
          service:
            name: langgraph
            port:
              number: 2024
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend
            port:
              number: 3000
```

#### 9. 一键部署

```bash
# 按顺序部署所有组件
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/gateway.yaml
kubectl apply -f k8s/langgraph.yaml
kubectl apply -f k8s/frontend.yaml
kubectl apply -f k8s/ingress.yaml

# 查看所有资源
kubectl get all -n deer-flow

# 查看 Pod 日志
kubectl logs -f deployment/gateway -n deer-flow
kubectl logs -f deployment/langgraph -n deer-flow
```

---

## 配置说明

### ConfigMap 配置

创建 ConfigMap 存储配置:

```bash
# 从 config.yaml 创建 ConfigMap
kubectl create configmap deer-flow-config \
  -n deer-flow \
  --from-file=config.yaml=./config.yaml
```

### Secret 管理

```bash
# 创建 API 密钥
kubectl create secret generic deer-flow-api-keys \
  -n deer-flow \
  --from-literal=openai-key=sk-xxx \
  --from-literal=deepseek-key=sk-yyy \
  --from-literal=tavily-key=tvly-zzz
```

### 资源配额

为命名空间设置资源限制:

```yaml
# k8s/resource-quota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: deer-flow-quota
  namespace: deer-flow
spec:
  hard:
    requests.cpu: "50"
    requests.memory: 100Gi
    limits.cpu: "100"
    limits.memory: 200Gi
    pods: "200"
```

### 水平自动扩缩容 (HPA)

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: gateway-hpa
  namespace: deer-flow
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gateway
  minReplicas: 5
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

应用:
```bash
kubectl apply -f k8s/hpa.yaml
kubectl get hpa -n deer-flow
```

---

## 监控和日志

### Prometheus 监控

```yaml
# k8s/monitoring.yaml
apiVersion: v1
kind: ServiceMonitor
metadata:
  name: deer-flow
  namespace: deer-flow
spec:
  selector:
    matchLabels:
      app: gateway
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### 日志收集

使用 Fluent Bit 收集日志:

```bash
# 部署 Fluent Bit
kubectl apply -f https://raw.githubusercontent.com/fluent/fluent-bit-kubernetes-logging/master/fluent-bit-service-account.yaml
kubectl apply -f https://raw.githubusercontent.com/fluent/fluent-bit-kubernetes-logging/master/fluent-bit-role.yaml
kubectl apply -f https://raw.githubusercontent.com/fluent/fluent-bit-kubernetes-logging/master/fluent-bit-role-binding.yaml
kubectl apply -f https://raw.githubusercontent.com/fluent/fluent-bit-kubernetes-logging/master/output/elasticsearch/fluent-bit-configmap.yaml
kubectl apply -f https://raw.githubusercontent.com/fluent/fluent-bit-kubernetes-logging/master/output/elasticsearch/fluent-bit-ds.yaml
```

---

## 故障排查

### 常见问题

#### 1. Pod 无法启动

```bash
# 查看 Pod 状态
kubectl get pods -n deer-flow

# 查看详细信息
kubectl describe pod <pod-name> -n deer-flow

# 查看日志
kubectl logs <pod-name> -n deer-flow

# 进入容器调试
kubectl exec -it <pod-name> -n deer-flow -- /bin/sh
```

#### 2. 数据库连接失败

```bash
# 测试 PostgreSQL 连接
kubectl run -it --rm debug --image=postgres:16-alpine --restart=Never -n deer-flow -- \
  psql -h postgres -U deerflow -d deerflow

# 检查密钥
kubectl get secret deer-flow-secrets -n deer-flow -o yaml
```

#### 3. Provisioner 无法创建沙箱

```bash
# 检查 Provisioner 日志
kubectl logs -f deployment/provisioner -n deer-flow

# 检查 Provisioner 健康状态
curl http://<provisioner-service>:8002/health

# 列出所有沙箱
kubectl get pods -n deer-flow -l app=deer-flow-sandbox
```

#### 4. 性能问题

```bash
# 查看资源使用
kubectl top pods -n deer-flow
kubectl top nodes

# 查看 HPA 状态
kubectl get hpa -n deer-flow

# 查看事件
kubectl get events -n deer-flow --sort-by='.lastTimestamp'
```

### 调试技巧

```bash
# 端口转发到本地
kubectl port-forward svc/gateway 8001:8001 -n deer-flow
kubectl port-forward svc/postgres 5432:5432 -n deer-flow

# 查看所有资源
kubectl get all,cm,secret,pvc -n deer-flow

# 删除所有资源
kubectl delete namespace deer-flow
```

---

## 生产环境最佳实践

### 1. 高可用部署

- ✅ 使用 StatefulSet 部署 PostgreSQL (或使用云数据库)
- ✅ 启用 HPA 自动扩缩容
- ✅ 配置 Pod Disruption Budget
- ✅ 使用多可用区部署

### 2. 安全加固

```yaml
# 网络策略示例
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-all-ingress
  namespace: deer-flow
spec:
  podSelector: {}
  policyTypes:
  - Ingress
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-frontend-to-gateway
  namespace: deer-flow
spec:
  podSelector:
    matchLabels:
      app: gateway
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: frontend
```

### 3. 备份策略

```bash
# 备份 PostgreSQL
kubectl exec -it postgres-0 -n deer-flow -- \
  pg_dump -U deerflow deerflow | gzip > backup-$(date +%Y%m%d).sql.gz

# 恢复
gunzip < backup-20260323.sql.gz | \
  kubectl exec -i postgres-0 -n deer-flow -- \
  psql -U deerflow deerflow
```

### 4. 成本优化

- 使用 Spot/Preemptible 实例运行非关键 Pods
- 配置资源请求和限制
- 启用集群自动缩放
- 使用 PVC 动态供应

---

## 参考资料

- [Kubernetes 官方文档](https://kubernetes.io/docs/)
- [Helm Charts (DeerFlow)](../helm/)
- [Docker Compose 开发环境](docker-compose-dev.yaml)
- [Provisioner 文档](../docker/provisioner/README.md)

---

**文档版本**: 1.0  
**最后更新**: 2026-03-23  
**维护者**: DeerFlow Team
