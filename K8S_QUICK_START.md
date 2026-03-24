# DeerFlow Kubernetes 快速开始 🚀

本文档提供 DeerFlow 在 Kubernetes 环境中的快速启动指南。

---

## 📋 前置条件

- ✅ Kubernetes 集群 (Docker Desktop / OrbStack / minikube / 云服务)
- ✅ kubectl 已安装并配置
- ✅ 至少 8GB 可用内存
- ✅ 至少 4 CPU 核心

---

## 🎯 三种部署模式

### 模式 1: Provisioner 模式 (推荐开发)

**主服务在 Docker Compose,沙箱在 K8s**

```bash
# 1. 启用 Kubernetes (Docker Desktop / OrbStack)
# 参见: Settings → Kubernetes → Enable Kubernetes

# 2. 验证集群
kubectl cluster-info

# 3. 配置 DeerFlow
cat > config.yaml << 'EOF'
sandbox:
  use: src.community.aio_sandbox:AioSandboxProvider
  provisioner_url: http://provisioner:8002
  replicas: 50
EOF

# 4. 设置环境变量
export DEER_FLOW_ROOT=$(pwd)

# 5. 启动服务
make docker-start

# 6. 访问
open http://localhost:2026
```

**验证部署**:
```bash
# 检查 Provisioner
curl http://localhost:8002/health

# 查看沙箱 (发送消息后)
kubectl get pods -n deer-flow -w
```

---

### 模式 2: 完全 K8s 部署 (推荐生产)

**所有组件都在 Kubernetes**

```bash
# 1. 创建命名空间
kubectl create namespace deer-flow

# 2. 创建密钥
kubectl create secret generic deer-flow-secrets \
  -n deer-flow \
  --from-literal=db-password=your-secure-password \
  --from-literal=openai-key=sk-xxx \
  --from-literal=deepseek-key=sk-yyy

# 3. 部署数据层
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml

# 4. 等待数据库就绪
kubectl wait --for=condition=ready pod -l app=postgres -n deer-flow --timeout=300s

# 5. 部署应用层
kubectl apply -f k8s/gateway.yaml
kubectl apply -f k8s/langgraph.yaml
kubectl apply -f k8s/frontend.yaml

# 6. 配置 Ingress
kubectl apply -f k8s/ingress.yaml

# 7. 查看状态
kubectl get all -n deer-flow
```

---

### 模式 3: Helm 部署 (最简单)

```bash
# 1. 添加 Helm 仓库
helm repo add deer-flow https://charts.deerflow.io
helm repo update

# 2. 安装
helm install deer-flow deer-flow/deer-flow \
  --namespace deer-flow \
  --create-namespace \
  --set postgresql.auth.password=your-password \
  --set ingress.enabled=true \
  --set ingress.hosts[0].host=deerflow.yourdomain.com

# 3. 查看状态
helm status deer-flow -n deer-flow

# 4. 升级
helm upgrade deer-flow deer-flow/deer-flow \
  --namespace deer-flow \
  --reuse-values \
  --set replicas.gateway=10

# 5. 卸载
helm uninstall deer-flow -n deer-flow
```

---

## 🔧 常用命令

### 查看资源

```bash
# 所有资源
kubectl get all -n deer-flow

# Pod 详情
kubectl describe pod <pod-name> -n deer-flow

# 日志
kubectl logs -f deployment/gateway -n deer-flow
kubectl logs -f deployment/langgraph -n deer-flow

# 资源使用
kubectl top pods -n deer-flow
kubectl top nodes
```

### 调试

```bash
# 进入容器
kubectl exec -it <pod-name> -n deer-flow -- /bin/sh

# 端口转发
kubectl port-forward svc/gateway 8001:8001 -n deer-flow
kubectl port-forward svc/postgres 5432:5432 -n deer-flow

# 查看事件
kubectl get events -n deer-flow --sort-by='.lastTimestamp'
```

### 扩缩容

```bash
# 手动扩容
kubectl scale deployment gateway --replicas=10 -n deer-flow
kubectl scale deployment langgraph --replicas=10 -n deer-flow

# 自动扩容 (HPA)
kubectl autoscale deployment gateway \
  --cpu-percent=70 \
  --min=5 \
  --max=20 \
  -n deer-flow

# 查看 HPA
kubectl get hpa -n deer-flow
```

### 备份和恢复

```bash
# 备份数据库
kubectl exec -it postgres-0 -n deer-flow -- \
  pg_dump -U deerflow deerflow | gzip > backup-$(date +%Y%m%d).sql.gz

# 恢复数据库
gunzip < backup-20260323.sql.gz | \
  kubectl exec -i postgres-0 -n deer-flow -- \
  psql -U deerflow deerflow

# 备份配置
kubectl get cm,secret -n deer-flow -o yaml > config-backup.yaml
```

---

## 📊 监控指标

### Prometheus 查询

```promql
# QPS
sum(rate(http_requests_total[5m]))

# 响应时间 P95
histogram_quantile(0.95, sum(rate(http_response_time_seconds_bucket[5m])) by (le))

# 错误率
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# Pod CPU 使用率
sum(rate(container_cpu_usage_seconds_total{namespace="deer-flow"}[5m])) by (pod)

# Pod 内存使用
sum(container_memory_usage_bytes{namespace="deer-flow"}) by (pod)
```

### Grafana 仪表板

访问: http://localhost:3001 (默认密码: admin/admin)

导入仪表板:
- DeerFlow Overview: `monitoring/grafana/dashboards/overview.json`
- Kubernetes Cluster: Dashboard ID 315
- PostgreSQL: Dashboard ID 9628

---

## 🛠 故障排查

### Pod 无法启动

```bash
# 1. 检查 Pod 状态
kubectl get pods -n deer-flow

# 2. 查看详细信息
kubectl describe pod <pod-name> -n deer-flow

# 3. 查看日志
kubectl logs <pod-name> -n deer-flow --previous  # 上一次运行的日志

# 4. 常见原因
# - 镜像拉取失败: 检查 imagePullPolicy
# - 资源不足: 检查节点资源 (kubectl describe nodes)
# - 配置错误: 检查 ConfigMap/Secret
# - 依赖未就绪: 检查数据库连接
```

### 数据库连接失败

```bash
# 测试连接
kubectl run -it --rm debug --image=postgres:16-alpine --restart=Never -n deer-flow -- \
  psql -h postgres -U deerflow -d deerflow -W

# 检查服务
kubectl get svc postgres -n deer-flow

# 检查密钥
kubectl get secret deer-flow-secrets -n deer-flow -o jsonpath='{.data.db-password}' | base64 -d
```

### 沙箱创建失败

```bash
# 检查 Provisioner
kubectl logs -f deployment/provisioner -n deer-flow

# 检查沙箱 Pods
kubectl get pods -n deer-flow -l app=deer-flow-sandbox

# 检查资源配额
kubectl describe resourcequota -n deer-flow

# 手动测试沙箱创建
curl -X POST http://provisioner:8002/api/sandboxes \
  -H "Content-Type: application/json" \
  -d '{"sandbox_id":"test-123","thread_id":"thread-456"}'
```

### 性能问题

```bash
# 查看资源使用
kubectl top pods -n deer-flow
kubectl top nodes

# 检查 HPA
kubectl get hpa -n deer-flow
kubectl describe hpa gateway-hpa -n deer-flow

# 查看限流
kubectl logs -f deployment/gateway -n deer-flow | grep -i "rate limit"

# 数据库连接池
kubectl exec -it postgres-0 -n deer-flow -- \
  psql -U deerflow -c "SELECT count(*) FROM pg_stat_activity;"
```

---

## 🌐 云服务商特定配置

### 阿里云 ACK

```bash
# 使用阿里云 LoadBalancer
kubectl annotate svc frontend \
  service.beta.kubernetes.io/alibaba-cloud-loadbalancer-spec="slb.s1.small" \
  -n deer-flow

# 使用云盘 PVC
kubectl patch storageclass alicloud-disk-ssd -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

### 腾讯云 TKE

```bash
# 使用腾讯云 LoadBalancer
kubectl annotate svc frontend \
  service.kubernetes.io/qcloud-loadbalancer-internal-subnetid=subnet-xxxxx \
  -n deer-flow
```

### AWS EKS

```bash
# 使用 ELB
kubectl annotate svc frontend \
  service.beta.kubernetes.io/aws-load-balancer-type="nlb" \
  -n deer-flow

# 使用 EBS PVC
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/aws-ebs-csi-driver/master/deploy/kubernetes/overlays/stable/ecr/kustomization.yaml
```

---

## 📚 更多文档

- [完整 Kubernetes 部署指南](backend/docs/KUBERNETES.md)
- [扩展到1万用户](backend/docs/SCALING.md)
- [配置参考](backend/docs/CONFIGURATION.md)
- [Provisioner 文档](docker/provisioner/README.md)

---

## 💡 最佳实践

### 开发环境

- ✅ 使用 Provisioner 模式 (Docker Compose + K8s 沙箱)
- ✅ 启用热重载 (`make dev`)
- ✅ 使用 SQLite 或本地 PostgreSQL
- ✅ 单实例部署

### 生产环境

- ✅ 完全 K8s 部署
- ✅ 使用云数据库 (RDS/Cloud SQL)
- ✅ 启用 HPA 自动扩缩容
- ✅ 配置 Ingress + TLS
- ✅ 多副本高可用
- ✅ 配置资源限制
- ✅ 启用监控和告警
- ✅ 定期备份

---

## 🆘 获取帮助

- GitHub Issues: https://github.com/deer-flow/deer-flow/issues
- 文档: https://docs.deerflow.io
- 社区讨论: https://discord.gg/deerflow

---

**快速开始版本**: 1.0  
**最后更新**: 2026-03-23
