#!/usr/bin/env python3
"""
Generate Comprehensive Microservices Architecture Training Examples
Target: 500+ examples covering all microservices patterns
"""

import json
import random
from pathlib import Path
from typing import List, Dict

OUTPUT_DIR = Path(__file__).parent / "microservices_comprehensive"

# ============================================================================
# EXPANDED DOMAINS (20 domains)
# ============================================================================

DOMAINS = {
    "ecommerce": {
        "name": "E-Commerce Platform",
        "services": ["user-service", "product-service", "order-service", "payment-service", "inventory-service", "notification-service", "cart-service", "review-service", "search-service", "recommendation-service"],
    },
    "fintech": {
        "name": "FinTech Banking Platform",
        "services": ["account-service", "transaction-service", "payment-service", "notification-service", "audit-service", "fraud-detection-service", "kyc-service", "loan-service", "investment-service", "report-service"],
    },
    "healthcare": {
        "name": "Healthcare Management System",
        "services": ["patient-service", "appointment-service", "doctor-service", "prescription-service", "billing-service", "notification-service", "lab-service", "pharmacy-service", "insurance-service", "report-service"],
    },
    "logistics": {
        "name": "Logistics & Delivery Platform",
        "services": ["shipment-service", "tracking-service", "warehouse-service", "driver-service", "route-service", "notification-service", "billing-service", "analytics-service", "fleet-service", "customer-service"],
    },
    "social_media": {
        "name": "Social Media Platform",
        "services": ["user-service", "post-service", "feed-service", "notification-service", "messaging-service", "media-service", "search-service", "analytics-service", "moderation-service", "ad-service"],
    },
    "iot_platform": {
        "name": "IoT Device Management Platform",
        "services": ["device-service", "telemetry-service", "alert-service", "command-service", "firmware-service", "analytics-service", "user-service", "notification-service", "rule-engine-service", "dashboard-service"],
    },
    "streaming": {
        "name": "Video Streaming Platform",
        "services": ["user-service", "content-service", "streaming-service", "recommendation-service", "search-service", "billing-service", "analytics-service", "cdn-service", "transcoding-service", "notification-service"],
    },
    "food_delivery": {
        "name": "Food Delivery Platform",
        "services": ["user-service", "restaurant-service", "order-service", "delivery-service", "payment-service", "notification-service", "rating-service", "search-service", "promo-service", "analytics-service"],
    },
    "travel": {
        "name": "Travel Booking Platform",
        "services": ["user-service", "flight-service", "hotel-service", "booking-service", "payment-service", "notification-service", "search-service", "review-service", "loyalty-service", "support-service"],
    },
    "education": {
        "name": "E-Learning Platform",
        "services": ["user-service", "course-service", "enrollment-service", "content-service", "assessment-service", "certificate-service", "payment-service", "notification-service", "analytics-service", "discussion-service"],
    },
    "real_estate": {
        "name": "Real Estate Platform",
        "services": ["user-service", "property-service", "listing-service", "booking-service", "payment-service", "notification-service", "search-service", "agent-service", "document-service", "analytics-service"],
    },
    "hr_management": {
        "name": "HR Management System",
        "services": ["employee-service", "recruitment-service", "payroll-service", "attendance-service", "leave-service", "performance-service", "training-service", "notification-service", "report-service", "document-service"],
    },
    "inventory": {
        "name": "Inventory Management System",
        "services": ["product-service", "warehouse-service", "order-service", "supplier-service", "shipping-service", "notification-service", "report-service", "barcode-service", "forecast-service", "audit-service"],
    },
    "crm": {
        "name": "CRM Platform",
        "services": ["contact-service", "lead-service", "opportunity-service", "account-service", "campaign-service", "email-service", "notification-service", "report-service", "integration-service", "analytics-service"],
    },
    "gaming": {
        "name": "Online Gaming Platform",
        "services": ["user-service", "game-service", "matchmaking-service", "leaderboard-service", "chat-service", "payment-service", "notification-service", "analytics-service", "reward-service", "moderation-service"],
    },
    "insurance": {
        "name": "Insurance Platform",
        "services": ["customer-service", "policy-service", "claim-service", "underwriting-service", "payment-service", "notification-service", "document-service", "agent-service", "fraud-service", "report-service"],
    },
    "marketplace": {
        "name": "Multi-Vendor Marketplace",
        "services": ["user-service", "vendor-service", "product-service", "order-service", "payment-service", "shipping-service", "review-service", "search-service", "notification-service", "dispute-service"],
    },
    "parking": {
        "name": "Smart Parking System",
        "services": ["user-service", "parking-service", "booking-service", "payment-service", "sensor-service", "notification-service", "analytics-service", "enforcement-service", "report-service", "integration-service"],
    },
    "telecom": {
        "name": "Telecom Platform",
        "services": ["customer-service", "subscription-service", "billing-service", "usage-service", "notification-service", "support-service", "network-service", "provisioning-service", "report-service", "analytics-service"],
    },
    "supply_chain": {
        "name": "Supply Chain Management",
        "services": ["supplier-service", "procurement-service", "inventory-service", "order-service", "shipping-service", "tracking-service", "warehouse-service", "analytics-service", "notification-service", "compliance-service"],
    },
}

# Architecture patterns
PATTERNS = [
    "docker_compose",
    "kubernetes",
    "grpc",
    "kafka",
    "rabbitmq",
    "service_mesh",
    "api_gateway",
    "circuit_breaker",
    "saga_pattern",
    "cqrs",
]


def generate_docker_compose(domain_key: str, services: List[str]) -> Dict:
    """Generate Docker Compose example"""
    svc_list = services[:6]

    prompt = f"Create a Docker Compose microservices setup for {DOMAINS[domain_key]['name']} with services: {', '.join(svc_list)}"

    compose_content = f"""version: '3.8'

services:
  # API Gateway
  api-gateway:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - {svc_list[0]}
      - {svc_list[1]}
    networks:
      - {domain_key}-net

  # Message Broker
  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: admin
      RABBITMQ_DEFAULT_PASS: password
    networks:
      - {domain_key}-net

  # Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - {domain_key}-net

  # Database
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: password
      POSTGRES_DB: {domain_key}_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - {domain_key}-net

  # Services
  {svc_list[0]}:
    build: ./{svc_list[0]}
    environment:
      - DATABASE_URL=postgresql://admin:password@postgres:5432/{svc_list[0].replace('-', '_')}_db
      - RABBITMQ_URL=amqp://admin:password@rabbitmq:5672
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - rabbitmq
      - redis
    networks:
      - {domain_key}-net

  {svc_list[1]}:
    build: ./{svc_list[1]}
    environment:
      - DATABASE_URL=postgresql://admin:password@postgres:5432/{svc_list[1].replace('-', '_')}_db
      - RABBITMQ_URL=amqp://admin:password@rabbitmq:5672
      - {svc_list[0].upper().replace('-', '_')}_URL=http://{svc_list[0]}:8000
    depends_on:
      - postgres
      - {svc_list[0]}
    networks:
      - {domain_key}-net

  {svc_list[2]}:
    build: ./{svc_list[2]}
    environment:
      - DATABASE_URL=postgresql://admin:password@postgres:5432/{svc_list[2].replace('-', '_')}_db
      - RABBITMQ_URL=amqp://admin:password@rabbitmq:5672
    depends_on:
      - postgres
      - rabbitmq
    networks:
      - {domain_key}-net

  {svc_list[3]}:
    build: ./{svc_list[3]}
    environment:
      - RABBITMQ_URL=amqp://admin:password@rabbitmq:5672
      - STRIPE_KEY=${{STRIPE_KEY}}
    depends_on:
      - rabbitmq
    networks:
      - {domain_key}-net

  {svc_list[4]}:
    build: ./{svc_list[4]}
    environment:
      - MONGODB_URL=mongodb://mongo:27017/{domain_key}
      - RABBITMQ_URL=amqp://admin:password@rabbitmq:5672
    depends_on:
      - mongo
      - rabbitmq
    networks:
      - {domain_key}-net

  {svc_list[5]}:
    build: ./{svc_list[5]}
    environment:
      - RABBITMQ_URL=amqp://admin:password@rabbitmq:5672
      - SMTP_HOST=mailhog
    depends_on:
      - rabbitmq
      - mailhog
    networks:
      - {domain_key}-net

  # MongoDB for document storage
  mongo:
    image: mongo:6
    volumes:
      - mongo_data:/data/db
    networks:
      - {domain_key}-net

  # Email testing
  mailhog:
    image: mailhog/mailhog
    ports:
      - "8025:8025"
    networks:
      - {domain_key}-net

networks:
  {domain_key}-net:
    driver: bridge

volumes:
  postgres_data:
  mongo_data:
"""

    response = f"""I'll create a Docker Compose microservices setup for {DOMAINS[domain_key]['name']}.

## docker-compose.yml

```yaml
{compose_content}
```

## Service Implementation - {svc_list[0]}/main.py

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import aio_pika
import redis.asyncio as redis

app = FastAPI(title="{svc_list[0].replace('-', ' ').title()} API")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# RabbitMQ publisher
async def publish_event(event_type: str, data: dict):
    connection = await aio_pika.connect_robust(os.getenv("RABBITMQ_URL"))
    async with connection:
        channel = await connection.channel()
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps({{"type": event_type, "data": data}}).encode()),
            routing_key="{domain_key}_events"
        )

@app.get("/health")
async def health():
    return {{"status": "healthy", "service": "{svc_list[0]}"}}

@app.post("/api/v1/{svc_list[0].split('-')[0]}s")
async def create(data: dict, db: Session = Depends(get_db)):
    # Create record
    item = Model(**data)
    db.add(item)
    db.commit()

    # Publish event
    await publish_event("{svc_list[0].split('-')[0]}_created", {{"id": str(item.id)}})

    return item
```

## Run Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f {svc_list[0]}

# Scale service
docker-compose up -d --scale {svc_list[0]}=3

# Stop
docker-compose down -v
```
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in microservices architecture and Docker. Generate production-ready Docker Compose configurations."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_kubernetes(domain_key: str, services: List[str]) -> Dict:
    """Generate Kubernetes manifests"""
    svc = services[0]

    prompt = f"Create Kubernetes deployment manifests for {svc} in {DOMAINS[domain_key]['name']} with Deployment, Service, HPA, and ConfigMap"

    response = f"""I'll create Kubernetes manifests for {svc}.

## deployment.yaml

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {svc}
  namespace: {domain_key}
  labels:
    app: {svc}
spec:
  replicas: 3
  selector:
    matchLabels:
      app: {svc}
  template:
    metadata:
      labels:
        app: {svc}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
    spec:
      containers:
        - name: {svc}
          image: {domain_key}/{svc}:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: {svc}-config
            - secretRef:
                name: {svc}-secrets
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

## service.yaml

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {svc}
  namespace: {domain_key}
spec:
  type: ClusterIP
  ports:
    - port: 8000
      targetPort: 8000
  selector:
    app: {svc}
```

## hpa.yaml

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {svc}-hpa
  namespace: {domain_key}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {svc}
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

## configmap.yaml

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: {svc}-config
  namespace: {domain_key}
data:
  LOG_LEVEL: "INFO"
  SERVICE_NAME: "{svc}"
  RABBITMQ_HOST: "rabbitmq.{domain_key}.svc.cluster.local"
  REDIS_HOST: "redis.{domain_key}.svc.cluster.local"
```

## Deploy

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f hpa.yaml
kubectl apply -f configmap.yaml
```
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in Kubernetes. Generate production-ready K8s manifests."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_kafka_consumer(domain_key: str, services: List[str]) -> Dict:
    """Generate Kafka consumer example"""
    svc = services[0]
    event = f"{svc.split('-')[0]}_created"

    prompt = f"Create a Kafka consumer for {svc} in {DOMAINS[domain_key]['name']} that processes {event} events"

    response = f"""I'll create a Kafka consumer for {svc}.

## consumer.py

```python
import asyncio
import json
from aiokafka import AIOKafkaConsumer
from prometheus_client import Counter, Histogram

# Metrics
EVENTS_PROCESSED = Counter('events_processed_total', 'Total events', ['event_type', 'status'])
PROCESSING_TIME = Histogram('event_processing_seconds', 'Processing time', ['event_type'])

class {svc.replace('-', ' ').title().replace(' ', '')}Consumer:
    def __init__(self):
        self.consumer = None
        self.running = False

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            '{domain_key}.events.{event}',
            bootstrap_servers='kafka:9092',
            group_id='{svc}-consumer-group',
            auto_offset_reset='earliest',
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        await self.consumer.start()
        self.running = True

        try:
            async for msg in self.consumer:
                await self.process_message(msg)
        finally:
            await self.consumer.stop()

    async def process_message(self, msg):
        event_type = msg.value.get('event_type', 'unknown')

        with PROCESSING_TIME.labels(event_type=event_type).time():
            try:
                await self.handle_event(msg.value)
                await self.consumer.commit()
                EVENTS_PROCESSED.labels(event_type=event_type, status='success').inc()
            except Exception as e:
                EVENTS_PROCESSED.labels(event_type=event_type, status='failed').inc()
                await self.send_to_dlq(msg, str(e))

    async def handle_event(self, event: dict):
        data = event.get('data', {{}})
        print(f"Processing event: {{data.get('id')}}")
        # Business logic here
        await asyncio.sleep(0.1)

    async def send_to_dlq(self, msg, error: str):
        # Send to dead letter queue
        pass

async def main():
    consumer = {svc.replace('-', ' ').title().replace(' ', '')}Consumer()
    await consumer.start()

if __name__ == "__main__":
    asyncio.run(main())
```

## docker-compose.yml (Kafka setup)

```yaml
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  {svc}:
    build: ./{svc}
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:29092
    depends_on:
      - kafka
```
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in Apache Kafka and event-driven architecture."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_grpc_service(domain_key: str, services: List[str]) -> Dict:
    """Generate gRPC service example"""
    svc = services[0]
    entity = svc.split('-')[0].title()

    prompt = f"Create a gRPC service for {svc} in {DOMAINS[domain_key]['name']} with proto file and Python implementation"

    response = f"""I'll create a gRPC service for {svc}.

## {svc.replace('-', '_')}.proto

```protobuf
syntax = "proto3";

package {domain_key}.{svc.replace('-', '_')};

service {entity}Service {{
    rpc Create{entity}(Create{entity}Request) returns (Create{entity}Response);
    rpc Get{entity}(Get{entity}Request) returns (Get{entity}Response);
    rpc List{entity}s(List{entity}sRequest) returns (List{entity}sResponse);
    rpc Update{entity}(Update{entity}Request) returns (Update{entity}Response);
    rpc Delete{entity}(Delete{entity}Request) returns (Delete{entity}Response);
    rpc Watch{entity}s(Empty) returns (stream {entity}Event);
}}

message {entity} {{
    string id = 1;
    string name = 2;
    string status = 3;
    int64 created_at = 4;
}}

message Create{entity}Request {{
    string name = 1;
}}

message Create{entity}Response {{
    {entity} {entity.lower()} = 1;
}}

message Get{entity}Request {{
    string id = 1;
}}

message Get{entity}Response {{
    {entity} {entity.lower()} = 1;
}}

message List{entity}sRequest {{
    int32 page = 1;
    int32 page_size = 2;
}}

message List{entity}sResponse {{
    repeated {entity} {entity.lower()}s = 1;
    int32 total = 2;
}}

message Update{entity}Request {{
    string id = 1;
    string name = 2;
    string status = 3;
}}

message Update{entity}Response {{
    {entity} {entity.lower()} = 1;
}}

message Delete{entity}Request {{
    string id = 1;
}}

message Delete{entity}Response {{
    bool success = 1;
}}

message {entity}Event {{
    string event_type = 1;
    {entity} {entity.lower()} = 2;
}}

message Empty {{}}
```

## server.py

```python
import grpc
from concurrent import futures
import {svc.replace('-', '_')}_pb2 as pb2
import {svc.replace('-', '_')}_pb2_grpc as pb2_grpc

class {entity}Servicer(pb2_grpc.{entity}ServiceServicer):
    def __init__(self):
        self.db = {{}}

    def Create{entity}(self, request, context):
        import uuid
        id = str(uuid.uuid4())
        {entity.lower()} = pb2.{entity}(
            id=id,
            name=request.name,
            status="active",
            created_at=int(time.time())
        )
        self.db[id] = {entity.lower()}
        return pb2.Create{entity}Response({entity.lower()}={entity.lower()})

    def Get{entity}(self, request, context):
        {entity.lower()} = self.db.get(request.id)
        if not {entity.lower()}:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            return pb2.Get{entity}Response()
        return pb2.Get{entity}Response({entity.lower()}={entity.lower()})

    def List{entity}s(self, request, context):
        items = list(self.db.values())
        start = (request.page - 1) * request.page_size
        end = start + request.page_size
        return pb2.List{entity}sResponse(
            {entity.lower()}s=items[start:end],
            total=len(items)
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_{entity}ServiceServicer_to_server({entity}Servicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()

if __name__ == '__main__':
    serve()
```

## client.py

```python
import grpc
import {svc.replace('-', '_')}_pb2 as pb2
import {svc.replace('-', '_')}_pb2_grpc as pb2_grpc

class {entity}Client:
    def __init__(self, host='localhost', port=50051):
        self.channel = grpc.insecure_channel(f'{{host}}:{{port}}')
        self.stub = pb2_grpc.{entity}ServiceStub(self.channel)

    def create(self, name: str):
        response = self.stub.Create{entity}(pb2.Create{entity}Request(name=name))
        return response.{entity.lower()}

    def get(self, id: str):
        response = self.stub.Get{entity}(pb2.Get{entity}Request(id=id))
        return response.{entity.lower()}

    def list(self, page=1, page_size=10):
        response = self.stub.List{entity}s(pb2.List{entity}sRequest(page=page, page_size=page_size))
        return response.{entity.lower()}s
```
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in gRPC and Protocol Buffers."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_saga_pattern(domain_key: str, services: List[str]) -> Dict:
    """Generate Saga pattern example"""
    prompt = f"Implement the Saga pattern for {DOMAINS[domain_key]['name']} order processing across {services[0]}, {services[1]}, {services[2]}"

    response = f"""I'll implement the Saga pattern for distributed transaction management.

## saga_orchestrator.py

```python
import asyncio
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any
import aio_pika

class SagaState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    FAILED = "failed"

@dataclass
class SagaStep:
    name: str
    service: str
    action: str
    compensation: str

@dataclass
class Saga:
    id: str
    state: SagaState
    current_step: int
    steps: List[SagaStep]
    data: Dict[str, Any]
    completed_steps: List[str]

class SagaOrchestrator:
    def __init__(self):
        self.sagas: Dict[str, Saga] = {{}}
        self.rabbitmq = None

    async def start_saga(self, saga_id: str, data: dict) -> Saga:
        saga = Saga(
            id=saga_id,
            state=SagaState.PENDING,
            current_step=0,
            steps=[
                SagaStep("{services[0]}", "{services[0]}", "create_{services[0].split('-')[0]}", "cancel_{services[0].split('-')[0]}"),
                SagaStep("{services[1]}", "{services[1]}", "reserve_{services[1].split('-')[0]}", "release_{services[1].split('-')[0]}"),
                SagaStep("{services[2]}", "{services[2]}", "process_{services[2].split('-')[0]}", "refund_{services[2].split('-')[0]}"),
            ],
            data=data,
            completed_steps=[]
        )
        self.sagas[saga_id] = saga
        await self.execute_saga(saga)
        return saga

    async def execute_saga(self, saga: Saga):
        saga.state = SagaState.RUNNING

        for i, step in enumerate(saga.steps):
            saga.current_step = i
            try:
                await self.execute_step(saga, step)
                saga.completed_steps.append(step.name)
            except Exception as e:
                print(f"Step {{step.name}} failed: {{e}}")
                await self.compensate(saga)
                return

        saga.state = SagaState.COMPLETED

    async def execute_step(self, saga: Saga, step: SagaStep):
        # Send command to service
        await self.send_command(step.service, {{
            "saga_id": saga.id,
            "action": step.action,
            "data": saga.data
        }})

        # Wait for response (with timeout)
        response = await self.wait_for_response(saga.id, step.name, timeout=30)
        if not response.get("success"):
            raise Exception(response.get("error", "Step failed"))

    async def compensate(self, saga: Saga):
        saga.state = SagaState.COMPENSATING

        # Execute compensations in reverse order
        for step_name in reversed(saga.completed_steps):
            step = next(s for s in saga.steps if s.name == step_name)
            try:
                await self.send_command(step.service, {{
                    "saga_id": saga.id,
                    "action": step.compensation,
                    "data": saga.data
                }})
            except Exception as e:
                print(f"Compensation {{step.name}} failed: {{e}}")

        saga.state = SagaState.FAILED

    async def send_command(self, service: str, command: dict):
        connection = await aio_pika.connect_robust("amqp://admin:password@rabbitmq:5672")
        async with connection:
            channel = await connection.channel()
            await channel.default_exchange.publish(
                aio_pika.Message(body=json.dumps(command).encode()),
                routing_key=f"{{service}}.commands"
            )

    async def wait_for_response(self, saga_id: str, step_name: str, timeout: int):
        # Implement response waiting logic
        await asyncio.sleep(0.1)
        return {{"success": True}}

# Usage
async def process_order(order_data: dict):
    orchestrator = SagaOrchestrator()
    saga = await orchestrator.start_saga(
        saga_id=str(uuid.uuid4()),
        data=order_data
    )
    return saga
```

## Service participant example

```python
# {services[0]}/saga_handler.py

class SagaParticipant:
    async def handle_command(self, command: dict):
        action = command["action"]
        saga_id = command["saga_id"]
        data = command["data"]

        try:
            if action == "create_{services[0].split('-')[0]}":
                result = await self.create(data)
            elif action == "cancel_{services[0].split('-')[0]}":
                result = await self.cancel(data)
            else:
                raise ValueError(f"Unknown action: {{action}}")

            await self.send_response(saga_id, {{"success": True, "result": result}})
        except Exception as e:
            await self.send_response(saga_id, {{"success": False, "error": str(e)}})

    async def create(self, data: dict):
        # Create logic
        return {{"id": "123"}}

    async def cancel(self, data: dict):
        # Compensation logic
        return {{"cancelled": True}}
```

This Saga pattern implementation provides:
- Distributed transaction management
- Automatic compensation on failure
- Step-by-step execution tracking
- Message-based communication
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in distributed systems and microservices patterns."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_circuit_breaker(domain_key: str, services: List[str]) -> Dict:
    """Generate Circuit Breaker pattern"""
    svc = services[0]

    prompt = f"Implement Circuit Breaker pattern for {svc} in {DOMAINS[domain_key]['name']}"

    response = f"""I'll implement the Circuit Breaker pattern for {svc}.

## circuit_breaker.py

```python
import time
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Any
from functools import wraps

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: int = 30
    half_open_max_calls: int = 3

    state: CircuitState = field(default=CircuitState.CLOSED)
    failure_count: int = field(default=0)
    success_count: int = field(default=0)
    last_failure_time: float = field(default=0)
    half_open_calls: int = field(default=0)

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                return True
            return False
        else:  # HALF_OPEN
            return self.half_open_calls < self.half_open_max_calls

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        else:
            self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

def circuit_breaker(cb: CircuitBreaker):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not cb.can_execute():
                raise CircuitBreakerOpen(f"Circuit breaker is {{cb.state.value}}")

            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                cb.record_success()
                return result
            except Exception as e:
                cb.record_failure()
                raise
        return wrapper
    return decorator

class CircuitBreakerOpen(Exception):
    pass

# Usage in {svc}
{svc.replace('-', '_')}_cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

@circuit_breaker({svc.replace('-', '_')}_cb)
async def call_{svc.replace('-', '_')}(data: dict):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://{svc}:8000/api/v1/action",
            json=data,
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()

# FastAPI middleware
from fastapi import Request, HTTPException

async def circuit_breaker_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except CircuitBreakerOpen as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
```

## With metrics

```python
from prometheus_client import Counter, Gauge

CIRCUIT_STATE = Gauge('{svc.replace('-', '_')}_circuit_state', 'Circuit breaker state', ['service'])
CIRCUIT_FAILURES = Counter('{svc.replace('-', '_')}_circuit_failures', 'Circuit breaker failures', ['service'])

class MonitoredCircuitBreaker(CircuitBreaker):
    def __init__(self, service_name: str, **kwargs):
        super().__init__(**kwargs)
        self.service_name = service_name
        self._update_metrics()

    def record_failure(self):
        super().record_failure()
        CIRCUIT_FAILURES.labels(service=self.service_name).inc()
        self._update_metrics()

    def _update_metrics(self):
        state_value = {{"closed": 0, "open": 1, "half_open": 0.5}}[self.state.value]
        CIRCUIT_STATE.labels(service=self.service_name).set(state_value)
```
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in microservices resilience patterns."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_api_gateway(domain_key: str, services: List[str]) -> Dict:
    """Generate API Gateway configuration"""
    svc_list = services[:5]

    prompt = f"Create API Gateway configuration (Kong/Nginx) for {DOMAINS[domain_key]['name']} routing to {', '.join(svc_list)}"

    response = f"""I'll create API Gateway configurations for {DOMAINS[domain_key]['name']}.

## Kong Configuration (kong.yml)

```yaml
_format_version: "3.0"

services:
  - name: {svc_list[0]}
    url: http://{svc_list[0]}:8000
    routes:
      - name: {svc_list[0]}-route
        paths:
          - /api/v1/{svc_list[0].split('-')[0]}s
        strip_path: false
    plugins:
      - name: rate-limiting
        config:
          minute: 100
          policy: local
      - name: jwt
      - name: correlation-id
        config:
          header_name: X-Request-ID
          generator: uuid

  - name: {svc_list[1]}
    url: http://{svc_list[1]}:8000
    routes:
      - name: {svc_list[1]}-route
        paths:
          - /api/v1/{svc_list[1].split('-')[0]}s
    plugins:
      - name: rate-limiting
        config:
          minute: 200

  - name: {svc_list[2]}
    url: http://{svc_list[2]}:8000
    routes:
      - name: {svc_list[2]}-route
        paths:
          - /api/v1/{svc_list[2].split('-')[0]}s

consumers:
  - username: api-user
    jwt_secrets:
      - key: api-key
        secret: your-secret-key

plugins:
  - name: prometheus
  - name: cors
    config:
      origins:
        - "*"
      methods:
        - GET
        - POST
        - PUT
        - DELETE
      headers:
        - Authorization
        - Content-Type
```

## Nginx Configuration (nginx.conf)

```nginx
upstream {svc_list[0].replace('-', '_')} {{
    least_conn;
    server {svc_list[0]}:8000 weight=5;
    server {svc_list[0]}-2:8000 weight=5;
    keepalive 32;
}}

upstream {svc_list[1].replace('-', '_')} {{
    least_conn;
    server {svc_list[1]}:8000;
    keepalive 32;
}}

upstream {svc_list[2].replace('-', '_')} {{
    server {svc_list[2]}:8000;
}}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;

server {{
    listen 80;
    server_name api.{domain_key}.com;

    # Health check
    location /health {{
        return 200 'OK';
    }}

    # {svc_list[0]} routes
    location /api/v1/{svc_list[0].split('-')[0]}s {{
        limit_req zone=api_limit burst=50 nodelay;

        proxy_pass http://{svc_list[0].replace('-', '_')};
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Request-ID $request_id;

        # Timeouts
        proxy_connect_timeout 5s;
        proxy_read_timeout 30s;

        # Circuit breaker
        proxy_next_upstream error timeout http_500 http_502 http_503;
        proxy_next_upstream_tries 3;
    }}

    # {svc_list[1]} routes
    location /api/v1/{svc_list[1].split('-')[0]}s {{
        proxy_pass http://{svc_list[1].replace('-', '_')};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}

    # {svc_list[2]} routes
    location /api/v1/{svc_list[2].split('-')[0]}s {{
        proxy_pass http://{svc_list[2].replace('-', '_')};
        proxy_set_header Host $host;
    }}

    # Error pages
    error_page 502 503 504 /50x.html;
    location = /50x.html {{
        return 503 '{{"error": "Service temporarily unavailable"}}';
        add_header Content-Type application/json;
    }}
}}
```

## docker-compose.yml

```yaml
version: '3.8'
services:
  kong:
    image: kong:3.4
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /kong/kong.yml
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
    volumes:
      - ./kong.yml:/kong/kong.yml
    ports:
      - "8000:8000"
      - "8001:8001"
```
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in API Gateway and reverse proxy configurations."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_cqrs(domain_key: str, services: List[str]) -> Dict:
    """Generate CQRS pattern example"""
    svc = services[0]
    entity = svc.split('-')[0].title()

    prompt = f"Implement CQRS (Command Query Responsibility Segregation) for {svc} in {DOMAINS[domain_key]['name']}"

    response = f"""I'll implement CQRS for {svc}.

## Project Structure

```
{svc}/
├── commands/
│   ├── __init__.py
│   ├── handlers.py
│   └── models.py
├── queries/
│   ├── __init__.py
│   ├── handlers.py
│   └── models.py
├── events/
│   ├── __init__.py
│   └── handlers.py
├── write_db/
│   └── models.py
├── read_db/
│   └── models.py
└── main.py
```

## commands/models.py

```python
from pydantic import BaseModel
from typing import Optional

class Create{entity}Command(BaseModel):
    name: str
    email: str

class Update{entity}Command(BaseModel):
    id: str
    name: Optional[str] = None
    email: Optional[str] = None

class Delete{entity}Command(BaseModel):
    id: str
```

## commands/handlers.py

```python
from typing import Dict
import uuid
from events.handlers import EventPublisher

class CommandHandler:
    def __init__(self, write_db, event_publisher: EventPublisher):
        self.write_db = write_db
        self.event_publisher = event_publisher

    async def handle_create(self, command: Create{entity}Command) -> str:
        # Create in write database
        {entity.lower()}_id = str(uuid.uuid4())
        await self.write_db.insert({{
            "id": {entity.lower()}_id,
            "name": command.name,
            "email": command.email,
            "version": 1
        }})

        # Publish event for read model update
        await self.event_publisher.publish("{entity}Created", {{
            "id": {entity.lower()}_id,
            "name": command.name,
            "email": command.email
        }})

        return {entity.lower()}_id

    async def handle_update(self, command: Update{entity}Command):
        # Get current state
        current = await self.write_db.find_one({{"id": command.id}})
        if not current:
            raise ValueError("{entity} not found")

        # Apply update
        updates = command.dict(exclude_unset=True, exclude={{"id"}})
        updates["version"] = current["version"] + 1

        # Optimistic locking
        result = await self.write_db.update_one(
            {{"id": command.id, "version": current["version"]}},
            {{"$set": updates}}
        )

        if result.modified_count == 0:
            raise ValueError("Concurrent modification detected")

        # Publish event
        await self.event_publisher.publish("{entity}Updated", {{
            "id": command.id,
            **updates
        }})
```

## queries/handlers.py

```python
from typing import List, Optional
from queries.models import {entity}ReadModel, {entity}ListResponse

class QueryHandler:
    def __init__(self, read_db):
        self.read_db = read_db

    async def get_{entity.lower()}(self, id: str) -> Optional[{entity}ReadModel]:
        result = await self.read_db.find_one({{"id": id}})
        if result:
            return {entity}ReadModel(**result)
        return None

    async def list_{entity.lower()}s(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> {entity}ListResponse:
        query = {{}}
        if search:
            query["$text"] = {{"$search": search}}

        total = await self.read_db.count_documents(query)
        items = await self.read_db.find(query) \\
            .skip((page - 1) * page_size) \\
            .limit(page_size) \\
            .to_list(page_size)

        return {entity}ListResponse(
            items=[{entity}ReadModel(**item) for item in items],
            total=total,
            page=page,
            page_size=page_size
        )
```

## events/handlers.py

```python
import json
import aio_pika

class EventPublisher:
    def __init__(self, rabbitmq_url: str):
        self.rabbitmq_url = rabbitmq_url

    async def publish(self, event_type: str, data: dict):
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        async with connection:
            channel = await connection.channel()
            exchange = await channel.declare_exchange(
                "{domain_key}_events",
                aio_pika.ExchangeType.TOPIC,
                durable=True
            )

            message = aio_pika.Message(
                body=json.dumps({{
                    "event_type": event_type,
                    "data": data
                }}).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )

            await exchange.publish(message, routing_key=event_type)

class ReadModelUpdater:
    def __init__(self, read_db):
        self.read_db = read_db

    async def handle_{entity.lower()}_created(self, event: dict):
        await self.read_db.insert_one({{
            "id": event["data"]["id"],
            "name": event["data"]["name"],
            "email": event["data"]["email"],
            "created_at": datetime.utcnow()
        }})

    async def handle_{entity.lower()}_updated(self, event: dict):
        await self.read_db.update_one(
            {{"id": event["data"]["id"]}},
            {{"$set": event["data"]}}
        )
```

## main.py (FastAPI)

```python
from fastapi import FastAPI, HTTPException
from commands.handlers import CommandHandler
from queries.handlers import QueryHandler

app = FastAPI()

# Initialize handlers
command_handler = CommandHandler(write_db, event_publisher)
query_handler = QueryHandler(read_db)

# Commands (Write)
@app.post("/api/v1/{entity.lower()}s")
async def create_{entity.lower()}(command: Create{entity}Command):
    id = await command_handler.handle_create(command)
    return {{"id": id}}

@app.put("/api/v1/{entity.lower()}s/{{id}}")
async def update_{entity.lower()}(id: str, command: Update{entity}Command):
    command.id = id
    await command_handler.handle_update(command)
    return {{"status": "updated"}}

# Queries (Read)
@app.get("/api/v1/{entity.lower()}s/{{id}}")
async def get_{entity.lower()}(id: str):
    result = await query_handler.get_{entity.lower()}(id)
    if not result:
        raise HTTPException(status_code=404)
    return result

@app.get("/api/v1/{entity.lower()}s")
async def list_{entity.lower()}s(page: int = 1, page_size: int = 20):
    return await query_handler.list_{entity.lower()}s(page, page_size)
```

CQRS benefits:
- Separate read/write models for optimization
- Event sourcing support
- Independent scaling of read/write sides
- Eventual consistency with event-driven updates
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in CQRS and event sourcing patterns."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_service_discovery(domain_key: str, services: List[str]) -> Dict:
    """Generate Service Discovery example"""
    prompt = f"Implement service discovery using Consul for {DOMAINS[domain_key]['name']} microservices"

    response = f"""I'll implement service discovery using Consul.

## docker-compose.yml

```yaml
version: '3.8'
services:
  consul:
    image: consul:1.15
    ports:
      - "8500:8500"
      - "8600:8600/udp"
    command: agent -server -bootstrap-expect=1 -ui -client=0.0.0.0
    networks:
      - {domain_key}-net

  {services[0]}:
    build: ./{services[0]}
    environment:
      - CONSUL_HTTP_ADDR=consul:8500
      - SERVICE_NAME={services[0]}
      - SERVICE_PORT=8000
    depends_on:
      - consul
    networks:
      - {domain_key}-net

  {services[1]}:
    build: ./{services[1]}
    environment:
      - CONSUL_HTTP_ADDR=consul:8500
      - SERVICE_NAME={services[1]}
      - SERVICE_PORT=8000
    depends_on:
      - consul
    networks:
      - {domain_key}-net

networks:
  {domain_key}-net:
```

## service_registry.py

```python
import consul
import socket
import os
import asyncio
from typing import Optional, List

class ServiceRegistry:
    def __init__(self):
        self.consul = consul.Consul(
            host=os.getenv("CONSUL_HTTP_ADDR", "localhost").split(":")[0],
            port=int(os.getenv("CONSUL_HTTP_ADDR", "localhost:8500").split(":")[-1])
        )
        self.service_id = None

    def register(self, name: str, port: int, tags: List[str] = None):
        hostname = socket.gethostname()
        self.service_id = f"{{name}}-{{hostname}}"

        self.consul.agent.service.register(
            name=name,
            service_id=self.service_id,
            address=hostname,
            port=port,
            tags=tags or [],
            check=consul.Check.http(
                f"http://{{hostname}}:{{port}}/health",
                interval="10s",
                timeout="5s",
                deregister="1m"
            )
        )
        print(f"Registered service: {{self.service_id}}")

    def deregister(self):
        if self.service_id:
            self.consul.agent.service.deregister(self.service_id)
            print(f"Deregistered service: {{self.service_id}}")

    def discover(self, service_name: str) -> Optional[str]:
        _, services = self.consul.health.service(service_name, passing=True)
        if services:
            service = services[0]["Service"]
            return f"http://{{service['Address']}}:{{service['Port']}}"
        return None

    def discover_all(self, service_name: str) -> List[str]:
        _, services = self.consul.health.service(service_name, passing=True)
        return [
            f"http://{{s['Service']['Address']}}:{{s['Service']['Port']}}"
            for s in services
        ]

# Service client with discovery
class ServiceClient:
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.cache = {{}}
        self.cache_ttl = 30

    async def call(self, service_name: str, path: str, method: str = "GET", **kwargs):
        url = self.registry.discover(service_name)
        if not url:
            raise Exception(f"Service {{service_name}} not found")

        async with httpx.AsyncClient() as client:
            response = await client.request(method, f"{{url}}{{path}}", **kwargs)
            return response.json()

# Usage in FastAPI
from fastapi import FastAPI
from contextlib import asynccontextmanager

registry = ServiceRegistry()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Register on startup
    registry.register(
        name=os.getenv("SERVICE_NAME"),
        port=int(os.getenv("SERVICE_PORT", 8000)),
        tags=["api", "v1"]
    )
    yield
    # Deregister on shutdown
    registry.deregister()

app = FastAPI(lifespan=lifespan)

@app.get("/call-{services[1].split('-')[0]}")
async def call_other_service():
    client = ServiceClient(registry)
    return await client.call("{services[1]}", "/api/v1/data")
```

## Load balancing with discovered services

```python
import random
from typing import List

class LoadBalancer:
    def __init__(self, registry: ServiceRegistry):
        self.registry = registry

    def round_robin(self, service_name: str) -> str:
        urls = self.registry.discover_all(service_name)
        if not urls:
            raise Exception(f"No instances of {{service_name}}")
        # Simple round-robin (use redis for distributed)
        return urls[hash(time.time()) % len(urls)]

    def random(self, service_name: str) -> str:
        urls = self.registry.discover_all(service_name)
        return random.choice(urls)
```
"""

    return {
        "messages": [
            {"role": "system", "content": "You are an expert in service discovery and microservices."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
    }


def generate_all_examples() -> List[Dict]:
    """Generate all microservices examples"""
    examples = []

    for domain_key, domain in DOMAINS.items():
        services = domain["services"]

        # Docker Compose (2 variants)
        examples.append(generate_docker_compose(domain_key, services))
        examples.append(generate_docker_compose(domain_key, services[3:]))

        # Kubernetes (for each service)
        for svc in services[:4]:
            examples.append(generate_kubernetes(domain_key, [svc] + services))

        # Kafka consumers
        for svc in services[:3]:
            examples.append(generate_kafka_consumer(domain_key, [svc] + services))

        # gRPC
        for svc in services[:2]:
            examples.append(generate_grpc_service(domain_key, [svc] + services))

        # Saga pattern
        examples.append(generate_saga_pattern(domain_key, services))

        # Circuit breaker
        for svc in services[:2]:
            examples.append(generate_circuit_breaker(domain_key, [svc] + services))

        # API Gateway
        examples.append(generate_api_gateway(domain_key, services))

        # CQRS
        examples.append(generate_cqrs(domain_key, services))

        # Service Discovery
        examples.append(generate_service_discovery(domain_key, services))

    return examples


def main():
    print("=" * 70)
    print("GENERATING COMPREHENSIVE MICROSERVICES EXAMPLES")
    print("=" * 70)

    examples = generate_all_examples()
    print(f"\nGenerated {len(examples)} examples")

    # Save
    OUTPUT_DIR.mkdir(exist_ok=True)

    random.shuffle(examples)
    eval_size = max(10, len(examples) // 10)

    eval_examples = examples[:eval_size]
    train_examples = examples[eval_size:]

    with open(OUTPUT_DIR / "train.jsonl", 'w', encoding='utf-8') as f:
        for ex in train_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    with open(OUTPUT_DIR / "eval.jsonl", 'w', encoding='utf-8') as f:
        for ex in eval_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + '\n')

    print(f"\nSaved to {OUTPUT_DIR}")
    print(f"  Train: {len(train_examples)}")
    print(f"  Eval: {len(eval_examples)}")


if __name__ == "__main__":
    main()
