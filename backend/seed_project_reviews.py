"""
Seed Project Review Data

Creates sample projects with team members and reviews for testing the faculty reviews page.

Run with: python seed_project_reviews.py
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import select

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionLocal, init_db
from app.core.security import get_password_hash
from app.models.project_review import (
    ReviewProject, ProjectTeamMember, ProjectReview,
    ReviewPanelMember, ProjectType, ReviewType, ReviewStatus
)
from app.models.user import User, UserRole


# Sample project data
PROJECTS_DATA = [
    {
        'title': 'AI-Powered Healthcare Diagnosis System',
        'description': 'Machine learning system for early disease detection using patient symptoms and medical history',
        'project_type': ProjectType.major_project,
        'technology_stack': 'Python, TensorFlow, FastAPI, React',
        'domain': 'Healthcare AI',
        'team_name': 'Team MedAI',
        'semester': 7,
        'batch': '2021-2025',
        'department': 'Computer Science',
        'members': [
            {'name': 'Rahul Sharma', 'roll_number': '21CS001', 'email': 'rahul@college.edu', 'role': 'Team Lead'},
            {'name': 'Priya Patel', 'roll_number': '21CS002', 'email': 'priya@college.edu', 'role': 'ML Engineer'},
        ]
    },
    {
        'title': 'Smart Campus Management Portal',
        'description': 'Integrated system for managing college resources, attendance, and events',
        'project_type': ProjectType.major_project,
        'technology_stack': 'React, Node.js, MongoDB, Express',
        'domain': 'Education Technology',
        'team_name': 'Team CampusX',
        'semester': 7,
        'batch': '2021-2025',
        'department': 'Computer Science',
        'members': [
            {'name': 'Amit Kumar', 'roll_number': '21CS003', 'email': 'amit@college.edu', 'role': 'Team Lead'},
            {'name': 'Sneha Reddy', 'roll_number': '21CS004', 'email': 'sneha@college.edu', 'role': 'Frontend Dev'},
        ]
    },
    {
        'title': 'E-Commerce Price Tracker',
        'description': 'Web scraping tool to track and compare prices across e-commerce platforms',
        'project_type': ProjectType.mini_project,
        'technology_stack': 'Python, Flask, BeautifulSoup, SQLite',
        'domain': 'Web Development',
        'team_name': 'Team PriceWatch',
        'semester': 5,
        'batch': '2022-2026',
        'department': 'Computer Science',
        'members': [
            {'name': 'Vikram Singh', 'roll_number': '22CS010', 'email': 'vikram@college.edu', 'role': 'Team Lead'},
        ]
    },
    {
        'title': 'IoT-Based Smart Agriculture System',
        'description': 'Sensor-based monitoring system for crop health and irrigation management',
        'project_type': ProjectType.major_project,
        'technology_stack': 'Arduino, Python, MQTT, React Native',
        'domain': 'IoT & Agriculture',
        'team_name': 'Team AgriTech',
        'semester': 7,
        'batch': '2021-2025',
        'department': 'Electronics',
        'members': [
            {'name': 'Karthik Nair', 'roll_number': '21EC005', 'email': 'karthik@college.edu', 'role': 'Team Lead'},
            {'name': 'Deepa Menon', 'roll_number': '21EC006', 'email': 'deepa@college.edu', 'role': 'Hardware Dev'},
        ]
    },
    {
        'title': 'Student Portfolio Generator',
        'description': 'Automated portfolio website generator for students with customizable templates',
        'project_type': ProjectType.mini_project,
        'technology_stack': 'Next.js, Tailwind CSS, Firebase',
        'domain': 'Web Development',
        'team_name': 'Team PortfolioX',
        'semester': 5,
        'batch': '2022-2026',
        'department': 'Computer Science',
        'members': [
            {'name': 'Anjali Gupta', 'roll_number': '22CS015', 'email': 'anjali@college.edu', 'role': 'Team Lead'},
            {'name': 'Rohit Verma', 'roll_number': '22CS016', 'email': 'rohit@college.edu', 'role': 'Developer'},
        ]
    },
    {
        'title': 'Blockchain-Based Voting System',
        'description': 'Secure and transparent voting system using blockchain technology',
        'project_type': ProjectType.major_project,
        'technology_stack': 'Solidity, Ethereum, React, Web3.js',
        'domain': 'Blockchain',
        'team_name': 'Team SecureVote',
        'semester': 8,
        'batch': '2021-2025',
        'department': 'Computer Science',
        'members': [
            {'name': 'Arjun Mehta', 'roll_number': '21CS020', 'email': 'arjun@college.edu', 'role': 'Team Lead'},
            {'name': 'Kavya Sharma', 'roll_number': '21CS021', 'email': 'kavya@college.edu', 'role': 'Smart Contract Dev'},
        ]
    },
    {
        'title': 'Library Management System',
        'description': 'Digital system for managing library books, members, and transactions',
        'project_type': ProjectType.mini_project,
        'technology_stack': 'Java, Spring Boot, MySQL, Angular',
        'domain': 'Enterprise Software',
        'team_name': 'Team LibraryPro',
        'semester': 5,
        'batch': '2022-2026',
        'department': 'Information Technology',
        'members': [
            {'name': 'Neha Agarwal', 'roll_number': '22IT008', 'email': 'neha@college.edu', 'role': 'Team Lead'},
        ]
    },
    {
        'title': 'Mental Health Chatbot',
        'description': 'AI chatbot for mental health support and counseling assistance',
        'project_type': ProjectType.major_project,
        'technology_stack': 'Python, GPT API, FastAPI, Vue.js',
        'domain': 'Healthcare AI',
        'team_name': 'Team MindCare',
        'semester': 7,
        'batch': '2021-2025',
        'department': 'Computer Science',
        'members': [
            {'name': 'Sanya Joshi', 'roll_number': '21CS025', 'email': 'sanya@college.edu', 'role': 'Team Lead'},
            {'name': 'Manish Tiwari', 'roll_number': '21CS026', 'email': 'manish@college.edu', 'role': 'AI Developer'},
        ]
    },
    {
        'title': 'Online Examination System',
        'description': 'Proctored online examination platform with anti-cheating measures',
        'project_type': ProjectType.mini_project,
        'technology_stack': 'Django, PostgreSQL, React, WebRTC',
        'domain': 'Education Technology',
        'team_name': 'Team ExamPro',
        'semester': 6,
        'batch': '2022-2026',
        'department': 'Computer Science',
        'members': [
            {'name': 'Ravi Krishnan', 'roll_number': '22CS030', 'email': 'ravi@college.edu', 'role': 'Team Lead'},
            {'name': 'Meera Das', 'roll_number': '22CS031', 'email': 'meera@college.edu', 'role': 'Backend Dev'},
        ]
    },
    {
        'title': 'Food Delivery App',
        'description': 'Mobile application for food ordering and delivery tracking',
        'project_type': ProjectType.mini_project,
        'technology_stack': 'Flutter, Firebase, Node.js, Google Maps API',
        'domain': 'Mobile Development',
        'team_name': 'Team FoodieExpress',
        'semester': 6,
        'batch': '2022-2026',
        'department': 'Computer Science',
        'members': [
            {'name': 'Aditya Rao', 'roll_number': '22CS035', 'email': 'aditya@college.edu', 'role': 'Team Lead'},
        ]
    },
]


async def seed_project_reviews():
    """Seed project review data"""
    print("=" * 50)
    print("Seeding Project Reviews...")
    print("=" * 50)

    await init_db()

    async with AsyncSessionLocal() as db:
        # Get or create a faculty user for guide
        result = await db.execute(select(User).where(User.role == UserRole.FACULTY).limit(1))
        faculty = result.scalar_one_or_none()

        if not faculty:
            print("No faculty user found. Creating one...")
            faculty = User(
                email='guide@college.edu',
                hashed_password=get_password_hash('demo123'),
                full_name='Dr. Rajesh Kumar',
                role=UserRole.FACULTY,
                is_active=True,
                is_verified=True
            )
            db.add(faculty)
            await db.commit()
            await db.refresh(faculty)

        print(f"Using faculty: {faculty.full_name} ({faculty.email})")

        created_projects = 0
        created_reviews = 0

        for proj_data in PROJECTS_DATA:
            # Check if project exists
            result = await db.execute(
                select(ReviewProject).where(ReviewProject.title == proj_data['title'])
            )
            if result.scalar_one_or_none():
                print(f"  Skipping existing: {proj_data['title']}")
                continue

            # Create project
            project = ReviewProject(
                title=proj_data['title'],
                description=proj_data['description'],
                project_type=proj_data['project_type'],
                technology_stack=proj_data['technology_stack'],
                domain=proj_data['domain'],
                team_name=proj_data['team_name'],
                team_size=len(proj_data['members']),
                semester=proj_data['semester'],
                batch=proj_data['batch'],
                department=proj_data['department'],
                guide_id=faculty.id,
                guide_name=faculty.full_name,
                student_id=faculty.id,  # Using faculty as placeholder
            )
            db.add(project)
            await db.flush()

            # Add team members
            for member in proj_data['members']:
                team_member = ProjectTeamMember(
                    project_id=project.id,
                    name=member['name'],
                    roll_number=member['roll_number'],
                    email=member['email'],
                    role=member['role']
                )
                db.add(team_member)

            # Create reviews based on semester
            review_types = [ReviewType.review_1, ReviewType.review_2, ReviewType.review_3, ReviewType.final_review]
            base_date = datetime.now() - timedelta(days=60)

            for i, review_type in enumerate(review_types):
                # Determine status based on position and semester
                if i == 0:
                    status = ReviewStatus.completed
                    total_score = 75 + (hash(proj_data['title']) % 20)
                elif i == 1:
                    status = ReviewStatus.completed if proj_data['semester'] >= 7 else ReviewStatus.scheduled
                    total_score = 70 + (hash(proj_data['title']) % 25) if status == ReviewStatus.completed else 0
                elif i == 2:
                    status = ReviewStatus.in_progress if proj_data['semester'] >= 7 else ReviewStatus.scheduled
                    total_score = 0
                else:
                    status = ReviewStatus.scheduled
                    total_score = 0

                scheduled_date = base_date + timedelta(days=i * 21)

                review = ProjectReview(
                    project_id=project.id,
                    review_type=review_type,
                    review_number=i + 1,
                    scheduled_date=scheduled_date,
                    scheduled_time='10:00 AM',
                    venue=f'Seminar Hall {(i % 3) + 1}',
                    status=status,
                    total_score=total_score,
                    innovation_score=total_score * 0.2 if total_score else 0,
                    technical_score=total_score * 0.25 if total_score else 0,
                    implementation_score=total_score * 0.25 if total_score else 0,
                    documentation_score=total_score * 0.15 if total_score else 0,
                    presentation_score=total_score * 0.15 if total_score else 0,
                )
                db.add(review)
                await db.flush()

                # Add panel member
                panel_member = ReviewPanelMember(
                    review_id=review.id,
                    faculty_id=faculty.id,
                    name=faculty.full_name,
                    designation='Associate Professor',
                    department=proj_data['department'],
                    email=faculty.email,
                    role='Lead',
                    is_lead=True
                )
                db.add(panel_member)
                created_reviews += 1

            created_projects += 1
            print(f"  Created: {proj_data['title']} ({proj_data['team_name']})")

        await db.commit()

        print("=" * 50)
        print(f"Seeded Successfully!")
        print(f"  Projects: {created_projects}")
        print(f"  Reviews: {created_reviews}")
        print("=" * 50)
        print("\nSample Data Summary:")
        print("-" * 50)
        print("| Semester | Projects |")
        print("-" * 50)
        print("| Sem 5    | 3 mini projects |")
        print("| Sem 6    | 2 mini projects |")
        print("| Sem 7    | 4 major projects |")
        print("| Sem 8    | 1 major project |")
        print("-" * 50)


if __name__ == "__main__":
    asyncio.run(seed_project_reviews())
