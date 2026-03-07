"""add_college_onboarding_tables

Revision ID: 353a63b07534
Revises: 709ed4ac38d4
Create Date: 2026-02-26 15:26:49.841062

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '353a63b07534'
down_revision = '709ed4ac38d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types first (IF NOT EXISTS)
    op.execute("DO $$ BEGIN CREATE TYPE collegetype AS ENUM ('AUTONOMOUS', 'AFFILIATED', 'DEEMED', 'CENTRAL', 'STATE', 'PRIVATE'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE accreditationstatus AS ENUM ('NOT_ACCREDITED', 'NAAC_APPLIED', 'NAAC_ACCREDITED', 'NBA_APPLIED', 'NBA_ACCREDITED', 'BOTH_ACCREDITED'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE college_subscriptionplan AS ENUM ('FREE_TRIAL', 'BASIC', 'PRO', 'ENTERPRISE'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE onboardingstep AS ENUM ('REGISTRATION', 'PROFILE_SETUP', 'DEPARTMENTS', 'PROGRAMS', 'TEAM_SETUP', 'ROLE_ASSIGNMENT', 'COMPLETED'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE invitationstatus AS ENUM ('PENDING', 'ACCEPTED', 'EXPIRED', 'CANCELLED'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    # Create college_profiles table
    op.create_table('college_profiles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('short_name', sa.String(100), nullable=True),
        sa.Column('aishe_code', sa.String(50), nullable=True),
        sa.Column('college_type', sa.VARCHAR(50), nullable=True),
        sa.Column('university_affiliation', sa.String(500), nullable=True),
        sa.Column('year_established', sa.Integer(), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(100), nullable=True),
        sa.Column('pincode', sa.String(10), nullable=True),
        sa.Column('country', sa.String(100), nullable=True, server_default='India'),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('principal_name', sa.String(255), nullable=True),
        sa.Column('principal_email', sa.String(255), nullable=True),
        sa.Column('principal_phone', sa.String(20), nullable=True),
        sa.Column('iqac_coordinator_name', sa.String(255), nullable=True),
        sa.Column('iqac_coordinator_email', sa.String(255), nullable=True),
        sa.Column('accreditation_status', sa.VARCHAR(50), nullable=True, server_default='not_accredited'),
        sa.Column('naac_grade', sa.String(10), nullable=True),
        sa.Column('naac_cgpa', sa.String(10), nullable=True),
        sa.Column('naac_validity', sa.DateTime(), nullable=True),
        sa.Column('nba_accredited_programs', sa.JSON(), nullable=True),
        sa.Column('aicte_approval_number', sa.String(100), nullable=True),
        sa.Column('ugc_recognition', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('naac_application_id', sa.String(100), nullable=True),
        sa.Column('subscription_plan', sa.VARCHAR(50), nullable=True, server_default='free_trial'),
        sa.Column('subscription_start', sa.DateTime(), nullable=True),
        sa.Column('subscription_end', sa.DateTime(), nullable=True),
        sa.Column('onboarding_step', sa.VARCHAR(50), nullable=True, server_default='REGISTRATION'),
        sa.Column('onboarding_completed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('onboarding_completed_at', sa.DateTime(), nullable=True),
        sa.Column('admin_user_id', sa.String(36), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('total_students', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_faculty', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_programs', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('total_departments', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['admin_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aishe_code')
    )

    # Create college_departments table
    op.create_table('college_departments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('college_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), nullable=True),
        sa.Column('hod_name', sa.String(255), nullable=True),
        sa.Column('hod_email', sa.String(255), nullable=True),
        sa.Column('hod_user_id', sa.String(36), nullable=True),
        sa.Column('faculty_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('student_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['college_id'], ['college_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hod_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create college_programs table
    op.create_table('college_programs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('college_id', sa.String(36), nullable=False),
        sa.Column('department_id', sa.String(36), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('code', sa.String(50), nullable=True),
        sa.Column('degree_type', sa.String(50), nullable=True),
        sa.Column('duration_years', sa.Integer(), nullable=True, server_default='4'),
        sa.Column('intake', sa.Integer(), nullable=True, server_default='60'),
        sa.Column('nba_accredited', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('nba_validity', sa.DateTime(), nullable=True),
        sa.Column('tier', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['college_id'], ['college_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['college_departments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create college_invitations table
    op.create_table('college_invitations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('college_id', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('naac_role', sa.String(100), nullable=True),
        sa.Column('department_id', sa.String(36), nullable=True),
        sa.Column('criterion_number', sa.Integer(), nullable=True),
        sa.Column('invite_token', sa.String(255), nullable=False),
        sa.Column('status', sa.VARCHAR(50), nullable=True, server_default='PENDING'),
        sa.Column('invited_by_id', sa.String(36), nullable=True),
        sa.Column('accepted_by_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['accepted_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['college_id'], ['college_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['college_departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invite_token')
    )

    # Create onboarding_progress table
    op.create_table('onboarding_progress',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('college_id', sa.String(36), nullable=False),
        sa.Column('registration_completed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('profile_completed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('departments_added', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('programs_added', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('team_invited', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('roles_assigned', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('first_data_entered', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('departments_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('programs_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('team_members_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('invitations_sent', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('invitations_accepted', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('completion_percentage', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('current_step', sa.VARCHAR(50), nullable=True, server_default='REGISTRATION'),
        sa.Column('registration_at', sa.DateTime(), nullable=True),
        sa.Column('profile_at', sa.DateTime(), nullable=True),
        sa.Column('departments_at', sa.DateTime(), nullable=True),
        sa.Column('programs_at', sa.DateTime(), nullable=True),
        sa.Column('team_at', sa.DateTime(), nullable=True),
        sa.Column('roles_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['college_id'], ['college_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('college_id')
    )

    # Create indexes
    op.create_index('ix_college_profiles_aishe_code', 'college_profiles', ['aishe_code'])
    op.create_index('ix_college_profiles_state', 'college_profiles', ['state'])
    op.create_index('ix_college_departments_college_id', 'college_departments', ['college_id'])
    op.create_index('ix_college_programs_college_id', 'college_programs', ['college_id'])
    op.create_index('ix_college_invitations_college_id', 'college_invitations', ['college_id'])
    op.create_index('ix_college_invitations_email', 'college_invitations', ['email'])
    op.create_index('ix_college_invitations_token', 'college_invitations', ['invite_token'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_college_invitations_token', table_name='college_invitations')
    op.drop_index('ix_college_invitations_email', table_name='college_invitations')
    op.drop_index('ix_college_invitations_college_id', table_name='college_invitations')
    op.drop_index('ix_college_programs_college_id', table_name='college_programs')
    op.drop_index('ix_college_departments_college_id', table_name='college_departments')
    op.drop_index('ix_college_profiles_state', table_name='college_profiles')
    op.drop_index('ix_college_profiles_aishe_code', table_name='college_profiles')

    # Drop tables
    op.drop_table('onboarding_progress')
    op.drop_table('college_invitations')
    op.drop_table('college_programs')
    op.drop_table('college_departments')
    op.drop_table('college_profiles')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS invitationstatus")
    op.execute("DROP TYPE IF EXISTS onboardingstep")
    op.execute("DROP TYPE IF EXISTS college_subscriptionplan")
    op.execute("DROP TYPE IF EXISTS accreditationstatus")
    op.execute("DROP TYPE IF EXISTS collegetype")
