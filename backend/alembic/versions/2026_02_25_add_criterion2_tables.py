"""Add NAAC Criterion 2 tables

Revision ID: criterion2_001
Revises: criterion1_001
Create Date: 2026-02-25

Tables created:
- lms_adoption: LMS platform usage tracking
- lesson_plans: Lesson plans with Bloom's Taxonomy
- attendance_records: Student attendance tracking
- cie_records: Continuous Internal Evaluation
- evaluation_rubrics: Rubrics-based assessment
- student_performance: Student performance analytics
- teacher_profiles: Teacher quality tracking
- digital_contents: Digital learning resources
- learning_outcome_attainments: CO/PO attainment tracking
- blended_learning_sessions: Blended learning tracking
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'criterion2_001'
down_revision = 'criterion1_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (IF NOT EXISTS for idempotency)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE lmsplatform AS ENUM ('moodle', 'google_classroom', 'microsoft_teams', 'canvas', 'blackboard', 'custom', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE bloomslevel AS ENUM ('L1_remember', 'L2_understand', 'L3_apply', 'L4_analyze', 'L5_evaluate', 'L6_create');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE attendancestatus AS ENUM ('present', 'absent', 'late', 'excused', 'on_duty');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE assessmenttype AS ENUM ('quiz', 'assignment', 'mid_term', 'end_term', 'project', 'presentation', 'lab', 'viva', 'seminar', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE teachingmethod AS ENUM ('lecture', 'flipped_classroom', 'project_based', 'problem_based', 'case_study', 'group_discussion', 'experiential', 'peer_learning', 'ict_enabled', 'blended', 'simulation', 'field_visit');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE contenttype AS ENUM ('video', 'pdf', 'ppt', 'interactive', 'simulation', 'e_book', 'mooc', 'quiz', 'animation', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE teacherdesignation AS ENUM ('professor', 'associate_professor', 'assistant_professor', 'lecturer', 'guest_faculty', 'adjunct_faculty', 'visiting_faculty');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE performancelevel AS ENUM ('outstanding', 'excellent', 'good', 'average', 'below_average', 'poor');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create lms_adoption table
    op.execute("""
        CREATE TABLE IF NOT EXISTS lms_adoption (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            platform lmsplatform NOT NULL,
            platform_name VARCHAR(255),
            platform_url VARCHAR(500),
            department VARCHAR(255) NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            total_courses INTEGER DEFAULT 0,
            active_courses INTEGER DEFAULT 0,
            total_faculty_registered INTEGER DEFAULT 0,
            total_students_registered INTEGER DEFAULT 0,
            active_users_monthly INTEGER DEFAULT 0,
            total_resources_uploaded INTEGER DEFAULT 0,
            total_assignments_created INTEGER DEFAULT 0,
            total_quizzes_created INTEGER DEFAULT 0,
            total_discussion_forums INTEGER DEFAULT 0,
            avg_login_frequency FLOAT,
            assignment_submission_rate FLOAT,
            quiz_completion_rate FLOAT,
            screenshots_path VARCHAR(500),
            usage_report_path VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create lesson_plans table
    op.execute("""
        CREATE TABLE IF NOT EXISTS lesson_plans (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            course_name VARCHAR(500) NOT NULL,
            course_code VARCHAR(50) NOT NULL,
            department VARCHAR(255) NOT NULL,
            program VARCHAR(255),
            semester INTEGER NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            credits INTEGER,
            faculty_name VARCHAR(255) NOT NULL,
            faculty_email VARCHAR(255),
            unit_number INTEGER,
            unit_name VARCHAR(500),
            topic VARCHAR(500) NOT NULL,
            subtopics JSONB,
            planned_hours FLOAT NOT NULL,
            actual_hours FLOAT,
            session_date DATE,
            learning_objectives JSONB,
            course_outcomes_mapped JSONB,
            blooms_levels JSONB,
            teaching_methods JSONB,
            teaching_aids JSONB,
            ict_tools_used JSONB,
            assessment_methods JSONB,
            assessment_blooms_level bloomslevel,
            reference_materials JSONB,
            additional_resources TEXT,
            is_completed BOOLEAN DEFAULT FALSE,
            completion_date DATE,
            remarks TEXT,
            document_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create attendance_records table
    op.execute("""
        CREATE TABLE IF NOT EXISTS attendance_records (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            student_id VARCHAR(50) NOT NULL,
            student_name VARCHAR(255) NOT NULL,
            department VARCHAR(255) NOT NULL,
            batch VARCHAR(20),
            semester INTEGER,
            course_code VARCHAR(50) NOT NULL,
            course_name VARCHAR(255) NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            attendance_date DATE NOT NULL,
            period INTEGER,
            status attendancestatus NOT NULL,
            marked_by VARCHAR(255),
            remarks VARCHAR(500),
            is_makeup_class BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create evaluation_rubrics table (before cie_records due to FK)
    op.execute("""
        CREATE TABLE IF NOT EXISTS evaluation_rubrics (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            course_code VARCHAR(50),
            course_name VARCHAR(255),
            department VARCHAR(255),
            academic_year VARCHAR(20),
            assessment_type assessmenttype,
            total_points FLOAT NOT NULL,
            criteria JSONB NOT NULL,
            performance_levels JSONB,
            course_outcomes_mapped JSONB,
            blooms_levels_covered JSONB,
            document_path VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            is_template BOOLEAN DEFAULT FALSE,
            created_by VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create cie_records table
    op.execute("""
        CREATE TABLE IF NOT EXISTS cie_records (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            student_id VARCHAR(50) NOT NULL,
            student_name VARCHAR(255) NOT NULL,
            department VARCHAR(255) NOT NULL,
            batch VARCHAR(20),
            semester INTEGER,
            course_code VARCHAR(50) NOT NULL,
            course_name VARCHAR(255) NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            assessment_type assessmenttype NOT NULL,
            assessment_name VARCHAR(255) NOT NULL,
            assessment_date DATE NOT NULL,
            max_marks FLOAT NOT NULL,
            marks_obtained FLOAT,
            percentage FLOAT,
            grade VARCHAR(10),
            course_outcomes_assessed JSONB,
            blooms_level bloomslevel,
            rubric_id VARCHAR(36) REFERENCES evaluation_rubrics(id) ON DELETE SET NULL,
            feedback TEXT,
            evaluated_by VARCHAR(255),
            evaluated_at TIMESTAMP,
            answer_sheet_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create student_performance table
    op.execute("""
        CREATE TABLE IF NOT EXISTS student_performance (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            student_id VARCHAR(50) NOT NULL,
            student_name VARCHAR(255) NOT NULL,
            department VARCHAR(255) NOT NULL,
            program VARCHAR(255),
            batch VARCHAR(20),
            semester INTEGER NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            sgpa FLOAT,
            cgpa FLOAT,
            total_credits_earned INTEGER DEFAULT 0,
            total_credits_attempted INTEGER DEFAULT 0,
            percentage FLOAT,
            performance_level performancelevel,
            course_performance JSONB,
            co_attainment JSONB,
            po_attainment JSONB,
            pso_attainment JSONB,
            overall_attendance_percentage FLOAT,
            average_cie_score FLOAT,
            cie_performance_trend JSONB,
            strengths JSONB,
            areas_for_improvement JSONB,
            mentor_name VARCHAR(255),
            mentor_remarks TEXT,
            is_passed BOOLEAN,
            backlogs_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create teacher_profiles table
    op.execute("""
        CREATE TABLE IF NOT EXISTS teacher_profiles (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            employee_id VARCHAR(50) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            phone VARCHAR(50),
            department VARCHAR(255) NOT NULL,
            designation teacherdesignation NOT NULL,
            highest_qualification VARCHAR(255),
            specialization VARCHAR(255),
            qualifications_list JSONB,
            teaching_experience_years FLOAT DEFAULT 0,
            industry_experience_years FLOAT DEFAULT 0,
            research_experience_years FLOAT DEFAULT 0,
            date_of_joining DATE,
            awards JSONB,
            publications_count INTEGER DEFAULT 0,
            patents_count INTEGER DEFAULT 0,
            funded_projects_count INTEGER DEFAULT 0,
            research_indices JSONB,
            fdp_attended JSONB,
            workshops_conducted JSONB,
            certifications JSONB,
            current_courses JSONB,
            teaching_hours_per_week FLOAT,
            student_feedback_rating FLOAT,
            api_score FLOAT,
            uses_lms BOOLEAN DEFAULT FALSE,
            digital_content_created INTEGER DEFAULT 0,
            moocs_developed INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            is_phd_guide BOOLEAN DEFAULT FALSE,
            phd_students_guided INTEGER DEFAULT 0,
            profile_document_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create digital_contents table
    op.execute("""
        CREATE TABLE IF NOT EXISTS digital_contents (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            title VARCHAR(500) NOT NULL,
            description TEXT,
            content_type contenttype NOT NULL,
            course_code VARCHAR(50),
            course_name VARCHAR(255),
            department VARCHAR(255) NOT NULL,
            semester INTEGER,
            topics JSONB,
            learning_outcomes JSONB,
            blooms_level bloomslevel,
            file_path VARCHAR(500),
            file_size INTEGER,
            external_url VARCHAR(500),
            duration_minutes INTEGER,
            created_by VARCHAR(255) NOT NULL,
            creator_email VARCHAR(255),
            view_count INTEGER DEFAULT 0,
            download_count INTEGER DEFAULT 0,
            average_rating FLOAT,
            ratings_count INTEGER DEFAULT 0,
            is_accessible BOOLEAN DEFAULT TRUE,
            has_transcripts BOOLEAN DEFAULT FALSE,
            supported_languages JSONB,
            is_published BOOLEAN DEFAULT FALSE,
            is_approved BOOLEAN DEFAULT FALSE,
            approved_by VARCHAR(255),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create learning_outcome_attainments table
    op.execute("""
        CREATE TABLE IF NOT EXISTS learning_outcome_attainments (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            course_code VARCHAR(50) NOT NULL,
            course_name VARCHAR(255) NOT NULL,
            department VARCHAR(255) NOT NULL,
            semester INTEGER NOT NULL,
            academic_year VARCHAR(20) NOT NULL,
            batch VARCHAR(20),
            total_students INTEGER NOT NULL,
            students_appeared INTEGER,
            students_passed INTEGER,
            pass_percentage FLOAT,
            course_outcomes JSONB NOT NULL,
            co_attainment_direct JSONB,
            co_attainment_indirect JSONB,
            co_attainment_overall JSONB,
            co_attainment_target JSONB,
            co_po_mapping JSONB,
            po_contribution JSONB,
            direct_assessment_methods JSONB,
            indirect_assessment_methods JSONB,
            direct_weightage FLOAT DEFAULT 80,
            indirect_weightage FLOAT DEFAULT 20,
            attainment_threshold FLOAT DEFAULT 60,
            gap_analysis JSONB,
            action_taken TEXT,
            attainment_report_path VARCHAR(500),
            course_coordinator VARCHAR(255),
            verified_by VARCHAR(255),
            verified_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create blended_learning_sessions table
    op.execute("""
        CREATE TABLE IF NOT EXISTS blended_learning_sessions (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            course_code VARCHAR(50) NOT NULL,
            course_name VARCHAR(255) NOT NULL,
            department VARCHAR(255) NOT NULL,
            semester INTEGER,
            academic_year VARCHAR(20) NOT NULL,
            session_title VARCHAR(500) NOT NULL,
            session_date DATE NOT NULL,
            duration_minutes INTEGER,
            teaching_method teachingmethod NOT NULL,
            is_synchronous BOOLEAN DEFAULT TRUE,
            online_component_percentage FLOAT,
            offline_component_percentage FLOAT,
            tools_used JSONB,
            lms_platform VARCHAR(100),
            pre_class_materials JSONB,
            in_class_activities JSONB,
            post_class_assignments JSONB,
            students_enrolled INTEGER,
            students_attended_online INTEGER,
            students_attended_offline INTEGER,
            attendance_percentage FLOAT,
            faculty_name VARCHAR(255) NOT NULL,
            faculty_email VARCHAR(255),
            student_feedback_rating FLOAT,
            feedback_comments TEXT,
            learning_outcomes_covered JSONB,
            blooms_levels_addressed JSONB,
            session_recording_path VARCHAR(500),
            screenshots_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create indexes for lms_adoption
    op.execute("CREATE INDEX IF NOT EXISTS ix_lms_adoption_platform ON lms_adoption(platform)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lms_adoption_department ON lms_adoption(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lms_adoption_academic_year ON lms_adoption(academic_year)")

    # Create indexes for lesson_plans
    op.execute("CREATE INDEX IF NOT EXISTS ix_lesson_plans_course_code ON lesson_plans(course_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lesson_plans_department ON lesson_plans(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lesson_plans_academic_year ON lesson_plans(academic_year)")

    # Create indexes for attendance_records
    op.execute("CREATE INDEX IF NOT EXISTS ix_attendance_records_student_id ON attendance_records(student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_attendance_records_course_code ON attendance_records(course_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_attendance_records_date ON attendance_records(attendance_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_attendance_records_department ON attendance_records(department)")

    # Create indexes for cie_records
    op.execute("CREATE INDEX IF NOT EXISTS ix_cie_records_student_id ON cie_records(student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cie_records_course_code ON cie_records(course_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cie_records_assessment_type ON cie_records(assessment_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cie_records_academic_year ON cie_records(academic_year)")

    # Create indexes for evaluation_rubrics
    op.execute("CREATE INDEX IF NOT EXISTS ix_evaluation_rubrics_course_code ON evaluation_rubrics(course_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_evaluation_rubrics_assessment_type ON evaluation_rubrics(assessment_type)")

    # Create indexes for student_performance
    op.execute("CREATE INDEX IF NOT EXISTS ix_student_performance_student_id ON student_performance(student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_student_performance_department ON student_performance(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_student_performance_academic_year ON student_performance(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_student_performance_level ON student_performance(performance_level)")

    # Create indexes for teacher_profiles
    op.execute("CREATE INDEX IF NOT EXISTS ix_teacher_profiles_department ON teacher_profiles(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_teacher_profiles_designation ON teacher_profiles(designation)")

    # Create indexes for digital_contents
    op.execute("CREATE INDEX IF NOT EXISTS ix_digital_contents_course_code ON digital_contents(course_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_digital_contents_content_type ON digital_contents(content_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_digital_contents_department ON digital_contents(department)")

    # Create indexes for learning_outcome_attainments
    op.execute("CREATE INDEX IF NOT EXISTS ix_lo_attainment_course_code ON learning_outcome_attainments(course_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lo_attainment_academic_year ON learning_outcome_attainments(academic_year)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lo_attainment_department ON learning_outcome_attainments(department)")

    # Create indexes for blended_learning_sessions
    op.execute("CREATE INDEX IF NOT EXISTS ix_blended_sessions_course_code ON blended_learning_sessions(course_code)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_blended_sessions_department ON blended_learning_sessions(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_blended_sessions_date ON blended_learning_sessions(session_date)")


def downgrade() -> None:
    # Drop indexes for blended_learning_sessions
    op.execute("DROP INDEX IF EXISTS ix_blended_sessions_date")
    op.execute("DROP INDEX IF EXISTS ix_blended_sessions_department")
    op.execute("DROP INDEX IF EXISTS ix_blended_sessions_course_code")

    # Drop indexes for learning_outcome_attainments
    op.execute("DROP INDEX IF EXISTS ix_lo_attainment_department")
    op.execute("DROP INDEX IF EXISTS ix_lo_attainment_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_lo_attainment_course_code")

    # Drop indexes for digital_contents
    op.execute("DROP INDEX IF EXISTS ix_digital_contents_department")
    op.execute("DROP INDEX IF EXISTS ix_digital_contents_content_type")
    op.execute("DROP INDEX IF EXISTS ix_digital_contents_course_code")

    # Drop indexes for teacher_profiles
    op.execute("DROP INDEX IF EXISTS ix_teacher_profiles_designation")
    op.execute("DROP INDEX IF EXISTS ix_teacher_profiles_department")

    # Drop indexes for student_performance
    op.execute("DROP INDEX IF EXISTS ix_student_performance_level")
    op.execute("DROP INDEX IF EXISTS ix_student_performance_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_student_performance_department")
    op.execute("DROP INDEX IF EXISTS ix_student_performance_student_id")

    # Drop indexes for evaluation_rubrics
    op.execute("DROP INDEX IF EXISTS ix_evaluation_rubrics_assessment_type")
    op.execute("DROP INDEX IF EXISTS ix_evaluation_rubrics_course_code")

    # Drop indexes for cie_records
    op.execute("DROP INDEX IF EXISTS ix_cie_records_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_cie_records_assessment_type")
    op.execute("DROP INDEX IF EXISTS ix_cie_records_course_code")
    op.execute("DROP INDEX IF EXISTS ix_cie_records_student_id")

    # Drop indexes for attendance_records
    op.execute("DROP INDEX IF EXISTS ix_attendance_records_department")
    op.execute("DROP INDEX IF EXISTS ix_attendance_records_date")
    op.execute("DROP INDEX IF EXISTS ix_attendance_records_course_code")
    op.execute("DROP INDEX IF EXISTS ix_attendance_records_student_id")

    # Drop indexes for lesson_plans
    op.execute("DROP INDEX IF EXISTS ix_lesson_plans_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_lesson_plans_department")
    op.execute("DROP INDEX IF EXISTS ix_lesson_plans_course_code")

    # Drop indexes for lms_adoption
    op.execute("DROP INDEX IF EXISTS ix_lms_adoption_academic_year")
    op.execute("DROP INDEX IF EXISTS ix_lms_adoption_department")
    op.execute("DROP INDEX IF EXISTS ix_lms_adoption_platform")

    # Drop tables
    op.drop_table('blended_learning_sessions')
    op.drop_table('learning_outcome_attainments')
    op.drop_table('digital_contents')
    op.drop_table('teacher_profiles')
    op.drop_table('student_performance')
    op.drop_table('cie_records')
    op.drop_table('evaluation_rubrics')
    op.drop_table('attendance_records')
    op.drop_table('lesson_plans')
    op.drop_table('lms_adoption')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS performancelevel")
    op.execute("DROP TYPE IF EXISTS teacherdesignation")
    op.execute("DROP TYPE IF EXISTS contenttype")
    op.execute("DROP TYPE IF EXISTS teachingmethod")
    op.execute("DROP TYPE IF EXISTS assessmenttype")
    op.execute("DROP TYPE IF EXISTS attendancestatus")
    op.execute("DROP TYPE IF EXISTS bloomslevel")
    op.execute("DROP TYPE IF EXISTS lmsplatform")
