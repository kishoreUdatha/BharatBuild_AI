"""Add NAAC Criterion 1 tables

Revision ID: criterion1_001
Revises: add_owner_name_coupons
Create Date: 2026-02-25

Tables created:
- curriculum_feedback: Feedback from students, alumni, employers, teachers
- curriculum_evidence: Evidence documents for NAAC compliance
- industry_partners: MoUs and industry collaborations
- advisory_board_meetings: IAB/BOG meeting records
- value_added_courses: Skill certification programs
- value_added_course_enrollments: Student enrollments in value-added courses
- internship_records: Internship tracking
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'criterion1_001'
down_revision = 'add_owner_name_coupons'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (IF NOT EXISTS for idempotency)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE feedbacktype AS ENUM ('student', 'alumni', 'employer', 'teacher', 'industry_expert', 'parent');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE feedbackstatus AS ENUM ('pending', 'reviewed', 'action_taken', 'closed');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE evidencetype AS ENUM ('syllabus', 'co_po_matrix', 'mou', 'feedback_report', 'meeting_minutes', 'course_file', 'attainment_report', 'curriculum_revision', 'board_resolution', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE partnertype AS ENUM ('corporate', 'startup', 'government', 'research_institution', 'ngo', 'professional_body');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE moustatus AS ENUM ('draft', 'active', 'expired', 'renewed', 'terminated');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE coursetype AS ENUM ('skill_development', 'soft_skills', 'language', 'ict', 'employability', 'entrepreneurship', 'certification', 'bridge_course');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE coursemode AS ENUM ('offline', 'online', 'hybrid');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE internshiptype AS ENUM ('industry', 'research', 'government', 'ngo', 'startup', 'international');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE internshipstatus AS ENUM ('ongoing', 'completed', 'withdrawn');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create curriculum_feedback table
    op.execute("""
        CREATE TABLE IF NOT EXISTS curriculum_feedback (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            feedback_type feedbacktype NOT NULL,
            respondent_name VARCHAR(255),
            respondent_email VARCHAR(255),
            respondent_organization VARCHAR(255),
            respondent_designation VARCHAR(255),
            department VARCHAR(255) NOT NULL,
            program VARCHAR(255),
            course_code VARCHAR(50),
            course_name VARCHAR(255),
            academic_year VARCHAR(20) NOT NULL,
            semester INTEGER,
            feedback_content TEXT NOT NULL,
            rating INTEGER,
            suggestions TEXT,
            structured_responses JSONB,
            status feedbackstatus DEFAULT 'pending',
            reviewed_by VARCHAR(255),
            reviewed_at TIMESTAMP,
            action_taken TEXT,
            action_date TIMESTAMP,
            action_evidence VARCHAR(500),
            submitted_at TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create curriculum_evidence table
    op.execute("""
        CREATE TABLE IF NOT EXISTS curriculum_evidence (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            evidence_type evidencetype NOT NULL,
            key_indicator VARCHAR(10) NOT NULL,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            file_path VARCHAR(500) NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            file_size INTEGER,
            file_type VARCHAR(50),
            department VARCHAR(255),
            program VARCHAR(255),
            course_code VARCHAR(50),
            academic_year VARCHAR(20) NOT NULL,
            is_verified BOOLEAN DEFAULT FALSE,
            verified_by VARCHAR(255),
            verified_at TIMESTAMP,
            verification_remarks TEXT,
            uploaded_by VARCHAR(255) NOT NULL,
            metadata JSONB,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create industry_partners table
    op.execute("""
        CREATE TABLE IF NOT EXISTS industry_partners (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            name VARCHAR(500) NOT NULL,
            partner_type partnertype NOT NULL,
            industry_sector VARCHAR(255),
            website VARCHAR(500),
            contact_person VARCHAR(255),
            contact_email VARCHAR(255),
            contact_phone VARCHAR(50),
            address TEXT,
            mou_number VARCHAR(100),
            mou_status moustatus DEFAULT 'draft',
            mou_signed_date DATE,
            mou_expiry_date DATE,
            mou_document_path VARCHAR(500),
            department VARCHAR(255),
            collaboration_areas JSONB,
            activities_conducted JSONB,
            students_benefited INTEGER DEFAULT 0,
            projects_completed INTEGER DEFAULT 0,
            placements_provided INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create advisory_board_meetings table
    op.execute("""
        CREATE TABLE IF NOT EXISTS advisory_board_meetings (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            title VARCHAR(500) NOT NULL,
            meeting_type VARCHAR(50) NOT NULL,
            meeting_date DATE NOT NULL,
            venue VARCHAR(255),
            department VARCHAR(255),
            academic_year VARCHAR(20) NOT NULL,
            partner_id VARCHAR(36) REFERENCES industry_partners(id) ON DELETE SET NULL,
            attendees JSONB,
            external_experts JSONB,
            agenda TEXT,
            minutes TEXT,
            resolutions JSONB,
            minutes_document_path VARCHAR(500),
            attendance_sheet_path VARCHAR(500),
            action_items JSONB,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create value_added_courses table
    op.execute("""
        CREATE TABLE IF NOT EXISTS value_added_courses (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            course_name VARCHAR(500) NOT NULL,
            course_code VARCHAR(50),
            course_type coursetype NOT NULL,
            course_mode coursemode DEFAULT 'offline',
            department VARCHAR(255) NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            semester INTEGER,
            description TEXT,
            objectives JSONB,
            outcomes JSONB,
            duration_hours INTEGER NOT NULL,
            credits FLOAT,
            co_po_mapping JSONB,
            instructor_name VARCHAR(255),
            instructor_qualification VARCHAR(255),
            instructor_organization VARCHAR(255),
            start_date DATE,
            end_date DATE,
            schedule JSONB,
            max_enrollment INTEGER,
            current_enrollment INTEGER DEFAULT 0,
            completed_count INTEGER DEFAULT 0,
            certification_provided BOOLEAN DEFAULT FALSE,
            certifying_body VARCHAR(255),
            syllabus_path VARCHAR(500),
            materials_path VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create value_added_course_enrollments table
    op.execute("""
        CREATE TABLE IF NOT EXISTS value_added_course_enrollments (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            course_id VARCHAR(36) NOT NULL REFERENCES value_added_courses(id) ON DELETE CASCADE,
            student_id VARCHAR(50) NOT NULL,
            student_name VARCHAR(255) NOT NULL,
            student_email VARCHAR(255),
            department VARCHAR(255),
            batch VARCHAR(20),
            enrollment_date DATE NOT NULL,
            status VARCHAR(50) DEFAULT 'enrolled',
            completion_date DATE,
            grade VARCHAR(10),
            score FLOAT,
            certificate_issued BOOLEAN DEFAULT FALSE,
            certificate_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create internship_records table
    op.execute("""
        CREATE TABLE IF NOT EXISTS internship_records (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            student_id VARCHAR(50) NOT NULL,
            student_name VARCHAR(255) NOT NULL,
            student_email VARCHAR(255),
            department VARCHAR(255) NOT NULL,
            batch VARCHAR(20),
            semester INTEGER,
            academic_year VARCHAR(20) NOT NULL,
            internship_type internshiptype NOT NULL,
            company_name VARCHAR(500) NOT NULL,
            company_website VARCHAR(500),
            industry_sector VARCHAR(255),
            location VARCHAR(255),
            is_remote BOOLEAN DEFAULT FALSE,
            start_date DATE NOT NULL,
            end_date DATE,
            duration_weeks INTEGER,
            role_title VARCHAR(255),
            project_title VARCHAR(500),
            project_description TEXT,
            skills_used JSONB,
            company_mentor VARCHAR(255),
            faculty_mentor VARCHAR(255),
            is_paid BOOLEAN DEFAULT FALSE,
            stipend_amount FLOAT,
            stipend_currency VARCHAR(10) DEFAULT 'INR',
            status internshipstatus DEFAULT 'ongoing',
            ppo_offered BOOLEAN DEFAULT FALSE,
            converted_to_job BOOLEAN DEFAULT FALSE,
            performance_rating FLOAT,
            feedback TEXT,
            offer_letter_path VARCHAR(500),
            completion_certificate_path VARCHAR(500),
            report_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_curriculum_feedback_type ON curriculum_feedback(feedback_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_curriculum_feedback_status ON curriculum_feedback(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_curriculum_feedback_academic_year ON curriculum_feedback(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_curriculum_feedback_department ON curriculum_feedback(department)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_curriculum_evidence_type ON curriculum_evidence(evidence_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_curriculum_evidence_key_indicator ON curriculum_evidence(key_indicator)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_curriculum_evidence_academic_year ON curriculum_evidence(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_curriculum_evidence_verified ON curriculum_evidence(is_verified)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_industry_partners_type ON industry_partners(partner_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_industry_partners_status ON industry_partners(mou_status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_industry_partners_department ON industry_partners(department)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_advisory_board_meetings_date ON advisory_board_meetings(meeting_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_advisory_board_meetings_type ON advisory_board_meetings(meeting_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_advisory_board_meetings_department ON advisory_board_meetings(department)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_value_added_courses_type ON value_added_courses(course_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_value_added_courses_academic_year ON value_added_courses(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_value_added_courses_department ON value_added_courses(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_value_added_courses_status ON value_added_courses(is_active)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_vac_enrollments_course_id ON value_added_course_enrollments(course_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_vac_enrollments_student_id ON value_added_course_enrollments(student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_vac_enrollments_status ON value_added_course_enrollments(status)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_internship_records_type ON internship_records(internship_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_internship_records_status ON internship_records(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_internship_records_department ON internship_records(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_internship_records_academic_year ON internship_records(academic_year)")


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_internship_records_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_internship_records_department")
    op.execute("DROP INDEX IF EXISTS ix_internship_records_status")
    op.execute("DROP INDEX IF EXISTS ix_internship_records_type")

    op.execute("DROP INDEX IF EXISTS ix_vac_enrollments_status")
    op.execute("DROP INDEX IF EXISTS ix_vac_enrollments_student_id")
    op.execute("DROP INDEX IF EXISTS ix_vac_enrollments_course_id")

    op.execute("DROP INDEX IF EXISTS ix_value_added_courses_status")
    op.execute("DROP INDEX IF EXISTS ix_value_added_courses_department")
    op.execute("DROP INDEX IF EXISTS ix_value_added_courses_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_value_added_courses_type")

    op.execute("DROP INDEX IF EXISTS ix_advisory_board_meetings_department")
    op.execute("DROP INDEX IF EXISTS ix_advisory_board_meetings_type")
    op.execute("DROP INDEX IF EXISTS ix_advisory_board_meetings_date")

    op.execute("DROP INDEX IF EXISTS ix_industry_partners_department")
    op.execute("DROP INDEX IF EXISTS ix_industry_partners_status")
    op.execute("DROP INDEX IF EXISTS ix_industry_partners_type")

    op.execute("DROP INDEX IF EXISTS ix_curriculum_evidence_verified")
    op.execute("DROP INDEX IF EXISTS ix_curriculum_evidence_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_curriculum_evidence_key_indicator")
    op.execute("DROP INDEX IF EXISTS ix_curriculum_evidence_type")

    op.execute("DROP INDEX IF EXISTS ix_curriculum_feedback_department")
    op.execute("DROP INDEX IF EXISTS ix_curriculum_feedback_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_curriculum_feedback_status")
    op.execute("DROP INDEX IF EXISTS ix_curriculum_feedback_type")

    # Drop tables
    op.drop_table('internship_records')
    op.drop_table('value_added_course_enrollments')
    op.drop_table('value_added_courses')
    op.drop_table('advisory_board_meetings')
    op.drop_table('industry_partners')
    op.drop_table('curriculum_evidence')
    op.drop_table('curriculum_feedback')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS internshipstatus")
    op.execute("DROP TYPE IF EXISTS internshiptype")
    op.execute("DROP TYPE IF EXISTS coursemode")
    op.execute("DROP TYPE IF EXISTS coursetype")
    op.execute("DROP TYPE IF EXISTS moustatus")
    op.execute("DROP TYPE IF EXISTS partnertype")
    op.execute("DROP TYPE IF EXISTS evidencetype")
    op.execute("DROP TYPE IF EXISTS feedbackstatus")
    op.execute("DROP TYPE IF EXISTS feedbacktype")
