-- Campus Drive Seed Script for AWS PostgreSQL
-- Run this directly on your database

-- First, create the enum types if they don't exist
DO $$ BEGIN
    CREATE TYPE questioncategory AS ENUM ('logical', 'technical', 'ai_ml', 'english');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE questiondifficulty AS ENUM ('easy', 'medium', 'hard');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE registrationstatus AS ENUM ('registered', 'quiz_in_progress', 'quiz_completed', 'qualified', 'not_qualified');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create tables if they don't exist
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
);

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
);

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
);

CREATE TABLE IF NOT EXISTS campus_drive_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    registration_id UUID NOT NULL REFERENCES campus_drive_registrations(id) ON DELETE CASCADE,
    question_id UUID NOT NULL REFERENCES campus_drive_questions(id) ON DELETE CASCADE,
    selected_option INTEGER,
    is_correct BOOLEAN DEFAULT FALSE,
    marks_obtained FLOAT DEFAULT 0,
    answered_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_campus_drive_registrations_email ON campus_drive_registrations(email);
CREATE INDEX IF NOT EXISTS ix_campus_drive_registrations_drive_id ON campus_drive_registrations(campus_drive_id);
CREATE INDEX IF NOT EXISTS ix_campus_drive_questions_category ON campus_drive_questions(category);

-- Insert Campus Drive 2026
INSERT INTO campus_drives (name, company_name, description, registration_end, quiz_date, quiz_duration_minutes, passing_percentage, total_questions, logical_questions, technical_questions, ai_ml_questions, english_questions, is_active)
VALUES (
    'Campus Placement Drive 2026',
    'BharatBuild',
    'Annual campus placement drive for engineering students. Test your skills in logical reasoning, technical knowledge, AI/ML concepts, and English proficiency.',
    NOW() + INTERVAL '30 days',
    NOW() + INTERVAL '1 day',
    60,
    60.0,
    30,
    5,
    10,
    10,
    5,
    TRUE
);

-- Insert LOGICAL Questions (6 questions)
INSERT INTO campus_drive_questions (question_text, category, difficulty, options, correct_option, marks, is_global) VALUES
('If all Bloops are Razzies and all Razzies are Lazzies, then all Bloops are definitely Lazzies. Is this statement true?', 'logical', 'medium', '["True", "False", "Cannot be determined", "Partially true"]', 0, 1.0, TRUE),
('A is the brother of B. B is the sister of C. D is the father of A. How is C related to D?', 'logical', 'medium', '["Daughter", "Son", "Granddaughter", "Cannot be determined"]', 0, 1.0, TRUE),
('Complete the series: 2, 6, 12, 20, 30, ?', 'logical', 'medium', '["40", "42", "44", "46"]', 1, 1.0, TRUE),
('Find the odd one out: 8, 27, 64, 100, 125, 216', 'logical', 'medium', '["27", "64", "100", "125"]', 2, 1.0, TRUE),
('A clock shows 3:15. What is the angle between the hour and minute hands?', 'logical', 'medium', '["0 degrees", "7.5 degrees", "15 degrees", "22.5 degrees"]', 1, 1.0, TRUE),
('In a row of students, Ram is 7th from the left and Shyam is 9th from the right. If they interchange, Ram becomes 11th from left. How many students are in the row?', 'logical', 'medium', '["17", "18", "19", "20"]', 2, 1.0, TRUE);

-- Insert TECHNICAL Questions (12 questions)
INSERT INTO campus_drive_questions (question_text, category, difficulty, options, correct_option, marks, is_global) VALUES
('What is the time complexity of binary search?', 'technical', 'medium', '["O(n)", "O(log n)", "O(n log n)", "O(1)"]', 1, 1.0, TRUE),
('Which data structure uses LIFO (Last In First Out)?', 'technical', 'medium', '["Queue", "Stack", "Array", "Linked List"]', 1, 1.0, TRUE),
('What is the output of: print(type([]) == type({}))?', 'technical', 'medium', '["True", "False", "Error", "None"]', 1, 1.0, TRUE),
('Which HTTP method is idempotent?', 'technical', 'medium', '["POST", "GET", "PATCH", "None of the above"]', 1, 1.0, TRUE),
('What does SQL stand for?', 'technical', 'medium', '["Structured Query Language", "Simple Query Language", "Standard Query Language", "Sequential Query Language"]', 0, 1.0, TRUE),
('Which sorting algorithm has the best average case time complexity?', 'technical', 'medium', '["Bubble Sort", "Insertion Sort", "Quick Sort", "Selection Sort"]', 2, 1.0, TRUE),
('What is the purpose of the finally block in exception handling?', 'technical', 'medium', '["Execute only if exception occurs", "Execute only if no exception", "Always execute regardless of exception", "Skip exception handling"]', 2, 1.0, TRUE),
('Which of the following is NOT a valid JavaScript data type?', 'technical', 'medium', '["Boolean", "Undefined", "Integer", "Symbol"]', 2, 1.0, TRUE),
('What is the difference between == and === in JavaScript?', 'technical', 'medium', '["No difference", "=== checks type also", "== checks type also", "=== is faster"]', 1, 1.0, TRUE),
('Which CSS property is used to change the background color?', 'technical', 'medium', '["color", "bgcolor", "background-color", "background"]', 2, 1.0, TRUE),
('What is Git primarily used for?', 'technical', 'medium', '["Database management", "Version control", "Web hosting", "Compilation"]', 1, 1.0, TRUE),
('Which of the following is a NoSQL database?', 'technical', 'medium', '["MySQL", "PostgreSQL", "MongoDB", "Oracle"]', 2, 1.0, TRUE);

-- Insert AI/ML Questions (12 questions)
INSERT INTO campus_drive_questions (question_text, category, difficulty, options, correct_option, marks, is_global) VALUES
('What does CNN stand for in deep learning?', 'ai_ml', 'medium', '["Central Neural Network", "Convolutional Neural Network", "Connected Neural Network", "Computed Neural Network"]', 1, 1.0, TRUE),
('Which algorithm is commonly used for classification problems?', 'ai_ml', 'medium', '["Linear Regression", "K-Means Clustering", "Random Forest", "PCA"]', 2, 1.0, TRUE),
('What is overfitting in machine learning?', 'ai_ml', 'medium', '["Model performs well on training data but poorly on test data", "Model performs poorly on training data", "Model takes too long to train", "Model uses too much memory"]', 0, 1.0, TRUE),
('Which activation function is most commonly used in hidden layers of neural networks?', 'ai_ml', 'medium', '["Sigmoid", "Tanh", "ReLU", "Softmax"]', 2, 1.0, TRUE),
('What is the purpose of the learning rate in gradient descent?', 'ai_ml', 'medium', '["Controls model complexity", "Controls step size in optimization", "Controls regularization", "Controls batch size"]', 1, 1.0, TRUE),
('Which metric is used to evaluate classification models?', 'ai_ml', 'medium', '["RMSE", "MAE", "Accuracy", "R-squared"]', 2, 1.0, TRUE),
('What type of machine learning is used when we have labeled data?', 'ai_ml', 'medium', '["Unsupervised Learning", "Supervised Learning", "Reinforcement Learning", "Semi-supervised Learning"]', 1, 1.0, TRUE),
('Which library is commonly used for deep learning in Python?', 'ai_ml', 'medium', '["NumPy", "Pandas", "TensorFlow", "Matplotlib"]', 2, 1.0, TRUE),
('What is the purpose of dropout in neural networks?', 'ai_ml', 'medium', '["Speed up training", "Prevent overfitting", "Increase accuracy", "Reduce memory usage"]', 1, 1.0, TRUE),
('Which of the following is a clustering algorithm?', 'ai_ml', 'medium', '["Linear Regression", "Decision Tree", "K-Means", "Naive Bayes"]', 2, 1.0, TRUE),
('What does NLP stand for?', 'ai_ml', 'medium', '["Neural Learning Process", "Natural Language Processing", "Network Layer Protocol", "Non-Linear Programming"]', 1, 1.0, TRUE),
('Which optimizer is an improvement over standard gradient descent?', 'ai_ml', 'medium', '["SGD", "Adam", "RMSprop", "All of the above"]', 3, 1.0, TRUE);

-- Insert ENGLISH Questions (6 questions)
INSERT INTO campus_drive_questions (question_text, category, difficulty, options, correct_option, marks, is_global) VALUES
('Choose the correct sentence:', 'english', 'medium', '["He don''t know nothing", "He doesn''t know anything", "He don''t know anything", "He doesn''t know nothing"]', 1, 1.0, TRUE),
('What is the synonym of Eloquent?', 'english', 'medium', '["Silent", "Articulate", "Humble", "Arrogant"]', 1, 1.0, TRUE),
('Choose the antonym of Benevolent:', 'english', 'medium', '["Kind", "Generous", "Malevolent", "Caring"]', 2, 1.0, TRUE),
('Fill in the blank: She ___ to the store yesterday.', 'english', 'medium', '["go", "goes", "went", "going"]', 2, 1.0, TRUE),
('Which sentence is grammatically correct?', 'english', 'medium', '["Me and him went to the park", "Him and me went to the park", "He and I went to the park", "I and he went to the park"]', 2, 1.0, TRUE),
('What does ubiquitous mean?', 'english', 'medium', '["Rare", "Present everywhere", "Unique", "Unknown"]', 1, 1.0, TRUE);

-- Verify insertion
SELECT 'Campus Drive Created:' as status, name FROM campus_drives;
SELECT 'Questions by Category:' as status, category, COUNT(*) as count FROM campus_drive_questions GROUP BY category;
SELECT 'Total Questions:' as status, COUNT(*) as total FROM campus_drive_questions;
