"""Add NAAC Criterion 6 tables

Revision ID: criterion6_001
Revises: criterion5_001
Create Date: 2026-02-25

Tables created:
- institutional_governance: Institutional Governance Records
- governance_meetings: Governance Meeting Records
- institutional_policies: Institutional Policies
- iqac_activities: IQAC Activities
- faculty_development: Faculty Development Programs
- financial_audits: Financial Audit Records
- strategic_plans: Strategic Plans
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'criterion6_001'
down_revision = 'criterion5_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (IF NOT EXISTS for idempotency)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE meetingtype AS ENUM ('governing_body', 'academic_council', 'board_of_studies', 'finance_committee', 'iqac', 'department', 'faculty', 'cdc', 'examination', 'grievance', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE policytype AS ENUM ('academic', 'administrative', 'hr', 'financial', 'student', 'research', 'it', 'safety', 'environment', 'ethics', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE qualityinitiativetype AS ENUM ('aqar', 'iiqa', 'ssr', 'naac_visit', 'nba_visit', 'iso_audit', 'nirf', 'academic_audit', 'feedback_analysis', 'curriculum_review', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE fdptype AS ENUM ('workshop', 'seminar', 'conference', 'fdp', 'sttp', 'online_course', 'certification', 'industrial_training', 'sabbatical', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE audittype AS ENUM ('statutory', 'internal', 'external', 'cag', 'iso', 'academic', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create institutional_governance table
    op.execute("""
        CREATE TABLE IF NOT EXISTS institutional_governance (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            academic_year VARCHAR(20) NOT NULL,
            vision_statement TEXT,
            mission_statement TEXT,
            core_values JSONB,
            quality_policy TEXT,
            leadership_details JSONB,
            governance_committees JSONB,
            organogram_path VARCHAR(500),
            e_governance_modules JSONB,
            decentralization_practices JSONB,
            participative_management JSONB,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create governance_meetings table
    op.execute("""
        CREATE TABLE IF NOT EXISTS governance_meetings (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            meeting_type meetingtype NOT NULL,
            title VARCHAR(500) NOT NULL,
            meeting_number VARCHAR(50),
            meeting_date DATE NOT NULL,
            start_time VARCHAR(10),
            end_time VARCHAR(10),
            venue VARCHAR(255),
            mode VARCHAR(50),
            academic_year VARCHAR(20) NOT NULL,
            chairperson VARCHAR(255),
            convener VARCHAR(255),
            agenda_items JSONB,
            attendees JSONB,
            members_present INTEGER DEFAULT 0,
            members_absent INTEGER DEFAULT 0,
            decisions_taken JSONB,
            action_items JSONB,
            notice_path VARCHAR(500),
            agenda_path VARCHAR(500),
            minutes_path VARCHAR(500),
            attendance_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create institutional_policies table
    op.execute("""
        CREATE TABLE IF NOT EXISTS institutional_policies (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            policy_name VARCHAR(500) NOT NULL,
            policy_type policytype NOT NULL,
            policy_number VARCHAR(50),
            description TEXT,
            objectives JSONB,
            scope TEXT,
            key_provisions JSONB,
            implementation_guidelines TEXT,
            responsible_authority VARCHAR(255),
            effective_date DATE,
            approved_by VARCHAR(255),
            approval_date DATE,
            review_frequency VARCHAR(50),
            last_reviewed_date DATE,
            version VARCHAR(20),
            policy_document_path VARCHAR(500),
            approval_document_path VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create iqac_activities table
    op.execute("""
        CREATE TABLE IF NOT EXISTS iqac_activities (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            activity_name VARCHAR(500) NOT NULL,
            activity_type qualityinitiativetype NOT NULL,
            description TEXT,
            objectives JSONB,
            academic_year VARCHAR(20) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE,
            coordinator VARCHAR(255),
            committee_members JSONB,
            key_initiatives JSONB,
            outcomes JSONB,
            action_items JSONB,
            recommendations JSONB,
            implementation_status VARCHAR(100),
            report_path VARCHAR(500),
            evidence_path VARCHAR(500),
            is_completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create faculty_development table
    op.execute("""
        CREATE TABLE IF NOT EXISTS faculty_development (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            faculty_name VARCHAR(255) NOT NULL,
            faculty_id VARCHAR(50),
            faculty_email VARCHAR(255),
            department VARCHAR(255) NOT NULL,
            designation VARCHAR(100),
            program_type fdptype NOT NULL,
            program_name VARCHAR(500) NOT NULL,
            organizing_body VARCHAR(255),
            venue VARCHAR(255),
            mode VARCHAR(50),
            start_date DATE NOT NULL,
            end_date DATE,
            duration_days INTEGER,
            academic_year VARCHAR(20) NOT NULL,
            topics_covered JSONB,
            skills_acquired JSONB,
            is_sponsored BOOLEAN DEFAULT FALSE,
            sponsorship_amount FLOAT,
            certificate_received BOOLEAN DEFAULT FALSE,
            certificate_path VARCHAR(500),
            report_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create financial_audits table
    op.execute("""
        CREATE TABLE IF NOT EXISTS financial_audits (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            audit_type audittype NOT NULL,
            audit_name VARCHAR(255) NOT NULL,
            financial_year VARCHAR(20) NOT NULL,
            auditor_name VARCHAR(255),
            auditor_firm VARCHAR(255),
            audit_start_date DATE,
            audit_end_date DATE,
            total_income FLOAT,
            total_expenditure FLOAT,
            surplus_deficit FLOAT,
            audit_observations JSONB,
            compliance_status VARCHAR(100),
            action_taken JSONB,
            audit_report_path VARCHAR(500),
            financial_statements_path VARCHAR(500),
            utilization_certificate_path VARCHAR(500),
            is_completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create strategic_plans table
    op.execute("""
        CREATE TABLE IF NOT EXISTS strategic_plans (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            plan_name VARCHAR(500) NOT NULL,
            plan_period VARCHAR(50) NOT NULL,
            start_year INTEGER NOT NULL,
            end_year INTEGER NOT NULL,
            vision_2030 TEXT,
            mission_goals JSONB,
            strategic_objectives JSONB,
            key_initiatives JSONB,
            kpis JSONB,
            resource_allocation JSONB,
            implementation_progress FLOAT,
            milestones_achieved JSONB,
            challenges JSONB,
            plan_document_path VARCHAR(500),
            progress_report_path VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_institutional_governance_academic_year ON institutional_governance(academic_year)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_governance_meetings_type ON governance_meetings(meeting_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_governance_meetings_date ON governance_meetings(meeting_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_governance_meetings_academic_year ON governance_meetings(academic_year)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_institutional_policies_type ON institutional_policies(policy_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_institutional_policies_active ON institutional_policies(is_active)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_iqac_activities_type ON iqac_activities(activity_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_iqac_activities_academic_year ON iqac_activities(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_iqac_activities_completed ON iqac_activities(is_completed)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_faculty_development_type ON faculty_development(program_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_faculty_development_department ON faculty_development(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_faculty_development_academic_year ON faculty_development(academic_year)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_financial_audits_type ON financial_audits(audit_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_financial_audits_year ON financial_audits(financial_year)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_strategic_plans_active ON strategic_plans(is_active)")


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_strategic_plans_active")
    op.execute("DROP INDEX IF EXISTS ix_financial_audits_year")
    op.execute("DROP INDEX IF EXISTS ix_financial_audits_type")
    op.execute("DROP INDEX IF EXISTS ix_faculty_development_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_faculty_development_department")
    op.execute("DROP INDEX IF EXISTS ix_faculty_development_type")
    op.execute("DROP INDEX IF EXISTS ix_iqac_activities_completed")
    op.execute("DROP INDEX IF EXISTS ix_iqac_activities_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_iqac_activities_type")
    op.execute("DROP INDEX IF EXISTS ix_institutional_policies_active")
    op.execute("DROP INDEX IF EXISTS ix_institutional_policies_type")
    op.execute("DROP INDEX IF EXISTS ix_governance_meetings_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_governance_meetings_date")
    op.execute("DROP INDEX IF EXISTS ix_governance_meetings_type")
    op.execute("DROP INDEX IF EXISTS ix_institutional_governance_academic_year")

    # Drop tables
    op.drop_table('strategic_plans')
    op.drop_table('financial_audits')
    op.drop_table('faculty_development')
    op.drop_table('iqac_activities')
    op.drop_table('institutional_policies')
    op.drop_table('governance_meetings')
    op.drop_table('institutional_governance')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS audittype")
    op.execute("DROP TYPE IF EXISTS fdptype")
    op.execute("DROP TYPE IF EXISTS qualityinitiativetype")
    op.execute("DROP TYPE IF EXISTS policytype")
    op.execute("DROP TYPE IF EXISTS meetingtype")
