"""
Curriculum-to-Project Mapping Engine
Maps courses to relevant projects based on Course Outcomes (COs) and Program Outcomes (POs)
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    RESEARCH = "research"


class ProjectType(str, Enum):
    MINI_PROJECT = "mini_project"
    CAPSTONE = "capstone"
    CASE_STUDY = "case_study"
    LAB_EXERCISE = "lab_exercise"
    HACKATHON = "hackathon"
    RESEARCH = "research"


class TechnologyDomain(str, Enum):
    WEB_DEVELOPMENT = "web_development"
    MOBILE_DEVELOPMENT = "mobile_development"
    AI_ML = "ai_ml"
    DATA_SCIENCE = "data_science"
    CLOUD_COMPUTING = "cloud_computing"
    DEVOPS = "devops"
    CYBERSECURITY = "cybersecurity"
    IOT = "iot"
    BLOCKCHAIN = "blockchain"
    GAME_DEVELOPMENT = "game_development"
    EMBEDDED_SYSTEMS = "embedded_systems"
    DATABASE = "database"


@dataclass
class CourseInfo:
    """Course information for mapping"""
    course_name: str
    course_code: str
    department: str
    semester: int
    credits: int
    course_outcomes: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)


@dataclass
class ProjectSuggestion:
    """AI-generated project suggestion"""
    title: str
    description: str
    difficulty: DifficultyLevel
    project_type: ProjectType
    domain: TechnologyDomain
    technologies: List[str]
    duration_weeks: int
    team_size: int
    course_outcomes_mapped: List[str]
    program_outcomes_mapped: List[str]
    blooms_levels: List[str]
    industry_relevance: str
    learning_objectives: List[str]
    deliverables: List[str]
    evaluation_criteria: List[str]


# Comprehensive course-to-domain mapping
COURSE_DOMAIN_MAPPING = {
    # Computer Science Core
    "data structures": [TechnologyDomain.WEB_DEVELOPMENT, TechnologyDomain.AI_ML],
    "algorithms": [TechnologyDomain.AI_ML, TechnologyDomain.DATA_SCIENCE],
    "database": [TechnologyDomain.DATABASE, TechnologyDomain.WEB_DEVELOPMENT],
    "dbms": [TechnologyDomain.DATABASE, TechnologyDomain.WEB_DEVELOPMENT],
    "operating systems": [TechnologyDomain.CLOUD_COMPUTING, TechnologyDomain.DEVOPS],
    "computer networks": [TechnologyDomain.CLOUD_COMPUTING, TechnologyDomain.CYBERSECURITY],
    "software engineering": [TechnologyDomain.WEB_DEVELOPMENT, TechnologyDomain.DEVOPS],

    # Web & Mobile
    "web development": [TechnologyDomain.WEB_DEVELOPMENT],
    "web technologies": [TechnologyDomain.WEB_DEVELOPMENT],
    "mobile application": [TechnologyDomain.MOBILE_DEVELOPMENT],
    "android": [TechnologyDomain.MOBILE_DEVELOPMENT],
    "ios": [TechnologyDomain.MOBILE_DEVELOPMENT],

    # AI/ML
    "artificial intelligence": [TechnologyDomain.AI_ML],
    "machine learning": [TechnologyDomain.AI_ML, TechnologyDomain.DATA_SCIENCE],
    "deep learning": [TechnologyDomain.AI_ML],
    "neural networks": [TechnologyDomain.AI_ML],
    "natural language processing": [TechnologyDomain.AI_ML],
    "nlp": [TechnologyDomain.AI_ML],
    "computer vision": [TechnologyDomain.AI_ML],
    "data mining": [TechnologyDomain.DATA_SCIENCE, TechnologyDomain.AI_ML],

    # Data Science
    "data science": [TechnologyDomain.DATA_SCIENCE],
    "big data": [TechnologyDomain.DATA_SCIENCE, TechnologyDomain.CLOUD_COMPUTING],
    "data analytics": [TechnologyDomain.DATA_SCIENCE],
    "statistics": [TechnologyDomain.DATA_SCIENCE],

    # Cloud & DevOps
    "cloud computing": [TechnologyDomain.CLOUD_COMPUTING],
    "devops": [TechnologyDomain.DEVOPS],
    "distributed systems": [TechnologyDomain.CLOUD_COMPUTING],

    # Security
    "cyber security": [TechnologyDomain.CYBERSECURITY],
    "information security": [TechnologyDomain.CYBERSECURITY],
    "cryptography": [TechnologyDomain.CYBERSECURITY, TechnologyDomain.BLOCKCHAIN],

    # Emerging Tech
    "iot": [TechnologyDomain.IOT],
    "internet of things": [TechnologyDomain.IOT],
    "blockchain": [TechnologyDomain.BLOCKCHAIN],
    "embedded systems": [TechnologyDomain.EMBEDDED_SYSTEMS, TechnologyDomain.IOT],

    # Others
    "game development": [TechnologyDomain.GAME_DEVELOPMENT],
    "graphics": [TechnologyDomain.GAME_DEVELOPMENT],
}

# NBA Program Outcomes (12 POs)
PROGRAM_OUTCOMES = {
    "PO1": "Engineering Knowledge",
    "PO2": "Problem Analysis",
    "PO3": "Design/Development of Solutions",
    "PO4": "Conduct Investigations",
    "PO5": "Modern Tool Usage",
    "PO6": "Engineer and Society",
    "PO7": "Environment and Sustainability",
    "PO8": "Ethics",
    "PO9": "Individual and Team Work",
    "PO10": "Communication",
    "PO11": "Project Management and Finance",
    "PO12": "Life-long Learning",
}

# Bloom's Taxonomy action verbs by level
BLOOMS_TAXONOMY = {
    "L1_Remember": ["Define", "List", "State", "Identify", "Recall"],
    "L2_Understand": ["Describe", "Explain", "Summarize", "Interpret", "Compare"],
    "L3_Apply": ["Apply", "Demonstrate", "Implement", "Solve", "Use"],
    "L4_Analyze": ["Analyze", "Differentiate", "Examine", "Compare", "Investigate"],
    "L5_Evaluate": ["Evaluate", "Justify", "Assess", "Critique", "Recommend"],
    "L6_Create": ["Design", "Develop", "Create", "Construct", "Formulate"],
}


class CurriculumMappingEngine:
    """
    Maps courses to relevant projects based on:
    - Course Outcomes (COs)
    - Program Outcomes (POs)
    - Industry relevance
    - Bloom's Taxonomy levels
    """

    def __init__(self):
        self.industry_library = IndustryUseCaseLibrary()

    def map_course_to_projects(
        self,
        course: CourseInfo,
        num_suggestions: int = 5,
        difficulty_filter: Optional[DifficultyLevel] = None,
        project_type_filter: Optional[ProjectType] = None
    ) -> List[ProjectSuggestion]:
        """
        Generate project suggestions based on course information.

        Args:
            course: Course information
            num_suggestions: Number of project suggestions to generate
            difficulty_filter: Filter by difficulty level
            project_type_filter: Filter by project type

        Returns:
            List of project suggestions mapped to COs and POs
        """
        # Detect relevant domains from course name and topics
        domains = self._detect_domains(course)

        # Get industry use cases for detected domains
        use_cases = []
        for domain in domains:
            domain_cases = self.industry_library.get_use_cases_by_domain(domain)
            use_cases.extend(domain_cases)

        # Filter by difficulty and project type if specified
        if difficulty_filter:
            use_cases = [uc for uc in use_cases if uc.get("difficulty") == difficulty_filter.value]
        if project_type_filter:
            use_cases = [uc for uc in use_cases if uc.get("project_type") == project_type_filter.value]

        # Map use cases to project suggestions with CO-PO mapping
        suggestions = []
        for use_case in use_cases[:num_suggestions]:
            suggestion = self._create_project_suggestion(course, use_case, domains[0] if domains else TechnologyDomain.WEB_DEVELOPMENT)
            suggestions.append(suggestion)

        # If not enough use cases, generate custom suggestions
        if len(suggestions) < num_suggestions:
            custom_suggestions = self._generate_custom_suggestions(
                course, domains, num_suggestions - len(suggestions)
            )
            suggestions.extend(custom_suggestions)

        return suggestions[:num_suggestions]

    def _detect_domains(self, course: CourseInfo) -> List[TechnologyDomain]:
        """Detect relevant technology domains from course information."""
        domains = set()

        # Check course name
        course_lower = course.course_name.lower()
        for keyword, domain_list in COURSE_DOMAIN_MAPPING.items():
            if keyword in course_lower:
                domains.update(domain_list)

        # Check topics
        for topic in course.topics:
            topic_lower = topic.lower()
            for keyword, domain_list in COURSE_DOMAIN_MAPPING.items():
                if keyword in topic_lower:
                    domains.update(domain_list)

        # Default to web development if no match
        if not domains:
            domains.add(TechnologyDomain.WEB_DEVELOPMENT)

        return list(domains)

    def _create_project_suggestion(
        self,
        course: CourseInfo,
        use_case: Dict[str, Any],
        domain: TechnologyDomain
    ) -> ProjectSuggestion:
        """Create a project suggestion from an industry use case."""
        # Map to Course Outcomes
        cos_mapped = self._map_to_course_outcomes(use_case, course.course_outcomes)

        # Map to Program Outcomes
        pos_mapped = self._map_to_program_outcomes(use_case)

        # Determine Bloom's levels
        blooms = self._determine_blooms_levels(use_case.get("difficulty", "intermediate"))

        return ProjectSuggestion(
            title=use_case.get("title", "Untitled Project"),
            description=use_case.get("description", ""),
            difficulty=DifficultyLevel(use_case.get("difficulty", "intermediate")),
            project_type=ProjectType(use_case.get("project_type", "mini_project")),
            domain=domain,
            technologies=use_case.get("technologies", []),
            duration_weeks=use_case.get("duration_weeks", 4),
            team_size=use_case.get("team_size", 3),
            course_outcomes_mapped=cos_mapped,
            program_outcomes_mapped=pos_mapped,
            blooms_levels=blooms,
            industry_relevance=use_case.get("industry_relevance", "High"),
            learning_objectives=use_case.get("learning_objectives", []),
            deliverables=use_case.get("deliverables", []),
            evaluation_criteria=use_case.get("evaluation_criteria", [])
        )

    def _map_to_course_outcomes(
        self,
        use_case: Dict[str, Any],
        course_outcomes: List[str]
    ) -> List[str]:
        """Map project to Course Outcomes."""
        if not course_outcomes:
            # Generate default COs based on project
            return [
                f"CO1: Apply {use_case.get('technologies', ['technology'])[0]} concepts",
                f"CO2: Design and implement {use_case.get('title', 'system')}",
                "CO3: Analyze and evaluate solution effectiveness",
                "CO4: Demonstrate team collaboration and communication"
            ]
        return course_outcomes[:4]

    def _map_to_program_outcomes(self, use_case: Dict[str, Any]) -> List[str]:
        """Map project to Program Outcomes (NBA POs)."""
        # Default mapping based on project characteristics
        pos = ["PO1", "PO2", "PO3", "PO5"]  # Core POs for any project

        difficulty = use_case.get("difficulty", "intermediate")
        if difficulty in ["advanced", "expert", "research"]:
            pos.extend(["PO4", "PO11"])  # Research + Project Management

        project_type = use_case.get("project_type", "mini_project")
        if project_type in ["capstone", "hackathon"]:
            pos.extend(["PO9", "PO10"])  # Team Work + Communication

        return list(set(pos))

    def _determine_blooms_levels(self, difficulty: str) -> List[str]:
        """Determine Bloom's Taxonomy levels based on difficulty."""
        levels_map = {
            "beginner": ["L1_Remember", "L2_Understand", "L3_Apply"],
            "intermediate": ["L2_Understand", "L3_Apply", "L4_Analyze"],
            "advanced": ["L3_Apply", "L4_Analyze", "L5_Evaluate"],
            "expert": ["L4_Analyze", "L5_Evaluate", "L6_Create"],
            "research": ["L5_Evaluate", "L6_Create"]
        }
        return levels_map.get(difficulty, ["L3_Apply", "L4_Analyze"])

    def _generate_custom_suggestions(
        self,
        course: CourseInfo,
        domains: List[TechnologyDomain],
        count: int
    ) -> List[ProjectSuggestion]:
        """Generate custom project suggestions when library doesn't have enough."""
        suggestions = []

        templates = [
            {
                "title_template": "{course} Management System",
                "description": "Build a comprehensive management system applying {course} concepts",
                "project_type": ProjectType.MINI_PROJECT,
                "difficulty": DifficultyLevel.INTERMEDIATE,
                "duration_weeks": 4
            },
            {
                "title_template": "{course} Analysis Dashboard",
                "description": "Create an analytics dashboard for {course} data visualization",
                "project_type": ProjectType.CAPSTONE,
                "difficulty": DifficultyLevel.ADVANCED,
                "duration_weeks": 8
            },
            {
                "title_template": "{course} Case Study Implementation",
                "description": "Implement a real-world case study demonstrating {course} principles",
                "project_type": ProjectType.CASE_STUDY,
                "difficulty": DifficultyLevel.INTERMEDIATE,
                "duration_weeks": 3
            }
        ]

        for i, template in enumerate(templates[:count]):
            domain = domains[i % len(domains)] if domains else TechnologyDomain.WEB_DEVELOPMENT
            tech_stack = self.industry_library.get_tech_stack_for_domain(domain)

            suggestion = ProjectSuggestion(
                title=template["title_template"].format(course=course.course_name),
                description=template["description"].format(course=course.course_name),
                difficulty=template["difficulty"],
                project_type=template["project_type"],
                domain=domain,
                technologies=tech_stack[:5],
                duration_weeks=template["duration_weeks"],
                team_size=3,
                course_outcomes_mapped=[f"CO{j+1}" for j in range(4)],
                program_outcomes_mapped=["PO1", "PO2", "PO3", "PO5", "PO9"],
                blooms_levels=self._determine_blooms_levels(template["difficulty"].value),
                industry_relevance="High",
                learning_objectives=[
                    f"Apply {course.course_name} concepts in real-world scenario",
                    "Design and implement a complete solution",
                    "Collaborate effectively in a team environment",
                    "Document and present the project professionally"
                ],
                deliverables=[
                    "Source code with documentation",
                    "Project report",
                    "Presentation slides",
                    "Demo video"
                ],
                evaluation_criteria=[
                    "Code quality and best practices",
                    "Functionality and features",
                    "Documentation completeness",
                    "Presentation and viva"
                ]
            )
            suggestions.append(suggestion)

        return suggestions

    def generate_co_po_mapping_report(
        self,
        course: CourseInfo,
        projects: List[ProjectSuggestion]
    ) -> Dict[str, Any]:
        """Generate a comprehensive CO-PO mapping report."""
        report = {
            "course_info": {
                "name": course.course_name,
                "code": course.course_code,
                "department": course.department,
                "semester": course.semester
            },
            "course_outcomes": course.course_outcomes or [f"CO{i+1}" for i in range(5)],
            "program_outcomes": PROGRAM_OUTCOMES,
            "projects": [],
            "co_po_matrix": {},
            "attainment_summary": {}
        }

        # Build CO-PO matrix
        for co in report["course_outcomes"]:
            report["co_po_matrix"][co] = {po: 0 for po in PROGRAM_OUTCOMES.keys()}

        # Map projects
        for project in projects:
            project_data = {
                "title": project.title,
                "difficulty": project.difficulty.value,
                "cos_mapped": project.course_outcomes_mapped,
                "pos_mapped": project.program_outcomes_mapped,
                "blooms_levels": project.blooms_levels
            }
            report["projects"].append(project_data)

            # Update CO-PO matrix
            for co in project.course_outcomes_mapped:
                if co in report["co_po_matrix"]:
                    for po in project.program_outcomes_mapped:
                        if po in report["co_po_matrix"][co]:
                            report["co_po_matrix"][co][po] = min(3, report["co_po_matrix"][co][po] + 1)

        return report


class IndustryUseCaseLibrary:
    """
    Library of industry-aligned project use cases.
    Organized by domain, difficulty, and project type.
    """

    def __init__(self):
        self.use_cases = self._initialize_use_cases()

    def _initialize_use_cases(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize the industry use case library."""
        return {
            TechnologyDomain.WEB_DEVELOPMENT.value: [
                {
                    "title": "E-Commerce Platform with Payment Integration",
                    "description": "Build a full-featured e-commerce platform with product catalog, cart, checkout, and payment gateway integration",
                    "difficulty": "advanced",
                    "project_type": "capstone",
                    "technologies": ["React", "Node.js", "MongoDB", "Stripe", "Redis"],
                    "duration_weeks": 10,
                    "team_size": 4,
                    "industry_relevance": "Direct industry application in retail and online business",
                    "learning_objectives": [
                        "Design scalable web architecture",
                        "Implement secure payment processing",
                        "Build responsive user interfaces",
                        "Handle real-time inventory management"
                    ],
                    "deliverables": ["Source code", "API documentation", "User manual", "Deployment guide"],
                    "evaluation_criteria": ["Functionality", "Security", "Performance", "Code quality"]
                },
                {
                    "title": "Learning Management System (LMS)",
                    "description": "Create an online learning platform with course management, video streaming, quizzes, and progress tracking",
                    "difficulty": "advanced",
                    "project_type": "capstone",
                    "technologies": ["Next.js", "PostgreSQL", "AWS S3", "WebRTC", "Socket.io"],
                    "duration_weeks": 12,
                    "team_size": 4,
                    "industry_relevance": "EdTech sector - rapidly growing industry",
                    "learning_objectives": [
                        "Implement video streaming",
                        "Design assessment systems",
                        "Build real-time features",
                        "Handle large file uploads"
                    ],
                    "deliverables": ["Platform", "Mobile-responsive UI", "Admin dashboard", "Analytics"],
                    "evaluation_criteria": ["User experience", "Scalability", "Feature completeness"]
                },
                {
                    "title": "Real-time Collaboration Tool",
                    "description": "Build a Notion/Google Docs-like collaborative editor with real-time sync",
                    "difficulty": "expert",
                    "project_type": "capstone",
                    "technologies": ["React", "Node.js", "Socket.io", "CRDTs", "MongoDB"],
                    "duration_weeks": 10,
                    "team_size": 3,
                    "industry_relevance": "Remote work tools - high demand",
                    "learning_objectives": [
                        "Implement real-time synchronization",
                        "Handle conflict resolution",
                        "Build rich text editors",
                        "Optimize for performance"
                    ],
                    "deliverables": ["Web app", "Real-time sync engine", "Documentation"],
                    "evaluation_criteria": ["Real-time accuracy", "Performance", "User experience"]
                },
                {
                    "title": "Task Management Dashboard",
                    "description": "Build a Kanban-style project management tool with drag-drop, assignments, and notifications",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["React", "Express", "MongoDB", "JWT", "Tailwind CSS"],
                    "duration_weeks": 4,
                    "team_size": 2,
                    "industry_relevance": "Productivity tools for teams",
                    "learning_objectives": [
                        "Implement drag-and-drop interfaces",
                        "Build authentication systems",
                        "Design RESTful APIs",
                        "Create responsive dashboards"
                    ],
                    "deliverables": ["Web application", "REST API", "Documentation"],
                    "evaluation_criteria": ["UI/UX", "Functionality", "Code organization"]
                },
                {
                    "title": "Personal Portfolio Generator",
                    "description": "Create a portfolio website generator with templates and CMS",
                    "difficulty": "beginner",
                    "project_type": "mini_project",
                    "technologies": ["HTML", "CSS", "JavaScript", "Node.js"],
                    "duration_weeks": 2,
                    "team_size": 1,
                    "industry_relevance": "Essential for developers",
                    "learning_objectives": [
                        "Build responsive layouts",
                        "Implement template systems",
                        "Handle form submissions"
                    ],
                    "deliverables": ["Portfolio site", "Template engine"],
                    "evaluation_criteria": ["Design", "Responsiveness", "Code quality"]
                }
            ],
            TechnologyDomain.AI_ML.value: [
                {
                    "title": "Intelligent Document Processing System",
                    "description": "Build an AI system that extracts, classifies, and summarizes documents using NLP",
                    "difficulty": "advanced",
                    "project_type": "capstone",
                    "technologies": ["Python", "TensorFlow", "Transformers", "FastAPI", "PostgreSQL"],
                    "duration_weeks": 10,
                    "team_size": 3,
                    "industry_relevance": "Document automation - enterprise demand",
                    "learning_objectives": [
                        "Implement NLP pipelines",
                        "Train document classifiers",
                        "Build text extraction systems",
                        "Deploy ML models as APIs"
                    ],
                    "deliverables": ["ML models", "REST API", "Web interface", "Documentation"],
                    "evaluation_criteria": ["Accuracy", "Performance", "API design"]
                },
                {
                    "title": "Predictive Maintenance System",
                    "description": "Build an IoT + ML system that predicts equipment failures",
                    "difficulty": "expert",
                    "project_type": "research",
                    "technologies": ["Python", "scikit-learn", "TensorFlow", "MQTT", "InfluxDB"],
                    "duration_weeks": 12,
                    "team_size": 4,
                    "industry_relevance": "Industry 4.0 - manufacturing sector",
                    "learning_objectives": [
                        "Process time-series data",
                        "Build predictive models",
                        "Integrate IoT sensors",
                        "Create monitoring dashboards"
                    ],
                    "deliverables": ["ML pipeline", "Dashboard", "Alert system", "Research paper"],
                    "evaluation_criteria": ["Prediction accuracy", "Real-time processing", "Scalability"]
                },
                {
                    "title": "Sentiment Analysis Dashboard",
                    "description": "Build a real-time sentiment analysis system for social media",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Python", "NLTK", "Flask", "React", "MongoDB"],
                    "duration_weeks": 4,
                    "team_size": 2,
                    "industry_relevance": "Social media monitoring",
                    "learning_objectives": [
                        "Implement sentiment classification",
                        "Process streaming data",
                        "Visualize analytics",
                        "Build REST APIs"
                    ],
                    "deliverables": ["ML model", "Web dashboard", "API"],
                    "evaluation_criteria": ["Accuracy", "Real-time performance", "Visualization"]
                },
                {
                    "title": "Image Classification App",
                    "description": "Build a mobile app that classifies images using CNN",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Python", "TensorFlow", "Flutter", "FastAPI"],
                    "duration_weeks": 5,
                    "team_size": 2,
                    "industry_relevance": "Computer vision applications",
                    "learning_objectives": [
                        "Train CNN models",
                        "Deploy models on mobile",
                        "Optimize for edge devices"
                    ],
                    "deliverables": ["Trained model", "Mobile app", "API"],
                    "evaluation_criteria": ["Accuracy", "Speed", "Mobile performance"]
                },
                {
                    "title": "Chatbot with Intent Recognition",
                    "description": "Build a conversational AI chatbot for customer support",
                    "difficulty": "beginner",
                    "project_type": "mini_project",
                    "technologies": ["Python", "Rasa", "Flask", "SQLite"],
                    "duration_weeks": 3,
                    "team_size": 2,
                    "industry_relevance": "Customer service automation",
                    "learning_objectives": [
                        "Design conversation flows",
                        "Train intent classifiers",
                        "Handle context management"
                    ],
                    "deliverables": ["Chatbot", "Training data", "Integration guide"],
                    "evaluation_criteria": ["Response accuracy", "Conversation flow", "User experience"]
                }
            ],
            TechnologyDomain.CLOUD_COMPUTING.value: [
                {
                    "title": "Multi-Tenant SaaS Platform",
                    "description": "Build a scalable multi-tenant application with isolated data and billing",
                    "difficulty": "expert",
                    "project_type": "capstone",
                    "technologies": ["Node.js", "PostgreSQL", "AWS", "Terraform", "Docker"],
                    "duration_weeks": 12,
                    "team_size": 4,
                    "industry_relevance": "SaaS business model",
                    "learning_objectives": [
                        "Design multi-tenant architecture",
                        "Implement data isolation",
                        "Build subscription billing",
                        "Deploy on cloud infrastructure"
                    ],
                    "deliverables": ["Platform", "Infrastructure code", "Documentation"],
                    "evaluation_criteria": ["Scalability", "Security", "Cost optimization"]
                },
                {
                    "title": "Serverless Data Pipeline",
                    "description": "Build an event-driven data processing pipeline using serverless",
                    "difficulty": "advanced",
                    "project_type": "capstone",
                    "technologies": ["AWS Lambda", "S3", "DynamoDB", "Step Functions", "Python"],
                    "duration_weeks": 6,
                    "team_size": 2,
                    "industry_relevance": "Data engineering",
                    "learning_objectives": [
                        "Design serverless architectures",
                        "Implement event-driven systems",
                        "Process data at scale",
                        "Monitor serverless applications"
                    ],
                    "deliverables": ["Pipeline", "IaC templates", "Monitoring dashboard"],
                    "evaluation_criteria": ["Reliability", "Cost efficiency", "Performance"]
                },
                {
                    "title": "Kubernetes Deployment Platform",
                    "description": "Build a self-service platform for deploying applications on Kubernetes",
                    "difficulty": "advanced",
                    "project_type": "capstone",
                    "technologies": ["Kubernetes", "Helm", "ArgoCD", "React", "Go"],
                    "duration_weeks": 8,
                    "team_size": 3,
                    "industry_relevance": "Platform engineering",
                    "learning_objectives": [
                        "Manage Kubernetes clusters",
                        "Implement GitOps workflows",
                        "Build developer portals",
                        "Automate deployments"
                    ],
                    "deliverables": ["Platform", "Helm charts", "Documentation"],
                    "evaluation_criteria": ["Automation", "Reliability", "User experience"]
                },
                {
                    "title": "Cloud Cost Optimizer",
                    "description": "Build a tool to analyze and optimize cloud spending",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Python", "AWS SDK", "React", "PostgreSQL"],
                    "duration_weeks": 4,
                    "team_size": 2,
                    "industry_relevance": "FinOps - cost management",
                    "learning_objectives": [
                        "Analyze cloud billing data",
                        "Identify optimization opportunities",
                        "Build recommendation engines"
                    ],
                    "deliverables": ["Dashboard", "Recommendations engine", "Reports"],
                    "evaluation_criteria": ["Accuracy", "Actionability", "Visualization"]
                }
            ],
            TechnologyDomain.MOBILE_DEVELOPMENT.value: [
                {
                    "title": "Health & Fitness Tracking App",
                    "description": "Build a comprehensive fitness app with workout tracking, nutrition, and social features",
                    "difficulty": "advanced",
                    "project_type": "capstone",
                    "technologies": ["Flutter", "Firebase", "Node.js", "MongoDB"],
                    "duration_weeks": 10,
                    "team_size": 3,
                    "industry_relevance": "Health tech - growing market",
                    "learning_objectives": [
                        "Build cross-platform apps",
                        "Integrate device sensors",
                        "Implement social features",
                        "Handle offline data sync"
                    ],
                    "deliverables": ["Mobile app", "Backend API", "Admin panel"],
                    "evaluation_criteria": ["UI/UX", "Performance", "Feature completeness"]
                },
                {
                    "title": "Food Delivery App Clone",
                    "description": "Build a Swiggy/Zomato-like food delivery app with real-time tracking",
                    "difficulty": "advanced",
                    "project_type": "capstone",
                    "technologies": ["React Native", "Node.js", "MongoDB", "Socket.io", "Maps API"],
                    "duration_weeks": 12,
                    "team_size": 4,
                    "industry_relevance": "Food delivery - established market",
                    "learning_objectives": [
                        "Build location-based services",
                        "Implement real-time tracking",
                        "Handle payments",
                        "Build multi-role apps"
                    ],
                    "deliverables": ["Customer app", "Driver app", "Restaurant app", "Admin dashboard"],
                    "evaluation_criteria": ["Real-time accuracy", "User experience", "Scalability"]
                },
                {
                    "title": "Expense Tracker App",
                    "description": "Build a personal finance app with budget tracking and analytics",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Flutter", "SQLite", "Charts library"],
                    "duration_weeks": 4,
                    "team_size": 2,
                    "industry_relevance": "Personal finance apps",
                    "learning_objectives": [
                        "Build local-first apps",
                        "Implement data visualization",
                        "Design intuitive UIs"
                    ],
                    "deliverables": ["Mobile app", "Documentation"],
                    "evaluation_criteria": ["UI/UX", "Functionality", "Performance"]
                },
                {
                    "title": "QR Code Scanner App",
                    "description": "Build a QR code scanner with history and sharing features",
                    "difficulty": "beginner",
                    "project_type": "mini_project",
                    "technologies": ["Flutter", "Camera API", "SQLite"],
                    "duration_weeks": 2,
                    "team_size": 1,
                    "industry_relevance": "Utility apps",
                    "learning_objectives": [
                        "Use device camera",
                        "Process QR codes",
                        "Store scan history"
                    ],
                    "deliverables": ["Mobile app"],
                    "evaluation_criteria": ["Scanning accuracy", "Speed", "UI"]
                }
            ],
            TechnologyDomain.BLOCKCHAIN.value: [
                {
                    "title": "Decentralized Voting System",
                    "description": "Build a transparent voting system using blockchain",
                    "difficulty": "advanced",
                    "project_type": "capstone",
                    "technologies": ["Solidity", "Ethereum", "React", "Web3.js", "IPFS"],
                    "duration_weeks": 10,
                    "team_size": 3,
                    "industry_relevance": "Governance and transparency",
                    "learning_objectives": [
                        "Write smart contracts",
                        "Build DApps",
                        "Handle blockchain transactions",
                        "Implement voting mechanisms"
                    ],
                    "deliverables": ["Smart contracts", "Web DApp", "Documentation"],
                    "evaluation_criteria": ["Security", "Gas optimization", "User experience"]
                },
                {
                    "title": "NFT Marketplace",
                    "description": "Build a marketplace for minting and trading NFTs",
                    "difficulty": "advanced",
                    "project_type": "capstone",
                    "technologies": ["Solidity", "Next.js", "IPFS", "Ethers.js", "Hardhat"],
                    "duration_weeks": 8,
                    "team_size": 3,
                    "industry_relevance": "Digital assets market",
                    "learning_objectives": [
                        "Implement ERC-721 tokens",
                        "Build auction systems",
                        "Integrate wallets",
                        "Handle IPFS storage"
                    ],
                    "deliverables": ["Smart contracts", "Marketplace frontend", "Admin panel"],
                    "evaluation_criteria": ["Security", "Functionality", "Gas efficiency"]
                },
                {
                    "title": "Supply Chain Tracker",
                    "description": "Build a blockchain-based supply chain tracking system",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Solidity", "React", "Node.js", "Web3.js"],
                    "duration_weeks": 5,
                    "team_size": 2,
                    "industry_relevance": "Supply chain transparency",
                    "learning_objectives": [
                        "Design supply chain flows",
                        "Implement tracking logic",
                        "Build verification systems"
                    ],
                    "deliverables": ["Smart contract", "Web interface", "QR integration"],
                    "evaluation_criteria": ["Traceability", "Security", "Usability"]
                }
            ],
            TechnologyDomain.IOT.value: [
                {
                    "title": "Smart Home Automation System",
                    "description": "Build an IoT system to control home appliances with voice and app",
                    "difficulty": "advanced",
                    "project_type": "capstone",
                    "technologies": ["ESP32", "MQTT", "Node.js", "React", "Google Assistant"],
                    "duration_weeks": 10,
                    "team_size": 3,
                    "industry_relevance": "Smart home market",
                    "learning_objectives": [
                        "Program microcontrollers",
                        "Implement MQTT protocols",
                        "Build mobile controls",
                        "Integrate voice assistants"
                    ],
                    "deliverables": ["Hardware prototype", "Mobile app", "Backend", "Documentation"],
                    "evaluation_criteria": ["Reliability", "Latency", "User experience"]
                },
                {
                    "title": "Environmental Monitoring Station",
                    "description": "Build a weather and air quality monitoring station with dashboard",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Arduino", "Sensors", "Python", "InfluxDB", "Grafana"],
                    "duration_weeks": 4,
                    "team_size": 2,
                    "industry_relevance": "Environmental monitoring",
                    "learning_objectives": [
                        "Interface sensors",
                        "Store time-series data",
                        "Build visualization dashboards"
                    ],
                    "deliverables": ["Hardware station", "Dashboard", "API"],
                    "evaluation_criteria": ["Accuracy", "Reliability", "Visualization"]
                },
                {
                    "title": "Smart Parking System",
                    "description": "Build an IoT-based parking management system with availability tracking",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Raspberry Pi", "Ultrasonic sensors", "Python", "React"],
                    "duration_weeks": 5,
                    "team_size": 3,
                    "industry_relevance": "Smart city solutions",
                    "learning_objectives": [
                        "Build sensor networks",
                        "Process real-time data",
                        "Build mobile interfaces"
                    ],
                    "deliverables": ["Hardware prototype", "Mobile app", "Admin dashboard"],
                    "evaluation_criteria": ["Detection accuracy", "Real-time updates", "Scalability"]
                }
            ],
            TechnologyDomain.DATA_SCIENCE.value: [
                {
                    "title": "Customer Churn Prediction System",
                    "description": "Build an ML system to predict and prevent customer churn",
                    "difficulty": "advanced",
                    "project_type": "capstone",
                    "technologies": ["Python", "scikit-learn", "XGBoost", "Streamlit", "PostgreSQL"],
                    "duration_weeks": 8,
                    "team_size": 3,
                    "industry_relevance": "Customer retention - all industries",
                    "learning_objectives": [
                        "Build classification models",
                        "Feature engineering",
                        "Model interpretation",
                        "Build ML dashboards"
                    ],
                    "deliverables": ["ML model", "Dashboard", "API", "Documentation"],
                    "evaluation_criteria": ["Prediction accuracy", "Business insights", "Usability"]
                },
                {
                    "title": "Sales Forecasting Dashboard",
                    "description": "Build a time-series forecasting system for sales prediction",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Python", "Prophet", "Pandas", "Plotly", "Flask"],
                    "duration_weeks": 4,
                    "team_size": 2,
                    "industry_relevance": "Business analytics",
                    "learning_objectives": [
                        "Time-series analysis",
                        "Build forecasting models",
                        "Create interactive visualizations"
                    ],
                    "deliverables": ["Forecasting model", "Dashboard", "API"],
                    "evaluation_criteria": ["Forecast accuracy", "Visualization quality"]
                },
                {
                    "title": "Data Quality Monitoring Tool",
                    "description": "Build a tool to monitor and report data quality issues",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Python", "Great Expectations", "Airflow", "PostgreSQL"],
                    "duration_weeks": 4,
                    "team_size": 2,
                    "industry_relevance": "Data governance",
                    "learning_objectives": [
                        "Define data quality rules",
                        "Build monitoring pipelines",
                        "Generate quality reports"
                    ],
                    "deliverables": ["Quality framework", "Dashboard", "Alert system"],
                    "evaluation_criteria": ["Detection accuracy", "Automation", "Reporting"]
                }
            ],
            TechnologyDomain.CYBERSECURITY.value: [
                {
                    "title": "Vulnerability Scanner",
                    "description": "Build an automated web application vulnerability scanner",
                    "difficulty": "advanced",
                    "project_type": "capstone",
                    "technologies": ["Python", "OWASP ZAP", "Docker", "React", "PostgreSQL"],
                    "duration_weeks": 10,
                    "team_size": 3,
                    "industry_relevance": "Security testing",
                    "learning_objectives": [
                        "Understand web vulnerabilities",
                        "Build scanning engines",
                        "Generate security reports"
                    ],
                    "deliverables": ["Scanner tool", "Dashboard", "Report generator"],
                    "evaluation_criteria": ["Detection accuracy", "False positive rate", "Usability"]
                },
                {
                    "title": "Password Manager",
                    "description": "Build a secure password manager with encryption",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Python", "AES encryption", "React", "SQLite"],
                    "duration_weeks": 4,
                    "team_size": 2,
                    "industry_relevance": "Personal security",
                    "learning_objectives": [
                        "Implement encryption",
                        "Secure key management",
                        "Build secure UIs"
                    ],
                    "deliverables": ["Desktop/mobile app", "Browser extension"],
                    "evaluation_criteria": ["Security", "Usability", "Cross-platform support"]
                },
                {
                    "title": "Network Traffic Analyzer",
                    "description": "Build a tool to capture and analyze network traffic",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Python", "Scapy", "Wireshark", "Flask"],
                    "duration_weeks": 4,
                    "team_size": 2,
                    "industry_relevance": "Network security",
                    "learning_objectives": [
                        "Capture network packets",
                        "Analyze traffic patterns",
                        "Detect anomalies"
                    ],
                    "deliverables": ["Analyzer tool", "Dashboard", "Reports"],
                    "evaluation_criteria": ["Analysis accuracy", "Performance", "Visualization"]
                }
            ],
            TechnologyDomain.DEVOPS.value: [
                {
                    "title": "CI/CD Pipeline Generator",
                    "description": "Build a tool that generates CI/CD pipelines based on project type",
                    "difficulty": "advanced",
                    "project_type": "capstone",
                    "technologies": ["Python", "Jenkins", "GitHub Actions", "Docker", "Kubernetes"],
                    "duration_weeks": 8,
                    "team_size": 3,
                    "industry_relevance": "DevOps automation",
                    "learning_objectives": [
                        "Design CI/CD workflows",
                        "Implement pipeline generators",
                        "Integrate multiple CI systems"
                    ],
                    "deliverables": ["Generator tool", "Templates", "Documentation"],
                    "evaluation_criteria": ["Flexibility", "Reliability", "Ease of use"]
                },
                {
                    "title": "Infrastructure Monitoring Dashboard",
                    "description": "Build a centralized monitoring dashboard for infrastructure",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Prometheus", "Grafana", "Python", "Docker"],
                    "duration_weeks": 4,
                    "team_size": 2,
                    "industry_relevance": "Infrastructure management",
                    "learning_objectives": [
                        "Set up monitoring systems",
                        "Create alerting rules",
                        "Build custom dashboards"
                    ],
                    "deliverables": ["Monitoring stack", "Dashboards", "Alerts"],
                    "evaluation_criteria": ["Coverage", "Alert accuracy", "Visualization"]
                },
                {
                    "title": "Log Analysis Platform",
                    "description": "Build a centralized log aggregation and analysis platform",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["ELK Stack", "Python", "Docker", "Kafka"],
                    "duration_weeks": 5,
                    "team_size": 2,
                    "industry_relevance": "Observability",
                    "learning_objectives": [
                        "Aggregate logs from multiple sources",
                        "Build search and analysis features",
                        "Create log-based alerts"
                    ],
                    "deliverables": ["Log platform", "Dashboards", "Alert system"],
                    "evaluation_criteria": ["Search performance", "Scalability", "Usability"]
                }
            ],
            TechnologyDomain.DATABASE.value: [
                {
                    "title": "Database Migration Tool",
                    "description": "Build a tool for automated database schema migrations",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Python", "PostgreSQL", "MySQL", "SQLAlchemy"],
                    "duration_weeks": 4,
                    "team_size": 2,
                    "industry_relevance": "Database management",
                    "learning_objectives": [
                        "Handle schema changes",
                        "Build rollback mechanisms",
                        "Support multiple databases"
                    ],
                    "deliverables": ["Migration tool", "CLI", "Documentation"],
                    "evaluation_criteria": ["Reliability", "Rollback support", "Multi-DB support"]
                },
                {
                    "title": "Query Performance Analyzer",
                    "description": "Build a tool to analyze and optimize SQL queries",
                    "difficulty": "intermediate",
                    "project_type": "mini_project",
                    "technologies": ["Python", "PostgreSQL", "React", "explain analyze"],
                    "duration_weeks": 4,
                    "team_size": 2,
                    "industry_relevance": "Database optimization",
                    "learning_objectives": [
                        "Analyze query execution plans",
                        "Identify optimization opportunities",
                        "Build suggestion engines"
                    ],
                    "deliverables": ["Analyzer tool", "Dashboard", "Recommendations"],
                    "evaluation_criteria": ["Analysis accuracy", "Recommendations quality"]
                }
            ]
        }

    def get_use_cases_by_domain(self, domain: TechnologyDomain) -> List[Dict[str, Any]]:
        """Get all use cases for a specific domain."""
        return self.use_cases.get(domain.value, [])

    def get_all_use_cases(self) -> List[Dict[str, Any]]:
        """Get all use cases across all domains."""
        all_cases = []
        for domain_cases in self.use_cases.values():
            all_cases.extend(domain_cases)
        return all_cases

    def get_use_cases_by_difficulty(self, difficulty: DifficultyLevel) -> List[Dict[str, Any]]:
        """Get use cases filtered by difficulty level."""
        all_cases = self.get_all_use_cases()
        return [uc for uc in all_cases if uc.get("difficulty") == difficulty.value]

    def get_use_cases_by_type(self, project_type: ProjectType) -> List[Dict[str, Any]]:
        """Get use cases filtered by project type."""
        all_cases = self.get_all_use_cases()
        return [uc for uc in all_cases if uc.get("project_type") == project_type.value]

    def get_tech_stack_for_domain(self, domain: TechnologyDomain) -> List[str]:
        """Get recommended tech stack for a domain."""
        tech_stacks = {
            TechnologyDomain.WEB_DEVELOPMENT: ["React", "Node.js", "MongoDB", "Express", "Tailwind CSS", "PostgreSQL"],
            TechnologyDomain.MOBILE_DEVELOPMENT: ["Flutter", "React Native", "Firebase", "SQLite", "REST APIs"],
            TechnologyDomain.AI_ML: ["Python", "TensorFlow", "PyTorch", "scikit-learn", "FastAPI", "Pandas"],
            TechnologyDomain.DATA_SCIENCE: ["Python", "Pandas", "NumPy", "Matplotlib", "Jupyter", "SQL"],
            TechnologyDomain.CLOUD_COMPUTING: ["AWS", "Docker", "Kubernetes", "Terraform", "Python", "Go"],
            TechnologyDomain.DEVOPS: ["Jenkins", "GitHub Actions", "Docker", "Kubernetes", "Ansible", "Prometheus"],
            TechnologyDomain.CYBERSECURITY: ["Python", "Kali Linux", "Burp Suite", "Wireshark", "OWASP tools"],
            TechnologyDomain.IOT: ["Arduino", "Raspberry Pi", "MQTT", "Python", "Node.js", "InfluxDB"],
            TechnologyDomain.BLOCKCHAIN: ["Solidity", "Ethereum", "Web3.js", "Hardhat", "IPFS", "React"],
            TechnologyDomain.GAME_DEVELOPMENT: ["Unity", "C#", "Unreal Engine", "C++", "Blender"],
            TechnologyDomain.EMBEDDED_SYSTEMS: ["C", "C++", "ARM", "RTOS", "STM32"],
            TechnologyDomain.DATABASE: ["PostgreSQL", "MongoDB", "Redis", "MySQL", "SQLAlchemy", "Prisma"]
        }
        return tech_stacks.get(domain, ["Python", "JavaScript", "SQL"])

    def search_use_cases(self, query: str) -> List[Dict[str, Any]]:
        """Search use cases by keyword."""
        all_cases = self.get_all_use_cases()
        query_lower = query.lower()
        results = []

        for uc in all_cases:
            if (query_lower in uc.get("title", "").lower() or
                query_lower in uc.get("description", "").lower() or
                any(query_lower in tech.lower() for tech in uc.get("technologies", []))):
                results.append(uc)

        return results


# Singleton instances
curriculum_mapping_engine = CurriculumMappingEngine()
industry_library = IndustryUseCaseLibrary()
