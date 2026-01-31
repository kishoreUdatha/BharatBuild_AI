"""Migration script to add lab_reports and semester_progress tables"""

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = 'postgresql+asyncpg://bharatbuild:password@localhost:5432/bharatbuild_db'

async def run_migration():
    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as conn:
        # Check if labreportstatus enum exists
        result = await conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'labreportstatus'"))
        if not result.fetchone():
            await conn.execute(text("CREATE TYPE labreportstatus AS ENUM ('not_submitted', 'submitted', 'under_review', 'approved', 'rejected', 'resubmit_required')"))
            print('Created labreportstatus enum')
        else:
            print('labreportstatus enum already exists')

        # Create lab_reports table
        await conn.execute(text('''
            CREATE TABLE IF NOT EXISTS lab_reports (
                id VARCHAR(36) PRIMARY KEY,
                enrollment_id VARCHAR(36) REFERENCES lab_enrollments(id) ON DELETE CASCADE,
                lab_id VARCHAR(36) REFERENCES labs(id) ON DELETE CASCADE,
                user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                file_url VARCHAR(500),
                file_name VARCHAR(255),
                file_size INTEGER,
                status labreportstatus DEFAULT 'not_submitted',
                reviewed_by VARCHAR(36) REFERENCES users(id),
                review_comments TEXT,
                grade VARCHAR(10),
                marks FLOAT,
                submission_count INTEGER DEFAULT 0,
                max_submissions INTEGER DEFAULT 3,
                submitted_at TIMESTAMP,
                reviewed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                deadline TIMESTAMP
            )
        '''))
        print('Created lab_reports table')

        # Create semester_progress table
        await conn.execute(text('''
            CREATE TABLE IF NOT EXISTS semester_progress (
                id VARCHAR(36) PRIMARY KEY,
                user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
                semester semester NOT NULL,
                branch branch NOT NULL,
                total_labs INTEGER DEFAULT 0,
                labs_completed INTEGER DEFAULT 0,
                labs_in_progress INTEGER DEFAULT 0,
                reports_submitted INTEGER DEFAULT 0,
                reports_approved INTEGER DEFAULT 0,
                average_mcq_score FLOAT DEFAULT 0.0,
                average_coding_score FLOAT DEFAULT 0.0,
                overall_grade VARCHAR(10),
                is_completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        '''))
        print('Created semester_progress table')

        # Create indexes
        await conn.execute(text('CREATE INDEX IF NOT EXISTS ix_lab_reports_user_id ON lab_reports(user_id)'))
        await conn.execute(text('CREATE INDEX IF NOT EXISTS ix_lab_reports_lab_id ON lab_reports(lab_id)'))
        await conn.execute(text('CREATE INDEX IF NOT EXISTS ix_semester_progress_user_id ON semester_progress(user_id)'))
        print('Created indexes')

    await engine.dispose()
    print('Migration completed successfully!')

if __name__ == '__main__':
    asyncio.run(run_migration())
