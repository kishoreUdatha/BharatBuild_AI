"""
Sample Data Module for NAAC/NBA Accreditation
Contains comprehensive seed data for all accreditation scenarios
"""

from .sample_accreditation_data import (
    SAMPLE_INSTITUTIONS,
    SAMPLE_APPLICATIONS,
    SAMPLE_MBGL_ASSESSMENTS,
    MBGL_LEVEL_CRITERIA,
    DASHBOARD_STATS,
    get_all_sample_data,
)

from .sample_naac_criteria_data import (
    NAAC_CRITERIA_DATA,
    NAAC_SUMMARY,
    CRITERION_1_DATA,
    CRITERION_2_DATA,
    CRITERION_3_DATA,
    CRITERION_4_DATA,
    CRITERION_5_DATA,
    CRITERION_6_DATA,
    CRITERION_7_DATA,
    get_criterion_data,
    get_all_criteria_data,
    get_naac_summary,
)

from .sample_nba_data import (
    NBA_CRITERIA,
    SAMPLE_PROGRAMS,
    SAMPLE_PEOS,
    PROGRAM_OUTCOMES,
    SAMPLE_PO_ATTAINMENT,
    SAMPLE_FACULTY,
    NBA_CRITERIA_SCORES,
    NBA_DASHBOARD_STATS,
    get_program_by_id,
    get_all_programs,
    get_peo_data,
    get_po_attainment,
    get_faculty_data,
    get_nba_criteria_scores,
    get_nba_dashboard_stats,
)

__all__ = [
    # Accreditation Framework (Binary + MBGL)
    'SAMPLE_INSTITUTIONS',
    'SAMPLE_APPLICATIONS',
    'SAMPLE_MBGL_ASSESSMENTS',
    'MBGL_LEVEL_CRITERIA',
    'DASHBOARD_STATS',
    'get_all_sample_data',

    # NAAC Criteria
    'NAAC_CRITERIA_DATA',
    'NAAC_SUMMARY',
    'CRITERION_1_DATA',
    'CRITERION_2_DATA',
    'CRITERION_3_DATA',
    'CRITERION_4_DATA',
    'CRITERION_5_DATA',
    'CRITERION_6_DATA',
    'CRITERION_7_DATA',
    'get_criterion_data',
    'get_all_criteria_data',
    'get_naac_summary',

    # NBA Accreditation
    'NBA_CRITERIA',
    'SAMPLE_PROGRAMS',
    'SAMPLE_PEOS',
    'PROGRAM_OUTCOMES',
    'SAMPLE_PO_ATTAINMENT',
    'SAMPLE_FACULTY',
    'NBA_CRITERIA_SCORES',
    'NBA_DASHBOARD_STATS',
    'get_program_by_id',
    'get_all_programs',
    'get_peo_data',
    'get_po_attainment',
    'get_faculty_data',
    'get_nba_criteria_scores',
    'get_nba_dashboard_stats',
]
