"""add campus drive tables

Revision ID: campus_drive_001
Revises: 2025_12_14_add_token_transactions
Create Date: 2026-01-22

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'campus_drive_001'
down_revision = 'add_token_transactions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (IF NOT EXISTS for idempotency)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE questioncategory AS ENUM ('logical', 'technical', 'ai_ml', 'english');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE questiondifficulty AS ENUM ('easy', 'medium', 'hard');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE registrationstatus AS ENUM ('registered', 'quiz_in_progress', 'quiz_completed', 'qualified', 'not_qualified');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create tables using raw SQL with IF NOT EXISTS for idempotency
    op.execute("""
        CREATE TABLE IF NOT EXISTS campus_drives (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            company_name VARCHAR(255),
            description TEXT,
            registration_start TIMESTAMP DEFAULT NOW(),
            registration_end TIMESTAMP,
            quiz_date TIMESTAMP,
            quiz_duration_minutes INTEGER DEFAULT 60,
            passing_percentage FLOAT DEFAULT 60.0,
            total_questions INTEGER DEFAULT 30,
            logical_questions INTEGER DEFAULT 5,
            technical_questions INTEGER DEFAULT 10,
            ai_ml_questions INTEGER DEFAULT 10,
            english_questions INTEGER DEFAULT 5,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS campus_drive_questions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            campus_drive_id UUID REFERENCES campus_drives(id) ON DELETE CASCADE,
            question_text TEXT NOT NULL,
            category questioncategory NOT NULL,
            difficulty questiondifficulty DEFAULT 'medium',
            options JSONB NOT NULL,
            correct_option INTEGER NOT NULL,
            marks FLOAT DEFAULT 1.0,
            is_global BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS campus_drive_registrations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            campus_drive_id UUID NOT NULL REFERENCES campus_drives(id) ON DELETE CASCADE,
            full_name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(20) NOT NULL,
            college_name VARCHAR(255) NOT NULL,
            department VARCHAR(255) NOT NULL,
            year_of_study VARCHAR(50) NOT NULL,
            roll_number VARCHAR(50),
            cgpa FLOAT,
            status registrationstatus DEFAULT 'registered',
            quiz_start_time TIMESTAMP,
            quiz_end_time TIMESTAMP,
            quiz_score FLOAT,
            total_marks FLOAT,
            percentage FLOAT,
            is_qualified BOOLEAN DEFAULT FALSE,
            logical_score FLOAT DEFAULT 0,
            technical_score FLOAT DEFAULT 0,
            ai_ml_score FLOAT DEFAULT 0,
            english_score FLOAT DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS campus_drive_responses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            registration_id UUID NOT NULL REFERENCES campus_drive_registrations(id) ON DELETE CASCADE,
            question_id UUID NOT NULL REFERENCES campus_drive_questions(id) ON DELETE CASCADE,
            selected_option INTEGER,
            is_correct BOOLEAN DEFAULT FALSE,
            marks_obtained FLOAT DEFAULT 0,
            answered_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create indexes (IF NOT EXISTS)
    op.execute("CREATE INDEX IF NOT EXISTS ix_campus_drive_registrations_email ON campus_drive_registrations(email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_campus_drive_registrations_drive_id ON campus_drive_registrations(campus_drive_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_campus_drive_questions_category ON campus_drive_questions(category)")

    # Seed data - Create default campus drive (only if none exists)
    op.execute("""
        INSERT INTO campus_drives (id, name, company_name, description, registration_start, registration_end, quiz_date, quiz_duration_minutes, passing_percentage, total_questions, logical_questions, technical_questions, ai_ml_questions, english_questions, is_active, created_at, updated_at)
        SELECT
            gen_random_uuid(),
            'Campus Placement Drive 2026',
            'BharatBuild',
            'Annual campus placement drive for engineering students. Test your skills in logical reasoning, technical knowledge, AI/ML concepts, and English proficiency.',
            NOW(),
            NOW() + INTERVAL '30 days',
            NOW() + INTERVAL '1 day',
            60,
            60.0,
            30,
            5,
            10,
            10,
            5,
            TRUE,
            NOW(),
            NOW()
        WHERE NOT EXISTS (SELECT 1 FROM campus_drives WHERE name = 'Campus Placement Drive 2026')
    """)

    # Seed LOGICAL Questions (only if no questions exist)
    op.execute("""
        INSERT INTO campus_drive_questions (id, question_text, category, difficulty, options, correct_option, marks, is_global, created_at)
        SELECT gen_random_uuid(), q.question_text, q.category::questioncategory, q.difficulty::questiondifficulty, q.options::jsonb, q.correct_option, 1.0, TRUE, NOW()
        FROM (VALUES
            ('If all Bloops are Razzies and all Razzies are Lazzies, then all Bloops are definitely Lazzies. Is this statement true?', 'logical', 'medium', '["True", "False", "Cannot be determined", "Partially true"]', 0),
            ('A is the brother of B. B is the sister of C. D is the father of A. How is C related to D?', 'logical', 'medium', '["Daughter", "Son", "Granddaughter", "Cannot be determined"]', 0),
            ('Complete the series: 2, 6, 12, 20, 30, ?', 'logical', 'medium', '["40", "42", "44", "46"]', 1),
            ('Find the odd one out: 8, 27, 64, 100, 125, 216', 'logical', 'medium', '["27", "64", "100", "125"]', 2),
            ('A clock shows 3:15. What is the angle between the hour and minute hands?', 'logical', 'medium', '["0 degrees", "7.5 degrees", "15 degrees", "22.5 degrees"]', 1),
            ('In a row of students, Ram is 7th from the left and Shyam is 9th from the right. If they interchange, Ram becomes 11th from left. How many students are in the row?', 'logical', 'medium', '["17", "18", "19", "20"]', 2)
        ) AS q(question_text, category, difficulty, options, correct_option)
        WHERE NOT EXISTS (SELECT 1 FROM campus_drive_questions WHERE category = 'logical' LIMIT 1)
    """)

    # Seed TECHNICAL Questions (only if no technical questions exist)
    op.execute("""
        INSERT INTO campus_drive_questions (id, question_text, category, difficulty, options, correct_option, marks, is_global, created_at)
        SELECT gen_random_uuid(), q.question_text, q.category::questioncategory, q.difficulty::questiondifficulty, q.options::jsonb, q.correct_option, 1.0, TRUE, NOW()
        FROM (VALUES
            ('What is the time complexity of binary search?', 'technical', 'medium', '["O(n)", "O(log n)", "O(n log n)", "O(1)"]', 1),
            ('Which data structure uses LIFO (Last In First Out)?', 'technical', 'medium', '["Queue", "Stack", "Array", "Linked List"]', 1),
            ('What is the output of: print(type([]) == type({}))?', 'technical', 'medium', '["True", "False", "Error", "None"]', 1),
            ('Which HTTP method is idempotent?', 'technical', 'medium', '["POST", "GET", "PATCH", "None of the above"]', 1),
            ('What does SQL stand for?', 'technical', 'medium', '["Structured Query Language", "Simple Query Language", "Standard Query Language", "Sequential Query Language"]', 0),
            ('Which sorting algorithm has the best average case time complexity?', 'technical', 'medium', '["Bubble Sort", "Insertion Sort", "Quick Sort", "Selection Sort"]', 2),
            ('What is the purpose of the finally block in exception handling?', 'technical', 'medium', '["Execute only if exception occurs", "Execute only if no exception", "Always execute regardless of exception", "Skip exception handling"]', 2),
            ('Which of the following is NOT a valid JavaScript data type?', 'technical', 'medium', '["Boolean", "Undefined", "Integer", "Symbol"]', 2),
            ('What is the difference between == and === in JavaScript?', 'technical', 'medium', '["No difference", "=== checks type also", "== checks type also", "=== is faster"]', 1),
            ('Which CSS property is used to change the background color?', 'technical', 'medium', '["color", "bgcolor", "background-color", "background"]', 2),
            ('What is Git primarily used for?', 'technical', 'medium', '["Database management", "Version control", "Web hosting", "Compilation"]', 1),
            ('Which of the following is a NoSQL database?', 'technical', 'medium', '["MySQL", "PostgreSQL", "MongoDB", "Oracle"]', 2)
        ) AS q(question_text, category, difficulty, options, correct_option)
        WHERE NOT EXISTS (SELECT 1 FROM campus_drive_questions WHERE category = 'technical' LIMIT 1)
    """)

    # Seed AI/ML Questions (only if no ai_ml questions exist)
    op.execute("""
        INSERT INTO campus_drive_questions (id, question_text, category, difficulty, options, correct_option, marks, is_global, created_at)
        SELECT gen_random_uuid(), q.question_text, q.category::questioncategory, q.difficulty::questiondifficulty, q.options::jsonb, q.correct_option, 1.0, TRUE, NOW()
        FROM (VALUES
            ('What does CNN stand for in deep learning?', 'ai_ml', 'medium', '["Central Neural Network", "Convolutional Neural Network", "Connected Neural Network", "Computed Neural Network"]', 1),
            ('Which algorithm is commonly used for classification problems?', 'ai_ml', 'medium', '["Linear Regression", "K-Means Clustering", "Random Forest", "PCA"]', 2),
            ('What is overfitting in machine learning?', 'ai_ml', 'medium', '["Model performs well on training data but poorly on test data", "Model performs poorly on training data", "Model takes too long to train", "Model uses too much memory"]', 0),
            ('Which activation function is most commonly used in hidden layers of neural networks?', 'ai_ml', 'medium', '["Sigmoid", "Tanh", "ReLU", "Softmax"]', 2),
            ('What is the purpose of the learning rate in gradient descent?', 'ai_ml', 'medium', '["Controls model complexity", "Controls step size in optimization", "Controls regularization", "Controls batch size"]', 1),
            ('Which metric is used to evaluate classification models?', 'ai_ml', 'medium', '["RMSE", "MAE", "Accuracy", "R-squared"]', 2),
            ('What type of machine learning is used when we have labeled data?', 'ai_ml', 'medium', '["Unsupervised Learning", "Supervised Learning", "Reinforcement Learning", "Semi-supervised Learning"]', 1),
            ('Which library is commonly used for deep learning in Python?', 'ai_ml', 'medium', '["NumPy", "Pandas", "TensorFlow", "Matplotlib"]', 2),
            ('What is the purpose of dropout in neural networks?', 'ai_ml', 'medium', '["Speed up training", "Prevent overfitting", "Increase accuracy", "Reduce memory usage"]', 1),
            ('Which of the following is a clustering algorithm?', 'ai_ml', 'medium', '["Linear Regression", "Decision Tree", "K-Means", "Naive Bayes"]', 2),
            ('What does NLP stand for?', 'ai_ml', 'medium', '["Neural Learning Process", "Natural Language Processing", "Network Layer Protocol", "Non-Linear Programming"]', 1),
            ('Which optimizer is an improvement over standard gradient descent?', 'ai_ml', 'medium', '["SGD", "Adam", "RMSprop", "All of the above"]', 3)
        ) AS q(question_text, category, difficulty, options, correct_option)
        WHERE NOT EXISTS (SELECT 1 FROM campus_drive_questions WHERE category = 'ai_ml' LIMIT 1)
    """)

    # Seed ENGLISH Questions (only if no english questions exist)
    op.execute("""
        INSERT INTO campus_drive_questions (id, question_text, category, difficulty, options, correct_option, marks, is_global, created_at)
        SELECT gen_random_uuid(), q.question_text, q.category::questioncategory, q.difficulty::questiondifficulty, q.options::jsonb, q.correct_option, 1.0, TRUE, NOW()
        FROM (VALUES
            ('Choose the correct sentence:', 'english', 'medium', '["He don''t know nothing", "He doesn''t know anything", "He don''t know anything", "He doesn''t know nothing"]', 1),
            ('What is the synonym of Eloquent?', 'english', 'medium', '["Silent", "Articulate", "Humble", "Arrogant"]', 1),
            ('Choose the antonym of Benevolent:', 'english', 'medium', '["Kind", "Generous", "Malevolent", "Caring"]', 2),
            ('Fill in the blank: She ___ to the store yesterday.', 'english', 'medium', '["go", "goes", "went", "going"]', 2),
            ('Which sentence is grammatically correct?', 'english', 'medium', '["Me and him went to the park", "Him and me went to the park", "He and I went to the park", "I and he went to the park"]', 2),
            ('What does ubiquitous mean?', 'english', 'medium', '["Rare", "Present everywhere", "Unique", "Unknown"]', 1)
        ) AS q(question_text, category, difficulty, options, correct_option)
        WHERE NOT EXISTS (SELECT 1 FROM campus_drive_questions WHERE category = 'english' LIMIT 1)
    """)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_campus_drive_questions_category', table_name='campus_drive_questions')
    op.drop_index('ix_campus_drive_registrations_drive_id', table_name='campus_drive_registrations')
    op.drop_index('ix_campus_drive_registrations_email', table_name='campus_drive_registrations')

    # Drop tables
    op.drop_table('campus_drive_responses')
    op.drop_table('campus_drive_registrations')
    op.drop_table('campus_drive_questions')
    op.drop_table('campus_drives')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS registrationstatus")
    op.execute("DROP TYPE IF EXISTS questiondifficulty")
    op.execute("DROP TYPE IF EXISTS questioncategory")
