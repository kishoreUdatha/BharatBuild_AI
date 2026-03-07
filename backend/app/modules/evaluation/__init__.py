"""
Evaluation Module
Provides automated project evaluation, rubric-based grading, and attainment calculation
"""

from app.modules.evaluation.project_evaluator import (
    ProjectEvaluator,
    EvaluationRubric,
    RubricCriterion,
    EvaluationResult,
    EvaluationCriteria,
    GradeLevel,
    project_evaluator
)

__all__ = [
    'ProjectEvaluator',
    'EvaluationRubric',
    'RubricCriterion',
    'EvaluationResult',
    'EvaluationCriteria',
    'GradeLevel',
    'project_evaluator'
]
