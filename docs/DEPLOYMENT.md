# Deployment Guide - Temporal Framework

This guide provides comprehensive instructions for deploying the Temporal Framework in various environments, from development to production.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Local Development Setup](#local-development-setup)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Deployments](#cloud-deployments)
- [Monitoring & Observability](#monitoring--observability)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### Required Infrastructure

- **Python 3.12+** runtime environment
- **Neo4j Database 5.0+** (local, cloud, or containerized)
- **Redis** (optional, for caching and session storage)
- **Container Runtime** (Docker/Podman for containerized deployments)
- **Kubernetes Cluster** (for K8s deployments)

### Development Tools

- **UV Package Manager** (recommended) or pip
- **Git** for version control
- **Docker** for containerization
- **kubectl** for Kubernetes deployments
- **Helm** (optional, for Kubernetes package management)

## ⚙️ Environment Configuration

### Environment Variables

Create environment-specific configuration files:

#### Development (`.env.development`)

```env
# Application Settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Database Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=dev_password
NEO4J_DATABASE=neo4j

# Optional: Graphiti Configuration
GRAPHITI_SERVER_URL=http://localhost:8000
GRAPHITI_API_KEY=dev_api_key

# Logging Configuration
AUDIT_LOG_ENABLED=true
SECURITY_LOG_ENABLED=true
LOG_FILE_PATH=logs/

# Performance Settings
CACHE_ENABLED=true
CACHE_TTL_SECONDS=300
MAX_CONCURRENT_EVALUATIONS=50

# Framework Settings
EMERGENCY_OVERRIDE_ENABLED=true
DEFAULT_TIMEZONE=UTC
MAX_CONTEXT_AGE_HOURS=24
```

#### Staging (`.env.staging`)

```env
# Application Settings
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO

# Database Configuration
NEO4J_URI=bolt://staging-neo4j.company.com:7687
NEO4J_USER=staging_user
NEO4J_PASSWORD=${NEO4J_STAGING_PASSWORD}
NEO4J_DATABASE=temporal_staging

# Graphiti Configuration
GRAPHITI_SERVER_URL=https://staging-graphiti.company.com
GRAPHITI_API_KEY=${GRAPHITI_STAGING_API_KEY}

# Logging Configuration
AUDIT_LOG_ENABLED=true
SECURITY_LOG_ENABLED=true
LOG_FILE_PATH=/var/log/temporal-framework/

# Performance Settings
CACHE_ENABLED=true
CACHE_TTL_SECONDS=600
MAX_CONCURRENT_EVALUATIONS=100

# Framework Settings
EMERGENCY_OVERRIDE_ENABLED=true
DEFAULT_TIMEZONE=UTC
MAX_CONTEXT_AGE_HOURS=12
```

#### Production (`.env.production`)

```env
# Application Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Database Configuration
NEO4J_URI=bolt+s://prod-neo4j.company.com:7687
NEO4J_USER=prod_user
NEO4J_PASSWORD=${NEO4J_PROD_PASSWORD}
NEO4J_DATABASE=temporal_production

# Graphiti Configuration
GRAPHITI_SERVER_URL=https://api.graphiti.company.com
GRAPHITI_API_KEY=${GRAPHITI_PROD_API_KEY}

# Logging Configuration
AUDIT_LOG_ENABLED=true
SECURITY_LOG_ENABLED=true
LOG_FILE_PATH=/var/log/temporal-framework/

# Performance Settings
CACHE_ENABLED=true
CACHE_TTL_SECONDS=900
MAX_CONCURRENT_EVALUATIONS=200

# Security Settings
EMERGENCY_OVERRIDE_ENABLED=true
DEFAULT_TIMEZONE=UTC
MAX_CONTEXT_AGE_HOURS=6

# Monitoring
PROMETHEUS_METRICS_ENABLED=true
JAEGER_TRACING_ENABLED=true
```

## 🏠 Local Development Setup

### Quick Start

```bash
# Clone repository
git clone https://github.com/Mehraayisha/temporal-framework.git
cd temporal-framework

# Set up development environment
cp .env.development .env
uv sync --dev

# Start Neo4j (Docker method)
docker run --name neo4j-dev \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/dev_password \
  -e NEO4J_PLUGINS='["apoc"]' \
  -d neo4j:5.0

# Verify setup
uv run python examples/team_onboarding_demo.py
```

### Development with Docker Compose

Create `docker-compose.dev.yml`:

```yaml
version: '3.8'

services:
  temporal-framework:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    environment:
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=dev_password
    volumes:
      - .:/app
      - /app/.venv
    depends_on:
      neo4j:
        condition: service_healthy
    command: uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  neo4j:
    image: neo4j:5.0
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/dev_password
      - NEO4J_PLUGINS=["apoc"]
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "dev_password", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  neo4j_data:
```

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f temporal-framework
```

## 🐳 Docker Deployment

### Single Container Deployment

```bash
# Build image
docker build -t temporal-framework:latest .

# Run container
docker run -d \
  --name temporal-framework \
  -p 8000:8000 \
  -e NEO4J_URI=bolt://host.docker.internal:7687 \
  -e NEO4J_USER=neo4j \
  -e NEO4J_PASSWORD=password \
  --restart unless-stopped \
  temporal-framework:latest
```

### Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  temporal-framework:
    image: temporal-framework:latest
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD_FILE=/run/secrets/neo4j_password
    secrets:
      - neo4j_password
    volumes:
      - logs:/var/log/temporal-framework
    depends_on:
      neo4j:
        condition: service_healthy
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

  neo4j:
    image: neo4j:5.0-enterprise
    ports:
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=1G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "${NEO4J_PASSWORD}", "RETURN 1"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

secrets:
  neo4j_password:
    external: true

volumes:
  neo4j_data:
  neo4j_logs:
  redis_data:
  logs:
```

```bash
# Deploy production stack
docker stack deploy -c docker-compose.prod.yml temporal-framework-stack
```

## ☸️ Kubernetes Deployment

### Basic Deployment

Create Kubernetes manifests:

#### ConfigMap (`k8s/configmap.yaml`)

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: temporal-framework-config
  namespace: temporal-framework
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  CACHE_ENABLED: "true"
  CACHE_TTL_SECONDS: "900"
  DEFAULT_TIMEZONE: "UTC"
  MAX_CONTEXT_AGE_HOURS: "6"
```

#### Secret (`k8s/secret.yaml`)

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: temporal-framework-secrets
  namespace: temporal-framework
type: Opaque
data:
  NEO4J_PASSWORD: <base64-encoded-password>
  GRAPHITI_API_KEY: <base64-encoded-api-key>
```

#### Deployment (`k8s/deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: temporal-framework
  namespace: temporal-framework
  labels:
    app: temporal-framework
spec:
  replicas: 3
  selector:
    matchLabels:
      app: temporal-framework
  template:
    metadata:
      labels:
        app: temporal-framework
    spec:
      containers:
      - name: temporal-framework
        image: temporal-framework:latest
        ports:
        - containerPort: 8000
        env:
        - name: NEO4J_URI
          value: "bolt://neo4j-service:7687"
        - name: NEO4J_USER
          value: "neo4j"
        - name: NEO4J_PASSWORD
          valueFrom:
            secretKeyRef:
              name: temporal-framework-secrets
              key: NEO4J_PASSWORD
        envFrom:
        - configMapRef:
            name: temporal-framework-config
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

#### Service (`k8s/service.yaml`)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: temporal-framework-service
  namespace: temporal-framework
spec:
  selector:
    app: temporal-framework
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
```

#### Ingress (`k8s/ingress.yaml`)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: temporal-framework-ingress
  namespace: temporal-framework
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - api.temporal-framework.company.com
    secretName: temporal-framework-tls
  rules:
  - host: api.temporal-framework.company.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: temporal-framework-service
            port:
              number: 80
```

#### Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace temporal-framework

# Apply manifests
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n temporal-framework
kubectl logs -f deployment/temporal-framework -n temporal-framework
```

### Helm Chart Deployment

Create Helm chart structure:

```bash
temporal-framework/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   └── secret.yaml
```

#### values.yaml

```yaml
replicaCount: 3

image:
  repository: temporal-framework
  tag: "latest"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: api.temporal-framework.company.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: temporal-framework-tls
      hosts:
        - api.temporal-framework.company.com

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 250m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

config:
  environment: production
  logLevel: INFO
  cacheEnabled: true
  cacheTtlSeconds: 900

neo4j:
  uri: "bolt://neo4j-service:7687"
  user: "neo4j"
  password: "changeme"

graphiti:
  serverUrl: "https://api.graphiti.company.com"
  apiKey: "your-api-key"
```

#### Deploy with Helm

```bash
# Package chart
helm package temporal-framework/

# Install
helm install temporal-framework temporal-framework-1.0.0.tgz \
  --namespace temporal-framework \
  --create-namespace \
  --values production-values.yaml

# Upgrade
helm upgrade temporal-framework temporal-framework-1.0.0.tgz \
  --namespace temporal-framework \
  --values production-values.yaml
```

## ☁️ Cloud Deployments

### AWS EKS Deployment

```bash
# Create EKS cluster
eksctl create cluster \
  --name temporal-framework \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type m5.large \
  --nodes 3 \
  --nodes-min 1 \
  --nodes-max 4

# Deploy application
kubectl apply -f k8s/
```

### Google GKE Deployment

```bash
# Create GKE cluster
gcloud container clusters create temporal-framework \
  --zone us-central1-a \
  --num-nodes 3 \
  --enable-autoscaling \
  --min-nodes 1 \
  --max-nodes 10

# Deploy application
kubectl apply -f k8s/
```

### Azure AKS Deployment

```bash
# Create AKS cluster
az aks create \
  --resource-group temporal-framework-rg \
  --name temporal-framework \
  --node-count 3 \
  --enable-addons monitoring \
  --generate-ssh-keys

# Deploy application
kubectl apply -f k8s/
```

## 📊 Monitoring & Observability

### Prometheus Metrics

Add to your deployment:

```yaml
# prometheus-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
    scrape_configs:
    - job_name: 'temporal-framework'
      static_configs:
      - targets: ['temporal-framework-service:80']
      metrics_path: /metrics
```

### Grafana Dashboard

Key metrics to monitor:

- Request rate and response time
- Policy evaluation performance
- Cache hit rates
- Database connection health
- Error rates by endpoint
- Memory and CPU usage

### Logging Configuration

```yaml
# fluentd-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluentd-config
data:
  fluent.conf: |
    <source>
      @type tail
      path /var/log/temporal-framework/*.log
      pos_file /var/log/fluentd-temporal.log.pos
      tag temporal-framework.*
      format json
    </source>
    
    <match temporal-framework.**>
      @type elasticsearch
      host elasticsearch.logging.svc.cluster.local
      port 9200
      index_name temporal-framework
    </match>
```

## 🔒 Security Considerations

### Network Security

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: temporal-framework-netpol
spec:
  podSelector:
    matchLabels:
      app: temporal-framework
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: neo4j
    ports:
    - protocol: TCP
      port: 7687
```

### Pod Security Policy

```yaml
# pod-security-policy.yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: temporal-framework-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

### Secret Management

```bash
# Using Kubernetes secrets
kubectl create secret generic temporal-framework-secrets \
  --from-literal=neo4j-password=your-secure-password \
  --from-literal=graphiti-api-key=your-api-key

# Using sealed secrets (recommended)
echo -n your-password | kubectl create secret generic temporal-framework-secrets \
  --dry-run=client --from-file=neo4j-password=/dev/stdin -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Neo4j Connection Issues

```bash
# Check Neo4j connectivity
kubectl exec -it deployment/temporal-framework -- \
  python -c "from core.neo4j_manager import TemporalNeo4jManager; \
  mgr = TemporalNeo4jManager('bolt://neo4j:7687', 'neo4j', 'password'); \
  print('Connected' if mgr.health_check() else 'Failed')"
```

#### 2. Performance Issues

```bash
# Check resource usage
kubectl top pods -n temporal-framework

# Check logs for performance metrics
kubectl logs -f deployment/temporal-framework -n temporal-framework | grep "processing_time"
```

#### 3. Memory Leaks

```bash
# Monitor memory usage over time
kubectl exec -it deployment/temporal-framework -- \
  python -c "import psutil; print(f'Memory: {psutil.virtual_memory().percent}%')"
```

### Health Check Endpoints

```bash
# Application health
curl -f http://api.temporal-framework.company.com/health

# Detailed metrics
curl http://api.temporal-framework.company.com/metrics

# Component status
curl http://api.temporal-framework.company.com/status
```

### Log Analysis

```bash
# View application logs
kubectl logs -f deployment/temporal-framework -n temporal-framework

# Search for errors
kubectl logs deployment/temporal-framework -n temporal-framework | grep ERROR

# Audit logs
kubectl logs deployment/temporal-framework -n temporal-framework | grep AUDIT
```

## 📈 Scaling & Performance

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: temporal-framework-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: temporal-framework
  minReplicas: 2
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

### Performance Tuning

```yaml
# High-performance configuration
env:
- name: CACHE_ENABLED
  value: "true"
- name: CACHE_TTL_SECONDS
  value: "1800"
- name: MAX_CONCURRENT_EVALUATIONS
  value: "500"
- name: WORKER_PROCESSES
  value: "4"
- name: WORKER_CONNECTIONS
  value: "1000"
```

---

This deployment guide provides comprehensive instructions for deploying the Temporal Framework across various environments. Choose the deployment method that best fits your infrastructure and requirements.

For additional support, refer to the [troubleshooting section](#troubleshooting) or create an issue in the GitHub repository.