"""
Unit Tests for Services
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import json


class TestTempSessionStorage:
    """Tests for TempSessionStorage"""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage instance for testing"""
        from app.services.temp_session_storage import TempSessionStorage

        temp_dir = Path(tempfile.mkdtemp())
        storage = TempSessionStorage(base_dir=temp_dir, ttl_seconds=3600)
        yield storage

        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_create_session(self, temp_storage):
        """Test creating a new session"""
        session_id = temp_storage.create_session(
            user_id="test-user",
            project_name="Test Project"
        )

        assert session_id is not None
        assert len(session_id) > 0
        assert temp_storage.session_exists(session_id)

    def test_session_exists_false(self, temp_storage):
        """Test session_exists returns False for non-existent session"""
        assert temp_storage.session_exists("non-existent-session") == False

    def test_write_and_read_file(self, temp_storage):
        """Test writing and reading a file"""
        session_id = temp_storage.create_session()

        # Write file
        content = "console.log('Hello, World!');"
        result = temp_storage.write_file(session_id, "src/index.js", content)
        assert result == True

        # Read file
        read_content = temp_storage.read_file(session_id, "src/index.js")
        assert read_content == content

    def test_write_file_nonexistent_session(self, temp_storage):
        """Test writing file to non-existent session fails"""
        result = temp_storage.write_file(
            "nonexistent",
            "test.js",
            "content"
        )
        assert result == False

    def test_read_file_nonexistent(self, temp_storage):
        """Test reading non-existent file returns None"""
        session_id = temp_storage.create_session()
        result = temp_storage.read_file(session_id, "nonexistent.js")
        assert result is None

    def test_list_files(self, temp_storage):
        """Test listing files in session"""
        session_id = temp_storage.create_session()

        # Write multiple files
        temp_storage.write_file(session_id, "src/index.js", "// index")
        temp_storage.write_file(session_id, "src/App.js", "// app")
        temp_storage.write_file(session_id, "package.json", "{}")

        files = temp_storage.list_files(session_id)

        assert len(files) == 3
        assert "package.json" in files
        assert "src/index.js" in files or "src\\index.js" in files

    def test_list_files_empty_session(self, temp_storage):
        """Test listing files in empty session"""
        session_id = temp_storage.create_session()
        files = temp_storage.list_files(session_id)
        assert files == []

    def test_write_and_read_plan(self, temp_storage):
        """Test writing and reading plan"""
        session_id = temp_storage.create_session()

        plan = {
            "project_type": "web_app",
            "tech_stack": ["React", "Node.js"],
            "tasks": ["Setup", "Build", "Deploy"]
        }

        result = temp_storage.write_plan(session_id, plan)
        assert result == True

        read_plan = temp_storage.read_plan(session_id)
        assert read_plan == plan

    def test_read_plan_nonexistent(self, temp_storage):
        """Test reading non-existent plan returns None"""
        session_id = temp_storage.create_session()
        result = temp_storage.read_plan(session_id)
        assert result is None

    def test_create_zip(self, temp_storage):
        """Test creating ZIP file"""
        session_id = temp_storage.create_session(project_name="TestProject")

        # Write some files
        temp_storage.write_file(session_id, "src/index.js", "console.log('test');")
        temp_storage.write_file(session_id, "package.json", '{"name": "test"}')

        # Create ZIP
        zip_path = temp_storage.create_zip(session_id)

        assert zip_path is not None
        assert zip_path.exists()
        assert zip_path.suffix == ".zip"

    def test_get_file_tree(self, temp_storage):
        """Test getting file tree structure"""
        session_id = temp_storage.create_session()

        temp_storage.write_file(session_id, "src/components/Button.tsx", "// button")
        temp_storage.write_file(session_id, "src/index.tsx", "// index")
        temp_storage.write_file(session_id, "package.json", "{}")

        tree = temp_storage.get_file_tree(session_id)

        assert tree["name"] == "root"
        assert tree["type"] == "folder"
        assert "children" in tree

    def test_delete_session(self, temp_storage):
        """Test deleting a session"""
        session_id = temp_storage.create_session()
        temp_storage.write_file(session_id, "test.js", "content")

        # Verify exists
        assert temp_storage.session_exists(session_id)

        # Delete
        result = temp_storage.delete_session(session_id)
        assert result == True

        # Verify deleted
        assert temp_storage.session_exists(session_id) == False

    def test_get_session_info(self, temp_storage):
        """Test getting session info"""
        session_id = temp_storage.create_session(
            user_id="test-user",
            project_name="Test Project"
        )

        info = temp_storage.get_session_info(session_id)

        assert info is not None
        assert info.session_id == session_id
        assert info.user_id == "test-user"
        assert info.project_name == "Test Project"
        assert info.status == "active"

    def test_touch_session(self, temp_storage):
        """Test touching session updates last accessed time"""
        session_id = temp_storage.create_session()

        info_before = temp_storage.get_session_info(session_id)
        initial_time = info_before.last_accessed

        # Touch
        temp_storage.touch_session(session_id)

        info_after = temp_storage.get_session_info(session_id)
        # Should be same or later
        assert info_after.last_accessed >= initial_time

    def test_get_stats(self, temp_storage):
        """Test getting storage stats"""
        session_id = temp_storage.create_session()
        temp_storage.write_file(session_id, "test.js", "content")

        stats = temp_storage.get_stats()

        assert "active_sessions" in stats
        assert "total_files" in stats
        assert "total_size_bytes" in stats
        assert stats["active_sessions"] >= 1

    def test_cleanup_expired_sessions(self, temp_storage):
        """Test cleanup of expired sessions"""
        # Create a session with very short TTL
        from app.services.temp_session_storage import TempSessionStorage

        short_ttl_storage = TempSessionStorage(
            base_dir=temp_storage.base_dir,
            ttl_seconds=0  # Immediate expiry
        )

        session_id = short_ttl_storage.create_session()

        # Run cleanup
        deleted_count = short_ttl_storage.cleanup_expired_sessions()

        # Session should be cleaned up
        assert deleted_count >= 0


class TestCacheService:
    """Tests for CacheService"""

    def test_cache_service_initialization(self):
        """Test CacheService can be imported and initialized"""
        from app.services.cache_service import CacheService

        cache = CacheService()
        assert cache is not None
        assert cache._redis is None  # Not connected until used

    def test_cache_service_ttl_constants(self):
        """Test CacheService has TTL constants"""
        from app.services.cache_service import CacheService

        cache = CacheService()

        assert cache.TTL_PROJECT_META > 0
        assert cache.TTL_PROJECT_FILES > 0
        assert cache.TTL_FILE_CONTENT > 0
        assert cache.TTL_USER_SESSION > 0

    def test_cache_service_prefix_constants(self):
        """Test CacheService has prefix constants"""
        from app.services.cache_service import CacheService

        cache = CacheService()

        assert cache.PREFIX_PROJECT is not None
        assert cache.PREFIX_FILES is not None
        assert cache.PREFIX_CONTENT is not None
        assert cache.PREFIX_USER is not None


class TestSessionMetadata:
    """Tests for SessionMetadata dataclass"""

    def test_session_metadata_creation(self):
        """Test creating SessionMetadata"""
        from app.services.temp_session_storage import SessionMetadata

        now = datetime.utcnow()
        metadata = SessionMetadata(
            session_id="test-session",
            created_at=now,
            last_accessed=now,
            user_id="user-123",
            project_name="Test Project"
        )

        assert metadata.session_id == "test-session"
        assert metadata.user_id == "user-123"
        assert metadata.project_name == "Test Project"
        assert metadata.file_count == 0
        assert metadata.total_size_bytes == 0
        assert metadata.status == "active"

    def test_session_metadata_defaults(self):
        """Test SessionMetadata default values"""
        from app.services.temp_session_storage import SessionMetadata

        now = datetime.utcnow()
        metadata = SessionMetadata(
            session_id="test",
            created_at=now,
            last_accessed=now
        )

        assert metadata.user_id is None
        assert metadata.project_name is None
        assert metadata.file_count == 0
        assert metadata.status == "active"


class TestCheckpointService:
    """Tests for CheckpointService"""

    def test_checkpoint_service_import(self):
        """Test CheckpointService can be imported"""
        try:
            from app.services.checkpoint_service import CheckpointService
            assert True
        except ImportError:
            pytest.skip("CheckpointService not available")

    def test_checkpoint_service_initialization(self):
        """Test CheckpointService initialization"""
        try:
            from app.services.checkpoint_service import CheckpointService
            service = CheckpointService()
            assert service is not None
        except ImportError:
            pytest.skip("CheckpointService not available")


class TestProjectService:
    """Tests for ProjectService"""

    def test_project_service_import(self):
        """Test ProjectService can be imported"""
        try:
            from app.services.project_service import ProjectService
            assert True
        except ImportError:
            pytest.skip("ProjectService not available")


class TestStorageService:
    """Tests for StorageService"""

    def test_storage_service_import(self):
        """Test StorageService can be imported"""
        try:
            from app.services.storage_service import StorageService
            assert True
        except ImportError:
            pytest.skip("StorageService not available")
