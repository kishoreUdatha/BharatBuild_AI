"""
Curriculum Module
Provides curriculum-to-project mapping, industry use-case library, and OBE support
"""

from app.modules.curriculum.curriculum_mapping import (
    CurriculumMappingEngine,
    IndustryUseCaseLibrary,
    CourseInfo,
    ProjectSuggestion,
    DifficultyLevel,
    ProjectType,
    TechnologyDomain,
    curriculum_mapping_engine,
    industry_library,
    PROGRAM_OUTCOMES,
    BLOOMS_TAXONOMY
)

__all__ = [
    'CurriculumMappingEngine',
    'IndustryUseCaseLibrary',
    'CourseInfo',
    'ProjectSuggestion',
    'DifficultyLevel',
    'ProjectType',
    'TechnologyDomain',
    'curriculum_mapping_engine',
    'industry_library',
    'PROGRAM_OUTCOMES',
    'BLOOMS_TAXONOMY'
]
