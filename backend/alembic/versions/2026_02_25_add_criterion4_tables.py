"""Add NAAC Criterion 4 tables

Revision ID: criterion4_001
Revises: criterion3_001
Create Date: 2026-02-25

Tables created:
- infrastructure: Physical Infrastructure (Classrooms, Labs, etc.)
- lab_equipment: Laboratory Equipment and Assets
- software_licenses: Software Licenses Management
- library_resources: Library Resources (Books, E-Resources)
- lab_utilization: Lab Utilization Logs
- maintenance_records: Maintenance Records
- e_resource_access: E-Resource Access Logs
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'criterion4_001'
down_revision = 'criterion3_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (IF NOT EXISTS for idempotency)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE infrastructuretype AS ENUM ('classroom', 'smart_classroom', 'laboratory', 'computer_lab', 'workshop', 'library', 'seminar_hall', 'auditorium', 'sports_facility', 'hostel', 'canteen', 'medical_center', 'parking', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE equipmentstatus AS ENUM ('working', 'under_maintenance', 'needs_repair', 'condemned', 'not_in_use');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE licensetype AS ENUM ('perpetual', 'subscription', 'academic', 'open_source', 'trial', 'freeware');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE resourcetype AS ENUM ('book', 'e_book', 'journal', 'e_journal', 'magazine', 'newspaper', 'cd_dvd', 'project_report', 'thesis', 'question_paper', 'other');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE maintenancetype AS ENUM ('preventive', 'corrective', 'emergency', 'upgrade', 'annual');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Create infrastructure table
    op.execute("""
        CREATE TABLE IF NOT EXISTS infrastructure (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            name VARCHAR(255) NOT NULL,
            infra_type infrastructuretype NOT NULL,
            description TEXT,
            location VARCHAR(255),
            room_number VARCHAR(50),
            department VARCHAR(255),
            is_shared BOOLEAN DEFAULT FALSE,
            area_sqft FLOAT,
            seating_capacity INTEGER,
            status equipmentstatus DEFAULT 'working',
            is_active BOOLEAN DEFAULT TRUE,
            establishment_date DATE,
            last_renovation_date DATE,
            has_projector BOOLEAN DEFAULT FALSE,
            has_smart_board BOOLEAN DEFAULT FALSE,
            has_ac BOOLEAN DEFAULT FALSE,
            has_wifi BOOLEAN DEFAULT FALSE,
            has_cctv BOOLEAN DEFAULT FALSE,
            ict_tools JSONB,
            photo_path VARCHAR(500),
            layout_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create lab_equipment table
    op.execute("""
        CREATE TABLE IF NOT EXISTS lab_equipment (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            make VARCHAR(255),
            model VARCHAR(255),
            serial_number VARCHAR(100),
            asset_id VARCHAR(100),
            lab_id VARCHAR(36) REFERENCES infrastructure(id) ON DELETE SET NULL,
            department VARCHAR(255) NOT NULL,
            purchase_date DATE,
            purchase_cost FLOAT,
            vendor_name VARCHAR(255),
            warranty_expiry DATE,
            invoice_number VARCHAR(100),
            status equipmentstatus DEFAULT 'working',
            quantity INTEGER DEFAULT 1,
            current_value FLOAT,
            last_maintenance_date DATE,
            next_maintenance_date DATE,
            amc_vendor VARCHAR(255),
            amc_expiry DATE,
            photo_path VARCHAR(500),
            invoice_path VARCHAR(500),
            manual_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create software_licenses table
    op.execute("""
        CREATE TABLE IF NOT EXISTS software_licenses (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            software_name VARCHAR(255) NOT NULL,
            version VARCHAR(50),
            vendor VARCHAR(255),
            description TEXT,
            category VARCHAR(100),
            license_type licensetype NOT NULL,
            license_key VARCHAR(500),
            license_count INTEGER DEFAULT 1,
            users_assigned INTEGER DEFAULT 0,
            department VARCHAR(255),
            is_institution_wide BOOLEAN DEFAULT FALSE,
            purchase_date DATE,
            activation_date DATE,
            expiry_date DATE,
            purchase_cost FLOAT,
            annual_cost FLOAT,
            installation_count INTEGER DEFAULT 0,
            labs_installed JSONB,
            license_document_path VARCHAR(500),
            invoice_path VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create library_resources table
    op.execute("""
        CREATE TABLE IF NOT EXISTS library_resources (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            title VARCHAR(500) NOT NULL,
            resource_type resourcetype NOT NULL,
            author VARCHAR(500),
            publisher VARCHAR(255),
            edition VARCHAR(50),
            year_of_publication INTEGER,
            isbn VARCHAR(50),
            issn VARCHAR(50),
            accession_number VARCHAR(100) UNIQUE,
            call_number VARCHAR(100),
            subject VARCHAR(255),
            department VARCHAR(255),
            keywords JSONB,
            copies_available INTEGER DEFAULT 1,
            copies_total INTEGER DEFAULT 1,
            location VARCHAR(100),
            pages INTEGER,
            is_digital BOOLEAN DEFAULT FALSE,
            digital_url VARCHAR(500),
            database_name VARCHAR(255),
            access_type VARCHAR(50),
            purchase_cost FLOAT,
            subscription_cost FLOAT,
            subscription_period VARCHAR(50),
            times_borrowed INTEGER DEFAULT 0,
            times_accessed INTEGER DEFAULT 0,
            is_available BOOLEAN DEFAULT TRUE,
            is_active BOOLEAN DEFAULT TRUE,
            acquired_date DATE,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create lab_utilization table
    op.execute("""
        CREATE TABLE IF NOT EXISTS lab_utilization (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            lab_id VARCHAR(36) NOT NULL REFERENCES infrastructure(id) ON DELETE CASCADE,
            lab_name VARCHAR(255) NOT NULL,
            department VARCHAR(255) NOT NULL,
            date DATE NOT NULL,
            start_time VARCHAR(10) NOT NULL,
            end_time VARCHAR(10) NOT NULL,
            duration_hours FLOAT,
            course_code VARCHAR(50),
            course_name VARCHAR(255),
            semester INTEGER,
            batch VARCHAR(50),
            academic_year VARCHAR(20) NOT NULL,
            faculty_name VARCHAR(255),
            faculty_email VARCHAR(255),
            students_count INTEGER DEFAULT 0,
            student_list JSONB,
            purpose VARCHAR(255),
            topics_covered JSONB,
            experiments_conducted JSONB,
            equipment_used JSONB,
            software_used JSONB,
            remarks TEXT,
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create maintenance_records table
    op.execute("""
        CREATE TABLE IF NOT EXISTS maintenance_records (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            asset_type VARCHAR(50) NOT NULL,
            asset_id VARCHAR(36) NOT NULL,
            asset_name VARCHAR(255) NOT NULL,
            department VARCHAR(255),
            maintenance_type maintenancetype NOT NULL,
            description TEXT,
            issue_reported TEXT,
            action_taken TEXT,
            request_date DATE,
            maintenance_date DATE NOT NULL,
            completion_date DATE,
            reported_by VARCHAR(255),
            technician_name VARCHAR(255),
            vendor_name VARCHAR(255),
            cost FLOAT,
            parts_replaced JSONB,
            is_completed BOOLEAN DEFAULT FALSE,
            next_maintenance_due DATE,
            work_order_path VARCHAR(500),
            invoice_path VARCHAR(500),
            photo_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Create e_resource_access table
    op.execute("""
        CREATE TABLE IF NOT EXISTS e_resource_access (
            id VARCHAR(36) PRIMARY KEY DEFAULT gen_random_uuid()::text,
            resource_id VARCHAR(36) REFERENCES library_resources(id) ON DELETE CASCADE,
            resource_name VARCHAR(500) NOT NULL,
            resource_type VARCHAR(50),
            database_name VARCHAR(255),
            access_date DATE NOT NULL,
            access_time VARCHAR(10),
            duration_minutes INTEGER,
            user_type VARCHAR(50),
            user_id VARCHAR(50),
            user_name VARCHAR(255),
            department VARCHAR(255),
            ip_address VARCHAR(50),
            access_mode VARCHAR(50),
            pages_viewed INTEGER,
            downloaded BOOLEAN DEFAULT FALSE,
            academic_year VARCHAR(20),
            created_at TIMESTAMP DEFAULT NOW() NOT NULL
        )
    """)

    # Create indexes for infrastructure
    op.execute("CREATE INDEX IF NOT EXISTS ix_infrastructure_type ON infrastructure(infra_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_infrastructure_department ON infrastructure(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_infrastructure_status ON infrastructure(status)")

    # Create indexes for lab_equipment
    op.execute("CREATE INDEX IF NOT EXISTS ix_lab_equipment_lab_id ON lab_equipment(lab_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lab_equipment_status ON lab_equipment(status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lab_equipment_department ON lab_equipment(department)")

    # Create indexes for software_licenses
    op.execute("CREATE INDEX IF NOT EXISTS ix_software_licenses_type ON software_licenses(license_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_software_licenses_department ON software_licenses(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_software_licenses_expiry ON software_licenses(expiry_date)")

    # Create indexes for library_resources
    op.execute("CREATE INDEX IF NOT EXISTS ix_library_resources_type ON library_resources(resource_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_library_resources_department ON library_resources(department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_library_resources_accession ON library_resources(accession_number)")

    # Create indexes for lab_utilization
    op.execute("CREATE INDEX IF NOT EXISTS ix_lab_utilization_lab_id ON lab_utilization(lab_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lab_utilization_date ON lab_utilization(date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_lab_utilization_department ON lab_utilization(department)")

    # Create indexes for maintenance_records
    op.execute("CREATE INDEX IF NOT EXISTS ix_maintenance_records_type ON maintenance_records(maintenance_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_maintenance_records_date ON maintenance_records(maintenance_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_maintenance_records_asset_type ON maintenance_records(asset_type)")

    # Create indexes for e_resource_access
    op.execute("CREATE INDEX IF NOT EXISTS ix_e_resource_access_resource_id ON e_resource_access(resource_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_e_resource_access_date ON e_resource_access(access_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_e_resource_access_department ON e_resource_access(department)")


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_e_resource_access_department")
    op.execute("DROP INDEX IF EXISTS ix_e_resource_access_date")
    op.execute("DROP INDEX IF EXISTS ix_e_resource_access_resource_id")
    op.execute("DROP INDEX IF EXISTS ix_maintenance_records_asset_type")
    op.execute("DROP INDEX IF EXISTS ix_maintenance_records_date")
    op.execute("DROP INDEX IF EXISTS ix_maintenance_records_type")
    op.execute("DROP INDEX IF EXISTS ix_lab_utilization_department")
    op.execute("DROP INDEX IF EXISTS ix_lab_utilization_date")
    op.execute("DROP INDEX IF EXISTS ix_lab_utilization_lab_id")
    op.execute("DROP INDEX IF EXISTS ix_library_resources_accession")
    op.execute("DROP INDEX IF EXISTS ix_library_resources_department")
    op.execute("DROP INDEX IF EXISTS ix_library_resources_type")
    op.execute("DROP INDEX IF EXISTS ix_software_licenses_expiry")
    op.execute("DROP INDEX IF EXISTS ix_software_licenses_department")
    op.execute("DROP INDEX IF EXISTS ix_software_licenses_type")
    op.execute("DROP INDEX IF EXISTS ix_lab_equipment_department")
    op.execute("DROP INDEX IF EXISTS ix_lab_equipment_status")
    op.execute("DROP INDEX IF EXISTS ix_lab_equipment_lab_id")
    op.execute("DROP INDEX IF EXISTS ix_infrastructure_status")
    op.execute("DROP INDEX IF EXISTS ix_infrastructure_department")
    op.execute("DROP INDEX IF EXISTS ix_infrastructure_type")

    # Drop tables (in reverse order of creation due to foreign keys)
    op.drop_table('e_resource_access')
    op.drop_table('maintenance_records')
    op.drop_table('lab_utilization')
    op.drop_table('library_resources')
    op.drop_table('software_licenses')
    op.drop_table('lab_equipment')
    op.drop_table('infrastructure')

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS maintenancetype")
    op.execute("DROP TYPE IF EXISTS resourcetype")
    op.execute("DROP TYPE IF EXISTS licensetype")
    op.execute("DROP TYPE IF EXISTS equipmentstatus")
    op.execute("DROP TYPE IF EXISTS infrastructuretype")
