# 🔧 ENHANCER AGENT - User Guide

## Overview

**AGENT 6 - ENHANCER AGENT** intelligently adds new features and modules to existing projects by analyzing the codebase, creating enhancement plans, and coordinating Writer/Fixer agents to implement changes.

### What It Does

When students request:
- ✅ "Add Admin Panel"
- ✅ "Add OTP login"
- ✅ "Add charts/analytics"
- ✅ "Add ML model"
- ✅ "Add payment integration"
- ✅ "Add any new module"

The Enhancer Agent:
1. **Analyzes** your existing project structure
2. **Plans** what needs to be added/modified
3. **Generates** all required code
4. **Saves** files to your project

---

## How It Works

```
User Request: "Add Admin Panel"
         ↓
   Enhancer Agent
   (analyzes project, creates plan)
         ↓
 Enhancement Plan (XML)
 - Database changes
 - Backend tasks
 - Frontend tasks
 - Testing requirements
         ↓
  Enhancement Orchestrator
  (coordinates execution)
         ↓
  ┌──────┬──────┬──────┐
  │Writer│Fixer │Tester│
  │Agent │Agent │Agent │
  └──┬───┴───┬──┴───┬──┘
     │       │      │
     ▼       ▼      ▼
 New Files | Modified | Tests
  Created  | Files    | Generated
```

---

## Quick Start

### Basic Usage

```python
from app.modules.agents.enhancement_orchestrator import EnhancementOrchestrator
from app.modules.agents.project_analyzer import ProjectAnalyzer

# 1. Analyze your project
analyzer = ProjectAnalyzer("/path/to/project")
analysis = analyzer.analyze()

# 2. Create orchestrator
orchestrator = EnhancementOrchestrator("/path/to/project")

# 3. Request enhancement
results = await orchestrator.execute_enhancement(
    project_analysis=analysis,
    enhancement_request="Add Admin Panel with user management and analytics"
)

# 4. Check results
print(f"Files created: {results['files_created']}")
print(f"Files modified: {results['files_modified']}")
```

### CLI Usage

```bash
# Run the enhancement orchestrator
python backend/app/modules/agents/enhancement_orchestrator.py

# Follow prompts:
# > What would you like to add to the project?
# > Add Admin Panel
```

---

## Enhancement Plan Structure

The Enhancer Agent outputs a structured XML plan:

```xml
<enhancement_plan>
  <summary>Brief description of enhancement</summary>

  <impact_analysis>
    <architecture_changes>Any architectural changes needed</architecture_changes>
    <affected_modules>Existing modules that will be affected</affected_modules>
    <new_dependencies>New packages/libraries to install</new_dependencies>
  </impact_analysis>

  <database_changes>
    <new_tables>
      <table>
        <name>admin_logs</name>
        <columns>id, user_id, action, timestamp</columns>
        <relationships>Foreign key to users</relationships>
      </table>
    </new_tables>
    <table_modifications>
      <modification>
        <table>users</table>
        <changes>Add is_admin boolean column</changes>
      </modification>
    </table_modifications>
  </database_changes>

  <backend_tasks>
    <task>
      <type>create</type>
      <file>backend/app/api/v1/endpoints/admin.py</file>
      <description>Create admin API endpoints</description>
      <specifications>
        - GET /admin/users (list all users)
        - PUT /admin/users/{id} (update user)
        - DELETE /admin/users/{id} (delete user)
        - GET /admin/stats (dashboard statistics)
      </specifications>
    </task>
  </backend_tasks>

  <frontend_tasks>
    <task>
      <type>create</type>
      <file>frontend/src/app/admin/page.tsx</file>
      <description>Create admin dashboard page</description>
      <specifications>
        - User table with search/filter
        - Statistics cards
        - Charts (user growth, activity)
      </specifications>
    </task>
  </frontend_tasks>

  <testing_requirements>
    <requirement>Test admin authentication and authorization</requirement>
    <requirement>Test CRUD operations for user management</requirement>
  </testing_requirements>

  <documentation_updates>
    <update>Add admin panel section to README</update>
    <update>Update API documentation with new endpoints</update>
  </documentation_updates>

  <estimated_effort>
    <backend>4-6 hours</backend>
    <frontend>6-8 hours</frontend>
    <testing>2-3 hours</testing>
    <total>12-17 hours</total>
  </estimated_effort>
</enhancement_plan>
```

---

## Common Enhancement Examples

### 1. Add Admin Panel

**Request:**
```python
enhancement_request = """Add an Admin Panel with:
- Dashboard showing user statistics
- User management (view, edit, delete users)
- Activity logs
- Role-based access control
"""
```

**What Gets Generated:**
- ✅ Database model: `AdminLog`
- ✅ API endpoints: `backend/app/api/v1/endpoints/admin.py`
- ✅ Admin dashboard: `frontend/src/app/admin/page.tsx`
- ✅ User table component: `frontend/src/components/admin/UserTable.tsx`
- ✅ Statistics widgets: `frontend/src/components/admin/StatsCard.tsx`
- ✅ Tests: `backend/tests/test_admin.py`

### 2. Add OTP Authentication

**Request:**
```python
enhancement_request = "Add OTP-based phone authentication with Twilio"
```

**What Gets Generated:**
- ✅ Database model: `OTP` (phone, code, expires_at)
- ✅ API endpoints:
  - `POST /auth/send-otp` (send OTP)
  - `POST /auth/verify-otp` (verify OTP)
- ✅ Frontend component: `OTPInput.tsx`
- ✅ Twilio integration: `app/utils/sms_client.py`
- ✅ Tests: `test_otp_auth.py`

### 3. Add Analytics Dashboard

**Request:**
```python
enhancement_request = "Add analytics dashboard with charts showing user growth, activity, and revenue"
```

**What Gets Generated:**
- ✅ Analytics service: `backend/app/services/analytics.py`
- ✅ API endpoints: `GET /analytics/users`, `GET /analytics/revenue`
- ✅ Dashboard page: `frontend/src/app/analytics/page.tsx`
- ✅ Chart components using Recharts
- ✅ Date range picker
- ✅ Export to CSV functionality

### 4. Add ML Model Integration

**Request:**
```python
enhancement_request = "Add ML model for predicting user churn using scikit-learn"
```

**What Gets Generated:**
- ✅ Model training script: `backend/app/ml/train_churn_model.py`
- ✅ Prediction API: `POST /ml/predict-churn`
- ✅ Feature preprocessing: `app/ml/preprocessor.py`
- ✅ Model versioning: `app/ml/model_manager.py`
- ✅ Scheduled retraining: Celery task

### 5. Add Payment Integration

**Request:**
```python
enhancement_request = "Add Razorpay payment integration for subscription billing"
```

**What Gets Generated:**
- ✅ Database models: `Payment`, `Subscription`
- ✅ Payment endpoints:
  - `POST /payments/create-order`
  - `POST /payments/verify`
  - `POST /payments/webhook` (Razorpay webhooks)
- ✅ Frontend: Checkout page, payment form
- ✅ Razorpay client: `app/utils/razorpay_client.py`

---

## Quick Enhancement Templates

For common enhancements, use the `quick_enhance()` method:

```python
from app.modules.agents.enhancer_agent import EnhancerAgent

enhancer = EnhancerAgent()

# Available templates:
# - admin_panel
# - otp_auth
# - analytics
# - ml_model
# - payment
# - notifications
# - search

plan = await enhancer.quick_enhance(
    project_analysis=analysis,
    feature_name="Admin Panel",
    feature_type="admin_panel"
)
```

### Available Templates

| Feature Type | What It Adds |
|--------------|--------------|
| `admin_panel` | User management, dashboard, activity logs, permissions |
| `otp_auth` | Phone verification, OTP generation/sending, verification |
| `analytics` | Charts, user activity tracking, export to CSV/PDF |
| `ml_model` | Model training pipeline, prediction API, versioning |
| `payment` | Razorpay/Stripe integration, order processing, webhooks |
| `notifications` | Email, in-app, push notifications, templates |
| `search` | Full-text search, filters, autocomplete, Elasticsearch |

---

## Integration with Multi-Agent System

The Enhancer Agent works with other agents:

### Agent Collaboration

```
Enhancer Agent (creates plan)
      ↓
Writer Agent (creates new files)
      ↓
Fixer Agent (modifies existing files)
      ↓
Tester Agent (generates tests)
      ↓
Complete Enhancement
```

### Example Workflow

```python
from app.modules.agents.enhancer_agent import EnhancerAgent
from app.modules.agents.project_analyzer import ProjectAnalyzer

# 1. Analyze project
analyzer = ProjectAnalyzer("/path/to/project")
analysis = analyzer.analyze()

# 2. Create enhancement plan
enhancer = EnhancerAgent()
plan = await enhancer.create_enhancement_plan(
    analysis,
    "Add real-time notifications using WebSockets"
)

# 3. Generate task list
tasks = enhancer.generate_task_list(plan)

# 4. Execute tasks
for task in tasks:
    if task["agent"] == "writer":
        # Create new file
        await writer_agent.create_file(task)
    elif task["agent"] == "fixer":
        # Modify existing file
        await fixer_agent.modify_file(task)
    elif task["agent"] == "tester":
        # Generate tests
        await tester_agent.generate_tests(task)
```

---

## API Integration

Add enhancement endpoint to your FastAPI app:

```python
from fastapi import APIRouter, BackgroundTasks
from app.modules.agents.enhancement_orchestrator import EnhancementOrchestrator
from app.modules.agents.project_analyzer import ProjectAnalyzer

router = APIRouter()

@router.post("/projects/{project_id}/enhance")
async def enhance_project(
    project_id: str,
    enhancement_request: str,
    background_tasks: BackgroundTasks
):
    """
    Add new feature to existing project
    """

    # Get project
    project = get_project(project_id)

    # Analyze
    analyzer = ProjectAnalyzer(project.source_code_path)
    analysis = analyzer.analyze()

    # Execute enhancement in background
    orchestrator = EnhancementOrchestrator(project.source_code_path)

    background_tasks.add_task(
        orchestrator.execute_enhancement,
        analysis,
        enhancement_request
    )

    return {
        "message": "Enhancement started",
        "project_id": project_id
    }
```

### With Streaming

```python
from fastapi.responses import StreamingResponse

@router.post("/projects/{project_id}/enhance/stream")
async def enhance_project_stream(
    project_id: str,
    enhancement_request: str
):
    """
    Stream enhancement progress via SSE
    """

    async def event_generator():
        orchestrator = EnhancementOrchestrator(project.source_code_path)

        async def stream_callback(message: str):
            event = f"data: {json.dumps({'message': message})}\n\n"
            yield event

        results = await orchestrator.execute_enhancement(
            analysis,
            enhancement_request,
            stream_callback
        )

        # Final event
        yield f"data: {json.dumps({'status': 'complete', 'results': results})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

---

## Advanced Usage

### Custom Enhancement with Detailed Specs

```python
enhancement_request = """Add a Content Management System (CMS) with:

BACKEND:
- Database models: Article, Category, Tag
- API endpoints for CRUD operations
- Rich text editor support (store HTML)
- Image upload (to S3)
- Publish/Draft status
- SEO metadata (title, description, keywords)

FRONTEND:
- Article list with pagination
- Article detail page with rich text rendering
- Admin: Article editor with WYSIWYG
- Category and tag filtering
- Search functionality
- SEO-friendly URLs

INTEGRATIONS:
- AWS S3 for image storage
- Elasticsearch for full-text search (optional)
- Sitemap generation for SEO
"""

plan = await enhancer.create_enhancement_plan(analysis, enhancement_request)
```

### Modify Enhancement Plan Before Execution

```python
# Create plan
plan = await enhancer.create_enhancement_plan(analysis, request)

# Modify tasks (e.g., skip frontend)
plan["frontend_tasks"] = []

# Or add custom task
plan["backend_tasks"].append({
    "type": "create",
    "file": "backend/app/custom/my_service.py",
    "description": "Custom service",
    "specifications": "..."
})

# Execute modified plan
tasks = enhancer.generate_task_list(plan)
```

### Save Enhancement Plan for Review

```python
import json

# Generate plan
plan = await enhancer.create_enhancement_plan(analysis, request)

# Save to file
with open("enhancement_plans/admin_panel.json", "w") as f:
    json.dump(plan, f, indent=2)

# Review, modify, then execute later
with open("enhancement_plans/admin_panel.json", "r") as f:
    plan = json.load(f)

tasks = enhancer.generate_task_list(plan)
# Execute tasks...
```

---

## Best Practices

### 1. Be Specific in Requests

❌ **Vague:** "Add admin features"

✅ **Specific:** "Add Admin Panel with user management (view, edit, delete), dashboard with statistics (total users, active today, revenue this month), and activity logs table"

### 2. Consider Existing Architecture

The Enhancer Agent analyzes your current tech stack automatically. If you're using FastAPI + Next.js, it will generate FastAPI endpoints and Next.js components.

### 3. Review Plans Before Execution

```python
# Generate plan first
plan = await enhancer.create_enhancement_plan(analysis, request)

# Print summary
print(f"Summary: {plan['summary']}")
print(f"Backend tasks: {len(plan['backend_tasks'])}")
print(f"Frontend tasks: {len(plan['frontend_tasks'])}")
print(f"Database changes: {len(plan['database_changes']['new_tables'])}")

# Review, then execute
if input("Proceed? (y/n): ") == "y":
    orchestrator.execute_enhancement(...)
```

### 4. Test After Enhancement

Always run tests after adding features:

```bash
# Backend tests
cd backend
pytest

# Frontend tests (if applicable)
cd frontend
npm test
```

### 5. Commit Changes Incrementally

```bash
# After each major enhancement
git add .
git commit -m "feat: Add admin panel with user management"
```

---

## Troubleshooting

### Issue: "Enhancement plan is too generic"

**Solution:** Provide more detailed specifications in your request.

```python
# Instead of:
"Add analytics"

# Use:
"Add analytics dashboard showing:
- User growth chart (line chart, last 30 days)
- Activity heatmap (by hour and day)
- Revenue chart (bar chart, monthly)
- Top 10 users table (by activity)
- Export to CSV button"
```

### Issue: "Generated code doesn't match my style"

**Solution:** The agent follows the existing code style automatically. Ensure your codebase has consistent style.

### Issue: "Task failed during execution"

**Solution:** Check error logs. Common causes:
- Claude API timeout (retry)
- Invalid file path (check project structure)
- Missing dependencies (install required packages)

### Issue: "Database migration needed"

**Solution:** After adding new models, run migrations:

```bash
cd backend
alembic revision --autogenerate -m "Add admin models"
alembic upgrade head
```

---

## Cost Estimation

Using Claude 3.5 Sonnet:

| Enhancement | Tokens | Cost |
|-------------|--------|------|
| Admin Panel (full) | ~6,000 | $0.10 |
| OTP Auth | ~3,000 | $0.05 |
| Analytics Dashboard | ~5,000 | $0.08 |
| ML Model Integration | ~4,000 | $0.07 |
| Payment Integration | ~4,500 | $0.075 |

**Average enhancement: $0.05 - $0.15**

Compare to manual development:
- Manual coding: 8-20 hours
- With Enhancer Agent: 3-5 minutes + review time

---

## Examples Gallery

### Example 1: E-Commerce Add Cart

```python
request = "Add shopping cart functionality with add to cart, remove, update quantity, and checkout"

# Generates:
# - cart.py model
# - cart.py API endpoints
# - CartContext.tsx (React context)
# - Cart.tsx component
# - AddToCartButton.tsx
```

### Example 2: Blog Add Comments

```python
request = "Add comment system with nested replies, likes, and moderation"

# Generates:
# - comment.py model
# - comment.py endpoints
# - CommentSection.tsx
# - CommentForm.tsx
# - Nested comment rendering
```

### Example 3: Add Social Login

```python
request = "Add Google and GitHub OAuth login"

# Generates:
# - OAuth models (social_account)
# - OAuth endpoints
# - Social login buttons
# - OAuth callback handlers
```

---

## FAQ

**Q: Can I use this for non-Python projects?**
A: The Enhancer Agent adapts to your tech stack. It detects your languages and generates appropriate code.

**Q: Will it overwrite my existing code?**
A: Only files marked for modification will be changed. New files are created safely.

**Q: Can I undo changes?**
A: Use Git to version control. Commit before enhancement, revert if needed.

**Q: How accurate is the generated code?**
A: 85-90% production-ready. Always review and test before deployment.

**Q: Can I enhance multiple features at once?**
A: Yes! Provide a list: "Add admin panel, OTP auth, and analytics dashboard"

---

## Support

For issues:
1. Check enhancement plan JSON for details
2. Review generated files for errors
3. Check Claude API status
4. Open issue on GitHub

---

**Happy Enhancing! 🚀**
