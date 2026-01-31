"""
Check Project Cost - Query token usage for a project
"""

import asyncio
import os
from pathlib import Path

# Load API key
for env_file in [".env.test", ".env"]:
    env_path = Path(__file__).parent / env_file
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").split("\n"):
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        break

from sqlalchemy import select, func, and_, desc
from app.core.database import AsyncSessionLocal
from app.models.project import Project
from app.models.usage import TokenUsageLog, AgentType


async def check_project_cost(project_name: str = "Hospital"):
    """Check token usage for a project by name."""

    print("=" * 70)
    print(f"CHECKING COST FOR PROJECT: {project_name}")
    print("=" * 70)

    async with AsyncSessionLocal() as db:
        # Find project by name
        result = await db.execute(
            select(Project)
            .where(Project.title.ilike(f"%{project_name}%"))
            .order_by(desc(Project.created_at))
            .limit(5)
        )
        projects = result.scalars().all()

        if not projects:
            print(f"\n[!] No project found matching '{project_name}'")
            return

        print(f"\nFound {len(projects)} matching projects:")
        for i, p in enumerate(projects, 1):
            print(f"  {i}. {p.title} (Status: {p.status.value}, Created: {p.created_at})")

        # Check the most recent one
        project = projects[0]
        project_id = str(project.id)

        print(f"\n" + "-" * 50)
        print(f"Analyzing: {project.title}")
        print(f"Status: {project.status.value}")
        print(f"Project ID: {project_id}")
        print("-" * 50)

        # Get totals from project model
        print(f"\n[Project Model Totals]")
        print(f"  Total tokens: {project.total_tokens:,}")
        print(f"  Total cost: ₹{project.total_cost / 100:.2f} ({project.total_cost} paise)")

        # Get detailed breakdown from token_usage_logs
        total_result = await db.execute(
            select(
                func.sum(TokenUsageLog.input_tokens),
                func.sum(TokenUsageLog.output_tokens),
                func.sum(TokenUsageLog.total_tokens),
                func.sum(TokenUsageLog.cost_paise),
                func.count(TokenUsageLog.id)
            ).where(TokenUsageLog.project_id == project_id)
        )
        total_row = total_result.one()
        input_tokens = total_row[0] or 0
        output_tokens = total_row[1] or 0
        total_tokens = total_row[2] or 0
        total_cost_paise = total_row[3] or 0
        tx_count = total_row[4] or 0

        print(f"\n[Token Usage Logs]")
        print(f"  API Calls: {tx_count}")
        print(f"  Input tokens: {input_tokens:,}")
        print(f"  Output tokens: {output_tokens:,}")
        print(f"  Total tokens: {total_tokens:,}")
        print(f"  Total cost: ₹{total_cost_paise / 100:.2f} ({total_cost_paise} paise)")

        # Convert to USD (approx 83 INR = 1 USD)
        usd_cost = (total_cost_paise / 100) / 83
        print(f"  Total cost (USD): ${usd_cost:.2f}")

        # Breakdown by agent type
        agent_result = await db.execute(
            select(
                TokenUsageLog.agent_type,
                func.sum(TokenUsageLog.input_tokens),
                func.sum(TokenUsageLog.output_tokens),
                func.sum(TokenUsageLog.total_tokens),
                func.sum(TokenUsageLog.cost_paise),
                func.count(TokenUsageLog.id)
            )
            .where(TokenUsageLog.project_id == project_id)
            .group_by(TokenUsageLog.agent_type)
            .order_by(func.sum(TokenUsageLog.cost_paise).desc())
        )

        print(f"\n[Cost Breakdown by Agent]")
        print("-" * 70)
        print(f"{'Agent':<15} {'Calls':<8} {'Input':>12} {'Output':>12} {'Cost (₹)':>12} {'%':>8}")
        print("-" * 70)

        for row in agent_result.all():
            agent_type = row[0].value if row[0] else "unknown"
            a_input = row[1] or 0
            a_output = row[2] or 0
            a_total = row[3] or 0
            a_cost = row[4] or 0
            a_count = row[5] or 0
            pct = (a_cost / total_cost_paise * 100) if total_cost_paise > 0 else 0
            print(f"{agent_type:<15} {a_count:<8} {a_input:>12,} {a_output:>12,} {a_cost/100:>12.2f} {pct:>7.1f}%")

        print("-" * 70)
        print(f"{'TOTAL':<15} {tx_count:<8} {input_tokens:>12,} {output_tokens:>12,} {total_cost_paise/100:>12.2f} {'100.0':>7}%")

        # Breakdown by model
        model_result = await db.execute(
            select(
                TokenUsageLog.model,
                func.sum(TokenUsageLog.total_tokens),
                func.sum(TokenUsageLog.cost_paise),
                func.count(TokenUsageLog.id)
            )
            .where(TokenUsageLog.project_id == project_id)
            .group_by(TokenUsageLog.model)
        )

        print(f"\n[Cost Breakdown by Model]")
        print("-" * 50)
        for row in model_result.all():
            model = row[0] or "unknown"
            m_tokens = row[1] or 0
            m_cost = row[2] or 0
            m_count = row[3] or 0
            print(f"  {model}: {m_tokens:,} tokens, ₹{m_cost/100:.2f} ({m_count} calls)")
        print("-" * 50)

        # Recent transactions
        recent_result = await db.execute(
            select(TokenUsageLog)
            .where(TokenUsageLog.project_id == project_id)
            .order_by(desc(TokenUsageLog.created_at))
            .limit(10)
        )
        recent_txs = recent_result.scalars().all()

        if recent_txs:
            print(f"\n[Recent API Calls (last 10)]")
            print("-" * 80)
            for tx in recent_txs:
                file_info = f" - {tx.file_path.split('/')[-1]}" if tx.file_path else ""
                print(f"  {tx.agent_type.value:<10} | {tx.operation.value:<15} | "
                      f"{tx.total_tokens:>8,} tokens | ₹{tx.cost_paise/100:>6.2f}{file_info}")
            print("-" * 80)


if __name__ == "__main__":
    asyncio.run(check_project_cost("Hospital"))
