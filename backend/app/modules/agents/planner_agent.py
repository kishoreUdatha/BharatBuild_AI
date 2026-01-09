"""
AGENT 1 - Planner Agent
Understands user requests and creates detailed project plans
"""

from typing import Dict, List, Optional, Any
import json
from datetime import datetime
from pathlib import Path

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext


class PlannerAgent(BaseAgent):
    """
    Planner / Understanding Agent with Dynamic Prompt Loading

    Responsibilities:
    - Understand vague or abstract user requests
    - Identify project requirements
    - Determine appropriate technology stack
    - Create detailed feature lists
    - Plan implementation steps
    - Consider learning goals for students

    Optimization:
    - Detects technology from user request
    - Loads only relevant prompt sections (~300 lines vs 2000+ lines)
    - Reduces API costs and improves response quality
    """

    # Prompt directory
    PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"

    # Technology detection keywords
    TECH_KEYWORDS = {
        "react": ["react", "vite", "tsx", "frontend", "tailwind", "next.js", "nextjs", "ui", "dashboard"],
        "python": ["fastapi", "django", "flask", "python", "uvicorn", "sqlalchemy", "backend", "api"],
        "java": ["spring", "java", "maven", "gradle", "spring boot", "springboot"],
        "node": ["express", "node", "nestjs", "prisma"],
        "mobile": ["flutter", "react native", "android", "ios", "kotlin", "swift"],
        "ai_ml": ["machine learning", "ml", "ai", "tensorflow", "pytorch", "model", "neural", "prediction"],
    }

    @classmethod
    def _load_prompt_file(cls, filename: str) -> str:
        """Load a prompt file from the prompts directory"""
        filepath = cls.PROMPTS_DIR / filename
        if filepath.exists():
            return filepath.read_text(encoding="utf-8")
        logger.warning(f"[PlannerAgent] Prompt file not found: {filepath}")
        return ""

    @classmethod
    def _detect_technologies(cls, user_request: str) -> List[str]:
        """Detect technologies mentioned in user request"""
        request_lower = user_request.lower()
        detected = []

        for tech, keywords in cls.TECH_KEYWORDS.items():
            if any(kw in request_lower for kw in keywords):
                detected.append(tech)

        # Default to react + python for fullstack if no specific tech mentioned
        if not detected:
            # Check for fullstack indicators
            if any(word in request_lower for word in ["app", "application", "platform", "system", "dashboard", "portal", "website"]):
                detected = ["react", "python"]
            else:
                detected = ["react"]  # Default to React for frontend

        logger.info(f"[PlannerAgent] Detected technologies: {detected}")
        return detected

    @classmethod
    def _build_dynamic_prompt(cls, user_request: str) -> str:
        """Build prompt dynamically based on detected technologies - REDUCES PROMPT FROM 50k TO ~8k TOKENS"""
        # Always load core prompt
        core_prompt = cls._load_prompt_file("planner_core.txt")

        if not core_prompt:
            logger.warning("[PlannerAgent] Core prompt not found! Using SYSTEM_PROMPT fallback.")
            return cls.SYSTEM_PROMPT  # Fall back to the hardcoded prompt

        # Detect technologies and load relevant prompts
        detected_techs = cls._detect_technologies(user_request)

        tech_prompts = []
        prompt_mapping = {
            "react": "planner_react.txt",
            "python": "planner_python.txt",
            "java": "planner_java.txt",
        }

        for tech in detected_techs:
            if tech in prompt_mapping:
                tech_prompt = cls._load_prompt_file(prompt_mapping[tech])
                if tech_prompt:
                    tech_prompts.append(f"\n{'='*60}\n{tech.upper()} SPECIFIC RULES:\n{'='*60}\n{tech_prompt}")

        # Combine prompts
        full_prompt = core_prompt
        if tech_prompts:
            full_prompt += "\n" + "\n".join(tech_prompts)

        # Log prompt size for debugging
        token_estimate = len(full_prompt) // 4
        logger.info(f"[PlannerAgent] Dynamic prompt size: ~{token_estimate} tokens (vs ~50k with old prompt)")

        return full_prompt

    # FALLBACK: Keep the original SYSTEM_PROMPT for backwards compatibility
    SYSTEM_PROMPT = """You are the PLANNER AGENT for a Bolt.new-style multi-purpose project generator.

YOUR JOB:
1. Understand ANY user prompt: web app, mobile app, AI, ML, IoT, automation, CLI, college project, or startup MVP.
2. Automatically detect whether the project is:
   - Commercial Application
   - Academic/Student Project
   - Research Project
   - Prototype/MVP
   - AI Workflow
3. Select the optimal tech stack dynamically. DO NOT hardcode stacks.
4. Identify functional modules needed.
5. Identify backend, frontend, database, auth, APIs, ML models, external services.
6. Generate a COMPLETE step-by-step plan that the Writer Agent can follow.
7. ALWAYS choose simple, stable, modern technology (unless user explicitly requests something else).
8. If it's a student project, include required documents (SRS, Report, PPT, UML, Viva).
9. The plan MUST be executable automatically by Writer + Fixer + Runner agents.

OUTPUT FORMAT (MANDATORY):
<plan>
  <project_name>A professional, descriptive name for this project (e.g., "E-Commerce Platform", "Task Management System", "AI Phishing Detection Tool")</project_name>
  <project_description>A brief 1-2 sentence description of what the project does</project_description>
  <project_type>...</project_type>
  <design_theme>
    <domain>energy|finance|healthcare|food|ecommerce|education|gaming|travel|realestate|business|agriculture|security|aiml|default</domain>
    <primary_color>emerald|blue|cyan|orange|violet|indigo|pink|sky|amber|slate|lime|red|purple</primary_color>
    <secondary_color>teal|indigo|teal|red|purple|blue|fuchsia|blue|yellow|gray|green|rose|pink</secondary_color>
    <background>from-slate-900 to-gray-900</background>
    <accent>yellow|green|red|amber|pink|amber|cyan|amber|green|blue|amber|green|orange</accent>
  </design_theme>
  <tech_stack>...</tech_stack>
  <project_structure>...</project_structure>
  <files>
    <file path="path/to/file.tsx" priority="1" depends_on="">
      <description>Description of what this file does</description>
      <exports>ComponentName, functionName</exports>
    </file>
    <file path="path/to/another.ts" priority="2" depends_on="path/to/file.tsx">
      <description>Description of what this file does</description>
      <imports>ComponentName from path/to/file.tsx</imports>
      <exports>AnotherComponent</exports>
    </file>
    ...
  </files>
  <tasks>
    Step 1: ...
    Step 2: ...
    Step 3: ...
  </tasks>
  <notes>...</notes>
</plan>

═══════════════════════════════════════════════════════════════════════════════
                    🎨 DESIGN THEME SELECTION (REQUIRED!)
═══════════════════════════════════════════════════════════════════════════════

You MUST select appropriate colors based on project domain. DO NOT use same colors for all projects!

DOMAIN DETECTION AND COLOR MAPPING:

🔋 ENERGY/UTILITIES (Keywords: power, electric, bill, solar, energy, utility, meter, consumption):
  <domain>energy</domain>
  <primary_color>emerald</primary_color>
  <secondary_color>teal</secondary_color>
  <background>from-slate-900 to-gray-900</background>
  <accent>yellow</accent>

💰 FINANCE/BANKING (Keywords: payment, bank, money, trading, crypto, budget, invoice, wallet):
  <domain>finance</domain>
  <primary_color>blue</primary_color>
  <secondary_color>indigo</secondary_color>
  <background>from-slate-950 to-blue-950</background>
  <accent>green</accent>

🏥 HEALTHCARE/MEDICAL (Keywords: hospital, doctor, patient, pharmacy, health, fitness, medical):
  <domain>healthcare</domain>
  <primary_color>cyan</primary_color>
  <secondary_color>teal</secondary_color>
  <background>from-gray-900 to-slate-900</background>
  <accent>red</accent>

🍔 FOOD/RESTAURANT (Keywords: food, restaurant, recipe, delivery, menu, order, cooking):
  <domain>food</domain>
  <primary_color>orange</primary_color>
  <secondary_color>red</secondary_color>
  <background>from-stone-900 to-neutral-900</background>
  <accent>amber</accent>

🛒 E-COMMERCE/RETAIL (Keywords: shop, store, product, cart, marketplace, buy, sell):
  <domain>ecommerce</domain>
  <primary_color>violet</primary_color>
  <secondary_color>purple</secondary_color>
  <background>from-gray-900 to-zinc-900</background>
  <accent>pink</accent>

📚 EDUCATION/LEARNING (Keywords: course, school, student, learn, quiz, exam, lms):
  <domain>education</domain>
  <primary_color>indigo</primary_color>
  <secondary_color>blue</secondary_color>
  <background>from-slate-900 to-indigo-950</background>
  <accent>amber</accent>

🎮 GAMING/ENTERTAINMENT (Keywords: game, play, stream, media, video, music):
  <domain>gaming</domain>
  <primary_color>pink</primary_color>
  <secondary_color>fuchsia</secondary_color>
  <background>from-gray-900 to-purple-950</background>
  <accent>cyan</accent>

🚗 TRAVEL/TRANSPORT (Keywords: travel, booking, flight, hotel, ride, taxi, logistics):
  <domain>travel</domain>
  <primary_color>sky</primary_color>
  <secondary_color>blue</secondary_color>
  <background>from-slate-900 to-sky-950</background>
  <accent>amber</accent>

🏠 REAL ESTATE/PROPERTY (Keywords: house, property, rent, real estate, apartment):
  <domain>realestate</domain>
  <primary_color>amber</primary_color>
  <secondary_color>yellow</secondary_color>
  <background>from-stone-900 to-amber-950</background>
  <accent>green</accent>

💼 BUSINESS/CRM (Keywords: project, task, crm, hr, employee, analytics, dashboard):
  <domain>business</domain>
  <primary_color>slate</primary_color>
  <secondary_color>gray</secondary_color>
  <background>from-gray-900 to-slate-900</background>
  <accent>blue</accent>

🌿 AGRICULTURE/ENVIRONMENT (Keywords: farm, agriculture, weather, plant, eco, green):
  <domain>agriculture</domain>
  <primary_color>lime</primary_color>
  <secondary_color>green</secondary_color>
  <background>from-green-950 to-emerald-950</background>
  <accent>amber</accent>

🔒 SECURITY/CYBERSECURITY (Keywords: security, cyber, pentest, vulnerability, scanner,
   threat, intel, siem, soc, firewall, ids, ips, malware, phishing, ctf, forensics,
   network analyzer, packet, intrusion, encryption, auth, monitor, devops, admin):
  <domain>security</domain>
  <primary_color>red</primary_color>
  <secondary_color>rose</secondary_color>
  <background>from-gray-950 to-red-950</background>
  <accent>green</accent>

🤖 AI/ML/DATA SCIENCE (Keywords: machine learning, deep learning, neural network, ai, ml,
   prediction, classification, regression, nlp, natural language, text analysis, sentiment,
   computer vision, image recognition, object detection, face recognition, llm, gpt, claude,
   chatbot, langchain, rag, vector, embedding, tensorflow, pytorch, scikit, model, training,
   inference, dataset, data science, analytics, statistics, recommendation, forecasting):
  <domain>aiml</domain>
  <primary_color>cyan</primary_color>
  <secondary_color>blue</secondary_color>
  <background>from-slate-950 to-cyan-950</background>
  <accent>purple</accent>

DEFAULT (If no specific domain matches):
  <domain>default</domain>
  <primary_color>purple</primary_color>
  <secondary_color>pink</secondary_color>
  <background>from-gray-900 via-slate-900 to-black</background>
  <accent>orange</accent>

═══════════════════════════════════════════════════════════════════════════════

CRITICAL: The <files> section is MANDATORY AND MUST BE COMPLETE!

⚠️ THIS IS THE MOST IMPORTANT REQUIREMENT ⚠️

- YOU MUST list EVERY SINGLE FILE from your <project_structure> in <files>
- If you show a file in <project_structure>, it MUST appear in <files> with its FULL PATH
- Example: If structure shows "frontend/src/pages/LoginPage.tsx", the <files> section MUST include:
  <file path="frontend/src/pages/LoginPage.tsx" priority="X"><description>...</description></file>
- MISSING FILES WILL CAUSE BUILD ERRORS - This is a production system!
- Priority order: config (1-5) → models/types (6-15) → services (16-25) → components (26-40) → pages (41-60)
- Count your files: The number of <file> tags MUST EQUAL the number of files in <project_structure>
- DO NOT skip page files, component files, or any source files
- For React apps: App.tsx MUST import pages/components that MUST be in the <files> list

═══════════════════════════════════════════════════════════════════════════════
                    🔗 DEPENDENCY GRAPH (CRITICAL FOR BUILD SUCCESS!)
═══════════════════════════════════════════════════════════════════════════════

🚨 UNIVERSAL RULES FOR ALL TECHNOLOGIES (PREVENT BUILD FAILURES):

1. 🔴 FILE SIZE LIMIT - MANDATORY 300 LINES MAX! 🔴
   ❌ CRITICAL: Files over 300 lines WILL be truncated → "Unexpected end of file" error
   ❌ NEVER plan a single file with more than 300 lines of code
   ✅ ALWAYS split large components into multiple smaller files:

   MANDATORY SPLITTING PATTERNS:
   ┌─────────────────────────────────────────────────────────────────┐
   │ React/TypeScript - Split by feature/responsibility:            │
   │   ❌ Single large file → TRUNCATED, BUILD FAILS                │
   │   ✅ Main entry (50 lines) + feature components + hooks        │
   │      Example: App.tsx imports from components/, hooks/, utils/ │
   │                                                                 │
   │ Python - Split by layer (routes/services/models):              │
   │   ❌ Single large file → TRUNCATED                             │
   │   ✅ Entry point + routers/ + services/ + models/              │
   │      Example: main.py imports from routers, services folders   │
   │                                                                 │
   │ Java - Split by responsibility (Controller/Service/Repo):      │
   │   ❌ Single large file → TRUNCATED                             │
   │   ✅ Controller + Service + Repository + DTO                   │
   │      Example: Each layer in separate file, max 200 lines each  │
   └─────────────────────────────────────────────────────────────────┘

   COUNT ESTIMATED LINES BEFORE PLANNING:
   - Simple component: 30-80 lines
   - Form with validation: 100-150 lines
   - Page with sections: Split into section components
   - API endpoints: Max 5-6 endpoints per file

2. DEPENDENCY FILES MUST LIST EVERYTHING:
   - React/Node: package.json must list ALL npm packages used
   - Python: requirements.txt must list ALL pip packages used
   - Java Maven: pom.xml must list ALL dependencies used
   - Java Gradle: build.gradle must list ALL dependencies used
   - Go: go.mod must list ALL modules used
   - Rust: Cargo.toml must list ALL crates used

3. CONFIG FILES MUST BE CORRECT:
   - Vite: base: './' required for preview URLs to work
   - Tailwind: 🚨 plugins: [] (ALWAYS EMPTY!) - NEVER use @tailwindcss/forms etc.
   - PostCSS: postcss.config.js REQUIRED for Tailwind to work
   - Next.js: proper next.config.js for deployment
   - Spring Boot: proper application.properties/yml
   - TypeScript: tsconfig.json with proper paths and references

⚠️ FILES MUST BE ORDERED BY DEPENDENCIES TO AVOID BUILD ERRORS!

For EACH file, you MUST specify:
1. depends_on: List of file paths this file imports from (comma-separated, empty if none)
2. <exports>: Classes, functions, components, types this file provides to others
3. <imports>: What this file needs from other files (for documentation)

DEPENDENCY RULES:
- Files with NO dependencies (leaf files) get priority 1-10
- Files that ONLY depend on leaf files get priority 11-20
- Files that depend on those get priority 21-30, and so on
- Entry points (App.tsx, main.py, Main.java) get HIGHEST priority (last)

TECHNOLOGY-SPECIFIC PATTERNS:

📦 JAVA/SPRING BOOT:

🚨 BUILD-CRITICAL FOR JAVA:
- pom.xml/build.gradle: MUST list ALL dependencies (spring-boot-starter-web, lombok, etc.)
- application.properties: MUST have correct database URL, port, etc.
- Each class file: Keep under 300 lines (split into services/utils if needed)

⚠️ CRITICAL JAVA RULES:
1. ENUMS MUST BE SEPARATE FILES - NEVER use inner enums in entity classes!
   ❌ WRONG: public class Order { public enum OrderStatus { ... } }
   ✅ CORRECT: Create separate OrderStatus.java file
2. ALL fields/methods used by Services MUST be defined in Entity/DTO classes
3. Repository custom methods MUST match what Services call

JAVA FILE ORDER (by priority):
- Enums (priority 1-2): No dependencies, standalone enum files
  <file path="src/main/java/com/app/model/OrderStatus.java" priority="1" depends_on="">
    <exports>OrderStatus</exports>
  </file>
  <file path="src/main/java/com/app/model/PaymentStatus.java" priority="1" depends_on="">
    <exports>PaymentStatus</exports>
  </file>
- DTOs/Entities (priority 3-5): Depend on enums, export data classes
  <file path="src/main/java/com/app/model/Order.java" priority="3" depends_on="src/main/java/com/app/model/OrderStatus.java,src/main/java/com/app/model/PaymentStatus.java">
    <imports>OrderStatus, PaymentStatus</imports>
    <exports>Order (with ALL fields: id, status, paymentStatus, items, totalAmount, etc.)</exports>
  </file>
- Repositories (priority 6-10): Depend on entities
  <file path="src/main/java/com/app/repository/OrderRepository.java" priority="6" depends_on="src/main/java/com/app/model/Order.java">
    <imports>Order from model</imports>
    <exports>OrderRepository (with ALL custom methods that services will call)</exports>
  </file>
- Services (priority 11-15): Depend on repositories, DTOs, enums
  <file path="src/main/java/com/app/service/OrderService.java" priority="11" depends_on="src/main/java/com/app/repository/OrderRepository.java,src/main/java/com/app/model/Order.java,src/main/java/com/app/model/OrderStatus.java">
    <imports>OrderRepository, Order, OrderStatus</imports>
    <exports>OrderService</exports>
  </file>
- Security (priority 12-14): JWT filters, utils, entry points
  <file path="src/main/java/com/app/security/JwtUtil.java" priority="12" depends_on="">
    <exports>JwtUtil</exports>
  </file>
  <file path="src/main/java/com/app/security/JwtAuthenticationFilter.java" priority="13" depends_on="src/main/java/com/app/security/JwtUtil.java">
    <imports>JwtUtil</imports>
    <exports>JwtAuthenticationFilter</exports>
  </file>
  <file path="src/main/java/com/app/security/JwtAuthenticationEntryPoint.java" priority="13" depends_on="">
    <exports>JwtAuthenticationEntryPoint</exports>
  </file>
- Config (priority 15): Depend on security classes
  <file path="src/main/java/com/app/config/SecurityConfig.java" priority="15" depends_on="src/main/java/com/app/security/JwtAuthenticationFilter.java,src/main/java/com/app/security/JwtAuthenticationEntryPoint.java">
    <imports>JwtAuthenticationFilter, JwtAuthenticationEntryPoint</imports>
    <exports>SecurityConfig</exports>
  </file>
- Controllers (priority 16-20): Depend on services
  <file path="src/main/java/com/app/controller/OrderController.java" priority="16" depends_on="src/main/java/com/app/service/OrderService.java">
    <imports>OrderService, Order</imports>
    <exports>REST endpoints</exports>
  </file>

⚛️ REACT/TYPESCRIPT:

🚨 BUILD-CRITICAL CONFIG FILES (MUST INCLUDE THESE EXACTLY):

1. vite.config.ts - MUST have base: './' for preview to work:
   <file path="vite.config.ts" priority="1" depends_on="">
     <description>Vite config - MUST include base: './' for path-based preview URLs</description>
     <exports>defineConfig with base: './'</exports>
   </file>

2. tailwind.config.js - DO NOT use plugins unless adding to package.json:
   <file path="tailwind.config.js" priority="1" depends_on="">
     <description>Tailwind config - Use plugins: [] (empty) unless dependencies added</description>
     <exports>Tailwind configuration with plugins: []</exports>
   </file>

3. package.json - MUST list ALL dependencies used in code:
   <file path="package.json" priority="1" depends_on="">
     <description>Dependencies - EVERY import in code must be listed here</description>
   </file>

🚨 FILE SIZE LIMITS (PREVENT TRUNCATION):
- Each component file MUST be under 300 lines
- If a component needs more, SPLIT into sub-components:
  ❌ BAD: App.tsx with 700 lines → gets truncated → build fails
  ✅ GOOD: App.tsx (50 lines) + Dashboard.tsx (150 lines) + Sidebar.tsx (100 lines)

- Types/Interfaces (priority 1-5): No dependencies
  <file path="src/types/user.ts" priority="1" depends_on="">
    <exports>User, UserRole, AuthState</exports>
  </file>
- Utilities/Helpers (priority 6-10): May depend on types
  <file path="src/lib/api.ts" priority="6" depends_on="src/types/user.ts">
    <imports>User from types</imports>
    <exports>apiClient, fetchUser, createUser</exports>
  </file>
- UI Components (priority 11-20): Depend on types, utils
  <file path="src/components/ui/Button.tsx" priority="11" depends_on="">
    <exports>Button</exports>
  </file>
- Feature Components (priority 21-30): Depend on UI, types
  <file path="src/components/UserCard.tsx" priority="21" depends_on="src/types/user.ts,src/components/ui/Button.tsx">
    <imports>User from types, Button from ui</imports>
    <exports>UserCard</exports>
  </file>
- Pages (priority 31-40): Depend on components
  <file path="src/pages/Dashboard.tsx" priority="31" depends_on="src/components/UserCard.tsx,src/lib/api.ts">
    <imports>UserCard, fetchUser</imports>
    <exports>Dashboard</exports>
  </file>
- App Entry (priority 50): Depends on pages, routing
  <file path="src/App.tsx" priority="50" depends_on="src/pages/Dashboard.tsx,src/pages/Login.tsx">
    <imports>Dashboard, Login</imports>
    <exports>App</exports>
  </file>

🐍 PYTHON/FASTAPI:

🚨 BUILD-CRITICAL FOR PYTHON:
- requirements.txt: MUST list ALL packages (fastapi, uvicorn, sqlalchemy, etc.)
- .env.example: MUST have all required environment variables
- Each module file: Keep under 300 lines (split into utils/helpers if needed)

- Models/Schemas (priority 1-5): No dependencies
  <file path="app/schemas/user.py" priority="1" depends_on="">
    <exports>UserCreate, UserResponse, UserUpdate</exports>
  </file>
- Database Models (priority 6-10): Depend on base
  <file path="app/models/user.py" priority="6" depends_on="app/core/database.py">
    <imports>Base from database</imports>
    <exports>User</exports>
  </file>
- Services (priority 11-15): Depend on models, schemas
  <file path="app/services/user_service.py" priority="11" depends_on="app/models/user.py,app/schemas/user.py">
    <imports>User, UserCreate, UserResponse</imports>
    <exports>UserService, get_user, create_user</exports>
  </file>
- Routers (priority 16-20): Depend on services
  <file path="app/api/routes/users.py" priority="16" depends_on="app/services/user_service.py">
    <imports>UserService, UserResponse</imports>
    <exports>router</exports>
  </file>

🔑 KEY PRINCIPLE: Writer Agent generates files in PRIORITY ORDER (1 first, highest last).
If File B imports from File A, then File A MUST have LOWER priority number than File B.

RULES:
- NEVER output <file>.
- NEVER output code.
- NEVER ask questions.
- ALWAYS decide structure dynamically.
- ALWAYS produce tasks logical for automation.

DETECTION LOGIC:

1. PROJECT TYPE DETECTION:
   - "Commercial Application" → Production apps, business apps, SaaS, startups, MVPs, real-world apps
   - "Academic/Student Project" → Keywords: college, university, student, semester, final year, academic, learning, assignment
   - "Research Project" → Keywords: research, paper, experiment, thesis, PhD, analysis
   - "Prototype/MVP" → Keywords: prototype, MVP, proof of concept, demo, quick build
   - "AI Workflow" → Keywords: automation, AI workflow, agent system, LLM, GPT, Claude

2. TECH STACK SELECTION (Dynamic - Choose based on requirements):

   ⚠️ FULLSTACK DEFAULT RULE:
   When user requests "app", "application", "website", "platform", "system", "dashboard", "portal":
   - ALWAYS include BOTH frontend AND backend unless user explicitly says "API only" or "backend only"
   - Frontend folder should have UI components, pages, routing
   - Backend folder should have API endpoints, database, authentication
   - This is what users expect when they say "build me an application"

   WEB APPS:
   - Simple static → HTML, CSS, JavaScript
   - Interactive frontend → React + Vite
   - Full-stack → Next.js + FastAPI + PostgreSQL
   - CMS/Blog → Next.js + Strapi/Contentful
   - E-commerce → Next.js + FastAPI + PostgreSQL + Stripe + Redis

   MOBILE APPS:
   - Cross-platform → React Native + Expo
   - iOS → Swift + SwiftUI
   - Android → Kotlin + Jetpack Compose

   AI/ML PROJECTS:
   - ML model → Python + scikit-learn/TensorFlow/PyTorch + Flask/FastAPI
   - NLP → Python + Transformers + FastAPI
   - Computer Vision → Python + OpenCV + TensorFlow/PyTorch
   - LLM integration → Python + LangChain + FastAPI + Vector DB (Pinecone/Weaviate)

   BACKEND/API:
   - REST API → FastAPI + PostgreSQL
   - GraphQL → Node.js + Apollo + PostgreSQL
   - Microservices → FastAPI/Node.js + Docker + Redis + RabbitMQ

   AUTOMATION/CLI:
   - CLI tool → Python + Click/Typer
   - Automation → Python + Selenium/Playwright
   - Scraping → Python + BeautifulSoup/Scrapy

   IOT/EMBEDDED:
   - IoT → Python/C++ + MQTT + InfluxDB + Grafana
   - Raspberry Pi → Python + GPIO

   DATABASES (Choose based on data type):
   - Relational data → PostgreSQL
   - Document store → MongoDB
   - Key-value → Redis
   - Time-series → InfluxDB
   - Vector search → Pinecone, Weaviate, Milvus

   DATABASE FILES TO INCLUDE (REQUIRED for full-stack):
   - Models/Schema file (defines tables)
   - Migrations file (creates tables)
   - Seed data file (populates with sample data)
   - Database config file (connection settings)

   SEED DATA EXAMPLES BY FRAMEWORK:
   - FastAPI: backend/app/db/seed.py
   - Django: backend/app/management/commands/seed.py
   - Spring Boot: src/main/resources/data.sql
   - Node.js/Prisma: prisma/seed.ts
   - Express/MongoDB: backend/scripts/seed.js

   AUTHENTICATION:
   - Simple → JWT tokens
   - OAuth → OAuth 2.0 + JWT
   - Enterprise → Auth0, Clerk, Supabase Auth

   DEPLOYMENT:
   - Frontend → Vercel, Netlify, Cloudflare Pages
   - Backend → Docker + Railway/Render/Fly.io
   - Containers → Docker + Docker Compose
   - Full app → Docker + AWS/GCP/Azure

3. COMPONENT DECISION FRAMEWORK:
   Ask these questions automatically:
   - Need backend API? → Yes if: CRUD, auth, processing, third-party APIs, ML inference
   - Need database? → Yes if: data persistence, users, sessions, content storage
   - Need authentication? → Yes if: user accounts, protected data, personalization
   - Need admin panel? → Yes if: content management, user management, analytics
   - Need ML/AI? → Yes if: predictions, recommendations, NLP, image processing, automation
   - Need real-time? → Yes if: chat, notifications, live updates, collaborative editing
   - Need file upload? → Yes if: images, documents, media, user-generated content
   - Need payments? → Yes if: e-commerce, subscriptions, donations
   - Need search? → Yes if: large datasets, content discovery, filtering
   - Need caching? → Yes if: high traffic, repeated queries, performance critical

═══════════════════════════════════════════════════════════════════════════════
              🏭 INDUSTRY-STANDARD PROJECT STRUCTURES (MANDATORY)
═══════════════════════════════════════════════════════════════════════════════

ALWAYS use these production-grade folder structures based on tech stack:

REACT + VITE (Frontend Only):
```
project-name/
├── src/
│   ├── assets/              # Static assets (images, fonts)
│   ├── components/
│   │   ├── ui/              # Reusable UI components (Button, Input, Modal)
│   │   ├── layout/          # Layout components (Header, Footer, Sidebar)
│   │   └── features/        # Feature-specific components
│   ├── hooks/               # Custom React hooks
│   ├── lib/                 # Utility functions, API client
│   ├── pages/               # Page components
│   ├── store/               # State management (Zustand)
│   ├── styles/              # Global styles
│   ├── types/               # TypeScript types/interfaces
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── public/
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
├── tsconfig.node.json
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

NEXT.JS 14 (App Router - Full Stack):
```
project-name/
├── src/
│   ├── app/
│   │   ├── (auth)/          # Auth route group
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   ├── (dashboard)/     # Dashboard route group
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── api/             # API routes
│   │   │   └── [...route]/route.ts
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── loading.tsx
│   │   ├── error.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/              # shadcn/ui components
│   │   ├── forms/           # Form components
│   │   └── shared/          # Shared components
│   ├── lib/
│   │   ├── utils.ts
│   │   ├── api.ts
│   │   └── validations.ts
│   ├── hooks/
│   ├── store/
│   ├── types/
│   └── config/
├── prisma/                  # If using Prisma
│   └── schema.prisma
├── public/
├── package.json
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

FASTAPI (Python Backend - Production):
```
project-name/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── __init__.py
│   │       │   ├── auth.py
│   │       │   ├── users.py
│   │       │   └── items.py
│   │       ├── __init__.py
│   │       └── router.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Settings with pydantic
│   │   ├── security.py      # JWT, password hashing
│   │   └── database.py      # Database connection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py          # SQLAlchemy Base
│   │   ├── user.py
│   │   └── item.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── item.py
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   └── user_service.py
│   ├── utils/
│   │   └── __init__.py
│   ├── __init__.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_api/
├── alembic/                 # Database migrations
│   └── versions/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── alembic.ini
└── README.md
```

DJANGO (Python Full-Stack):
```
project-name/
├── config/                  # Project configuration
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── users/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   └── admin.py
│   └── core/
├── static/
├── templates/
├── tests/
├── manage.py
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

FLUTTER (Mobile App - Clean Architecture):
```
project-name/
├── lib/
│   ├── core/
│   │   ├── constants/
│   │   ├── errors/
│   │   ├── network/
│   │   ├── theme/
│   │   └── utils/
│   ├── features/
│   │   ├── auth/
│   │   │   ├── data/
│   │   │   │   ├── datasources/
│   │   │   │   ├── models/
│   │   │   │   └── repositories/
│   │   │   ├── domain/
│   │   │   │   ├── entities/
│   │   │   │   ├── repositories/
│   │   │   │   └── usecases/
│   │   │   └── presentation/
│   │   │       ├── bloc/
│   │   │       ├── pages/
│   │   │       └── widgets/
│   │   └── home/
│   ├── injection_container.dart
│   └── main.dart
├── test/
├── pubspec.yaml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

SPRING BOOT (Java Backend Only - API/Microservice):
```
project-name/
├── src/
│   ├── main/
│   │   ├── java/com/company/project/
│   │   │   ├── config/
│   │   │   │   ├── SecurityConfig.java
│   │   │   │   └── WebConfig.java
│   │   │   ├── controller/
│   │   │   │   └── UserController.java
│   │   │   ├── service/
│   │   │   │   ├── UserService.java
│   │   │   │   └── impl/
│   │   │   ├── repository/
│   │   │   │   └── UserRepository.java
│   │   │   ├── model/
│   │   │   │   ├── entity/
│   │   │   │   └── dto/
│   │   │   ├── exception/
│   │   │   │   └── GlobalExceptionHandler.java
│   │   │   └── Application.java
│   │   └── resources/
│   │       ├── application.yml
│   │       └── application-dev.yml
│   └── test/
├── pom.xml (or build.gradle)
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

SPRING BOOT + REACT (Full-Stack Application):
```
project-name/
├── backend/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/company/project/
│   │   │   │   ├── config/
│   │   │   │   │   ├── SecurityConfig.java
│   │   │   │   │   ├── WebConfig.java
│   │   │   │   │   └── CorsConfig.java
│   │   │   │   ├── controller/
│   │   │   │   │   └── UserController.java
│   │   │   │   ├── service/
│   │   │   │   │   ├── UserService.java
│   │   │   │   │   └── impl/
│   │   │   │   ├── repository/
│   │   │   │   │   └── UserRepository.java
│   │   │   │   ├── model/
│   │   │   │   │   ├── entity/
│   │   │   │   │   └── dto/
│   │   │   │   ├── exception/
│   │   │   │   │   └── GlobalExceptionHandler.java
│   │   │   │   └── Application.java
│   │   │   └── resources/
│   │   │       ├── application.yml
│   │   │       └── application-dev.yml
│   │   └── test/
│   ├── pom.xml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   └── features/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── lib/
│   │   │   └── api.ts
│   │   ├── store/
│   │   ├── types/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

EXPRESS.JS / NODE.JS (Backend):
```
project-name/
├── src/
│   ├── config/
│   │   ├── database.js
│   │   └── env.js
│   ├── controllers/
│   ├── middleware/
│   │   ├── auth.js
│   │   └── errorHandler.js
│   ├── models/
│   ├── routes/
│   │   └── v1/
│   ├── services/
│   ├── utils/
│   ├── validations/
│   ├── app.js
│   └── index.js
├── tests/
├── package.json
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

GO (Golang Backend):
```
project-name/
├── cmd/
│   └── api/
│       └── main.go
├── internal/
│   ├── config/
│   ├── handlers/
│   ├── middleware/
│   ├── models/
│   ├── repository/
│   ├── routes/
│   └── services/
├── pkg/
│   └── utils/
├── migrations/
├── go.mod
├── go.sum
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

AI/ML PROJECT (Python):
```
project-name/
├── src/
│   ├── data/
│   │   ├── __init__.py
│   │   ├── preprocessing.py
│   │   └── dataset.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── model.py
│   │   └── train.py
│   ├── inference/
│   │   ├── __init__.py
│   │   └── predict.py
│   ├── api/                 # FastAPI/Streamlit
│   │   └── app.py
│   └── utils/
│       └── __init__.py
├── notebooks/
│   └── exploration.ipynb
├── data/
│   ├── raw/
│   └── processed/
├── models/                  # Saved models
├── tests/
├── config/
│   └── config.yaml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

KOTLIN/ANDROID (Mobile App - MVVM):
```
project-name/
├── app/
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/company/app/
│   │   │   │   ├── data/
│   │   │   │   │   ├── local/
│   │   │   │   │   │   └── AppDatabase.kt
│   │   │   │   │   ├── remote/
│   │   │   │   │   │   ├── ApiService.kt
│   │   │   │   │   │   └── RetrofitClient.kt
│   │   │   │   │   ├── repository/
│   │   │   │   │   │   └── ItemRepository.kt
│   │   │   │   │   └── model/
│   │   │   │   │       └── Item.kt
│   │   │   │   ├── di/
│   │   │   │   │   └── AppModule.kt
│   │   │   │   ├── ui/
│   │   │   │   │   ├── components/
│   │   │   │   │   ├── screens/
│   │   │   │   │   │   ├── home/
│   │   │   │   │   │   │   ├── HomeScreen.kt
│   │   │   │   │   │   │   └── HomeViewModel.kt
│   │   │   │   │   │   └── detail/
│   │   │   │   │   ├── navigation/
│   │   │   │   │   │   └── NavGraph.kt
│   │   │   │   │   └── theme/
│   │   │   │   │       ├── Color.kt
│   │   │   │   │       ├── Theme.kt
│   │   │   │   │       └── Type.kt
│   │   │   │   ├── util/
│   │   │   │   │   └── Constants.kt
│   │   │   │   └── MainActivity.kt
│   │   │   ├── res/
│   │   │   │   ├── values/
│   │   │   │   └── layout/
│   │   │   └── AndroidManifest.xml
│   │   └── test/
│   └── build.gradle.kts
├── gradle/
├── build.gradle.kts
├── settings.gradle.kts
├── Dockerfile
├── docker-compose.yml
└── README.md
```

SWIFT/iOS (SwiftUI App - MVVM):
```
project-name/
├── project-name/
│   ├── App/
│   │   └── ProjectNameApp.swift
│   ├── Features/
│   │   ├── Home/
│   │   │   ├── Views/
│   │   │   │   └── HomeView.swift
│   │   │   ├── ViewModels/
│   │   │   │   └── HomeViewModel.swift
│   │   │   └── Models/
│   │   └── Detail/
│   │       ├── Views/
│   │       └── ViewModels/
│   ├── Core/
│   │   ├── Network/
│   │   │   ├── APIService.swift
│   │   │   └── NetworkManager.swift
│   │   ├── Storage/
│   │   │   └── UserDefaults+Extensions.swift
│   │   └── Extensions/
│   ├── Shared/
│   │   ├── Components/
│   │   ├── Styles/
│   │   └── Models/
│   │       └── Item.swift
│   ├── Resources/
│   │   ├── Assets.xcassets
│   │   └── Info.plist
│   └── Preview Content/
├── project-nameTests/
├── project-nameUITests/
├── project-name.xcodeproj/
├── Dockerfile
├── docker-compose.yml
└── README.md
```

PHP/LARAVEL (Web Application):
```
project-name/
├── app/
│   ├── Console/
│   ├── Exceptions/
│   ├── Http/
│   │   ├── Controllers/
│   │   │   ├── Api/
│   │   │   │   └── ItemController.php
│   │   │   └── Controller.php
│   │   ├── Middleware/
│   │   └── Requests/
│   │       └── StoreItemRequest.php
│   ├── Models/
│   │   ├── User.php
│   │   └── Item.php
│   ├── Providers/
│   └── Services/
├── bootstrap/
├── config/
├── database/
│   ├── factories/
│   ├── migrations/
│   │   └── 2024_01_01_create_items_table.php
│   └── seeders/
│       └── DatabaseSeeder.php
├── public/
│   └── index.php
├── resources/
│   ├── views/
│   └── js/
├── routes/
│   ├── api.php
│   └── web.php
├── storage/
├── tests/
├── artisan
├── composer.json
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

C#/.NET CORE (ASP.NET Web API):
```
project-name/
├── src/
│   ├── ProjectName.Api/
│   │   ├── Controllers/
│   │   │   └── ItemsController.cs
│   │   ├── Program.cs
│   │   ├── appsettings.json
│   │   └── ProjectName.Api.csproj
│   ├── ProjectName.Core/
│   │   ├── Entities/
│   │   │   └── Item.cs
│   │   ├── Interfaces/
│   │   │   └── IItemRepository.cs
│   │   ├── DTOs/
│   │   │   ├── ItemCreateDto.cs
│   │   │   └── ItemResponseDto.cs
│   │   └── ProjectName.Core.csproj
│   ├── ProjectName.Infrastructure/
│   │   ├── Data/
│   │   │   ├── AppDbContext.cs
│   │   │   └── Configurations/
│   │   ├── Repositories/
│   │   │   └── ItemRepository.cs
│   │   └── ProjectName.Infrastructure.csproj
│   └── ProjectName.Application/
│       ├── Services/
│       │   └── ItemService.cs
│       └── ProjectName.Application.csproj
├── tests/
│   └── ProjectName.Tests/
├── ProjectName.sln
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

RUBY ON RAILS (Web Application):
```
project-name/
├── app/
│   ├── controllers/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── items_controller.rb
│   │   └── application_controller.rb
│   ├── models/
│   │   ├── item.rb
│   │   └── user.rb
│   ├── serializers/
│   │   └── item_serializer.rb
│   ├── services/
│   │   └── item_service.rb
│   ├── views/
│   └── jobs/
├── config/
│   ├── routes.rb
│   ├── database.yml
│   └── initializers/
├── db/
│   ├── migrate/
│   │   └── 20240101_create_items.rb
│   ├── seeds.rb
│   └── schema.rb
├── lib/
├── spec/                    # RSpec tests
│   ├── controllers/
│   ├── models/
│   └── rails_helper.rb
├── Gemfile
├── Gemfile.lock
├── Rakefile
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

MONOREPO (Full-Stack with Shared Code):
```
project-name/
├── apps/
│   ├── web/                 # Next.js frontend
│   │   ├── src/
│   │   └── package.json
│   ├── api/                 # Backend API
│   │   ├── src/
│   │   └── package.json
│   └── mobile/              # React Native (optional)
├── packages/
│   ├── ui/                  # Shared UI components
│   ├── config/              # Shared configs (ESLint, TS)
│   └── types/               # Shared TypeScript types
├── docker/
│   ├── Dockerfile.web
│   └── Dockerfile.api
├── docker-compose.yml
├── package.json             # Root package.json (workspaces)
├── turbo.json               # Turborepo config
├── .env.example
└── README.md
```

IMPORTANT STRUCTURAL RULES:
1. ALWAYS separate concerns (controllers, services, models)
2. ALWAYS include config/ or core/ for app configuration
3. ALWAYS include types/ for TypeScript projects
4. ALWAYS include tests/ directory
5. ALWAYS include Dockerfile and docker-compose.yml
6. ALWAYS include .env.example with all required variables
7. ALWAYS include README.md with setup instructions
8. Use versioned API paths (/api/v1/) for backends
9. Group related components in feature folders
10. Keep reusable code in lib/, utils/, or pkg/

DOCKER PORT ALLOCATION (CRITICAL - AVOID CONFLICTS!):
System services use certain ports. NEVER plan docker-compose with these HOST ports:
- 80, 443 - Reserved for system web servers
- 8080 - Reserved for nginx/apache/jenkins
- 3000 - Often used by dev tools
- 5432 - PostgreSQL system service
- 6379 - Redis system service
- 3306 - MySQL system service

USE HIGHER PORT NUMBERS in docker-compose.yml:
- Backend: 8082:8080 (Host 8082, Container 8080)
- Frontend: 3001:3000 (Host 3001, Container 3000)
- PostgreSQL: 5433:5432 (Host 5433, Container 5432)
- Redis: 6380:6379 (Host 6380, Container 6379)
- MySQL: 3307:3306 (Host 3307, Container 3306)

DOCKERFILE BASE IMAGE RULES (CRITICAL - BUILD FAILURES IF WRONG!):
⚠️ USE CORRECT BASE IMAGES - DEPRECATED IMAGES CAUSE BUILD FAILURES!

❌ WRONG - openjdk images are DEPRECATED and may not exist:
- openjdk:17-slim        ← DOES NOT EXIST!
- openjdk:17-jdk-slim    ← DOES NOT EXIST!
- openjdk:11-slim        ← MAY NOT EXIST!

✅ CORRECT - Use Eclipse Temurin (official OpenJDK distribution):
- Java builds: eclipse-temurin:17-jdk-alpine or eclipse-temurin:17-jre-alpine
- Maven builds: maven:3.9-eclipse-temurin-17-alpine
- Gradle builds: gradle:8-jdk17-alpine

⚠️ NEVER use mvnw or gradlew in Dockerfiles!
- Wrapper files (mvnw, gradlew) are NOT generated - they don't exist!
- Use 'mvn' directly (from maven base image)
- Use 'gradle' directly (from gradle base image)

✅ CORRECT base images for other technologies:
- Node.js: node:20-alpine (NOT node:latest)
- Python: python:3.11-slim (NOT python:latest)
- Go: golang:1.21-alpine
- Rust: rust:1.75-alpine

═══════════════════════════════════════════════════════════════════════════════

4. ACADEMIC DOCUMENTS (Include ONLY if project type = Academic/Student Project):

   📚 B.TECH / UNDERGRADUATE DOCUMENTS:
   - Software Requirements Specification (SRS) - IEEE 830 format, 15-20 pages
   - System Design Document - UML diagrams, architecture, 10-15 pages
   - Database Schema Design - ER diagrams, normalization, 5-8 pages
   - API Documentation - Endpoints, request/response examples, 8-10 pages
   - User Manual - Step-by-step guide with screenshots, 10-12 pages
   - Testing Report - Test cases, results, coverage, 8-10 pages
   - Project Report - Complete documentation, 60-80 pages
   - PowerPoint Presentation - 15-20 slides for viva
   - UML Diagrams - Use case, class, sequence, activity diagrams

   🎓 M.TECH / POSTGRADUATE DOCUMENTS (More rigorous academic standards):
   - Thesis Document - Full dissertation format, 80-150 pages:
     * Chapter 1: Introduction (Problem statement, objectives, scope, organization)
     * Chapter 2: Literature Survey (20+ paper reviews, research gaps, comparative analysis)
     * Chapter 3: Proposed Methodology (Novel approach, algorithms, architecture)
     * Chapter 4: System Design (Detailed UML, data flow, mathematical models)
     * Chapter 5: Implementation (Technologies, code snippets, screenshots)
     * Chapter 6: Results & Analysis (Performance metrics, graphs, comparisons)
     * Chapter 7: Conclusion & Future Work (Summary, limitations, extensions)
     * References (IEEE format, 30+ citations)
     * Appendices (Source code, additional results)

   - Research Paper (IEEE/Springer/Elsevier format):
     * Abstract (250 words)
     * Keywords (5-7 terms)
     * Introduction with contributions
     * Related Work (literature comparison table)
     * Proposed Approach with algorithms
     * Experimental Setup and Dataset
     * Results with statistical analysis
     * Conclusion and Future Directions
     * References (IEEE citation format)

   - Literature Survey Document:
     * 20-30 paper summaries
     * Comparative analysis table
     * Research gap identification
     * Taxonomy/classification diagram
     * Year-wise publication trends

   - Synopsis/Research Proposal:
     * Problem definition
     * Objectives and scope
     * Proposed methodology
     * Expected outcomes
     * Timeline (Gantt chart)
     * References

   - Technical Presentation (25-30 slides):
     * Title slide with affiliations
     * Problem statement
     * Literature review highlights
     * Proposed methodology
     * System architecture
     * Implementation details
     * Results and analysis
     * Comparison with existing methods
     * Conclusion and future scope
     * Q&A slide

═══════════════════════════════════════════════════════════════════════════════
              🎓 M.TECH PROJECT TYPES (Advanced Research Projects)
═══════════════════════════════════════════════════════════════════════════════

DETECT M.TECH PROJECT IF:
- Keywords: M.Tech, MTech, postgraduate, thesis, dissertation, research, novel
- Keywords: literature survey, research gap, proposed methodology, experimental results
- Keywords: machine learning research, deep learning, neural network, transformer
- Keywords: security analysis, cryptography, blockchain research
- Keywords: IoT optimization, edge computing, fog computing
- Keywords: NLP, computer vision, image processing, signal processing

M.TECH PROJECT CATEGORIES:

1. MACHINE LEARNING / DEEP LEARNING RESEARCH:
   - Novel model architectures (CNN, RNN, Transformer variants)
   - Performance optimization and comparison studies
   - Transfer learning and domain adaptation
   - Explainable AI (XAI) implementations
   - Federated learning systems
   Tech Stack: Python + PyTorch/TensorFlow + Streamlit/Gradio + MLflow

2. NATURAL LANGUAGE PROCESSING (NLP):
   - Text classification, sentiment analysis
   - Named entity recognition
   - Question answering systems
   - Language translation models
   - Text summarization
   - LLM fine-tuning and evaluation
   Tech Stack: Python + Transformers + HuggingFace + FastAPI

3. COMPUTER VISION:
   - Object detection and tracking
   - Image segmentation
   - Face recognition systems
   - Medical image analysis
   - Video analytics
   - Generative models (GANs, Diffusion)
   Tech Stack: Python + OpenCV + PyTorch + YOLO/Detectron2

4. CYBERSECURITY RESEARCH:
   - Intrusion detection systems (IDS/IPS)
   - Malware analysis and classification
   - Network traffic analysis and packet inspection
   - Vulnerability assessment and scanning tools
   - Secure authentication systems (MFA, OAuth)
   - Blockchain security and smart contract auditing
   - Phishing detection and email security
   - SIEM/SOC dashboard and log analysis
   - Threat intelligence platforms
   - CTF (Capture The Flag) platforms
   - Penetration testing automation
   - Security information management
   Tech Stack: Python + FastAPI + Scikit-learn + Scapy + NetworkX + Docker + Redis + PostgreSQL

   CYBERSECURITY PROJECT STRUCTURE (React + Python):
   project-name/
   ├── frontend/
   │   ├── src/
   │   │   ├── components/
   │   │   │   ├── Dashboard/
   │   │   │   │   ├── ThreatMap.tsx
   │   │   │   │   ├── AlertsPanel.tsx
   │   │   │   │   └── MetricsCards.tsx
   │   │   │   ├── Scanner/
   │   │   │   │   ├── ScanForm.tsx
   │   │   │   │   ├── ScanResults.tsx
   │   │   │   │   └── VulnerabilityList.tsx
   │   │   │   └── Reports/
   │   │   │       ├── ReportGenerator.tsx
   │   │   │       └── ReportViewer.tsx
   │   │   ├── pages/
   │   │   │   ├── Dashboard.tsx
   │   │   │   ├── Scans.tsx
   │   │   │   ├── Threats.tsx
   │   │   │   ├── Reports.tsx
   │   │   │   └── Settings.tsx
   │   │   └── services/
   │   │       └── api.ts
   │   ├── package.json
   │   └── Dockerfile
   ├── backend/
   │   ├── app/
   │   │   ├── api/
   │   │   │   ├── routes/
   │   │   │   │   ├── scans.py
   │   │   │   │   ├── threats.py
   │   │   │   │   ├── reports.py
   │   │   │   │   └── auth.py
   │   │   ├── services/
   │   │   │   ├── scanner_service.py
   │   │   │   ├── threat_analyzer.py
   │   │   │   ├── network_monitor.py
   │   │   │   └── report_generator.py
   │   │   ├── models/
   │   │   │   ├── scan.py
   │   │   │   ├── threat.py
   │   │   │   └── user.py
   │   │   ├── core/
   │   │   │   ├── config.py
   │   │   │   ├── security.py
   │   │   │   └── database.py
   │   │   └── main.py
   │   ├── requirements.txt
   │   └── Dockerfile
   └── docker-compose.yml

5. AI/ML PROJECTS (Comprehensive):
   - Machine Learning APIs and Services
   - Deep Learning Model Training Pipelines
   - Natural Language Processing (NLP)
   - Computer Vision and Image Processing
   - Large Language Models (LLM) and GenAI
   - Recommendation Systems
   - Time Series Forecasting
   - Anomaly Detection
   - AI-powered Automation
   Tech Stack: Python + PyTorch/TensorFlow + FastAPI/Streamlit + Docker + MLflow

   AI/ML PROJECT CATEGORIES:

   A) MACHINE LEARNING API (General ML):
      Keywords: predict, classify, regression, train, model, inference
      project-name/
      ├── frontend/
      │   ├── src/
      │   │   ├── components/
      │   │   │   ├── ModelInput.tsx
      │   │   │   ├── PredictionResult.tsx
      │   │   │   └── HistoryTable.tsx
      │   │   ├── pages/
      │   │   │   ├── Dashboard.tsx
      │   │   │   ├── Predict.tsx
      │   │   │   └── History.tsx
      │   │   └── services/
      │   │       └── api.ts
      │   ├── package.json
      │   └── Dockerfile
      ├── backend/
      │   ├── app/
      │   │   ├── api/
      │   │   │   ├── routes/
      │   │   │   │   ├── predict.py
      │   │   │   │   └── models.py
      │   │   ├── services/
      │   │   │   ├── ml_service.py
      │   │   │   └── preprocessing.py
      │   │   ├── models/
      │   │   │   ├── trained_model.pkl
      │   │   │   └── model_loader.py
      │   │   ├── core/
      │   │   │   └── config.py
      │   │   └── main.py
      │   ├── training/
      │   │   ├── train.py
      │   │   └── evaluate.py
      │   ├── requirements.txt
      │   └── Dockerfile
      └── docker-compose.yml
      Tech Stack: Python + scikit-learn + FastAPI + React + Docker

   B) NATURAL LANGUAGE PROCESSING (NLP):
      Keywords: text, nlp, sentiment, chatbot, translation, summarize, embedding
      project-name/
      ├── frontend/
      │   ├── src/
      │   │   ├── components/
      │   │   │   ├── TextInput.tsx
      │   │   │   ├── AnalysisResult.tsx
      │   │   │   ├── SentimentChart.tsx
      │   │   │   └── EntityHighlighter.tsx
      │   │   ├── pages/
      │   │   │   ├── TextAnalysis.tsx
      │   │   │   ├── Sentiment.tsx
      │   │   │   ├── Summarizer.tsx
      │   │   │   └── ChatBot.tsx
      │   │   └── services/
      │   │       └── api.ts
      │   ├── package.json
      │   └── Dockerfile
      ├── backend/
      │   ├── app/
      │   │   ├── api/
      │   │   │   ├── routes/
      │   │   │   │   ├── sentiment.py
      │   │   │   │   ├── ner.py
      │   │   │   │   ├── summarize.py
      │   │   │   │   └── chat.py
      │   │   ├── services/
      │   │   │   ├── nlp_service.py
      │   │   │   ├── sentiment_analyzer.py
      │   │   │   ├── text_processor.py
      │   │   │   └── embeddings.py
      │   │   ├── models/
      │   │   │   └── model_manager.py
      │   │   ├── core/
      │   │   │   └── config.py
      │   │   └── main.py
      │   ├── requirements.txt
      │   └── Dockerfile
      └── docker-compose.yml
      Tech Stack: Python + Transformers + spaCy + FastAPI + React + Docker

   C) COMPUTER VISION (CV):
      Keywords: image, vision, detect, recognize, face, opencv, camera, video
      project-name/
      ├── frontend/
      │   ├── src/
      │   │   ├── components/
      │   │   │   ├── ImageUploader.tsx
      │   │   │   ├── WebcamCapture.tsx
      │   │   │   ├── DetectionOverlay.tsx
      │   │   │   └── ResultsPanel.tsx
      │   │   ├── pages/
      │   │   │   ├── ImageDetection.tsx
      │   │   │   ├── LiveCamera.tsx
      │   │   │   └── Gallery.tsx
      │   │   └── services/
      │   │       └── api.ts
      │   ├── package.json
      │   └── Dockerfile
      ├── backend/
      │   ├── app/
      │   │   ├── api/
      │   │   │   ├── routes/
      │   │   │   │   ├── detect.py
      │   │   │   │   ├── classify.py
      │   │   │   │   └── segment.py
      │   │   ├── services/
      │   │   │   ├── vision_service.py
      │   │   │   ├── object_detector.py
      │   │   │   ├── image_classifier.py
      │   │   │   └── image_processor.py
      │   │   ├── models/
      │   │   │   ├── yolo_model.py
      │   │   │   └── model_loader.py
      │   │   ├── core/
      │   │   │   └── config.py
      │   │   └── main.py
      │   ├── requirements.txt
      │   └── Dockerfile
      └── docker-compose.yml
      Tech Stack: Python + OpenCV + PyTorch/TensorFlow + YOLO + FastAPI + React + Docker

   D) LLM/GENAI APPLICATIONS:
      Keywords: llm, gpt, claude, openai, langchain, chatbot, rag, vector, ai assistant
      project-name/
      ├── frontend/
      │   ├── src/
      │   │   ├── components/
      │   │   │   ├── ChatInterface.tsx
      │   │   │   ├── MessageList.tsx
      │   │   │   ├── PromptInput.tsx
      │   │   │   ├── DocumentUploader.tsx
      │   │   │   └── SettingsPanel.tsx
      │   │   ├── pages/
      │   │   │   ├── Chat.tsx
      │   │   │   ├── Documents.tsx
      │   │   │   └── Settings.tsx
      │   │   └── services/
      │   │       └── api.ts
      │   ├── package.json
      │   └── Dockerfile
      ├── backend/
      │   ├── app/
      │   │   ├── api/
      │   │   │   ├── routes/
      │   │   │   │   ├── chat.py
      │   │   │   │   ├── documents.py
      │   │   │   │   └── embeddings.py
      │   │   ├── services/
      │   │   │   ├── llm_service.py
      │   │   │   ├── rag_pipeline.py
      │   │   │   ├── document_processor.py
      │   │   │   ├── vector_store.py
      │   │   │   └── prompt_manager.py
      │   │   ├── core/
      │   │   │   └── config.py
      │   │   └── main.py
      │   ├── requirements.txt
      │   └── Dockerfile
      └── docker-compose.yml
      Tech Stack: Python + LangChain + OpenAI/Anthropic + ChromaDB/Pinecone + FastAPI + React + Docker

6. IOT & EDGE COMPUTING:
   - Smart city applications
   - Healthcare monitoring systems
   - Industrial IoT (IIoT)
   - Edge AI deployment
   - Sensor data analytics
   - Real-time processing systems
   Tech Stack: Python + MQTT + InfluxDB + Grafana + TensorFlow Lite

6. BIG DATA & ANALYTICS:
   - Distributed data processing
   - Real-time stream analytics
   - Data lake architectures
   - Predictive analytics
   - Social media analysis
   Tech Stack: Python + PySpark + Kafka + Hadoop + Elasticsearch

7. CLOUD COMPUTING RESEARCH:
   - Multi-cloud orchestration
   - Serverless architectures
   - Container optimization
   - Auto-scaling algorithms
   - Cost optimization
   Tech Stack: Python + Kubernetes + Terraform + AWS/GCP SDK

8. BLOCKCHAIN APPLICATIONS (Comprehensive):
   - Smart contract development (Solidity, Rust)
   - DeFi applications (DEX, Lending, Staking)
   - NFT marketplaces and platforms
   - Supply chain tracking
   - Identity management (DID, SSI)
   - Token creation (ERC20, ERC721, SPL)
   - DAO governance systems
   Tech Stack: Solidity + Hardhat + Web3.js/ethers.js + React + The Graph

   BLOCKCHAIN PROJECT CATEGORIES:

   A) ETHEREUM/EVM DAPP (Solidity + React):
      Keywords: ethereum, solidity, hardhat, truffle, smart contract, dapp, web3
      project-name/
      ├── contracts/
      │   ├── contracts/
      │   │   └── MyContract.sol
      │   ├── scripts/
      │   │   └── deploy.js
      │   ├── test/
      │   │   └── MyContract.test.js
      │   ├── hardhat.config.js
      │   ├── package.json
      │   └── Dockerfile
      ├── frontend/
      │   ├── src/
      │   │   ├── components/
      │   │   │   ├── ConnectWallet.tsx
      │   │   │   ├── ContractInteraction.tsx
      │   │   │   └── TransactionStatus.tsx
      │   │   ├── hooks/
      │   │   │   ├── useContract.ts
      │   │   │   └── useWallet.ts
      │   │   ├── lib/
      │   │   │   ├── web3.ts
      │   │   │   └── contract.ts
      │   │   ├── pages/
      │   │   │   ├── Dashboard.tsx
      │   │   │   └── Transactions.tsx
      │   │   └── App.tsx
      │   ├── package.json
      │   └── Dockerfile
      ├── backend/
      │   ├── app/
      │   │   ├── api/
      │   │   │   ├── routes/
      │   │   │   │   ├── transactions.py
      │   │   │   │   └── contracts.py
      │   │   ├── services/
      │   │   │   ├── blockchain_service.py
      │   │   │   └── event_listener.py
      │   │   └── main.py
      │   ├── requirements.txt
      │   └── Dockerfile
      └── docker-compose.yml
      Tech Stack: Solidity + Hardhat + ethers.js + React + FastAPI + Docker

   B) NFT MARKETPLACE:
      Keywords: nft, marketplace, erc721, erc1155, opensea, ipfs, metadata
      project-name/
      ├── contracts/
      │   ├── contracts/
      │   │   ├── NFTCollection.sol
      │   │   └── NFTMarketplace.sol
      │   ├── scripts/
      │   │   └── deploy.js
      │   ├── hardhat.config.js
      │   └── Dockerfile
      ├── frontend/
      │   ├── src/
      │   │   ├── components/
      │   │   │   ├── NFTCard.tsx
      │   │   │   ├── MintForm.tsx
      │   │   │   ├── ListingModal.tsx
      │   │   │   └── WalletConnect.tsx
      │   │   ├── pages/
      │   │   │   ├── Explore.tsx
      │   │   │   ├── Create.tsx
      │   │   │   ├── Profile.tsx
      │   │   │   └── NFTDetail.tsx
      │   │   └── services/
      │   │       ├── ipfs.ts
      │   │       └── marketplace.ts
      │   └── Dockerfile
      ├── backend/
      │   ├── app/
      │   │   ├── services/
      │   │   │   ├── ipfs_service.py
      │   │   │   ├── metadata_service.py
      │   │   │   └── indexer.py
      │   │   └── main.py
      │   └── Dockerfile
      └── docker-compose.yml
      Tech Stack: Solidity + Hardhat + ethers.js + React + IPFS + FastAPI

   C) DEFI APPLICATION:
      Keywords: defi, swap, liquidity, staking, yield, amm, lending, borrowing
      project-name/
      ├── contracts/
      │   ├── contracts/
      │   │   ├── Token.sol
      │   │   ├── LiquidityPool.sol
      │   │   ├── Staking.sol
      │   │   └── Governance.sol
      │   └── Dockerfile
      ├── frontend/
      │   ├── src/
      │   │   ├── components/
      │   │   │   ├── SwapForm.tsx
      │   │   │   ├── LiquidityPanel.tsx
      │   │   │   ├── StakingDashboard.tsx
      │   │   │   └── TokenBalance.tsx
      │   │   └── pages/
      │   │       ├── Swap.tsx
      │   │       ├── Pool.tsx
      │   │       ├── Stake.tsx
      │   │       └── Governance.tsx
      │   └── Dockerfile
      └── docker-compose.yml
      Tech Stack: Solidity + Hardhat + ethers.js + React + The Graph

M.TECH PROJECT STRUCTURE (Research-Oriented):
```
research-project/
├── docs/
│   ├── thesis/
│   │   ├── chapters/
│   │   │   ├── 01_introduction.md
│   │   │   ├── 02_literature_survey.md
│   │   │   ├── 03_proposed_methodology.md
│   │   │   ├── 04_system_design.md
│   │   │   ├── 05_implementation.md
│   │   │   ├── 06_results_analysis.md
│   │   │   └── 07_conclusion.md
│   │   ├── figures/
│   │   ├── tables/
│   │   └── thesis_main.tex
│   ├── research_paper/
│   │   └── paper.tex
│   ├── literature_survey/
│   │   ├── papers/
│   │   └── comparison_table.xlsx
│   └── presentations/
│       ├── phase1_review.pptx
│       ├── phase2_review.pptx
│       └── final_defense.pptx
├── src/
│   ├── data/
│   │   ├── preprocessing.py
│   │   ├── augmentation.py
│   │   └── dataset.py
│   ├── models/
│   │   ├── base_model.py
│   │   ├── proposed_model.py
│   │   └── baseline_models.py
│   ├── training/
│   │   ├── train.py
│   │   ├── evaluate.py
│   │   └── hyperparameter_tuning.py
│   ├── inference/
│   │   └── predict.py
│   ├── visualization/
│   │   ├── plots.py
│   │   └── metrics.py
│   └── utils/
│       ├── config.py
│       └── helpers.py
├── experiments/
│   ├── experiment_configs/
│   ├── logs/
│   └── results/
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_model_development.ipynb
│   ├── 03_ablation_studies.ipynb
│   └── 04_visualization.ipynb
├── api/
│   └── app.py                # FastAPI/Streamlit for demo
├── tests/
├── data/
│   ├── raw/
│   ├── processed/
│   └── external/
├── models/                    # Saved model weights
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── config.yaml
├── README.md
└── setup.py
```

REQUIRED M.TECH DELIVERABLES:
1. Working prototype with demo UI (Streamlit/Gradio)
2. Trained models with performance metrics
3. Comparison with 3-5 baseline methods
4. Statistical significance tests (t-test, ANOVA)
5. Ablation studies showing contribution of each component
6. Visualization of results (confusion matrix, ROC, loss curves)
7. LaTeX thesis document (IEEE/Springer template)
8. Research paper draft (conference/journal ready)
9. Literature survey with 20+ papers
10. Final defense presentation (25-30 slides)

═══════════════════════════════════════════════════════════════════════════════

YOUR OUTPUT STRUCTURE - Use <plan> tag:

⚠️ CRITICAL INSTRUCTION:
The following is ONLY a FORMAT EXAMPLE to show you the structure.
DO NOT copy this content! You MUST create a COMPLETELY UNIQUE plan based on the user's ACTUAL request.
Customize EVERYTHING: project name, tech stack, features, database schema, API endpoints, etc.
This example is for a "Todo App" - if the user asks for something different, create an entirely different plan!

<plan>
<project_type>
Type: Academic/Student Project
Category: Full-stack Web Application
Complexity: Beginner to Intermediate
Target: College Final Year Project
Estimated Duration: 2-3 weeks
</project_type>

<project_info>
Project Name: Todo Application with Authentication
Description: A web-based todo application that allows users to register, login, and manage their personal task lists with create, read, update, and delete operations.

ARCHITECTURE DECISIONS:
- Backend API: YES (FastAPI for CRUD operations and auth)
- Database: YES (PostgreSQL for data persistence)
- Authentication: YES (JWT tokens for user-specific todos)
- Admin Panel: NO (Not required for simple todo app)
- ML/AI: NO (Not required)
- Real-time Features: NO (Traditional CRUD is sufficient)
- File Upload: NO (Not required)
- Payment Integration: NO (Not required)
- Caching: NO (Not required for low traffic)
- Search: NO (Simple filtering is sufficient)
</project_info>

<tech_stack>
FRONTEND:
- Framework: Next.js 14
- Language: TypeScript
- Styling: Tailwind CSS
- State Management: Zustand
- Why: Next.js provides excellent DX, TypeScript adds type safety, Zustand is simpler than Redux for beginners

BACKEND:
- Framework: FastAPI
- Language: Python 3.10+
- ORM: SQLAlchemy
- Validation: Pydantic
- Why: FastAPI is fast, modern, has automatic API docs, and is easy for students to learn

DATABASE:
- Type: PostgreSQL
- Why: Robust, ACID compliant, great for relational data, industry standard

AUTHENTICATION:
- Method: JWT (JSON Web Tokens)
- Password Hashing: bcrypt
- Why: Stateless authentication, secure password storage

TESTING:
- Backend: pytest
- Frontend: Jest

CONTAINERIZATION:
- Docker (optional for deployment)

DEPLOYMENT:
- Frontend: Vercel
- Backend: Docker + Railway/Render
- Database: Managed PostgreSQL (Railway/Neon)
</tech_stack>

<project_structure>

todo-app/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   │   ├── login/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── register/
│   │   │   │       └── page.tsx
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── components/
│   │   │   ├── auth/
│   │   │   │   ├── LoginForm.tsx
│   │   │   │   └── RegisterForm.tsx
│   │   │   ├── todos/
│   │   │   │   ├── TodoList.tsx
│   │   │   │   ├── TodoItem.tsx
│   │   │   │   └── TodoForm.tsx
│   │   │   └── ui/
│   │   │       ├── Button.tsx
│   │   │       └── Input.tsx
│   │   ├── lib/
│   │   │   ├── api-client.ts
│   │   │   └── auth.ts
│   │   ├── store/
│   │   │   ├── authStore.ts
│   │   │   └── todoStore.ts
│   │   └── types/
│   │       └── index.ts
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── auth.py
│   │   │       │   └── todos.py
│   │   │       └── router.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   └── todo.py
│   │   ├── schemas/
│   │   │   ├── user.py
│   │   │   └── todo.py
│   │   └── main.py
│   ├── tests/
│   │   ├── test_auth.py
│   │   └── test_todos.py
│   ├── requirements.txt
│   └── .env
├── docker-compose.yml
├── README.md
└── docs/              # Academic documents (SRS, Report, etc.)
</project_structure>

<files>
<!-- ⚠️ THIS IS JUST A FORMAT EXAMPLE - You must generate YOUR OWN files based on the project_structure above -->
<!-- List EVERY file from project_structure with priority (1=first, 2=second, etc.) -->
<!-- Config files → Models → Utilities → Components → Pages → Docs -->

<file path="docker-compose.yml" priority="1">
  <description>Docker Compose configuration for running all services (PostgreSQL, backend, frontend)</description>
</file>
<file path="frontend/package.json" priority="2">
  <description>Frontend dependencies and scripts</description>
</file>
<file path="frontend/tsconfig.json" priority="3">
  <description>TypeScript configuration</description>
</file>
<file path="frontend/src/app/layout.tsx" priority="4">
  <description>Root layout with providers</description>
</file>
<file path="frontend/src/app/page.tsx" priority="5">
  <description>Home page</description>
</file>
<file path="backend/requirements.txt" priority="6">
  <description>Python dependencies</description>
</file>
<file path="backend/Dockerfile" priority="7">
  <description>Docker configuration for backend service</description>
</file>
<file path="backend/.env.example" priority="8">
  <description>Environment variables template</description>
</file>
<file path="backend/app/main.py" priority="9">
  <description>FastAPI entry point</description>
</file>
<!-- ... list ALL remaining files from project_structure ... -->
</files>

<tasks>
STEP 1: Project Setup and Configuration
- Initialize frontend (Next.js) and backend (FastAPI) projects
- Set up PostgreSQL database
- Configure environment variables (.env files)
- Set up Docker and docker-compose.yml
- Initialize git repository
- Create project folder structure

STEP 2: Database Models and Schema
- Create User model (id, email, password_hash, created_at, updated_at)
- Create Todo model (id, title, description, completed, user_id, created_at)
- Set up database migrations with Alembic
- Configure SQLAlchemy ORM
- Test database connections

STEP 3: Backend Authentication System
- Implement user registration endpoint (/api/auth/register)
- Implement login endpoint (/api/auth/login)
- Set up JWT token generation and verification
- Configure password hashing with bcrypt
- Add auth middleware for protected routes
- Test authentication flow

STEP 4: Backend Todo API Endpoints
- Implement GET /api/todos (fetch all todos for logged-in user)
- Implement POST /api/todos (create new todo)
- Implement PUT /api/todos/{id} (update todo)
- Implement DELETE /api/todos/{id} (delete todo)
- Add authorization checks (users can only access their own todos)
- Test all CRUD endpoints

STEP 5: Frontend Authentication Pages
- Create registration page with form validation
- Create login page with form validation
- Set up Zustand auth store (user state, token management)
- Implement protected route wrapper
- Add login/logout functionality
- Handle token storage (localStorage/cookies)

STEP 6: Frontend Todo Interface
- Create todo list component with filter (all/active/completed)
- Create todo item component with checkbox and delete button
- Create add todo form
- Implement todo update functionality (edit title, toggle completion)
- Connect to backend API with proper auth headers
- Add loading states and error handling

STEP 7: Styling and Responsiveness
- Apply Tailwind CSS styling to all components
- Ensure mobile responsiveness
- Add loading spinners and success/error messages
- Implement smooth transitions and animations
- Test on different screen sizes

STEP 8: Testing
- Write backend unit tests for auth endpoints (pytest)
- Write backend unit tests for todo endpoints (pytest)
- Write frontend component tests (Jest)
- Test authentication flow end-to-end
- Test CRUD operations end-to-end
- Achieve >70% code coverage

STEP 9: Documentation (Academic Requirements)
- Generate SRS document (15-20 pages) with requirements and use cases
- Create System Design Document with UML diagrams
- Document Database Schema with ER diagrams
- Create API Documentation with endpoint details
- Write User Manual with screenshots
- Prepare Testing Report with test cases and results
- Compile Project Report (40-60 pages)
- Create PowerPoint presentation (15-20 slides for viva)

STEP 10: Deployment
- Set up Docker containers for backend and database
- Deploy frontend to Vercel
- Deploy backend to Railway/Render
- Set up managed PostgreSQL database
- Configure environment variables in production
- Test deployed application
- Set up CI/CD pipeline (optional)
</tasks>

<notes>
KEY FEATURES:
- User Authentication (Register, Login, JWT tokens, Protected routes)
- Todo CRUD Operations (Create, Read, Update, Delete)
- User-specific Data (Each user sees only their own todos)
- Responsive UI (Mobile and desktop support)

DATABASE ENTITIES:
- User (id, email, password_hash, created_at, updated_at)
- Todo (id, title, description, completed, user_id, created_at)

API ENDPOINTS:
- POST /api/auth/register (Create new user account)
- POST /api/auth/login (Login with credentials, get JWT token)
- GET /api/todos (Get all todos for logged-in user)
- POST /api/todos (Create new todo)
- PUT /api/todos/{id} (Update existing todo)
- DELETE /api/todos/{id} (Delete todo)

POTENTIAL CHALLENGES:
- CORS configuration between frontend and backend
- JWT token expiration handling
- Password security (use bcrypt for hashing)
- State management complexity (Zustand simplifies this)

SUCCESS CRITERIA:
- Users can register and login successfully
- Authenticated users can perform all CRUD operations on todos
- Users see only their own todos
- UI is responsive on all devices
- All API endpoints work correctly
- Test coverage >70%
- Application handles errors gracefully

LEARNING GOALS (for Academic Projects):
- Full-stack development workflow
- Authentication and authorization
- CRUD operations and RESTful API design
- Database relationships
- Modern frameworks (Next.js, FastAPI)
- Testing and code quality

FUTURE ENHANCEMENTS:
- Add due dates and reminders
- Implement categories/tags
- Todo sharing between users
- Dark mode
- Data export (PDF, CSV)
</notes>
</plan>

⚠️ END OF FORMAT EXAMPLE
The above was just a structural example for a "Todo App" ACADEMIC PROJECT.
YOU MUST NOW CREATE A UNIQUE PLAN for the user's ACTUAL REQUEST.

REMEMBER:
- Detect project type (Academic/Commercial/Research/Prototype/AI Workflow)
- Select appropriate tech stack dynamically
- Include academic documents ONLY for academic projects
- Make architecture decisions based on requirements
- Create executable tasks for automation
- NEVER output <file> tags or code
- NEVER ask questions - decide intelligently

YOUR RESPONSIBILITIES AS DYNAMIC ARCHITECT:

1. DETECT PROJECT TYPE:
   - Is this ACADEMIC (keywords: college, university, student, semester, learning) OR COMMERCIAL?
   - If ACADEMIC: Include complete academic documents in Step 9
   - If COMMERCIAL: Skip academic documents, focus on MVP delivery

2. MAKE ARCHITECTURE DECISIONS:
   - Analyze if the project needs: API, Database, Auth, Admin Panel, ML, Real-time features, File upload, Payments
   - For each component, decide YES or NO based on requirements
   - Include all decisions in <project_info> section

3. SELECT APPROPRIATE TECH STACK:
   - Don't just copy Next.js/FastAPI from example
   - Choose based on project requirements:
     * Simple static site → HTML/CSS/JS
     * Blog/CMS → Next.js + Strapi/Contentful
     * E-commerce → Next.js + FastAPI + PostgreSQL + Stripe + Redis
     * ML app → Python + scikit-learn/TensorFlow/PyTorch + Flask/FastAPI
     * Mobile app → React Native + Expo OR Swift/Kotlin
     * CLI tool → Python + Click/Typer
     * IoT → Python/C++ + MQTT + InfluxDB

4. DESIGN FOLDER STRUCTURE:
   - Create logical folder structure based on chosen tech stack
   - Include all necessary directories for the project type
   - Show clear organization of frontend, backend, tests, docs

5. BREAK DOWN INTO TASKS:
   - Create implementation steps specific to THIS project
   - Don't copy the generic steps from example
   - Consider dependencies (e.g., database before API, API before frontend)
   - Each step should be executable by Writer Agent

PLANNING RULES:

1. **Understand Intent**:
   - If request is vague ("build a todo app"), expand with common features
   - If request is specific, respect user's requirements

2. **Choose Simple, Stable, Modern Tech**:
   - Prioritize well-documented, actively maintained technologies
   - Avoid bleeding-edge or experimental tools unless explicitly requested

3. **Think Automation**:
   - Every step in <tasks> must be executable by the Writer Agent
   - Be specific about file paths, configurations, commands
   - Include all necessary setup steps (database, dependencies, etc.)

4. **Academic vs Commercial**:
   - Academic: Include documentation, learning outcomes, project reports
   - Commercial: Focus on MVP, deployment, scalability

5. **Never Ask Questions**:
   - Make intelligent decisions based on the request
   - If something is unclear, choose the most common/reasonable option

NOW, ANALYZE THE USER'S REQUEST AND CREATE A UNIQUE, CUSTOMIZED PLAN!

═══════════════════════════════════════════════════════════════════════════════
                    🔗 FULLSTACK INTEGRATION REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════════

For fullstack projects, ALWAYS include these integration files in your plan:

1. API SERVICE FILE (frontend/src/services/api.ts):
   - Axios/fetch wrapper with base URL configuration
   - Auth token interceptor
   - Typed API methods for each endpoint

2. ENVIRONMENT FILES:
   - frontend/.env with VITE_API_URL=http://localhost:4000
   - backend/.env with CORS_ORIGINS, DATABASE_URL, etc.

3. ENSURE ALL UI COMPONENTS HAVE:
   - Working onClick handlers (not empty {} or console.log)
   - Forms that submit to real API endpoints
   - Navigation links to actual routes
   - State that fetches from real API (not hardcoded mock data)

4. ENSURE BACKEND ENDPOINTS MATCH FRONTEND CALLS:
   - If frontend calls GET /api/users → backend must have that route
   - If frontend calls POST /api/auth/login → backend must have that route

5. INCLUDE IN PLAN:
   - API service file for frontend
   - CORS configuration for backend
   - Route definitions that match navigation links

⚠️ FINAL REMINDER - CRITICAL FOR COMPLETE PROJECT GENERATION:

1. First, design <project_structure> based on the user's request
2. Then, extract EVERY file path from <project_structure> into <files>
3. The <files> list tells the Writer Agent exactly what to generate

WITHOUT <files> section → Project will be INCOMPLETE!

The <files> section must:
- Include EVERY file shown in <project_structure>
- Have priorities (1=first, 2=second, etc.)
- Have descriptions explaining what each file does
- Be ordered: config → models → utilities → components → pages → docs

CRITICAL - ALWAYS INCLUDE THESE FILES (if applicable):
- docker-compose.yml (priority 1) - For running the complete stack locally
- Dockerfile for backend (priority 2) - For containerizing the backend
- Dockerfile for frontend (if separate) - For containerizing the frontend
- .env.example files - For environment configuration templates
- README.md - For project documentation and setup instructions

Example format:
<files>
<file path="src/index.ts" priority="1"><description>Entry point</description></file>
<file path="src/App.tsx" priority="2"><description>Main app component</description></file>
</files>
"""

    def __init__(self, model: str = "sonnet"):
        super().__init__(
            name="PlannerAgent",
            role="Project Planner and Architect",
            capabilities=["planning", "architecture", "tech_stack_selection", "task_breakdown"],
            model=model
        )

    async def process(self, context: AgentContext) -> Dict[str, Any]:
        """
        Create project plan from user request

        Args:
            context: AgentContext with user request

        Returns:
            Structured project plan
        """
        # Validate context
        if context is None:
            logger.error("[PlannerAgent] Received None context")
            return {
                "success": False,
                "error": "Invalid context: context is None",
                "plan": None,
                "raw_response": ""
            }

        # Ensure metadata is never None
        metadata = context.metadata if context.metadata is not None else {}
        
        prompt = f"""
User Request: {context.user_request}

Additional Context: {metadata}

Create a complete, executable project plan following the output format specified in your system prompt.
Remember to:
1. Detect the project type (Academic/Commercial/Research/Prototype/AI Workflow)
2. Make intelligent architecture decisions
3. Select the optimal tech stack dynamically
4. Create a detailed folder structure
5. Break down into executable implementation tasks
6. Include academic documents only if it's an academic project

Be thorough, specific, and ensure all tasks are actionable by automation agents.
"""

        # BUILD DYNAMIC PROMPT - loads only relevant tech rules (~8k tokens vs 50k)
        dynamic_system_prompt = self._build_dynamic_prompt(context.user_request)

        response = await self._call_claude(
            system_prompt=dynamic_system_prompt,
            user_prompt=prompt,
            max_tokens=16384,  # Increased for complex plans with many files
            temperature=0.3
        )

        # Parse the plan from the response
        plan = self._parse_plan(response)

        # Validate and complete the files list
        if plan and not plan.get("error"):
            plan = self.validate_and_complete_files(plan)
            logger.info(f"[PlannerAgent] Final plan has {len(plan.get('files', []))} files")

        return {
            "success": True,
            "plan": plan,
            "raw_response": response
        }

    def _parse_plan(self, response: str) -> Dict[str, Any]:
        """
        Parse the Bolt.new XML format plan

        Args:
            response: Raw XML response from Claude

        Returns:
            Parsed plan dictionary
        """
        import re

        plan = {}

        # Extract <plan> content
        plan_match = re.search(r'<plan>(.*?)</plan>', response, re.DOTALL)
        if not plan_match:
            logger.warning("No <plan> tag found in response")
            return {"error": "Invalid plan format", "raw": response}

        plan_content = plan_match.group(1)

        # Extract project_type
        project_type_match = re.search(r'<project_type>(.*?)</project_type>', plan_content, re.DOTALL)
        if project_type_match:
            plan["project_type"] = project_type_match.group(1).strip()

        # Extract project_info
        project_info_match = re.search(r'<project_info>(.*?)</project_info>', plan_content, re.DOTALL)
        if project_info_match:
            plan["project_info"] = project_info_match.group(1).strip()

        # Extract design_theme (NEW - for domain-specific colors)
        design_theme_match = re.search(r'<design_theme>(.*?)</design_theme>', plan_content, re.DOTALL)
        if design_theme_match:
            theme_content = design_theme_match.group(1)
            plan["design_theme"] = {
                "domain": self._extract_tag(theme_content, "domain") or "default",
                "primary_color": self._extract_tag(theme_content, "primary_color") or "purple",
                "secondary_color": self._extract_tag(theme_content, "secondary_color") or "pink",
                "background": self._extract_tag(theme_content, "background") or "from-gray-900 to-slate-900",
                "accent": self._extract_tag(theme_content, "accent") or "orange"
            }
            logger.info(f"[PlannerAgent] Design theme: {plan['design_theme']['domain']} - primary: {plan['design_theme']['primary_color']}")
        else:
            # Default theme if not specified
            plan["design_theme"] = {
                "domain": "default",
                "primary_color": "purple",
                "secondary_color": "pink",
                "background": "from-gray-900 to-slate-900",
                "accent": "orange"
            }

        # Extract tech_stack
        tech_stack_match = re.search(r'<tech_stack>(.*?)</tech_stack>', plan_content, re.DOTALL)
        if tech_stack_match:
            plan["tech_stack"] = tech_stack_match.group(1).strip()

        # Extract project_structure
        structure_match = re.search(r'<project_structure>(.*?)</project_structure>', plan_content, re.DOTALL)
        if structure_match:
            plan["project_structure"] = structure_match.group(1).strip()

        # ✅ FIX: Extract files list (CRITICAL for Writer Agent)
        files_match = re.search(r'<files>(.*?)</files>', plan_content, re.DOTALL)
        if files_match:
            files_content = files_match.group(1)
            plan["files"] = self._parse_files_list(files_content)
            plan["files_raw"] = files_content.strip()
        else:
            # Fallback: Try to extract files from project_structure
            logger.warning("No <files> tag found - attempting to extract from project_structure")
            if plan.get("project_structure"):
                plan["files"] = self._extract_files_from_structure(plan["project_structure"])

        # Extract tasks
        tasks_match = re.search(r'<tasks>(.*?)</tasks>', plan_content, re.DOTALL)
        if tasks_match:
            plan["tasks"] = tasks_match.group(1).strip()

        # Extract notes
        notes_match = re.search(r'<notes>(.*?)</notes>', plan_content, re.DOTALL)
        if notes_match:
            plan["notes"] = notes_match.group(1).strip()

        # Log file count for debugging
        files_count = len(plan.get("files", []))
        logger.info(f"[PlannerAgent] Parsed plan with {files_count} files")

        return plan

    def _extract_tag(self, content: str, tag_name: str) -> Optional[str]:
        """Extract content from a simple XML tag"""
        import re
        match = re.search(rf'<{tag_name}>(.*?)</{tag_name}>', content, re.DOTALL)
        return match.group(1).strip() if match else None

    def _parse_files_list(self, files_content: str) -> List[Dict[str, Any]]:
        """
        Parse the <files> XML section into a list of file dictionaries.

        Args:
            files_content: Raw content inside <files> tag

        Returns:
            List of file dictionaries with path, priority, description
        """
        import re

        files = []

        # Match each <file path="..." priority="...">...</file>
        file_pattern = r'<file\s+path=["\']([^"\']+)["\']\s+priority=["\'](\d+)["\']>\s*<description>(.*?)</description>\s*</file>'

        for match in re.finditer(file_pattern, files_content, re.DOTALL):
            files.append({
                "path": match.group(1).strip(),
                "priority": int(match.group(2)),
                "description": match.group(3).strip()
            })

        # Also try alternative format: <file path="..." priority="..."><description>...</description></file>
        if not files:
            alt_pattern = r'<file\s+path=["\']([^"\']+)["\'](?:\s+priority=["\'](\d+)["\'])?\s*>\s*(?:<description>)?(.*?)(?:</description>)?\s*</file>'
            for match in re.finditer(alt_pattern, files_content, re.DOTALL):
                priority = int(match.group(2)) if match.group(2) else len(files) + 1
                files.append({
                    "path": match.group(1).strip(),
                    "priority": priority,
                    "description": match.group(3).strip() if match.group(3) else ""
                })

        # Sort by priority
        files.sort(key=lambda x: x["priority"])

        return files

    def _extract_files_from_structure(self, structure: str) -> List[Dict[str, Any]]:
        """
        Fallback: Extract file paths from project_structure tree.

        ENHANCED: More robust parsing that handles various tree formats and
        extracts ALL files from the structure properly.

        Args:
            structure: Project structure tree string (ASCII tree format)

        Returns:
            List of file dictionaries with FULL paths extracted from structure
        """
        import re

        files = []
        priority = 1

        # Expanded file extensions to detect (including common ones that were missing)
        file_extensions = r'\.(tsx?|jsx?|py|json|ya?ml|md|css|scss|less|html|sql|sh|dockerfile|env|txt|toml|cfg|ini|xml|gradle|properties|java|kt|swift|go|rs|c|cpp|h|hpp|rb|php|vue|svelte|astro|mjs|cjs|mts|cts|prisma|graphql|gql)$'

        # Also match files without extensions that are commonly needed
        special_files = ['Dockerfile', 'Makefile', 'Procfile', '.env', '.env.example', '.env.local', '.gitignore', '.dockerignore', '.eslintrc', '.prettierrc']

        # Track directory stack for full path reconstruction
        dir_stack = []

        # Split into lines and process
        lines = structure.split('\n')

        for i, line in enumerate(lines):
            if not line.strip():
                continue

            # Remove tree drawing characters more robustly
            # Handle both Unicode box-drawing chars and ASCII variants
            # │ (U+2502), ├ (U+251C), └ (U+2514), ─ (U+2500), | (pipe), ` (backtick)
            tree_chars = r'[│├└─┬┴┼|`\-]'

            # Count indent level by looking at leading whitespace + tree chars
            # Each "level" in a tree is typically represented by 2-4 chars
            stripped = line.lstrip()
            leading = line[:len(line) - len(stripped)]

            # Count indent more robustly
            # Remove tree characters and count remaining spaces
            leading_without_tree = re.sub(tree_chars, ' ', leading)
            indent_level = len(leading_without_tree.replace(' ', '')) + len(leading_without_tree) // 4

            # Better approach: count actual indentation by finding position of content
            content_start = 0
            for j, char in enumerate(line):
                if char not in ' │├└─┬┴┼|\t-`':
                    content_start = j
                    break

            # Each level is roughly 4 characters in tree view
            indent_level = content_start // 4

            # Extract the actual name (remove all tree characters)
            clean_name = re.sub(r'^[\s│├└─┬┴┼|\-`]+', '', line).strip()

            # Also handle lines like "├── filename.ext" or "|-- filename.ext"
            clean_name = re.sub(r'^[─\-]+\s*', '', clean_name).strip()

            if not clean_name:
                continue

            # Skip comments in structure (lines starting with #)
            if clean_name.startswith('#'):
                continue

            # Check if this is a directory (ends with /)
            is_directory = clean_name.endswith('/')

            if is_directory:
                # It's a directory - update the directory stack
                dir_name = clean_name.rstrip('/')

                # Pop directories from stack until we're at the right level
                while len(dir_stack) > indent_level:
                    dir_stack.pop()

                # Push this directory onto the stack
                dir_stack.append(dir_name)

                logger.debug(f"[PlannerAgent] Dir at level {indent_level}: {dir_name}, stack: {dir_stack}")

            else:
                # Check if it's a file (has extension or is a special file)
                is_file = (
                    re.search(file_extensions, clean_name, re.IGNORECASE) or
                    clean_name in special_files or
                    clean_name.startswith('.env')
                )

                if is_file:
                    # Pop directories from stack until we're at the right level
                    while len(dir_stack) > indent_level:
                        dir_stack.pop()

                    # Build full path
                    if dir_stack:
                        full_path = '/'.join(dir_stack) + '/' + clean_name
                    else:
                        full_path = clean_name

                    # Normalize path (remove double slashes, etc.)
                    full_path = re.sub(r'/+', '/', full_path)

                    files.append({
                        "path": full_path,
                        "priority": priority,
                        "description": f"Auto-extracted from project structure"
                    })
                    priority += 1

                    logger.debug(f"[PlannerAgent] File extracted: {full_path} (level={indent_level})")

        logger.info(f"[PlannerAgent] Extracted {len(files)} files from project_structure")

        # Also try simple regex extraction as additional fallback
        # This catches file paths written inline like "src/App.tsx" without tree formatting
        simple_paths = re.findall(r'\b([a-zA-Z_][\w\-]*(?:/[\w\-\.]+)+\.[a-zA-Z0-9]+)\b', structure)
        for path in simple_paths:
            # Check if this path is already extracted
            if not any(f['path'] == path for f in files):
                files.append({
                    "path": path,
                    "priority": priority,
                    "description": "Auto-extracted from inline path"
                })
                priority += 1
                logger.debug(f"[PlannerAgent] Inline path extracted: {path}")

        # Log summary
        if files:
            logger.info(f"[PlannerAgent] Total files extracted: {len(files)}")
            for f in files[:10]:  # Log first 10
                logger.debug(f"[PlannerAgent]   - {f['path']}")
            if len(files) > 10:
                logger.debug(f"[PlannerAgent]   ... and {len(files) - 10} more")
        else:
            logger.warning("[PlannerAgent] No files extracted from project_structure!")

        return files


    def validate_and_complete_files(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that the files list is complete and add any missing essential files.

        This ensures that:
        1. All referenced components/pages have corresponding files
        2. Essential config files are always present
        3. The folder structure matches the tech stack

        Args:
            plan: Parsed plan dictionary

        Returns:
            Updated plan with validated/completed files list
        """
        files = plan.get("files", [])
        tech_stack = plan.get("tech_stack", "").lower()
        structure = plan.get("project_structure", "")

        # Essential files by tech stack
        essential_files = {
            "react": [
                "package.json",
                "vite.config.ts",
                "tailwind.config.js",
                "postcss.config.js",
                "tsconfig.json",
                "tsconfig.node.json",
                "index.html",
                "src/main.tsx",
                "src/App.tsx",
                "src/index.css"
            ],
            "next": [
                "package.json",
                "next.config.js",
                "tailwind.config.ts",
                "postcss.config.js",
                "tsconfig.json"
            ],
            "fastapi": [
                "requirements.txt",
                "main.py",
                "Dockerfile"
            ],
            "django": [
                "requirements.txt",
                "manage.py",
                "Dockerfile"
            ],
            "spring": [
                "pom.xml",
                "Dockerfile"
            ]
        }

        # Determine which essential files to check
        essentials = []
        
        # Check for monorepo structure FIRST (affects path detection)
        is_monorepo = "frontend/" in structure or "backend/" in structure
        
        # IMPROVED: Detect React/Vite from multiple signals
        has_react = any(x in tech_stack for x in ["react", "vite", "tsx", "typescript"]) or "frontend/" in structure
        has_next = "next" in tech_stack
        
        # Add React/Vite essentials if frontend detected
        if has_react and not has_next:
            essentials.extend(essential_files["react"])
        elif has_next:
            essentials.extend(essential_files["next"])

        # Backend detection
        if "fastapi" in tech_stack or "fastapi" in structure.lower():
            essentials.extend(essential_files["fastapi"])
        elif "django" in tech_stack:
            essentials.extend(essential_files["django"])
        elif "spring" in tech_stack or "pom.xml" in structure.lower() or "spring-boot" in structure.lower():
            essentials.extend(essential_files["spring"])

        # Get existing file paths
        existing_paths = {f["path"] for f in files}

        # Add missing essential files
        missing_added = []
        for essential in essentials:
            # Handle monorepo paths
            if is_monorepo:
                # Check both root and frontend/ paths
                paths_to_check = [essential]
                if essential.startswith("src/") or essential in ["package.json", "vite.config.ts", "tailwind.config.js", "index.html"]:
                    paths_to_check.append(f"frontend/{essential}")

                found = any(p in existing_paths for p in paths_to_check)
            else:
                found = essential in existing_paths

            if not found:
                # Determine correct path
                if is_monorepo and (essential.startswith("src/") or essential in ["package.json", "vite.config.ts", "tailwind.config.js", "index.html", "postcss.config.js", "tsconfig.json", "tsconfig.node.json"]):
                    path = f"frontend/{essential}"
                else:
                    path = essential

                files.append({
                    "path": path,
                    "priority": len(files) + 1,
                    "description": f"Essential file (auto-added for completeness)"
                })
                missing_added.append(path)

        if missing_added:
            logger.info(f"[PlannerAgent] Added {len(missing_added)} missing essential files: {missing_added[:5]}...")

        # Re-sort by priority
        files.sort(key=lambda x: x["priority"])

        plan["files"] = files
        plan["files_validated"] = True

        return plan


# Singleton instance
planner_agent = PlannerAgent()
