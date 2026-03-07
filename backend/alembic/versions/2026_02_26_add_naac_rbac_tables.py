"""Add NAAC RBAC tables

Revision ID: naac_rbac_001
Revises:
Create Date: 2026-02-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# revision identifiers, used by Alembic
revision = 'naac_rbac_001'
down_revision = 'nba_001'
branch_labels = None
depends_on = None


def generate_uuid():
    return str(uuid.uuid4())


def upgrade() -> None:
    # Create naac_roles table (SQLAlchemy will auto-create enum types)
    op.create_table(
        'naac_roles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('role_type', postgresql.ENUM(
            'head_of_institution', 'iqac_coordinator', 'criterion_coordinator',
            'department_coordinator', 'documentation_team', 'it_data_analytics',
            'ssr_drafting_committee', 'student_representative', 'administrative_officer',
            'alumni_coordinator', 'placement_officer',
            name='naacrole_type', create_type=True
        ), nullable=False, unique=True),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('hierarchy_level', sa.Integer, nullable=False, default=5),
        sa.Column('can_access_all_criteria', sa.Boolean, default=False),
        sa.Column('can_access_all_departments', sa.Boolean, default=False),
        sa.Column('allowed_criteria', postgresql.JSON, nullable=True),
        sa.Column('can_approve_level', sa.Integer, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_naac_roles_role_type', 'naac_roles', ['role_type'])

    # Create naac_permissions table
    op.create_table(
        'naac_permissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('resource', sa.String(100), nullable=False),
        sa.Column('action', postgresql.ENUM(
            'view', 'create', 'edit', 'delete', 'approve', 'submit', 'export', 'assign',
            name='naacpermission_type', create_type=True
        ), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.UniqueConstraint('resource', 'action', name='uq_permission_resource_action'),
    )
    op.create_index('ix_naac_permissions_resource', 'naac_permissions', ['resource'])

    # Create role_permissions table
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('role_id', sa.String(36), sa.ForeignKey('naac_roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('permission_id', sa.String(36), sa.ForeignKey('naac_permissions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('criterion_scope', postgresql.JSON, nullable=True),
        sa.Column('department_scope', postgresql.JSON, nullable=True),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )

    # Create user_naac_roles table
    op.create_table(
        'user_naac_roles',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role_id', sa.String(36), sa.ForeignKey('naac_roles.id', ondelete='CASCADE'), nullable=False),
        sa.Column('criterion_number', sa.Integer, nullable=True),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('assigned_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_at', sa.DateTime, default=sa.func.now()),
        sa.Column('valid_from', sa.DateTime, default=sa.func.now()),
        sa.Column('valid_until', sa.DateTime, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('assignment_notes', sa.Text, nullable=True),
        sa.UniqueConstraint('user_id', 'role_id', 'criterion_number', 'department', name='uq_user_role_scope'),
    )
    op.create_index('ix_user_naac_roles_user', 'user_naac_roles', ['user_id'])
    op.create_index('ix_user_naac_roles_role', 'user_naac_roles', ['role_id'])

    # Create naac_tasks table
    op.create_table(
        'naac_tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('task_type', sa.String(50), nullable=True),
        sa.Column('criterion_number', sa.Integer, nullable=True),
        sa.Column('key_indicator', sa.String(20), nullable=True),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('academic_year', sa.String(20), nullable=True),
        sa.Column('created_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_to', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('assigned_at', sa.DateTime, nullable=True),
        sa.Column('status', postgresql.ENUM(
            'pending', 'assigned', 'in_progress', 'submitted', 'completed', 'overdue',
            name='task_status', create_type=True
        ), default='pending', nullable=False),
        sa.Column('priority', postgresql.ENUM(
            'low', 'medium', 'high', 'critical',
            name='task_priority', create_type=True
        ), default='medium', nullable=False),
        sa.Column('due_date', sa.DateTime, nullable=True),
        sa.Column('started_at', sa.DateTime, nullable=True),
        sa.Column('submitted_at', sa.DateTime, nullable=True),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('progress_percentage', sa.Integer, default=0),
        sa.Column('related_record_type', sa.String(50), nullable=True),
        sa.Column('related_record_id', sa.String(36), nullable=True),
        sa.Column('attachments', postgresql.JSON, nullable=True),
        sa.Column('extra_data', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_naac_tasks_assignee', 'naac_tasks', ['assigned_to'])
    op.create_index('ix_naac_tasks_status', 'naac_tasks', ['status'])
    op.create_index('ix_naac_tasks_criterion', 'naac_tasks', ['criterion_number'])
    op.create_index('ix_naac_tasks_due', 'naac_tasks', ['due_date'])

    # Create naac_task_comments table
    op.create_table(
        'naac_task_comments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('task_id', sa.String(36), sa.ForeignKey('naac_tasks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('attachments', postgresql.JSON, nullable=True),
        sa.Column('is_system_comment', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_naac_task_comments_task', 'naac_task_comments', ['task_id'])

    # Create naac_approval_workflows table
    op.create_table(
        'naac_approval_workflows',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('record_type', sa.String(100), nullable=False),
        sa.Column('record_id', sa.String(36), nullable=False),
        sa.Column('criterion_number', sa.Integer, nullable=True),
        sa.Column('department', sa.String(100), nullable=True),
        sa.Column('academic_year', sa.String(20), nullable=True),
        sa.Column('status', postgresql.ENUM(
            'draft', 'pending_department', 'pending_criterion', 'pending_iqac',
            'pending_head', 'approved', 'rejected', 'revision_requested',
            name='approval_status', create_type=True
        ), default='draft', nullable=False),
        sa.Column('submitted_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('submitted_at', sa.DateTime, nullable=True),
        sa.Column('submission_remarks', sa.Text, nullable=True),
        sa.Column('department_approved_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('department_approved_at', sa.DateTime, nullable=True),
        sa.Column('department_remarks', sa.Text, nullable=True),
        sa.Column('criterion_approved_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('criterion_approved_at', sa.DateTime, nullable=True),
        sa.Column('criterion_remarks', sa.Text, nullable=True),
        sa.Column('iqac_approved_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('iqac_approved_at', sa.DateTime, nullable=True),
        sa.Column('iqac_remarks', sa.Text, nullable=True),
        sa.Column('head_approved_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('head_approved_at', sa.DateTime, nullable=True),
        sa.Column('head_remarks', sa.Text, nullable=True),
        sa.Column('rejected_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('rejected_at', sa.DateTime, nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('revision_requested_by', sa.String(36), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('revision_requested_at', sa.DateTime, nullable=True),
        sa.Column('revision_remarks', sa.Text, nullable=True),
        sa.Column('approval_history', postgresql.JSON, nullable=True),
        sa.Column('extra_data', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_naac_approvals_record', 'naac_approval_workflows', ['record_type', 'record_id'])
    op.create_index('ix_naac_approvals_status', 'naac_approval_workflows', ['status'])
    op.create_index('ix_naac_approvals_criterion', 'naac_approval_workflows', ['criterion_number'])

    # Create naac_notifications table
    op.create_table(
        'naac_notifications',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('notification_type', postgresql.ENUM(
            'task_assigned', 'task_updated', 'task_completed', 'task_overdue',
            'approval_requested', 'approval_action', 'role_assigned', 'role_revoked',
            'deadline_reminder', 'system_announcement',
            name='notification_type', create_type=True
        ), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('related_entity_type', sa.String(50), nullable=True),
        sa.Column('related_entity_id', sa.String(36), nullable=True),
        sa.Column('action_url', sa.String(500), nullable=True),
        sa.Column('is_read', sa.Boolean, default=False),
        sa.Column('read_at', sa.DateTime, nullable=True),
        sa.Column('is_important', sa.Boolean, default=False),
        sa.Column('extra_data', postgresql.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime, default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime, nullable=True),
    )
    op.create_index('ix_naac_notifications_user', 'naac_notifications', ['user_id'])
    op.create_index('ix_naac_notifications_read', 'naac_notifications', ['is_read'])
    op.create_index('ix_naac_notifications_created', 'naac_notifications', ['created_at'])

    # Seed the 11 default NAAC roles
    roles_data = [
        {
            'id': generate_uuid(),
            'role_type': 'head_of_institution',
            'display_name': 'Head of Institution',
            'description': 'Principal/Director with final approval authority for all accreditation matters',
            'hierarchy_level': 1,
            'can_access_all_criteria': True,
            'can_access_all_departments': True,
            'allowed_criteria': None,
            'can_approve_level': 4,
            'is_active': True
        },
        {
            'id': generate_uuid(),
            'role_type': 'iqac_coordinator',
            'display_name': 'IQAC Coordinator',
            'description': 'Coordinates quality assurance activities across all criteria',
            'hierarchy_level': 2,
            'can_access_all_criteria': True,
            'can_access_all_departments': True,
            'allowed_criteria': None,
            'can_approve_level': 3,
            'is_active': True
        },
        {
            'id': generate_uuid(),
            'role_type': 'criterion_coordinator',
            'display_name': 'Criterion Coordinator',
            'description': 'Responsible for data collection and documentation of assigned criterion',
            'hierarchy_level': 3,
            'can_access_all_criteria': False,
            'can_access_all_departments': True,
            'allowed_criteria': None,
            'can_approve_level': 2,
            'is_active': True
        },
        {
            'id': generate_uuid(),
            'role_type': 'department_coordinator',
            'display_name': 'Department Coordinator',
            'description': 'Manages department-level data entry and initial verification',
            'hierarchy_level': 4,
            'can_access_all_criteria': False,
            'can_access_all_departments': False,
            'allowed_criteria': None,
            'can_approve_level': 1,
            'is_active': True
        },
        {
            'id': generate_uuid(),
            'role_type': 'documentation_team',
            'display_name': 'Documentation Team',
            'description': 'Assists with evidence collection and document organization',
            'hierarchy_level': 5,
            'can_access_all_criteria': True,
            'can_access_all_departments': True,
            'allowed_criteria': None,
            'can_approve_level': None,
            'is_active': True
        },
        {
            'id': generate_uuid(),
            'role_type': 'it_data_analytics',
            'display_name': 'IT/Data Analytics',
            'description': 'Handles data analysis, metrics calculation, and report generation',
            'hierarchy_level': 5,
            'can_access_all_criteria': True,
            'can_access_all_departments': True,
            'allowed_criteria': None,
            'can_approve_level': None,
            'is_active': True
        },
        {
            'id': generate_uuid(),
            'role_type': 'ssr_drafting_committee',
            'display_name': 'SSR Drafting Committee',
            'description': 'Responsible for drafting the Self Study Report',
            'hierarchy_level': 5,
            'can_access_all_criteria': True,
            'can_access_all_departments': True,
            'allowed_criteria': None,
            'can_approve_level': None,
            'is_active': True
        },
        {
            'id': generate_uuid(),
            'role_type': 'student_representative',
            'display_name': 'Student Representative',
            'description': 'Student council representative with view-only access',
            'hierarchy_level': 6,
            'can_access_all_criteria': False,
            'can_access_all_departments': False,
            'allowed_criteria': [5],  # Only Student Support criterion
            'can_approve_level': None,
            'is_active': True
        },
        {
            'id': generate_uuid(),
            'role_type': 'administrative_officer',
            'display_name': 'Administrative Officer',
            'description': 'Manages infrastructure, governance, and administrative data',
            'hierarchy_level': 5,
            'can_access_all_criteria': False,
            'can_access_all_departments': True,
            'allowed_criteria': [4, 5, 6],  # Infrastructure, Student Support, Governance
            'can_approve_level': None,
            'is_active': True
        },
        {
            'id': generate_uuid(),
            'role_type': 'alumni_coordinator',
            'display_name': 'Alumni Coordinator',
            'description': 'Manages alumni data and engagement activities',
            'hierarchy_level': 5,
            'can_access_all_criteria': False,
            'can_access_all_departments': True,
            'allowed_criteria': [5],  # Student Support
            'can_approve_level': None,
            'is_active': True
        },
        {
            'id': generate_uuid(),
            'role_type': 'placement_officer',
            'display_name': 'Placement Officer',
            'description': 'Manages placement data and career counseling records',
            'hierarchy_level': 5,
            'can_access_all_criteria': False,
            'can_access_all_departments': True,
            'allowed_criteria': [5],  # Student Support
            'can_approve_level': None,
            'is_active': True
        },
    ]

    # Insert roles
    for role in roles_data:
        allowed_criteria = role['allowed_criteria']
        if allowed_criteria:
            allowed_criteria = str(allowed_criteria).replace("'", '"')
        else:
            allowed_criteria = 'NULL'

        op.execute(f"""
            INSERT INTO naac_roles (
                id, role_type, display_name, description, hierarchy_level,
                can_access_all_criteria, can_access_all_departments, allowed_criteria,
                can_approve_level, is_active, created_at, updated_at
            ) VALUES (
                '{role['id']}',
                '{role['role_type']}',
                '{role['display_name']}',
                '{role['description'].replace("'", "''")}',
                {role['hierarchy_level']},
                {str(role['can_access_all_criteria']).lower()},
                {str(role['can_access_all_departments']).lower()},
                {f"'{allowed_criteria}'" if allowed_criteria != 'NULL' else 'NULL'},
                {role['can_approve_level'] if role['can_approve_level'] else 'NULL'},
                true,
                NOW(),
                NOW()
            )
        """)

    # Seed default permissions
    resources = ['criterion1', 'criterion2', 'criterion3', 'criterion4', 'criterion5', 'criterion6', 'criterion7',
                 'evidence', 'feedback', 'task', 'approval', 'report', 'dashboard']
    actions = ['view', 'create', 'edit', 'delete', 'approve', 'submit', 'export', 'assign']

    for resource in resources:
        for action in actions:
            perm_id = generate_uuid()
            op.execute(f"""
                INSERT INTO naac_permissions (id, resource, action, description)
                VALUES ('{perm_id}', '{resource}', '{action}', '{resource} {action} permission')
            """)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('naac_notifications')
    op.drop_table('naac_approval_workflows')
    op.drop_table('naac_task_comments')
    op.drop_table('naac_tasks')
    op.drop_table('user_naac_roles')
    op.drop_table('role_permissions')
    op.drop_table('naac_permissions')
    op.drop_table('naac_roles')

    # Drop enum types
    op.execute('DROP TYPE IF EXISTS notification_type')
    op.execute('DROP TYPE IF EXISTS task_priority')
    op.execute('DROP TYPE IF EXISTS task_status')
    op.execute('DROP TYPE IF EXISTS approval_status')
    op.execute('DROP TYPE IF EXISTS naacpermission_type')
    op.execute('DROP TYPE IF EXISTS naacrole_type')
