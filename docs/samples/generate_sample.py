"""
Generate Sample IEEE Documents

Run this script to generate sample IEEE documents:
    python generate_sample.py

Requirements:
    pip install python-docx reportlab Pillow
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def generate_samples():
    """Generate sample IEEE documents"""

    try:
        from cli.templates.ieee_templates import ProjectInfo, generate_all_ieee_documents
        from cli.templates.ieee_word_generator import IEEEWordGenerator
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you're running from the correct directory")
        return

    # Sample project information
    project_info = ProjectInfo(
        title="Online Examination System",
        team_name="Team Alpha",
        team_members=[
            "Rahul Kumar (20CS001)",
            "Priya Sharma (20CS002)",
            "Amit Singh (20CS003)",
            "Neha Patel (20CS004)"
        ],
        guide_name="Dr. Rajesh Kumar",
        college_name="XYZ University of Technology",
        department="Department of Computer Science and Engineering",
        academic_year="2024-2025",
        version="1.0"
    )

    output_dir = os.path.dirname(__file__)

    print("=" * 60)
    print("IEEE Document Generator - Sample Output")
    print("=" * 60)
    print(f"\nProject: {project_info.title}")
    print(f"Team: {project_info.team_name}")
    print(f"Output: {output_dir}")
    print()

    # Generate Markdown documents
    print("Generating Markdown documents...")
    try:
        md_files = generate_all_ieee_documents(project_info, output_dir)
        for doc_type, filepath in md_files.items():
            print(f"  ✓ {doc_type}: {filepath}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

    print()

    # Generate Word documents
    print("Generating Word documents...")
    try:
        from cli.templates.document_generator import DOCX_AVAILABLE

        if not DOCX_AVAILABLE:
            print("  ⚠ python-docx not installed")
            print("  Install with: pip install python-docx")
        else:
            generator = IEEEWordGenerator(project_info, output_dir)

            # Sample functional requirements
            functional_reqs = [
                {"id": "FR-001", "description": "System shall allow user registration with email and password", "priority": "High"},
                {"id": "FR-002", "description": "System shall authenticate users during login", "priority": "High"},
                {"id": "FR-003", "description": "System shall support OTP-based verification", "priority": "High"},
                {"id": "FR-004", "description": "System shall allow examiner to create new examinations", "priority": "High"},
                {"id": "FR-005", "description": "System shall support MCQ and descriptive questions", "priority": "High"},
                {"id": "FR-006", "description": "System shall randomize questions for each student", "priority": "Medium"},
                {"id": "FR-007", "description": "System shall enforce time limit with countdown timer", "priority": "High"},
                {"id": "FR-008", "description": "System shall auto-submit when time expires", "priority": "High"},
                {"id": "FR-009", "description": "System shall calculate and display results automatically", "priority": "High"},
                {"id": "FR-010", "description": "System shall generate detailed result reports", "priority": "Medium"},
            ]

            non_functional_reqs = [
                {"id": "NFR-001", "category": "Performance", "description": "Response time shall be less than 2 seconds", "priority": "High"},
                {"id": "NFR-002", "category": "Performance", "description": "System shall support 500 concurrent users", "priority": "High"},
                {"id": "NFR-003", "category": "Security", "description": "All passwords shall be encrypted using bcrypt", "priority": "High"},
                {"id": "NFR-004", "category": "Security", "description": "System shall use HTTPS for all communications", "priority": "High"},
                {"id": "NFR-005", "category": "Reliability", "description": "System uptime shall be 99.5%", "priority": "High"},
                {"id": "NFR-006", "category": "Usability", "description": "System shall work on mobile devices", "priority": "Medium"},
            ]

            use_cases = [
                "User Registration",
                "User Login",
                "Create Examination",
                "Add Questions",
                "Take Examination",
                "View Results",
                "Generate Reports"
            ]

            actors = ["Student", "Examiner", "Administrator"]

            # Generate SRS
            srs_path = generator.generate_srs(
                functional_requirements=functional_reqs,
                non_functional_requirements=non_functional_reqs,
                use_cases=use_cases,
                actors=actors,
                include_diagrams=True
            )
            print(f"  ✓ SRS: {srs_path}")

            # Generate SDD
            sdd_path = generator.generate_sdd(include_diagrams=True)
            print(f"  ✓ SDD: {sdd_path}")

            # Generate Test Doc
            test_cases = [
                {
                    "id": "TC-001",
                    "name": "User Registration - Valid Data",
                    "module": "Authentication",
                    "priority": "High",
                    "preconditions": "User is not registered",
                    "steps": [
                        "Navigate to registration page",
                        "Enter valid name",
                        "Enter valid email",
                        "Enter valid password",
                        "Click Register button"
                    ],
                    "expected": "User account is created and confirmation email is sent"
                },
                {
                    "id": "TC-002",
                    "name": "User Login - Valid Credentials",
                    "module": "Authentication",
                    "priority": "High",
                    "preconditions": "User is registered",
                    "steps": [
                        "Navigate to login page",
                        "Enter valid email",
                        "Enter valid password",
                        "Click Login button"
                    ],
                    "expected": "User is redirected to dashboard"
                },
                {
                    "id": "TC-003",
                    "name": "Create Examination",
                    "module": "Examination",
                    "priority": "High",
                    "preconditions": "Examiner is logged in",
                    "steps": [
                        "Navigate to Create Exam page",
                        "Enter exam title and description",
                        "Set duration and passing marks",
                        "Add questions from question bank",
                        "Click Create button"
                    ],
                    "expected": "Examination is created successfully"
                },
                {
                    "id": "TC-004",
                    "name": "Take Online Exam",
                    "module": "Examination",
                    "priority": "High",
                    "preconditions": "Student is logged in and exam is available",
                    "steps": [
                        "Navigate to Available Exams",
                        "Click Start Exam",
                        "Answer all questions",
                        "Click Submit button"
                    ],
                    "expected": "Exam is submitted and result is displayed"
                },
                {
                    "id": "TC-005",
                    "name": "Auto-submit on Timeout",
                    "module": "Examination",
                    "priority": "High",
                    "preconditions": "Student is taking exam",
                    "steps": [
                        "Start exam",
                        "Wait for timer to expire",
                        "Observe system behavior"
                    ],
                    "expected": "Exam is automatically submitted when time expires"
                },
            ]

            test_path = generator.generate_test_document(test_cases=test_cases)
            print(f"  ✓ Test Doc: {test_path}")

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 60)
    print("Document Generation Complete!")
    print("=" * 60)
    print()
    print("Generated files:")
    print(f"  📁 {output_dir}/")
    for f in os.listdir(output_dir):
        if f.endswith(('.md', '.docx', '.pdf')):
            size = os.path.getsize(os.path.join(output_dir, f))
            print(f"      📄 {f} ({size/1024:.1f} KB)")


if __name__ == "__main__":
    generate_samples()
