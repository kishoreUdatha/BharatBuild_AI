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
    # Create enum types
    op.execute("CREATE TYPE questioncategory AS ENUM ('logical', 'technical', 'ai_ml', 'english')")
    op.execute("CREATE TYPE questiondifficulty AS ENUM ('easy', 'medium', 'hard')")
    op.execute("CREATE TYPE registrationstatus AS ENUM ('registered', 'quiz_in_progress', 'quiz_completed', 'qualified', 'not_qualified')")

    # Create campus_drives table
    op.create_table(
        'campus_drives',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('company_name', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('registration_start', sa.DateTime, default=sa.func.now()),
        sa.Column('registration_end', sa.DateTime, nullable=True),
        sa.Column('quiz_date', sa.DateTime, nullable=True),
        sa.Column('quiz_duration_minutes', sa.Integer, default=60),
        sa.Column('passing_percentage', sa.Float, default=60.0),
        sa.Column('total_questions', sa.Integer, default=30),
        sa.Column('logical_questions', sa.Integer, default=5),
        sa.Column('technical_questions', sa.Integer, default=10),
        sa.Column('ai_ml_questions', sa.Integer, default=10),
        sa.Column('english_questions', sa.Integer, default=5),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create campus_drive_questions table
    op.create_table(
        'campus_drive_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('campus_drive_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campus_drives.id', ondelete='CASCADE'), nullable=True),
        sa.Column('question_text', sa.Text, nullable=False),
        sa.Column('category', sa.Enum('logical', 'technical', 'ai_ml', 'english', name='questioncategory'), nullable=False),
        sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='questiondifficulty'), default='medium'),
        sa.Column('options', postgresql.JSON, nullable=False),
        sa.Column('correct_option', sa.Integer, nullable=False),
        sa.Column('marks', sa.Float, default=1.0),
        sa.Column('is_global', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
    )

    # Create campus_drive_registrations table
    op.create_table(
        'campus_drive_registrations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('campus_drive_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campus_drives.id', ondelete='CASCADE'), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('college_name', sa.String(255), nullable=False),
        sa.Column('department', sa.String(255), nullable=False),
        sa.Column('year_of_study', sa.String(50), nullable=False),
        sa.Column('roll_number', sa.String(50), nullable=True),
        sa.Column('cgpa', sa.Float, nullable=True),
        sa.Column('status', sa.Enum('registered', 'quiz_in_progress', 'quiz_completed', 'qualified', 'not_qualified', name='registrationstatus'), default='registered'),
        sa.Column('quiz_start_time', sa.DateTime, nullable=True),
        sa.Column('quiz_end_time', sa.DateTime, nullable=True),
        sa.Column('quiz_score', sa.Float, nullable=True),
        sa.Column('total_marks', sa.Float, nullable=True),
        sa.Column('percentage', sa.Float, nullable=True),
        sa.Column('is_qualified', sa.Boolean, default=False),
        sa.Column('logical_score', sa.Float, default=0),
        sa.Column('technical_score', sa.Float, default=0),
        sa.Column('ai_ml_score', sa.Float, default=0),
        sa.Column('english_score', sa.Float, default=0),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create campus_drive_responses table
    op.create_table(
        'campus_drive_responses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('registration_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campus_drive_registrations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('campus_drive_questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('selected_option', sa.Integer, nullable=True),
        sa.Column('is_correct', sa.Boolean, default=False),
        sa.Column('marks_obtained', sa.Float, default=0),
        sa.Column('answered_at', sa.DateTime, default=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_campus_drive_registrations_email', 'campus_drive_registrations', ['email'])
    op.create_index('ix_campus_drive_registrations_drive_id', 'campus_drive_registrations', ['campus_drive_id'])
    op.create_index('ix_campus_drive_questions_category', 'campus_drive_questions', ['category'])

    # Seed data - Create default campus drive and questions
    op.execute("""
        INSERT INTO campus_drives (id, name, company_name, description, registration_start, registration_end, quiz_date, quiz_duration_minutes, passing_percentage, total_questions, logical_questions, technical_questions, ai_ml_questions, english_questions, is_active, created_at, updated_at)
        VALUES (
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
        )
    """)

    # Seed LOGICAL Questions
    op.execute("""
        INSERT INTO campus_drive_questions (id, question_text, category, difficulty, options, correct_option, marks, is_global, created_at) VALUES
        (gen_random_uuid(), 'If all Bloops are Razzies and all Razzies are Lazzies, then all Bloops are definitely Lazzies. Is this statement true?', 'logical', 'medium', '["True", "False", "Cannot be determined", "Partially true"]', 0, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'A is the brother of B. B is the sister of C. D is the father of A. How is C related to D?', 'logical', 'medium', '["Daughter", "Son", "Granddaughter", "Cannot be determined"]', 0, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Complete the series: 2, 6, 12, 20, 30, ?', 'logical', 'medium', '["40", "42", "44", "46"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Find the odd one out: 8, 27, 64, 100, 125, 216', 'logical', 'medium', '["27", "64", "100", "125"]', 2, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'A clock shows 3:15. What is the angle between the hour and minute hands?', 'logical', 'medium', '["0 degrees", "7.5 degrees", "15 degrees", "22.5 degrees"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'In a row of students, Ram is 7th from the left and Shyam is 9th from the right. If they interchange, Ram becomes 11th from left. How many students are in the row?', 'logical', 'medium', '["17", "18", "19", "20"]', 2, 1.0, TRUE, NOW())
    """)

    # Seed TECHNICAL Questions
    op.execute("""
        INSERT INTO campus_drive_questions (id, question_text, category, difficulty, options, correct_option, marks, is_global, created_at) VALUES
        (gen_random_uuid(), 'What is the time complexity of binary search?', 'technical', 'medium', '["O(n)", "O(log n)", "O(n log n)", "O(1)"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Which data structure uses LIFO (Last In First Out)?', 'technical', 'medium', '["Queue", "Stack", "Array", "Linked List"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'What is the output of: print(type([]) == type({}))?', 'technical', 'medium', '["True", "False", "Error", "None"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Which HTTP method is idempotent?', 'technical', 'medium', '["POST", "GET", "PATCH", "None of the above"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'What does SQL stand for?', 'technical', 'medium', '["Structured Query Language", "Simple Query Language", "Standard Query Language", "Sequential Query Language"]', 0, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Which sorting algorithm has the best average case time complexity?', 'technical', 'medium', '["Bubble Sort", "Insertion Sort", "Quick Sort", "Selection Sort"]', 2, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'What is the purpose of the finally block in exception handling?', 'technical', 'medium', '["Execute only if exception occurs", "Execute only if no exception", "Always execute regardless of exception", "Skip exception handling"]', 2, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Which of the following is NOT a valid JavaScript data type?', 'technical', 'medium', '["Boolean", "Undefined", "Integer", "Symbol"]', 2, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'What is the difference between == and === in JavaScript?', 'technical', 'medium', '["No difference", "=== checks type also", "== checks type also", "=== is faster"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Which CSS property is used to change the background color?', 'technical', 'medium', '["color", "bgcolor", "background-color", "background"]', 2, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'What is Git primarily used for?', 'technical', 'medium', '["Database management", "Version control", "Web hosting", "Compilation"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Which of the following is a NoSQL database?', 'technical', 'medium', '["MySQL", "PostgreSQL", "MongoDB", "Oracle"]', 2, 1.0, TRUE, NOW())
    """)

    # Seed AI/ML Questions
    op.execute("""
        INSERT INTO campus_drive_questions (id, question_text, category, difficulty, options, correct_option, marks, is_global, created_at) VALUES
        (gen_random_uuid(), 'What does CNN stand for in deep learning?', 'ai_ml', 'medium', '["Central Neural Network", "Convolutional Neural Network", "Connected Neural Network", "Computed Neural Network"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Which algorithm is commonly used for classification problems?', 'ai_ml', 'medium', '["Linear Regression", "K-Means Clustering", "Random Forest", "PCA"]', 2, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'What is overfitting in machine learning?', 'ai_ml', 'medium', '["Model performs well on training data but poorly on test data", "Model performs poorly on training data", "Model takes too long to train", "Model uses too much memory"]', 0, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Which activation function is most commonly used in hidden layers of neural networks?', 'ai_ml', 'medium', '["Sigmoid", "Tanh", "ReLU", "Softmax"]', 2, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'What is the purpose of the learning rate in gradient descent?', 'ai_ml', 'medium', '["Controls model complexity", "Controls step size in optimization", "Controls regularization", "Controls batch size"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Which metric is used to evaluate classification models?', 'ai_ml', 'medium', '["RMSE", "MAE", "Accuracy", "R-squared"]', 2, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'What type of machine learning is used when we have labeled data?', 'ai_ml', 'medium', '["Unsupervised Learning", "Supervised Learning", "Reinforcement Learning", "Semi-supervised Learning"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Which library is commonly used for deep learning in Python?', 'ai_ml', 'medium', '["NumPy", "Pandas", "TensorFlow", "Matplotlib"]', 2, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'What is the purpose of dropout in neural networks?', 'ai_ml', 'medium', '["Speed up training", "Prevent overfitting", "Increase accuracy", "Reduce memory usage"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Which of the following is a clustering algorithm?', 'ai_ml', 'medium', '["Linear Regression", "Decision Tree", "K-Means", "Naive Bayes"]', 2, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'What does NLP stand for?', 'ai_ml', 'medium', '["Neural Learning Process", "Natural Language Processing", "Network Layer Protocol", "Non-Linear Programming"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Which optimizer is an improvement over standard gradient descent?', 'ai_ml', 'medium', '["SGD", "Adam", "RMSprop", "All of the above"]', 3, 1.0, TRUE, NOW())
    """)

    # Seed ENGLISH Questions
    op.execute("""
        INSERT INTO campus_drive_questions (id, question_text, category, difficulty, options, correct_option, marks, is_global, created_at) VALUES
        (gen_random_uuid(), 'Choose the correct sentence:', 'english', 'medium', '["He don''t know nothing", "He doesn''t know anything", "He don''t know anything", "He doesn''t know nothing"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'What is the synonym of Eloquent?', 'english', 'medium', '["Silent", "Articulate", "Humble", "Arrogant"]', 1, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Choose the antonym of Benevolent:', 'english', 'medium', '["Kind", "Generous", "Malevolent", "Caring"]', 2, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Fill in the blank: She ___ to the store yesterday.', 'english', 'medium', '["go", "goes", "went", "going"]', 2, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'Which sentence is grammatically correct?', 'english', 'medium', '["Me and him went to the park", "Him and me went to the park", "He and I went to the park", "I and he went to the park"]', 2, 1.0, TRUE, NOW()),
        (gen_random_uuid(), 'What does ubiquitous mean?', 'english', 'medium', '["Rare", "Present everywhere", "Unique", "Unknown"]', 1, 1.0, TRUE, NOW())
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
