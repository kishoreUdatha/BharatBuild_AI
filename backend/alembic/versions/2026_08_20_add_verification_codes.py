"""One-time codes for email and mobile verification.

Registration previously issued an email link that nothing depended on, and had
no mobile check at all. These codes are proof-of-ownership taken on the
registration form itself, before the account exists - so the table is keyed by
the destination rather than by a user.

Only a salted hash of the code is stored.

Revision ID: add_verification_codes
Revises: add_student_registration
"""

from alembic import op

revision = 'add_verification_codes'
down_revision = 'add_student_registration'
branch_labels = None
depends_on = None

# Labels are the Python enum MEMBER NAMES, uppercase - SQLAlchemy persists
# Enum(PyEnum) members by name.
ENUMS = {
    "verificationchannel": ["EMAIL", "PHONE"],
    "verificationpurpose": ["SIGNUP", "PROFILE_UPDATE"],
}


def upgrade() -> None:
    for name, values in ENUMS.items():
        labels = ", ".join(f"'{v}'" for v in values)
        op.execute(f"""
            DO $$ BEGIN
                CREATE TYPE {name} AS ENUM ({labels});
            EXCEPTION WHEN duplicate_object THEN null;
            END $$;
        """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS verification_codes (
            id UUID PRIMARY KEY,
            channel verificationchannel NOT NULL,
            destination VARCHAR(180) NOT NULL,
            purpose verificationpurpose NOT NULL DEFAULT 'SIGNUP',
            code_hash VARCHAR(128) NOT NULL,
            salt VARCHAR(32) NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            send_count INTEGER NOT NULL DEFAULT 1,
            expires_at TIMESTAMP NOT NULL,
            last_sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
            verified_at TIMESTAMP,
            consumed_at TIMESTAMP,
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            request_ip VARCHAR(64),
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_verification_codes_channel ON verification_codes (channel);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_verification_codes_destination ON verification_codes (destination);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_verification_codes_expires_at ON verification_codes (expires_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_verification_codes_user_id ON verification_codes (user_id);")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_verification_lookup
        ON verification_codes (channel, destination, consumed_at);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS verification_codes CASCADE;")
    for name in ENUMS:
        op.execute(f"DROP TYPE IF EXISTS {name};")
