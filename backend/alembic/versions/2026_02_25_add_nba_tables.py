"""Add NBA Accreditation tables

Revision ID: nba_001
Revises: criterion7_001
Create Date: 2026-02-25

Tables created:
- program_vision_mission: Program Vision/Mission and PEOs
- program_outcomes: Program Outcomes (POs)
- course_outcomes: Course Outcomes (COs)
- co_attainment: CO Attainment Records
- po_attainment: PO Attainment Records
- student_result_analysis: Student Result Analysis
- nba_continuous_improvement: Continuous Improvement Actions
- nba_faculty_contribution: Faculty Contributions
- nba_lab_facilities: Lab Facilities for NBA
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'nba_001'
down_revision = 'criterion7_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (IF NOT EXISTS for idempotency)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE programtype AS ENUM ('ug', 'pg', 'diploma', 'phd');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE attainmentlevel AS ENUM ('level_1', 'level_2', 'level_3', 'not_attained');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE assessmentmethod AS ENUM ('direct', 'indirect');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE feedbacksource AS ENUM ('student', 'alumni', 'employer', 'parent', 'faculty', 'industry');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE actionstatus AS ENUM ('planned', 'in_progress', 'completed', 'deferred');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create program_vision_mission table
    op.execute("""
        CREATE TABLE IF NOT EXISTS program_vision_mission (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            program_name VARCHAR(255) NOT NULL,
            program_code VARCHAR(50) NOT NULL,
            program_type programtype NOT NULL,
            department VARCHAR(255) NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            vision_statement TEXT NOT NULL,
            mission_statements JSONB NOT NULL,
            peos JSONB NOT NULL,
            psos JSONB,
            peo_pso_mapping JSONB,
            stakeholder_consultation JSONB,
            review_history JSONB,
            document_path VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create program_outcomes table
    op.execute("""
        CREATE TABLE IF NOT EXISTS program_outcomes (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            program_id VARCHAR(36) NOT NULL REFERENCES program_vision_mission(id) ON DELETE CASCADE,
            po_number VARCHAR(10) NOT NULL,
            po_statement TEXT NOT NULL,
            bloom_level VARCHAR(50),
            nba_graduate_attribute VARCHAR(255),
            peo_mapping JSONB,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create course_outcomes table
    op.execute("""
        CREATE TABLE IF NOT EXISTS course_outcomes (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            course_code VARCHAR(50) NOT NULL,
            course_name VARCHAR(255) NOT NULL,
            program_id VARCHAR(36) NOT NULL REFERENCES program_vision_mission(id) ON DELETE CASCADE,
            semester INTEGER NOT NULL,
            co_number VARCHAR(10) NOT NULL,
            co_statement TEXT NOT NULL,
            bloom_level VARCHAR(50) NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            po_mapping JSONB,
            pso_mapping JSONB,
            teaching_methods JSONB,
            assessment_methods JSONB,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create co_attainment table
    op.execute("""
        CREATE TABLE IF NOT EXISTS co_attainment (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            course_outcome_id VARCHAR(36) NOT NULL REFERENCES course_outcomes(id) ON DELETE CASCADE,
            course_code VARCHAR(50) NOT NULL,
            co_number VARCHAR(10) NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            semester INTEGER NOT NULL,
            batch VARCHAR(50) NOT NULL,
            section VARCHAR(10),
            direct_attainment FLOAT,
            indirect_attainment FLOAT,
            overall_attainment FLOAT,
            attainment_level attainmentlevel,
            target_attainment FLOAT,
            cie_attainment FLOAT,
            see_attainment FLOAT,
            assignment_attainment FLOAT,
            quiz_attainment FLOAT,
            lab_attainment FLOAT,
            survey_attainment FLOAT,
            students_above_target INTEGER,
            total_students INTEGER,
            gap_analysis TEXT,
            action_taken TEXT,
            evidence_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create po_attainment table
    op.execute("""
        CREATE TABLE IF NOT EXISTS po_attainment (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            program_id VARCHAR(36) NOT NULL REFERENCES program_vision_mission(id) ON DELETE CASCADE,
            po_number VARCHAR(10) NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            batch VARCHAR(50) NOT NULL,
            direct_attainment FLOAT,
            indirect_attainment FLOAT,
            overall_attainment FLOAT,
            attainment_level attainmentlevel,
            target_attainment FLOAT,
            course_contributions JSONB,
            co_po_matrix JSONB,
            alumni_feedback_score FLOAT,
            employer_feedback_score FLOAT,
            exit_survey_score FLOAT,
            gap_analysis TEXT,
            improvement_actions JSONB,
            evidence_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create student_result_analysis table
    op.execute("""
        CREATE TABLE IF NOT EXISTS student_result_analysis (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            program_id VARCHAR(36) NOT NULL REFERENCES program_vision_mission(id) ON DELETE CASCADE,
            course_code VARCHAR(50) NOT NULL,
            course_name VARCHAR(255) NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            semester INTEGER NOT NULL,
            batch VARCHAR(50) NOT NULL,
            section VARCHAR(10),
            exam_type VARCHAR(50),
            total_students INTEGER NOT NULL,
            students_appeared INTEGER DEFAULT 0,
            students_passed INTEGER DEFAULT 0,
            pass_percentage FLOAT,
            average_marks FLOAT,
            highest_marks FLOAT,
            lowest_marks FLOAT,
            grade_distribution JSONB,
            distinction_count INTEGER DEFAULT 0,
            first_class_count INTEGER DEFAULT 0,
            second_class_count INTEGER DEFAULT 0,
            failed_count INTEGER DEFAULT 0,
            absent_count INTEGER DEFAULT 0,
            co_wise_analysis JSONB,
            question_wise_analysis JSONB,
            result_sheet_path VARCHAR(500),
            remarks TEXT,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create nba_continuous_improvement table
    op.execute("""
        CREATE TABLE IF NOT EXISTS nba_continuous_improvement (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            program_id VARCHAR(36) NOT NULL REFERENCES program_vision_mission(id) ON DELETE CASCADE,
            academic_year VARCHAR(20) NOT NULL,
            improvement_area VARCHAR(255) NOT NULL,
            issue_identified TEXT NOT NULL,
            source_of_identification VARCHAR(255),
            po_affected JSONB,
            co_affected JSONB,
            action_planned TEXT,
            action_taken TEXT,
            resources_required JSONB,
            responsible_person VARCHAR(255),
            target_date DATE,
            completion_date DATE,
            status actionstatus DEFAULT 'planned',
            outcome TEXT,
            impact_on_attainment TEXT,
            evidence_path VARCHAR(500),
            next_review_date DATE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create nba_faculty_contribution table
    op.execute("""
        CREATE TABLE IF NOT EXISTS nba_faculty_contribution (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            program_id VARCHAR(36) NOT NULL REFERENCES program_vision_mission(id) ON DELETE CASCADE,
            faculty_name VARCHAR(255) NOT NULL,
            faculty_id VARCHAR(50),
            faculty_email VARCHAR(255),
            designation VARCHAR(100),
            academic_year VARCHAR(20) NOT NULL,
            qualification VARCHAR(255),
            experience_years INTEGER,
            courses_taught JSONB,
            average_result FLOAT,
            co_attainment_average FLOAT,
            publications_count INTEGER DEFAULT 0,
            fdps_attended INTEGER DEFAULT 0,
            certifications JSONB,
            industry_experience INTEGER DEFAULT 0,
            projects_guided INTEGER DEFAULT 0,
            research_projects INTEGER DEFAULT 0,
            consultancy_amount FLOAT,
            professional_memberships JSONB,
            awards JSONB,
            resume_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create nba_lab_facilities table
    op.execute("""
        CREATE TABLE IF NOT EXISTS nba_lab_facilities (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            program_id VARCHAR(36) NOT NULL REFERENCES program_vision_mission(id) ON DELETE CASCADE,
            lab_name VARCHAR(255) NOT NULL,
            lab_code VARCHAR(50),
            lab_type VARCHAR(100),
            location VARCHAR(255),
            area_sqft FLOAT,
            established_year INTEGER,
            equipment_list JSONB,
            software_available JSONB,
            total_equipment_value FLOAT,
            seating_capacity INTEGER,
            courses_supported JSONB,
            cos_addressed JSONB,
            pos_addressed JSONB,
            utilization_percentage FLOAT,
            weekly_hours FLOAT,
            maintenance_budget FLOAT,
            last_upgrade_date DATE,
            layout_path VARCHAR(500),
            photos_path VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_program_vision_mission_program_code ON program_vision_mission(program_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_program_vision_mission_department ON program_vision_mission(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_program_vision_mission_academic_year ON program_vision_mission(academic_year)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_program_outcomes_program_id ON program_outcomes(program_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_program_outcomes_po_number ON program_outcomes(po_number)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_course_outcomes_program_id ON course_outcomes(program_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_course_outcomes_course_code ON course_outcomes(course_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_course_outcomes_semester ON course_outcomes(semester)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_course_outcomes_academic_year ON course_outcomes(academic_year)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_co_attainment_course_outcome_id ON co_attainment(course_outcome_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_co_attainment_course_code ON co_attainment(course_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_co_attainment_academic_year ON co_attainment(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_co_attainment_batch ON co_attainment(batch)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_po_attainment_program_id ON po_attainment(program_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_po_attainment_po_number ON po_attainment(po_number)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_po_attainment_academic_year ON po_attainment(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_po_attainment_batch ON po_attainment(batch)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_student_result_analysis_program_id ON student_result_analysis(program_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_student_result_analysis_course_code ON student_result_analysis(course_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_student_result_analysis_academic_year ON student_result_analysis(academic_year)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_nba_continuous_improvement_program_id ON nba_continuous_improvement(program_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_nba_continuous_improvement_status ON nba_continuous_improvement(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_nba_continuous_improvement_academic_year ON nba_continuous_improvement(academic_year)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_nba_faculty_contribution_program_id ON nba_faculty_contribution(program_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_nba_faculty_contribution_academic_year ON nba_faculty_contribution(academic_year)")

    op.execute("CREATE INDEX IF NOT EXISTS ix_nba_lab_facilities_program_id ON nba_lab_facilities(program_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_nba_lab_facilities_active ON nba_lab_facilities(is_active)")


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_nba_lab_facilities_active")
    op.execute("DROP INDEX IF EXISTS ix_nba_lab_facilities_program_id")
    op.execute("DROP INDEX IF EXISTS ix_nba_faculty_contribution_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_nba_faculty_contribution_program_id")
    op.execute("DROP INDEX IF EXISTS ix_nba_continuous_improvement_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_nba_continuous_improvement_status")
    op.execute("DROP INDEX IF EXISTS ix_nba_continuous_improvement_program_id")
    op.execute("DROP INDEX IF EXISTS ix_student_result_analysis_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_student_result_analysis_course_code")
    op.execute("DROP INDEX IF EXISTS ix_student_result_analysis_program_id")
    op.execute("DROP INDEX IF EXISTS ix_po_attainment_batch")
    op.execute("DROP INDEX IF EXISTS ix_po_attainment_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_po_attainment_po_number")
    op.execute("DROP INDEX IF EXISTS ix_po_attainment_program_id")
    op.execute("DROP INDEX IF EXISTS ix_co_attainment_batch")
    op.execute("DROP INDEX IF EXISTS ix_co_attainment_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_co_attainment_course_code")
    op.execute("DROP INDEX IF EXISTS ix_co_attainment_course_outcome_id")
    op.execute("DROP INDEX IF EXISTS ix_course_outcomes_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_course_outcomes_semester")
    op.execute("DROP INDEX IF EXISTS ix_course_outcomes_course_code")
    op.execute("DROP INDEX IF EXISTS ix_course_outcomes_program_id")
    op.execute("DROP INDEX IF EXISTS ix_program_outcomes_po_number")
    op.execute("DROP INDEX IF EXISTS ix_program_outcomes_program_id")
    op.execute("DROP INDEX IF EXISTS ix_program_vision_mission_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_program_vision_mission_department")
    op.execute("DROP INDEX IF EXISTS ix_program_vision_mission_program_code")

    # Drop tables (in reverse order due to foreign keys)
    op.drop_table('nba_lab_facilities')
    op.drop_table('nba_faculty_contribution')
    op.drop_table('nba_continuous_improvement')
    op.drop_table('student_result_analysis')
    op.drop_table('po_attainment')
    op.drop_table('co_attainment')
    op.drop_table('course_outcomes')
    op.drop_table('program_outcomes')
    op.drop_table('program_vision_mission')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS actionstatus")
    op.execute("DROP TYPE IF EXISTS feedbacksource")
    op.execute("DROP TYPE IF EXISTS assessmentmethod")
    op.execute("DROP TYPE IF EXISTS attainmentlevel")
    op.execute("DROP TYPE IF EXISTS programtype")
