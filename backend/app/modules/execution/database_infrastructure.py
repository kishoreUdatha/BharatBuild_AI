"""
Shared Database Infrastructure Manager

PRODUCTION APPROACH:
Instead of spinning up a separate database container for each project,
we use shared database infrastructure where each project gets its own
database/schema dynamically created.

Benefits:
1. Resource Efficient: 1 PostgreSQL cluster serves 10,000+ projects
2. Cost Effective: No per-project container overhead
3. Easier Management: Single point for backups, monitoring
4. Faster Startup: No waiting for DB container to initialize
5. Connection Pooling: Shared connection pool across projects

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                    SHARED DB INFRASTRUCTURE                      │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL Cluster (Primary)                                    │
│  ├── Database: project_abc123  (User A's project)               │
│  │   ├── Schema: public                                         │
│  │   └── Tables: users, orders, products...                     │
│  ├── Database: project_def456  (User B's project)               │
│  │   ├── Schema: public                                         │
│  │   └── Tables: users, posts, comments...                      │
│  └── Database: project_xyz789  (User C's project)               │
│      └── ...                                                     │
├─────────────────────────────────────────────────────────────────┤
│  MySQL Cluster (For MySQL projects)                              │
│  └── Same structure...                                           │
├─────────────────────────────────────────────────────────────────┤
│  MongoDB Cluster (For NoSQL projects)                            │
│  └── Database per project...                                     │
├─────────────────────────────────────────────────────────────────┤
│  Redis Cluster (Shared cache/session store)                      │
│  └── Key prefix per project: project_abc123:*                   │
└─────────────────────────────────────────────────────────────────┘
"""

import asyncio
import asyncpg
import aiomysql
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as aioredis
from typing import Dict, Optional, Any, List
from dataclasses import dataclass
from enum import Enum
import os
import re
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    REDIS = "redis"


@dataclass
class DatabaseCredentials:
    """Credentials for a project's database"""
    db_type: DatabaseType
    host: str
    port: int
    database: str
    username: str
    password: str
    connection_url: str

    def to_env_vars(self) -> Dict[str, str]:
        """Convert to environment variables for container injection"""
        base_vars = {
            "DB_HOST": self.host,
            "DB_PORT": str(self.port),
            "DB_NAME": self.database,
            "DB_USER": self.username,
            "DB_PASSWORD": self.password,
        }

        if self.db_type == DatabaseType.POSTGRESQL:
            return {
                **base_vars,
                "DATABASE_URL": self.connection_url,
                "POSTGRES_HOST": self.host,
                "POSTGRES_PORT": str(self.port),
                "POSTGRES_DB": self.database,
                "POSTGRES_USER": self.username,
                "POSTGRES_PASSWORD": self.password,
                # Spring Boot format
                "SPRING_DATASOURCE_URL": f"jdbc:postgresql://{self.host}:{self.port}/{self.database}",
                "SPRING_DATASOURCE_USERNAME": self.username,
                "SPRING_DATASOURCE_PASSWORD": self.password,
            }
        elif self.db_type == DatabaseType.MYSQL:
            return {
                **base_vars,
                "DATABASE_URL": self.connection_url,
                "MYSQL_HOST": self.host,
                "MYSQL_PORT": str(self.port),
                "MYSQL_DATABASE": self.database,
                "MYSQL_USER": self.username,
                "MYSQL_PASSWORD": self.password,
                # Spring Boot format
                "SPRING_DATASOURCE_URL": f"jdbc:mysql://{self.host}:{self.port}/{self.database}",
                "SPRING_DATASOURCE_USERNAME": self.username,
                "SPRING_DATASOURCE_PASSWORD": self.password,
            }
        elif self.db_type == DatabaseType.MONGODB:
            return {
                **base_vars,
                "MONGODB_URL": self.connection_url,
                "MONGODB_URI": self.connection_url,
                "MONGO_URL": self.connection_url,
                "MONGO_HOST": self.host,
                "MONGO_PORT": str(self.port),
                "MONGO_DB": self.database,
            }
        elif self.db_type == DatabaseType.REDIS:
            return {
                "REDIS_URL": self.connection_url,
                "REDIS_HOST": self.host,
                "REDIS_PORT": str(self.port),
            }

        return base_vars


class DatabaseInfrastructure:
    """
    Manages shared database infrastructure for all projects.

    Usage:
        db_infra = DatabaseInfrastructure()
        await db_infra.initialize()

        # Create database for a new project
        creds = await db_infra.provision_database("project_123", DatabaseType.POSTGRESQL)

        # Use creds.connection_url in the project's container

        # Cleanup when project is deleted
        await db_infra.deprovision_database("project_123", DatabaseType.POSTGRESQL)
    """

    def __init__(self):
        # Infrastructure connection settings (from environment/config)
        self.pg_host = os.getenv("INFRA_POSTGRES_HOST", "localhost")
        self.pg_port = int(os.getenv("INFRA_POSTGRES_PORT", "5432"))
        self.pg_admin_user = os.getenv("INFRA_POSTGRES_USER", "postgres")
        self.pg_admin_password = os.getenv("INFRA_POSTGRES_PASSWORD", "postgres")

        self.mysql_host = os.getenv("INFRA_MYSQL_HOST", "localhost")
        self.mysql_port = int(os.getenv("INFRA_MYSQL_PORT", "3306"))
        self.mysql_admin_user = os.getenv("INFRA_MYSQL_USER", "root")
        self.mysql_admin_password = os.getenv("INFRA_MYSQL_PASSWORD", "password")

        self.mongo_host = os.getenv("INFRA_MONGO_HOST", "localhost")
        self.mongo_port = int(os.getenv("INFRA_MONGO_PORT", "27017"))
        self.mongo_admin_user = os.getenv("INFRA_MONGO_USER", "")
        self.mongo_admin_password = os.getenv("INFRA_MONGO_PASSWORD", "")

        self.redis_host = os.getenv("INFRA_REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("INFRA_REDIS_PORT", "6379"))

        # Connection pools
        self._pg_pool: Optional[asyncpg.Pool] = None
        self._mysql_pool = None
        self._mongo_client: Optional[AsyncIOMotorClient] = None
        self._redis_client: Optional[aioredis.Redis] = None

        # Track provisioned databases
        self._provisioned: Dict[str, Dict[str, DatabaseCredentials]] = {}

    async def initialize(self):
        """Initialize connection pools to infrastructure databases"""
        try:
            # PostgreSQL pool
            self._pg_pool = await asyncpg.create_pool(
                host=self.pg_host,
                port=self.pg_port,
                user=self.pg_admin_user,
                password=self.pg_admin_password,
                database="postgres",  # Admin database
                min_size=5,
                max_size=20
            )
            logger.info(f"PostgreSQL infrastructure pool initialized: {self.pg_host}:{self.pg_port}")
        except Exception as e:
            logger.warning(f"PostgreSQL infrastructure not available: {e}")

        try:
            # MySQL pool
            self._mysql_pool = await aiomysql.create_pool(
                host=self.mysql_host,
                port=self.mysql_port,
                user=self.mysql_admin_user,
                password=self.mysql_admin_password,
                minsize=5,
                maxsize=20
            )
            logger.info(f"MySQL infrastructure pool initialized: {self.mysql_host}:{self.mysql_port}")
        except Exception as e:
            logger.warning(f"MySQL infrastructure not available: {e}")

        try:
            # MongoDB client
            mongo_uri = f"mongodb://{self.mongo_host}:{self.mongo_port}"
            if self.mongo_admin_user and self.mongo_admin_password:
                mongo_uri = f"mongodb://{self.mongo_admin_user}:{self.mongo_admin_password}@{self.mongo_host}:{self.mongo_port}"
            self._mongo_client = AsyncIOMotorClient(mongo_uri)
            logger.info(f"MongoDB infrastructure client initialized: {self.mongo_host}:{self.mongo_port}")
        except Exception as e:
            logger.warning(f"MongoDB infrastructure not available: {e}")

        try:
            # Redis client
            self._redis_client = await aioredis.from_url(
                f"redis://{self.redis_host}:{self.redis_port}"
            )
            logger.info(f"Redis infrastructure client initialized: {self.redis_host}:{self.redis_port}")
        except Exception as e:
            logger.warning(f"Redis infrastructure not available: {e}")

    def _sanitize_db_name(self, project_id: str) -> str:
        """Sanitize project_id to valid database name"""
        # Remove non-alphanumeric chars, replace with underscore
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', project_id)
        # Ensure it starts with letter
        if safe_name and not safe_name[0].isalpha():
            safe_name = f"p_{safe_name}"
        # Limit length
        return safe_name[:63].lower()

    def _generate_password(self, project_id: str) -> str:
        """Generate a deterministic but secure password for project"""
        import hashlib
        secret = os.getenv("DB_PASSWORD_SECRET", "bharatbuild-secret-key")
        hash_input = f"{project_id}:{secret}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:32]

    async def provision_database(
        self,
        project_id: str,
        db_type: DatabaseType
    ) -> DatabaseCredentials:
        """
        Provision a new database for a project.
        Creates database/schema if it doesn't exist.
        """
        db_name = self._sanitize_db_name(project_id)
        password = self._generate_password(project_id)

        if db_type == DatabaseType.POSTGRESQL:
            return await self._provision_postgresql(project_id, db_name, password)
        elif db_type == DatabaseType.MYSQL:
            return await self._provision_mysql(project_id, db_name, password)
        elif db_type == DatabaseType.MONGODB:
            return await self._provision_mongodb(project_id, db_name)
        elif db_type == DatabaseType.REDIS:
            return self._provision_redis(project_id)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    async def _provision_postgresql(
        self,
        project_id: str,
        db_name: str,
        password: str
    ) -> DatabaseCredentials:
        """Provision PostgreSQL database"""
        if not self._pg_pool:
            raise RuntimeError("PostgreSQL infrastructure not available")

        async with self._pg_pool.acquire() as conn:
            # Check if database exists
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1",
                db_name
            )

            if not exists:
                # Create database
                # Note: CREATE DATABASE can't be in a transaction
                await conn.execute(f'CREATE DATABASE "{db_name}"')
                logger.info(f"Created PostgreSQL database: {db_name}")

            # Create user if not exists and grant privileges
            user_exists = await conn.fetchval(
                "SELECT 1 FROM pg_roles WHERE rolname = $1",
                db_name
            )

            if not user_exists:
                await conn.execute(
                    f'CREATE USER "{db_name}" WITH PASSWORD \'{password}\''
                )
                await conn.execute(
                    f'GRANT ALL PRIVILEGES ON DATABASE "{db_name}" TO "{db_name}"'
                )
                logger.info(f"Created PostgreSQL user: {db_name}")

        # Connect to new database and grant schema privileges
        conn = await asyncpg.connect(
            host=self.pg_host,
            port=self.pg_port,
            user=self.pg_admin_user,
            password=self.pg_admin_password,
            database=db_name
        )
        try:
            await conn.execute(
                f'GRANT ALL ON SCHEMA public TO "{db_name}"'
            )
            await conn.execute(
                f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO "{db_name}"'
            )
        finally:
            await conn.close()

        connection_url = f"postgresql://{db_name}:{password}@{self.pg_host}:{self.pg_port}/{db_name}"

        creds = DatabaseCredentials(
            db_type=DatabaseType.POSTGRESQL,
            host=self.pg_host,
            port=self.pg_port,
            database=db_name,
            username=db_name,
            password=password,
            connection_url=connection_url
        )

        # Track provisioned database
        if project_id not in self._provisioned:
            self._provisioned[project_id] = {}
        self._provisioned[project_id][DatabaseType.POSTGRESQL.value] = creds

        return creds

    async def _provision_mysql(
        self,
        project_id: str,
        db_name: str,
        password: str
    ) -> DatabaseCredentials:
        """Provision MySQL database"""
        if not self._mysql_pool:
            raise RuntimeError("MySQL infrastructure not available")

        async with self._mysql_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Create database if not exists
                await cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{db_name}`"
                )

                # Create user if not exists
                await cur.execute(
                    f"CREATE USER IF NOT EXISTS '{db_name}'@'%' IDENTIFIED BY '{password}'"
                )

                # Grant privileges
                await cur.execute(
                    f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO '{db_name}'@'%'"
                )

                await cur.execute("FLUSH PRIVILEGES")

                logger.info(f"Created MySQL database and user: {db_name}")

        connection_url = f"mysql://{db_name}:{password}@{self.mysql_host}:{self.mysql_port}/{db_name}"

        creds = DatabaseCredentials(
            db_type=DatabaseType.MYSQL,
            host=self.mysql_host,
            port=self.mysql_port,
            database=db_name,
            username=db_name,
            password=password,
            connection_url=connection_url
        )

        if project_id not in self._provisioned:
            self._provisioned[project_id] = {}
        self._provisioned[project_id][DatabaseType.MYSQL.value] = creds

        return creds

    async def _provision_mongodb(
        self,
        project_id: str,
        db_name: str
    ) -> DatabaseCredentials:
        """Provision MongoDB database"""
        if not self._mongo_client:
            raise RuntimeError("MongoDB infrastructure not available")

        # MongoDB creates database automatically on first write
        # Just verify connection and create a placeholder collection
        db = self._mongo_client[db_name]
        await db.command("ping")

        # Create a system collection to ensure DB exists
        await db["_system"].insert_one({"created": True})
        await db["_system"].delete_many({})

        logger.info(f"Created MongoDB database: {db_name}")

        connection_url = f"mongodb://{self.mongo_host}:{self.mongo_port}/{db_name}"
        if self.mongo_admin_user:
            connection_url = f"mongodb://{self.mongo_admin_user}:{self.mongo_admin_password}@{self.mongo_host}:{self.mongo_port}/{db_name}"

        creds = DatabaseCredentials(
            db_type=DatabaseType.MONGODB,
            host=self.mongo_host,
            port=self.mongo_port,
            database=db_name,
            username=self.mongo_admin_user or "",
            password=self.mongo_admin_password or "",
            connection_url=connection_url
        )

        if project_id not in self._provisioned:
            self._provisioned[project_id] = {}
        self._provisioned[project_id][DatabaseType.MONGODB.value] = creds

        return creds

    def _provision_redis(self, project_id: str) -> DatabaseCredentials:
        """Provision Redis namespace (key prefix)"""
        # Redis uses key prefixes for isolation, not separate databases
        db_name = self._sanitize_db_name(project_id)

        connection_url = f"redis://{self.redis_host}:{self.redis_port}"

        creds = DatabaseCredentials(
            db_type=DatabaseType.REDIS,
            host=self.redis_host,
            port=self.redis_port,
            database=db_name,  # Used as key prefix
            username="",
            password="",
            connection_url=connection_url
        )

        if project_id not in self._provisioned:
            self._provisioned[project_id] = {}
        self._provisioned[project_id][DatabaseType.REDIS.value] = creds

        return creds

    async def deprovision_database(
        self,
        project_id: str,
        db_type: DatabaseType,
        keep_data: bool = False
    ) -> bool:
        """
        Deprovision a project's database.

        Args:
            project_id: Project identifier
            db_type: Type of database
            keep_data: If True, keeps the database but revokes access (soft delete)
        """
        db_name = self._sanitize_db_name(project_id)

        try:
            if db_type == DatabaseType.POSTGRESQL and self._pg_pool:
                async with self._pg_pool.acquire() as conn:
                    if keep_data:
                        # Just revoke access
                        await conn.execute(
                            f'REVOKE ALL PRIVILEGES ON DATABASE "{db_name}" FROM "{db_name}"'
                        )
                    else:
                        # Terminate connections and drop database
                        await conn.execute(f"""
                            SELECT pg_terminate_backend(pg_stat_activity.pid)
                            FROM pg_stat_activity
                            WHERE pg_stat_activity.datname = '{db_name}'
                            AND pid <> pg_backend_pid()
                        """)
                        await conn.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
                        await conn.execute(f'DROP USER IF EXISTS "{db_name}"')

            elif db_type == DatabaseType.MYSQL and self._mysql_pool:
                async with self._mysql_pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        if keep_data:
                            await cur.execute(
                                f"REVOKE ALL PRIVILEGES ON `{db_name}`.* FROM '{db_name}'@'%'"
                            )
                        else:
                            await cur.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
                            await cur.execute(f"DROP USER IF EXISTS '{db_name}'@'%'")

            elif db_type == DatabaseType.MONGODB and self._mongo_client:
                if not keep_data:
                    await self._mongo_client.drop_database(db_name)

            elif db_type == DatabaseType.REDIS and self._redis_client:
                if not keep_data:
                    # Delete all keys with project prefix
                    cursor = 0
                    pattern = f"{db_name}:*"
                    while True:
                        cursor, keys = await self._redis_client.scan(cursor, match=pattern)
                        if keys:
                            await self._redis_client.delete(*keys)
                        if cursor == 0:
                            break

            # Remove from tracking
            if project_id in self._provisioned:
                if db_type.value in self._provisioned[project_id]:
                    del self._provisioned[project_id][db_type.value]
                if not self._provisioned[project_id]:
                    del self._provisioned[project_id]

            logger.info(f"Deprovisioned {db_type.value} database for project {project_id}")
            return True

        except Exception as e:
            logger.error(f"Error deprovisioning database: {e}")
            return False

    def get_credentials(
        self,
        project_id: str,
        db_type: DatabaseType
    ) -> Optional[DatabaseCredentials]:
        """Get credentials for a provisioned database"""
        if project_id in self._provisioned:
            return self._provisioned[project_id].get(db_type.value)
        return None

    async def get_database_stats(self, project_id: str) -> Dict[str, Any]:
        """Get database usage statistics for a project"""
        db_name = self._sanitize_db_name(project_id)
        stats = {}

        # PostgreSQL stats
        if self._pg_pool:
            try:
                async with self._pg_pool.acquire() as conn:
                    size = await conn.fetchval(
                        "SELECT pg_database_size($1)",
                        db_name
                    )
                    if size:
                        stats["postgresql"] = {
                            "size_bytes": size,
                            "size_mb": round(size / (1024 * 1024), 2)
                        }
            except:
                pass

        # MySQL stats
        if self._mysql_pool:
            try:
                async with self._mysql_pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(f"""
                            SELECT SUM(data_length + index_length) as size
                            FROM information_schema.tables
                            WHERE table_schema = '{db_name}'
                        """)
                        result = await cur.fetchone()
                        if result and result[0]:
                            stats["mysql"] = {
                                "size_bytes": result[0],
                                "size_mb": round(result[0] / (1024 * 1024), 2)
                            }
            except:
                pass

        # MongoDB stats
        if self._mongo_client:
            try:
                db = self._mongo_client[db_name]
                db_stats = await db.command("dbStats")
                stats["mongodb"] = {
                    "size_bytes": db_stats.get("dataSize", 0),
                    "size_mb": round(db_stats.get("dataSize", 0) / (1024 * 1024), 2),
                    "collections": db_stats.get("collections", 0)
                }
            except:
                pass

        return stats

    async def run_migrations(
        self,
        project_id: str,
        db_type: DatabaseType,
        sql_content: str
    ) -> bool:
        """
        Run SQL migrations for a project.
        Used for seed data and schema setup.
        """
        db_name = self._sanitize_db_name(project_id)

        try:
            if db_type == DatabaseType.POSTGRESQL:
                conn = await asyncpg.connect(
                    host=self.pg_host,
                    port=self.pg_port,
                    user=self.pg_admin_user,
                    password=self.pg_admin_password,
                    database=db_name
                )
                try:
                    await conn.execute(sql_content)
                    logger.info(f"Ran PostgreSQL migrations for {project_id}")
                    return True
                finally:
                    await conn.close()

            elif db_type == DatabaseType.MYSQL:
                async with self._mysql_pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute(f"USE `{db_name}`")
                        # Split by semicolon and execute each statement
                        for statement in sql_content.split(';'):
                            statement = statement.strip()
                            if statement:
                                await cur.execute(statement)
                        logger.info(f"Ran MySQL migrations for {project_id}")
                        return True

        except Exception as e:
            logger.error(f"Migration error for {project_id}: {e}")
            return False

        return False

    async def close(self):
        """Close all connections"""
        if self._pg_pool:
            await self._pg_pool.close()
        if self._mysql_pool:
            self._mysql_pool.close()
            await self._mysql_pool.wait_closed()
        if self._mongo_client:
            self._mongo_client.close()
        if self._redis_client:
            await self._redis_client.close()


# Global instance
db_infrastructure = DatabaseInfrastructure()


# ============================================================================
# HELPER FUNCTIONS FOR DOCKER INTEGRATION
# ============================================================================

async def get_database_env_vars(
    project_id: str,
    db_type: DatabaseType
) -> Dict[str, str]:
    """
    Get environment variables for database connection.
    Provisions database if needed.
    """
    creds = db_infrastructure.get_credentials(project_id, db_type)
    if not creds:
        creds = await db_infrastructure.provision_database(project_id, db_type)
    return creds.to_env_vars()


def detect_database_type(project_path: str) -> DatabaseType:
    """
    Detect which database type a project needs based on its files.
    """
    from pathlib import Path
    path = Path(project_path)

    # Check various config files
    files_to_check = [
        path / "requirements.txt",
        path / "backend" / "requirements.txt",
        path / "package.json",
        path / "backend" / "package.json",
        path / "pom.xml",
        path / "backend" / "pom.xml",
        path / "build.gradle",
        path / "application.properties",
        path / "application.yml",
    ]

    for file_path in files_to_check:
        if file_path.exists():
            try:
                content = file_path.read_text().lower()

                if "mongodb" in content or "mongoose" in content:
                    return DatabaseType.MONGODB
                elif "mysql" in content or "mariadb" in content:
                    return DatabaseType.MYSQL
                elif "postgresql" in content or "psycopg" in content or "pg" in content:
                    return DatabaseType.POSTGRESQL
            except:
                pass

    # Default to PostgreSQL
    return DatabaseType.POSTGRESQL
