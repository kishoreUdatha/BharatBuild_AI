"""
AGENT 6 — ENHANCER AGENT (Add Modules / Improve Features)

Used when student requests:
- "Add Admin Panel"
- "Add OTP login"
- "Add charts"
- "Add ML model"
- "Add new module"

The Enhancer Agent:
1. Analyzes the current project structure
2. Understands the enhancement request
3. Creates a detailed enhancement plan
4. Outputs tasks for Writer and Fixer agents to execute
"""

from typing import Dict, Any, List
from app.utils.claude_client import ClaudeClient
import json
import re


class EnhancerAgent:
    """
    Enhancement Agent for adding new features and modules to existing projects.
    """

    def __init__(self):
        self.claude_client = ClaudeClient()
        self.model = "claude-3-5-sonnet-20241022"

    async def create_enhancement_plan(
        self,
        project_analysis: Dict[str, Any],
        enhancement_request: str
    ) -> Dict[str, Any]:
        """
        Create an enhancement plan based on project analysis and user request.

        Args:
            project_analysis: Current project structure and details
            enhancement_request: What the user wants to add/improve

        Returns:
            Enhancement plan with tasks, file changes, and architecture updates
        """

        system_prompt = """You are the ENHANCER AGENT.

Your job:
- Understand user enhancement request.
- Update architecture if needed.
- Generate required new tasks OR updated modules.
- Output only <enhancement_plan>...</enhancement_plan>.

Writer + Fixer Agents will handle code.

IMPORTANT RULES:
- NO CODE in your output (Writer agent will generate code)
- Only provide structured plan and specifications
- Be specific about files to create/modify
- Consider existing architecture and tech stack
- Ensure backward compatibility
- Think about database changes, API endpoints, frontend components
"""

        user_prompt = f"""Based on the following project and enhancement request, create a detailed enhancement plan.

# CURRENT PROJECT

## Project Name
{project_analysis.get('project_name', 'Unknown')}

## Technology Stack
### Backend
{json.dumps(project_analysis.get('technology_stack', {}).get('backend', {}), indent=2)}

### Frontend
{json.dumps(project_analysis.get('technology_stack', {}).get('frontend', {}), indent=2)}

### Database
{json.dumps(project_analysis.get('technology_stack', {}).get('database', {}), indent=2)}

## Current Architecture
{project_analysis.get('architecture', 'Not specified')}

## Existing Modules
{json.dumps(project_analysis.get('modules', []), indent=2)}

## Current Features
{chr(10).join(f"- {feature}" for feature in project_analysis.get('features', []))}

## Database Schema (Tables)
{json.dumps(project_analysis.get('database_schema', {}).get('tables', []), indent=2)}

## File Structure
{json.dumps(project_analysis.get('file_structure', {}), indent=2)}

---

# ENHANCEMENT REQUEST

{enhancement_request}

---

# YOUR TASK

Create a comprehensive enhancement plan using this XML format:

<enhancement_plan>
  <summary>Brief description of what will be added/changed</summary>

  <impact_analysis>
    <architecture_changes>Any changes to system architecture</architecture_changes>
    <affected_modules>List of existing modules that will be affected</affected_modules>
    <new_dependencies>New packages/libraries needed</new_dependencies>
  </impact_analysis>

  <database_changes>
    <new_tables>
      <table>
        <name>table_name</name>
        <columns>column1, column2, column3</columns>
        <relationships>Foreign keys and relationships</relationships>
      </table>
    </new_tables>
    <table_modifications>
      <modification>
        <table>existing_table</table>
        <changes>What columns to add/modify</changes>
      </modification>
    </table_modifications>
  </database_changes>

  <backend_tasks>
    <task>
      <type>create|modify</type>
      <file>path/to/file.py</file>
      <description>What needs to be done</description>
      <specifications>Detailed specs (API endpoints, models, logic)</specifications>
    </task>
  </backend_tasks>

  <frontend_tasks>
    <task>
      <type>create|modify</type>
      <file>path/to/component.tsx</file>
      <description>What UI component/page to create</description>
      <specifications>Component props, state, API calls</specifications>
    </task>
  </frontend_tasks>

  <testing_requirements>
    <requirement>What needs to be tested</requirement>
  </testing_requirements>

  <documentation_updates>
    <update>What documentation needs updating</update>
  </documentation_updates>

  <estimated_effort>
    <backend>X hours/days</backend>
    <frontend>X hours/days</frontend>
    <testing>X hours/days</testing>
    <total>X hours/days</total>
  </estimated_effort>
</enhancement_plan>

Remember:
- NO CODE, only specifications
- Be specific about file paths
- Consider existing architecture
- Think about frontend AND backend
- Include database changes if needed
"""

        # Call Claude API
        response = await self.claude_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=self.model,
            max_tokens=4000,
            temperature=0.7
        )

        # Parse XML response
        enhancement_plan = self._parse_enhancement_plan(response['content'][0]['text'])

        return enhancement_plan

    def _parse_enhancement_plan(self, xml_content: str) -> Dict[str, Any]:
        """
        Parse XML enhancement plan from Claude response.

        Args:
            xml_content: XML string with <enhancement_plan> root

        Returns:
            Structured enhancement plan dict
        """

        def extract_tag(content: str, tag: str) -> str:
            pattern = f'<{tag}>(.*?)</{tag}>'
            match = re.search(pattern, content, re.DOTALL)
            return match.group(1).strip() if match else ""

        def extract_list(content: str, parent_tag: str, child_tag: str) -> List[str]:
            parent_pattern = f'<{parent_tag}>(.*?)</{parent_tag}>'
            parent_match = re.search(parent_pattern, content, re.DOTALL)
            if not parent_match:
                return []

            parent_content = parent_match.group(1)
            child_pattern = f'<{child_tag}>(.*?)</{child_tag}>'
            return re.findall(child_pattern, parent_content, re.DOTALL)

        # Parse main sections
        plan = {
            "summary": extract_tag(xml_content, "summary"),
            "impact_analysis": {
                "architecture_changes": extract_tag(xml_content, "architecture_changes"),
                "affected_modules": extract_tag(xml_content, "affected_modules"),
                "new_dependencies": extract_tag(xml_content, "new_dependencies")
            },
            "database_changes": {
                "new_tables": [],
                "table_modifications": []
            },
            "backend_tasks": [],
            "frontend_tasks": [],
            "testing_requirements": [],
            "documentation_updates": [],
            "estimated_effort": {}
        }

        # Parse database changes
        new_tables_section = re.search(r'<new_tables>(.*?)</new_tables>', xml_content, re.DOTALL)
        if new_tables_section:
            tables = re.findall(r'<table>(.*?)</table>', new_tables_section.group(1), re.DOTALL)
            for table in tables:
                plan["database_changes"]["new_tables"].append({
                    "name": extract_tag(table, "name"),
                    "columns": extract_tag(table, "columns"),
                    "relationships": extract_tag(table, "relationships")
                })

        # Parse backend tasks
        backend_section = re.search(r'<backend_tasks>(.*?)</backend_tasks>', xml_content, re.DOTALL)
        if backend_section:
            tasks = re.findall(r'<task>(.*?)</task>', backend_section.group(1), re.DOTALL)
            for task in tasks:
                plan["backend_tasks"].append({
                    "type": extract_tag(task, "type"),
                    "file": extract_tag(task, "file"),
                    "description": extract_tag(task, "description"),
                    "specifications": extract_tag(task, "specifications")
                })

        # Parse frontend tasks
        frontend_section = re.search(r'<frontend_tasks>(.*?)</frontend_tasks>', xml_content, re.DOTALL)
        if frontend_section:
            tasks = re.findall(r'<task>(.*?)</task>', frontend_section.group(1), re.DOTALL)
            for task in tasks:
                plan["frontend_tasks"].append({
                    "type": extract_tag(task, "type"),
                    "file": extract_tag(task, "file"),
                    "description": extract_tag(task, "description"),
                    "specifications": extract_tag(task, "specifications")
                })

        # Parse testing requirements
        plan["testing_requirements"] = extract_list(xml_content, "testing_requirements", "requirement")

        # Parse documentation updates
        plan["documentation_updates"] = extract_list(xml_content, "documentation_updates", "update")

        # Parse estimated effort
        effort_section = re.search(r'<estimated_effort>(.*?)</estimated_effort>', xml_content, re.DOTALL)
        if effort_section:
            effort_content = effort_section.group(1)
            plan["estimated_effort"] = {
                "backend": extract_tag(effort_content, "backend"),
                "frontend": extract_tag(effort_content, "frontend"),
                "testing": extract_tag(effort_content, "testing"),
                "total": extract_tag(effort_content, "total")
            }

        return plan

    def generate_task_list(self, enhancement_plan: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Generate ordered task list for Writer and Fixer agents.

        Args:
            enhancement_plan: Parsed enhancement plan

        Returns:
            List of tasks with type, file, and specifications
        """

        tasks = []

        # 1. Database tasks first
        for table in enhancement_plan.get("database_changes", {}).get("new_tables", []):
            tasks.append({
                "agent": "writer",
                "type": "database_model",
                "file": f"backend/app/models/{table['name']}.py",
                "description": f"Create database model for {table['name']}",
                "specifications": f"Columns: {table['columns']}\nRelationships: {table['relationships']}"
            })

        # 2. Backend tasks
        for task in enhancement_plan.get("backend_tasks", []):
            tasks.append({
                "agent": "writer" if task["type"] == "create" else "fixer",
                "type": task["type"],
                "file": task["file"],
                "description": task["description"],
                "specifications": task["specifications"]
            })

        # 3. Frontend tasks
        for task in enhancement_plan.get("frontend_tasks", []):
            tasks.append({
                "agent": "writer" if task["type"] == "create" else "fixer",
                "type": task["type"],
                "file": task["file"],
                "description": task["description"],
                "specifications": task["specifications"]
            })

        # 4. Testing tasks
        for requirement in enhancement_plan.get("testing_requirements", []):
            tasks.append({
                "agent": "tester",
                "type": "test",
                "description": requirement,
                "specifications": "Generate comprehensive tests"
            })

        return tasks

    async def quick_enhance(
        self,
        project_analysis: Dict[str, Any],
        feature_name: str,
        feature_type: str
    ) -> Dict[str, Any]:
        """
        Quick enhancement for common features.

        Args:
            project_analysis: Current project
            feature_name: Name of feature (e.g., "Admin Panel", "OTP Login")
            feature_type: Type (admin_panel, otp_auth, analytics, ml_model, etc.)

        Returns:
            Enhancement plan
        """

        templates = {
            "admin_panel": """Add a complete admin panel with:
- User management (CRUD operations)
- Dashboard with statistics
- Activity logs
- Role-based permissions
- Data export features""",

            "otp_auth": """Add OTP-based authentication with:
- Phone number verification
- OTP generation and sending (Twilio/SMS service)
- OTP verification endpoint
- Expiry mechanism (5 minutes)
- Rate limiting""",

            "analytics": """Add analytics and charts with:
- User activity tracking
- Dashboard with charts (line, bar, pie)
- Export to CSV/PDF
- Real-time statistics
- Data visualization library (Recharts/Chart.js)""",

            "ml_model": """Add machine learning model with:
- Model training pipeline
- Prediction API endpoint
- Model versioning
- Feature preprocessing
- Integration with existing data""",

            "payment": """Add payment integration with:
- Razorpay/Stripe integration
- Order creation and processing
- Payment verification
- Webhook handling
- Transaction history""",

            "notifications": """Add notification system with:
- Email notifications (SendGrid/AWS SES)
- In-app notifications
- Push notifications (optional)
- Notification preferences
- Template management""",

            "search": """Add advanced search with:
- Full-text search capability
- Filters and sorting
- Autocomplete/suggestions
- Search history
- Elasticsearch integration (optional)"""
        }

        enhancement_request = templates.get(
            feature_type,
            f"Add {feature_name} feature to the project"
        )

        return await self.create_enhancement_plan(project_analysis, enhancement_request)


# Example usage
async def example_usage():
    """
    Example of using EnhancerAgent
    """
    from app.modules.agents.project_analyzer import ProjectAnalyzer

    # Analyze current project
    analyzer = ProjectAnalyzer(r"C:\Users\KishoreUdatha\IdeaProjects\BharatBuild_AI")
    project_analysis = analyzer.analyze()

    # Initialize enhancer agent
    enhancer = EnhancerAgent()

    # Example 1: Custom enhancement request
    print("=" * 60)
    print("Example 1: Custom Enhancement")
    print("=" * 60)

    enhancement_request = """Add an Admin Panel with the following features:
- Dashboard showing user statistics, project counts, token usage
- User management (view all users, activate/deactivate, change roles)
- Project management (view all projects, delete projects)
- Analytics charts showing usage over time
- Activity logs table
"""

    plan = await enhancer.create_enhancement_plan(project_analysis, enhancement_request)

    print(f"\n✅ Enhancement Plan Created!")
    print(f"\nSummary: {plan['summary']}")
    print(f"\nBackend Tasks: {len(plan['backend_tasks'])}")
    print(f"Frontend Tasks: {len(plan['frontend_tasks'])}")
    print(f"Database Changes: {len(plan['database_changes']['new_tables'])} new tables")
    print(f"\nEstimated Effort: {plan['estimated_effort'].get('total', 'Not estimated')}")

    # Generate task list for execution
    tasks = enhancer.generate_task_list(plan)
    print(f"\n📋 Generated {len(tasks)} tasks for execution:")
    for i, task in enumerate(tasks[:5], 1):  # Show first 5
        print(f"   {i}. [{task['agent']}] {task['description']}")
    if len(tasks) > 5:
        print(f"   ... and {len(tasks) - 5} more tasks")

    # Example 2: Quick enhancement with template
    print("\n" + "=" * 60)
    print("Example 2: Quick Enhancement (OTP Login)")
    print("=" * 60)

    quick_plan = await enhancer.quick_enhance(
        project_analysis,
        "OTP Authentication",
        "otp_auth"
    )

    print(f"\n✅ Quick Enhancement Plan Created!")
    print(f"\nSummary: {quick_plan['summary']}")
    print(f"Backend Tasks: {len(quick_plan['backend_tasks'])}")
    print(f"Frontend Tasks: {len(quick_plan['frontend_tasks'])}")

    # Save plan to JSON
    import os
    output_dir = "enhancement_plans"
    os.makedirs(output_dir, exist_ok=True)

    with open(f"{output_dir}/admin_panel_plan.json", 'w') as f:
        json.dump(plan, f, indent=2)

    print(f"\n💾 Enhancement plan saved to {output_dir}/admin_panel_plan.json")

    return plan, tasks


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
