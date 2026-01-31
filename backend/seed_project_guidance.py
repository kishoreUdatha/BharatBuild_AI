"""
Seed sample data for Project Guidance module
"""
import asyncio
import sys
sys.path.insert(0, '.')

from datetime import datetime, timedelta
from uuid import uuid4
import random

async def seed_data():
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import select
    from app.core.config import settings
    from app.models.project_review import (
        ReviewProject, ProjectReview, ReviewPanelMember, ProjectTeamMember,
        ReviewType, ReviewStatus, ProjectType, ReviewDecision, VivaReadiness
    )
    from app.models.user import User

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Sample data
    teams = [
        {"name": "Tech Titans", "members": ["Rahul Kumar", "Priya Sharma", "Amit Singh"]},
        {"name": "Code Crusaders", "members": ["Sneha Patel", "Vikram Reddy", "Ananya Gupta"]},
        {"name": "Binary Builders", "members": ["Karthik Nair", "Meera Iyer", "Rohan Das"]},
        {"name": "Digital Dynamos", "members": ["Arun Joshi", "Kavya Menon", "Sanjay Verma"]},
        {"name": "Innovate Squad", "members": ["Neha Agarwal", "Raj Malhotra", "Pooja Saxena"]},
        {"name": "Pixel Pioneers", "members": ["Arjun Kapoor", "Divya Krishnan", "Manish Tiwari"]},
        {"name": "Cloud Crafters", "members": ["Shreya Bansal", "Nikhil Chauhan", "Ritu Sharma"]},
        {"name": "AI Architects", "members": ["Varun Mehta", "Anjali Rao", "Deepak Pillai"]},
        {"name": "Data Wizards", "members": ["Swati Deshmukh", "Gaurav Mishra", "Lakshmi Narayan"]},
        {"name": "Web Warriors", "members": ["Akash Bhatt", "Simran Kaur", "Vivek Pandey"]},
        {"name": "Smart Solvers", "members": ["Harini Venkat", "Mohit Agrawal", "Tanvi Shah"]},
        {"name": "Logic Lords", "members": ["Pranav Sinha", "Ishita Jain", "Suresh Kumar"]},
    ]

    projects_data = [
        {"title": "Smart Campus Navigation System", "tech": "React, Node.js, MongoDB", "domain": "IoT & Navigation", "type": "major"},
        {"title": "AI-Powered Attendance System", "tech": "Python, TensorFlow, Flask", "domain": "Machine Learning", "type": "major"},
        {"title": "Online Exam Portal", "tech": "Next.js, PostgreSQL, Redis", "domain": "Education Technology", "type": "mini"},
        {"title": "Hospital Management System", "tech": "Java, Spring Boot, MySQL", "domain": "Healthcare", "type": "major"},
        {"title": "E-Commerce Platform", "tech": "MERN Stack", "domain": "E-Commerce", "type": "mini"},
        {"title": "Blockchain Voting System", "tech": "Solidity, React, Ethereum", "domain": "Blockchain", "type": "major"},
        {"title": "Food Delivery App", "tech": "Flutter, Firebase", "domain": "Mobile Apps", "type": "mini"},
        {"title": "Library Management System", "tech": "PHP, Laravel, MySQL", "domain": "Management", "type": "mini"},
        {"title": "Sentiment Analysis Tool", "tech": "Python, NLP, FastAPI", "domain": "NLP", "type": "major"},
        {"title": "IoT Home Automation", "tech": "Arduino, React Native, MQTT", "domain": "IoT", "type": "major"},
        {"title": "Student Feedback System", "tech": "Django, PostgreSQL", "domain": "Education", "type": "mini"},
        {"title": "Real-time Chat Application", "tech": "Socket.io, Express, MongoDB", "domain": "Communication", "type": "mini"},
    ]

    guides = ["Dr. Ramesh Kumar", "Prof. Sunita Sharma", "Dr. Anil Verma", "Prof. Meena Iyer", "Dr. Suresh Nair"]

    async with async_session() as session:
        # Get any existing user to use as student_id
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()

        if not user:
            print("No users found in database. Please create a user first.")
            return

        student_id = user.id
        print(f"Using user '{user.email}' as student for all projects")

        projects = []

        # Create projects for semesters 5, 6, 7, 8
        for i, (team, proj) in enumerate(zip(teams, projects_data)):
            semester = random.choice([5, 6, 7, 8])

            project = ReviewProject(
                id=uuid4(),
                title=proj["title"],
                description=f"A comprehensive {proj['domain'].lower()} project focusing on {proj['title'].lower()}. This project aims to solve real-world problems using modern technologies.",
                project_type=ProjectType.major_project if proj["type"] == "major" else ProjectType.mini_project,
                technology_stack=proj["tech"],
                domain=proj["domain"],
                team_name=team["name"],
                team_size=len(team["members"]),
                student_id=student_id,
                semester=semester,
                batch="2021-25",
                department="CSE",
                guide_name=random.choice(guides),
                total_score=0,
                average_score=0,
                is_approved=False,
                is_completed=False
            )
            session.add(project)
            projects.append((project, team, i))

        await session.flush()

        # Create team members for each project
        for project, team, idx in projects:
            for j, member_name in enumerate(team["members"]):
                team_member = ProjectTeamMember(
                    id=uuid4(),
                    project_id=project.id,
                    name=member_name,
                    roll_number=f"21CSE{100+idx*3+j}",
                    role="Team Lead" if j == 0 else "Developer"
                )
                session.add(team_member)

        # Create reviews for each project
        review_types = [ReviewType.review_1, ReviewType.review_2, ReviewType.review_3, ReviewType.final_review]

        for project, team, idx in projects:
            # Randomly decide how many reviews are scheduled/completed
            num_reviews = random.randint(1, 4)

            for i in range(num_reviews):
                review_type = review_types[i]

                # Determine status based on position
                if i < num_reviews - 1:
                    status = ReviewStatus.completed
                    total_score = random.randint(60, 95)
                    decision = ReviewDecision.approved if total_score >= 50 else ReviewDecision.revision_needed
                elif i == num_reviews - 1 and random.random() > 0.5:
                    status = ReviewStatus.in_progress
                    total_score = 0
                    decision = None
                else:
                    status = ReviewStatus.scheduled
                    total_score = 0
                    decision = None

                scheduled_date = datetime.now() - timedelta(days=random.randint(0, 60))

                review = ProjectReview(
                    id=uuid4(),
                    project_id=project.id,
                    review_type=review_type,
                    review_number=i + 1,
                    scheduled_date=scheduled_date,
                    scheduled_time="10:00 AM" if i % 2 == 0 else "2:00 PM",
                    venue=f"Room {random.choice(['A', 'B', 'C'])}-{random.randint(101, 110)}",
                    status=status,
                    total_score=total_score,
                    decision=decision,
                    overall_feedback="Good progress shown" if status == ReviewStatus.completed else None,
                    started_at=scheduled_date if status != ReviewStatus.scheduled else None,
                    completed_at=scheduled_date if status == ReviewStatus.completed else None
                )
                session.add(review)

                await session.flush()

                # Add panel member for the review
                panel_member = ReviewPanelMember(
                    id=uuid4(),
                    review_id=review.id,
                    name=random.choice(guides),
                    role="Guide" if i == 0 else "Panel Member",
                    is_lead=i == 0
                )
                session.add(panel_member)

                # Update project scores if review completed
                if status == ReviewStatus.completed:
                    project.total_score += total_score
                    project.current_review = i + 1

        # Calculate average scores
        for project, team, idx in projects:
            completed_reviews = sum(1 for _ in range(4) if project.total_score > 0)
            if completed_reviews > 0:
                project.average_score = project.total_score / max(completed_reviews, 1)

        await session.commit()
        print(f"\nSuccessfully created {len(projects)} projects with reviews!")

        # Print summary
        for sem in [5, 6, 7, 8]:
            count = sum(1 for p, t, i in projects if p.semester == sem)
            print(f"  Semester {sem}: {count} projects")

if __name__ == "__main__":
    asyncio.run(seed_data())
