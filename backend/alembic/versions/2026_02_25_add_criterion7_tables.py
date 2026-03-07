"""Add NAAC Criterion 7 tables

Revision ID: criterion7_001
Revises: criterion6_001
Create Date: 2026-02-25

Tables created:
- gender_equity_programs: Gender Equity Programs
- green_initiatives: Green Initiatives
- inclusivity_programs: Inclusivity Programs
- ethics_programs: Ethics Programs
- best_practices: Best Practices
- institutional_distinctiveness: Institutional Distinctiveness
- institutional_awards: Institutional Awards
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'criterion7_001'
down_revision = 'criterion6_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (IF NOT EXISTS for idempotency)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE greeninitiativetype AS ENUM ('solar_energy', 'rainwater_harvesting', 'waste_management', 'e_waste', 'green_audit', 'plantation', 'carbon_footprint', 'water_conservation', 'energy_audit', 'recycling', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE inclusivitytype AS ENUM ('divyangjan', 'economically_weaker', 'sc_st', 'obc', 'minority', 'women', 'first_generation', 'transgender', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE ethicstype AS ENUM ('code_of_conduct', 'anti_ragging', 'sexual_harassment', 'academic_integrity', 'research_ethics', 'professional_ethics', 'human_values', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE bestpracticecategory AS ENUM ('teaching_learning', 'research', 'extension', 'student_support', 'governance', 'infrastructure', 'industry_collaboration', 'community_engagement', 'innovation', 'sustainability', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE awardcategory AS ENUM ('national', 'state', 'university', 'accreditation', 'ranking', 'industry', 'media', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create gender_equity_programs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS gender_equity_programs (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            program_name VARCHAR(500) NOT NULL,
            description TEXT,
            objectives JSONB,
            program_type VARCHAR(100),
            academic_year VARCHAR(20) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE,
            organized_by VARCHAR(255),
            target_group VARCHAR(255),
            activities_conducted JSONB,
            participants_count INTEGER DEFAULT 0,
            male_participants INTEGER DEFAULT 0,
            female_participants INTEGER DEFAULT 0,
            resource_persons JSONB,
            outcomes JSONB,
            impact TEXT,
            budget FLOAT,
            expenditure FLOAT,
            report_path VARCHAR(500),
            photos_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create green_initiatives table
    op.execute("""
        CREATE TABLE IF NOT EXISTS green_initiatives (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            initiative_name VARCHAR(500) NOT NULL,
            initiative_type greeninitiativetype NOT NULL,
            description TEXT,
            objectives JSONB,
            academic_year VARCHAR(20) NOT NULL,
            implementation_date DATE NOT NULL,
            location VARCHAR(255),
            responsible_department VARCHAR(255),
            coordinator VARCHAR(255),
            capacity VARCHAR(100),
            investment FLOAT,
            annual_savings FLOAT,
            carbon_reduction_kg FLOAT,
            water_saved_liters FLOAT,
            energy_saved_kwh FLOAT,
            waste_recycled_kg FLOAT,
            trees_planted INTEGER,
            certifications JSONB,
            awards_received JSONB,
            sdg_goals_addressed JSONB,
            impact_metrics JSONB,
            audit_report_path VARCHAR(500),
            photos_path VARCHAR(500),
            certificate_path VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create inclusivity_programs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS inclusivity_programs (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            program_name VARCHAR(500) NOT NULL,
            inclusivity_type inclusivitytype NOT NULL,
            description TEXT,
            objectives JSONB,
            academic_year VARCHAR(20) NOT NULL,
            implementation_date DATE NOT NULL,
            target_group VARCHAR(255),
            beneficiaries_count INTEGER DEFAULT 0,
            facilities_provided JSONB,
            financial_support FLOAT,
            scholarships_provided INTEGER DEFAULT 0,
            special_provisions JSONB,
            accessibility_features JSONB,
            sensitization_programs JSONB,
            outcomes JSONB,
            impact TEXT,
            policy_document_path VARCHAR(500),
            report_path VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create ethics_programs table
    op.execute("""
        CREATE TABLE IF NOT EXISTS ethics_programs (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            program_name VARCHAR(500) NOT NULL,
            ethics_type ethicstype NOT NULL,
            description TEXT,
            objectives JSONB,
            academic_year VARCHAR(20) NOT NULL,
            implementation_date DATE NOT NULL,
            responsible_committee VARCHAR(255),
            coordinator VARCHAR(255),
            activities_conducted JSONB,
            participants_count INTEGER DEFAULT 0,
            sessions_conducted INTEGER DEFAULT 0,
            cases_handled INTEGER DEFAULT 0,
            cases_resolved INTEGER DEFAULT 0,
            awareness_programs JSONB,
            outcomes JSONB,
            policy_document_path VARCHAR(500),
            committee_details_path VARCHAR(500),
            report_path VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create best_practices table
    op.execute("""
        CREATE TABLE IF NOT EXISTS best_practices (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            title VARCHAR(500) NOT NULL,
            category bestpracticecategory NOT NULL,
            objective TEXT NOT NULL,
            context TEXT,
            the_practice TEXT NOT NULL,
            evidence_of_success TEXT,
            problems_encountered TEXT,
            resources_required JSONB,
            notes TEXT,
            academic_year VARCHAR(20) NOT NULL,
            introduced_year INTEGER,
            department VARCHAR(255),
            outcomes JSONB,
            impact_metrics JSONB,
            beneficiaries INTEGER DEFAULT 0,
            awards_recognition JSONB,
            documentation_path VARCHAR(500),
            photos_path VARCHAR(500),
            video_url VARCHAR(500),
            is_featured BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create institutional_distinctiveness table
    op.execute("""
        CREATE TABLE IF NOT EXISTS institutional_distinctiveness (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            title VARCHAR(500) NOT NULL,
            description TEXT NOT NULL,
            unique_features JSONB,
            academic_year VARCHAR(20) NOT NULL,
            year_established INTEGER,
            achievements JSONB,
            impact_on_students TEXT,
            impact_on_society TEXT,
            national_recognition JSONB,
            international_recognition JSONB,
            media_coverage JSONB,
            documentation_path VARCHAR(500),
            photos_path VARCHAR(500),
            video_url VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create institutional_awards table
    op.execute("""
        CREATE TABLE IF NOT EXISTS institutional_awards (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            award_name VARCHAR(500) NOT NULL,
            category awardcategory NOT NULL,
            awarding_body VARCHAR(500) NOT NULL,
            description TEXT,
            academic_year VARCHAR(20) NOT NULL,
            award_date DATE NOT NULL,
            rank VARCHAR(50),
            score FLOAT,
            significance TEXT,
            selection_criteria TEXT,
            competition_details TEXT,
            media_coverage JSONB,
            certificate_path VARCHAR(500),
            photos_path VARCHAR(500),
            press_release_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_gender_equity_programs_academic_year ON gender_equity_programs(academic_year)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_green_initiatives_type ON green_initiatives(initiative_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_green_initiatives_academic_year ON green_initiatives(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_green_initiatives_active ON green_initiatives(is_active)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_inclusivity_programs_type ON inclusivity_programs(inclusivity_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inclusivity_programs_academic_year ON inclusivity_programs(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_inclusivity_programs_active ON inclusivity_programs(is_active)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_ethics_programs_type ON ethics_programs(ethics_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ethics_programs_academic_year ON ethics_programs(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_ethics_programs_active ON ethics_programs(is_active)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_best_practices_category ON best_practices(category)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_best_practices_academic_year ON best_practices(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_best_practices_featured ON best_practices(is_featured)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_institutional_distinctiveness_academic_year ON institutional_distinctiveness(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_institutional_distinctiveness_active ON institutional_distinctiveness(is_active)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_institutional_awards_category ON institutional_awards(category)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_institutional_awards_academic_year ON institutional_awards(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_institutional_awards_date ON institutional_awards(award_date)")


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_institutional_awards_date")
    op.execute("DROP INDEX IF EXISTS ix_institutional_awards_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_institutional_awards_category")
    op.execute("DROP INDEX IF EXISTS ix_institutional_distinctiveness_active")
    op.execute("DROP INDEX IF EXISTS ix_institutional_distinctiveness_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_best_practices_featured")
    op.execute("DROP INDEX IF EXISTS ix_best_practices_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_best_practices_category")
    op.execute("DROP INDEX IF EXISTS ix_ethics_programs_active")
    op.execute("DROP INDEX IF EXISTS ix_ethics_programs_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_ethics_programs_type")
    op.execute("DROP INDEX IF EXISTS ix_inclusivity_programs_active")
    op.execute("DROP INDEX IF EXISTS ix_inclusivity_programs_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_inclusivity_programs_type")
    op.execute("DROP INDEX IF EXISTS ix_green_initiatives_active")
    op.execute("DROP INDEX IF EXISTS ix_green_initiatives_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_green_initiatives_type")
    op.execute("DROP INDEX IF EXISTS ix_gender_equity_programs_academic_year")

    # Drop tables
    op.drop_table('institutional_awards')
    op.drop_table('institutional_distinctiveness')
    op.drop_table('best_practices')
    op.drop_table('ethics_programs')
    op.drop_table('inclusivity_programs')
    op.drop_table('green_initiatives')
    op.drop_table('gender_equity_programs')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS awardcategory")
    op.execute("DROP TYPE IF EXISTS bestpracticecategory")
    op.execute("DROP TYPE IF EXISTS ethicstype")
    op.execute("DROP TYPE IF EXISTS inclusivitytype")
    op.execute("DROP TYPE IF EXISTS greeninitiativetype")
