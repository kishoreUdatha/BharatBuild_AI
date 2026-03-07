#!/usr/bin/env python3
"""
Generate Microservices Architecture Training Examples

Covers:
1. Multi-service architectures (5+ services)
2. Docker Compose setups
3. Kubernetes manifests (Deployments, Services, Ingress, ConfigMaps)
4. gRPC service definitions
5. Event-driven architecture (Kafka, RabbitMQ)
6. API Gateway patterns
7. Service discovery
8. Circuit breaker patterns
"""

import json
import random
from pathlib import Path
from typing import List, Dict

OUTPUT_DIR = Path(__file__).parent / "microservices_data"


# ============================================================================
# MICROSERVICES DOMAINS
# ============================================================================

DOMAINS = {
    "ecommerce": {
        "name": "E-Commerce Platform",
        "services": ["user-service", "product-service", "order-service", "payment-service", "inventory-service", "notification-service", "cart-service", "review-service"],
        "events": ["UserRegistered", "OrderCreated", "PaymentProcessed", "InventoryUpdated", "OrderShipped"],
        "entities": {
            "user-service": ["User", "Address", "Profile"],
            "product-service": ["Product", "Category", "Brand"],
            "order-service": ["Order", "OrderItem", "OrderStatus"],
            "payment-service": ["Payment", "Transaction", "Refund"],
            "inventory-service": ["Stock", "Warehouse", "StockMovement"],
        }
    },
    "fintech": {
        "name": "FinTech Banking Platform",
        "services": ["account-service", "transaction-service", "payment-service", "notification-service", "audit-service", "fraud-detection-service", "kyc-service", "loan-service"],
        "events": ["AccountCreated", "TransactionProcessed", "FraudDetected", "KYCVerified", "LoanApproved"],
        "entities": {
            "account-service": ["Account", "AccountHolder", "Balance"],
            "transaction-service": ["Transaction", "Transfer", "Statement"],
            "payment-service": ["Payment", "Beneficiary", "PaymentMethod"],
            "fraud-detection-service": ["FraudAlert", "RiskScore", "Pattern"],
        }
    },
    "healthcare": {
        "name": "Healthcare Management System",
        "services": ["patient-service", "appointment-service", "doctor-service", "prescription-service", "billing-service", "notification-service", "lab-service", "pharmacy-service"],
        "events": ["PatientRegistered", "AppointmentBooked", "PrescriptionCreated", "LabResultReady", "BillGenerated"],
        "entities": {
            "patient-service": ["Patient", "MedicalHistory", "Insurance"],
            "appointment-service": ["Appointment", "TimeSlot", "Consultation"],
            "doctor-service": ["Doctor", "Specialty", "Schedule"],
            "prescription-service": ["Prescription", "Medication", "Dosage"],
        }
    },
    "logistics": {
        "name": "Logistics & Delivery Platform",
        "services": ["shipment-service", "tracking-service", "warehouse-service", "driver-service", "route-service", "notification-service", "billing-service", "analytics-service"],
        "events": ["ShipmentCreated", "PackageScanned", "DeliveryCompleted", "RouteOptimized", "DriverAssigned"],
        "entities": {
            "shipment-service": ["Shipment", "Package", "Sender", "Receiver"],
            "tracking-service": ["TrackingEvent", "Location", "Status"],
            "warehouse-service": ["Warehouse", "Inventory", "Zone"],
            "driver-service": ["Driver", "Vehicle", "Assignment"],
        }
    },
    "social_media": {
        "name": "Social Media Platform",
        "services": ["user-service", "post-service", "feed-service", "notification-service", "messaging-service", "media-service", "search-service", "analytics-service"],
        "events": ["UserFollowed", "PostCreated", "PostLiked", "CommentAdded", "MessageSent"],
        "entities": {
            "user-service": ["User", "Profile", "Follower"],
            "post-service": ["Post", "Comment", "Like", "Share"],
            "feed-service": ["Feed", "FeedItem", "Timeline"],
            "messaging-service": ["Message", "Conversation", "Attachment"],
        }
    },
    "iot_platform": {
        "name": "IoT Device Management Platform",
        "services": ["device-service", "telemetry-service", "alert-service", "command-service", "firmware-service", "analytics-service", "user-service", "notification-service"],
        "events": ["DeviceRegistered", "TelemetryReceived", "AlertTriggered", "FirmwareUpdated", "CommandExecuted"],
        "entities": {
            "device-service": ["Device", "DeviceType", "DeviceGroup"],
            "telemetry-service": ["Telemetry", "Metric", "TimeSeries"],
            "alert-service": ["Alert", "Rule", "Threshold"],
            "command-service": ["Command", "CommandHistory", "Response"],
        }
    },
}


# ============================================================================
# DOCKER COMPOSE GENERATOR
# ============================================================================

def generate_docker_compose_example(domain_key: str) -> Dict:
    domain = DOMAINS[domain_key]
    services = domain["services"][:6]  # Use 6 services

    prompt = f"Create a complete Docker Compose setup for a {domain['name']} microservices architecture with the following services: {', '.join(services)}. Include API Gateway, message broker, and databases."

    docker_compose = f"""I'll create a complete Docker Compose microservices setup for the {domain['name']}.

## Project Structure

```
{domain_key}-microservices/
├── docker-compose.yml
├── docker-compose.override.yml
├── .env
├── api-gateway/
│   ├── Dockerfile
│   ├── nginx.conf
│   └── conf.d/
│       └── default.conf
├── {services[0]}/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── models.py
│       ├── schemas.py
│       ├── routes.py
│       └── events.py
├── {services[1]}/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       └── ...
├── {services[2]}/
│   └── ...
├── {services[3]}/
│   └── ...
├── {services[4]}/
│   └── ...
└── {services[5]}/
    └── ...
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  # ===========================================
  # INFRASTRUCTURE
  # ===========================================

  api-gateway:
    build: ./api-gateway
    ports:
      - "80:80"
      - "443:443"
    depends_on:
      - {services[0]}
      - {services[1]}
      - {services[2]}
    networks:
      - {domain_key}-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  rabbitmq:
    image: rabbitmq:3-management-alpine
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: ${{RABBITMQ_PASSWORD}}
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    networks:
      - {domain_key}-network
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "check_running"]
      interval: 30s
      timeout: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - {domain_key}-network
    command: redis-server --appendonly yes

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${{POSTGRES_USER}}
      POSTGRES_PASSWORD: ${{POSTGRES_PASSWORD}}
      POSTGRES_MULTIPLE_DATABASES: {','.join([s.replace('-', '_') + '_db' for s in services[:4]])}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-multiple-dbs.sh:/docker-entrypoint-initdb.d/init-multiple-dbs.sh
    ports:
      - "5432:5432"
    networks:
      - {domain_key}-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${{POSTGRES_USER}}"]
      interval: 10s
      timeout: 5s
      retries: 5

  mongodb:
    image: mongo:6
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${{MONGO_USER}}
      MONGO_INITDB_ROOT_PASSWORD: ${{MONGO_PASSWORD}}
    volumes:
      - mongodb_data:/data/db
    ports:
      - "27017:27017"
    networks:
      - {domain_key}-network

  # ===========================================
  # MICROSERVICES
  # ===========================================

  {services[0]}:
    build: ./{services[0]}
    environment:
      - DATABASE_URL=postgresql://${{POSTGRES_USER}}:${{POSTGRES_PASSWORD}}@postgres:5432/{services[0].replace('-', '_')}_db
      - RABBITMQ_URL=amqp://admin:${{RABBITMQ_PASSWORD}}@rabbitmq:5672
      - REDIS_URL=redis://redis:6379/0
      - SERVICE_NAME={services[0]}
      - LOG_LEVEL=INFO
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
      redis:
        condition: service_started
    networks:
      - {domain_key}-network
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  {services[1]}:
    build: ./{services[1]}
    environment:
      - DATABASE_URL=postgresql://${{POSTGRES_USER}}:${{POSTGRES_PASSWORD}}@postgres:5432/{services[1].replace('-', '_')}_db
      - RABBITMQ_URL=amqp://admin:${{RABBITMQ_PASSWORD}}@rabbitmq:5672
      - REDIS_URL=redis://redis:6379/1
      - SERVICE_NAME={services[1]}
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    networks:
      - {domain_key}-network
    deploy:
      replicas: 2

  {services[2]}:
    build: ./{services[2]}
    environment:
      - DATABASE_URL=postgresql://${{POSTGRES_USER}}:${{POSTGRES_PASSWORD}}@postgres:5432/{services[2].replace('-', '_')}_db
      - RABBITMQ_URL=amqp://admin:${{RABBITMQ_PASSWORD}}@rabbitmq:5672
      - REDIS_URL=redis://redis:6379/2
      - {services[0].upper().replace('-', '_')}_URL=http://{services[0]}:8000
      - {services[1].upper().replace('-', '_')}_URL=http://{services[1]}:8000
    depends_on:
      - {services[0]}
      - {services[1]}
    networks:
      - {domain_key}-network

  {services[3]}:
    build: ./{services[3]}
    environment:
      - DATABASE_URL=postgresql://${{POSTGRES_USER}}:${{POSTGRES_PASSWORD}}@postgres:5432/{services[3].replace('-', '_')}_db
      - RABBITMQ_URL=amqp://admin:${{RABBITMQ_PASSWORD}}@rabbitmq:5672
      - STRIPE_SECRET_KEY=${{STRIPE_SECRET_KEY}}
    depends_on:
      - rabbitmq
      - postgres
    networks:
      - {domain_key}-network

  {services[4]}:
    build: ./{services[4]}
    environment:
      - MONGODB_URL=mongodb://${{MONGO_USER}}:${{MONGO_PASSWORD}}@mongodb:27017
      - RABBITMQ_URL=amqp://admin:${{RABBITMQ_PASSWORD}}@rabbitmq:5672
      - REDIS_URL=redis://redis:6379/3
    depends_on:
      - mongodb
      - rabbitmq
    networks:
      - {domain_key}-network

  {services[5]}:
    build: ./{services[5]}
    environment:
      - RABBITMQ_URL=amqp://admin:${{RABBITMQ_PASSWORD}}@rabbitmq:5672
      - SMTP_HOST=${{SMTP_HOST}}
      - SMTP_PORT=${{SMTP_PORT}}
      - SMTP_USER=${{SMTP_USER}}
      - SMTP_PASSWORD=${{SMTP_PASSWORD}}
      - TWILIO_SID=${{TWILIO_SID}}
      - TWILIO_TOKEN=${{TWILIO_TOKEN}}
    depends_on:
      - rabbitmq
    networks:
      - {domain_key}-network

  # ===========================================
  # OBSERVABILITY
  # ===========================================

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - {domain_key}-network

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${{GRAFANA_PASSWORD}}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
    networks:
      - {domain_key}-network

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"
      - "6831:6831/udp"
    networks:
      - {domain_key}-network

networks:
  {domain_key}-network:
    driver: bridge

volumes:
  postgres_data:
  mongodb_data:
  rabbitmq_data:
  redis_data:
  prometheus_data:
  grafana_data:
```

## API Gateway - nginx.conf

```nginx
upstream {services[0].replace('-', '_')} {{
    least_conn;
    server {services[0]}:8000;
}}

upstream {services[1].replace('-', '_')} {{
    least_conn;
    server {services[1]}:8000;
}}

upstream {services[2].replace('-', '_')} {{
    least_conn;
    server {services[2]}:8000;
}}

server {{
    listen 80;
    server_name api.{domain_key}.com;

    # Health check endpoint
    location /health {{
        return 200 'OK';
        add_header Content-Type text/plain;
    }}

    # {services[0]} routes
    location /api/v1/{services[0].split('-')[0]}s {{
        proxy_pass http://{services[0].replace('-', '_')};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Request-ID $request_id;

        # Circuit breaker
        proxy_connect_timeout 5s;
        proxy_read_timeout 30s;
        proxy_next_upstream error timeout http_500 http_502 http_503;
        proxy_next_upstream_tries 3;
    }}

    # {services[1]} routes
    location /api/v1/{services[1].split('-')[0]}s {{
        proxy_pass http://{services[1].replace('-', '_')};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}

    # {services[2]} routes
    location /api/v1/{services[2].split('-')[0]}s {{
        proxy_pass http://{services[2].replace('-', '_')};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
    limit_req zone=api_limit burst=200 nodelay;
}}
```

## {services[0]}/app/main.py

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import aio_pika
import redis.asyncio as redis
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.routes import router
from app.database import engine, Base
from app.events import setup_event_consumers
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Setup RabbitMQ consumers
    app.state.rabbitmq = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    app.state.redis = redis.from_url(settings.REDIS_URL)

    await setup_event_consumers(app.state.rabbitmq)

    yield

    # Shutdown
    await app.state.rabbitmq.close()
    await app.state.redis.close()

app = FastAPI(
    title="{services[0].replace('-', ' ').title()} API",
    version="1.0.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instrumentation
Instrumentator().instrument(app).expose(app)
FastAPIInstrumentor.instrument_app(app)

# Routes
app.include_router(router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {{"status": "healthy", "service": "{services[0]}"}}
```

## {services[0]}/app/events.py

```python
import json
import aio_pika
from app.config import settings

# Event Publisher
class EventPublisher:
    def __init__(self, connection: aio_pika.Connection):
        self.connection = connection
        self.channel = None
        self.exchange = None

    async def setup(self):
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            "{domain_key}_events",
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

    async def publish(self, event_type: str, data: dict):
        message = aio_pika.Message(
            body=json.dumps({{
                "event_type": event_type,
                "data": data,
                "service": "{services[0]}",
            }}).encode(),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self.exchange.publish(message, routing_key=event_type)

# Event Consumer
async def setup_event_consumers(connection: aio_pika.Connection):
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)

    exchange = await channel.declare_exchange(
        "{domain_key}_events",
        aio_pika.ExchangeType.TOPIC,
        durable=True,
    )

    queue = await channel.declare_queue(
        "{services[0]}_queue",
        durable=True,
    )

    # Bind to relevant events
    await queue.bind(exchange, routing_key="{domain['events'][0]}")
    await queue.bind(exchange, routing_key="{domain['events'][1]}")

    async def process_message(message: aio_pika.IncomingMessage):
        async with message.process():
            data = json.loads(message.body.decode())
            event_type = data["event_type"]

            if event_type == "{domain['events'][0]}":
                await handle_{domain['events'][0].lower()}(data["data"])
            elif event_type == "{domain['events'][1]}":
                await handle_{domain['events'][1].lower()}(data["data"])

    await queue.consume(process_message)

async def handle_{domain['events'][0].lower()}(data: dict):
    print(f"Handling {domain['events'][0]}: {{data}}")
    # Process event logic here

async def handle_{domain['events'][1].lower()}(data: dict):
    print(f"Handling {domain['events'][1]}: {{data}}")
    # Process event logic here
```

## .env

```env
# Database
POSTGRES_USER=admin
POSTGRES_PASSWORD=secure_password_123

# MongoDB
MONGO_USER=admin
MONGO_PASSWORD=secure_password_123

# RabbitMQ
RABBITMQ_PASSWORD=rabbitmq_password

# External Services
STRIPE_SECRET_KEY=sk_test_xxx
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=notifications@example.com
SMTP_PASSWORD=smtp_password
TWILIO_SID=xxx
TWILIO_TOKEN=xxx

# Monitoring
GRAFANA_PASSWORD=admin_password
```

## Running the Services

```bash
# Start all services
docker-compose up -d

# Scale specific service
docker-compose up -d --scale {services[0]}=3

# View logs
docker-compose logs -f {services[0]}

# Health check
curl http://localhost/api/v1/{services[0].split('-')[0]}s/health

# Stop all services
docker-compose down -v
```

This microservices setup includes:
- **6 business services** with inter-service communication
- **API Gateway** (Nginx) with load balancing and circuit breaker
- **Message Broker** (RabbitMQ) for async event-driven communication
- **Databases** (PostgreSQL for relational, MongoDB for documents)
- **Caching** (Redis)
- **Observability** (Prometheus, Grafana, Jaeger)
- **Health checks** and **automatic restart** policies
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in microservices architecture and DevOps. Generate production-ready microservices setups with Docker, Kubernetes, and best practices."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": docker_compose}
        ]
    }


# ============================================================================
# KUBERNETES GENERATOR
# ============================================================================

def generate_kubernetes_example(domain_key: str) -> Dict:
    domain = DOMAINS[domain_key]
    services = domain["services"][:5]

    prompt = f"Create complete Kubernetes manifests for deploying a {domain['name']} microservices architecture with {', '.join(services)}. Include Deployments, Services, Ingress, ConfigMaps, Secrets, and HPA."

    k8s_manifests = f"""I'll create complete Kubernetes manifests for the {domain['name']} microservices architecture.

## Project Structure

```
k8s/
├── namespace.yaml
├── configmaps/
│   ├── common-config.yaml
│   └── service-configs.yaml
├── secrets/
│   ├── db-secrets.yaml
│   └── api-secrets.yaml
├── infrastructure/
│   ├── postgres/
│   │   ├── statefulset.yaml
│   │   ├── service.yaml
│   │   └── pvc.yaml
│   ├── redis/
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   └── rabbitmq/
│       ├── statefulset.yaml
│       └── service.yaml
├── services/
│   ├── {services[0]}/
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── hpa.yaml
│   ├── {services[1]}/
│   │   └── ...
│   └── ...
├── ingress/
│   └── ingress.yaml
└── monitoring/
    ├── prometheus/
    └── grafana/
```

## namespace.yaml

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: {domain_key}
  labels:
    app.kubernetes.io/name: {domain_key}
    istio-injection: enabled
```

## configmaps/common-config.yaml

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: common-config
  namespace: {domain_key}
data:
  LOG_LEVEL: "INFO"
  ENVIRONMENT: "production"
  RABBITMQ_HOST: "rabbitmq.{domain_key}.svc.cluster.local"
  RABBITMQ_PORT: "5672"
  REDIS_HOST: "redis.{domain_key}.svc.cluster.local"
  REDIS_PORT: "6379"
  POSTGRES_HOST: "postgres.{domain_key}.svc.cluster.local"
  POSTGRES_PORT: "5432"
  JAEGER_AGENT_HOST: "jaeger-agent.observability.svc.cluster.local"
  JAEGER_AGENT_PORT: "6831"
```

## secrets/db-secrets.yaml

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-secrets
  namespace: {domain_key}
type: Opaque
stringData:
  POSTGRES_USER: admin
  POSTGRES_PASSWORD: <base64-encoded-password>
  RABBITMQ_USER: admin
  RABBITMQ_PASSWORD: <base64-encoded-password>
---
apiVersion: v1
kind: Secret
metadata:
  name: api-secrets
  namespace: {domain_key}
type: Opaque
stringData:
  JWT_SECRET: <base64-encoded-secret>
  STRIPE_SECRET_KEY: <base64-encoded-key>
```

## services/{services[0]}/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {services[0]}
  namespace: {domain_key}
  labels:
    app: {services[0]}
    version: v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: {services[0]}
  template:
    metadata:
      labels:
        app: {services[0]}
        version: v1
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: {services[0]}-sa
      containers:
        - name: {services[0]}
          image: {domain_key}/{services[0]}:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 8000
              name: http
              protocol: TCP
          envFrom:
            - configMapRef:
                name: common-config
            - secretRef:
                name: db-secrets
          env:
            - name: SERVICE_NAME
              value: "{services[0]}"
            - name: DATABASE_URL
              value: "postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@$(POSTGRES_HOST):$(POSTGRES_PORT)/{services[0].replace('-', '_')}_db"
            - name: POD_NAME
              valueFrom:
                fieldRef:
                  fieldPath: metadata.name
            - name: POD_NAMESPACE
              valueFrom:
                fieldRef:
                  fieldPath: metadata.namespace
          resources:
            requests:
              cpu: "100m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 10"]
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchLabels:
                    app: {services[0]}
                topologyKey: kubernetes.io/hostname
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: ScheduleAnyway
          labelSelector:
            matchLabels:
              app: {services[0]}
```

## services/{services[0]}/service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {services[0]}
  namespace: {domain_key}
  labels:
    app: {services[0]}
spec:
  type: ClusterIP
  ports:
    - port: 8000
      targetPort: 8000
      protocol: TCP
      name: http
  selector:
    app: {services[0]}
```

## services/{services[0]}/hpa.yaml

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {services[0]}-hpa
  namespace: {domain_key}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {services[0]}
  minReplicas: 2
  maxReplicas: 10
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
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "1000"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
        - type: Pods
          value: 4
          periodSeconds: 15
      selectPolicy: Max
```

## services/{services[1]}/deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {services[1]}
  namespace: {domain_key}
  labels:
    app: {services[1]}
spec:
  replicas: 3
  selector:
    matchLabels:
      app: {services[1]}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: {services[1]}
    spec:
      containers:
        - name: {services[1]}
          image: {domain_key}/{services[1]}:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: common-config
            - secretRef:
                name: db-secrets
          env:
            - name: SERVICE_NAME
              value: "{services[1]}"
            - name: {services[0].upper().replace('-', '_')}_URL
              value: "http://{services[0]}.{domain_key}.svc.cluster.local:8000"
          resources:
            requests:
              cpu: "100m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 5
```

## ingress/ingress.yaml

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {domain_key}-ingress
  namespace: {domain_key}
  annotations:
    kubernetes.io/ingress.class: nginx
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "60"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  tls:
    - hosts:
        - api.{domain_key}.com
      secretName: {domain_key}-tls
  rules:
    - host: api.{domain_key}.com
      http:
        paths:
          - path: /api/v1/{services[0].split('-')[0]}s
            pathType: Prefix
            backend:
              service:
                name: {services[0]}
                port:
                  number: 8000
          - path: /api/v1/{services[1].split('-')[0]}s
            pathType: Prefix
            backend:
              service:
                name: {services[1]}
                port:
                  number: 8000
          - path: /api/v1/{services[2].split('-')[0]}s
            pathType: Prefix
            backend:
              service:
                name: {services[2]}
                port:
                  number: 8000
          - path: /api/v1/{services[3].split('-')[0]}s
            pathType: Prefix
            backend:
              service:
                name: {services[3]}
                port:
                  number: 8000
```

## infrastructure/postgres/statefulset.yaml

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: {domain_key}
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
          image: postgres:15-alpine
          ports:
            - containerPort: 5432
          envFrom:
            - secretRef:
                name: db-secrets
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              cpu: "250m"
              memory: "512Mi"
            limits:
              cpu: "1000m"
              memory: "2Gi"
  volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: standard
        resources:
          requests:
            storage: 20Gi
```

## Network Policy

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {services[0]}-network-policy
  namespace: {domain_key}
spec:
  podSelector:
    matchLabels:
      app: {services[0]}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api-gateway
        - podSelector:
            matchLabels:
              app: {services[1]}
      ports:
        - protocol: TCP
          port: 8000
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
    - to:
        - podSelector:
            matchLabels:
              app: rabbitmq
      ports:
        - protocol: TCP
          port: 5672
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - protocol: TCP
          port: 6379
```

## Deployment Commands

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Apply configs and secrets
kubectl apply -f k8s/configmaps/
kubectl apply -f k8s/secrets/

# Deploy infrastructure
kubectl apply -f k8s/infrastructure/

# Deploy services
kubectl apply -f k8s/services/

# Apply ingress
kubectl apply -f k8s/ingress/

# Check status
kubectl get pods -n {domain_key}
kubectl get services -n {domain_key}
kubectl get ingress -n {domain_key}

# Scale deployment
kubectl scale deployment {services[0]} --replicas=5 -n {domain_key}

# Rolling update
kubectl set image deployment/{services[0]} {services[0]}={domain_key}/{services[0]}:v2 -n {domain_key}

# Rollback
kubectl rollout undo deployment/{services[0]} -n {domain_key}
```

This Kubernetes setup includes:
- **Namespace** isolation
- **ConfigMaps** and **Secrets** for configuration
- **Deployments** with health checks, resource limits, and anti-affinity
- **Services** for internal communication
- **HPA** for auto-scaling based on CPU, memory, and custom metrics
- **Ingress** with TLS, rate limiting
- **StatefulSets** for databases
- **NetworkPolicies** for security
- **Rolling updates** and **rollback** support
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in Kubernetes and cloud-native architectures. Generate production-ready Kubernetes manifests with best practices for microservices deployments."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": k8s_manifests}
        ]
    }


# ============================================================================
# gRPC SERVICE GENERATOR
# ============================================================================

def generate_grpc_example(domain_key: str) -> Dict:
    domain = DOMAINS[domain_key]
    services = domain["services"][:3]
    entities = domain.get("entities", {}).get(services[0], ["Item", "Entity"])

    prompt = f"Create a gRPC-based microservices setup for {domain['name']} with {services[0]} and {services[1]}. Include proto files, Python server implementation, and client code."

    grpc_code = f"""I'll create a complete gRPC microservices setup for the {domain['name']}.

## Project Structure

```
grpc-{domain_key}/
├── protos/
│   ├── common/
│   │   └── types.proto
│   ├── {services[0].replace('-', '_')}/
│   │   └── service.proto
│   └── {services[1].replace('-', '_')}/
│       └── service.proto
├── {services[0]}/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── server.py
│   ├── service.py
│   └── generated/
│       └── ...
├── {services[1]}/
│   └── ...
└── docker-compose.yml
```

## protos/common/types.proto

```protobuf
syntax = "proto3";

package common;

option go_package = "github.com/{domain_key}/common";

// Pagination
message PaginationRequest {{
    int32 page = 1;
    int32 page_size = 2;
}}

message PaginationResponse {{
    int32 total = 1;
    int32 page = 2;
    int32 page_size = 3;
    int32 total_pages = 4;
}}

// Common response wrapper
message Empty {{}}

message ErrorResponse {{
    int32 code = 1;
    string message = 2;
    map<string, string> details = 3;
}}

// Timestamps
message Timestamp {{
    int64 seconds = 1;
    int32 nanos = 2;
}}
```

## protos/{services[0].replace('-', '_')}/service.proto

```protobuf
syntax = "proto3";

package {services[0].replace('-', '_')};

import "common/types.proto";

option go_package = "github.com/{domain_key}/{services[0].replace('-', '_')}";

// {entities[0]} message
message {entities[0]} {{
    string id = 1;
    string name = 2;
    string email = 3;
    string status = 4;
    map<string, string> metadata = 5;
    common.Timestamp created_at = 6;
    common.Timestamp updated_at = 7;
}}

// Request/Response messages
message Create{entities[0]}Request {{
    string name = 1;
    string email = 2;
    map<string, string> metadata = 3;
}}

message Create{entities[0]}Response {{
    {entities[0]} {entities[0].lower()} = 1;
}}

message Get{entities[0]}Request {{
    string id = 1;
}}

message Get{entities[0]}Response {{
    {entities[0]} {entities[0].lower()} = 1;
}}

message List{entities[0]}sRequest {{
    common.PaginationRequest pagination = 1;
    string status = 2;
    string search = 3;
}}

message List{entities[0]}sResponse {{
    repeated {entities[0]} {entities[0].lower()}s = 1;
    common.PaginationResponse pagination = 2;
}}

message Update{entities[0]}Request {{
    string id = 1;
    optional string name = 2;
    optional string email = 3;
    optional string status = 4;
    map<string, string> metadata = 5;
}}

message Update{entities[0]}Response {{
    {entities[0]} {entities[0].lower()} = 1;
}}

message Delete{entities[0]}Request {{
    string id = 1;
}}

message Delete{entities[0]}Response {{
    bool success = 1;
}}

// Streaming messages
message {entities[0]}Event {{
    string event_type = 1;  // created, updated, deleted
    {entities[0]} {entities[0].lower()} = 2;
    common.Timestamp timestamp = 3;
}}

// Service definition
service {services[0].replace('-', ' ').title().replace(' ', '')}Service {{
    // Unary RPCs
    rpc Create{entities[0]}(Create{entities[0]}Request) returns (Create{entities[0]}Response);
    rpc Get{entities[0]}(Get{entities[0]}Request) returns (Get{entities[0]}Response);
    rpc Update{entities[0]}(Update{entities[0]}Request) returns (Update{entities[0]}Response);
    rpc Delete{entities[0]}(Delete{entities[0]}Request) returns (Delete{entities[0]}Response);
    rpc List{entities[0]}s(List{entities[0]}sRequest) returns (List{entities[0]}sResponse);

    // Server streaming RPC
    rpc Watch{entities[0]}s(common.Empty) returns (stream {entities[0]}Event);

    // Bidirectional streaming RPC
    rpc Bulk{entities[0]}Operations(stream Create{entities[0]}Request) returns (stream Create{entities[0]}Response);
}}
```

## {services[0]}/server.py

```python
import asyncio
import logging
from concurrent import futures
import grpc
from grpc_reflection.v1alpha import reflection
from grpc_health.v1 import health_pb2, health_pb2_grpc
from grpc_health.v1.health import HealthServicer
from opentelemetry import trace
from opentelemetry.instrumentation.grpc import GrpcInstrumentorServer
from prometheus_client import start_http_server, Counter, Histogram

from generated import {services[0].replace('-', '_')}_pb2
from generated import {services[0].replace('-', '_')}_pb2_grpc
from service import {services[0].replace('-', ' ').title().replace(' ', '')}Servicer
from interceptors import LoggingInterceptor, AuthInterceptor, RateLimitInterceptor

# Metrics
REQUEST_COUNT = Counter(
    '{services[0].replace('-', '_')}_requests_total',
    'Total requests',
    ['method', 'status']
)
REQUEST_LATENCY = Histogram(
    '{services[0].replace('-', '_')}_request_latency_seconds',
    'Request latency',
    ['method']
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def serve():
    # Start metrics server
    start_http_server(8001)

    # Create server with interceptors
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[
            LoggingInterceptor(),
            AuthInterceptor(),
            RateLimitInterceptor(rate=100, per_seconds=1),
        ],
        options=[
            ('grpc.max_send_message_length', 50 * 1024 * 1024),
            ('grpc.max_receive_message_length', 50 * 1024 * 1024),
            ('grpc.keepalive_time_ms', 10000),
            ('grpc.keepalive_timeout_ms', 5000),
            ('grpc.keepalive_permit_without_calls', True),
            ('grpc.http2.max_pings_without_data', 0),
            ('grpc.http2.min_time_between_pings_ms', 10000),
            ('grpc.http2.min_ping_interval_without_data_ms', 5000),
        ],
    )

    # Add services
    {services[0].replace('-', '_')}_pb2_grpc.add_{services[0].replace('-', ' ').title().replace(' ', '')}ServiceServicer_to_server(
        {services[0].replace('-', ' ').title().replace(' ', '')}Servicer(), server
    )

    # Add health check service
    health_servicer = HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)
    health_servicer.set(
        "{services[0].replace('-', '_')}.{services[0].replace('-', ' ').title().replace(' ', '')}Service",
        health_pb2.HealthCheckResponse.SERVING
    )

    # Add reflection for debugging
    SERVICE_NAMES = (
        {services[0].replace('-', '_')}_pb2.DESCRIPTOR.services_by_name['{services[0].replace('-', ' ').title().replace(' ', '')}Service'].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(SERVICE_NAMES, server)

    # Instrument with OpenTelemetry
    GrpcInstrumentorServer().instrument()

    # Start server
    listen_addr = '[::]:50051'
    server.add_insecure_port(listen_addr)
    logger.info(f"Starting gRPC server on {{listen_addr}}")

    await server.start()

    # Graceful shutdown
    async def graceful_shutdown():
        logger.info("Shutting down gracefully...")
        await server.stop(5)

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        await graceful_shutdown()


if __name__ == '__main__':
    asyncio.run(serve())
```

## {services[0]}/service.py

```python
import uuid
from datetime import datetime
from typing import AsyncIterator
import grpc
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from generated import {services[0].replace('-', '_')}_pb2
from generated import {services[0].replace('-', '_')}_pb2_grpc
from generated import common_pb2
from database import get_session
from models import {entities[0]}Model
from events import publish_event


class {services[0].replace('-', ' ').title().replace(' ', '')}Servicer({services[0].replace('-', '_')}_pb2_grpc.{services[0].replace('-', ' ').title().replace(' ', '')}ServiceServicer):

    async def Create{entities[0]}(
        self,
        request: {services[0].replace('-', '_')}_pb2.Create{entities[0]}Request,
        context: grpc.aio.ServicerContext,
    ) -> {services[0].replace('-', '_')}_pb2.Create{entities[0]}Response:
        async with get_session() as session:
            # Create entity
            {entities[0].lower()} = {entities[0]}Model(
                id=str(uuid.uuid4()),
                name=request.name,
                email=request.email,
                metadata=dict(request.metadata),
                status="active",
            )
            session.add({entities[0].lower()})
            await session.commit()
            await session.refresh({entities[0].lower()})

            # Publish event
            await publish_event(
                event_type="{entities[0]}Created",
                data={{{entities[0].lower()}.to_dict()}},
            )

            return {services[0].replace('-', '_')}_pb2.Create{entities[0]}Response(
                {entities[0].lower()}=self._to_proto({entities[0].lower()})
            )

    async def Get{entities[0]}(
        self,
        request: {services[0].replace('-', '_')}_pb2.Get{entities[0]}Request,
        context: grpc.aio.ServicerContext,
    ) -> {services[0].replace('-', '_')}_pb2.Get{entities[0]}Response:
        async with get_session() as session:
            {entities[0].lower()} = await session.get({entities[0]}Model, request.id)

            if not {entities[0].lower()}:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"{entities[0]} not found: {{request.id}}")
                return {services[0].replace('-', '_')}_pb2.Get{entities[0]}Response()

            return {services[0].replace('-', '_')}_pb2.Get{entities[0]}Response(
                {entities[0].lower()}=self._to_proto({entities[0].lower()})
            )

    async def List{entities[0]}s(
        self,
        request: {services[0].replace('-', '_')}_pb2.List{entities[0]}sRequest,
        context: grpc.aio.ServicerContext,
    ) -> {services[0].replace('-', '_')}_pb2.List{entities[0]}sResponse:
        async with get_session() as session:
            page = request.pagination.page or 1
            page_size = request.pagination.page_size or 20

            # Query with filters
            query = session.query({entities[0]}Model)

            if request.status:
                query = query.filter({entities[0]}Model.status == request.status)

            if request.search:
                query = query.filter(
                    {entities[0]}Model.name.ilike(f"%{{request.search}}%")
                )

            # Count total
            total = await session.execute(query.count())

            # Paginate
            {entities[0].lower()}s = await session.execute(
                query.offset((page - 1) * page_size).limit(page_size)
            )

            return {services[0].replace('-', '_')}_pb2.List{entities[0]}sResponse(
                {entities[0].lower()}s=[self._to_proto(u) for u in {entities[0].lower()}s.scalars()],
                pagination=common_pb2.PaginationResponse(
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=(total + page_size - 1) // page_size,
                ),
            )

    async def Watch{entities[0]}s(
        self,
        request: common_pb2.Empty,
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[{services[0].replace('-', '_')}_pb2.{entities[0]}Event]:
        \"\"\"Server streaming - watch for {entities[0].lower()} changes\"\"\"
        # Subscribe to Redis pub/sub or message queue
        from events import subscribe_events

        async for event in subscribe_events("{entities[0]}*"):
            if context.cancelled():
                break

            yield {services[0].replace('-', '_')}_pb2.{entities[0]}Event(
                event_type=event["type"],
                {entities[0].lower()}=self._to_proto(event["data"]),
                timestamp=common_pb2.Timestamp(
                    seconds=int(datetime.now().timestamp())
                ),
            )

    async def Bulk{entities[0]}Operations(
        self,
        request_iterator: AsyncIterator[{services[0].replace('-', '_')}_pb2.Create{entities[0]}Request],
        context: grpc.aio.ServicerContext,
    ) -> AsyncIterator[{services[0].replace('-', '_')}_pb2.Create{entities[0]}Response]:
        \"\"\"Bidirectional streaming - bulk create {entities[0].lower()}s\"\"\"
        async for request in request_iterator:
            response = await self.Create{entities[0]}(request, context)
            yield response

    def _to_proto(self, model: {entities[0]}Model) -> {services[0].replace('-', '_')}_pb2.{entities[0]}:
        return {services[0].replace('-', '_')}_pb2.{entities[0]}(
            id=model.id,
            name=model.name,
            email=model.email,
            status=model.status,
            metadata=model.metadata or {{}},
            created_at=common_pb2.Timestamp(
                seconds=int(model.created_at.timestamp())
            ),
            updated_at=common_pb2.Timestamp(
                seconds=int(model.updated_at.timestamp())
            ) if model.updated_at else None,
        )
```

## {services[0]}/client.py (gRPC Client)

```python
import grpc
from grpc import aio
import asyncio
from typing import List, AsyncIterator

from generated import {services[0].replace('-', '_')}_pb2
from generated import {services[0].replace('-', '_')}_pb2_grpc
from generated import common_pb2


class {services[0].replace('-', ' ').title().replace(' ', '')}Client:
    def __init__(self, host: str = "localhost", port: int = 50051):
        self.channel = None
        self.stub = None
        self.host = host
        self.port = port

    async def connect(self):
        self.channel = aio.insecure_channel(
            f"{{self.host}}:{{self.port}}",
            options=[
                ('grpc.keepalive_time_ms', 10000),
                ('grpc.keepalive_timeout_ms', 5000),
            ],
        )
        self.stub = {services[0].replace('-', '_')}_pb2_grpc.{services[0].replace('-', ' ').title().replace(' ', '')}ServiceStub(self.channel)

    async def close(self):
        if self.channel:
            await self.channel.close()

    async def create_{entities[0].lower()}(
        self,
        name: str,
        email: str,
        metadata: dict = None,
    ) -> {services[0].replace('-', '_')}_pb2.{entities[0]}:
        request = {services[0].replace('-', '_')}_pb2.Create{entities[0]}Request(
            name=name,
            email=email,
            metadata=metadata or {{}},
        )
        response = await self.stub.Create{entities[0]}(request)
        return response.{entities[0].lower()}

    async def get_{entities[0].lower()}(self, id: str) -> {services[0].replace('-', '_')}_pb2.{entities[0]}:
        request = {services[0].replace('-', '_')}_pb2.Get{entities[0]}Request(id=id)
        response = await self.stub.Get{entities[0]}(request)
        return response.{entities[0].lower()}

    async def list_{entities[0].lower()}s(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str = None,
        search: str = None,
    ) -> List[{services[0].replace('-', '_')}_pb2.{entities[0]}]:
        request = {services[0].replace('-', '_')}_pb2.List{entities[0]}sRequest(
            pagination=common_pb2.PaginationRequest(
                page=page,
                page_size=page_size,
            ),
            status=status or "",
            search=search or "",
        )
        response = await self.stub.List{entities[0]}s(request)
        return list(response.{entities[0].lower()}s)

    async def watch_{entities[0].lower()}s(self) -> AsyncIterator[{services[0].replace('-', '_')}_pb2.{entities[0]}Event]:
        request = common_pb2.Empty()
        async for event in self.stub.Watch{entities[0]}s(request):
            yield event

    async def bulk_create_{entities[0].lower()}s(
        self,
        items: List[dict],
    ) -> List[{services[0].replace('-', '_')}_pb2.{entities[0]}]:
        async def request_generator():
            for item in items:
                yield {services[0].replace('-', '_')}_pb2.Create{entities[0]}Request(
                    name=item["name"],
                    email=item["email"],
                    metadata=item.get("metadata", {{}}),
                )

        results = []
        async for response in self.stub.Bulk{entities[0]}Operations(request_generator()):
            results.append(response.{entities[0].lower()})
        return results


# Usage example
async def main():
    client = {services[0].replace('-', ' ').title().replace(' ', '')}Client()
    await client.connect()

    try:
        # Create
        {entities[0].lower()} = await client.create_{entities[0].lower()}(
            name="John Doe",
            email="john@example.com",
        )
        print(f"Created: {{{entities[0].lower()}.id}}")

        # Get
        {entities[0].lower()} = await client.get_{entities[0].lower()}({entities[0].lower()}.id)
        print(f"Got: {{{entities[0].lower()}.name}}")

        # List
        {entities[0].lower()}s = await client.list_{entities[0].lower()}s(page=1, page_size=10)
        print(f"Total: {{len({entities[0].lower()}s)}}")

        # Watch (streaming)
        async for event in client.watch_{entities[0].lower()}s():
            print(f"Event: {{event.event_type}} - {{event.{entities[0].lower()}.id}}")
            break  # Stop after first event

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  {services[0]}:
    build: ./{services[0]}
    ports:
      - "50051:50051"
      - "8001:8001"  # Metrics
    environment:
      - DATABASE_URL=postgresql://admin:password@postgres:5432/{services[0].replace('-', '_')}_db
      - RABBITMQ_URL=amqp://admin:password@rabbitmq:5672
    depends_on:
      - postgres
      - rabbitmq
    networks:
      - grpc-network

  {services[1]}:
    build: ./{services[1]}
    ports:
      - "50052:50051"
    environment:
      - DATABASE_URL=postgresql://admin:password@postgres:5432/{services[1].replace('-', '_')}_db
      - {services[0].upper().replace('-', '_')}_GRPC_HOST={services[0]}
      - {services[0].upper().replace('-', '_')}_GRPC_PORT=50051
    depends_on:
      - {services[0]}
    networks:
      - grpc-network

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - grpc-network

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "15672:15672"
    networks:
      - grpc-network

networks:
  grpc-network:
    driver: bridge

volumes:
  postgres_data:
```

This gRPC microservices setup includes:
- **Protocol Buffers** definitions with common types
- **Unary RPCs** for CRUD operations
- **Server streaming** for real-time updates
- **Bidirectional streaming** for bulk operations
- **Health checks** and **reflection** for debugging
- **Interceptors** for logging, auth, and rate limiting
- **OpenTelemetry** instrumentation
- **Prometheus** metrics
- **Async Python** implementation with SQLAlchemy
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in gRPC and microservices. Generate production-ready gRPC services with Protocol Buffers, streaming, and best practices."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": grpc_code}
        ]
    }


# ============================================================================
# EVENT-DRIVEN ARCHITECTURE GENERATOR
# ============================================================================

def generate_event_driven_example(domain_key: str) -> Dict:
    domain = DOMAINS[domain_key]
    services = domain["services"][:4]
    events = domain["events"]

    prompt = f"Create an event-driven architecture for {domain['name']} using Apache Kafka. Include producers, consumers, event schemas, and dead letter queue handling for events: {', '.join(events)}."

    event_driven_code = f"""I'll create a complete event-driven architecture for {domain['name']} using Apache Kafka.

## Project Structure

```
event-driven-{domain_key}/
├── docker-compose.yml
├── schemas/
│   └── events/
│       ├── {events[0].lower()}.avsc
│       ├── {events[1].lower()}.avsc
│       └── ...
├── shared/
│   ├── kafka_config.py
│   ├── event_schemas.py
│   └── circuit_breaker.py
├── {services[0]}/
│   ├── producer.py
│   └── handlers.py
├── {services[1]}/
│   ├── consumer.py
│   └── handlers.py
└── {services[2]}/
    ├── consumer.py
    └── handlers.py
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    ports:
      - "2181:2181"
    networks:
      - kafka-network

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
      - "29092:29092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: 'false'
    networks:
      - kafka-network

  schema-registry:
    image: confluentinc/cp-schema-registry:7.5.0
    depends_on:
      - kafka
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:29092
    networks:
      - kafka-network

  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    ports:
      - "8080:8080"
    environment:
      KAFKA_CLUSTERS_0_NAME: local
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:29092
      KAFKA_CLUSTERS_0_SCHEMAREGISTRY: http://schema-registry:8081
    depends_on:
      - kafka
      - schema-registry
    networks:
      - kafka-network

  # Services
  {services[0]}:
    build: ./{services[0]}
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:29092
      SCHEMA_REGISTRY_URL: http://schema-registry:8081
    depends_on:
      - kafka
      - schema-registry
    networks:
      - kafka-network

  {services[1]}:
    build: ./{services[1]}
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:29092
      SCHEMA_REGISTRY_URL: http://schema-registry:8081
    depends_on:
      - kafka
    networks:
      - kafka-network

  {services[2]}:
    build: ./{services[2]}
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:29092
      SCHEMA_REGISTRY_URL: http://schema-registry:8081
    depends_on:
      - kafka
    networks:
      - kafka-network

networks:
  kafka-network:
    driver: bridge
```

## schemas/events/{events[0].lower()}.avsc

```json
{{
  "type": "record",
  "name": "{events[0]}",
  "namespace": "com.{domain_key}.events",
  "fields": [
    {{"name": "event_id", "type": "string"}},
    {{"name": "event_type", "type": "string", "default": "{events[0]}"}},
    {{"name": "timestamp", "type": "long", "logicalType": "timestamp-millis"}},
    {{"name": "version", "type": "string", "default": "1.0"}},
    {{"name": "source", "type": "string"}},
    {{"name": "correlation_id", "type": ["null", "string"], "default": null}},
    {{"name": "data", "type": {{
      "type": "record",
      "name": "{events[0]}Data",
      "fields": [
        {{"name": "id", "type": "string"}},
        {{"name": "name", "type": "string"}},
        {{"name": "email", "type": ["null", "string"], "default": null}},
        {{"name": "metadata", "type": {{"type": "map", "values": "string"}}, "default": {{}}}}
      ]
    }}}}
  ]
}}
```

## shared/kafka_config.py

```python
import os
from dataclasses import dataclass
from typing import Optional
from confluent_kafka import Producer, Consumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer, AvroDeserializer


@dataclass
class KafkaConfig:
    bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    schema_registry_url: str = os.getenv("SCHEMA_REGISTRY_URL", "http://localhost:8081")
    group_id: str = os.getenv("KAFKA_GROUP_ID", "default-group")

    # Topics
    TOPIC_{events[0].upper()}: str = "{domain_key}.events.{events[0].lower()}"
    TOPIC_{events[1].upper()}: str = "{domain_key}.events.{events[1].lower()}"
    TOPIC_{events[2].upper()}: str = "{domain_key}.events.{events[2].lower()}"
    TOPIC_DLQ: str = "{domain_key}.events.dlq"


class KafkaProducerFactory:
    def __init__(self, config: KafkaConfig):
        self.config = config
        self.schema_registry = SchemaRegistryClient({{"url": config.schema_registry_url}})

    def create_producer(self) -> Producer:
        return Producer({{
            "bootstrap.servers": self.config.bootstrap_servers,
            "acks": "all",
            "retries": 5,
            "retry.backoff.ms": 100,
            "enable.idempotence": True,
            "max.in.flight.requests.per.connection": 5,
            "compression.type": "snappy",
            "batch.size": 16384,
            "linger.ms": 10,
        }})

    def get_serializer(self, schema_str: str) -> AvroSerializer:
        return AvroSerializer(
            self.schema_registry,
            schema_str,
            conf={{"auto.register.schemas": True}},
        )


class KafkaConsumerFactory:
    def __init__(self, config: KafkaConfig):
        self.config = config
        self.schema_registry = SchemaRegistryClient({{"url": config.schema_registry_url}})

    def create_consumer(self, group_id: Optional[str] = None) -> Consumer:
        return Consumer({{
            "bootstrap.servers": self.config.bootstrap_servers,
            "group.id": group_id or self.config.group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "max.poll.interval.ms": 300000,
            "session.timeout.ms": 45000,
            "heartbeat.interval.ms": 15000,
        }})

    def get_deserializer(self, schema_str: str) -> AvroDeserializer:
        return AvroDeserializer(
            self.schema_registry,
            schema_str,
        )
```

## shared/event_schemas.py

```python
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
import json


@dataclass
class BaseEvent:
    event_id: str
    event_type: str
    timestamp: int
    version: str
    source: str
    correlation_id: Optional[str]
    data: Dict[str, Any]

    @classmethod
    def create(
        cls,
        event_type: str,
        source: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> "BaseEvent":
        return cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=int(datetime.utcnow().timestamp() * 1000),
            version="1.0",
            source=source,
            correlation_id=correlation_id,
            data=data,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class {events[0]}(BaseEvent):
    @classmethod
    def create(
        cls,
        source: str,
        id: str,
        name: str,
        email: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        correlation_id: Optional[str] = None,
    ) -> "{events[0]}":
        return super().create(
            event_type="{events[0]}",
            source=source,
            data={{
                "id": id,
                "name": name,
                "email": email,
                "metadata": metadata or {{}},
            }},
            correlation_id=correlation_id,
        )


@dataclass
class {events[1]}(BaseEvent):
    @classmethod
    def create(
        cls,
        source: str,
        id: str,
        status: str,
        amount: Optional[float] = None,
        correlation_id: Optional[str] = None,
    ) -> "{events[1]}":
        return super().create(
            event_type="{events[1]}",
            source=source,
            data={{
                "id": id,
                "status": status,
                "amount": amount,
            }},
            correlation_id=correlation_id,
        )
```

## {services[0]}/producer.py

```python
import asyncio
import logging
from typing import Dict, Any
from confluent_kafka import Producer, KafkaError
from prometheus_client import Counter, Histogram

from shared.kafka_config import KafkaConfig, KafkaProducerFactory
from shared.event_schemas import {events[0]}, {events[1]}

logger = logging.getLogger(__name__)

# Metrics
EVENTS_PRODUCED = Counter(
    'events_produced_total',
    'Total events produced',
    ['event_type', 'status']
)
EVENT_LATENCY = Histogram(
    'event_produce_latency_seconds',
    'Event produce latency',
    ['event_type']
)


class EventProducer:
    def __init__(self):
        self.config = KafkaConfig()
        self.factory = KafkaProducerFactory(self.config)
        self.producer = self.factory.create_producer()

    def _delivery_callback(self, err, msg):
        if err:
            logger.error(f"Message delivery failed: {{err}}")
            EVENTS_PRODUCED.labels(
                event_type=msg.topic().split('.')[-1],
                status="failed"
            ).inc()
        else:
            logger.info(f"Message delivered to {{msg.topic()}} [{{msg.partition()}}]")
            EVENTS_PRODUCED.labels(
                event_type=msg.topic().split('.')[-1],
                status="success"
            ).inc()

    async def publish_{events[0].lower()}(
        self,
        id: str,
        name: str,
        email: str = None,
        metadata: Dict[str, str] = None,
        correlation_id: str = None,
    ):
        event = {events[0]}.create(
            source="{services[0]}",
            id=id,
            name=name,
            email=email,
            metadata=metadata,
            correlation_id=correlation_id,
        )

        with EVENT_LATENCY.labels(event_type="{events[0]}").time():
            self.producer.produce(
                topic=self.config.TOPIC_{events[0].upper()},
                key=id,
                value=event.to_json(),
                callback=self._delivery_callback,
                headers={{
                    "event_type": "{events[0]}",
                    "correlation_id": correlation_id or "",
                }},
            )
            self.producer.flush()

        logger.info(f"Published {events[0]}: {{id}}")
        return event

    async def publish_{events[1].lower()}(
        self,
        id: str,
        status: str,
        amount: float = None,
        correlation_id: str = None,
    ):
        event = {events[1]}.create(
            source="{services[0]}",
            id=id,
            status=status,
            amount=amount,
            correlation_id=correlation_id,
        )

        self.producer.produce(
            topic=self.config.TOPIC_{events[1].upper()},
            key=id,
            value=event.to_json(),
            callback=self._delivery_callback,
        )
        self.producer.flush()

        return event

    def close(self):
        self.producer.flush()


# Usage in FastAPI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
producer = EventProducer()


class Create{events[0].replace('Created', '').replace('Processed', '')}Request(BaseModel):
    name: str
    email: str = None


@app.post("/api/v1/{services[0].split('-')[0]}s")
async def create_item(request: Create{events[0].replace('Created', '').replace('Processed', '')}Request):
    import uuid
    item_id = str(uuid.uuid4())

    # Save to database...

    # Publish event
    await producer.publish_{events[0].lower()}(
        id=item_id,
        name=request.name,
        email=request.email,
    )

    return {{"id": item_id, "status": "created"}}
```

## {services[1]}/consumer.py

```python
import asyncio
import logging
import json
from typing import Callable, Dict, Any
from confluent_kafka import Consumer, KafkaError, KafkaException
from prometheus_client import Counter, Histogram

from shared.kafka_config import KafkaConfig, KafkaConsumerFactory
from shared.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)

# Metrics
EVENTS_CONSUMED = Counter(
    'events_consumed_total',
    'Total events consumed',
    ['event_type', 'status']
)
EVENT_PROCESSING_TIME = Histogram(
    'event_processing_seconds',
    'Event processing time',
    ['event_type']
)


class EventConsumer:
    def __init__(self, group_id: str):
        self.config = KafkaConfig()
        self.factory = KafkaConsumerFactory(self.config)
        self.consumer = self.factory.create_consumer(group_id)
        self.handlers: Dict[str, Callable] = {{}}
        self.running = False
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
        )

    def register_handler(self, event_type: str, handler: Callable):
        self.handlers[event_type] = handler

    async def start(self, topics: list):
        self.consumer.subscribe(topics)
        self.running = True

        logger.info(f"Consumer started, subscribed to: {{topics}}")

        while self.running:
            try:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        raise KafkaException(msg.error())

                await self._process_message(msg)

            except Exception as e:
                logger.error(f"Consumer error: {{e}}")
                await asyncio.sleep(1)

    async def _process_message(self, msg):
        try:
            # Parse message
            event = json.loads(msg.value().decode('utf-8'))
            event_type = event.get('event_type')

            logger.info(f"Received event: {{event_type}} - {{event.get('event_id')}}")

            # Get handler
            handler = self.handlers.get(event_type)
            if not handler:
                logger.warning(f"No handler for event type: {{event_type}}")
                self.consumer.commit(msg)
                return

            # Process with circuit breaker
            with EVENT_PROCESSING_TIME.labels(event_type=event_type).time():
                if self.circuit_breaker.is_open():
                    await self._send_to_dlq(msg, "Circuit breaker open")
                    return

                try:
                    await handler(event)
                    self.circuit_breaker.record_success()
                    EVENTS_CONSUMED.labels(event_type=event_type, status="success").inc()
                except Exception as e:
                    self.circuit_breaker.record_failure()
                    EVENTS_CONSUMED.labels(event_type=event_type, status="failed").inc()
                    raise

            # Commit offset
            self.consumer.commit(msg)

        except Exception as e:
            logger.error(f"Failed to process message: {{e}}")
            await self._send_to_dlq(msg, str(e))

    async def _send_to_dlq(self, msg, error: str):
        \"\"\"Send failed message to Dead Letter Queue\"\"\"
        dlq_producer = self.factory.create_producer()

        dlq_message = {{
            "original_topic": msg.topic(),
            "original_partition": msg.partition(),
            "original_offset": msg.offset(),
            "original_key": msg.key().decode() if msg.key() else None,
            "original_value": msg.value().decode(),
            "error": error,
            "timestamp": int(asyncio.get_event_loop().time() * 1000),
        }}

        dlq_producer.produce(
            topic=self.config.TOPIC_DLQ,
            value=json.dumps(dlq_message),
        )
        dlq_producer.flush()

        logger.warning(f"Message sent to DLQ: {{error}}")

        # Commit to move past the failed message
        self.consumer.commit(msg)

    def stop(self):
        self.running = False
        self.consumer.close()


# Event handlers
async def handle_{events[0].lower()}(event: Dict[str, Any]):
    data = event["data"]
    logger.info(f"Processing {events[0]}: {{data['id']}}")

    # Business logic here
    # e.g., send welcome email, create related records, etc.

    await asyncio.sleep(0.1)  # Simulate processing


async def handle_{events[1].lower()}(event: Dict[str, Any]):
    data = event["data"]
    logger.info(f"Processing {events[1]}: {{data['id']}}")

    # Business logic here


# Main
async def main():
    consumer = EventConsumer(group_id="{services[1]}-consumer-group")

    # Register handlers
    consumer.register_handler("{events[0]}", handle_{events[0].lower()})
    consumer.register_handler("{events[1]}", handle_{events[1].lower()})

    # Start consuming
    await consumer.start([
        KafkaConfig.TOPIC_{events[0].upper()},
        KafkaConfig.TOPIC_{events[1].upper()},
    ])


if __name__ == "__main__":
    asyncio.run(main())
```

## shared/circuit_breaker.py

```python
import time
from enum import Enum
from threading import Lock


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0
        self.lock = Lock()

    def is_open(self) -> bool:
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    return False
                return True
            return False

    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.recovery_timeout

    def record_success(self):
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.half_open_max_calls:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def record_failure(self):
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
```

This event-driven architecture includes:
- **Apache Kafka** with Schema Registry
- **Avro schemas** for event serialization
- **Producer** with delivery guarantees and idempotence
- **Consumer** with manual offset commits
- **Dead Letter Queue (DLQ)** for failed messages
- **Circuit Breaker** pattern for fault tolerance
- **Prometheus metrics** for monitoring
- **Async Python** implementation
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in event-driven architecture and Apache Kafka. Generate production-ready event-driven systems with proper error handling, dead letter queues, and monitoring."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": event_driven_code}
        ]
    }


# ============================================================================
# SERVICE MESH GENERATOR
# ============================================================================

def generate_service_mesh_example(domain_key: str) -> Dict:
    domain = DOMAINS[domain_key]
    services = domain["services"][:4]

    prompt = f"Create Istio service mesh configuration for {domain['name']} microservices including VirtualServices, DestinationRules, Gateway, and traffic management policies."

    service_mesh_code = f"""I'll create a complete Istio service mesh configuration for the {domain['name']} microservices.

## Project Structure

```
istio-config/
├── namespace.yaml
├── gateway/
│   └── gateway.yaml
├── virtual-services/
│   ├── {services[0]}-vs.yaml
│   ├── {services[1]}-vs.yaml
│   └── ...
├── destination-rules/
│   ├── {services[0]}-dr.yaml
│   └── ...
├── policies/
│   ├── authorization-policy.yaml
│   ├── peer-authentication.yaml
│   └── request-authentication.yaml
├── traffic-management/
│   ├── circuit-breaker.yaml
│   ├── retry-policy.yaml
│   └── rate-limit.yaml
└── observability/
    ├── telemetry.yaml
    └── service-entry.yaml
```

## namespace.yaml

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: {domain_key}
  labels:
    istio-injection: enabled
```

## gateway/gateway.yaml

```yaml
apiVersion: networking.istio.io/v1beta1
kind: Gateway
metadata:
  name: {domain_key}-gateway
  namespace: {domain_key}
spec:
  selector:
    istio: ingressgateway
  servers:
    - port:
        number: 80
        name: http
        protocol: HTTP
      hosts:
        - "api.{domain_key}.com"
        - "*.{domain_key}.com"
      tls:
        httpsRedirect: true
    - port:
        number: 443
        name: https
        protocol: HTTPS
      hosts:
        - "api.{domain_key}.com"
        - "*.{domain_key}.com"
      tls:
        mode: SIMPLE
        credentialName: {domain_key}-tls-cert
```

## virtual-services/{services[0]}-vs.yaml

```yaml
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: {services[0]}
  namespace: {domain_key}
spec:
  hosts:
    - {services[0]}
    - "api.{domain_key}.com"
  gateways:
    - {domain_key}-gateway
    - mesh
  http:
    # Canary deployment - route 10% to v2
    - match:
        - uri:
            prefix: /api/v1/{services[0].split('-')[0]}s
          headers:
            x-canary:
              exact: "true"
      route:
        - destination:
            host: {services[0]}
            subset: v2
          weight: 100

    # A/B testing based on header
    - match:
        - uri:
            prefix: /api/v1/{services[0].split('-')[0]}s
          headers:
            x-user-group:
              exact: "beta"
      route:
        - destination:
            host: {services[0]}
            subset: v2

    # Default traffic split
    - match:
        - uri:
            prefix: /api/v1/{services[0].split('-')[0]}s
      route:
        - destination:
            host: {services[0]}
            subset: v1
          weight: 90
        - destination:
            host: {services[0]}
            subset: v2
          weight: 10

      # Retry policy
      retries:
        attempts: 3
        perTryTimeout: 2s
        retryOn: gateway-error,connect-failure,refused-stream,5xx

      # Timeout
      timeout: 30s

      # Fault injection for testing
      # fault:
      #   delay:
      #     percentage:
      #       value: 10
      #     fixedDelay: 5s
      #   abort:
      #     percentage:
      #       value: 5
      #     httpStatus: 500

      # Request mirroring for shadow testing
      mirror:
        host: {services[0]}-shadow
        subset: v2
      mirrorPercentage:
        value: 5.0

      # Headers manipulation
      headers:
        request:
          add:
            x-forwarded-service: "{services[0]}"
          remove:
            - x-internal-header
        response:
          add:
            x-served-by: "{services[0]}"
```

## destination-rules/{services[0]}-dr.yaml

```yaml
apiVersion: networking.istio.io/v1beta1
kind: DestinationRule
metadata:
  name: {services[0]}
  namespace: {domain_key}
spec:
  host: {services[0]}

  # Traffic policy
  trafficPolicy:
    # Connection pool settings
    connectionPool:
      tcp:
        maxConnections: 100
        connectTimeout: 5s
        tcpKeepalive:
          time: 7200s
          interval: 75s
      http:
        h2UpgradePolicy: UPGRADE
        http1MaxPendingRequests: 1024
        http2MaxRequests: 1024
        maxRequestsPerConnection: 100
        maxRetries: 3

    # Load balancing
    loadBalancer:
      simple: LEAST_REQUEST
      localityLbSetting:
        enabled: true
        failover:
          - from: us-west-1
            to: us-east-1

    # Circuit breaker
    outlierDetection:
      consecutive5xxErrors: 5
      interval: 30s
      baseEjectionTime: 30s
      maxEjectionPercent: 50
      minHealthPercent: 30
      splitExternalLocalOriginErrors: true
      consecutiveLocalOriginFailures: 5
      consecutiveGatewayErrors: 5

    # TLS settings
    tls:
      mode: ISTIO_MUTUAL

  # Subsets for versioning
  subsets:
    - name: v1
      labels:
        version: v1
      trafficPolicy:
        connectionPool:
          http:
            http2MaxRequests: 500

    - name: v2
      labels:
        version: v2
      trafficPolicy:
        connectionPool:
          http:
            http2MaxRequests: 1000
```

## policies/authorization-policy.yaml

```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: {services[0]}-authz
  namespace: {domain_key}
spec:
  selector:
    matchLabels:
      app: {services[0]}
  action: ALLOW
  rules:
    # Allow from API gateway
    - from:
        - source:
            principals: ["cluster.local/ns/{domain_key}/sa/api-gateway"]
      to:
        - operation:
            methods: ["GET", "POST", "PUT", "DELETE"]
            paths: ["/api/v1/*"]

    # Allow internal service communication
    - from:
        - source:
            namespaces: ["{domain_key}"]
      to:
        - operation:
            methods: ["GET", "POST"]
            paths: ["/internal/*"]

    # Allow health checks
    - to:
        - operation:
            methods: ["GET"]
            paths: ["/health", "/ready", "/metrics"]
---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: deny-all
  namespace: {domain_key}
spec:
  {{}}  # Deny all by default
---
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: allow-nothing
  namespace: {domain_key}
spec:
  selector:
    matchLabels:
      app: {services[3]}
  action: DENY
  rules:
    - from:
        - source:
            notNamespaces: ["{domain_key}"]
```

## policies/peer-authentication.yaml

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: {domain_key}
spec:
  mtls:
    mode: STRICT
---
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: {services[0]}-mtls
  namespace: {domain_key}
spec:
  selector:
    matchLabels:
      app: {services[0]}
  mtls:
    mode: STRICT
  portLevelMtls:
    8080:
      mode: PERMISSIVE  # Allow non-mTLS for health checks
```

## policies/request-authentication.yaml

```yaml
apiVersion: security.istio.io/v1beta1
kind: RequestAuthentication
metadata:
  name: jwt-auth
  namespace: {domain_key}
spec:
  selector:
    matchLabels:
      app: {services[0]}
  jwtRules:
    - issuer: "https://auth.{domain_key}.com"
      jwksUri: "https://auth.{domain_key}.com/.well-known/jwks.json"
      audiences:
        - "api.{domain_key}.com"
      forwardOriginalToken: true
      outputPayloadToHeader: x-jwt-payload
```

## traffic-management/rate-limit.yaml

```yaml
apiVersion: networking.istio.io/v1alpha3
kind: EnvoyFilter
metadata:
  name: {services[0]}-ratelimit
  namespace: {domain_key}
spec:
  workloadSelector:
    labels:
      app: {services[0]}
  configPatches:
    - applyTo: HTTP_FILTER
      match:
        context: SIDECAR_INBOUND
        listener:
          filterChain:
            filter:
              name: "envoy.filters.network.http_connection_manager"
      patch:
        operation: INSERT_BEFORE
        value:
          name: envoy.filters.http.local_ratelimit
          typed_config:
            "@type": type.googleapis.com/udpa.type.v1.TypedStruct
            type_url: type.googleapis.com/envoy.extensions.filters.http.local_ratelimit.v3.LocalRateLimit
            value:
              stat_prefix: http_local_rate_limiter
              token_bucket:
                max_tokens: 1000
                tokens_per_fill: 100
                fill_interval: 1s
              filter_enabled:
                runtime_key: local_rate_limit_enabled
                default_value:
                  numerator: 100
                  denominator: HUNDRED
              filter_enforced:
                runtime_key: local_rate_limit_enforced
                default_value:
                  numerator: 100
                  denominator: HUNDRED
              response_headers_to_add:
                - append: false
                  header:
                    key: x-rate-limit-remaining
                    value: "%DYNAMIC_METADATA(envoy.filters.http.local_ratelimit:tokens_remaining)%"
```

## observability/telemetry.yaml

```yaml
apiVersion: telemetry.istio.io/v1alpha1
kind: Telemetry
metadata:
  name: {domain_key}-telemetry
  namespace: {domain_key}
spec:
  # Access logging
  accessLogging:
    - providers:
        - name: envoy
      filter:
        expression: response.code >= 400 || request.url_path.contains("debug")

  # Tracing configuration
  tracing:
    - providers:
        - name: jaeger
      randomSamplingPercentage: 10.0
      customTags:
        service.name:
          literal:
            value: "{domain_key}"
        environment:
          header:
            name: x-environment
            defaultValue: production

  # Metrics configuration
  metrics:
    - providers:
        - name: prometheus
      overrides:
        - match:
            metric: REQUEST_COUNT
            mode: CLIENT_AND_SERVER
          tagOverrides:
            response_code:
              operation: UPSERT
            request_method:
              operation: UPSERT
```

## Deployment Commands

```bash
# Install Istio
istioctl install --set profile=production

# Enable namespace injection
kubectl label namespace {domain_key} istio-injection=enabled

# Apply configurations
kubectl apply -f istio-config/namespace.yaml
kubectl apply -f istio-config/gateway/
kubectl apply -f istio-config/virtual-services/
kubectl apply -f istio-config/destination-rules/
kubectl apply -f istio-config/policies/
kubectl apply -f istio-config/traffic-management/
kubectl apply -f istio-config/observability/

# Verify configuration
istioctl analyze -n {domain_key}

# Check proxy status
istioctl proxy-status

# Debug routing
istioctl proxy-config routes deploy/{services[0]} -n {domain_key}

# View Kiali dashboard
istioctl dashboard kiali

# View Jaeger tracing
istioctl dashboard jaeger

# View Grafana metrics
istioctl dashboard grafana
```

This Istio service mesh configuration includes:
- **Gateway** with TLS termination
- **VirtualServices** with canary, A/B testing, retries, timeouts
- **DestinationRules** with circuit breaker, load balancing, connection pooling
- **Authorization policies** for access control
- **mTLS** for service-to-service encryption
- **JWT authentication** for external requests
- **Rate limiting** with Envoy filters
- **Telemetry** for logging, tracing, and metrics
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in Istio service mesh and cloud-native architectures. Generate production-ready Istio configurations with traffic management, security, and observability."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": service_mesh_code}
        ]
    }


# ============================================================================
# MAIN GENERATOR
# ============================================================================

def generate_all_examples() -> List[Dict]:
    examples = []

    for domain_key in DOMAINS.keys():
        # Docker Compose
        examples.append(generate_docker_compose_example(domain_key))

        # Kubernetes
        examples.append(generate_kubernetes_example(domain_key))

        # gRPC
        examples.append(generate_grpc_example(domain_key))

        # Event-driven
        examples.append(generate_event_driven_example(domain_key))

        # Service Mesh
        examples.append(generate_service_mesh_example(domain_key))

    return examples


def save_examples(examples: List[Dict], output_dir: Path):
    output_dir.mkdir(exist_ok=True)

    # Split into train/eval
    random.shuffle(examples)
    eval_size = max(1, len(examples) // 10)

    eval_examples = examples[:eval_size]
    train_examples = examples[eval_size:]

    # Save train
    train_file = output_dir / "train.jsonl"
    with open(train_file, 'w', encoding='utf-8') as f:
        for ex in train_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    # Save eval
    eval_file = output_dir / "eval.jsonl"
    with open(eval_file, 'w', encoding='utf-8') as f:
        for ex in eval_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    print(f"Saved {len(train_examples)} train examples to {train_file}")
    print(f"Saved {len(eval_examples)} eval examples to {eval_file}")

    return train_examples, eval_examples


def main():
    print("=" * 70)
    print("GENERATING MICROSERVICES ARCHITECTURE EXAMPLES")
    print("=" * 70)

    print(f"\nDomains: {list(DOMAINS.keys())}")
    print(f"Example types: Docker Compose, Kubernetes, gRPC, Event-driven, Service Mesh")

    # Generate examples
    examples = generate_all_examples()
    print(f"\nGenerated {len(examples)} examples")

    # Save
    train_examples, eval_examples = save_examples(examples, OUTPUT_DIR)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total examples: {len(examples)}")
    print(f"Train: {len(train_examples)}")
    print(f"Eval: {len(eval_examples)}")
    print(f"Location: {OUTPUT_DIR}")

    # Count by type
    types = {
        "docker_compose": 0,
        "kubernetes": 0,
        "grpc": 0,
        "event_driven": 0,
        "service_mesh": 0,
    }

    for ex in examples:
        content = ex["messages"][-1]["content"].lower()
        if "docker-compose" in content:
            types["docker_compose"] += 1
        if "kubernetes" in content or "kubectl" in content:
            types["kubernetes"] += 1
        if "grpc" in content or "protobuf" in content:
            types["grpc"] += 1
        if "kafka" in content or "event-driven" in content:
            types["event_driven"] += 1
        if "istio" in content or "service mesh" in content:
            types["service_mesh"] += 1

    print("\nBy type:")
    for t, count in types.items():
        print(f"  {t}: {count}")


if __name__ == "__main__":
    main()
