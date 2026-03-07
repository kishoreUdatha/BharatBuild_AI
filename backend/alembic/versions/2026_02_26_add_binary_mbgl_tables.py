"""Add Binary Accreditation and MBGL tables for NAAC 2025 Framework

Revision ID: binary_mbgl_2025
Revises:
Create Date: 2026-02-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'binary_mbgl_2025'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create accreditation_applications table
    op.create_table(
        'accreditation_applications',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('institution_id', sa.String(36), nullable=True),

        # Application Details
        sa.Column('application_number', sa.String(50), unique=True, nullable=False),
        sa.Column('application_date', sa.DateTime, server_default=sa.func.now()),

        # Cycle Information
        sa.Column('cycle', sa.String(20), default='first'),
        sa.Column('cycle_number', sa.Integer, default=1),

        # Binary Accreditation Status
        sa.Column('binary_status', sa.String(30), default='not_applied'),
        sa.Column('binary_assessment_date', sa.DateTime, nullable=True),
        sa.Column('binary_validity_start', sa.DateTime, nullable=True),
        sa.Column('binary_validity_end', sa.DateTime, nullable=True),

        # MBGL Status
        sa.Column('mbgl_level', sa.String(20), default='not_assessed'),
        sa.Column('mbgl_assessment_date', sa.DateTime, nullable=True),
        sa.Column('mbgl_score', sa.Float, nullable=True),
        sa.Column('mbgl_validity_start', sa.DateTime, nullable=True),
        sa.Column('mbgl_validity_end', sa.DateTime, nullable=True),

        # Previous Accreditation
        sa.Column('previous_grade', sa.String(10), nullable=True),
        sa.Column('previous_cgpa', sa.Float, nullable=True),
        sa.Column('previous_validity_end', sa.DateTime, nullable=True),

        # Current Assessment Phase
        sa.Column('current_phase', sa.String(30), default='self_study'),
        sa.Column('phase_started_at', sa.DateTime, nullable=True),

        # Scores
        sa.Column('self_study_score', sa.Float, nullable=True),
        sa.Column('ai_assessment_score', sa.Float, nullable=True),
        sa.Column('stakeholder_score', sa.Float, nullable=True),
        sa.Column('final_score', sa.Float, nullable=True),

        # Metadata
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('metadata', sa.JSON, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_index('idx_accreditation_binary_status', 'accreditation_applications', ['binary_status'])
    op.create_index('idx_accreditation_mbgl_level', 'accreditation_applications', ['mbgl_level'])

    # Create attribute_scores table
    op.create_table(
        'attribute_scores',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('application_id', sa.String(36), sa.ForeignKey('accreditation_applications.id'), nullable=False),

        # Attribute Details
        sa.Column('attribute', sa.String(50), nullable=False),
        sa.Column('attribute_number', sa.Integer, nullable=False),
        sa.Column('attribute_name', sa.String(200), nullable=False),

        # Scoring
        sa.Column('max_score', sa.Float, default=100.0),
        sa.Column('self_assessment_score', sa.Float, nullable=True),
        sa.Column('verified_score', sa.Float, nullable=True),
        sa.Column('final_score', sa.Float, nullable=True),
        sa.Column('weightage', sa.Float, default=10.0),

        # Evidence
        sa.Column('evidence_count', sa.Integer, default=0),
        sa.Column('evidence_verified', sa.Integer, default=0),
        sa.Column('documentation_complete', sa.Boolean, default=False),

        # AI Assessment
        sa.Column('ai_score', sa.Float, nullable=True),
        sa.Column('ai_confidence', sa.Float, nullable=True),
        sa.Column('ai_feedback', sa.Text, nullable=True),

        # Status
        sa.Column('is_complete', sa.Boolean, default=False),
        sa.Column('reviewed_by', sa.String(200), nullable=True),
        sa.Column('reviewed_at', sa.DateTime, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),

        sa.UniqueConstraint('application_id', 'attribute', name='uq_app_attribute'),
    )

    op.create_index('idx_attribute_score_attribute', 'attribute_scores', ['attribute'])

    # Create mbgl_assessments table
    op.create_table(
        'mbgl_assessments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('application_id', sa.String(36), sa.ForeignKey('accreditation_applications.id'), nullable=False),

        # Assessment Details
        sa.Column('assessment_year', sa.String(10), nullable=False),
        sa.Column('assessment_date', sa.DateTime, server_default=sa.func.now()),

        # Maturity Dimensions (1-5)
        sa.Column('leadership_maturity', sa.Integer, default=1),
        sa.Column('process_maturity', sa.Integer, default=1),
        sa.Column('people_maturity', sa.Integer, default=1),
        sa.Column('technology_maturity', sa.Integer, default=1),
        sa.Column('outcome_maturity', sa.Integer, default=1),
        sa.Column('innovation_maturity', sa.Integer, default=1),
        sa.Column('stakeholder_maturity', sa.Integer, default=1),
        sa.Column('sustainability_maturity', sa.Integer, default=1),

        # Calculated Scores
        sa.Column('average_maturity', sa.Float, nullable=True),
        sa.Column('weighted_score', sa.Float, nullable=True),

        # MBGL Level
        sa.Column('recommended_level', sa.String(20), nullable=True),
        sa.Column('final_level', sa.String(20), nullable=True),

        # Criteria Met Flags
        sa.Column('level_1_criteria_met', sa.Boolean, default=False),
        sa.Column('level_2_criteria_met', sa.Boolean, default=False),
        sa.Column('level_3_criteria_met', sa.Boolean, default=False),
        sa.Column('level_4_criteria_met', sa.Boolean, default=False),
        sa.Column('level_5_criteria_met', sa.Boolean, default=False),

        # Strengths & Improvements
        sa.Column('strengths', sa.JSON, nullable=True),
        sa.Column('improvements_needed', sa.JSON, nullable=True),
        sa.Column('action_plan', sa.Text, nullable=True),

        # Assessor Info
        sa.Column('assessed_by', sa.String(200), nullable=True),
        sa.Column('verified_by', sa.String(200), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create mbgl_level_criteria table
    op.create_table(
        'mbgl_level_criteria',
        sa.Column('id', sa.String(36), primary_key=True),

        # Level Details
        sa.Column('level', sa.String(20), nullable=False, unique=True),
        sa.Column('level_number', sa.Integer, nullable=False),
        sa.Column('level_name', sa.String(100), nullable=False),
        sa.Column('level_description', sa.Text, nullable=True),

        # Requirements
        sa.Column('min_binary_status', sa.Boolean, default=True),
        sa.Column('min_maturity_score', sa.Float, nullable=False),
        sa.Column('min_attribute_scores', sa.JSON, nullable=True),

        # Criteria
        sa.Column('mandatory_criteria', sa.JSON, nullable=True),
        sa.Column('optional_criteria', sa.JSON, nullable=True),
        sa.Column('optional_criteria_min', sa.Integer, default=0),

        # Benefits
        sa.Column('validity_years', sa.Integer, default=3),
        sa.Column('recognition_benefits', sa.JSON, nullable=True),

        # Status
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('effective_from', sa.DateTime, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create accreditation_timelines table
    op.create_table(
        'accreditation_timelines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('application_id', sa.String(36), sa.ForeignKey('accreditation_applications.id'), nullable=False),

        # Milestone Details
        sa.Column('milestone_name', sa.String(200), nullable=False),
        sa.Column('milestone_description', sa.Text, nullable=True),
        sa.Column('milestone_type', sa.String(50), nullable=False),

        # Dates
        sa.Column('planned_date', sa.DateTime, nullable=True),
        sa.Column('actual_date', sa.DateTime, nullable=True),

        # Status
        sa.Column('is_completed', sa.Boolean, default=False),
        sa.Column('completed_by', sa.String(200), nullable=True),

        # Notes
        sa.Column('notes', sa.Text, nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Insert default MBGL level criteria
    op.execute("""
        INSERT INTO mbgl_level_criteria (id, level, level_number, level_name, level_description, min_maturity_score, validity_years, is_active)
        VALUES
        ('mbgl-level-1', 'level_1', 1, 'Basic Compliance', 'Institution meets basic accreditation requirements', 1.0, 3, true),
        ('mbgl-level-2', 'level_2', 2, 'Developing', 'Institution shows developing quality practices', 2.0, 3, true),
        ('mbgl-level-3', 'level_3', 3, 'Established', 'Institution has established quality systems', 3.0, 3, true),
        ('mbgl-level-4', 'level_4', 4, 'Advanced', 'Institution demonstrates advanced quality practices', 4.0, 3, true),
        ('mbgl-level-5', 'level_5', 5, 'Excellence', 'Institution achieves excellence in all dimensions', 4.5, 3, true)
    """)


def downgrade() -> None:
    op.drop_table('accreditation_timelines')
    op.drop_table('mbgl_level_criteria')
    op.drop_table('mbgl_assessments')
    op.drop_table('attribute_scores')
    op.drop_table('accreditation_applications')
