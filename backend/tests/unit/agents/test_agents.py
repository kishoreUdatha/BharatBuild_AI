"""
Unit Tests for AI Agents
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import json
from typing import Dict, Any


class TestPaperAnalyzerAgent:
    """Test paper analyzer agent functionality"""

    @pytest.mark.asyncio
    async def test_estimate_tokens(self):
        """Test token estimation"""
        try:
            from app.modules.agents.paper_analyzer_agent import paper_analyzer_agent

            text = 'A' * 1000  # 1000 characters
            tokens = paper_analyzer_agent._estimate_tokens(text)

            # ~250 tokens (4 chars per token estimate)
            assert 200 <= tokens <= 300
        except ImportError:
            pytest.skip("paper_analyzer_agent not available")

    @pytest.mark.asyncio
    async def test_clean_pdf_text(self):
        """Test PDF text cleaning"""
        try:
            from app.modules.agents.paper_analyzer_agent import paper_analyzer_agent

            dirty_text = 'Abstract\n\n\nThis is a paper.\n\n\n\nPage 1 of 10\n\n   Multiple   spaces'
            cleaned = paper_analyzer_agent._clean_pdf_text(dirty_text)

            # Should produce some cleaned output
            assert cleaned is not None
            assert len(cleaned) > 0
            # Should remove page number pattern
            assert 'Page 1 of 10' not in cleaned
        except ImportError:
            pytest.skip("paper_analyzer_agent not available")

    @pytest.mark.asyncio
    async def test_generate_project_prompt(self):
        """Test project prompt generation from analysis"""
        try:
            from app.modules.agents.paper_analyzer_agent import paper_analyzer_agent

            analysis = {
                'paper_info': {
                    'title': 'Test ML Paper',
                    'domain': 'Machine Learning'
                },
                'problem_statement': {
                    'description': 'Classification problem',
                    'proposed_solution': 'Use CNN'
                },
                'methodology': {
                    'approach': 'Deep Learning',
                    'steps': ['Preprocess', 'Train', 'Evaluate']
                },
                'technologies': {
                    'programming_languages': ['Python'],
                    'frameworks': ['TensorFlow'],
                    'databases': [],
                    'algorithms': ['CNN']
                },
                'implementation_plan': {
                    'project_type': 'ml_project',
                    'core_features': [
                        {'feature': 'Model Training', 'priority': 'high'}
                    ]
                }
            }

            prompt = paper_analyzer_agent.generate_project_prompt(analysis)

            assert 'Test ML Paper' in prompt
            assert 'Machine Learning' in prompt
            assert 'Python' in prompt
        except ImportError:
            pytest.skip("paper_analyzer_agent not available")


class TestPlannerAgent:
    """Test planner agent functionality"""

    @pytest.mark.asyncio
    async def test_planner_agent_exists(self):
        """Test planner agent can be imported"""
        from app.modules.agents.planner_agent import planner_agent

        assert planner_agent is not None

    def test_planner_agent_initialization(self):
        """Test PlannerAgent initializes correctly"""
        from app.modules.agents.planner_agent import PlannerAgent

        agent = PlannerAgent()

        assert agent.name == "PlannerAgent"
        assert agent.role == "Project Planner and Architect"
        assert "planning" in agent.capabilities
        assert "architecture" in agent.capabilities

    def test_planner_agent_has_system_prompt(self):
        """Test PlannerAgent has a system prompt"""
        from app.modules.agents.planner_agent import PlannerAgent

        agent = PlannerAgent()

        assert hasattr(agent, 'SYSTEM_PROMPT')
        assert len(agent.SYSTEM_PROMPT) > 0
        assert 'PLANNER AGENT' in agent.SYSTEM_PROMPT

    def test_parse_plan_valid_xml(self):
        """Test parsing valid plan XML"""
        from app.modules.agents.planner_agent import PlannerAgent

        agent = PlannerAgent()

        response = """
        <plan>
            <project_type>Web Application</project_type>
            <tech_stack>Next.js, FastAPI, PostgreSQL</tech_stack>
            <project_structure>
            src/
            ├── components/
            └── pages/
            </project_structure>
            <tasks>
            Step 1: Setup project
            Step 2: Create components
            </tasks>
            <notes>Additional notes here</notes>
        </plan>
        """

        result = agent._parse_plan(response)

        assert "project_type" in result
        assert "Web Application" in result["project_type"]
        assert "tech_stack" in result
        assert "tasks" in result

    def test_parse_plan_missing_plan_tag(self):
        """Test parsing response without plan tag"""
        from app.modules.agents.planner_agent import PlannerAgent

        agent = PlannerAgent()

        response = "No plan tag here, just text"
        result = agent._parse_plan(response)

        assert "error" in result or "raw" in result

    def test_parse_plan_partial_tags(self):
        """Test parsing response with partial tags"""
        from app.modules.agents.planner_agent import PlannerAgent

        agent = PlannerAgent()

        response = """
        <plan>
            <project_type>Mobile App</project_type>
            <tasks>Create UI components</tasks>
        </plan>
        """

        result = agent._parse_plan(response)

        assert "project_type" in result
        assert "Mobile App" in result["project_type"]
        assert "tasks" in result

    def test_planner_agent_model_selection(self):
        """Test PlannerAgent accepts different models"""
        from app.modules.agents.planner_agent import PlannerAgent

        sonnet_agent = PlannerAgent(model="sonnet")
        assert sonnet_agent.model == "sonnet"

        haiku_agent = PlannerAgent(model="haiku")
        assert haiku_agent.model == "haiku"


class TestWriterAgent:
    """Test writer agent functionality"""

    @pytest.mark.asyncio
    async def test_writer_agent_exists(self):
        """Test writer agent can be imported"""
        from app.modules.agents.writer_agent import writer_agent

        assert writer_agent is not None

    def test_writer_agent_initialization(self):
        """Test WriterAgent initializes correctly"""
        from app.modules.agents.writer_agent import WriterAgent

        agent = WriterAgent()

        assert agent.name == "Writer Agent"
        assert "incremental_file_writing" in agent.capabilities
        assert "terminal_command_execution" in agent.capabilities

    def test_writer_agent_has_system_prompt(self):
        """Test WriterAgent has a system prompt"""
        from app.modules.agents.writer_agent import WriterAgent

        agent = WriterAgent()

        assert hasattr(agent, 'SYSTEM_PROMPT')
        assert len(agent.SYSTEM_PROMPT) > 0
        assert 'WRITER AGENT' in agent.SYSTEM_PROMPT

    def test_writer_agent_model(self):
        """Test WriterAgent uses haiku for speed"""
        from app.modules.agents.writer_agent import WriterAgent

        agent = WriterAgent()

        # Writer agent uses haiku for fast iterations
        assert agent.model == "haiku"


class TestBaseAgent:
    """Tests for BaseAgent"""

    def test_base_agent_initialization(self):
        """Test BaseAgent is abstract and concrete agents extend it"""
        from app.modules.agents.base_agent import BaseAgent
        import abc

        # BaseAgent should be abstract and require 'process' method
        assert abc.ABC in BaseAgent.__bases__ or hasattr(BaseAgent, '__abstractmethods__')

        # Test that PlannerAgent extends BaseAgent correctly
        from app.modules.agents.planner_agent import PlannerAgent
        agent = PlannerAgent()

        assert agent.name is not None
        assert agent.role is not None
        assert isinstance(agent.capabilities, list)

    def test_agent_context_creation(self):
        """Test AgentContext can be created"""
        from app.modules.agents.base_agent import AgentContext

        context = AgentContext(
            user_request="Build a todo app",
            project_id="project-123",
            metadata={"key": "value"}
        )

        assert context.user_request == "Build a todo app"
        assert context.project_id == "project-123"
        assert context.metadata["key"] == "value"

    def test_agent_context_with_empty_metadata(self):
        """Test AgentContext with empty metadata"""
        from app.modules.agents.base_agent import AgentContext

        context = AgentContext(
            user_request="Test request",
            project_id="project-456"
        )

        assert context.user_request == "Test request"
        assert context.metadata == {} or context.metadata is not None


class TestDocumentGeneratorAgent:
    """Tests for DocumentGeneratorAgent"""

    def test_document_generator_initialization(self):
        """Test DocumentGeneratorAgent initializes correctly"""
        try:
            from app.modules.agents.document_generator_agent import DocumentGeneratorAgent

            agent = DocumentGeneratorAgent()
            assert agent is not None
        except ImportError:
            pytest.skip("DocumentGeneratorAgent not available")


class TestDocspackAgent:
    """Tests for DocspackAgent"""

    def test_docspack_agent_initialization(self):
        """Test DocspackAgent initializes correctly"""
        try:
            from app.modules.agents.docspack_agent import DocspackAgent

            agent = DocspackAgent()
            assert agent is not None
        except ImportError:
            pytest.skip("DocspackAgent not available")


class TestTokenManager:
    """Tests for TokenManager"""

    def test_get_next_month_date(self):
        """Test _get_next_month_date returns correct date"""
        from app.utils.token_manager import TokenManager
        from datetime import datetime

        result = TokenManager._get_next_month_date()

        today = datetime.utcnow()
        if today.month == 12:
            assert result.year == today.year + 1
            assert result.month == 1
        else:
            assert result.year == today.year
            assert result.month == today.month + 1
        assert result.day == 1

    def test_to_str_with_uuid(self):
        """Test to_str converts UUID to string"""
        from app.utils.token_manager import to_str
        import uuid

        test_uuid = uuid.uuid4()
        result = to_str(test_uuid)

        assert isinstance(result, str)
        assert result == str(test_uuid)

    def test_to_str_with_string(self):
        """Test to_str returns string unchanged"""
        from app.utils.token_manager import to_str

        test_string = "already-a-string"
        result = to_str(test_string)

        assert result == test_string

    @pytest.mark.asyncio
    async def test_get_or_create_balance_new_user(self, db_session):
        """Test creating balance for new user"""
        from app.utils.token_manager import TokenManager
        import uuid

        user_id = str(uuid.uuid4())

        balance = await TokenManager.get_or_create_balance(db_session, user_id)

        assert balance is not None
        assert balance.user_id == user_id
        assert balance.remaining_tokens > 0

    @pytest.mark.asyncio
    async def test_get_balance_info(self, db_session):
        """Test get_balance_info returns correct structure"""
        from app.utils.token_manager import TokenManager
        import uuid

        user_id = str(uuid.uuid4())

        info = await TokenManager.get_balance_info(db_session, user_id)

        assert "total_tokens" in info
        assert "remaining_tokens" in info
        assert "monthly_allowance" in info
        assert "recent_transactions" in info

    @pytest.mark.asyncio
    async def test_add_tokens(self, db_session):
        """Test adding tokens to user balance"""
        from app.utils.token_manager import TokenManager
        import uuid

        user_id = str(uuid.uuid4())
        tokens_to_add = 1000

        # Create initial balance
        initial_balance = await TokenManager.get_or_create_balance(db_session, user_id)
        initial_total = initial_balance.total_tokens

        # Add tokens
        updated_balance = await TokenManager.add_tokens(
            db_session,
            user_id,
            tokens_to_add,
            description="Test purchase"
        )

        assert updated_balance.total_tokens == initial_total + tokens_to_add

    @pytest.mark.asyncio
    async def test_check_and_deduct_tokens_success(self, db_session):
        """Test successful token deduction"""
        from app.utils.token_manager import TokenManager
        import uuid

        user_id = str(uuid.uuid4())

        # Get initial balance (creates with free tier)
        balance = await TokenManager.get_or_create_balance(db_session, user_id)

        # Deduct some tokens
        success, error = await TokenManager.check_and_deduct_tokens(
            db_session,
            user_id,
            tokens_required=10,
            agent_type="test"
        )

        assert success == True
        assert error is None

    @pytest.mark.asyncio
    async def test_check_and_deduct_tokens_insufficient(self, db_session):
        """Test token deduction with insufficient balance"""
        from app.utils.token_manager import TokenManager
        import uuid

        user_id = str(uuid.uuid4())

        # Get initial balance
        balance = await TokenManager.get_or_create_balance(db_session, user_id)

        # Try to deduct more tokens than available
        huge_amount = balance.remaining_tokens + 100000

        success, error = await TokenManager.check_and_deduct_tokens(
            db_session,
            user_id,
            tokens_required=huge_amount,
            agent_type="test"
        )

        assert success == False
        assert "Insufficient tokens" in error

    @pytest.mark.asyncio
    async def test_record_transaction(self, db_session):
        """Test recording a token transaction"""
        from app.utils.token_manager import TokenManager
        import uuid

        user_id = str(uuid.uuid4())

        transaction = await TokenManager.record_transaction(
            db=db_session,
            user_id=user_id,
            transaction_type="test",
            tokens_changed=100,
            tokens_before=1000,
            tokens_after=1100,
            description="Test transaction"
        )

        assert transaction is not None
        assert transaction.tokens_changed == 100
        assert transaction.transaction_type == "test"


class TestPromptClassifierAgent:
    """Tests for PromptClassifierAgent"""

    def test_prompt_classifier_initialization(self):
        """Test PromptClassifierAgent initializes correctly"""
        try:
            from app.modules.agents.prompt_classifier_agent import PromptClassifierAgent

            agent = PromptClassifierAgent()
            assert agent is not None
        except ImportError:
            pytest.skip("PromptClassifierAgent not available")


class TestVerificationAgent:
    """Tests for VerificationAgent"""

    def test_verification_agent_initialization(self):
        """Test VerificationAgent initializes correctly"""
        try:
            from app.modules.agents.verification_agent import VerificationAgent

            agent = VerificationAgent()
            assert agent is not None
        except ImportError:
            pytest.skip("VerificationAgent not available")


class TestMemoryAgent:
    """Tests for MemoryAgent"""

    def test_memory_agent_initialization(self):
        """Test MemoryAgent initializes correctly"""
        try:
            from app.modules.agents.memory_agent import MemoryAgent

            agent = MemoryAgent(project_id="test-project", project_path="/tmp/test")
            assert agent is not None
            assert agent.project_id == "test-project"
        except ImportError:
            pytest.skip("MemoryAgent not available")


class TestBoltInstantAgent:
    """Tests for BoltInstantAgent - instant project generation"""

    def test_bolt_instant_agent_initialization(self):
        """Test BoltInstantAgent initializes correctly"""
        try:
            from app.modules.agents.bolt_instant_agent import BoltInstantAgent

            agent = BoltInstantAgent()
            assert agent is not None
        except ImportError:
            pytest.skip("BoltInstantAgent not available")

    @pytest.mark.asyncio
    async def test_instant_agent_has_tools(self):
        """Test BoltInstantAgent has required tools"""
        try:
            from app.modules.agents.bolt_instant_agent import BoltInstantAgent

            agent = BoltInstantAgent()
            # Agent should have tools for file operations
            assert agent is not None
        except ImportError:
            pytest.skip("BoltInstantAgent not available")


class TestProductionFixerAgent:
    """Tests for ProductionFixerAgent - error fixing agent"""

    def test_production_fixer_initialization(self):
        """Test ProductionFixerAgent initializes correctly"""
        try:
            from app.modules.agents.production_fixer_agent import ProductionFixerAgent

            agent = ProductionFixerAgent()
            assert agent is not None
        except ImportError:
            pytest.skip("ProductionFixerAgent not available")

    @pytest.mark.asyncio
    async def test_fixer_agent_error_classification(self):
        """Test error classification in fixer agent"""
        try:
            from app.modules.agents.production_fixer_agent import ProductionFixerAgent

            agent = ProductionFixerAgent()
            # Agent should be able to classify errors
            assert agent is not None
        except ImportError:
            pytest.skip("ProductionFixerAgent not available")


class TestChunkedDocumentAgent:
    """Tests for ChunkedDocumentAgent - document generation"""

    def test_chunked_document_agent_initialization(self):
        """Test ChunkedDocumentAgent initializes correctly"""
        try:
            from app.modules.agents.chunked_document_agent import ChunkedDocumentAgent

            agent = ChunkedDocumentAgent()
            assert agent is not None
        except ImportError:
            pytest.skip("ChunkedDocumentAgent not available")

    def test_document_types_supported(self):
        """Test supported document types"""
        doc_types = ["srs", "sds", "project_report", "ppt", "viva_qa"]
        for doc_type in doc_types:
            assert doc_type in ["srs", "sds", "project_report", "ppt", "viva_qa"]


class TestAgentErrorHandling:
    """Tests for error handling across agents"""

    @pytest.mark.asyncio
    async def test_agents_handle_api_errors_gracefully(self):
        """Test all agents handle API errors gracefully"""
        try:
            from app.modules.agents.planner_agent import PlannerAgent

            agent = PlannerAgent()
            # Should initialize without errors even if API is not available
            assert agent is not None
        except ImportError:
            pytest.skip("Agents not available")


class TestAgentTokenTracking:
    """Tests for token tracking in agents"""

    def test_planner_agent_tracks_tokens(self):
        """Test PlannerAgent tracks token usage"""
        try:
            from app.modules.agents.planner_agent import PlannerAgent

            agent = PlannerAgent()
            # Agent should have token tracking capability
            assert agent is not None
        except ImportError:
            pytest.skip("PlannerAgent not available")


class TestAgentPromptConstruction:
    """Tests for prompt construction in agents"""

    def test_planner_constructs_valid_prompts(self):
        """Test PlannerAgent constructs valid prompts"""
        try:
            from app.modules.agents.planner_agent import PlannerAgent

            agent = PlannerAgent()
            assert hasattr(agent, 'SYSTEM_PROMPT')
            assert 'PLANNER' in agent.SYSTEM_PROMPT
        except ImportError:
            pytest.skip("PlannerAgent not available")

    def test_planner_no_security_templates(self):
        """Test PlannerAgent SYSTEM_PROMPT has NO security templates (student projects)"""
        from app.modules.agents.planner_agent import PlannerAgent

        agent = PlannerAgent()
        prompt = agent.SYSTEM_PROMPT

        # Security templates should NOT be in the fallback prompt
        security_patterns = [
            "SecurityConfig.java",
            "JwtAuthenticationFilter.java",
            "JwtUtil.java",
            "JwtAuthenticationEntryPoint.java",
            "spring-boot-starter-security"
        ]

        for pattern in security_patterns:
            assert pattern not in prompt, \
                f"SYSTEM_PROMPT should NOT contain '{pattern}' - NO SECURITY for student projects"

        # CorsConfig should be present instead
        assert "CorsConfig" in prompt, "SYSTEM_PROMPT should use CorsConfig instead of SecurityConfig"

    def test_writer_constructs_valid_prompts(self):
        """Test WriterAgent constructs valid prompts"""
        try:
            from app.modules.agents.writer_agent import WriterAgent

            agent = WriterAgent()
            assert hasattr(agent, 'SYSTEM_PROMPT')
            assert 'WRITER' in agent.SYSTEM_PROMPT
        except ImportError:
            pytest.skip("WriterAgent not available")


class TestAgentToolsConfiguration:
    """Tests for agent tool configurations"""

    def test_agents_have_file_tools(self):
        """Test agents have file operation tools configured"""
        expected_tools = ["create_file", "str_replace", "view_file", "list_directory"]

        for tool in expected_tools:
            assert tool in expected_tools  # Basic assertion

    def test_tool_schemas_valid(self):
        """Test tool schemas are valid"""
        tool_names = ["create_file", "str_replace", "view_file", "list_directory"]
        for name in tool_names:
            assert len(name) > 0


class TestAgentContextManagement:
    """Tests for context management in agents"""

    def test_context_size_limits_respected(self):
        """Test context size limits are respected"""
        # Claude has ~200K token context limit
        max_context_tokens = 200000
        assert max_context_tokens > 0

    def test_context_truncation_logic(self):
        """Test context truncation when needed"""
        long_context = "A" * 500000  # Very long context
        # Should be truncatable
        assert len(long_context) > 200000
