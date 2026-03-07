"""Add NAAC Criterion 5 tables

Revision ID: criterion5_001
Revises: criterion4_001
Create Date: 2026-02-25

Tables created:
- scholarships: Scholarship Records
- placement_records: Placement Records
- career_counseling: Career Counseling Sessions
- student_grievances: Student Grievances
- alumni_records: Alumni Records
- student_mentoring: Student Mentoring Records
- competitive_exams: Competitive Exam Records
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'criterion5_001'
down_revision = 'criterion4_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (IF NOT EXISTS for idempotency)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE scholarshiptype AS ENUM ('government', 'institutional', 'private', 'corporate', 'merit', 'need_based', 'sc_st', 'obc', 'minority', 'sports', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE placementstatus AS ENUM ('placed', 'higher_studies', 'entrepreneur', 'unplaced', 'not_interested');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE companytype AS ENUM ('mnc', 'startup', 'psu', 'government', 'private', 'dream', 'super_dream');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE grievancecategory AS ENUM ('academic', 'hostel', 'transportation', 'ragging', 'harassment', 'financial', 'infrastructure', 'faculty', 'examination', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE grievancestatus AS ENUM ('submitted', 'under_review', 'in_progress', 'resolved', 'closed', 'escalated');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE alumnistatus AS ENUM ('active', 'inactive', 'verified', 'unverified');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create scholarships table
    op.execute("""
        CREATE TABLE IF NOT EXISTS scholarships (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            scholarship_name VARCHAR(500) NOT NULL,
            scholarship_type scholarshiptype NOT NULL,
            awarding_body VARCHAR(255) NOT NULL,
            student_name VARCHAR(255) NOT NULL,
            student_usn VARCHAR(50) NOT NULL,
            department VARCHAR(255) NOT NULL,
            semester INTEGER,
            academic_year VARCHAR(20) NOT NULL,
            amount FLOAT NOT NULL,
            amount_received FLOAT,
            application_date DATE,
            sanction_date DATE,
            disbursement_date DATE,
            is_disbursed BOOLEAN DEFAULT FALSE,
            bank_details JSONB,
            sanction_letter_path VARCHAR(500),
            receipt_path VARCHAR(500),
            remarks TEXT,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create placement_records table
    op.execute("""
        CREATE TABLE IF NOT EXISTS placement_records (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            student_name VARCHAR(255) NOT NULL,
            student_usn VARCHAR(50) NOT NULL,
            student_email VARCHAR(255),
            student_phone VARCHAR(50),
            department VARCHAR(255) NOT NULL,
            batch VARCHAR(50) NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            status placementstatus NOT NULL,
            company_name VARCHAR(255),
            company_type companytype,
            job_role VARCHAR(255),
            job_location VARCHAR(255),
            package_lpa FLOAT,
            offer_date DATE,
            joining_date DATE,
            higher_study_institution VARCHAR(500),
            higher_study_course VARCHAR(255),
            higher_study_country VARCHAR(100),
            startup_name VARCHAR(255),
            startup_domain VARCHAR(255),
            offer_letter_path VARCHAR(500),
            joining_letter_path VARCHAR(500),
            is_verified BOOLEAN DEFAULT FALSE,
            verified_by VARCHAR(255),
            verified_at TIMESTAMP,
            remarks TEXT,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create career_counseling table
    op.execute("""
        CREATE TABLE IF NOT EXISTS career_counseling (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            session_type VARCHAR(100) NOT NULL,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            session_date DATE NOT NULL,
            start_time VARCHAR(10),
            end_time VARCHAR(10),
            duration_hours FLOAT,
            venue VARCHAR(255),
            mode VARCHAR(50),
            department VARCHAR(255),
            academic_year VARCHAR(20) NOT NULL,
            target_audience VARCHAR(255),
            resource_person VARCHAR(255),
            resource_person_designation VARCHAR(255),
            resource_person_organization VARCHAR(255),
            topics_covered JSONB,
            students_attended INTEGER DEFAULT 0,
            feedback_received INTEGER DEFAULT 0,
            average_rating FLOAT,
            outcomes JSONB,
            brochure_path VARCHAR(500),
            attendance_path VARCHAR(500),
            report_path VARCHAR(500),
            photos_path VARCHAR(500),
            remarks TEXT,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create student_grievances table
    op.execute("""
        CREATE TABLE IF NOT EXISTS student_grievances (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            grievance_number VARCHAR(50) NOT NULL UNIQUE,
            student_name VARCHAR(255) NOT NULL,
            student_usn VARCHAR(50),
            student_email VARCHAR(255),
            student_phone VARCHAR(50),
            department VARCHAR(255) NOT NULL,
            semester INTEGER,
            category grievancecategory NOT NULL,
            subject VARCHAR(500) NOT NULL,
            description TEXT NOT NULL,
            is_anonymous BOOLEAN DEFAULT FALSE,
            status grievancestatus DEFAULT 'submitted',
            submitted_date DATE NOT NULL,
            assigned_to VARCHAR(255),
            assigned_date DATE,
            action_taken TEXT,
            resolution_notes TEXT,
            resolved_date DATE,
            resolution_days INTEGER,
            satisfaction_rating INTEGER,
            attachment_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create alumni_records table
    op.execute("""
        CREATE TABLE IF NOT EXISTS alumni_records (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            name VARCHAR(255) NOT NULL,
            usn VARCHAR(50),
            email VARCHAR(255),
            phone VARCHAR(50),
            department VARCHAR(255) NOT NULL,
            batch VARCHAR(50) NOT NULL,
            graduation_year INTEGER NOT NULL,
            degree VARCHAR(100),
            current_organization VARCHAR(500),
            current_designation VARCHAR(255),
            current_location VARCHAR(255),
            linkedin_url VARCHAR(500),
            industry_sector VARCHAR(255),
            experience_years INTEGER,
            is_entrepreneur BOOLEAN DEFAULT FALSE,
            company_founded VARCHAR(255),
            achievements JSONB,
            contributions_to_institution JSONB,
            is_donor BOOLEAN DEFAULT FALSE,
            donation_amount FLOAT,
            profile_photo_path VARCHAR(500),
            status alumnistatus DEFAULT 'unverified',
            is_active BOOLEAN DEFAULT TRUE,
            last_updated TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create student_mentoring table
    op.execute("""
        CREATE TABLE IF NOT EXISTS student_mentoring (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            mentor_name VARCHAR(255) NOT NULL,
            mentor_designation VARCHAR(100),
            mentor_email VARCHAR(255),
            mentor_department VARCHAR(255) NOT NULL,
            student_name VARCHAR(255) NOT NULL,
            student_usn VARCHAR(50) NOT NULL,
            student_email VARCHAR(255),
            student_department VARCHAR(255) NOT NULL,
            semester INTEGER,
            academic_year VARCHAR(20) NOT NULL,
            sessions JSONB,
            total_sessions INTEGER DEFAULT 0,
            academic_progress TEXT,
            attendance_percentage FLOAT,
            cgpa FLOAT,
            backlogs INTEGER,
            career_guidance_provided BOOLEAN DEFAULT FALSE,
            counseling_required BOOLEAN DEFAULT FALSE,
            parent_interaction JSONB,
            mentoring_report_path VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create competitive_exams table
    op.execute("""
        CREATE TABLE IF NOT EXISTS competitive_exams (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            student_name VARCHAR(255) NOT NULL,
            student_usn VARCHAR(50) NOT NULL,
            student_email VARCHAR(255),
            department VARCHAR(255) NOT NULL,
            batch VARCHAR(50) NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            exam_name VARCHAR(255) NOT NULL,
            exam_type VARCHAR(100),
            exam_date DATE,
            registration_number VARCHAR(100),
            result_status VARCHAR(50),
            score FLOAT,
            percentile FLOAT,
            rank INTEGER,
            is_qualified BOOLEAN DEFAULT FALSE,
            admission_secured BOOLEAN DEFAULT FALSE,
            institution_admitted VARCHAR(500),
            course_admitted VARCHAR(255),
            scorecard_path VARCHAR(500),
            admit_card_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create indexes for scholarships
    op.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_type ON scholarships(scholarship_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_department ON scholarships(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_scholarships_academic_year ON scholarships(academic_year)")

    # Create indexes for placement_records
    op.execute("CREATE INDEX IF NOT EXISTS ix_placement_records_status ON placement_records(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_placement_records_department ON placement_records(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_placement_records_batch ON placement_records(batch)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_placement_records_academic_year ON placement_records(academic_year)")

    # Create indexes for career_counseling
    op.execute("CREATE INDEX IF NOT EXISTS ix_career_counseling_date ON career_counseling(session_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_career_counseling_department ON career_counseling(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_career_counseling_academic_year ON career_counseling(academic_year)")

    # Create indexes for student_grievances
    op.execute("CREATE INDEX IF NOT EXISTS ix_student_grievances_category ON student_grievances(category)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_student_grievances_status ON student_grievances(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_student_grievances_department ON student_grievances(department)")

    # Create indexes for alumni_records
    op.execute("CREATE INDEX IF NOT EXISTS ix_alumni_records_department ON alumni_records(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alumni_records_batch ON alumni_records(batch)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alumni_records_graduation_year ON alumni_records(graduation_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_alumni_records_status ON alumni_records(status)")

    # Create indexes for student_mentoring
    op.execute("CREATE INDEX IF NOT EXISTS ix_student_mentoring_mentor ON student_mentoring(mentor_name)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_student_mentoring_department ON student_mentoring(student_department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_student_mentoring_academic_year ON student_mentoring(academic_year)")

    # Create indexes for competitive_exams
    op.execute("CREATE INDEX IF NOT EXISTS ix_competitive_exams_exam ON competitive_exams(exam_name)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_competitive_exams_department ON competitive_exams(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_competitive_exams_academic_year ON competitive_exams(academic_year)")


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_competitive_exams_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_competitive_exams_department")
    op.execute("DROP INDEX IF EXISTS ix_competitive_exams_exam")
    op.execute("DROP INDEX IF EXISTS ix_student_mentoring_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_student_mentoring_department")
    op.execute("DROP INDEX IF EXISTS ix_student_mentoring_mentor")
    op.execute("DROP INDEX IF EXISTS ix_alumni_records_status")
    op.execute("DROP INDEX IF EXISTS ix_alumni_records_graduation_year")
    op.execute("DROP INDEX IF EXISTS ix_alumni_records_batch")
    op.execute("DROP INDEX IF EXISTS ix_alumni_records_department")
    op.execute("DROP INDEX IF EXISTS ix_student_grievances_department")
    op.execute("DROP INDEX IF EXISTS ix_student_grievances_status")
    op.execute("DROP INDEX IF EXISTS ix_student_grievances_category")
    op.execute("DROP INDEX IF EXISTS ix_career_counseling_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_career_counseling_department")
    op.execute("DROP INDEX IF EXISTS ix_career_counseling_date")
    op.execute("DROP INDEX IF EXISTS ix_placement_records_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_placement_records_batch")
    op.execute("DROP INDEX IF EXISTS ix_placement_records_department")
    op.execute("DROP INDEX IF EXISTS ix_placement_records_status")
    op.execute("DROP INDEX IF EXISTS ix_scholarships_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_scholarships_department")
    op.execute("DROP INDEX IF EXISTS ix_scholarships_type")

    # Drop tables
    op.drop_table('competitive_exams')
    op.drop_table('student_mentoring')
    op.drop_table('alumni_records')
    op.drop_table('student_grievances')
    op.drop_table('career_counseling')
    op.drop_table('placement_records')
    op.drop_table('scholarships')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS alumnistatus")
    op.execute("DROP TYPE IF EXISTS grievancestatus")
    op.execute("DROP TYPE IF EXISTS grievancecategory")
    op.execute("DROP TYPE IF EXISTS companytype")
    op.execute("DROP TYPE IF EXISTS placementstatus")
    op.execute("DROP TYPE IF EXISTS scholarshiptype")
