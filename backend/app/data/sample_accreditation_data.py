"""
Sample Data for NAAC 2025 Binary Accreditation and MBGL Framework
This file contains comprehensive sample data for demonstration and testing
"""

import uuid
from datetime import datetime, timedelta

# ============================================================================
# SAMPLE INSTITUTIONS DATA
# ============================================================================

SAMPLE_INSTITUTIONS = [
    {
        "id": "inst-001",
        "name": "Bharath Institute of Technology",
        "type": "autonomous",
        "location": "Chennai, Tamil Nadu",
        "established": 1995,
        "students": 5200,
        "faculty": 320,
    },
    {
        "id": "inst-002",
        "name": "Vidya Engineering College",
        "type": "affiliated",
        "location": "Bangalore, Karnataka",
        "established": 2005,
        "students": 3500,
        "faculty": 180,
    },
    {
        "id": "inst-003",
        "name": "National College of Arts & Science",
        "type": "autonomous",
        "location": "Hyderabad, Telangana",
        "established": 1980,
        "students": 8000,
        "faculty": 450,
    },
]

# ============================================================================
# SAMPLE ACCREDITATION APPLICATIONS
# ============================================================================

SAMPLE_APPLICATIONS = [
    {
        "id": "app-001",
        "institution_id": "inst-001",
        "application_number": "NAAC/2025/TN/001234",
        "application_date": datetime(2025, 6, 15),
        "cycle": "third",
        "cycle_number": 3,
        "binary_status": "accredited",
        "binary_assessment_date": datetime(2025, 9, 20),
        "binary_validity_start": datetime(2025, 10, 1),
        "binary_validity_end": datetime(2028, 9, 30),
        "mbgl_level": "level_4",
        "mbgl_assessment_date": datetime(2025, 10, 5),
        "mbgl_score": 4.2,
        "mbgl_validity_start": datetime(2025, 10, 15),
        "mbgl_validity_end": datetime(2028, 10, 14),
        "previous_grade": "A++",
        "previous_cgpa": 3.75,
        "previous_validity_end": datetime(2025, 5, 31),
        "current_phase": "completed",
        "self_study_score": 92.5,
        "ai_assessment_score": 88.0,
        "stakeholder_score": 90.0,
        "final_score": 90.2,
        "notes": "Excellent performance in all criteria. Strong research output.",
    },
    {
        "id": "app-002",
        "institution_id": "inst-002",
        "application_number": "NAAC/2025/KA/002567",
        "application_date": datetime(2025, 8, 1),
        "cycle": "first",
        "cycle_number": 1,
        "binary_status": "under_review",
        "binary_assessment_date": None,
        "binary_validity_start": None,
        "binary_validity_end": None,
        "mbgl_level": "not_assessed",
        "mbgl_assessment_date": None,
        "mbgl_score": None,
        "mbgl_validity_start": None,
        "mbgl_validity_end": None,
        "previous_grade": None,
        "previous_cgpa": None,
        "previous_validity_end": None,
        "current_phase": "peer_review",
        "self_study_score": 78.5,
        "ai_assessment_score": 75.0,
        "stakeholder_score": None,
        "final_score": None,
        "notes": "First cycle application. AI assessment completed, awaiting peer review.",
    },
    {
        "id": "app-003",
        "institution_id": "inst-003",
        "application_number": "NAAC/2025/TS/003891",
        "application_date": datetime(2025, 4, 10),
        "cycle": "fourth",
        "cycle_number": 4,
        "binary_status": "accredited",
        "binary_assessment_date": datetime(2025, 7, 15),
        "binary_validity_start": datetime(2025, 8, 1),
        "binary_validity_end": datetime(2028, 7, 31),
        "mbgl_level": "level_5",
        "mbgl_assessment_date": datetime(2025, 8, 10),
        "mbgl_score": 4.75,
        "mbgl_validity_start": datetime(2025, 8, 20),
        "mbgl_validity_end": datetime(2028, 8, 19),
        "previous_grade": "A++",
        "previous_cgpa": 3.85,
        "previous_validity_end": datetime(2025, 3, 31),
        "current_phase": "completed",
        "self_study_score": 96.0,
        "ai_assessment_score": 94.5,
        "stakeholder_score": 95.0,
        "final_score": 95.2,
        "notes": "Excellence in all dimensions. National ranking in top 10.",
    },
]

# ============================================================================
# SAMPLE ATTRIBUTE SCORES (10 Attributes Framework)
# ============================================================================

ATTRIBUTES_DEFINITION = [
    {"number": 1, "attribute": "curricular_aspects", "name": "Curricular Aspects", "weightage": 10.0, "max_score": 100},
    {"number": 2, "attribute": "teaching_learning", "name": "Teaching-Learning & Evaluation", "weightage": 15.0, "max_score": 100},
    {"number": 3, "attribute": "research_innovation", "name": "Research, Innovations & Extension", "weightage": 15.0, "max_score": 100},
    {"number": 4, "attribute": "infrastructure", "name": "Infrastructure & Learning Resources", "weightage": 10.0, "max_score": 100},
    {"number": 5, "attribute": "student_support", "name": "Student Support & Progression", "weightage": 10.0, "max_score": 100},
    {"number": 6, "attribute": "governance", "name": "Governance, Leadership & Management", "weightage": 10.0, "max_score": 100},
    {"number": 7, "attribute": "institutional_values", "name": "Institutional Values & Best Practices", "weightage": 10.0, "max_score": 100},
    {"number": 8, "attribute": "nep_alignment", "name": "NEP 2020 Alignment", "weightage": 8.0, "max_score": 100},
    {"number": 9, "attribute": "digital_infrastructure", "name": "Digital Infrastructure & ICT", "weightage": 7.0, "max_score": 100},
    {"number": 10, "attribute": "sustainability", "name": "Sustainability & Environment", "weightage": 5.0, "max_score": 100},
]

# Scores for Application 1 (Bharath Institute - Level 4)
SAMPLE_ATTRIBUTE_SCORES_APP1 = [
    {"attribute": "curricular_aspects", "self_score": 88, "verified_score": 86, "final_score": 86, "ai_score": 85, "ai_confidence": 0.92, "evidence_count": 45, "evidence_verified": 42, "is_complete": True},
    {"attribute": "teaching_learning", "self_score": 92, "verified_score": 90, "final_score": 90, "ai_score": 89, "ai_confidence": 0.95, "evidence_count": 68, "evidence_verified": 65, "is_complete": True},
    {"attribute": "research_innovation", "self_score": 95, "verified_score": 94, "final_score": 94, "ai_score": 93, "ai_confidence": 0.94, "evidence_count": 120, "evidence_verified": 118, "is_complete": True},
    {"attribute": "infrastructure", "self_score": 90, "verified_score": 88, "final_score": 88, "ai_score": 87, "ai_confidence": 0.91, "evidence_count": 35, "evidence_verified": 33, "is_complete": True},
    {"attribute": "student_support", "self_score": 87, "verified_score": 85, "final_score": 85, "ai_score": 84, "ai_confidence": 0.90, "evidence_count": 55, "evidence_verified": 52, "is_complete": True},
    {"attribute": "governance", "self_score": 91, "verified_score": 89, "final_score": 89, "ai_score": 88, "ai_confidence": 0.93, "evidence_count": 40, "evidence_verified": 38, "is_complete": True},
    {"attribute": "institutional_values", "self_score": 93, "verified_score": 92, "final_score": 92, "ai_score": 91, "ai_confidence": 0.94, "evidence_count": 30, "evidence_verified": 29, "is_complete": True},
    {"attribute": "nep_alignment", "self_score": 85, "verified_score": 83, "final_score": 83, "ai_score": 82, "ai_confidence": 0.88, "evidence_count": 25, "evidence_verified": 23, "is_complete": True},
    {"attribute": "digital_infrastructure", "self_score": 94, "verified_score": 93, "final_score": 93, "ai_score": 92, "ai_confidence": 0.96, "evidence_count": 28, "evidence_verified": 27, "is_complete": True},
    {"attribute": "sustainability", "self_score": 88, "verified_score": 86, "final_score": 86, "ai_score": 85, "ai_confidence": 0.89, "evidence_count": 20, "evidence_verified": 19, "is_complete": True},
]

# Scores for Application 2 (Vidya Engineering - Under Review)
SAMPLE_ATTRIBUTE_SCORES_APP2 = [
    {"attribute": "curricular_aspects", "self_score": 75, "verified_score": None, "final_score": None, "ai_score": 72, "ai_confidence": 0.85, "evidence_count": 30, "evidence_verified": 15, "is_complete": False},
    {"attribute": "teaching_learning", "self_score": 78, "verified_score": None, "final_score": None, "ai_score": 75, "ai_confidence": 0.87, "evidence_count": 45, "evidence_verified": 20, "is_complete": False},
    {"attribute": "research_innovation", "self_score": 70, "verified_score": None, "final_score": None, "ai_score": 68, "ai_confidence": 0.82, "evidence_count": 50, "evidence_verified": 25, "is_complete": False},
    {"attribute": "infrastructure", "self_score": 80, "verified_score": None, "final_score": None, "ai_score": 78, "ai_confidence": 0.88, "evidence_count": 25, "evidence_verified": 12, "is_complete": False},
    {"attribute": "student_support", "self_score": 76, "verified_score": None, "final_score": None, "ai_score": 74, "ai_confidence": 0.84, "evidence_count": 35, "evidence_verified": 18, "is_complete": False},
    {"attribute": "governance", "self_score": 82, "verified_score": None, "final_score": None, "ai_score": 80, "ai_confidence": 0.89, "evidence_count": 28, "evidence_verified": 14, "is_complete": False},
    {"attribute": "institutional_values", "self_score": 79, "verified_score": None, "final_score": None, "ai_score": 77, "ai_confidence": 0.86, "evidence_count": 22, "evidence_verified": 11, "is_complete": False},
    {"attribute": "nep_alignment", "self_score": 72, "verified_score": None, "final_score": None, "ai_score": 70, "ai_confidence": 0.80, "evidence_count": 18, "evidence_verified": 9, "is_complete": False},
    {"attribute": "digital_infrastructure", "self_score": 85, "verified_score": None, "final_score": None, "ai_score": 83, "ai_confidence": 0.91, "evidence_count": 20, "evidence_verified": 10, "is_complete": False},
    {"attribute": "sustainability", "self_score": 74, "verified_score": None, "final_score": None, "ai_score": 72, "ai_confidence": 0.83, "evidence_count": 15, "evidence_verified": 7, "is_complete": False},
]

# Scores for Application 3 (National College - Level 5)
SAMPLE_ATTRIBUTE_SCORES_APP3 = [
    {"attribute": "curricular_aspects", "self_score": 96, "verified_score": 95, "final_score": 95, "ai_score": 94, "ai_confidence": 0.97, "evidence_count": 60, "evidence_verified": 60, "is_complete": True},
    {"attribute": "teaching_learning", "self_score": 97, "verified_score": 96, "final_score": 96, "ai_score": 95, "ai_confidence": 0.98, "evidence_count": 85, "evidence_verified": 85, "is_complete": True},
    {"attribute": "research_innovation", "self_score": 98, "verified_score": 97, "final_score": 97, "ai_score": 96, "ai_confidence": 0.98, "evidence_count": 150, "evidence_verified": 150, "is_complete": True},
    {"attribute": "infrastructure", "self_score": 95, "verified_score": 94, "final_score": 94, "ai_score": 93, "ai_confidence": 0.96, "evidence_count": 45, "evidence_verified": 45, "is_complete": True},
    {"attribute": "student_support", "self_score": 94, "verified_score": 93, "final_score": 93, "ai_score": 92, "ai_confidence": 0.95, "evidence_count": 70, "evidence_verified": 70, "is_complete": True},
    {"attribute": "governance", "self_score": 96, "verified_score": 95, "final_score": 95, "ai_score": 94, "ai_confidence": 0.97, "evidence_count": 50, "evidence_verified": 50, "is_complete": True},
    {"attribute": "institutional_values", "self_score": 97, "verified_score": 96, "final_score": 96, "ai_score": 95, "ai_confidence": 0.97, "evidence_count": 40, "evidence_verified": 40, "is_complete": True},
    {"attribute": "nep_alignment", "self_score": 93, "verified_score": 92, "final_score": 92, "ai_score": 91, "ai_confidence": 0.94, "evidence_count": 35, "evidence_verified": 35, "is_complete": True},
    {"attribute": "digital_infrastructure", "self_score": 98, "verified_score": 97, "final_score": 97, "ai_score": 96, "ai_confidence": 0.98, "evidence_count": 38, "evidence_verified": 38, "is_complete": True},
    {"attribute": "sustainability", "self_score": 95, "verified_score": 94, "final_score": 94, "ai_score": 93, "ai_confidence": 0.96, "evidence_count": 28, "evidence_verified": 28, "is_complete": True},
]

# ============================================================================
# SAMPLE MBGL ASSESSMENTS
# ============================================================================

SAMPLE_MBGL_ASSESSMENTS = [
    {
        "id": "mbgl-001",
        "application_id": "app-001",
        "assessment_year": "2025-26",
        "assessment_date": datetime(2025, 10, 5),
        # Maturity Dimensions (1-5)
        "leadership_maturity": 4,
        "process_maturity": 4,
        "people_maturity": 5,
        "technology_maturity": 5,
        "outcome_maturity": 4,
        "innovation_maturity": 4,
        "stakeholder_maturity": 4,
        "sustainability_maturity": 4,
        # Calculated
        "average_maturity": 4.25,
        "weighted_score": 85.0,
        "recommended_level": "level_4",
        "final_level": "level_4",
        # Criteria Met
        "level_1_criteria_met": True,
        "level_2_criteria_met": True,
        "level_3_criteria_met": True,
        "level_4_criteria_met": True,
        "level_5_criteria_met": False,
        # Analysis
        "strengths": [
            "Strong technology infrastructure with 100% digital classrooms",
            "Excellent faculty development programs",
            "High research output with 150+ publications annually",
            "Industry partnerships with 25+ companies",
            "Student placement rate above 95%",
        ],
        "improvements_needed": [
            "Increase international collaborations",
            "Enhance sustainability initiatives",
            "Expand community outreach programs",
            "Improve alumni engagement",
        ],
        "action_plan": "Focus on establishing 5 new international MOUs, implement solar power for 50% campus, and launch 3 new community extension programs by next assessment cycle.",
        "assessed_by": "Dr. Ramesh Kumar",
        "verified_by": "Prof. Sunita Sharma",
    },
    {
        "id": "mbgl-002",
        "application_id": "app-003",
        "assessment_year": "2025-26",
        "assessment_date": datetime(2025, 8, 10),
        # Maturity Dimensions (1-5)
        "leadership_maturity": 5,
        "process_maturity": 5,
        "people_maturity": 5,
        "technology_maturity": 5,
        "outcome_maturity": 5,
        "innovation_maturity": 4,
        "stakeholder_maturity": 5,
        "sustainability_maturity": 4,
        # Calculated
        "average_maturity": 4.75,
        "weighted_score": 95.0,
        "recommended_level": "level_5",
        "final_level": "level_5",
        # Criteria Met
        "level_1_criteria_met": True,
        "level_2_criteria_met": True,
        "level_3_criteria_met": True,
        "level_4_criteria_met": True,
        "level_5_criteria_met": True,
        # Analysis
        "strengths": [
            "National ranking in top 10 institutions",
            "International accreditations (ABET, AACSB)",
            "200+ research publications annually",
            "50+ international collaborations",
            "100% placement with average package 12 LPA",
            "Green campus with zero carbon footprint",
            "Industry-sponsored research centers",
        ],
        "improvements_needed": [
            "Further enhance innovation ecosystem",
            "Expand patent portfolio",
        ],
        "action_plan": "Continue excellence trajectory. Target 10 new patents, establish innovation hub, and achieve carbon negative status by 2027.",
        "assessed_by": "Dr. Anil Verma",
        "verified_by": "Prof. Lakshmi Narayanan",
    },
]

# ============================================================================
# SAMPLE MBGL LEVEL CRITERIA
# ============================================================================

MBGL_LEVEL_CRITERIA = [
    {
        "id": "mbgl-level-1",
        "level": "level_1",
        "level_number": 1,
        "level_name": "Basic Compliance",
        "level_description": "Institution meets basic accreditation requirements and demonstrates fundamental quality processes.",
        "min_binary_status": True,
        "min_maturity_score": 1.0,
        "min_attribute_scores": {"minimum_per_attribute": 50},
        "mandatory_criteria": [
            "Valid institutional recognition",
            "Basic infrastructure in place",
            "Qualified faculty as per norms",
            "Functional governance structure",
        ],
        "optional_criteria": [],
        "optional_criteria_min": 0,
        "validity_years": 3,
        "recognition_benefits": [
            "Basic accreditation certificate",
            "Eligible for government grants",
            "Can apply for MBGL Level 2 after 1 year",
        ],
        "is_active": True,
    },
    {
        "id": "mbgl-level-2",
        "level": "level_2",
        "level_number": 2,
        "level_name": "Developing",
        "level_description": "Institution shows developing quality practices with documented processes and improvement initiatives.",
        "min_binary_status": True,
        "min_maturity_score": 2.0,
        "min_attribute_scores": {"minimum_per_attribute": 60, "average": 65},
        "mandatory_criteria": [
            "All Level 1 criteria",
            "IQAC functioning effectively",
            "Student feedback system in place",
            "Faculty development programs",
            "Basic research activities",
        ],
        "optional_criteria": [
            "Industry collaborations",
            "Community extension activities",
            "Digital learning resources",
        ],
        "optional_criteria_min": 1,
        "validity_years": 3,
        "recognition_benefits": [
            "Enhanced accreditation certificate",
            "Priority for UGC schemes",
            "Eligible for autonomy consideration",
            "Can apply for MBGL Level 3 after 1 year",
        ],
        "is_active": True,
    },
    {
        "id": "mbgl-level-3",
        "level": "level_3",
        "level_number": 3,
        "level_name": "Established",
        "level_description": "Institution has established quality systems with consistent outcomes and stakeholder satisfaction.",
        "min_binary_status": True,
        "min_maturity_score": 3.0,
        "min_attribute_scores": {"minimum_per_attribute": 70, "average": 75},
        "mandatory_criteria": [
            "All Level 2 criteria",
            "Outcome-based education implemented",
            "Research publications track record",
            "Industry partnerships established",
            "Student placement cell active",
            "Alumni association functional",
        ],
        "optional_criteria": [
            "International collaborations",
            "Patent/IP activities",
            "Incubation center",
            "Green campus initiatives",
        ],
        "optional_criteria_min": 2,
        "validity_years": 3,
        "recognition_benefits": [
            "Premium accreditation status",
            "Autonomy fast-track",
            "Increased intake permitted",
            "International recognition eligible",
            "Can apply for MBGL Level 4",
        ],
        "is_active": True,
    },
    {
        "id": "mbgl-level-4",
        "level": "level_4",
        "level_number": 4,
        "level_name": "Advanced",
        "level_description": "Institution demonstrates advanced quality practices with innovation, research excellence, and national recognition.",
        "min_binary_status": True,
        "min_maturity_score": 4.0,
        "min_attribute_scores": {"minimum_per_attribute": 80, "average": 85},
        "mandatory_criteria": [
            "All Level 3 criteria",
            "Research centers established",
            "PhD programs running",
            "International collaborations active",
            "Innovation ecosystem in place",
            "High placement rate (>80%)",
            "NEP 2020 implementation advanced",
        ],
        "optional_criteria": [
            "International accreditation",
            "Funded research projects >5 Cr",
            "Patents granted",
            "Industry-sponsored labs",
            "Start-up incubation success",
        ],
        "optional_criteria_min": 3,
        "validity_years": 3,
        "recognition_benefits": [
            "National excellence recognition",
            "Research university eligibility",
            "International student recruitment",
            "Government policy advisory roles",
            "Can apply for MBGL Level 5",
        ],
        "is_active": True,
    },
    {
        "id": "mbgl-level-5",
        "level": "level_5",
        "level_number": 5,
        "level_name": "Excellence",
        "level_description": "Institution achieves excellence in all dimensions with global standards, innovation leadership, and transformative impact.",
        "min_binary_status": True,
        "min_maturity_score": 4.5,
        "min_attribute_scores": {"minimum_per_attribute": 90, "average": 92},
        "mandatory_criteria": [
            "All Level 4 criteria",
            "Global ranking presence",
            "International accreditations (ABET/AACSB/NBA Tier-1)",
            "Research funding >10 Cr annually",
            "Patent portfolio >10",
            "International faculty exchange",
            "Sustainability leadership",
            "Industry 4.0 integration",
        ],
        "optional_criteria": [
            "Top 100 global ranking",
            "Nobel/Turing laureate association",
            "Major innovation/discovery",
            "National policy contribution",
        ],
        "optional_criteria_min": 1,
        "validity_years": 3,
        "recognition_benefits": [
            "Institution of Eminence pathway",
            "Global brand recognition",
            "International research grants",
            "Government flagship programs partner",
            "Policy making participation",
            "Mentorship role for other institutions",
        ],
        "is_active": True,
    },
]

# ============================================================================
# SAMPLE ACCREDITATION TIMELINES
# ============================================================================

SAMPLE_TIMELINES_APP1 = [
    {"milestone_name": "Application Submitted", "milestone_type": "submission", "planned_date": datetime(2025, 6, 15), "actual_date": datetime(2025, 6, 15), "is_completed": True},
    {"milestone_name": "IIQA Approved", "milestone_type": "approval", "planned_date": datetime(2025, 6, 30), "actual_date": datetime(2025, 6, 28), "is_completed": True},
    {"milestone_name": "SSR Submitted", "milestone_type": "submission", "planned_date": datetime(2025, 7, 31), "actual_date": datetime(2025, 7, 25), "is_completed": True},
    {"milestone_name": "AI Assessment Completed", "milestone_type": "assessment", "planned_date": datetime(2025, 8, 15), "actual_date": datetime(2025, 8, 10), "is_completed": True},
    {"milestone_name": "DVV Clarifications", "milestone_type": "clarification", "planned_date": datetime(2025, 8, 31), "actual_date": datetime(2025, 8, 28), "is_completed": True},
    {"milestone_name": "Peer Review Visit", "milestone_type": "review", "planned_date": datetime(2025, 9, 15), "actual_date": datetime(2025, 9, 18), "is_completed": True},
    {"milestone_name": "Binary Decision", "milestone_type": "decision", "planned_date": datetime(2025, 9, 25), "actual_date": datetime(2025, 9, 20), "is_completed": True},
    {"milestone_name": "MBGL Assessment", "milestone_type": "assessment", "planned_date": datetime(2025, 10, 10), "actual_date": datetime(2025, 10, 5), "is_completed": True},
    {"milestone_name": "Final Certificate Issued", "milestone_type": "certificate", "planned_date": datetime(2025, 10, 20), "actual_date": datetime(2025, 10, 15), "is_completed": True},
]

SAMPLE_TIMELINES_APP2 = [
    {"milestone_name": "Application Submitted", "milestone_type": "submission", "planned_date": datetime(2025, 8, 1), "actual_date": datetime(2025, 8, 1), "is_completed": True},
    {"milestone_name": "IIQA Approved", "milestone_type": "approval", "planned_date": datetime(2025, 8, 15), "actual_date": datetime(2025, 8, 12), "is_completed": True},
    {"milestone_name": "SSR Submitted", "milestone_type": "submission", "planned_date": datetime(2025, 9, 15), "actual_date": datetime(2025, 9, 10), "is_completed": True},
    {"milestone_name": "AI Assessment Completed", "milestone_type": "assessment", "planned_date": datetime(2025, 9, 30), "actual_date": datetime(2025, 9, 28), "is_completed": True},
    {"milestone_name": "DVV Clarifications", "milestone_type": "clarification", "planned_date": datetime(2025, 10, 15), "actual_date": None, "is_completed": False},
    {"milestone_name": "Peer Review Visit", "milestone_type": "review", "planned_date": datetime(2025, 11, 1), "actual_date": None, "is_completed": False},
    {"milestone_name": "Binary Decision", "milestone_type": "decision", "planned_date": datetime(2025, 11, 15), "actual_date": None, "is_completed": False},
    {"milestone_name": "MBGL Assessment", "milestone_type": "assessment", "planned_date": datetime(2025, 11, 25), "actual_date": None, "is_completed": False},
    {"milestone_name": "Final Certificate Issued", "milestone_type": "certificate", "planned_date": datetime(2025, 12, 5), "actual_date": None, "is_completed": False},
]

# ============================================================================
# SAMPLE DASHBOARD STATISTICS
# ============================================================================

DASHBOARD_STATS = {
    "total_applications": 3,
    "accredited": 2,
    "under_review": 1,
    "not_accredited": 0,
    "mbgl_distribution": {
        "level_1": 0,
        "level_2": 0,
        "level_3": 0,
        "level_4": 1,
        "level_5": 1,
        "not_assessed": 1,
    },
    "average_maturity_score": 4.5,
    "attribute_performance": {
        "curricular_aspects": 85.3,
        "teaching_learning": 87.0,
        "research_innovation": 86.3,
        "infrastructure": 86.7,
        "student_support": 84.0,
        "governance": 86.3,
        "institutional_values": 88.0,
        "nep_alignment": 81.7,
        "digital_infrastructure": 91.0,
        "sustainability": 84.7,
    },
    "completion_rate": 66.7,
    "avg_processing_days": 95,
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_all_sample_data():
    """Return all sample data as a dictionary"""
    return {
        "institutions": SAMPLE_INSTITUTIONS,
        "applications": SAMPLE_APPLICATIONS,
        "attributes_definition": ATTRIBUTES_DEFINITION,
        "attribute_scores": {
            "app-001": SAMPLE_ATTRIBUTE_SCORES_APP1,
            "app-002": SAMPLE_ATTRIBUTE_SCORES_APP2,
            "app-003": SAMPLE_ATTRIBUTE_SCORES_APP3,
        },
        "mbgl_assessments": SAMPLE_MBGL_ASSESSMENTS,
        "mbgl_level_criteria": MBGL_LEVEL_CRITERIA,
        "timelines": {
            "app-001": SAMPLE_TIMELINES_APP1,
            "app-002": SAMPLE_TIMELINES_APP2,
        },
        "dashboard_stats": DASHBOARD_STATS,
    }


def generate_uuid():
    """Generate a new UUID string"""
    return str(uuid.uuid4())
