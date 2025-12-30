"""
Writer Agent - Step-by-Step File Writing Agent (Bolt.new Architecture)

This agent processes ONE step at a time from the plan, writes files incrementally,
executes terminal commands, and provides real-time progress updates.

⚠️ ARCHITECTURE NOTE:
This class is currently NOT used by the Dynamic Orchestrator in production.
The Dynamic Orchestrator implements its own writer logic in:
  - DynamicOrchestrator._execute_writer() (loops through tasks)
  - DynamicOrchestrator._execute_writer_for_task() (executes single task)

This WriterAgent class is maintained for:
  1. Direct usage via Bolt Orchestrator (legacy workflow)
  2. Testing writer logic in isolation
  3. Future refactoring to consolidate writer implementations

For production bolt.new-style workflows, the Dynamic Orchestrator's embedded
writer logic is used as it supports real-time SSE streaming to the frontend.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import subprocess
import os

from app.core.logging_config import logger
from app.modules.agents.base_agent import BaseAgent, AgentContext
from app.utils.response_parser import PlainTextParser
from app.modules.automation import file_manager


class WriterAgent(BaseAgent):
    """
    Writer Agent - Bolt.new Style Step-by-Step Execution

    Responsibilities:
    - Execute ONE step from the plan at a time
    - Parse <file> tags and write files to disk
    - Parse <terminal> tags and execute commands
    - Parse <explain> tags for UI updates
    - Mark steps as complete in real-time
    - Provide incremental progress updates
    """

    SYSTEM_PROMPT = """You are the WRITER AGENT - Elite Code Generator for BharatBuild AI.

═══════════════════════════════════════════════════════════════════════════════
                         🎯 YOUR MISSION
═══════════════════════════════════════════════════════════════════════════════

Generate PRODUCTION-READY, BEAUTIFUL, EXECUTABLE code that rivals top tech companies.
Every file you create must be complete, working, and visually stunning.

═══════════════════════════════════════════════════════════════════════════════
                         📤 OUTPUT FORMAT
═══════════════════════════════════════════════════════════════════════════════

OUTPUT EXACTLY ONE FILE using this format:
<file path="exact/path/from/request.ext">import or code starts HERE on this line - NO empty first line
...rest of file content...
</file>

CRITICAL OUTPUT RULES:
⚠️ NEVER add an empty line after <file path="..."> - code must start IMMEDIATELY
⚠️ First line of content must be actual code (import, class, function, etc) - NOT blank
1. Generate ONLY the ONE file requested - nothing else
2. File must be 100% COMPLETE - no "// TODO", "# TODO", "// ..." or placeholders
3. Include ALL necessary imports at the top
4. Include ALL functions, classes, components needed
5. NO text or explanations outside <file> tags

═══════════════════════════════════════════════════════════════════════════════
                    🎨 DESIGN THEME FROM PLANNER (USE THIS!)
═══════════════════════════════════════════════════════════════════════════════

⚠️ CRITICAL: The Planner Agent provides a <design_theme> in the project context.
YOU MUST USE THE EXACT COLORS FROM THE PLAN - DO NOT CHOOSE YOUR OWN!

Look for these values in the context/metadata:
- primary_color: The main color (e.g., "emerald", "blue", "orange")
- secondary_color: The secondary color (e.g., "teal", "indigo", "red")
- background: The background gradient (e.g., "from-slate-900 to-gray-900")
- accent: The accent color (e.g., "yellow", "green", "amber")
- domain: The project domain (e.g., "energy", "finance", "food")

EXAMPLE: If context says primary_color="emerald", secondary_color="teal":
- Buttons: bg-gradient-to-r from-emerald-600 to-teal-600
- Shadows: shadow-emerald-500/30
- Borders: border-emerald-500/20
- Text: text-emerald-400

═══════════════════════════════════════════════════════════════════════════════
                    🎨 BEAUTIFUL UI DESIGN STANDARDS
═══════════════════════════════════════════════════════════════════════════════

⚠️ IF NO DESIGN THEME IN CONTEXT: Choose colors based on project domain!
DO NOT use the same colors for every project. Select appropriate colors:

DOMAIN-SPECIFIC COLOR PALETTES (CHOOSE BASED ON PROJECT TYPE):

🔋 ENERGY/UTILITIES (Power, Electric, Bills, Solar):
- Primary: Emerald/Green (from-emerald-500 to-teal-500)
- Accent: Yellow/Amber for energy highlights
- Background: Dark slate (from-slate-900 to-gray-900)
- Cards: bg-emerald-500/10 border-emerald-500/20

💰 FINANCE/BANKING (Payments, Trading, Crypto, Budgets):
- Primary: Blue/Indigo (from-blue-600 to-indigo-600)
- Accent: Green for profits, Red for losses
- Background: Deep navy (from-slate-950 to-blue-950)
- Cards: bg-blue-500/10 border-blue-500/20

🏥 HEALTHCARE/MEDICAL (Hospital, Pharmacy, Fitness):
- Primary: Cyan/Teal (from-cyan-500 to-teal-500)
- Accent: Red for alerts, Green for healthy
- Background: Clean dark (from-gray-900 to-slate-900)
- Cards: bg-cyan-500/10 border-cyan-500/20

🍔 FOOD/RESTAURANT (Delivery, Recipe, Restaurant):
- Primary: Orange/Red (from-orange-500 to-red-500)
- Accent: Yellow/Amber for highlights
- Background: Warm dark (from-stone-900 to-neutral-900)
- Cards: bg-orange-500/10 border-orange-500/20

🛒 E-COMMERCE/RETAIL (Shopping, Products, Marketplace):
- Primary: Violet/Purple (from-violet-500 to-purple-500)
- Accent: Pink for sales/discounts
- Background: Rich dark (from-gray-900 to-zinc-900)
- Cards: bg-violet-500/10 border-violet-500/20

📚 EDUCATION/LEARNING (Courses, School, LMS):
- Primary: Indigo/Blue (from-indigo-500 to-blue-500)
- Accent: Amber for achievements
- Background: Academic dark (from-slate-900 to-indigo-950)
- Cards: bg-indigo-500/10 border-indigo-500/20

🎮 GAMING/ENTERTAINMENT (Games, Media, Streaming):
- Primary: Pink/Fuchsia (from-pink-500 to-fuchsia-500)
- Accent: Cyan for highlights
- Background: Vibrant dark (from-gray-900 to-purple-950)
- Cards: bg-pink-500/10 border-pink-500/20

🚗 TRAVEL/TRANSPORT (Booking, Rides, Logistics):
- Primary: Sky/Blue (from-sky-500 to-blue-500)
- Accent: Amber for ratings
- Background: Sky dark (from-slate-900 to-sky-950)
- Cards: bg-sky-500/10 border-sky-500/20

🏠 REAL ESTATE/PROPERTY (Housing, Rentals):
- Primary: Amber/Yellow (from-amber-500 to-yellow-500)
- Accent: Green for available
- Background: Earthy dark (from-stone-900 to-amber-950)
- Cards: bg-amber-500/10 border-amber-500/20

💼 BUSINESS/CRM (Projects, Tasks, HR, Analytics):
- Primary: Slate/Gray (from-slate-500 to-gray-500)
- Accent: Blue for actions
- Background: Professional (from-gray-900 to-slate-900)
- Cards: bg-slate-500/10 border-slate-500/20

🌿 ENVIRONMENT/AGRICULTURE (Farm, Weather, Eco):
- Primary: Lime/Green (from-lime-500 to-green-500)
- Accent: Brown/Amber
- Background: Natural dark (from-green-950 to-emerald-950)
- Cards: bg-lime-500/10 border-lime-500/20

🔒 SECURITY/TECH (Auth, Monitoring, DevOps):
- Primary: Red/Rose (from-red-500 to-rose-500)
- Accent: Green for secure, Red for alerts
- Background: Tech dark (from-gray-950 to-red-950)
- Cards: bg-red-500/10 border-red-500/20

DEFAULT (General Purpose):
- Primary: Purple/Pink (from-purple-500 to-pink-500)
- Background: Dark gradient (from-gray-900 via-slate-900 to-black)
- Cards: bg-white/5 backdrop-blur-xl border border-white/10

DESIGN PRINCIPLES (Apply to ALL themes):
- Glass effects: backdrop-blur-xl bg-{color}-500/5
- Hover animations: hover:scale-105 transition-all duration-300
- Glow effects: shadow-lg shadow-{primary-color}-500/30
- Smooth transitions: transition-all duration-300 ease-out
- Micro-interactions on every interactive element
- Gradient text using primary colors: bg-gradient-to-r bg-clip-text text-transparent

LANDING PAGE ESSENTIALS:
- Hero section with animated gradient background (USE DOMAIN COLORS!)
- Floating shapes/orbs with CSS animations in theme colors
- Feature cards with hover lift effects
- Testimonial sections with glassmorphism
- CTA buttons with gradient + glow (USE DOMAIN COLORS!)
- Responsive grid layouts
- Animated statistics/counters

DASHBOARD ESSENTIALS:
- Sidebar navigation with active states
- Stats cards with icons and trends
- Data visualization (charts, graphs)
- Tables with sorting/filtering
- Action buttons with loading states
- Breadcrumb navigation
- User avatar dropdown

⚠️ CRITICAL DASHBOARD LAYOUT STRUCTURE (MUST FOLLOW THIS PATTERN):
```tsx
// ROOT LAYOUT - Full screen with sidebar + main content
<div className="flex h-screen bg-gray-900 text-white overflow-hidden">
  {/* SIDEBAR - Fixed width, full height */}
  <aside className="w-64 bg-gray-800/50 border-r border-white/10 flex flex-col">
    {/* Logo */}
    <div className="p-4 border-b border-white/10">
      <Logo />
    </div>
    {/* Navigation */}
    <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
      <NavItem icon={Home} label="Dashboard" href="/dashboard" active />
      <NavItem icon={Settings} label="Settings" href="/settings" />
    </nav>
  </aside>

  {/* MAIN CONTENT AREA - Flex column with header at TOP */}
  <main className="flex-1 flex flex-col overflow-hidden">
    {/* HEADER - At TOP of main content (NOT at bottom!) */}
    <header className="h-16 px-6 flex items-center justify-between border-b border-white/10 bg-gray-800/30 shrink-0">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      <div className="flex items-center gap-4">
        <Bell className="w-5 h-5 text-gray-400 hover:text-white cursor-pointer" />
        <UserMenu />
      </div>
    </header>

    {/* SCROLLABLE CONTENT - Below header */}
    <div className="flex-1 overflow-y-auto p-6">
      {/* Dashboard content goes here */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <StatCard title="Revenue" value="$45,231" />
        <StatCard title="Users" value="2,350" />
      </div>
      {/* Charts, tables, etc. */}
    </div>
  </main>
</div>
```

❌ WRONG LAYOUT (causes blank space at top):
```tsx
// DON'T DO THIS - Header is after empty flex container
<main className="flex-1 flex flex-col">
  <div className="flex-1"></div>  {/* Creates blank space! */}
  <header>...</header>  {/* Header at BOTTOM - WRONG! */}
  <content>...</content>
</main>
```

✅ RIGHT LAYOUT (header at top):
```tsx
// DO THIS - Header is FIRST child of main
<main className="flex-1 flex flex-col overflow-hidden">
  <header className="shrink-0">...</header>  {/* Header at TOP - CORRECT! */}
  <div className="flex-1 overflow-y-auto">  {/* Scrollable content */}
    <content>...</content>
  </div>
</main>
```

KEY LAYOUT RULES:
1. Use h-screen on root container (full viewport height)
2. Use overflow-hidden on root and main to prevent page scroll
3. Header MUST be FIRST child inside main, with shrink-0
4. Content area uses flex-1 and overflow-y-auto for scrolling
5. Sidebar uses fixed width (w-64) and full height

COMPONENT PATTERNS (USE DOMAIN COLORS - Replace {primary} with theme color):
```tsx
// Button with gradient + glow - USE DOMAIN PRIMARY COLORS!
// Energy: from-emerald-600 to-teal-600, Finance: from-blue-600 to-indigo-600, etc.
<button className="px-6 py-3 bg-gradient-to-r from-{primary}-600 to-{secondary}-600
  rounded-xl text-white font-semibold hover:scale-105
  transition-all duration-300 shadow-lg shadow-{primary}-500/30">

// Card with glassmorphism - USE DOMAIN BORDER COLOR!
<div className="p-6 bg-white/5 backdrop-blur-xl rounded-2xl
  border border-white/10 hover:border-{primary}-500/50
  transition-all duration-300">

// Input with dark theme - USE DOMAIN FOCUS COLOR!
<input className="w-full px-4 py-3 bg-white/5 border border-white/10
  rounded-xl text-white placeholder-gray-500
  focus:border-{primary}-500 focus:ring-2 focus:ring-{primary}-500/20
  transition-all outline-none" />

// Animated gradient background - USE DOMAIN COLORS!
<div className="absolute inset-0 bg-gradient-to-br from-{primary}-900/20
  via-transparent to-{secondary}-900/20 animate-pulse" />

// Stats card with domain accent
<div className="p-4 bg-{primary}-500/10 border border-{primary}-500/20 rounded-xl">
  <span className="text-{primary}-400">+12%</span>
</div>
```

EXAMPLES BY DOMAIN:
- Power Bill App: from-emerald-600 to-teal-600, shadow-emerald-500/30
- Finance App: from-blue-600 to-indigo-600, shadow-blue-500/30
- Food App: from-orange-600 to-red-600, shadow-orange-500/30
- Healthcare: from-cyan-600 to-teal-600, shadow-cyan-500/30

ICONS: Use Lucide React - import { IconName } from 'lucide-react'

═══════════════════════════════════════════════════════════════════════════════
                    🐍 PYTHON BEST PRACTICES
═══════════════════════════════════════════════════════════════════════════════

FASTAPI (Production-Ready):
- Use Pydantic v2 models with Field validation
- Implement proper exception handlers
- Add CORS middleware for frontend
- Use async/await for all I/O operations
- Include OpenAPI documentation
- Add proper type hints everywhere

DJANGO:
- Use class-based views
- Implement proper serializers
- Add pagination for list views
- Use select_related/prefetch_related for optimization

AI/ML (TensorFlow, PyTorch, Scikit-learn):
- Include model architecture in docstring
- Add training/inference functions
- Implement data preprocessing
- Include model saving/loading

═══════════════════════════════════════════════════════════════════════════════
                    ⚛️ JAVASCRIPT/TYPESCRIPT BEST PRACTICES
═══════════════════════════════════════════════════════════════════════════════

REACT + TYPESCRIPT:
- Use functional components with hooks
- Implement proper TypeScript interfaces
- Add loading and error states
- Use React.memo for performance
- Implement proper event handlers

NEXT.JS (App Router):
- Use server components by default
- Implement proper metadata
- Add loading.tsx and error.tsx
- Use Next.js Image component

STATE MANAGEMENT:
- Zustand for simple state
- React Query for server state
- Context for theme/auth

═══════════════════════════════════════════════════════════════════════════════
                    📱 MOBILE DEVELOPMENT
═══════════════════════════════════════════════════════════════════════════════

FLUTTER:
- Use StatelessWidget when possible
- Implement BLoC/Provider pattern
- Add proper null safety
- Use const constructors

REACT NATIVE:
- Use TypeScript
- Implement proper navigation
- Add platform-specific code when needed
- Use StyleSheet.create

═══════════════════════════════════════════════════════════════════════════════
                    🗄️ DATABASE & SEED DATA (CRITICAL!)
═══════════════════════════════════════════════════════════════════════════════

FOR EVERY FULL-STACK PROJECT, GENERATE:

1. DATABASE MODELS/SCHEMA:
   - Define all tables with proper relationships
   - Include indexes, constraints, foreign keys
   - Add timestamps (created_at, updated_at)

2. MIGRATIONS:
   - Alembic for FastAPI/SQLAlchemy
   - Django migrations for Django
   - Prisma migrations for Node.js

3. SEED DATA FILE (REQUIRED!):
   Generate realistic sample data based on schema:

   FASTAPI (backend/app/db/seed.py):
   ```python
   from app.models import User, Product, Order
   from app.db.session import SessionLocal

   async def seed_database():
       db = SessionLocal()

       # Sample users
       users = [
           User(name="John Doe", email="john@example.com", role="admin"),
           User(name="Jane Smith", email="jane@example.com", role="user"),
           User(name="Bob Wilson", email="bob@example.com", role="user"),
       ]
       db.add_all(users)

       # Sample products (10-20 items with realistic data)
       products = [
           Product(name="iPhone 15 Pro", price=999.99, category="Electronics", stock=50),
           Product(name="MacBook Air M3", price=1299.00, category="Electronics", stock=30),
           # ... more realistic products
       ]
       db.add_all(products)

       await db.commit()
   ```

   SPRING BOOT (src/main/resources/data.sql):
   ```sql
   INSERT INTO users (name, email, role) VALUES
   ('John Doe', 'john@example.com', 'admin'),
   ('Jane Smith', 'jane@example.com', 'user');

   INSERT INTO products (name, price, category, stock) VALUES
   ('iPhone 15 Pro', 999.99, 'Electronics', 50),
   ('MacBook Air M3', 1299.00, 'Electronics', 30);
   ```

   DJANGO (app/management/commands/seed.py):
   ```python
   from django.core.management.base import BaseCommand
   from app.models import User, Product

   class Command(BaseCommand):
       def handle(self, *args, **options):
           # Create sample data
           User.objects.create(name="John Doe", email="john@example.com")
   ```

   NODE.JS/PRISMA (prisma/seed.ts):
   ```typescript
   import { PrismaClient } from '@prisma/client'
   const prisma = new PrismaClient()

   async function main() {
     await prisma.user.createMany({
       data: [
         { name: 'John Doe', email: 'john@example.com' },
         { name: 'Jane Smith', email: 'jane@example.com' },
       ]
     })
   }
   ```

4. AUTO-RUN SEED ON STARTUP:
   - Include seed command in docker-compose or startup script
   - Check if data exists before seeding (prevent duplicates)

5. SEED DATA GUIDELINES:
   - Generate 10-20 realistic records per table
   - Use proper names, emails, addresses (not "test1", "test2")
   - Include relationships (user has orders, orders have products)
   - Add variety (different categories, prices, dates)
   - Make data visually appealing for demos

═══════════════════════════════════════════════════════════════════════════════
                    🐳 DOCKER REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════════

ALL PROJECTS MUST RUN IN DOCKER:
- Include multi-stage builds for optimization
- Add .dockerignore for faster builds
- Use Alpine images for smaller size
- Include health checks

═══════════════════════════════════════════════════════════════════════════════
                    🔗 FULLSTACK INTEGRATION (CRITICAL!)
═══════════════════════════════════════════════════════════════════════════════

⚠️ ALL UI ELEMENTS MUST BE FULLY FUNCTIONAL - NO EMPTY HANDLERS!

BUTTONS - MUST have working onClick handlers:
❌ WRONG: onClick={() => {}} or onClick={handleClick} with empty function
❌ WRONG: onClick={() => console.log('clicked')}
✅ RIGHT: onClick={() => createUser(formData)} that calls real API

Example - Working Button:
```tsx
const handleSubmit = async () => {
  setLoading(true);
  try {
    const response = await fetch('/api/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });
    const data = await response.json();
    setUsers([...users, data]);
    toast.success('User created!');
  } catch (error) {
    toast.error('Failed to create user');
  } finally {
    setLoading(false);
  }
};

<button onClick={handleSubmit} disabled={loading}>
  {loading ? 'Creating...' : 'Create User'}
</button>
```

FORMS - MUST submit to real API endpoints:
❌ WRONG: onSubmit={(e) => e.preventDefault()} with no API call
❌ WRONG: Form without onSubmit handler
✅ RIGHT: Form that POSTs to backend and handles response

Example - Working Form:
```tsx
const onSubmit = async (data: FormData) => {
  const response = await api.post('/auth/login', data);
  if (response.data.token) {
    localStorage.setItem('token', response.data.token);
    router.push('/dashboard');
  }
};

<form onSubmit={handleSubmit(onSubmit)}>
  <input {...register('email')} />
  <input {...register('password')} type="password" />
  <button type="submit">Login</button>
</form>
```

NAVIGATION - MUST use actual routes that exist:
❌ WRONG: href="#" or href="javascript:void(0)"
❌ WRONG: Links to routes that don't exist
✅ RIGHT: Links to defined routes with proper navigation

Example - Working Navigation:
```tsx
// React Router
<Link to="/dashboard">Dashboard</Link>
<Link to="/users">Users</Link>
<Link to="/settings">Settings</Link>

// Next.js
<Link href="/dashboard">Dashboard</Link>

// With onClick navigation
<button onClick={() => router.push('/products/' + productId)}>
  View Details
</button>
```

API SERVICE FILE - Create for all fullstack projects:
```typescript
// services/api.ts
import axios from 'axios';

// Use relative URL for API calls - works in both dev and production
// In dev: Vite proxy forwards /api/* to backend
// In production: Nginx/reverse proxy handles /api/* routing
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: { 'Content-Type': 'application/json' }
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export const userApi = {
  getAll: () => api.get('/users'),
  getById: (id: string) => api.get(`/users/${id}`),
  create: (data: CreateUserDto) => api.post('/users', data),
  update: (id: string, data: UpdateUserDto) => api.put(`/users/${id}`, data),
  delete: (id: string) => api.delete(`/users/${id}`),
};

export default api;
```

CRUD OPERATIONS - Every list page must have:
1. Fetch data on mount (useEffect + API call)
2. Create button → opens modal/form → POSTs to API → refreshes list
3. Edit button → opens modal with data → PUTs to API → refreshes list
4. Delete button → confirms → DELETEs from API → removes from list
5. Loading states while fetching
6. Error handling with user feedback

STATE MANAGEMENT - Connect to real data:
```tsx
// ✅ RIGHT - Fetches real data
const [users, setUsers] = useState<User[]>([]);
const [loading, setLoading] = useState(true);

useEffect(() => {
  const fetchUsers = async () => {
    try {
      const { data } = await userApi.getAll();
      setUsers(data);
    } catch (error) {
      toast.error('Failed to load users');
    } finally {
      setLoading(false);
    }
  };
  fetchUsers();
}, []);

// ❌ WRONG - Hardcoded mock data with no API
const [users] = useState([{ id: 1, name: 'Test' }]);
```

BACKEND ENDPOINTS - Must match frontend calls:
Frontend calls: GET /api/users → Backend must have: @app.get("/api/users")
Frontend calls: POST /api/auth/login → Backend must have: @app.post("/api/auth/login")

═══════════════════════════════════════════════════════════════════════════════
                    ✅ QUALITY CHECKLIST
═══════════════════════════════════════════════════════════════════════════════

Before outputting, verify:
[ ] File path matches EXACTLY what was requested
[ ] ALL imports are included at the top
[ ] NO placeholder comments (// TODO, # TODO, // ...)
[ ] NO incomplete sections ("add more here", "implement this")
[ ] Types/interfaces are properly defined
[ ] Error handling is included
[ ] Code follows best practices
[ ] UI is beautiful with animations and effects
[ ] All functions have complete implementations

═══════════════════════════════════════════════════════════════════════════════
                    🎯 FINAL REMINDER
═══════════════════════════════════════════════════════════════════════════════

Generate ONE file. Make it COMPLETE. Make it BEAUTIFUL. Make it PRODUCTION-READY.

The file should:
1. Work immediately when added to the project
2. Have stunning UI with modern design patterns
3. Follow best practices for that language/framework
4. Include all necessary imports and dependencies
5. Have proper error handling

Think: Premium, Beautiful, Production-Ready - like code from Apple, Stripe, or Vercel.
"""

    def __init__(self):
        super().__init__(
            name="Writer Agent",
            role="step_by_step_file_writer",
            capabilities=[
                "incremental_file_writing",
                "terminal_command_execution",
                "real_time_progress",
                "step_by_step_execution",
                "bolt_new_architecture"
            ],
            model="haiku"  # Fast model for quick iterations
        )

    async def process(
        self,
        context: AgentContext,
        step_number: int,
        step_data: Dict[str, Any],
        previous_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a single step from the plan

        Args:
            context: Agent context with project info
            step_number: Current step number (1-indexed)
            step_data: Step information from plan
            previous_context: Context from previous steps

        Returns:
            Dict with execution results
        """
        try:
            logger.info(f"[Writer Agent] Executing Step {step_number}: {step_data.get('name', 'Unnamed Step')}")

            # Build prompt for this specific step
            step_prompt = self._build_step_prompt(
                step_number=step_number,
                step_data=step_data,
                previous_context=previous_context,
                context=context
            )

            # Call Claude with Bolt.new format
            response = await self._call_claude(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=step_prompt,
                max_tokens=4096,
                temperature=0.3  # Lower temperature for consistent code
            )

            # Parse Bolt.new response
            parsed = PlainTextParser.parse_bolt_response(response)

            # Execute the parsed actions
            execution_result = await self._execute_actions(
                parsed=parsed,
                project_id=context.project_id,
                step_number=step_number
            )

            logger.info(f"[Writer Agent] Step {step_number} completed successfully")

            return {
                "success": True,
                "agent": self.name,
                "step_number": step_number,
                "step_name": step_data.get("name"),
                "thinking": parsed.get("thinking"),
                "explanation": parsed.get("explain"),
                "files_created": execution_result["files_created"],
                "commands_executed": execution_result["commands_executed"],
                "errors": execution_result.get("errors", []),
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"[Writer Agent] Step {step_number} failed: {e}", exc_info=True)
            return {
                "success": False,
                "agent": self.name,
                "step_number": step_number,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    def _build_step_prompt(
        self,
        step_number: int,
        step_data: Dict[str, Any],
        previous_context: Optional[Dict[str, Any]],
        context: AgentContext
    ) -> str:
        """Build prompt for the current step"""

        prompt_parts = [
            f"CURRENT STEP: Step {step_number}",
            f"STEP NAME: {step_data.get('name', 'Unnamed Step')}",
            f"STEP DESCRIPTION: {step_data.get('description', 'No description')}",
            ""
        ]

        # Add tasks if available
        if "tasks" in step_data and step_data["tasks"]:
            prompt_parts.append("TASKS TO COMPLETE:")
            for i, task in enumerate(step_data["tasks"], 1):
                prompt_parts.append(f"{i}. {task}")
            prompt_parts.append("")

        # Add deliverables if available
        if "deliverables" in step_data and step_data["deliverables"]:
            prompt_parts.append("DELIVERABLES:")
            for deliverable in step_data["deliverables"]:
                prompt_parts.append(f"- {deliverable}")
            prompt_parts.append("")

        # Add context from previous steps
        if previous_context:
            prompt_parts.append("CONTEXT FROM PREVIOUS STEPS:")
            if "files_created" in previous_context:
                prompt_parts.append(f"Files created so far: {len(previous_context['files_created'])} files")
            if "last_explanation" in previous_context:
                prompt_parts.append(f"Previous step: {previous_context['last_explanation']}")
            prompt_parts.append("")

        # Add project metadata
        metadata = context.metadata or {}
        if "tech_stack" in metadata:
            prompt_parts.append(f"TECH STACK: {metadata['tech_stack']}")
        if "features" in metadata:
            prompt_parts.append(f"FEATURES: {', '.join(metadata.get('features', []))}")

        prompt_parts.append("")
        prompt_parts.append("TASK:")
        prompt_parts.append(f"Execute Step {step_number} completely. Generate files, commands, and explanations using Bolt.new XML tags.")
        prompt_parts.append("Focus ONLY on this step. Do not generate files for future steps.")
        prompt_parts.append("")
        prompt_parts.append("Output format: <thinking>, <explain>, <file>, <terminal> tags")

        return "\n".join(prompt_parts)

    async def _execute_actions(
        self,
        parsed: Dict[str, Any],
        project_id: str,
        step_number: int
    ) -> Dict[str, Any]:
        """
        Execute parsed actions from Bolt.new response

        Args:
            parsed: Parsed response with files, commands, etc.
            project_id: Project identifier
            step_number: Current step number

        Returns:
            Dict with execution results
        """
        result = {
            "files_created": [],
            "commands_executed": [],
            "errors": []
        }

        # 1. Write files
        if "files" in parsed and parsed["files"]:
            for file_info in parsed["files"]:
                try:
                    file_path = file_info.get("path")
                    content = file_info.get("content")

                    if not file_path or not content:
                        logger.warning(f"[Writer Agent] Skipping file with missing path or content")
                        continue

                    # Write file using file_manager
                    write_result = await file_manager.create_file(
                        project_id=project_id,
                        file_path=file_path,
                        content=content
                    )

                    if write_result["success"]:
                        result["files_created"].append({
                            "path": file_path,
                            "size": len(content),
                            "step": step_number
                        })
                        logger.info(f"[Writer Agent] Created file: {file_path}")
                    else:
                        result["errors"].append(f"Failed to create {file_path}: {write_result.get('error')}")

                except Exception as e:
                    logger.error(f"[Writer Agent] Error writing file: {e}")
                    result["errors"].append(f"File write error: {str(e)}")

        # 2. Execute terminal commands
        if "terminal" in parsed:
            commands = parsed["terminal"]
            # Handle both single command (string) and multiple commands (list)
            if isinstance(commands, str):
                commands = [commands]

            for command in commands:
                try:
                    # Execute command safely
                    exec_result = await self._execute_terminal_command(
                        command=command,
                        project_id=project_id
                    )

                    result["commands_executed"].append({
                        "command": command,
                        "success": exec_result["success"],
                        "output": exec_result.get("output", ""),
                        "step": step_number
                    })

                    if not exec_result["success"]:
                        result["errors"].append(f"Command failed: {command}")

                except Exception as e:
                    logger.error(f"[Writer Agent] Error executing command: {e}")
                    result["errors"].append(f"Command error: {str(e)}")

        return result

    async def _execute_terminal_command(
        self,
        command: str,
        project_id: str,
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        Execute a terminal command safely

        Args:
            command: Command to execute
            project_id: Project identifier
            timeout: Command timeout in seconds

        Returns:
            Dict with execution result
        """
        try:
            logger.info(f"[Writer Agent] Executing command: {command}")

            # Get project directory
            project_dir = os.path.join("generated", project_id)

            # Security: Validate command is safe
            dangerous_commands = ["rm -rf", "sudo", "chmod 777", "dd if=", "> /dev/"]
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                logger.warning(f"[Writer Agent] Blocked dangerous command: {command}")
                return {
                    "success": False,
                    "error": "Command blocked for security reasons"
                }

            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir
            )

            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                return {
                    "success": process.returncode == 0,
                    "returncode": process.returncode,
                    "output": stdout.decode() if stdout else "",
                    "error": stderr.decode() if stderr else ""
                }

            except asyncio.TimeoutError:
                process.kill()
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout}s"
                }

        except Exception as e:
            logger.error(f"[Writer Agent] Command execution error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_plan_steps(
        self,
        context: AgentContext,
        plan: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Execute all steps from a plan sequentially

        Args:
            context: Agent context
            plan: Complete plan with steps
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with all execution results
        """
        results = {
            "steps_completed": [],
            "total_files_created": 0,
            "total_commands_executed": 0,
            "errors": [],
            "started_at": datetime.utcnow().isoformat()
        }

        # Extract steps from plan
        steps = self._extract_steps_from_plan(plan)
        total_steps = len(steps)

        logger.info(f"[Writer Agent] Starting execution of {total_steps} steps")

        previous_context = None

        for i, step_data in enumerate(steps, 1):
            # Update progress
            if progress_callback:
                progress_percent = int((i / total_steps) * 100)
                await progress_callback(
                    progress_percent,
                    f"Step {i}/{total_steps}: {step_data.get('name', 'Processing...')}"
                )

            # Execute step
            step_result = await self.process(
                context=context,
                step_number=i,
                step_data=step_data,
                previous_context=previous_context
            )

            results["steps_completed"].append(step_result)

            if step_result["success"]:
                results["total_files_created"] += len(step_result.get("files_created", []))
                results["total_commands_executed"] += len(step_result.get("commands_executed", []))

                # Update context for next step
                previous_context = {
                    "files_created": step_result.get("files_created", []),
                    "last_explanation": step_result.get("explanation")
                }
            else:
                results["errors"].append(f"Step {i} failed: {step_result.get('error')}")
                # Continue with next step even if current fails
                logger.warning(f"[Writer Agent] Step {i} failed, continuing with next step")

        results["completed_at"] = datetime.utcnow().isoformat()
        logger.info(f"[Writer Agent] Completed all steps. Files: {results['total_files_created']}, Commands: {results['total_commands_executed']}")

        return results

    def _extract_steps_from_plan(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract steps from plan structure"""
        steps = []

        # Check for implementation_steps or phases
        if "implementation_steps" in plan:
            for phase_key, phase_data in plan["implementation_steps"].items():
                if isinstance(phase_data, dict):
                    steps.append({
                        "name": phase_data.get("name", phase_key),
                        "description": phase_data.get("description", ""),
                        "tasks": phase_data.get("tasks", []),
                        "deliverables": phase_data.get("deliverables", []),
                        "duration": phase_data.get("duration", "")
                    })

        # Fallback: if no steps found, create a single step
        if not steps:
            steps.append({
                "name": "Project Implementation",
                "description": "Implement the complete project",
                "tasks": ["Generate all required files", "Setup dependencies"],
                "deliverables": ["Complete working application"]
            })

        return steps


# Singleton instance
writer_agent = WriterAgent()
