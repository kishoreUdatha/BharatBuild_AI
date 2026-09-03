"""
Batch Detail Seeder - content for the Batch Registration Details tabs.

    python -m app.db.seed_batch_detail

Enriches every active batch for the current academic year with objectives,
methodology, scope, technology stack, base-paper metadata, documents, approval
events and an activity trail. Re-running replaces only what it created.
"""

import asyncio
import random
from datetime import date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal, init_db
from app.models.batch_detail import (
    ActivityLog,
    ActivitySeverity,
    ApprovalEvent,
    ApprovalEventKind,
    BatchDocument,
    DocumentStatus,
    ItemStatus,
    NovelContribution,
    PaperKeyMethod,
    PaperMetric,
    ProjectMethodologyStep,
    ProjectObjective,
    ProjectScopeItem,
    ProjectTechnology,
    ScopeKind,
    SupportingPaper,
)
from app.models.faculty import (
    BasePaper,
    BasePaperStatus,
    BatchRegistrationStatus,
    ProjectBatch,
    ProjectBatchMember,
)
from app.models.user import User

ACADEMIC_YEAR = "2026-27"

# The project cycle the seeded cohort is living in. Anchored so a batch sits
# roughly two thirds of the way through on a 2026 demo - which is what makes
# 50-70% progress read as normal rather than impossible - while every start
# and finish still falls inside the 2026-27 year the batches are labelled with.
CYCLE_START = date(2026, 4, 6)
CYCLE_DAYS = 215

RESPONSIBILITIES = ["ML Lead", "Data Engineer", "Analytics & Visualisation", "Testing & Documentation", "Backend"]

DOMAINS = [
    "Artificial Intelligence / Machine Learning",
    "Computer Vision",
    "Internet of Things",
    "Data Engineering",
    "Cyber Security",
]

METHODOLOGY = [
    ("Data Collection", "Collect load, weather and calendar data."),
    ("Data Cleaning", "Handle missing values, outliers and inconsistencies."),
    ("Feature Engineering", "Create meaningful features for modeling."),
    ("Model Training", "Train models using multiple algorithms."),
    ("Ensemble Evaluation", "Evaluate ensembles and compare performance."),
    ("API Integration", "Expose forecasts through a secure REST API."),
    ("Dashboard", "Visualise forecasts and insights on a web dashboard."),
]

TECH_STACK = [
    ("Frontend", ["React", "TypeScript"]),
    ("Backend", ["FastAPI", "Python"]),
    ("Machine Learning", ["Pandas", "Scikit-learn", "XGBoost", "LightGBM"]),
    ("Database", ["PostgreSQL"]),
    ("Visualisation", ["Plotly"]),
    ("Deployment", ["Docker"]),
]

DOCUMENT_PLAN = [
    ("Student Declarations.pdf", "Student Declaration", True, DocumentStatus.VERIFIED, 1_200_000),
    ("Team Consent Form.pdf", "Team Document", True, DocumentStatus.VERIFIED, 860_000),
    ("Project Abstract.pdf", "Project Document", True, DocumentStatus.VERIFIED, 1_800_000),
    ("Requirements Specification.pdf", "Project Document", True, DocumentStatus.AWAITING_VERIFICATION, 3_400_000),
    ("Base Paper.pdf", "Base Paper", True, DocumentStatus.VERIFIED, 3_800_000),
    ("Guide Acceptance.pdf", "Faculty Document", True, DocumentStatus.VERIFIED, 720_000),
    ("Similarity Report.pdf", "Compliance", False, DocumentStatus.VERIFIED, 1_100_000),
    ("Technology Stack Confirmation.pdf", "Project Document", False, DocumentStatus.CHANGES_REQUESTED, 980_000),
    ("Budget Estimate.xlsx", "Supporting Document", False, DocumentStatus.AWAITING_VERIFICATION, 420_000),
    ("Ethics Approval Form.pdf", "Compliance", True, DocumentStatus.MISSING, 0),
]


async def seed(rng: random.Random) -> None:
    async with AsyncSessionLocal() as db:
        batches = list((await db.execute(
            select(ProjectBatch)
            .options(
                selectinload(ProjectBatch.members).selectinload(ProjectBatchMember.student),
                selectinload(ProjectBatch.base_paper),
                selectinload(ProjectBatch.guide),
            )
            .where(ProjectBatch.academic_year == ACADEMIC_YEAR)
            .where(ProjectBatch.is_active.is_(True))
            .order_by(ProjectBatch.batch_code)
        )).scalars().unique().all())

        if not batches:
            print("No batches found - run seed_faculty first.")
            return

        batch_ids = [b.id for b in batches]
        for model in (ProjectObjective, ProjectMethodologyStep, ProjectScopeItem, ProjectTechnology,
                      SupportingPaper, NovelContribution, BatchDocument, ApprovalEvent, ActivityLog):
            await db.execute(delete(model).where(model.batch_id.in_(batch_ids)))
        paper_ids = [b.base_paper.id for b in batches if b.base_paper]
        if paper_ids:
            for model in (PaperMetric, PaperKeyMethod):
                await db.execute(delete(model).where(model.base_paper_id.in_(paper_ids)))
        await db.flush()

        guide = batches[0].guide
        now = datetime.utcnow()
        seq = 0

        for index, batch in enumerate(batches):
            title = batch.title or "Untitled Project"
            created = batch.created_at or now

            # --- project fields
            batch.domain = DOMAINS[index % len(DOMAINS)]
            batch.problem_statement = (
                f"Current approaches to {title.lower()} are manual and inconsistent, which raises "
                "operating cost and slows decision making."
            )
            batch.keywords = ", ".join(["Load Forecasting", "Ensemble Learning", "Energy Analytics",
                                        "Time Series", "Smart Grid"][: 3 + index % 3])
            batch.internal_note = "Team composition is valid. Responsibilities are distributed clearly."
            # Every batch used to share one start date two days before the
            # demo, while carrying 50-70% progress - so the tracking screen
            # reported all forty-five as wildly ahead of schedule. Real cohorts
            # neither start on the same morning nor run to the same length, so
            # the cycle is staggered here. The step is derived from the index,
            # not randomised, to keep a reseed reproducible.
            batch.start_date = CYCLE_START + timedelta(days=(index % 11 - 5) * 7)
            batch.target_completion = batch.start_date + timedelta(
                days=CYCLE_DAYS + (index % 5) * 10
            )
            batch.weekly_effort_hours = 12

            # --- member responsibilities and join times
            for position, member in enumerate(sorted(batch.members, key=lambda m: m.created_at or created)):
                member.responsibility = "Batch Leader" if member.is_lead else RESPONSIBILITIES[position % len(RESPONSIBILITIES)]
                if member.is_lead:
                    member.responsibility = RESPONSIBILITIES[0]
                member.joined_at = created + timedelta(minutes=15 * position)

            # --- objectives
            for position, text in enumerate([
                f"Forecast short-term demand for industrial and residential facilities.",
                "Compare Random Forest, XGBoost, LightGBM and stacking ensemble performance.",
                "Analyse weather, calendar and usage-pattern effects on demand.",
                "Provide an interactive dashboard with forecasts, confidence ranges and insights.",
            ]):
                db.add(ProjectObjective(
                    batch_id=batch.id, position=position, text=text,
                    status=ItemStatus.COMPLETE if batch.abstract else ItemStatus.PENDING,
                ))

            for position, (step_title, description) in enumerate(METHODOLOGY):
                db.add(ProjectMethodologyStep(batch_id=batch.id, position=position,
                                              title=step_title, description=description))

            scope = [
                (ScopeKind.IN_SCOPE, ["Data ingestion and preprocessing", "Ensemble ML models development",
                                      "Forecast API and integration", "React dashboard development",
                                      "Model evaluation and reporting"]),
                (ScopeKind.OUT_OF_SCOPE, ["Real-time grid control", "Hardware meter installation",
                                          "Utility billing integration"]),
                (ScopeKind.DELIVERABLE, ["Source Code", "Dataset", "Requirements Specification",
                                         "Design Document", "Test Report", "User Manual",
                                         "Final Report", "Presentation"]),
                (ScopeKind.OUTCOME, ["Accurate hourly and daily demand forecasts",
                                     "Separate industrial and residential insights",
                                     "Comparison of baseline and ensemble models",
                                     "Interactive monitoring dashboard",
                                     "Downloadable forecast reports"]),
            ]
            for kind, items in scope:
                for position, text in enumerate(items):
                    db.add(ProjectScopeItem(batch_id=batch.id, kind=kind, position=position, text=text))

            for layer, names in TECH_STACK:
                for position, name in enumerate(names):
                    db.add(ProjectTechnology(batch_id=batch.id, layer=layer, name=name, position=position))

            # --- base paper detail
            paper = batch.base_paper
            if paper and paper.status != BasePaperStatus.MISSING:
                paper.publisher = "IEEE"
                paper.publication_type = "Journal Article"
                paper.volume = "12"
                paper.pages = "45820-45836"
                paper.doi = f"10.1109/ACCESS.2024.{1234567 + index}"
                paper.indexing = "Scopus, Web of Science"
                paper.quartile = "Q2"
                paper.file_name = f"Base_Paper_{batch.batch_code}.pdf"
                paper.file_size = 3_800_000
                paper.page_count = 16
                paper.abstract_summary = (
                    "The paper evaluates LSTM and ensemble approaches for short-term forecasting using "
                    "historical consumption and weather features. It reports improved accuracy over "
                    "conventional statistical models."
                )
                paper.dataset = "Hourly residential electricity demand with weather attributes"
                paper.current_limitation = "Single combined dataset; limited ensemble comparison; static output."
                paper.improvement_note = (
                    "Separate industrial and residential forecasting; compare Random Forest, XGBoost, "
                    "LightGBM and stacking; add confidence intervals and an interactive web dashboard."
                )
                paper.similarity_percent = 8.0
                paper.relevance_score = 95
                paper.methodology_score = 88
                paper.recency_score = 90
                paper.credibility_score = 94
                paper.faculty_note = (
                    "Primary paper is relevant and technically sound. The proposed improvement adds "
                    "sufficient scope for a major project."
                )
                paper.uploaded_by_id = next((m.student_id for m in batch.members if not m.is_lead), None)
                paper.uploaded_at = created + timedelta(days=3)

                for position, (name, value) in enumerate([("MAE", "2.84"), ("RMSE", "4.12"), ("MAPE", "3.7%")]):
                    db.add(PaperMetric(base_paper_id=paper.id, name=name, value=value, position=position))
                for position, name in enumerate(["LSTM", "Random Forest", "Gradient Boosting",
                                                 "Feature Engineering", "Time-Series Validation"]):
                    db.add(PaperKeyMethod(base_paper_id=paper.id, name=name, position=position))

                for position, text in enumerate([
                    "Multi-sector demand modelling",
                    "Wider ensemble benchmark",
                    "Confidence intervals and feature importance",
                    "Deployable forecast API and dashboard",
                ]):
                    db.add(NovelContribution(batch_id=batch.id, position=position, text=text))

                for position, (sp_title, authors, source, year, purpose) in enumerate([
                    ("Industrial Load Forecasting with XGBoost", "M. Chen et al.", "Applied Energy", 2023,
                     "Benchmark Comparison"),
                    ("Explainable AI for Smart Grid Demand Prediction", "A. Sharma et al.", "Sustainable Computing",
                     2024, "Explainability Reference"),
                ]):
                    db.add(SupportingPaper(
                        batch_id=batch.id, title=sp_title, authors=authors, source=source,
                        year=year, purpose=purpose, doi=f"10.1016/j.apenergy.2023.{100 + position}",
                    ))

            # --- documents
            members = sorted(batch.members, key=lambda m: m.created_at or created)
            for position, (name, category, required, doc_status, size) in enumerate(DOCUMENT_PLAN):
                uploader = None
                if doc_status != DocumentStatus.MISSING and members:
                    uploader = members[position % len(members)].student_id
                if category == "Faculty Document" and guide:
                    uploader = guide.id
                db.add(BatchDocument(
                    batch_id=batch.id,
                    name=name,
                    category=category,
                    version="v1.1" if doc_status == DocumentStatus.AWAITING_VERIFICATION else "v1.0",
                    file_size=size,
                    page_count=28 if "Requirements" in name else None,
                    mime_type="application/pdf" if name.endswith(".pdf") else
                              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    status=doc_status,
                    is_required=required,
                    similarity_percent=8.0 if "Similarity" in name else None,
                    faculty_note="Verify scope and functional requirements before approval."
                    if "Requirements" in name else None,
                    uploaded_by_id=uploader,
                    uploaded_at=created + timedelta(days=position // 2, hours=position),
                    verified_by_id=guide.id if doc_status == DocumentStatus.VERIFIED and guide else None,
                    verified_at=created + timedelta(days=4) if doc_status == DocumentStatus.VERIFIED else None,
                ))

            # --- approval journey
            leader = next((m for m in batch.members if m.is_lead), None)
            leader_id = leader.student_id if leader else None
            submitted = batch.submitted_at or (created + timedelta(days=8))
            journey = [
                (1, ApprovalEventKind.SUBMITTED, "Registration Submitted",
                 "Four members, project details, three papers and ten documents submitted.",
                 "Submitted", leader_id, "Batch Leader", submitted, None),
                (1, ApprovalEventKind.REVIEW_STARTED, "Initial Faculty Review Started",
                 "Base paper and project scope accepted.", "In Review",
                 guide.id if guide else None, "Faculty Reviewer", submitted + timedelta(hours=18), 80),
                (1, ApprovalEventKind.CHANGES_REQUESTED, "Changes Requested",
                 "Upload the ethics approval form, clarify the dataset source and revise the "
                 "technology-stack confirmation.", "Changes Requested",
                 guide.id if guide else None, "Faculty Reviewer", submitted + timedelta(hours=19), None),
                (2, ApprovalEventKind.RESUBMITTED, "Changes Resubmitted",
                 "Dataset source clarified; Technology Stack Confirmation v1.1 uploaded; "
                 "Ethics Approval Form requested from department.", "Resubmitted",
                 leader_id, "Batch Leader", submitted + timedelta(days=2), None),
                (2, ApprovalEventKind.DOCUMENTS_VERIFIED, "Documents Verified",
                 "Requirements Specification approved; Technology Stack Confirmation approved; "
                 "Similarity Report 8% passed; Ethics Approval remains pending.", "Partially Verified",
                 guide.id if guide else None, "Faculty Reviewer", submitted + timedelta(days=2, hours=2), None),
                (3, ApprovalEventKind.FINAL_REVIEW, "Final Approval Review",
                 "7 of 8 mandatory checks complete. Blocking item: Ethics Approval Form.",
                 "Pending Final Approval", guide.id if guide else None, "Faculty Reviewer",
                 submitted + timedelta(days=3), None),
            ]
            for cycle, kind, ev_title, body, label, actor, role, when, minutes in journey:
                db.add(ApprovalEvent(
                    batch_id=batch.id, cycle=cycle, kind=kind, title=ev_title, body=body,
                    status_label=label, actor_id=actor, actor_role=role,
                    occurred_at=when, duration_minutes=minutes,
                ))
            for position, note in enumerate([
                "Scope is acceptable; documents need correction.",
                "All critical items resolved except ethics approval.",
            ]):
                db.add(ApprovalEvent(
                    batch_id=batch.id, cycle=3, kind=ApprovalEventKind.FINAL_REVIEW,
                    title="Internal Review Note", body=note, status_label=None,
                    actor_id=guide.id if guide else None, actor_role="Faculty Reviewer",
                    occurred_at=submitted + timedelta(days=2 + position, hours=1), is_private=True,
                ))

            # --- activity trail
            member_names = {str(m.student_id): (m.student.full_name if m.student else "Student")
                            for m in batch.members}
            trail = [
                ("Assigned as faculty guide", "Team", "Assignment recorded", "Success", ActivitySeverity.SUCCESS,
                 guide, "Faculty", created + timedelta(days=1)),
                ("Verified primary base paper", "Base Papers", "DOI and relevance verified", "Success",
                 ActivitySeverity.SUCCESS, guide, "Faculty", created + timedelta(days=4)),
                ("Submitted registration v1.0", "Registration", "Initial submission", "Submitted",
                 ActivitySeverity.INFO, None, "Batch Leader", submitted),
                ("Started initial review", "Approval", "Review cycle 1 opened", "In Review",
                 ActivitySeverity.INFO, guide, "Faculty", submitted + timedelta(hours=18)),
                ("Requested changes", "Approval", "Clarify dataset source and upload ethics form",
                 "Changes Requested", ActivitySeverity.WARNING, guide, "Faculty", submitted + timedelta(hours=19)),
                ("Uploaded Technology Stack Confirmation v1.1", "Documents", "Replaced version v1.0", "Uploaded",
                 ActivitySeverity.INFO, None, "Student", submitted + timedelta(days=2, minutes=-4)),
                ("Resubmitted registration v1.1", "Registration", "Updated documents and dataset source",
                 "Submitted", ActivitySeverity.INFO, None, "Batch Leader", submitted + timedelta(days=2)),
                ("Verified Requirements Specification v1.1", "Documents", "Verification completed", "Success",
                 ActivitySeverity.SUCCESS, guide, "Faculty", submitted + timedelta(days=2, hours=2)),
                ("Approval checklist recalculated", "Approval", "Ethics approval marked pending", "Warning",
                 ActivitySeverity.WARNING, None, "System", submitted + timedelta(days=3, minutes=-2)),
                ("Opened final approval review", "Approval", "7/8 checks passed; Ethics Approval pending",
                 "In Progress", ActivitySeverity.INFO, guide, "Faculty", submitted + timedelta(days=3)),
            ]
            for activity, module, details, label, severity, actor, role, when in trail:
                seq += 1
                db.add(ActivityLog(
                    event_code=f"ACT-2026-{seq:04d}",
                    batch_id=batch.id,
                    actor_id=actor.id if actor else (leader_id if role in {"Batch Leader", "Student"} else None),
                    actor_name=(actor.full_name if actor else
                                (member_names.get(str(leader_id), "Student") if role != "System" else "System")),
                    actor_role=role,
                    activity=activity,
                    module=module,
                    details=details,
                    status_label=label,
                    severity=severity,
                    ip_address="10.***.***.24" if role != "System" else None,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)" if role != "System" else None,
                    source="Faculty Portal / Web" if role == "Faculty" else "Student Portal / Web",
                    occurred_at=when,
                    changed_field="Technology Stack" if "Technology Stack" in activity else None,
                    previous_value="v1.0" if "Technology Stack" in activity else None,
                    current_value="v1.1" if "Technology Stack" in activity else None,
                ))

        await db.commit()
        print(f"Enriched {len(batches)} batch(es) with detail content.")


async def main() -> None:
    print("Seeding batch registration detail...")
    await init_db()
    await seed(random.Random(20260819))


if __name__ == "__main__":
    asyncio.run(main())
