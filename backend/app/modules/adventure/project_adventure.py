"""
🎮 PROJECT ADVENTURE - Interactive Project Generation System

Transforms boring "abstract → generate" into an exciting journey:
✨ Choose → Click → Interact → Customize → Watch magic → Learn → Download

This module handles the complete interactive flow for student engagement.
"""

from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
import random
import asyncio
from datetime import datetime

from app.core.logging_config import logger


class ProjectTheme(str, Enum):
    """Project theme categories"""
    AI_ML = "ai_ml"
    WEB_DEV = "web_dev"
    MOBILE_APP = "mobile_app"
    CLOUD = "cloud"
    IOT = "iot"
    CYBER_SECURITY = "cyber_security"
    BLOCKCHAIN = "blockchain"
    DATA_SCIENCE = "data_science"


class Difficulty(str, Enum):
    """Project difficulty levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"


class UIPersonality(str, Enum):
    """UI style personalities"""
    ELEGANT_SIMPLE = "elegant_simple"
    DARK_DEVELOPER = "dark_developer"
    SOFT_FAIRY = "soft_fairy"
    ROBOTIC_TECH = "robotic_tech"
    COLORFUL_STUDENT = "colorful_student"
    MINIMAL_CLEAN = "minimal_clean"
    GLASSMORPHISM = "glassmorphism"


@dataclass
class AdventureState:
    """Current state of the project adventure"""
    session_id: str
    stage: int = 1
    theme: Optional[ProjectTheme] = None
    difficulty: Optional[Difficulty] = None
    tech_stack: Dict[str, str] = field(default_factory=dict)
    features: List[str] = field(default_factory=list)
    ui_personality: Optional[UIPersonality] = None
    project_name: Optional[str] = None
    is_college_project: bool = True
    college_info: Dict[str, str] = field(default_factory=dict)
    answers: Dict[str, Any] = field(default_factory=dict)
    achievements: List[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class ProjectAdventure:
    """
    🎮 Interactive Project Adventure Engine

    Transforms project generation into a fun, engaging experience.
    """

    # Theme configurations with emojis and descriptions
    THEMES = {
        ProjectTheme.AI_ML: {
            "icon": "🤖",
            "name": "AI / Machine Learning",
            "description": "Build intelligent systems that learn and predict",
            "suggested_features": ["ML Model", "Data Visualization", "Prediction API", "Training Dashboard"],
            "tech_suggestions": {"backend": "FastAPI + Python", "ml": "TensorFlow/PyTorch", "database": "PostgreSQL"}
        },
        ProjectTheme.WEB_DEV: {
            "icon": "🌐",
            "name": "Web Development",
            "description": "Create stunning web applications",
            "suggested_features": ["Authentication", "Dashboard", "REST API", "Real-time Updates"],
            "tech_suggestions": {"frontend": "React + Tailwind", "backend": "FastAPI/Node.js", "database": "PostgreSQL"}
        },
        ProjectTheme.MOBILE_APP: {
            "icon": "📱",
            "name": "Mobile Application",
            "description": "Build apps for iOS and Android",
            "suggested_features": ["Push Notifications", "Offline Mode", "Camera Integration", "GPS Location"],
            "tech_suggestions": {"mobile": "React Native/Flutter", "backend": "FastAPI", "database": "Firebase"}
        },
        ProjectTheme.CLOUD: {
            "icon": "☁️",
            "name": "Cloud Computing",
            "description": "Harness the power of cloud infrastructure",
            "suggested_features": ["Auto Scaling", "Load Balancing", "Serverless Functions", "Container Orchestration"],
            "tech_suggestions": {"cloud": "AWS/GCP", "containers": "Docker + Kubernetes", "iac": "Terraform"}
        },
        ProjectTheme.IOT: {
            "icon": "🔌",
            "name": "Internet of Things",
            "description": "Connect devices and sensors",
            "suggested_features": ["Sensor Dashboard", "Real-time Monitoring", "Alerts", "Device Management"],
            "tech_suggestions": {"hardware": "Arduino/Raspberry Pi", "protocol": "MQTT", "backend": "Node.js"}
        },
        ProjectTheme.CYBER_SECURITY: {
            "icon": "🔐",
            "name": "Cyber Security",
            "description": "Protect systems and data",
            "suggested_features": ["Vulnerability Scanner", "Log Analysis", "Threat Detection", "Security Dashboard"],
            "tech_suggestions": {"backend": "Python", "tools": "OWASP", "database": "MongoDB"}
        },
        ProjectTheme.BLOCKCHAIN: {
            "icon": "⛓️",
            "name": "Blockchain",
            "description": "Build decentralized applications",
            "suggested_features": ["Smart Contracts", "Wallet Integration", "Token System", "Transaction History"],
            "tech_suggestions": {"blockchain": "Ethereum/Solana", "frontend": "React", "backend": "Node.js"}
        },
        ProjectTheme.DATA_SCIENCE: {
            "icon": "📊",
            "name": "Data Science",
            "description": "Analyze and visualize data",
            "suggested_features": ["Data Pipeline", "Interactive Charts", "Report Generation", "Export to Excel"],
            "tech_suggestions": {"analysis": "Pandas + NumPy", "viz": "Plotly/D3.js", "backend": "FastAPI"}
        }
    }

    # Difficulty configurations
    DIFFICULTIES = {
        Difficulty.BEGINNER: {
            "icon": "🌱",
            "name": "Beginner",
            "description": "Simple project with basic features",
            "file_count": "8-12 files",
            "complexity": "Basic CRUD operations",
            "estimated_time": "2-3 days learning"
        },
        Difficulty.INTERMEDIATE: {
            "icon": "🌿",
            "name": "Intermediate",
            "description": "Moderate complexity with advanced features",
            "file_count": "15-25 files",
            "complexity": "Authentication, APIs, Database relations",
            "estimated_time": "1-2 weeks"
        },
        Difficulty.EXPERT: {
            "icon": "🌳",
            "name": "Expert",
            "description": "Production-ready with enterprise features",
            "file_count": "30-50 files",
            "complexity": "Microservices, Caching, Testing, CI/CD",
            "estimated_time": "3-4 weeks"
        }
    }

    # UI Personalities
    PERSONALITIES = {
        UIPersonality.ELEGANT_SIMPLE: {
            "icon": "🌈",
            "name": "Elegant & Simple",
            "colors": {"primary": "#6366f1", "bg": "#ffffff", "text": "#1f2937"},
            "style": "Clean, minimalist, lots of whitespace"
        },
        UIPersonality.DARK_DEVELOPER: {
            "icon": "🔥",
            "name": "Dark Mode Developer",
            "colors": {"primary": "#22d3ee", "bg": "#0f172a", "text": "#e2e8f0"},
            "style": "Dark theme, neon accents, developer-focused"
        },
        UIPersonality.SOFT_FAIRY: {
            "icon": "🧚",
            "name": "Soft Fairy Theme",
            "colors": {"primary": "#ec4899", "bg": "#fdf2f8", "text": "#831843"},
            "style": "Soft pastels, rounded corners, playful"
        },
        UIPersonality.ROBOTIC_TECH: {
            "icon": "🦾",
            "name": "Robotic Tech UI",
            "colors": {"primary": "#10b981", "bg": "#111827", "text": "#d1fae5"},
            "style": "Futuristic, grid-based, tech-inspired"
        },
        UIPersonality.COLORFUL_STUDENT: {
            "icon": "🎨",
            "name": "Colorful Student-Friendly",
            "colors": {"primary": "#f59e0b", "bg": "#fffbeb", "text": "#78350f"},
            "style": "Vibrant colors, fun gradients, engaging"
        },
        UIPersonality.MINIMAL_CLEAN: {
            "icon": "⬜",
            "name": "Minimal Clean",
            "colors": {"primary": "#000000", "bg": "#ffffff", "text": "#000000"},
            "style": "Black and white, typography-focused"
        },
        UIPersonality.GLASSMORPHISM: {
            "icon": "💎",
            "name": "Glassmorphism",
            "colors": {"primary": "#8b5cf6", "bg": "#1e1b4b", "text": "#e0e7ff"},
            "style": "Glass effects, blur, transparency"
        }
    }

    # Feature options by category
    FEATURES = {
        "authentication": {
            "icon": "🔐",
            "options": [
                {"id": "email_login", "name": "Email/Password Login", "difficulty": "beginner"},
                {"id": "oauth", "name": "Google/GitHub OAuth", "difficulty": "intermediate"},
                {"id": "otp", "name": "OTP Verification", "difficulty": "intermediate"},
                {"id": "2fa", "name": "Two-Factor Auth", "difficulty": "expert"},
                {"id": "biometric", "name": "Biometric Login", "difficulty": "expert"}
            ]
        },
        "ui_features": {
            "icon": "🎨",
            "options": [
                {"id": "dark_mode", "name": "Dark Mode Toggle", "difficulty": "beginner"},
                {"id": "responsive", "name": "Mobile Responsive", "difficulty": "beginner"},
                {"id": "animations", "name": "Smooth Animations", "difficulty": "intermediate"},
                {"id": "themes", "name": "Multiple Themes", "difficulty": "intermediate"},
                {"id": "i18n", "name": "Multi-language", "difficulty": "expert"}
            ]
        },
        "data_features": {
            "icon": "📊",
            "options": [
                {"id": "crud", "name": "CRUD Operations", "difficulty": "beginner"},
                {"id": "search", "name": "Search & Filter", "difficulty": "beginner"},
                {"id": "pagination", "name": "Pagination", "difficulty": "beginner"},
                {"id": "export", "name": "Export to CSV/PDF", "difficulty": "intermediate"},
                {"id": "charts", "name": "Interactive Charts", "difficulty": "intermediate"},
                {"id": "realtime", "name": "Real-time Updates", "difficulty": "expert"}
            ]
        },
        "ai_features": {
            "icon": "🤖",
            "options": [
                {"id": "chatbot", "name": "AI Chatbot", "difficulty": "intermediate"},
                {"id": "recommendations", "name": "Smart Recommendations", "difficulty": "intermediate"},
                {"id": "image_recognition", "name": "Image Recognition", "difficulty": "expert"},
                {"id": "nlp", "name": "Natural Language Processing", "difficulty": "expert"},
                {"id": "prediction", "name": "Predictive Analytics", "difficulty": "expert"}
            ]
        },
        "communication": {
            "icon": "💬",
            "options": [
                {"id": "notifications", "name": "Push Notifications", "difficulty": "intermediate"},
                {"id": "email", "name": "Email Integration", "difficulty": "intermediate"},
                {"id": "sms", "name": "SMS Alerts", "difficulty": "intermediate"},
                {"id": "chat", "name": "Real-time Chat", "difficulty": "expert"},
                {"id": "video_call", "name": "Video Calling", "difficulty": "expert"}
            ]
        }
    }

    # Smart questions flow
    SMART_QUESTIONS = [
        {
            "id": "purpose",
            "question": "What should your project do? 🎯",
            "type": "text",
            "placeholder": "e.g., Help students manage their tasks and deadlines",
            "required": True
        },
        {
            "id": "is_college",
            "question": "Is this for college/university? 🎓",
            "type": "choice",
            "options": [
                {"value": True, "label": "Yes, it's a college project", "icon": "🎓"},
                {"value": False, "label": "No, personal/commercial", "icon": "💼"}
            ],
            "required": True
        },
        {
            "id": "platform",
            "question": "Where will it run? 💻",
            "type": "choice",
            "options": [
                {"value": "web", "label": "Web Browser", "icon": "🌐"},
                {"value": "mobile", "label": "Mobile App", "icon": "📱"},
                {"value": "desktop", "label": "Desktop App", "icon": "🖥️"},
                {"value": "all", "label": "All Platforms", "icon": "🚀"}
            ],
            "required": True
        },
        {
            "id": "users",
            "question": "Who will use it? 👥",
            "type": "multi_choice",
            "options": [
                {"value": "students", "label": "Students", "icon": "👨‍🎓"},
                {"value": "teachers", "label": "Teachers", "icon": "👨‍🏫"},
                {"value": "admins", "label": "Admins", "icon": "👨‍💼"},
                {"value": "public", "label": "General Public", "icon": "👥"},
                {"value": "businesses", "label": "Businesses", "icon": "🏢"}
            ],
            "required": True
        },
        {
            "id": "complexity",
            "question": "How complex should it be? 📈",
            "type": "choice",
            "options": [
                {"value": "simple", "label": "Simple & Clean", "icon": "🌱", "description": "Basic features, easy to understand"},
                {"value": "moderate", "label": "Feature-Rich", "icon": "🌿", "description": "Good balance of features"},
                {"value": "advanced", "label": "Production-Ready", "icon": "🌳", "description": "Enterprise-grade features"}
            ],
            "required": True
        },
        {
            "id": "ai_features",
            "question": "Want AI superpowers? 🤖",
            "type": "choice",
            "options": [
                {"value": "none", "label": "No AI needed", "icon": "➖"},
                {"value": "basic", "label": "Basic AI (Chatbot/Suggestions)", "icon": "💡"},
                {"value": "advanced", "label": "Advanced AI (ML Models)", "icon": "🧠"}
            ],
            "required": False
        },
        {
            "id": "ui_style",
            "question": "Pick your UI vibe! 🎨",
            "type": "choice",
            "options": [
                {"value": "modern", "label": "Modern & Sleek", "icon": "✨"},
                {"value": "playful", "label": "Fun & Colorful", "icon": "🎨"},
                {"value": "professional", "label": "Professional & Clean", "icon": "💼"},
                {"value": "dark", "label": "Dark Mode", "icon": "🌙"}
            ],
            "required": True
        }
    ]

    # Storytelling messages during build
    STORY_MESSAGES = {
        "planning": [
            "🧠 Analyzing your vision...",
            "📋 Creating the master plan...",
            "🎯 Mapping out the architecture...",
            "✨ Sprinkling some magic dust..."
        ],
        "backend": [
            "⚙️ Forging the backend engines...",
            "🔧 Crafting API endpoints...",
            "🗄️ Summoning database tables...",
            "🔐 Weaving security shields..."
        ],
        "frontend": [
            "🎨 Painting beautiful interfaces...",
            "✨ Adding sparkle to buttons...",
            "📱 Making it mobile-friendly...",
            "🌈 Applying your chosen style..."
        ],
        "features": [
            "🚀 Activating superpowers...",
            "💫 Installing cool features...",
            "🔮 Enchanting with functionality...",
            "⚡ Charging up the modules..."
        ],
        "testing": [
            "🧪 Running quality checks...",
            "🔍 Hunting for bugs...",
            "✅ Verifying everything works...",
            "🛡️ Stress-testing the system..."
        ],
        "docs": [
            "📚 Writing your documentation...",
            "📄 Generating IEEE reports...",
            "📊 Creating UML diagrams...",
            "📝 Preparing viva questions..."
        ],
        "finishing": [
            "🎁 Wrapping up your project...",
            "🏆 Adding final touches...",
            "🎉 Almost ready for launch...",
            "🚀 Preparing for takeoff..."
        ]
    }

    # Achievement badges
    ACHIEVEMENTS = {
        "first_choice": {"icon": "🎯", "title": "Decision Maker", "description": "Made your first choice!"},
        "theme_selected": {"icon": "🎨", "title": "Style Guru", "description": "Selected a project theme!"},
        "features_selected": {"icon": "⚡", "title": "Feature Hunter", "description": "Picked awesome features!"},
        "halfway": {"icon": "🌟", "title": "Halfway Hero", "description": "50% complete!"},
        "backend_done": {"icon": "⚙️", "title": "Backend Boss", "description": "Backend is ready!"},
        "frontend_done": {"icon": "🎨", "title": "UI Master", "description": "Frontend looks amazing!"},
        "docs_done": {"icon": "📚", "title": "Documentation Pro", "description": "72 pages generated!"},
        "project_complete": {"icon": "🏆", "title": "Project Champion", "description": "Your project is complete!"},
        "speed_demon": {"icon": "⚡", "title": "Speed Demon", "description": "Completed in record time!"},
        "feature_rich": {"icon": "💎", "title": "Feature King", "description": "Added 10+ features!"}
    }

    # Surprise project ideas
    SURPRISE_PROJECTS = [
        {
            "name": "StudyBuddy AI",
            "description": "AI-powered study companion that creates flashcards, quizzes, and tracks learning progress",
            "theme": ProjectTheme.AI_ML,
            "features": ["chatbot", "quiz_generator", "progress_tracking", "dark_mode"],
            "difficulty": Difficulty.INTERMEDIATE
        },
        {
            "name": "CampusConnect",
            "description": "Social platform for college students to find study groups, share notes, and collaborate",
            "theme": ProjectTheme.WEB_DEV,
            "features": ["oauth", "chat", "file_sharing", "notifications"],
            "difficulty": Difficulty.INTERMEDIATE
        },
        {
            "name": "HealthMate",
            "description": "Personal health tracker with medication reminders, fitness goals, and doctor appointments",
            "theme": ProjectTheme.MOBILE_APP,
            "features": ["notifications", "charts", "calendar", "export"],
            "difficulty": Difficulty.INTERMEDIATE
        },
        {
            "name": "SmartAttendance",
            "description": "Face recognition-based attendance system with real-time analytics dashboard",
            "theme": ProjectTheme.AI_ML,
            "features": ["image_recognition", "charts", "export", "notifications"],
            "difficulty": Difficulty.EXPERT
        },
        {
            "name": "BudgetWise",
            "description": "Personal finance manager with expense tracking, budget planning, and spending insights",
            "theme": ProjectTheme.WEB_DEV,
            "features": ["charts", "export", "notifications", "dark_mode"],
            "difficulty": Difficulty.BEGINNER
        },
        {
            "name": "EventHub",
            "description": "College event management platform for organizing, promoting, and attending campus events",
            "theme": ProjectTheme.WEB_DEV,
            "features": ["calendar", "email", "qr_tickets", "responsive"],
            "difficulty": Difficulty.INTERMEDIATE
        },
        {
            "name": "CodeReview AI",
            "description": "AI-powered code review tool that analyzes code quality, suggests improvements, and detects bugs",
            "theme": ProjectTheme.AI_ML,
            "features": ["nlp", "recommendations", "export", "dark_mode"],
            "difficulty": Difficulty.EXPERT
        },
        {
            "name": "PlantCare IoT",
            "description": "Smart plant monitoring system with soil moisture sensors and automated watering",
            "theme": ProjectTheme.IOT,
            "features": ["realtime", "charts", "notifications", "mobile_app"],
            "difficulty": Difficulty.INTERMEDIATE
        }
    ]

    def __init__(self):
        self.states: Dict[str, AdventureState] = {}

    def create_session(self, session_id: str) -> AdventureState:
        """Create a new adventure session"""
        state = AdventureState(session_id=session_id)
        self.states[session_id] = state
        logger.info(f"[Adventure] Created session: {session_id}")
        return state

    def get_session(self, session_id: str) -> Optional[AdventureState]:
        """Get existing session"""
        return self.states.get(session_id)

    def get_stage_1_options(self) -> Dict[str, Any]:
        """Get Stage 1: Theme & Difficulty selection options"""
        return {
            "stage": 1,
            "title": "🚀 Let's Build Something Amazing!",
            "subtitle": "First, let's pick your project adventure",
            "themes": [
                {
                    "id": theme.value,
                    "icon": config["icon"],
                    "name": config["name"],
                    "description": config["description"]
                }
                for theme, config in self.THEMES.items()
            ],
            "difficulties": [
                {
                    "id": diff.value,
                    "icon": config["icon"],
                    "name": config["name"],
                    "description": config["description"],
                    "details": {
                        "files": config["file_count"],
                        "complexity": config["complexity"],
                        "time": config["estimated_time"]
                    }
                }
                for diff, config in self.DIFFICULTIES.items()
            ]
        }

    def process_stage_1(
        self,
        session_id: str,
        theme: str,
        difficulty: str
    ) -> Dict[str, Any]:
        """Process Stage 1 selections"""
        state = self.get_session(session_id)
        if not state:
            state = self.create_session(session_id)

        state.theme = ProjectTheme(theme)
        state.difficulty = Difficulty(difficulty)
        state.stage = 2

        # Award achievement
        state.achievements.append("first_choice")
        state.achievements.append("theme_selected")

        # Get suggested features based on theme
        theme_config = self.THEMES[state.theme]

        return {
            "success": True,
            "next_stage": 2,
            "achievements": [self.ACHIEVEMENTS["first_choice"], self.ACHIEVEMENTS["theme_selected"]],
            "message": f"{theme_config['icon']} Great choice! Let's add some features!",
            "suggested_tech": theme_config["tech_suggestions"],
            "suggested_features": theme_config["suggested_features"]
        }

    def get_stage_2_options(self, session_id: str) -> Dict[str, Any]:
        """Get Stage 2: Smart Questions flow"""
        state = self.get_session(session_id)

        return {
            "stage": 2,
            "title": "🎯 Tell Me About Your Project",
            "subtitle": "Answer a few quick questions (like chatting with a friend!)",
            "questions": self.SMART_QUESTIONS,
            "current_selections": state.answers if state else {}
        }

    def process_stage_2(
        self,
        session_id: str,
        answers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Stage 2 answers"""
        state = self.get_session(session_id)
        if not state:
            return {"success": False, "error": "Session not found"}

        state.answers = answers
        state.is_college_project = answers.get("is_college", True)
        state.stage = 3

        return {
            "success": True,
            "next_stage": 3,
            "message": "🎨 Awesome! Now let's pick features and style!"
        }

    def get_stage_3_options(self, session_id: str) -> Dict[str, Any]:
        """Get Stage 3: Features & Personality selection"""
        state = self.get_session(session_id)
        difficulty = state.difficulty if state else Difficulty.INTERMEDIATE

        # Filter features by difficulty
        filtered_features = {}
        for category, config in self.FEATURES.items():
            filtered_options = [
                opt for opt in config["options"]
                if self._is_feature_available(opt["difficulty"], difficulty)
            ]
            if filtered_options:
                filtered_features[category] = {
                    "icon": config["icon"],
                    "options": filtered_options
                }

        return {
            "stage": 3,
            "title": "⚡ Choose Your Superpowers",
            "subtitle": "Pick features and style for your project",
            "features": filtered_features,
            "personalities": [
                {
                    "id": personality.value,
                    "icon": config["icon"],
                    "name": config["name"],
                    "colors": config["colors"],
                    "style": config["style"]
                }
                for personality, config in self.PERSONALITIES.items()
            ]
        }

    def _is_feature_available(self, feature_difficulty: str, selected_difficulty: Difficulty) -> bool:
        """Check if feature is available for selected difficulty"""
        difficulty_levels = {"beginner": 1, "intermediate": 2, "expert": 3}
        return difficulty_levels.get(feature_difficulty, 1) <= difficulty_levels.get(selected_difficulty.value, 2)

    def process_stage_3(
        self,
        session_id: str,
        features: List[str],
        personality: str,
        project_name: str
    ) -> Dict[str, Any]:
        """Process Stage 3 selections"""
        state = self.get_session(session_id)
        if not state:
            return {"success": False, "error": "Session not found"}

        state.features = features
        state.ui_personality = UIPersonality(personality)
        state.project_name = project_name
        state.stage = 4

        # Award achievements
        if len(features) >= 5:
            state.achievements.append("features_selected")
        if len(features) >= 10:
            state.achievements.append("feature_rich")

        achievements = [
            self.ACHIEVEMENTS[a] for a in state.achievements
            if a in ["features_selected", "feature_rich"]
        ]

        return {
            "success": True,
            "next_stage": 4,
            "achievements": achievements,
            "message": f"✨ '{project_name}' is going to be amazing!"
        }

    def get_stage_4_options(self, session_id: str) -> Dict[str, Any]:
        """Get Stage 4: College info (if applicable)"""
        state = self.get_session(session_id)

        if not state or not state.is_college_project:
            return {
                "stage": 4,
                "skip": True,
                "message": "Not a college project, skipping to build!"
            }

        return {
            "stage": 4,
            "title": "🎓 College Info (30 seconds!)",
            "subtitle": "Quick details for your official documents",
            "fields": [
                {"id": "student_name", "label": "Your Name", "icon": "👤", "required": True},
                {"id": "roll_number", "label": "Roll Number", "icon": "🔢", "required": True},
                {"id": "college_name", "label": "College Name", "icon": "🏫", "required": True},
                {"id": "department", "label": "Department", "icon": "📚", "required": True, "default": "Computer Science and Engineering"},
                {"id": "guide_name", "label": "Guide Name", "icon": "👨‍🏫", "required": True},
                {"id": "hod_name", "label": "HOD Name", "icon": "👔", "required": False},
                {"id": "principal_name", "label": "Principal Name", "icon": "🎖️", "required": False},
                {"id": "academic_year", "label": "Academic Year", "icon": "📅", "required": True, "default": "2024-2025"}
            ],
            "team_members": {
                "enabled": True,
                "max": 4,
                "fields": ["name", "roll_number"]
            }
        }

    def process_stage_4(
        self,
        session_id: str,
        college_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process Stage 4 college info"""
        state = self.get_session(session_id)
        if not state:
            return {"success": False, "error": "Session not found"}

        state.college_info = college_info
        state.stage = 5

        return {
            "success": True,
            "next_stage": 5,
            "message": "🚀 All set! Let's build your project!"
        }

    async def generate_story_messages(
        self,
        phase: str
    ) -> AsyncGenerator[str, None]:
        """Generate storytelling messages for a build phase"""
        messages = self.STORY_MESSAGES.get(phase, ["Working on it..."])
        for msg in messages:
            yield msg
            await asyncio.sleep(0.5)  # Small delay for effect

    def get_surprise_project(self) -> Dict[str, Any]:
        """Get a random surprise project"""
        project = random.choice(self.SURPRISE_PROJECTS)
        return {
            "name": project["name"],
            "description": project["description"],
            "theme": project["theme"].value,
            "theme_info": self.THEMES[project["theme"]],
            "features": project["features"],
            "difficulty": project["difficulty"].value,
            "difficulty_info": self.DIFFICULTIES[project["difficulty"]],
            "message": f"🎁 Surprise! How about building '{project['name']}'?"
        }

    def build_generation_config(self, session_id: str) -> Dict[str, Any]:
        """Build the complete configuration for project generation"""
        state = self.get_session(session_id)
        if not state:
            return {}

        theme_config = self.THEMES.get(state.theme, {})
        personality_config = self.PERSONALITIES.get(state.ui_personality, {})
        difficulty_config = self.DIFFICULTIES.get(state.difficulty, {})

        return {
            "project_name": state.project_name,
            "theme": state.theme.value if state.theme else "web_dev",
            "difficulty": state.difficulty.value if state.difficulty else "intermediate",
            "tech_stack": {
                **theme_config.get("tech_suggestions", {}),
                **state.tech_stack
            },
            "features": state.features,
            "ui_config": {
                "personality": state.ui_personality.value if state.ui_personality else "dark_developer",
                "colors": personality_config.get("colors", {}),
                "style": personality_config.get("style", "")
            },
            "is_college_project": state.is_college_project,
            "college_info": state.college_info,
            "user_answers": state.answers,
            "metadata": {
                "session_id": session_id,
                "started_at": state.started_at,
                "achievements": state.achievements
            }
        }

    def get_final_stats(self, session_id: str, generation_result: Dict[str, Any]) -> Dict[str, Any]:
        """Get final project statistics for celebration screen"""
        state = self.get_session(session_id)

        return {
            "project_name": state.project_name if state else "Your Project",
            "stats": {
                "files_created": generation_result.get("files_count", 0),
                "lines_of_code": generation_result.get("total_lines", 0),
                "dependencies": generation_result.get("dependencies_count", 0),
                "build_time": generation_result.get("build_time", "0s"),
                "doc_pages": generation_result.get("doc_pages", 0) if state and state.is_college_project else 0
            },
            "achievements": [
                self.ACHIEVEMENTS[a] for a in (state.achievements if state else [])
                if a in self.ACHIEVEMENTS
            ],
            "quick_actions": [
                {"id": "run", "label": "▶️ Run App", "action": "run_project"},
                {"id": "download", "label": "📥 Download ZIP", "action": "download_zip"},
                {"id": "docs", "label": "📄 View Docs", "action": "view_docs"},
                {"id": "enhance", "label": "✨ Add Features", "action": "enhance_project"}
            ],
            "celebration_message": self._get_celebration_message(generation_result)
        }

    def _get_celebration_message(self, result: Dict[str, Any]) -> str:
        """Generate a fun celebration message"""
        messages = [
            "🎉 Your project is ready to conquer the world!",
            "🚀 Houston, we have a successful launch!",
            "✨ Magic complete! Your project awaits!",
            "🏆 Champion! You've built something amazing!",
            "🎊 Woohoo! Time to show off your creation!",
            "💫 Spectacular! Your project is live!",
            "🌟 Star developer! Project complete!"
        ]
        return random.choice(messages)


# Singleton instance
project_adventure = ProjectAdventure()
