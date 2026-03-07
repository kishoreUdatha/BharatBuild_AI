"""
Sample Data for NAAC 7 Criteria (700 Marks Total)
Comprehensive seed data for all criteria with metrics, KPIs, and evidence
"""

from datetime import datetime, date
from typing import Dict, List, Any

# ============================================================================
# CRITERION 1: CURRICULAR ASPECTS (150 Marks)
# ============================================================================

CRITERION_1_DATA = {
    "criterion_id": "C1",
    "criterion_name": "Curricular Aspects",
    "max_marks": 150,
    "key_indicators": [
        {"id": "1.1", "name": "Curricular Planning and Implementation", "marks": 50},
        {"id": "1.2", "name": "Academic Flexibility", "marks": 50},
        {"id": "1.3", "name": "Curriculum Enrichment", "marks": 30},
        {"id": "1.4", "name": "Feedback System", "marks": 20},
    ],
    "sample_metrics": {
        "1.1.1": {
            "metric": "Institution ensures effective curriculum planning and delivery",
            "data": {
                "curriculum_revision_year": "2023-24",
                "programs_revised": 45,
                "total_programs": 52,
                "revision_percentage": 86.5,
                "bos_meetings_held": 24,
                "academic_council_meetings": 4,
            },
            "evidence": [
                "Minutes of BoS meetings",
                "Academic Council resolutions",
                "Curriculum revision documents",
                "Program structure documents",
            ]
        },
        "1.2.1": {
            "metric": "Number of Add on/Certificate programs offered",
            "data": {
                "certificate_programs": 28,
                "diploma_programs": 12,
                "value_added_courses": 35,
                "mooc_courses_integrated": 45,
                "students_enrolled": 2850,
            },
            "evidence": [
                "List of certificate programs",
                "Course completion certificates",
                "Student enrollment data",
            ]
        },
        "1.2.2": {
            "metric": "Percentage of students enrolled in Certificate/Add-on programs",
            "data": {
                "total_students": 5200,
                "enrolled_students": 2850,
                "percentage": 54.8,
            }
        },
        "1.3.1": {
            "metric": "Institution integrates crosscutting issues",
            "data": {
                "gender_courses": 8,
                "environment_courses": 12,
                "human_values_courses": 6,
                "professional_ethics_courses": 10,
                "total_courses_with_integration": 36,
            }
        },
        "1.3.2": {
            "metric": "Average percentage of courses with focus on employability/entrepreneurship",
            "data": {
                "employability_courses": 85,
                "entrepreneurship_courses": 15,
                "skill_development_courses": 42,
                "total_courses": 320,
                "percentage": 44.4,
            }
        },
        "1.4.1": {
            "metric": "Structured feedback system for curriculum",
            "data": {
                "student_feedback_collected": True,
                "teacher_feedback_collected": True,
                "employer_feedback_collected": True,
                "alumni_feedback_collected": True,
                "feedback_analysis_done": True,
                "action_taken_reports": 12,
            }
        },
    },
    "score": 138,
    "percentage": 92.0,
}

# ============================================================================
# CRITERION 2: TEACHING-LEARNING AND EVALUATION (200 Marks)
# ============================================================================

CRITERION_2_DATA = {
    "criterion_id": "C2",
    "criterion_name": "Teaching-Learning and Evaluation",
    "max_marks": 200,
    "key_indicators": [
        {"id": "2.1", "name": "Student Enrollment and Profile", "marks": 30},
        {"id": "2.2", "name": "Student Teacher Ratio", "marks": 20},
        {"id": "2.3", "name": "Teaching-Learning Process", "marks": 40},
        {"id": "2.4", "name": "Teacher Profile and Quality", "marks": 50},
        {"id": "2.5", "name": "Evaluation Process and Reforms", "marks": 30},
        {"id": "2.6", "name": "Student Performance and Learning Outcomes", "marks": 30},
    ],
    "sample_metrics": {
        "2.1.1": {
            "metric": "Enrollment percentage",
            "data": {
                "sanctioned_intake": 1800,
                "enrolled_students": 1720,
                "enrollment_percentage": 95.6,
                "reserved_category_enrolled": 720,
                "reserved_percentage": 41.9,
            }
        },
        "2.1.2": {
            "metric": "Average percentage of seats filled against reserved categories",
            "data": {
                "sc_seats_filled": 98,
                "st_seats_filled": 95,
                "obc_seats_filled": 99,
                "ews_seats_filled": 92,
                "pwd_seats_filled": 85,
            }
        },
        "2.2.1": {
            "metric": "Student-Teacher Ratio",
            "data": {
                "total_students": 5200,
                "total_teachers": 320,
                "ratio": "16:1",
            }
        },
        "2.3.1": {
            "metric": "Student-centric methods",
            "data": {
                "experiential_learning_courses": 45,
                "participative_learning_courses": 68,
                "problem_solving_courses": 52,
                "ict_enabled_courses": 285,
                "flipped_classroom_courses": 24,
            }
        },
        "2.3.2": {
            "metric": "Teachers use ICT-enabled tools",
            "data": {
                "teachers_using_ict": 298,
                "total_teachers": 320,
                "percentage": 93.1,
                "lms_usage": True,
                "smart_boards": 120,
                "digital_content_created": 450,
            }
        },
        "2.4.1": {
            "metric": "Percentage of full time teachers with Ph.D./D.M/M.Ch.",
            "data": {
                "phd_teachers": 185,
                "total_teachers": 320,
                "percentage": 57.8,
            }
        },
        "2.4.2": {
            "metric": "Faculty with industry experience",
            "data": {
                "industry_experience_teachers": 95,
                "avg_experience_years": 8.5,
            }
        },
        "2.5.1": {
            "metric": "Mechanism of internal/external assessment",
            "data": {
                "continuous_assessment": True,
                "online_examinations": True,
                "automated_grading": True,
                "anti_plagiarism_check": True,
                "grievance_redressal": True,
            }
        },
        "2.6.1": {
            "metric": "Programme and course outcomes",
            "data": {
                "programs_with_cos_defined": 52,
                "total_programs": 52,
                "percentage": 100,
                "attainment_process_documented": True,
            }
        },
        "2.6.2": {
            "metric": "Pass percentage of final year students",
            "data": {
                "appeared": 1450,
                "passed": 1392,
                "pass_percentage": 96.0,
                "first_class_percentage": 72.5,
            }
        },
    },
    "score": 185,
    "percentage": 92.5,
}

# ============================================================================
# CRITERION 3: RESEARCH, INNOVATIONS AND EXTENSION (150 Marks)
# ============================================================================

CRITERION_3_DATA = {
    "criterion_id": "C3",
    "criterion_name": "Research, Innovations and Extension",
    "max_marks": 150,
    "key_indicators": [
        {"id": "3.1", "name": "Resource Mobilization for Research", "marks": 20},
        {"id": "3.2", "name": "Innovation Ecosystem", "marks": 20},
        {"id": "3.3", "name": "Research Publications and Awards", "marks": 50},
        {"id": "3.4", "name": "Extension Activities", "marks": 40},
        {"id": "3.5", "name": "Collaboration", "marks": 20},
    ],
    "sample_metrics": {
        "3.1.1": {
            "metric": "Grants received from Government and non-government agencies",
            "data": {
                "government_grants_rs_lakhs": 485,
                "non_government_grants_rs_lakhs": 125,
                "total_grants": 610,
                "ongoing_projects": 42,
                "completed_projects": 28,
            }
        },
        "3.1.2": {
            "metric": "Teachers recognized as research guides",
            "data": {
                "phd_guides": 85,
                "mphil_guides": 45,
                "scholars_enrolled": 180,
                "phd_awarded": 35,
            }
        },
        "3.2.1": {
            "metric": "Institution has incubation centre",
            "data": {
                "incubation_centre": True,
                "startups_incubated": 28,
                "successful_startups": 12,
                "funding_raised_lakhs": 85,
                "mentors_available": 25,
            }
        },
        "3.2.2": {
            "metric": "Number of workshops/seminars on IPR",
            "data": {
                "ipr_workshops": 12,
                "innovation_workshops": 18,
                "entrepreneurship_workshops": 15,
                "participants": 2500,
            }
        },
        "3.3.1": {
            "metric": "Research papers published per teacher",
            "data": {
                "scopus_papers": 285,
                "web_of_science_papers": 180,
                "ugc_care_papers": 420,
                "total_papers": 885,
                "papers_per_teacher": 2.77,
            }
        },
        "3.3.2": {
            "metric": "Books and chapters published",
            "data": {
                "books_published": 45,
                "book_chapters": 128,
                "edited_volumes": 12,
                "isbn_publications": 52,
            }
        },
        "3.3.3": {
            "metric": "Patents published/awarded",
            "data": {
                "patents_filed": 28,
                "patents_published": 18,
                "patents_granted": 8,
                "design_patents": 3,
                "copyrights": 12,
            }
        },
        "3.4.1": {
            "metric": "Extension activities in the neighbourhood community",
            "data": {
                "nss_units": 4,
                "nss_volunteers": 400,
                "ncc_units": 2,
                "ncc_cadets": 150,
                "blood_donation_camps": 8,
                "health_camps": 12,
                "literacy_programs": 15,
                "villages_adopted": 5,
            }
        },
        "3.4.2": {
            "metric": "Awards and recognitions received for extension activities",
            "data": {
                "national_awards": 3,
                "state_awards": 8,
                "university_awards": 12,
            }
        },
        "3.5.1": {
            "metric": "MoUs with institutions/industries",
            "data": {
                "academic_mous": 45,
                "industry_mous": 35,
                "international_mous": 18,
                "functional_mous": 85,
                "activities_conducted": 250,
            }
        },
    },
    "score": 142,
    "percentage": 94.7,
}

# ============================================================================
# CRITERION 4: INFRASTRUCTURE AND LEARNING RESOURCES (100 Marks)
# ============================================================================

CRITERION_4_DATA = {
    "criterion_id": "C4",
    "criterion_name": "Infrastructure and Learning Resources",
    "max_marks": 100,
    "key_indicators": [
        {"id": "4.1", "name": "Physical Facilities", "marks": 30},
        {"id": "4.2", "name": "Library as a Learning Resource", "marks": 30},
        {"id": "4.3", "name": "IT Infrastructure", "marks": 20},
        {"id": "4.4", "name": "Maintenance of Campus Infrastructure", "marks": 20},
    ],
    "sample_metrics": {
        "4.1.1": {
            "metric": "Classrooms and seminar halls with ICT facilities",
            "data": {
                "total_classrooms": 150,
                "ict_enabled_classrooms": 145,
                "percentage": 96.7,
                "seminar_halls": 12,
                "conference_rooms": 8,
                "auditoriums": 3,
            }
        },
        "4.1.2": {
            "metric": "Expenditure on infrastructure augmentation",
            "data": {
                "infrastructure_expenditure_lakhs": 285,
                "equipment_expenditure_lakhs": 125,
                "total_expenditure": 410,
            }
        },
        "4.2.1": {
            "metric": "Library is automated using ILMS",
            "data": {
                "ilms_software": "KOHA",
                "fully_automated": True,
                "barcode_enabled": True,
                "rfid_enabled": True,
                "opac_available": True,
            }
        },
        "4.2.2": {
            "metric": "Library resources",
            "data": {
                "total_books": 125000,
                "reference_books": 15000,
                "journals_subscribed": 285,
                "e_journals": 8500,
                "e_books": 45000,
                "databases": 12,
                "digital_repository_items": 5000,
            }
        },
        "4.2.3": {
            "metric": "Annual expenditure on books and journals",
            "data": {
                "books_expenditure_lakhs": 25,
                "journals_expenditure_lakhs": 45,
                "e_resources_expenditure_lakhs": 35,
                "total_expenditure": 105,
            }
        },
        "4.3.1": {
            "metric": "Institution has adequate IT facilities",
            "data": {
                "computers": 1200,
                "computer_student_ratio": "1:4",
                "internet_bandwidth_mbps": 1000,
                "wifi_coverage_percentage": 100,
                "servers": 25,
            }
        },
        "4.3.2": {
            "metric": "Student-Computer ratio",
            "data": {
                "total_computers": 1200,
                "total_students": 5200,
                "ratio": "1:4.3",
            }
        },
        "4.4.1": {
            "metric": "Expenditure on maintenance of infrastructure",
            "data": {
                "physical_facilities_lakhs": 85,
                "academic_support_lakhs": 45,
                "it_maintenance_lakhs": 35,
                "total_maintenance": 165,
            }
        },
        "4.4.2": {
            "metric": "Systems and procedures for maintaining infrastructure",
            "data": {
                "maintenance_policy": True,
                "annual_maintenance_contracts": 45,
                "dedicated_maintenance_staff": 35,
                "grievance_redressal_time_days": 2,
            }
        },
    },
    "score": 92,
    "percentage": 92.0,
}

# ============================================================================
# CRITERION 5: STUDENT SUPPORT AND PROGRESSION (100 Marks)
# ============================================================================

CRITERION_5_DATA = {
    "criterion_id": "C5",
    "criterion_name": "Student Support and Progression",
    "max_marks": 100,
    "key_indicators": [
        {"id": "5.1", "name": "Student Support", "marks": 30},
        {"id": "5.2", "name": "Student Progression", "marks": 30},
        {"id": "5.3", "name": "Student Participation and Activities", "marks": 25},
        {"id": "5.4", "name": "Alumni Engagement", "marks": 15},
    ],
    "sample_metrics": {
        "5.1.1": {
            "metric": "Students benefited by scholarships and freeships",
            "data": {
                "government_scholarships": 1250,
                "non_government_scholarships": 380,
                "institutional_scholarships": 450,
                "total_benefited": 2080,
                "total_amount_lakhs": 285,
            }
        },
        "5.1.2": {
            "metric": "Capacity building and skills enhancement",
            "data": {
                "soft_skills_programs": 25,
                "language_programs": 12,
                "life_skills_programs": 18,
                "ict_programs": 35,
                "yoga_wellness_programs": 8,
                "students_benefited": 3500,
            }
        },
        "5.1.3": {
            "metric": "Guidance for competitive examinations",
            "data": {
                "coaching_programs": 12,
                "gate_coaching": True,
                "civil_services_coaching": True,
                "cat_gre_coaching": True,
                "students_enrolled": 850,
                "students_qualified": 125,
            }
        },
        "5.1.4": {
            "metric": "Career counselling and placement",
            "data": {
                "placement_cell_established": True,
                "career_counselling_sessions": 45,
                "companies_visited": 185,
                "students_placed": 1380,
                "placement_percentage": 95.2,
                "avg_package_lpa": 8.5,
                "highest_package_lpa": 45,
            }
        },
        "5.2.1": {
            "metric": "Students qualifying state/national level examinations",
            "data": {
                "net_qualified": 28,
                "slet_qualified": 15,
                "gate_qualified": 85,
                "cat_qualified": 42,
                "civil_services_qualified": 5,
            }
        },
        "5.2.2": {
            "metric": "Students progressing to higher education",
            "data": {
                "total_outgoing": 1450,
                "higher_education": 380,
                "percentage": 26.2,
            }
        },
        "5.3.1": {
            "metric": "Student council and activities",
            "data": {
                "student_council_elected": True,
                "cultural_clubs": 15,
                "technical_clubs": 22,
                "sports_clubs": 12,
                "literary_clubs": 8,
            }
        },
        "5.3.2": {
            "metric": "Sports and cultural activities/competitions",
            "data": {
                "state_level_participants": 285,
                "national_level_participants": 85,
                "international_participants": 12,
                "medals_won": 145,
                "cultural_events_organized": 25,
            }
        },
        "5.4.1": {
            "metric": "Alumni association registered and functional",
            "data": {
                "alumni_registered": True,
                "registration_number": "SOC/2010/1234",
                "active_members": 8500,
                "chapters": 12,
                "annual_meets": 4,
            }
        },
        "5.4.2": {
            "metric": "Alumni contribution",
            "data": {
                "financial_contribution_lakhs": 45,
                "scholarships_sponsored": 25,
                "mentorship_programs": 8,
                "guest_lectures": 35,
                "placement_support": True,
            }
        },
    },
    "score": 88,
    "percentage": 88.0,
}

# ============================================================================
# CRITERION 6: GOVERNANCE, LEADERSHIP AND MANAGEMENT (100 Marks)
# ============================================================================

CRITERION_6_DATA = {
    "criterion_id": "C6",
    "criterion_name": "Governance, Leadership and Management",
    "max_marks": 100,
    "key_indicators": [
        {"id": "6.1", "name": "Institutional Vision and Leadership", "marks": 15},
        {"id": "6.2", "name": "Strategy Development and Deployment", "marks": 20},
        {"id": "6.3", "name": "Faculty Empowerment Strategies", "marks": 25},
        {"id": "6.4", "name": "Financial Management and Resource Mobilization", "marks": 20},
        {"id": "6.5", "name": "Internal Quality Assurance System", "marks": 20},
    ],
    "sample_metrics": {
        "6.1.1": {
            "metric": "Vision and mission of the Institution",
            "data": {
                "vision_defined": True,
                "mission_defined": True,
                "values_defined": True,
                "displayed_prominently": True,
                "communicated_to_stakeholders": True,
                "reflected_in_academic_programs": True,
            }
        },
        "6.1.2": {
            "metric": "Participative management",
            "data": {
                "governing_council_meetings": 4,
                "academic_council_meetings": 4,
                "finance_committee_meetings": 6,
                "iqac_meetings": 12,
                "department_council_meetings": 48,
                "staff_representation": True,
                "student_representation": True,
            }
        },
        "6.2.1": {
            "metric": "Perspective/Strategic plan",
            "data": {
                "strategic_plan_available": True,
                "plan_period": "2020-2025",
                "action_plans_developed": True,
                "monitoring_mechanism": True,
                "review_frequency": "Quarterly",
            }
        },
        "6.2.2": {
            "metric": "E-governance implementation",
            "data": {
                "administration": "ERP System",
                "finance_accounts": "Fully Automated",
                "student_admission": "Online",
                "examination": "Online",
                "planning_development": True,
            }
        },
        "6.3.1": {
            "metric": "Faculty welfare measures",
            "data": {
                "leave_policy": True,
                "medical_insurance": True,
                "gratuity": True,
                "provident_fund": True,
                "loan_facility": True,
                "children_education_allowance": True,
            }
        },
        "6.3.2": {
            "metric": "Faculty development programs",
            "data": {
                "fdps_organized": 25,
                "faculty_attended_fdps": 285,
                "refresher_courses": 45,
                "orientation_programs": 12,
                "total_faculty_days": 850,
            }
        },
        "6.3.3": {
            "metric": "Performance appraisal system",
            "data": {
                "appraisal_system": "360-degree",
                "api_score_based": True,
                "self_appraisal": True,
                "peer_appraisal": True,
                "student_feedback_included": True,
            }
        },
        "6.4.1": {
            "metric": "Institutional strategies for mobilization of funds",
            "data": {
                "government_grants_percentage": 45,
                "fee_collection_percentage": 35,
                "research_grants_percentage": 12,
                "consultancy_percentage": 5,
                "donations_percentage": 3,
            }
        },
        "6.4.2": {
            "metric": "Funds/Grants received from various bodies",
            "data": {
                "ugc_grants_lakhs": 125,
                "aicte_grants_lakhs": 85,
                "dst_grants_lakhs": 65,
                "industry_grants_lakhs": 45,
                "other_grants_lakhs": 35,
                "total_grants": 355,
            }
        },
        "6.5.1": {
            "metric": "IQAC contribution to institutionalization of quality",
            "data": {
                "iqac_established_year": 2005,
                "aqar_submitted_regularly": True,
                "quality_initiatives": 45,
                "best_practices_documented": 25,
                "academic_audits_conducted": 5,
            }
        },
        "6.5.2": {
            "metric": "Quality assurance initiatives",
            "data": {
                "iso_certification": "ISO 9001:2015",
                "nirf_participation": True,
                "nirf_rank": 85,
                "other_rankings": ["ARIIA", "QS I-Gauge"],
            }
        },
    },
    "score": 90,
    "percentage": 90.0,
}

# ============================================================================
# CRITERION 7: INSTITUTIONAL VALUES AND BEST PRACTICES (100 Marks)
# ============================================================================

CRITERION_7_DATA = {
    "criterion_id": "C7",
    "criterion_name": "Institutional Values and Best Practices",
    "max_marks": 100,
    "key_indicators": [
        {"id": "7.1", "name": "Institutional Values and Social Responsibilities", "marks": 50},
        {"id": "7.2", "name": "Best Practices", "marks": 30},
        {"id": "7.3", "name": "Institutional Distinctiveness", "marks": 20},
    ],
    "sample_metrics": {
        "7.1.1": {
            "metric": "Gender equity measures",
            "data": {
                "women_cell_functional": True,
                "icc_constituted": True,
                "gender_sensitization_programs": 15,
                "women_development_programs": 12,
                "creche_facility": True,
                "women_restrooms": 45,
                "sanitary_napkin_dispensers": 25,
            }
        },
        "7.1.2": {
            "metric": "Facilities for persons with disabilities",
            "data": {
                "ramps_available": True,
                "wheelchair_accessible": True,
                "disabled_friendly_washrooms": 12,
                "braille_software": True,
                "screen_reading_software": True,
                "scribes_for_exams": True,
                "special_seating": True,
            }
        },
        "7.1.3": {
            "metric": "Environmental consciousness",
            "data": {
                "green_audit_conducted": True,
                "energy_audit_conducted": True,
                "environment_audit_conducted": True,
                "waste_management_system": True,
                "rainwater_harvesting": True,
                "solar_power_kw": 250,
            }
        },
        "7.1.4": {
            "metric": "Quality audits",
            "data": {
                "green_audit": True,
                "energy_audit": True,
                "environment_audit": True,
                "clean_and_green_campus": True,
                "beyond_campus_activities": 25,
            }
        },
        "7.1.5": {
            "metric": "Human values and professional ethics",
            "data": {
                "code_of_conduct_faculty": True,
                "code_of_conduct_students": True,
                "ethics_committee": True,
                "human_values_courses": 8,
                "professional_ethics_courses": 6,
            }
        },
        "7.1.6": {
            "metric": "National identities and symbols",
            "data": {
                "national_flag_hoisting": "Daily",
                "national_anthem_frequency": "Regular",
                "constitutional_obligations": True,
                "national_days_celebrated": True,
                "commemorative_days": 15,
            }
        },
        "7.2.1": {
            "metric": "Best practices implemented",
            "data": {
                "best_practice_1": {
                    "title": "Industry-Integrated Learning (IIL)",
                    "objective": "Bridge academia-industry gap through real-world project experience",
                    "context": "Students lack practical exposure to industry practices",
                    "practice": "Mandatory 6-month industry internship with live projects",
                    "evidence": "2500+ students benefited, 95% placement rate",
                    "outcome": "Enhanced employability and industry readiness",
                },
                "best_practice_2": {
                    "title": "Green Campus Initiative",
                    "objective": "Achieve carbon neutrality and environmental sustainability",
                    "context": "Global climate change and environmental concerns",
                    "practice": "Solar power, rainwater harvesting, waste management",
                    "evidence": "250 kW solar, 40% energy savings, zero waste campus",
                    "outcome": "Reduced carbon footprint by 45%",
                },
            }
        },
        "7.3.1": {
            "metric": "Institutional distinctiveness",
            "data": {
                "title": "Center for Innovation and Entrepreneurship",
                "description": "Fostering startup culture and innovation ecosystem",
                "achievements": [
                    "28 startups incubated",
                    "12 successful exits",
                    "85 lakhs funding raised",
                    "5 patents granted",
                ],
                "recognition": "National award for best incubation center",
                "impact": "Created 250+ jobs through startups",
            }
        },
    },
    "score": 85,
    "percentage": 85.0,
}

# ============================================================================
# CONSOLIDATED NAAC DATA
# ============================================================================

NAAC_CRITERIA_DATA = {
    "C1": CRITERION_1_DATA,
    "C2": CRITERION_2_DATA,
    "C3": CRITERION_3_DATA,
    "C4": CRITERION_4_DATA,
    "C5": CRITERION_5_DATA,
    "C6": CRITERION_6_DATA,
    "C7": CRITERION_7_DATA,
}

NAAC_SUMMARY = {
    "total_marks": 700,
    "total_score": 820,  # Sum of all criteria scores
    "cgpa_equivalent": 3.68,  # Old system reference
    "grade": "A++",  # Old system reference
    "criteria_scores": {
        "C1": {"marks": 150, "score": 138, "percentage": 92.0},
        "C2": {"marks": 200, "score": 185, "percentage": 92.5},
        "C3": {"marks": 150, "score": 142, "percentage": 94.7},
        "C4": {"marks": 100, "score": 92, "percentage": 92.0},
        "C5": {"marks": 100, "score": 88, "percentage": 88.0},
        "C6": {"marks": 100, "score": 90, "percentage": 90.0},
        "C7": {"marks": 100, "score": 85, "percentage": 85.0},
    },
    "overall_percentage": 91.43,
    "strengths": [
        "Excellent research output with high h-index publications",
        "Strong industry collaborations and placement record",
        "Robust ICT infrastructure with 100% digital classrooms",
        "Active IQAC with regular quality initiatives",
        "Comprehensive student support mechanisms",
    ],
    "areas_for_improvement": [
        "Increase international collaborations and student exchange",
        "Enhance alumni contribution and engagement",
        "Expand green campus initiatives",
        "Improve entrepreneurship ecosystem",
    ],
}


def get_criterion_data(criterion_id: str) -> Dict[str, Any]:
    """Get data for a specific criterion"""
    return NAAC_CRITERIA_DATA.get(criterion_id, {})


def get_all_criteria_data() -> Dict[str, Any]:
    """Get all NAAC criteria data"""
    return NAAC_CRITERIA_DATA


def get_naac_summary() -> Dict[str, Any]:
    """Get NAAC summary data"""
    return NAAC_SUMMARY
