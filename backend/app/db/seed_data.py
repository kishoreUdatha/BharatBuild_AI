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
from sqlalchemy import text

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
from app.models.workshop_enrollment import WorkshopEnrollment
from app.models.campus_drive import CampusDrive, CampusDriveRegistration, RegistrationStatus

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
    {"name": "Indian Institute of Technology Delhi", "code": "IITD", "city": "New Delhi", "state": "Delhi"},
    {"name": "National Institute of Technology Trichy", "code": "NITT", "city": "Tiruchirappalli", "state": "Tamil Nadu"},
    {"name": "BITS Pilani", "code": "BITS", "city": "Pilani", "state": "Rajasthan"},
    {"name": "VIT Vellore", "code": "VIT", "city": "Vellore", "state": "Tamil Nadu"},
    {"name": "Delhi Technological University", "code": "DTU", "city": "Delhi", "state": "Delhi"},
]

SAMPLE_DOCUMENTS = [
    {"type": DocumentType.SRS, "title": "Software Requirements Specification"},
    {"type": DocumentType.PRD, "title": "Product Requirements Document"},
    {"type": DocumentType.UML, "title": "UML Diagrams"},
    {"type": DocumentType.CODE, "title": "Source Code Documentation"},
    {"type": DocumentType.REPORT, "title": "Project Report"},
    {"type": DocumentType.PPT, "title": "Project Presentation"},
    {"type": DocumentType.VIVA_QA, "title": "Viva Q&A Document"},
]

TOKEN_PACKAGES = [
    {"name": "starter", "tokens": 50000, "amount": 9900, "currency": "INR"},
    {"name": "pro", "tokens": 200000, "amount": 29900, "currency": "INR"},
    {"name": "unlimited", "tokens": 1000000, "amount": 99900, "currency": "INR"},
]

SAMPLE_WORKSHOPS = [
    "AI/ML Workshop 2024",
    "Full Stack Development Bootcamp",
    "Cloud Computing Masterclass",
    "Data Science with Python",
    "React & Node.js Workshop",
]

SAMPLE_DEPARTMENTS = [
    "Computer Science and Engineering",
    "Information Technology",
    "Electronics and Communication",
    "Electrical Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Artificial Intelligence",
]

SAMPLE_COLLEGES_NAMES = [
    "Indian Institute of Technology Delhi",
    "National Institute of Technology Trichy",
    "BITS Pilani",
    "VIT Vellore",
    "Delhi Technological University",
    "IIIT Hyderabad",
    "SRM Institute Chennai",
    "Manipal Institute of Technology",
    "JNTU Hyderabad",
    "Anna University Chennai",
    "PES University Bangalore",
    "RV College of Engineering",
    "BMS College of Engineering",
    "MS Ramaiah Institute",
    "Christ University Bangalore",
]

SAMPLE_FIRST_NAMES = [
    "Rahul", "Priya", "Amit", "Sneha", "Vikram", "Ananya", "Rohan", "Kavya",
    "Arjun", "Meera", "Karthik", "Divya", "Suresh", "Pooja", "Aditya", "Neha",
    "Rajesh", "Lakshmi", "Srinivas", "Aarti", "Venkat", "Deepika", "Harish", "Swati",
    "Manoj", "Rashmi", "Vijay", "Anjali", "Prakash", "Nandini", "Sanjay", "Rekha",
    "Ganesh", "Bhavya", "Krishna", "Shruthi", "Mohan", "Pallavi", "Ramesh", "Vidya"
]

SAMPLE_LAST_NAMES = [
    "Sharma", "Patel", "Kumar", "Reddy", "Singh", "Gupta", "Mehta", "Nair",
    "Verma", "Shah", "Rajan", "Krishnan", "Babu", "Iyer", "Rao", "Agarwal",
    "Menon", "Devi", "Naidu", "Joshi", "Pillai", "Bhat", "Shetty", "Yadav",
    "Mishra", "Chopra", "Kapoor", "Malhotra", "Saxena", "Bansal"
]

SAMPLE_CAMPUS_DRIVES = [
    {
        "name": "BharatBuild AI Campus Hiring 2024",
        "company_name": "BharatBuild AI",
        "description": "Campus placement drive for fresh graduates in AI/ML and Full Stack roles",
        "passing_percentage": 60.0,
        "total_questions": 30
    },
    {
        "name": "TechCorp India Summer Internship",
        "company_name": "TechCorp India",
        "description": "Summer internship program for pre-final year students",
        "passing_percentage": 55.0,
        "total_questions": 25
    },
    {
        "name": "InnovateTech Graduate Program 2024",
        "company_name": "InnovateTech Solutions",
        "description": "Graduate trainee program for B.Tech/M.Tech freshers",
        "passing_percentage": 65.0,
        "total_questions": 35
    }
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
            city=college_data["city"],
            state=college_data["state"],
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


async def seed_workshop_enrollments(db: AsyncSession) -> List[WorkshopEnrollment]:
    """Create sample workshop enrollments"""
    enrollments = []
    years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]

    # Create 50 workshop enrollments
    for i in range(50):
        first_name = random.choice(SAMPLE_FIRST_NAMES)
        last_name = random.choice(SAMPLE_LAST_NAMES)
        full_name = f"{first_name} {last_name}"
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}@student.edu"
        phone = f"+91 {random.randint(70000, 99999)}{random.randint(10000, 99999)}"

        enrollment = WorkshopEnrollment(
            full_name=full_name,
            email=email,
            phone=phone,
            college_name=random.choice(SAMPLE_COLLEGES_NAMES),
            department=random.choice(SAMPLE_DEPARTMENTS),
            year_of_study=random.choice(years),
            roll_number=f"{random.choice(['21', '22', '23', '24'])}{random.choice(['CS', 'IT', 'EC', 'EE', 'AI'])}{random.randint(100, 999)}",
            workshop_name=random.choice(SAMPLE_WORKSHOPS),
            is_confirmed=random.choice([True, True, True, False]),  # 75% confirmed
            payment_status=random.choice(["completed", "completed", "completed", "pending", "waived"]),
            previous_experience=random.choice([
                "Basic Python programming",
                "Web development with HTML/CSS",
                "No prior experience",
                "Completed online courses on Coursera",
                "Built small projects in college"
            ]) if random.random() > 0.3 else None,
            expectations=random.choice([
                "Want to learn practical AI/ML skills",
                "Looking to build portfolio projects",
                "Preparing for placements",
                "Interested in startup opportunities",
                "Want hands-on coding experience"
            ]) if random.random() > 0.3 else None,
            how_did_you_hear=random.choice([
                "College notice board",
                "Social media",
                "Friend referral",
                "Email newsletter",
                "Faculty recommendation"
            ]) if random.random() > 0.4 else None,
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 60))
        )
        db.add(enrollment)
        enrollments.append(enrollment)

    await db.flush()
    print(f"Created {len(enrollments)} workshop enrollments")
    return enrollments


async def seed_campus_drives(db: AsyncSession) -> List[CampusDrive]:
    """Create sample campus drives"""
    drives = []

    for drive_data in SAMPLE_CAMPUS_DRIVES:
        drive = CampusDrive(
            name=drive_data["name"],
            company_name=drive_data["company_name"],
            description=drive_data["description"],
            registration_start=datetime.utcnow() - timedelta(days=random.randint(30, 60)),
            registration_end=datetime.utcnow() + timedelta(days=random.randint(5, 30)),
            quiz_date=datetime.utcnow() + timedelta(days=random.randint(7, 45)),
            quiz_duration_minutes=60,
            passing_percentage=drive_data["passing_percentage"],
            total_questions=drive_data["total_questions"],
            logical_questions=5,
            technical_questions=10,
            ai_ml_questions=10,
            english_questions=5,
            coding_questions=5 if drive_data["total_questions"] >= 35 else 0,
            is_active=True,
            created_at=datetime.utcnow() - timedelta(days=random.randint(30, 90))
        )
        db.add(drive)
        drives.append(drive)

    await db.flush()
    print(f"Created {len(drives)} campus drives")
    return drives


async def seed_campus_drive_registrations(db: AsyncSession, drives: List[CampusDrive]) -> List[CampusDriveRegistration]:
    """Create sample campus drive registrations"""
    registrations = []
    years = ["1st Year", "2nd Year", "3rd Year", "4th Year"]
    statuses = [
        RegistrationStatus.REGISTERED,
        RegistrationStatus.QUIZ_COMPLETED,
        RegistrationStatus.QUALIFIED,
        RegistrationStatus.NOT_QUALIFIED
    ]

    for drive in drives:
        # Create 30-50 registrations per drive
        num_registrations = random.randint(30, 50)

        for i in range(num_registrations):
            first_name = random.choice(SAMPLE_FIRST_NAMES)
            last_name = random.choice(SAMPLE_LAST_NAMES)
            full_name = f"{first_name} {last_name}"
            email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}@student.edu"
            phone = f"+91 {random.randint(70000, 99999)}{random.randint(10000, 99999)}"

            status = random.choice(statuses)

            # Generate scores based on status
            if status == RegistrationStatus.REGISTERED:
                # Not attempted quiz yet
                logical_score = 0
                technical_score = 0
                ai_ml_score = 0
                english_score = 0
                coding_score = 0
                percentage = None
                is_qualified = False
            else:
                # Attempted quiz - generate realistic scores
                logical_score = random.randint(1, 5)  # out of 5
                technical_score = random.randint(3, 10)  # out of 10
                ai_ml_score = random.randint(3, 10)  # out of 10
                english_score = random.randint(2, 5)  # out of 5
                coding_score = random.randint(0, 5) if drive.coding_questions > 0 else 0

                total_score = logical_score + technical_score + ai_ml_score + english_score + coding_score
                total_marks = drive.total_questions
                percentage = (total_score / total_marks) * 100

                is_qualified = percentage >= drive.passing_percentage

                # Adjust status based on qualification
                if is_qualified:
                    status = RegistrationStatus.QUALIFIED
                elif percentage is not None:
                    status = RegistrationStatus.NOT_QUALIFIED

            registration = CampusDriveRegistration(
                campus_drive_id=drive.id,
                full_name=full_name,
                email=email,
                phone=phone,
                college_name=random.choice(SAMPLE_COLLEGES_NAMES),
                department=random.choice(SAMPLE_DEPARTMENTS),
                year_of_study=random.choice(years),
                roll_number=f"{random.choice(['21', '22', '23', '24'])}{random.choice(['CS', 'IT', 'EC', 'EE', 'AI'])}{random.randint(100, 999)}",
                cgpa=round(random.uniform(6.0, 9.5), 2),
                status=status,
                quiz_start_time=datetime.utcnow() - timedelta(hours=random.randint(1, 72)) if status != RegistrationStatus.REGISTERED else None,
                quiz_end_time=datetime.utcnow() - timedelta(hours=random.randint(0, 71)) if status != RegistrationStatus.REGISTERED else None,
                quiz_score=total_score if status != RegistrationStatus.REGISTERED else None,
                total_marks=total_marks if status != RegistrationStatus.REGISTERED else None,
                percentage=round(percentage, 2) if percentage is not None else None,
                is_qualified=is_qualified,
                logical_score=logical_score,
                technical_score=technical_score,
                ai_ml_score=ai_ml_score,
                english_score=english_score,
                coding_score=coding_score,
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
            )
            db.add(registration)
            registrations.append(registration)

    await db.flush()
    print(f"Created {len(registrations)} campus drive registrations")
    return registrations


# ==================== Main Seed Function ====================

async def seed_all():
    """Seed all sample data"""
    print("=" * 50)
    print("Starting database seeding...")
    print("=" * 50)

    # Initialize database
    await init_db()

    async with AsyncSessionLocal() as db:
        users = []
        workspaces = []
        projects = []

        # Seed users
        try:
            users = await seed_users(db)
            await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"Error seeding users: {e}")

        # Seed workspaces
        try:
            if users:
                workspaces = await seed_workspaces(db, users)
                await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"Error seeding workspaces: {e}")

        # Seed colleges
        try:
            await seed_colleges(db)
            await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"Error seeding colleges: {e}")

        # Seed projects
        try:
            if users and workspaces:
                projects = await seed_projects(db, users, workspaces)
                await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"Error seeding projects: {e}")

        # Seed subscriptions
        try:
            if users:
                await seed_subscriptions(db, users)
                await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"Error seeding subscriptions: {e}")

        # Seed token balances
        try:
            if users:
                await seed_token_balances(db, users)
                await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"Error seeding token balances: {e}")

        # Seed workshop enrollments
        try:
            await seed_workshop_enrollments(db)
            await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"Error seeding workshop enrollments: {e}")

        # Seed campus drives and registrations
        try:
            drives = await seed_campus_drives(db)
            await db.commit()
            await seed_campus_drive_registrations(db, drives)
            await db.commit()
        except Exception as e:
            await db.rollback()
            print(f"Error seeding campus drives: {e}")

        print("=" * 50)
        print("Database seeding completed!")
        print("=" * 50)


async def clear_all():
    """Clear all data from database"""
    print("Clearing all data...")
    async with AsyncSessionLocal() as db:
        # Delete in reverse order of dependencies
        tables_to_clear = [
            "usage_logs",
            "token_transactions",
            "token_balances",
            "token_purchases",
            "subscriptions",
            "api_keys",
            "agent_tasks",
            "documents",
            "project_files",
            "projects",
            "workspaces",
            "students",
            "batches",
            "faculty",
            "colleges",
            "workshop_enrollments",
            "campus_drive_responses",
            "campus_drive_registrations",
            "campus_drive_questions",
            "campus_drives",
            "users",
        ]
        for table in tables_to_clear:
            try:
                await db.execute(text(f"DELETE FROM {table}"))
            except Exception as e:
                print(f"Warning: Could not clear {table}: {e}")
        await db.commit()
        print("All data cleared!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        asyncio.run(clear_all())
    else:
        asyncio.run(seed_all())
