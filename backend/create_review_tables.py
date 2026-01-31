"""Create project review tables"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.core.database import get_engine

async def create_tables():
    """Create project review tables"""
    print("Creating project review tables...")

    engine = get_engine()
    async with engine.begin() as conn:
        # Drop old tables if they exist (to recreate with new schema)
        print("Dropping old tables if they exist...")
        await conn.execute(text("DROP TABLE IF EXISTS review_scores CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS review_panel_members CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS project_reviews CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS project_team_members CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS student_projects CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS review_projects CASCADE;"))
        print("  Old tables dropped")

        # Create enum types (ignore if already exist)
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE projecttype AS ENUM ('mini_project', 'major_project');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))

        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE reviewtype AS ENUM ('review_1', 'review_2', 'review_3', 'final_review');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))

        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE reviewstatus AS ENUM ('scheduled', 'in_progress', 'completed', 'rescheduled', 'cancelled');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))

        # Create review_projects table (using VARCHAR(36) to match users table)
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS review_projects (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                project_type projecttype DEFAULT 'mini_project',
                technology_stack VARCHAR(500),
                domain VARCHAR(255),
                team_name VARCHAR(255),
                team_size INTEGER DEFAULT 1,
                student_id VARCHAR(36) REFERENCES users(id),
                guide_id VARCHAR(36) REFERENCES users(id),
                guide_name VARCHAR(255),
                batch VARCHAR(50),
                semester INTEGER,
                department VARCHAR(255),
                github_url VARCHAR(500),
                demo_url VARCHAR(500),
                documentation_url VARCHAR(500),
                current_review INTEGER DEFAULT 0,
                total_score FLOAT DEFAULT 0.0,
                average_score FLOAT DEFAULT 0.0,
                is_approved BOOLEAN DEFAULT FALSE,
                is_completed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("  Created: review_projects")

        # Create project_team_members table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS project_team_members (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                project_id VARCHAR(36) REFERENCES review_projects(id) ON DELETE CASCADE,
                student_id VARCHAR(36) REFERENCES users(id),
                name VARCHAR(255) NOT NULL,
                roll_number VARCHAR(50),
                email VARCHAR(255),
                role VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("  Created: project_team_members")

        # Create project_reviews table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS project_reviews (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                project_id VARCHAR(36) REFERENCES review_projects(id) ON DELETE CASCADE NOT NULL,
                review_type reviewtype NOT NULL,
                review_number INTEGER NOT NULL,
                scheduled_date TIMESTAMP NOT NULL,
                scheduled_time VARCHAR(20),
                venue VARCHAR(255),
                duration_minutes INTEGER DEFAULT 30,
                status reviewstatus DEFAULT 'scheduled',
                innovation_score FLOAT DEFAULT 0.0,
                technical_score FLOAT DEFAULT 0.0,
                implementation_score FLOAT DEFAULT 0.0,
                documentation_score FLOAT DEFAULT 0.0,
                presentation_score FLOAT DEFAULT 0.0,
                total_score FLOAT DEFAULT 0.0,
                strengths TEXT,
                weaknesses TEXT,
                suggestions TEXT,
                overall_feedback TEXT,
                action_items TEXT,
                next_review_focus TEXT,
                student_present BOOLEAN DEFAULT TRUE,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(36) REFERENCES users(id)
            );
        """))
        print("  Created: project_reviews")

        # Create review_panel_members table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS review_panel_members (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                review_id VARCHAR(36) REFERENCES project_reviews(id) ON DELETE CASCADE NOT NULL,
                faculty_id VARCHAR(36) REFERENCES users(id),
                name VARCHAR(255) NOT NULL,
                designation VARCHAR(255),
                department VARCHAR(255),
                email VARCHAR(255),
                role VARCHAR(50) DEFAULT 'member',
                is_lead BOOLEAN DEFAULT FALSE,
                is_present BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("  Created: review_panel_members")

        # Create review_scores table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS review_scores (
                id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
                review_id VARCHAR(36) REFERENCES project_reviews(id) ON DELETE CASCADE NOT NULL,
                panel_member_id VARCHAR(36) REFERENCES review_panel_members(id) ON DELETE CASCADE NOT NULL,
                faculty_id VARCHAR(36) REFERENCES users(id),
                innovation_score FLOAT DEFAULT 0.0,
                technical_score FLOAT DEFAULT 0.0,
                implementation_score FLOAT DEFAULT 0.0,
                documentation_score FLOAT DEFAULT 0.0,
                presentation_score FLOAT DEFAULT 0.0,
                total_score FLOAT DEFAULT 0.0,
                comments TEXT,
                private_notes TEXT,
                scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        print("  Created: review_scores")

        # Create indexes
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_review_projects_batch ON review_projects(batch);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_review_projects_semester ON review_projects(semester);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_reviews_scheduled_date ON project_reviews(scheduled_date);"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_project_reviews_status ON project_reviews(status);"))
        print("  Created indexes")

    print("\nProject review tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables())
