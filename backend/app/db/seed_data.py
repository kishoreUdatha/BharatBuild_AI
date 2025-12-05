"""
Database Seed Data Module

Comprehensive sample data for all models with dynamic pagination support.
Run with: python -m app.db.seed_data
"""
import asyncio
import random
from datetime import datetime, timedelta
from typing import List
import uuid

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, init_db
from app.models.user import User, UserRole
from app.models.project import Project, ProjectStatus, ProjectMode
from app.models.workspace import Workspace
from app.models.project_file import ProjectFile
from app.models.api_key import APIKey, APIKeyStatus
from app.models.billing import Subscription, Plan, Transaction
from app.models.college import College, Faculty, Batch, Student
from app.models.document import Document, DocumentType
from app.models.agent_task import AgentTask, AgentTaskStatus
from app.models.token_balance import TokenBalance, TokenTransaction, TokenPurchase
from app.models.usage import UsageLog, TokenUsage

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ==================== Sample Data Constants ====================

SAMPLE_USERS = [
    # Students
    {"email": "student1@college.edu", "full_name": "Rahul Sharma", "role": UserRole.STUDENT, "organization": "IIT Delhi"},
    {"email": "student2@college.edu", "full_name": "Priya Patel", "role": UserRole.STUDENT, "organization": "NIT Trichy"},
    {"email": "student3@college.edu", "full_name": "Amit Kumar", "role": UserRole.STUDENT, "organization": "BITS Pilani"},
    {"email": "student4@college.edu", "full_name": "Sneha Reddy", "role": UserRole.STUDENT, "organization": "VIT Vellore"},
    {"email": "student5@college.edu", "full_name": "Vikram Singh", "role": UserRole.STUDENT, "organization": "DTU Delhi"},
    {"email": "student6@college.edu", "full_name": "Ananya Gupta", "role": UserRole.STUDENT, "organization": "IIIT Hyderabad"},
    {"email": "student7@college.edu", "full_name": "Rohan Mehta", "role": UserRole.STUDENT, "organization": "SRM Chennai"},
    {"email": "student8@college.edu", "full_name": "Kavya Nair", "role": UserRole.STUDENT, "organization": "Manipal University"},

    # Developers
    {"email": "dev1@company.com", "full_name": "Arjun Verma", "role": UserRole.DEVELOPER, "organization": "TechCorp India"},
    {"email": "dev2@company.com", "full_name": "Meera Shah", "role": UserRole.DEVELOPER, "organization": "Infosys"},
    {"email": "dev3@company.com", "full_name": "Karthik Rajan", "role": UserRole.DEVELOPER, "organization": "Wipro"},
    {"email": "dev4@company.com", "full_name": "Divya Krishnan", "role": UserRole.DEVELOPER, "organization": "TCS"},
    {"email": "dev5@company.com", "full_name": "Suresh Babu", "role": UserRole.DEVELOPER, "organization": "HCL Tech"},

    # Founders
    {"email": "founder1@startup.io", "full_name": "Aditya Rao", "role": UserRole.FOUNDER, "organization": "InnovateTech"},
    {"email": "founder2@startup.io", "full_name": "Neha Agarwal", "role": UserRole.FOUNDER, "organization": "HealthAI"},
    {"email": "founder3@startup.io", "full_name": "Rajesh Menon", "role": UserRole.FOUNDER, "organization": "EduSmart"},
    {"email": "founder4@startup.io", "full_name": "Pooja Iyer", "role": UserRole.FOUNDER, "organization": "FinFlow"},

    # Faculty
    {"email": "faculty1@college.edu", "full_name": "Dr. Srinivas Kumar", "role": UserRole.FACULTY, "organization": "IIT Bombay"},
    {"email": "faculty2@college.edu", "full_name": "Prof. Lakshmi Devi", "role": UserRole.FACULTY, "organization": "NIT Warangal"},

    # Admin
    {"email": "admin@bharatbuild.ai", "full_name": "System Admin", "role": UserRole.ADMIN, "organization": "BharatBuild"},

    # API Partners
    {"email": "api.partner@external.com", "full_name": "API Partner Corp", "role": UserRole.API_PARTNER, "organization": "ExternalCorp"},
]

SAMPLE_PROJECTS_STUDENT = [
    {"title": "E-Commerce Website", "description": "Full-stack e-commerce platform with payment integration", "domain": "Web Development", "tech_stack": ["React", "Node.js", "MongoDB", "Stripe"]},
    {"title": "Hospital Management System", "description": "Complete HMS with patient records and appointment booking", "domain": "Healthcare", "tech_stack": ["Python", "Django", "PostgreSQL", "Redis"]},
    {"title": "Online Learning Platform", "description": "LMS with video streaming and quiz modules", "domain": "Education", "tech_stack": ["Vue.js", "FastAPI", "MySQL", "AWS S3"]},
    {"title": "Food Delivery App", "description": "Real-time food ordering with live tracking", "domain": "Food Tech", "tech_stack": ["React Native", "Node.js", "MongoDB", "Socket.io"]},
    {"title": "Social Media Dashboard", "description": "Analytics dashboard for social media management", "domain": "Marketing", "tech_stack": ["Angular", "Spring Boot", "PostgreSQL", "Grafana"]},
    {"title": "Inventory Management System", "description": "Stock tracking with barcode scanning", "domain": "Retail", "tech_stack": ["Python", "Flask", "SQLite", "OpenCV"]},
    {"title": "Chat Application", "description": "Real-time messaging with file sharing", "domain": "Communication", "tech_stack": ["React", "Express.js", "MongoDB", "WebSocket"]},
    {"title": "Weather Forecast App", "description": "Weather prediction using ML models", "domain": "Data Science", "tech_stack": ["Python", "TensorFlow", "FastAPI", "React"]},
    {"title": "Task Management Tool", "description": "Kanban board with team collaboration", "domain": "Productivity", "tech_stack": ["Next.js", "Prisma", "PostgreSQL", "Tailwind"]},
    {"title": "Music Streaming Service", "description": "Audio streaming with playlist management", "domain": "Entertainment", "tech_stack": ["React", "Node.js", "MongoDB", "AWS"]},
]

SAMPLE_PROJECTS_DEVELOPER = [
    {"title": "Microservices Architecture", "description": "Cloud-native microservices with Kubernetes", "framework": "Spring Cloud", "deployment_target": "AWS EKS"},
    {"title": "CI/CD Pipeline Setup", "description": "Automated deployment pipeline with GitLab", "framework": "Jenkins", "deployment_target": "Docker Swarm"},
    {"title": "GraphQL API Gateway", "description": "Unified API gateway for multiple services", "framework": "Apollo Server", "deployment_target": "GCP Cloud Run"},
    {"title": "Real-time Data Pipeline", "description": "Stream processing with Apache Kafka", "framework": "Kafka Streams", "deployment_target": "Azure Event Hub"},
    {"title": "Serverless Application", "description": "Event-driven functions with AWS Lambda", "framework": "Serverless", "deployment_target": "AWS Lambda"},
]

SAMPLE_PROJECTS_FOUNDER = [
    {"title": "AI-Powered CRM", "description": "Customer relationship management with AI insights", "industry": "Enterprise Software", "target_market": "SMBs"},
    {"title": "HealthTech Platform", "description": "Telemedicine platform with AI diagnostics", "industry": "Healthcare", "target_market": "Hospitals & Clinics"},
    {"title": "EdTech Marketplace", "description": "Online course marketplace with certifications", "industry": "Education", "target_market": "Students & Professionals"},
    {"title": "FinTech Payment Solution", "description": "UPI-based payment gateway for merchants", "industry": "Financial Services", "target_market": "Retail Merchants"},
    {"title": "AgriTech Platform", "description": "Farm management and crop prediction", "industry": "Agriculture", "target_market": "Farmers & Agribusinesses"},
]

SAMPLE_COLLEGES = [
    {"name": "Indian Institute of Technology Delhi", "code": "IITD", "domain": "iitd.ac.in", "city": "New Delhi", "state": "Delhi"},
    {"name": "National Institute of Technology Trichy", "code": "NITT", "domain": "nitt.edu", "city": "Tiruchirappalli", "state": "Tamil Nadu"},
    {"name": "BITS Pilani", "code": "BITS", "domain": "bits-pilani.ac.in", "city": "Pilani", "state": "Rajasthan"},
    {"name": "VIT Vellore", "code": "VIT", "domain": "vit.ac.in", "city": "Vellore", "state": "Tamil Nadu"},
    {"name": "Delhi Technological University", "code": "DTU", "domain": "dtu.ac.in", "city": "Delhi", "state": "Delhi"},
]

SAMPLE_DOCUMENTS = [
    {"type": DocumentType.SRS, "title": "Software Requirements Specification"},
    {"type": DocumentType.DESIGN, "title": "System Design Document"},
    {"type": DocumentType.UML, "title": "UML Diagrams"},
    {"type": DocumentType.CODE, "title": "Source Code Documentation"},
    {"type": DocumentType.TEST, "title": "Test Cases Document"},
    {"type": DocumentType.USER_MANUAL, "title": "User Manual"},
    {"type": DocumentType.REPORT, "title": "Project Report"},
]

TOKEN_PACKAGES = [
    {"name": "starter", "tokens": 50000, "amount": 9900, "currency": "INR"},
    {"name": "pro", "tokens": 200000, "amount": 29900, "currency": "INR"},
    {"name": "unlimited", "tokens": 1000000, "amount": 99900, "currency": "INR"},
]


# ==================== Seed Functions ====================

async def seed_users(db: AsyncSession) -> List[User]:
    """Create sample users"""
    users = []
    default_password = pwd_context.hash("Password123!")

    for user_data in SAMPLE_USERS:
        user = User(
            email=user_data["email"],
            full_name=user_data["full_name"],
            username=user_data["email"].split("@")[0],
            hashed_password=default_password,
            role=user_data["role"],
            organization=user_data["organization"],
            is_active=True,
            is_verified=True,
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 365)),
            last_login=datetime.utcnow() - timedelta(hours=random.randint(1, 168))
        )
        db.add(user)
        users.append(user)

    await db.flush()
    print(f"Created {len(users)} users")
    return users


async def seed_workspaces(db: AsyncSession, users: List[User]) -> List[Workspace]:
    """Create workspaces for users"""
    workspaces = []

    for user in users:
        # Create default workspace
        default_ws = Workspace(
            user_id=user.id,
            name="My Workspace",
            description=f"Default workspace for {user.full_name}",
            is_default=True,
            storage_path=f"workspaces/{user.id}",
            s3_prefix=f"workspaces/{user.id}"
        )
        db.add(default_ws)
        workspaces.append(default_ws)

        # Create additional workspaces for some users
        if user.role in [UserRole.DEVELOPER, UserRole.FOUNDER]:
            extra_ws = Workspace(
                user_id=user.id,
                name="Side Projects",
                description="Personal side projects",
                is_default=False,
                storage_path=f"workspaces/{user.id}/side",
                s3_prefix=f"workspaces/{user.id}/side"
            )
            db.add(extra_ws)
            workspaces.append(extra_ws)

    await db.flush()
    print(f"Created {len(workspaces)} workspaces")
    return workspaces


async def seed_colleges(db: AsyncSession) -> List[College]:
    """Create sample colleges"""
    colleges = []

    for college_data in SAMPLE_COLLEGES:
        college = College(
            name=college_data["name"],
            code=college_data["code"],
            domain=college_data["domain"],
            address=f"{college_data['city']}, {college_data['state']}, India",
            is_active=True
        )
        db.add(college)
        colleges.append(college)

    await db.flush()
    print(f"Created {len(colleges)} colleges")
    return colleges


async def seed_projects(db: AsyncSession, users: List[User], workspaces: List[Workspace]) -> List[Project]:
    """Create sample projects for users"""
    projects = []
    statuses = [ProjectStatus.DRAFT, ProjectStatus.IN_PROGRESS, ProjectStatus.COMPLETED, ProjectStatus.FAILED]

    for user in users:
        # Get user's default workspace
        user_workspaces = [ws for ws in workspaces if ws.user_id == user.id]
        if not user_workspaces:
            continue
        default_ws = user_workspaces[0]

        # Select projects based on user role
        if user.role == UserRole.STUDENT:
            project_templates = random.sample(SAMPLE_PROJECTS_STUDENT, min(5, len(SAMPLE_PROJECTS_STUDENT)))
            mode = ProjectMode.STUDENT
        elif user.role == UserRole.DEVELOPER:
            project_templates = random.sample(SAMPLE_PROJECTS_DEVELOPER, min(3, len(SAMPLE_PROJECTS_DEVELOPER)))
            mode = ProjectMode.DEVELOPER
        elif user.role == UserRole.FOUNDER:
            project_templates = random.sample(SAMPLE_PROJECTS_FOUNDER, min(3, len(SAMPLE_PROJECTS_FOUNDER)))
            mode = ProjectMode.FOUNDER
        else:
            continue

        for template in project_templates:
            status = random.choice(statuses)
            progress = 100 if status == ProjectStatus.COMPLETED else random.randint(0, 90)
            created_at = datetime.utcnow() - timedelta(days=random.randint(1, 180))

            project = Project(
                user_id=user.id,
                workspace_id=default_ws.id,
                title=template["title"],
                description=template["description"],
                mode=mode,
                status=status,
                progress=progress,
                is_saved=random.choice([True, False]),
                created_at=created_at,
                updated_at=created_at + timedelta(days=random.randint(0, 30)),
                completed_at=created_at + timedelta(days=random.randint(1, 60)) if status == ProjectStatus.COMPLETED else None,
                total_tokens=random.randint(5000, 50000),
                total_cost=random.randint(100, 5000)
            )

            # Add mode-specific fields
            if mode == ProjectMode.STUDENT:
                project.domain = template.get("domain")
                project.tech_stack = template.get("tech_stack")
            elif mode == ProjectMode.DEVELOPER:
                project.framework = template.get("framework")
                project.deployment_target = template.get("deployment_target")
            elif mode == ProjectMode.FOUNDER:
                project.industry = template.get("industry")
                project.target_market = template.get("target_market")

            db.add(project)
            projects.append(project)

    await db.flush()
    print(f"Created {len(projects)} projects")
    return projects


async def seed_project_files(db: AsyncSession, projects: List[Project]) -> List[ProjectFile]:
    """Create sample files for projects"""
    files = []
    file_templates = [
        {"path": "src/index.js", "name": "index.js", "language": "javascript", "content": "// Main entry point"},
        {"path": "src/App.jsx", "name": "App.jsx", "language": "javascript", "content": "// React App component"},
        {"path": "src/styles.css", "name": "styles.css", "language": "css", "content": "/* Main styles */"},
        {"path": "package.json", "name": "package.json", "language": "json", "content": "{}"},
        {"path": "README.md", "name": "README.md", "language": "markdown", "content": "# Project"},
        {"path": "src/components/Header.jsx", "name": "Header.jsx", "language": "javascript", "content": "// Header"},
        {"path": "src/components/Footer.jsx", "name": "Footer.jsx", "language": "javascript", "content": "// Footer"},
        {"path": "src/utils/api.js", "name": "api.js", "language": "javascript", "content": "// API utils"},
        {"path": ".env.example", "name": ".env.example", "language": "text", "content": "# Environment variables"},
        {"path": "docker-compose.yml", "name": "docker-compose.yml", "language": "yaml", "content": "version: '3'"},
    ]

    for project in projects:
        if project.status in [ProjectStatus.IN_PROGRESS, ProjectStatus.COMPLETED]:
            num_files = random.randint(5, len(file_templates))
            selected_files = random.sample(file_templates, num_files)

            for file_template in selected_files:
                project_file = ProjectFile(
                    project_id=project.id,
                    path=file_template["path"],
                    name=file_template["name"],
                    language=file_template["language"],
                    content=file_template["content"],
                    size_bytes=random.randint(100, 10000)
                )
                db.add(project_file)
                files.append(project_file)

    await db.flush()
    print(f"Created {len(files)} project files")
    return files


async def seed_documents(db: AsyncSession, projects: List[Project]) -> List[Document]:
    """Create sample documents for projects"""
    documents = []

    for project in projects:
        if project.status == ProjectStatus.COMPLETED:
            # Completed projects get all documents
            doc_types = SAMPLE_DOCUMENTS
        elif project.status == ProjectStatus.IN_PROGRESS:
            # In-progress projects get some documents
            doc_types = random.sample(SAMPLE_DOCUMENTS, random.randint(1, 4))
        else:
            continue

        for doc_template in doc_types:
            doc = Document(
                project_id=project.id,
                user_id=project.user_id,
                document_type=doc_template["type"],
                title=f"{doc_template['title']} - {project.title}",
                content=f"Sample {doc_template['type'].value} content for {project.title}",
                status="completed",
                file_path=f"documents/{project.id}/{doc_template['type'].value}.pdf",
                file_size=random.randint(50000, 500000),
                created_at=project.created_at + timedelta(days=random.randint(1, 30))
            )
            db.add(doc)
            documents.append(doc)

    await db.flush()
    print(f"Created {len(documents)} documents")
    return documents


async def seed_api_keys(db: AsyncSession, users: List[User]) -> List[APIKey]:
    """Create sample API keys for users"""
    api_keys = []

    for user in users:
        if user.role in [UserRole.DEVELOPER, UserRole.API_PARTNER, UserRole.ADMIN]:
            num_keys = random.randint(1, 4)
            for i in range(num_keys):
                key = APIKey(
                    user_id=user.id,
                    name=f"API Key {i + 1}",
                    key_prefix=f"bb_{uuid.uuid4().hex[:8]}",
                    hashed_key=pwd_context.hash(f"secret_key_{uuid.uuid4().hex}"),
                    status=random.choice([APIKeyStatus.ACTIVE, APIKeyStatus.ACTIVE, APIKeyStatus.REVOKED]),
                    rate_limit=random.choice([100, 500, 1000, 5000]),
                    permissions=["read", "write"] if random.random() > 0.5 else ["read"],
                    last_used_at=datetime.utcnow() - timedelta(hours=random.randint(1, 720)) if random.random() > 0.3 else None,
                    expires_at=datetime.utcnow() + timedelta(days=random.randint(30, 365)) if random.random() > 0.3 else None
                )
                db.add(key)
                api_keys.append(key)

    await db.flush()
    print(f"Created {len(api_keys)} API keys")
    return api_keys


async def seed_token_balances(db: AsyncSession, users: List[User]) -> List[TokenBalance]:
    """Create token balances for users"""
    balances = []

    for user in users:
        monthly_allowance = {
            UserRole.STUDENT: 10000,
            UserRole.DEVELOPER: 50000,
            UserRole.FOUNDER: 100000,
            UserRole.FACULTY: 25000,
            UserRole.ADMIN: 1000000,
            UserRole.API_PARTNER: 500000
        }.get(user.role, 10000)

        used = random.randint(0, int(monthly_allowance * 0.8))

        balance = TokenBalance(
            user_id=user.id,
            total_tokens=monthly_allowance + random.randint(0, 50000),
            used_tokens=used,
            remaining_tokens=monthly_allowance - used + random.randint(0, 50000),
            monthly_allowance=monthly_allowance,
            monthly_used=used,
            premium_tokens=random.randint(0, 100000) if random.random() > 0.5 else 0,
            total_requests=random.randint(10, 500),
            requests_today=random.randint(0, 20)
        )
        db.add(balance)
        balances.append(balance)

    await db.flush()
    print(f"Created {len(balances)} token balances")
    return balances


async def seed_token_transactions(db: AsyncSession, users: List[User], projects: List[Project]) -> List[TokenTransaction]:
    """Create sample token transactions"""
    transactions = []
    transaction_types = ["usage", "purchase", "bonus", "monthly_reset"]
    agents = ["planner", "writer", "fixer", "runner", "documenter"]
    models = ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-5-sonnet-20241022"]

    for user in users:
        user_projects = [p for p in projects if p.user_id == user.id]
        num_transactions = random.randint(15, 50)

        tokens = 10000
        for _ in range(num_transactions):
            tx_type = random.choice(transaction_types)
            project = random.choice(user_projects) if user_projects and tx_type == "usage" else None

            if tx_type == "usage":
                change = -random.randint(100, 5000)
            elif tx_type == "purchase":
                change = random.randint(10000, 100000)
            elif tx_type == "bonus":
                change = random.randint(1000, 10000)
            else:  # monthly_reset
                change = random.randint(5000, 20000)

            tokens_after = max(0, tokens + change)

            tx = TokenTransaction(
                user_id=user.id,
                project_id=project.id if project else None,
                transaction_type=tx_type,
                tokens_before=tokens,
                tokens_changed=change,
                tokens_after=tokens_after,
                description=f"{tx_type.replace('_', ' ').title()} transaction",
                agent_type=random.choice(agents) if tx_type == "usage" else None,
                model_used=random.choice(models) if tx_type == "usage" else None,
                input_tokens=random.randint(100, 2000) if tx_type == "usage" else 0,
                output_tokens=random.randint(500, 5000) if tx_type == "usage" else 0,
                estimated_cost_usd=abs(change) // 100 if tx_type == "usage" else 0,
                estimated_cost_inr=abs(change) // 100 * 83 if tx_type == "usage" else 0,
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 90))
            )
            db.add(tx)
            transactions.append(tx)
            tokens = tokens_after

    await db.flush()
    print(f"Created {len(transactions)} token transactions")
    return transactions


async def seed_agent_tasks(db: AsyncSession, projects: List[Project]) -> List[AgentTask]:
    """Create sample agent tasks"""
    tasks = []
    agents = ["planner", "writer", "fixer", "runner", "documenter", "enhancer"]
    statuses = [AgentTaskStatus.COMPLETED, AgentTaskStatus.COMPLETED, AgentTaskStatus.COMPLETED, AgentTaskStatus.FAILED, AgentTaskStatus.PENDING]

    for project in projects:
        if project.status in [ProjectStatus.IN_PROGRESS, ProjectStatus.COMPLETED]:
            num_tasks = random.randint(5, 15)
            for i in range(num_tasks):
                agent = random.choice(agents)
                status = random.choice(statuses)

                task = AgentTask(
                    project_id=project.id,
                    agent_type=agent,
                    status=status,
                    input_data={"task": f"{agent} task {i + 1}"},
                    output_data={"result": "success"} if status == AgentTaskStatus.COMPLETED else None,
                    error_message="Task failed due to timeout" if status == AgentTaskStatus.FAILED else None,
                    tokens_used=random.randint(500, 5000),
                    execution_time_ms=random.randint(1000, 30000),
                    started_at=project.created_at + timedelta(hours=i),
                    completed_at=project.created_at + timedelta(hours=i, minutes=random.randint(1, 10)) if status != AgentTaskStatus.PENDING else None
                )
                db.add(task)
                tasks.append(task)

    await db.flush()
    print(f"Created {len(tasks)} agent tasks")
    return tasks


async def seed_subscriptions(db: AsyncSession, users: List[User]) -> List[Subscription]:
    """Create sample subscriptions"""
    subscriptions = []
    plans = ["free", "basic", "pro", "enterprise"]

    for user in users:
        # Assign plans based on role
        if user.role == UserRole.ADMIN:
            plan = "enterprise"
        elif user.role in [UserRole.FOUNDER, UserRole.API_PARTNER]:
            plan = random.choice(["pro", "enterprise"])
        elif user.role == UserRole.DEVELOPER:
            plan = random.choice(["basic", "pro"])
        else:
            plan = random.choice(["free", "basic"])

        sub = Subscription(
            user_id=user.id,
            plan_name=plan,
            status="active" if random.random() > 0.1 else "cancelled",
            tokens_per_month={
                "free": 10000,
                "basic": 50000,
                "pro": 200000,
                "enterprise": 1000000
            }.get(plan, 10000),
            price_per_month={
                "free": 0,
                "basic": 999,
                "pro": 2999,
                "enterprise": 9999
            }.get(plan, 0),
            started_at=datetime.utcnow() - timedelta(days=random.randint(1, 365)),
            current_period_start=datetime.utcnow() - timedelta(days=random.randint(0, 30)),
            current_period_end=datetime.utcnow() + timedelta(days=random.randint(1, 30))
        )
        db.add(sub)
        subscriptions.append(sub)

    await db.flush()
    print(f"Created {len(subscriptions)} subscriptions")
    return subscriptions


async def seed_usage_logs(db: AsyncSession, users: List[User], projects: List[Project]) -> List[UsageLog]:
    """Create sample usage logs"""
    logs = []
    endpoints = [
        "/api/v1/projects",
        "/api/v1/orchestrator/generate",
        "/api/v1/documents/generate",
        "/api/v1/tokens/balance",
        "/api/v1/workspace",
        "/api/v1/auth/me"
    ]
    methods = ["GET", "POST", "PUT", "DELETE"]

    for user in users:
        num_logs = random.randint(20, 100)
        for _ in range(num_logs):
            log = UsageLog(
                user_id=user.id,
                endpoint=random.choice(endpoints),
                method=random.choice(methods),
                status_code=random.choice([200, 200, 200, 201, 400, 401, 500]),
                response_time_ms=random.randint(50, 5000),
                ip_address=f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 720))
            )
            db.add(log)
            logs.append(log)

    await db.flush()
    print(f"Created {len(logs)} usage logs")
    return logs


# ==================== Main Seed Function ====================

async def seed_all():
    """Seed all sample data"""
    print("=" * 50)
    print("Starting database seeding...")
    print("=" * 50)

    # Initialize database
    await init_db()

    async with AsyncSessionLocal() as db:
        try:
            # Seed in order of dependencies
            users = await seed_users(db)
            workspaces = await seed_workspaces(db, users)
            colleges = await seed_colleges(db)
            projects = await seed_projects(db, users, workspaces)
            await seed_project_files(db, projects)
            await seed_documents(db, projects)
            await seed_api_keys(db, users)
            await seed_token_balances(db, users)
            await seed_token_transactions(db, users, projects)
            await seed_agent_tasks(db, projects)
            await seed_subscriptions(db, users)
            await seed_usage_logs(db, users, projects)

            await db.commit()
            print("=" * 50)
            print("Database seeding completed successfully!")
            print("=" * 50)

        except Exception as e:
            await db.rollback()
            print(f"Error seeding database: {e}")
            raise


async def clear_all():
    """Clear all data from database"""
    print("Clearing all data...")
    async with AsyncSessionLocal() as db:
        # Delete in reverse order of dependencies
        await db.execute("DELETE FROM usage_logs")
        await db.execute("DELETE FROM token_transactions")
        await db.execute("DELETE FROM token_balances")
        await db.execute("DELETE FROM token_purchases")
        await db.execute("DELETE FROM subscriptions")
        await db.execute("DELETE FROM api_keys")
        await db.execute("DELETE FROM agent_tasks")
        await db.execute("DELETE FROM documents")
        await db.execute("DELETE FROM project_files")
        await db.execute("DELETE FROM projects")
        await db.execute("DELETE FROM workspaces")
        await db.execute("DELETE FROM students")
        await db.execute("DELETE FROM batches")
        await db.execute("DELETE FROM faculty")
        await db.execute("DELETE FROM colleges")
        await db.execute("DELETE FROM users")
        await db.commit()
        print("All data cleared!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        asyncio.run(clear_all())
    else:
        asyncio.run(seed_all())
