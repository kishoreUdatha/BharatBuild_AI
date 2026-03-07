"""Add NAAC Criterion 3 tables

Revision ID: criterion3_001
Revises: criterion2_001
Create Date: 2026-02-25

Tables created:
- research_projects: Research Projects (Student & Faculty)
- publications: Research Publications
- patents: Patents (Filed/Granted)
- startups: Startups & Spin-offs
- innovation_cells: Innovation Cell / IIC
- hackathons: Hackathons & Competitions
- extension_activities: Extension Activities (Community Outreach)
- consultancies: Consultancy Projects
- research_funding: Research Funding and Grants
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'criterion3_001'
down_revision = 'criterion2_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (IF NOT EXISTS for idempotency)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE projecttype AS ENUM ('student', 'faculty', 'collaborative', 'sponsored', 'consultancy');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE researchprojectstatus AS ENUM ('proposed', 'ongoing', 'completed', 'extended', 'terminated');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE publicationtype AS ENUM ('journal_international', 'journal_national', 'conference_international', 'conference_national', 'book', 'book_chapter', 'patent', 'thesis', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE publicationindexing AS ENUM ('scopus', 'web_of_science', 'ugc_care', 'pubmed', 'ieee', 'acm', 'other', 'none');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE patentstatus AS ENUM ('filed', 'published', 'granted', 'rejected', 'abandoned');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE patenttype AS ENUM ('indian', 'international', 'us', 'european', 'pct');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE startupstage AS ENUM ('ideation', 'prototype', 'mvp', 'early_stage', 'growth', 'established');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE startupstatus AS ENUM ('incubated', 'registered', 'operational', 'funded', 'acquired', 'closed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE eventtype AS ENUM ('hackathon', 'ideathon', 'workshop', 'seminar', 'conference', 'competition', 'exhibition', 'bootcamp');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE extensiontype AS ENUM ('nss', 'ncc', 'community_service', 'awareness_program', 'health_camp', 'literacy_drive', 'environment', 'skill_development', 'village_adoption', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE fundingagency AS ENUM ('dst', 'dbt', 'serb', 'csir', 'ugc', 'aicte', 'icmr', 'drdo', 'isro', 'industry', 'international', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create research_projects table
    op.execute("""
        CREATE TABLE IF NOT EXISTS research_projects (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            title VARCHAR(500) NOT NULL,
            project_type projecttype NOT NULL,
            description TEXT,
            objectives JSONB,
            methodology TEXT,
            department VARCHAR(255) NOT NULL,
            domain VARCHAR(255),
            keywords JSONB,
            start_date DATE NOT NULL,
            end_date DATE,
            duration_months INTEGER,
            academic_year VARCHAR(20) NOT NULL,
            status researchprojectstatus DEFAULT 'proposed',
            principal_investigator VARCHAR(255) NOT NULL,
            pi_designation VARCHAR(100),
            pi_email VARCHAR(255),
            co_investigators JSONB,
            student_researchers JSONB,
            funding_agency fundingagency,
            funding_agency_name VARCHAR(255),
            sanctioned_amount FLOAT,
            received_amount FLOAT,
            grant_number VARCHAR(100),
            publications JSONB,
            patents JSONB,
            products_developed JSONB,
            awards_received JSONB,
            proposal_path VARCHAR(500),
            sanction_letter_path VARCHAR(500),
            completion_report_path VARCHAR(500),
            utilization_certificate_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create publications table
    op.execute("""
        CREATE TABLE IF NOT EXISTS publications (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            title VARCHAR(1000) NOT NULL,
            publication_type publicationtype NOT NULL,
            abstract TEXT,
            keywords JSONB,
            authors JSONB NOT NULL,
            corresponding_author VARCHAR(255),
            department VARCHAR(255) NOT NULL,
            journal_name VARCHAR(500),
            conference_name VARCHAR(500),
            publisher VARCHAR(255),
            volume VARCHAR(50),
            issue VARCHAR(50),
            pages VARCHAR(50),
            publication_year INTEGER NOT NULL,
            publication_date DATE,
            indexing publicationindexing DEFAULT 'none',
            impact_factor FLOAT,
            h_index INTEGER,
            citations INTEGER DEFAULT 0,
            doi VARCHAR(255),
            issn VARCHAR(50),
            isbn VARCHAR(50),
            paper_url VARCHAR(500),
            pdf_path VARCHAR(500),
            project_id VARCHAR(36) REFERENCES research_projects(id) ON DELETE SET NULL,
            is_verified BOOLEAN DEFAULT FALSE,
            verified_by VARCHAR(255),
            verified_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create patents table
    op.execute("""
        CREATE TABLE IF NOT EXISTS patents (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            title VARCHAR(1000) NOT NULL,
            patent_type patenttype NOT NULL,
            status patentstatus DEFAULT 'filed',
            description TEXT,
            claims TEXT,
            application_number VARCHAR(100),
            patent_number VARCHAR(100),
            filing_date DATE NOT NULL,
            filing_year INTEGER NOT NULL,
            publication_date DATE,
            grant_date DATE,
            inventors JSONB NOT NULL,
            applicant VARCHAR(500),
            department VARCHAR(255) NOT NULL,
            ipc_class VARCHAR(100),
            technology_area VARCHAR(255),
            is_commercialized BOOLEAN DEFAULT FALSE,
            commercialization_details TEXT,
            revenue_generated FLOAT,
            application_path VARCHAR(500),
            certificate_path VARCHAR(500),
            project_id VARCHAR(36) REFERENCES research_projects(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create startups table
    op.execute("""
        CREATE TABLE IF NOT EXISTS startups (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            problem_statement TEXT,
            solution TEXT,
            industry_sector VARCHAR(255),
            technology_used JSONB,
            stage startupstage DEFAULT 'ideation',
            status startupstatus DEFAULT 'incubated',
            founders JSONB NOT NULL,
            department VARCHAR(255) NOT NULL,
            incubated_at VARCHAR(255),
            registration_number VARCHAR(100),
            registration_date DATE,
            dpiit_recognized BOOLEAN DEFAULT FALSE,
            dpiit_number VARCHAR(100),
            seed_funding FLOAT,
            total_funding FLOAT,
            funding_rounds JSONB,
            investors JSONB,
            revenue FLOAT,
            employees_count INTEGER,
            products_services JSONB,
            awards JSONB,
            website VARCHAR(500),
            email VARCHAR(255),
            phone VARCHAR(50),
            address TEXT,
            pitch_deck_path VARCHAR(500),
            registration_certificate_path VARCHAR(500),
            mou_path VARCHAR(500),
            founded_date DATE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create innovation_cells table
    op.execute("""
        CREATE TABLE IF NOT EXISTS innovation_cells (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            name VARCHAR(255) NOT NULL,
            cell_type VARCHAR(100) NOT NULL,
            registration_number VARCHAR(100),
            establishment_date DATE,
            academic_year VARCHAR(20) NOT NULL,
            coordinator_name VARCHAR(255) NOT NULL,
            coordinator_designation VARCHAR(100),
            coordinator_email VARCHAR(255),
            coordinator_phone VARCHAR(50),
            faculty_members JSONB,
            student_members JSONB,
            external_mentors JSONB,
            activities_conducted JSONB,
            workshops_count INTEGER DEFAULT 0,
            seminars_count INTEGER DEFAULT 0,
            hackathons_count INTEGER DEFAULT 0,
            ideas_generated INTEGER DEFAULT 0,
            prototypes_developed INTEGER DEFAULT 0,
            startups_incubated INTEGER DEFAULT 0,
            patents_filed INTEGER DEFAULT 0,
            iic_star_rating INTEGER,
            mhrd_points FLOAT,
            annual_budget FLOAT,
            funds_utilized FLOAT,
            annual_report_path VARCHAR(500),
            registration_certificate_path VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create hackathons table
    op.execute("""
        CREATE TABLE IF NOT EXISTS hackathons (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            name VARCHAR(500) NOT NULL,
            event_type eventtype NOT NULL,
            description TEXT,
            theme VARCHAR(255),
            problem_statements JSONB,
            organized_by VARCHAR(255) NOT NULL,
            is_internal BOOLEAN DEFAULT TRUE,
            department VARCHAR(255),
            academic_year VARCHAR(20) NOT NULL,
            event_date DATE NOT NULL,
            end_date DATE,
            duration_hours INTEGER,
            venue VARCHAR(255),
            mode VARCHAR(50),
            registrations_count INTEGER DEFAULT 0,
            participants_count INTEGER DEFAULT 0,
            teams_count INTEGER DEFAULT 0,
            submissions_count INTEGER DEFAULT 0,
            winners JSONB,
            college_participants JSONB,
            college_achievements JSONB,
            total_prize_pool FLOAT,
            prizes JSONB,
            sponsors JSONB,
            brochure_path VARCHAR(500),
            report_path VARCHAR(500),
            photos_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create extension_activities table
    op.execute("""
        CREATE TABLE IF NOT EXISTS extension_activities (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            title VARCHAR(500) NOT NULL,
            activity_type extensiontype NOT NULL,
            description TEXT,
            objectives JSONB,
            outcomes JSONB,
            organized_by VARCHAR(255) NOT NULL,
            department VARCHAR(255),
            academic_year VARCHAR(20) NOT NULL,
            venue VARCHAR(255),
            village_adopted VARCHAR(255),
            district VARCHAR(100),
            state VARCHAR(100),
            activity_date DATE NOT NULL,
            end_date DATE,
            duration_days INTEGER DEFAULT 1,
            faculty_involved JSONB,
            students_participated INTEGER DEFAULT 0,
            student_list JSONB,
            beneficiaries_count INTEGER DEFAULT 0,
            beneficiaries_type VARCHAR(255),
            collaborating_agencies JSONB,
            funding_received FLOAT,
            funding_source VARCHAR(255),
            impact_description TEXT,
            sdg_goals_addressed JSONB,
            media_coverage JSONB,
            awards_received JSONB,
            report_path VARCHAR(500),
            photos_path VARCHAR(500),
            certificate_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create consultancies table
    op.execute("""
        CREATE TABLE IF NOT EXISTS consultancies (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            scope_of_work TEXT,
            deliverables JSONB,
            client_name VARCHAR(500) NOT NULL,
            client_type VARCHAR(100),
            client_contact VARCHAR(255),
            client_email VARCHAR(255),
            department VARCHAR(255) NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            consultant_name VARCHAR(255) NOT NULL,
            consultant_designation VARCHAR(100),
            team_members JSONB,
            start_date DATE NOT NULL,
            end_date DATE,
            status researchprojectstatus DEFAULT 'ongoing',
            consultancy_amount FLOAT NOT NULL,
            amount_received FLOAT,
            institute_share FLOAT,
            mou_number VARCHAR(100),
            mou_date DATE,
            mou_path VARCHAR(500),
            completion_certificate_path VARCHAR(500),
            payment_receipt_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create research_funding table
    op.execute("""
        CREATE TABLE IF NOT EXISTS research_funding (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            scheme_name VARCHAR(500) NOT NULL,
            funding_agency fundingagency NOT NULL,
            agency_name VARCHAR(255),
            project_id VARCHAR(36) REFERENCES research_projects(id) ON DELETE SET NULL,
            project_title VARCHAR(500),
            pi_name VARCHAR(255) NOT NULL,
            pi_designation VARCHAR(100),
            department VARCHAR(255) NOT NULL,
            financial_year VARCHAR(20) NOT NULL,
            sanctioned_amount FLOAT NOT NULL,
            received_amount FLOAT,
            utilized_amount FLOAT,
            grant_number VARCHAR(100),
            sanction_date DATE,
            duration_years INTEGER,
            sanction_letter_path VARCHAR(500),
            utilization_certificate_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create indexes for research_projects
    op.execute("CREATE INDEX IF NOT EXISTS ix_research_projects_type ON research_projects(project_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_research_projects_status ON research_projects(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_research_projects_department ON research_projects(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_research_projects_academic_year ON research_projects(academic_year)")

    # Create indexes for publications
    op.execute("CREATE INDEX IF NOT EXISTS ix_publications_type ON publications(publication_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_publications_department ON publications(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_publications_year ON publications(publication_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_publications_indexing ON publications(indexing)")

    # Create indexes for patents
    op.execute("CREATE INDEX IF NOT EXISTS ix_patents_status ON patents(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_patents_type ON patents(patent_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_patents_department ON patents(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_patents_year ON patents(filing_year)")

    # Create indexes for startups
    op.execute("CREATE INDEX IF NOT EXISTS ix_startups_stage ON startups(stage)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_startups_status ON startups(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_startups_department ON startups(department)")

    # Create indexes for innovation_cells
    op.execute("CREATE INDEX IF NOT EXISTS ix_innovation_cells_type ON innovation_cells(cell_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_innovation_cells_academic_year ON innovation_cells(academic_year)")

    # Create indexes for hackathons
    op.execute("CREATE INDEX IF NOT EXISTS ix_hackathons_type ON hackathons(event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_hackathons_date ON hackathons(event_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_hackathons_department ON hackathons(department)")

    # Create indexes for extension_activities
    op.execute("CREATE INDEX IF NOT EXISTS ix_extension_activities_type ON extension_activities(activity_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_extension_activities_date ON extension_activities(activity_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_extension_activities_department ON extension_activities(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_extension_activities_academic_year ON extension_activities(academic_year)")

    # Create indexes for consultancies
    op.execute("CREATE INDEX IF NOT EXISTS ix_consultancies_department ON consultancies(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_consultancies_status ON consultancies(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_consultancies_academic_year ON consultancies(academic_year)")

    # Create indexes for research_funding
    op.execute("CREATE INDEX IF NOT EXISTS ix_research_funding_agency ON research_funding(funding_agency)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_research_funding_department ON research_funding(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_research_funding_year ON research_funding(financial_year)")


def downgrade() -> None:
    # Drop indexes for research_funding
    op.execute("DROP INDEX IF EXISTS ix_research_funding_year")
    op.execute("DROP INDEX IF EXISTS ix_research_funding_department")
    op.execute("DROP INDEX IF EXISTS ix_research_funding_agency")

    # Drop indexes for consultancies
    op.execute("DROP INDEX IF EXISTS ix_consultancies_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_consultancies_status")
    op.execute("DROP INDEX IF EXISTS ix_consultancies_department")

    # Drop indexes for extension_activities
    op.execute("DROP INDEX IF EXISTS ix_extension_activities_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_extension_activities_department")
    op.execute("DROP INDEX IF EXISTS ix_extension_activities_date")
    op.execute("DROP INDEX IF EXISTS ix_extension_activities_type")

    # Drop indexes for hackathons
    op.execute("DROP INDEX IF EXISTS ix_hackathons_department")
    op.execute("DROP INDEX IF EXISTS ix_hackathons_date")
    op.execute("DROP INDEX IF EXISTS ix_hackathons_type")

    # Drop indexes for innovation_cells
    op.execute("DROP INDEX IF EXISTS ix_innovation_cells_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_innovation_cells_type")

    # Drop indexes for startups
    op.execute("DROP INDEX IF EXISTS ix_startups_department")
    op.execute("DROP INDEX IF EXISTS ix_startups_status")
    op.execute("DROP INDEX IF EXISTS ix_startups_stage")

    # Drop indexes for patents
    op.execute("DROP INDEX IF EXISTS ix_patents_year")
    op.execute("DROP INDEX IF EXISTS ix_patents_department")
    op.execute("DROP INDEX IF EXISTS ix_patents_type")
    op.execute("DROP INDEX IF EXISTS ix_patents_status")

    # Drop indexes for publications
    op.execute("DROP INDEX IF EXISTS ix_publications_indexing")
    op.execute("DROP INDEX IF EXISTS ix_publications_year")
    op.execute("DROP INDEX IF EXISTS ix_publications_department")
    op.execute("DROP INDEX IF EXISTS ix_publications_type")

    # Drop indexes for research_projects
    op.execute("DROP INDEX IF EXISTS ix_research_projects_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_research_projects_department")
    op.execute("DROP INDEX IF EXISTS ix_research_projects_status")
    op.execute("DROP INDEX IF EXISTS ix_research_projects_type")

    # Drop tables (in reverse order of creation due to foreign keys)
    op.drop_table('research_funding')
    op.drop_table('consultancies')
    op.drop_table('extension_activities')
    op.drop_table('hackathons')
    op.drop_table('innovation_cells')
    op.drop_table('startups')
    op.drop_table('patents')
    op.drop_table('publications')
    op.drop_table('research_projects')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS fundingagency")
    op.execute("DROP TYPE IF EXISTS extensiontype")
    op.execute("DROP TYPE IF EXISTS eventtype")
    op.execute("DROP TYPE IF EXISTS startupstatus")
    op.execute("DROP TYPE IF EXISTS startupstage")
    op.execute("DROP TYPE IF EXISTS patenttype")
    op.execute("DROP TYPE IF EXISTS patentstatus")
    op.execute("DROP TYPE IF EXISTS publicationindexing")
    op.execute("DROP TYPE IF EXISTS publicationtype")
    op.execute("DROP TYPE IF EXISTS researchprojectstatus")
    op.execute("DROP TYPE IF EXISTS projecttype")
