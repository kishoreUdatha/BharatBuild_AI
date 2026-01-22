"""
Seed script for Campus Drive - Creates sample questions and a default drive
Run this script to populate the database with sample data.
Usage: python seed_campus_drive.py
"""

import asyncio
import sys
from datetime import datetime, timedelta

# Add the backend directory to the path
sys.path.insert(0, '.')

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.campus_drive import (
    CampusDrive, CampusDriveQuestion, QuestionCategory, QuestionDifficulty
)

# Sample questions for each category (5 Logical, 10 Technical, 10 AI/ML, 5 English)
LOGICAL_QUESTIONS = [
    {
        "question": "If all Bloops are Razzies and all Razzies are Lazzies, then all Bloops are definitely Lazzies. Is this statement true?",
        "options": ["True", "False", "Cannot be determined", "Partially true"],
        "correct": 0
    },
    {
        "question": "A is the brother of B. B is the sister of C. D is the father of A. How is C related to D?",
        "options": ["Daughter", "Son", "Granddaughter", "Cannot be determined"],
        "correct": 0
    },
    {
        "question": "Complete the series: 2, 6, 12, 20, 30, ?",
        "options": ["40", "42", "44", "46"],
        "correct": 1
    },
    {
        "question": "Find the odd one out: 8, 27, 64, 100, 125, 216",
        "options": ["27", "64", "100", "125"],
        "correct": 2
    },
    {
        "question": "A clock shows 3:15. What is the angle between the hour and minute hands?",
        "options": ["0 degrees", "7.5 degrees", "15 degrees", "22.5 degrees"],
        "correct": 1
    },
    {
        "question": "In a row of students, Ram is 7th from the left and Shyam is 9th from the right. If they interchange, Ram becomes 11th from left. How many students are in the row?",
        "options": ["17", "18", "19", "20"],
        "correct": 2
    },
]

TECHNICAL_QUESTIONS = [
    {
        "question": "What is the time complexity of binary search?",
        "options": ["O(n)", "O(log n)", "O(n log n)", "O(1)"],
        "correct": 1
    },
    {
        "question": "Which data structure uses LIFO (Last In First Out)?",
        "options": ["Queue", "Stack", "Array", "Linked List"],
        "correct": 1
    },
    {
        "question": "What is the output of: print(type([]) == type({}))?",
        "options": ["True", "False", "Error", "None"],
        "correct": 1
    },
    {
        "question": "Which HTTP method is idempotent?",
        "options": ["POST", "GET", "PATCH", "None of the above"],
        "correct": 1
    },
    {
        "question": "What does SQL stand for?",
        "options": ["Structured Query Language", "Simple Query Language", "Standard Query Language", "Sequential Query Language"],
        "correct": 0
    },
    {
        "question": "Which sorting algorithm has the best average case time complexity?",
        "options": ["Bubble Sort", "Insertion Sort", "Quick Sort", "Selection Sort"],
        "correct": 2
    },
    {
        "question": "What is the purpose of the 'finally' block in exception handling?",
        "options": ["Execute only if exception occurs", "Execute only if no exception", "Always execute regardless of exception", "Skip exception handling"],
        "correct": 2
    },
    {
        "question": "Which of the following is NOT a valid JavaScript data type?",
        "options": ["Boolean", "Undefined", "Integer", "Symbol"],
        "correct": 2
    },
    {
        "question": "What is the difference between == and === in JavaScript?",
        "options": ["No difference", "=== checks type also", "== checks type also", "=== is faster"],
        "correct": 1
    },
    {
        "question": "Which CSS property is used to change the background color?",
        "options": ["color", "bgcolor", "background-color", "background"],
        "correct": 2
    },
    {
        "question": "What is Git primarily used for?",
        "options": ["Database management", "Version control", "Web hosting", "Compilation"],
        "correct": 1
    },
    {
        "question": "Which of the following is a NoSQL database?",
        "options": ["MySQL", "PostgreSQL", "MongoDB", "Oracle"],
        "correct": 2
    },
]

AI_ML_QUESTIONS = [
    {
        "question": "What does CNN stand for in deep learning?",
        "options": ["Central Neural Network", "Convolutional Neural Network", "Connected Neural Network", "Computed Neural Network"],
        "correct": 1
    },
    {
        "question": "Which algorithm is commonly used for classification problems?",
        "options": ["Linear Regression", "K-Means Clustering", "Random Forest", "PCA"],
        "correct": 2
    },
    {
        "question": "What is overfitting in machine learning?",
        "options": ["Model performs well on training data but poorly on test data", "Model performs poorly on training data", "Model takes too long to train", "Model uses too much memory"],
        "correct": 0
    },
    {
        "question": "Which activation function is most commonly used in hidden layers of neural networks?",
        "options": ["Sigmoid", "Tanh", "ReLU", "Softmax"],
        "correct": 2
    },
    {
        "question": "What is the purpose of the learning rate in gradient descent?",
        "options": ["Controls model complexity", "Controls step size in optimization", "Controls regularization", "Controls batch size"],
        "correct": 1
    },
    {
        "question": "Which metric is used to evaluate classification models?",
        "options": ["RMSE", "MAE", "Accuracy", "R-squared"],
        "correct": 2
    },
    {
        "question": "What type of machine learning is used when we have labeled data?",
        "options": ["Unsupervised Learning", "Supervised Learning", "Reinforcement Learning", "Semi-supervised Learning"],
        "correct": 1
    },
    {
        "question": "Which library is commonly used for deep learning in Python?",
        "options": ["NumPy", "Pandas", "TensorFlow", "Matplotlib"],
        "correct": 2
    },
    {
        "question": "What is the purpose of dropout in neural networks?",
        "options": ["Speed up training", "Prevent overfitting", "Increase accuracy", "Reduce memory usage"],
        "correct": 1
    },
    {
        "question": "Which of the following is a clustering algorithm?",
        "options": ["Linear Regression", "Decision Tree", "K-Means", "Naive Bayes"],
        "correct": 2
    },
    {
        "question": "What does NLP stand for?",
        "options": ["Neural Learning Process", "Natural Language Processing", "Network Layer Protocol", "Non-Linear Programming"],
        "correct": 1
    },
    {
        "question": "Which optimizer is an improvement over standard gradient descent?",
        "options": ["SGD", "Adam", "RMSprop", "All of the above"],
        "correct": 3
    },
]

ENGLISH_QUESTIONS = [
    {
        "question": "Choose the correct sentence:",
        "options": ["He don't know nothing", "He doesn't know anything", "He don't know anything", "He doesn't know nothing"],
        "correct": 1
    },
    {
        "question": "What is the synonym of 'Eloquent'?",
        "options": ["Silent", "Articulate", "Humble", "Arrogant"],
        "correct": 1
    },
    {
        "question": "Choose the antonym of 'Benevolent':",
        "options": ["Kind", "Generous", "Malevolent", "Caring"],
        "correct": 2
    },
    {
        "question": "Fill in the blank: She ___ to the store yesterday.",
        "options": ["go", "goes", "went", "going"],
        "correct": 2
    },
    {
        "question": "Which sentence is grammatically correct?",
        "options": ["Me and him went to the park", "Him and me went to the park", "He and I went to the park", "I and he went to the park"],
        "correct": 2
    },
    {
        "question": "What does 'ubiquitous' mean?",
        "options": ["Rare", "Present everywhere", "Unique", "Unknown"],
        "correct": 1
    },
]


async def seed_database():
    """Seed the database with sample data"""

    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Create a default campus drive
            drive = CampusDrive(
                name="Campus Placement Drive 2026",
                company_name="BharatBuild",
                description="Annual campus placement drive for engineering students. Test your skills in logical reasoning, technical knowledge, AI/ML concepts, and English proficiency.",
                registration_end=datetime.utcnow() + timedelta(days=30),
                quiz_date=datetime.utcnow() + timedelta(days=1),
                quiz_duration_minutes=60,
                passing_percentage=60.0,
                total_questions=30,
                logical_questions=5,
                technical_questions=10,
                ai_ml_questions=10,
                english_questions=5,
                is_active=True
            )
            session.add(drive)
            await session.flush()

            print(f"Created campus drive: {drive.name}")

            # Add Logical Questions
            for q in LOGICAL_QUESTIONS:
                question = CampusDriveQuestion(
                    question_text=q["question"],
                    category=QuestionCategory.LOGICAL,
                    difficulty=QuestionDifficulty.MEDIUM,
                    options=q["options"],
                    correct_option=q["correct"],
                    marks=1.0,
                    is_global=True
                )
                session.add(question)

            print(f"Added {len(LOGICAL_QUESTIONS)} logical questions")

            # Add Technical Questions
            for q in TECHNICAL_QUESTIONS:
                question = CampusDriveQuestion(
                    question_text=q["question"],
                    category=QuestionCategory.TECHNICAL,
                    difficulty=QuestionDifficulty.MEDIUM,
                    options=q["options"],
                    correct_option=q["correct"],
                    marks=1.0,
                    is_global=True
                )
                session.add(question)

            print(f"Added {len(TECHNICAL_QUESTIONS)} technical questions")

            # Add AI/ML Questions
            for q in AI_ML_QUESTIONS:
                question = CampusDriveQuestion(
                    question_text=q["question"],
                    category=QuestionCategory.AI_ML,
                    difficulty=QuestionDifficulty.MEDIUM,
                    options=q["options"],
                    correct_option=q["correct"],
                    marks=1.0,
                    is_global=True
                )
                session.add(question)

            print(f"Added {len(AI_ML_QUESTIONS)} AI/ML questions")

            # Add English Questions
            for q in ENGLISH_QUESTIONS:
                question = CampusDriveQuestion(
                    question_text=q["question"],
                    category=QuestionCategory.ENGLISH,
                    difficulty=QuestionDifficulty.MEDIUM,
                    options=q["options"],
                    correct_option=q["correct"],
                    marks=1.0,
                    is_global=True
                )
                session.add(question)

            print(f"Added {len(ENGLISH_QUESTIONS)} English questions")

            await session.commit()

            total_questions = len(LOGICAL_QUESTIONS) + len(TECHNICAL_QUESTIONS) + len(AI_ML_QUESTIONS) + len(ENGLISH_QUESTIONS)
            print(f"\n{'='*50}")
            print(f"Successfully seeded database!")
            print(f"- 1 Campus Drive created")
            print(f"- {total_questions} questions added")
            print(f"  - Logical: {len(LOGICAL_QUESTIONS)}")
            print(f"  - Technical: {len(TECHNICAL_QUESTIONS)}")
            print(f"  - AI/ML: {len(AI_ML_QUESTIONS)}")
            print(f"  - English: {len(ENGLISH_QUESTIONS)}")
            print(f"{'='*50}")

        except Exception as e:
            print(f"Error seeding database: {e}")
            await session.rollback()
            raise

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_database())
