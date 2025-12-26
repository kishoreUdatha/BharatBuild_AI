"""
Central Dynamic Orchestrator (Bolt.new-style)

A flexible, event-driven orchestrator that:
- Routes requests to appropriate agents dynamically
- Supports configurable prompts and models (not hardcoded)
- Implements plan → write → run → fix → docs workflow loop
- Handles file patching and diffs
- Streams events to frontend via SSE

Architecture:
- Agent Registry: Dynamic agent discovery and routing
- Workflow Engine: Configurable multi-step workflows
- Event System: Real-time SSE streaming
- State Management: Track execution context across steps
"""

from typing import Dict, Any, List, Optional, AsyncGenerator, Callable
from datetime import datetime
from enum import Enum
import asyncio
import json
import os
import re
import xml.etree.ElementTree as ET
from lxml import etree
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import deque

from app.core.logging_config import logger

# Sandbox public URL for preview (use sandbox EC2 public IP/domain in production)
SANDBOX_PUBLIC_URL = os.getenv("SANDBOX_PUBLIC_URL") or os.getenv("SANDBOX_PREVIEW_BASE_URL", "http://localhost")


def _get_preview_url(port: int) -> str:
    """Generate preview URL using sandbox public URL or localhost fallback"""
    if SANDBOX_PUBLIC_URL and SANDBOX_PUBLIC_URL != "http://localhost":
        base = SANDBOX_PUBLIC_URL.rstrip('/')
        if ':' in base.split('/')[-1]:
            base = ':'.join(base.rsplit(':', 1)[:-1])
        return f"{base}:{port}"
    return f"http://localhost:{port}"


from app.utils.claude_client import ClaudeClient
from app.modules.automation.file_manager import FileManager
from app.modules.agents.base_agent import AgentContext
from app.services.checkpoint_service import checkpoint_service, CheckpointStatus
from app.services.unified_storage import UnifiedStorageService

# Import agent classes to use their embedded SYSTEM_PROMPT (Bolt.new style)
# Core Agents (like Bolt.new)
from app.modules.agents.planner_agent import PlannerAgent
from app.modules.agents.writer_agent import WriterAgent
from app.modules.agents.fixer_agent import FixerAgent
from app.modules.agents.runner_agent import RunnerAgent
from app.modules.agents.summarizer_agent import SummarizerAgent  # Internal helper (Bolt.new Agent 5)

# Additional Agents
from app.modules.agents.verification_agent import VerificationAgent
from app.modules.agents.document_generator_agent import DocumentGeneratorAgent
from app.modules.agents.bolt_instant_agent import BoltInstantAgent  # For beautiful UI-only projects


# ============================================================================
# XML SCHEMA DEFINITIONS (Bolt.new Style)
# ============================================================================

class PlanXMLSchema:
    """
    Strong XML schema validator for <plan> tags
    Matches bolt.new's strict schema enforcement

    NEW: Supports file-based plan format:
    <plan>
      <files>
        <file path="..." priority="N"><description>...</description></file>
      </files>
    </plan>
    """

    # Required tags - now supports 'files' as alternative to 'tasks'
    REQUIRED_TAGS = {'plan'}  # 'files' OR 'tasks' required

    # Optional tags - PRODUCTION FIX: Added 'project_structure' as valid fallback source for files
    OPTIONAL_TAGS = {'project_name', 'project_description', 'project_type', 'category', 'complexity', 'tech_stack', 'notes', 'features', 'estimated_files', 'project_structure'}

    # All allowed tags
    ALLOWED_TAGS = REQUIRED_TAGS | OPTIONAL_TAGS | {'files', 'file', 'description', 'tasks', 'step', 'frontend', 'backend', 'database', 'feature', 'category'}

    @staticmethod
    def validate(xml_string: str) -> Dict[str, Any]:
        """
        Validate XML against plan schema

        Returns:
            Dict with validation result and errors
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': []
        }

        try:
            # Parse XML
            root = ET.fromstring(xml_string)

            # Check root tag
            if root.tag != 'plan':
                result['errors'].append(f"Root tag must be <plan>, got <{root.tag}>")
                return result

            # PRODUCTION FIX: Check for required tags - must have <files>, <tasks>, or <project_structure>
            files_elem = root.find('files')
            tasks_elem = root.find('tasks')
            structure_elem = root.find('project_structure')

            if files_elem is None and tasks_elem is None and structure_elem is None:
                result['errors'].append("Missing required tag: <files>, <tasks>, or <project_structure>")

            # Check for disallowed tags
            for elem in root.iter():
                if elem.tag not in PlanXMLSchema.ALLOWED_TAGS:
                    result['warnings'].append(f"Unknown tag: <{elem.tag}>")

            # Validate <files> structure (NEW file-based format)
            if files_elem is not None:
                file_elems = files_elem.findall('file')
                if len(file_elems) == 0:
                    result['errors'].append("<files> must contain at least one <file>")

                # Validate each file has path attribute
                for i, file_elem in enumerate(file_elems):
                    if 'path' not in file_elem.attrib:
                        result['errors'].append(f"File {i+1} missing 'path' attribute")
                    # Description is optional but recommended
                    desc_elem = file_elem.find('description')
                    if desc_elem is None or not desc_elem.text or not desc_elem.text.strip():
                        result['warnings'].append(f"File {i+1} missing description")

            # Validate <tasks> structure (legacy format)
            elif tasks_elem is not None:
                steps = tasks_elem.findall('step')
                if len(steps) == 0:
                    result['errors'].append("<tasks> must contain at least one <step>")

                for i, step in enumerate(steps):
                    if 'id' not in step.attrib:
                        result['warnings'].append(f"Step {i+1} missing 'id' attribute")
                    if not step.text or not step.text.strip():
                        result['errors'].append(f"Step {i+1} has empty content")

            # If no errors, mark as valid
            if len(result['errors']) == 0:
                result['valid'] = True

        except ET.ParseError as e:
            result['errors'].append(f"XML Parse Error: {str(e)}")
        except Exception as e:
            result['errors'].append(f"Validation Error: {str(e)}")

        return result

    @staticmethod
    def _extract_files_from_structure(structure_text: str) -> List[Dict[str, Any]]:
        """
        PRODUCTION FIX: Extract file paths from ASCII tree <project_structure>

        This parses structures like:
        frontend/
        ├── src/
        │   ├── pages/
        │   │   ├── LoginPage.tsx
        │   │   └── Dashboard.tsx
        │   ├── App.tsx
        │   └── main.tsx
        └── package.json

        Returns:
            List of file dicts with full paths reconstructed from tree
        """
        import re
        files = []

        # Track directory stack for full path reconstruction
        dir_stack = []

        # File extension patterns
        file_extensions = r'\.(tsx?|jsx?|py|java|html|css|scss|json|yaml|yml|md|txt|sql|sh|bat|xml|gradle|properties|toml|lock|config\.js|config\.ts|Dockerfile|gitignore|env)$'

        for line in structure_text.split('\n'):
            if not line.strip():
                continue

            # Calculate indent level by counting leading spaces/tree chars
            # Remove tree characters: │ ├ └ ─ and spaces
            indent_chars = ""
            clean_name = line
            for i, char in enumerate(line):
                if char in '│├└─ \t':
                    indent_chars += char
                else:
                    clean_name = line[i:].strip()
                    break

            # Approximate indent level (4 chars = 1 level typically)
            indent_level = len(indent_chars) // 4

            # Skip empty or comment lines
            if not clean_name or clean_name.startswith('#') or clean_name.startswith('//'):
                continue

            # Check if directory (ends with /)
            is_directory = clean_name.endswith('/')

            if is_directory:
                dir_name = clean_name.rstrip('/')
                # Adjust stack to current level
                while len(dir_stack) > indent_level:
                    dir_stack.pop()
                dir_stack.append(dir_name)
            elif re.search(file_extensions, clean_name, re.IGNORECASE):
                # This is a file - reconstruct full path
                while len(dir_stack) > indent_level:
                    dir_stack.pop()

                if dir_stack:
                    full_path = '/'.join(dir_stack) + '/' + clean_name
                else:
                    full_path = clean_name

                # Clean up path (remove any double slashes)
                full_path = re.sub(r'/+', '/', full_path)

                files.append({
                    'path': full_path,
                    'description': f"Generated from project structure",
                    'priority': len(files) + 1,
                    'status': 'pending'
                })

        return files

    @staticmethod
    def parse_files_from_plan(xml_string: str) -> List[Dict[str, Any]]:
        """
        Parse <files> from plan XML - new file-based format

        PRODUCTION FIX: Falls back to <project_structure> if <files> is missing

        Returns:
            List of file dicts with path, description, priority
        """
        files = []

        try:
            root = ET.fromstring(xml_string)
            files_elem = root.find('files')

            if files_elem is not None:
                for file_elem in files_elem.findall('file'):
                    path = file_elem.get('path', '')
                    priority = int(file_elem.get('priority', '99'))

                    # Get description from nested <description> tag
                    desc_elem = file_elem.find('description')
                    description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ''

                    if path:
                        files.append({
                            'path': path.strip(),
                            'description': description,
                            'priority': priority,
                            'status': 'pending'
                        })

                # Sort by priority
                files.sort(key=lambda x: x['priority'])
                logger.info(f"[PlanXMLSchema] Parsed {len(files)} files from <files> section")

            # PRODUCTION FIX: Fallback to <project_structure> if no <files>
            if not files:
                structure_elem = root.find('project_structure')
                if structure_elem is not None and structure_elem.text:
                    structure_text = structure_elem.text.strip()
                    files = PlanXMLSchema._extract_files_from_structure(structure_text)
                    if files:
                        logger.info(f"[PlanXMLSchema] [FALLBACK] Extracted {len(files)} files from <project_structure>")
                    else:
                        logger.warning("[PlanXMLSchema] No files found in <project_structure>")

        except ET.ParseError as e:
            logger.error(f"[PlanXMLSchema] Failed to parse files: {e}")
        except Exception as e:
            logger.error(f"[PlanXMLSchema] Unexpected error parsing files: {e}")

        return files


class FileSchema:
    """
    Bolt.new-style STRICT FILE SCHEMA

    Every file MUST match:
    <file path="string">content</file>

    Schema:
    {
      file: {
        path: "string|required",
        content: "string|required"
      }
    }
    """

    @staticmethod
    def validate(file_elem: etree._Element) -> Dict[str, Any]:
        """
        Validate file element against strict schema

        Returns:
            Dict with validation result
        """
        result = {
            'valid': False,
            'errors': [],
            'warnings': []
        }

        try:
            # Check required: path attribute
            path = file_elem.get('path')
            if not path or not path.strip():
                result['errors'].append("Missing or empty 'path' attribute")
                return result

            # Check required: content (text)
            content = file_elem.text
            if content is None:
                result['errors'].append("Missing file content")
                return result

            # Valid
            result['valid'] = True

        except Exception as e:
            result['errors'].append(f"Validation error: {str(e)}")

        return result


class BoltStreamingBuffer:
    """
    Bolt.new EXACT streaming buffer implementation

    This is the EXACT technique Bolt.new uses:

    buffer += chunk
    while "</file>" in buffer:
        extract XML block
        parse with lxml
        validate schema
        save file
        remove from buffer
    """

    def __init__(self, tag: str = 'file'):
        """Initialize streaming buffer"""
        self.tag = tag
        self.buffer = ""

    def feed_chunk(self, chunk: str) -> List[Dict[str, Any]]:
        """
        Feed chunk and extract complete files (EXACT Bolt.new technique)

        Args:
            chunk: Streaming chunk from Claude

        Returns:
            List of extracted files (as soon as complete)
        """
        self.buffer += chunk
        files = []

        # Extract all complete tags (Bolt.new exact logic)
        while f"</{self.tag}>" in self.buffer:
            try:
                # Find tag boundaries
                start = self.buffer.index(f"<{self.tag} ")
                end = self.buffer.index(f"</{self.tag}>") + len(f"</{self.tag}>")
                xml_block = self.buffer[start:end]

                # Parse with regex to extract file content
                # HTMLParser was incorrectly parsing HTML content inside <file> tags
                # Instead, use simple string extraction which preserves inner content

                # Find path attribute using regex
                path_match = re.search(r'<file\s+path="([^"]+)"[^>]*>', xml_block)
                if not path_match:
                    logger.error("[Bolt Buffer] [FAIL] Could not find path attribute")
                    self.buffer = self.buffer[end:]
                    continue

                path = path_match.group(1)

                # Extract content: everything between the end of opening tag and start of closing tag
                # The opening tag ends at path_match.end()
                content_start = path_match.end()
                content_end = xml_block.rfind(f'</{self.tag}>')

                # Debug logging
                logger.debug(f"[Bolt Buffer] xml_block length: {len(xml_block)}")
                logger.debug(f"[Bolt Buffer] content_start: {content_start}, content_end: {content_end}")
                logger.debug(f"[Bolt Buffer] xml_block[:100]: {xml_block[:100]}")
                logger.debug(f"[Bolt Buffer] xml_block[-100:]: {xml_block[-100:]}")

                if content_end > content_start:
                    content = xml_block[content_start:content_end]
                    logger.debug(f"[Bolt Buffer] Extracted content length: {len(content)}")
                    logger.debug(f"[Bolt Buffer] First 200 chars: {content[:200]}")
                else:
                    logger.warning(f"[Bolt Buffer] Could not extract content for {path}")
                    content = ""

                # STRICT SCHEMA validation
                if not path or not path.strip():
                    logger.error("[Schema] [FAIL] Missing 'path' attribute - file rejected")
                    self.buffer = self.buffer[end:]
                    continue

                files.append({
                    "path": path.strip(),
                    "content": content.strip('\n')
                })
                logger.info(f"[Bolt Buffer] [OK] Extracted: {path}")

                # Remove processed block from buffer
                self.buffer = self.buffer[end:]

            except ValueError:
                # No more complete tags
                break
            except Exception as e:
                logger.error(f"[Bolt Buffer] Unexpected error: {e}")
                # Skip this block
                try:
                    end = self.buffer.index(f"</{self.tag}>") + len(f"</{self.tag}>")
                    self.buffer = self.buffer[end:]
                except ValueError:
                    break

        return files

    def has_partial_tag(self) -> bool:
        """Check if buffer has partial tag"""
        return f"<{self.tag}" in self.buffer and f"</{self.tag}>" not in self.buffer

    def get_buffer(self) -> str:
        """Get buffer content"""
        return self.buffer


class BoltXMLParser:
    """
    Bolt.new-style XML parser using lxml incremental parser

    Uses lxml.etree.iterparse for true streaming XML parsing.
    Handles: nested tags, multi-line content, large files, partial chunks.

    Architecture (matches Bolt.new):
    Token Stream → lxml iterparse → Element Events → DOM Tree → Extraction
    """

    def __init__(self, target_tag: str = 'plan'):
        """
        Initialize incremental XML parser

        Args:
            target_tag: Root tag to parse (e.g., 'plan', 'file')
        """
        self.target_tag = target_tag
        self.buffer = []
        self.complete_elements = {}
        self.parser = None
        self._accumulated_text = ""

    def feed(self, chunk: str):
        """
        Feed chunk to incremental parser (Bolt.new style)

        Args:
            chunk: Text chunk from stream
        """
        self.buffer.append(chunk)
        self._accumulated_text += chunk

        # Try to parse accumulated text incrementally
        self._parse_incremental()

    def _parse_incremental(self):
        """
        Incremental parsing using lxml

        Uses lxml.etree.iterparse which handles:
        - Nested tags
        - Multi-line content
        - Large files
        - Partial chunks (gracefully handles incomplete XML)
        """
        try:
            # Wrap text for incremental parsing
            text = self._accumulated_text

            # Check if we have complete target tag
            if f'<{self.target_tag}' in text and f'</{self.target_tag}>' in text:
                # Extract complete tag
                start = text.find(f'<{self.target_tag}')
                end = text.find(f'</{self.target_tag}>') + len(f'</{self.target_tag}>')

                if start >= 0 and end > start:
                    xml_content = text[start:end]

                    # Parse using lxml (handles all edge cases)
                    try:
                        from io import BytesIO
                        parser = etree.XMLParser(recover=True, remove_blank_text=False)
                        tree = etree.parse(BytesIO(xml_content.encode('utf-8')), parser)
                        root = tree.getroot()

                        self.complete_elements[self.target_tag] = root
                        logger.info(f"[Bolt XML Parser] [OK] Parsed <{self.target_tag}> using lxml")

                    except etree.XMLSyntaxError as e:
                        logger.warning(f"[Bolt XML Parser] XML syntax error: {e}")

        except Exception as e:
            logger.debug(f"[Bolt XML Parser] Incremental parse not ready: {e}")

    def has_complete_tag(self, tag_name: str) -> bool:
        """Check if tag has been fully parsed"""
        return tag_name in self.complete_elements

    def get_element(self, tag_name: str) -> Optional[etree._Element]:
        """
        Get parsed lxml Element

        Returns:
            lxml.etree._Element (not xml.etree.ElementTree.Element)
        """
        return self.complete_elements.get(tag_name)

    def get_text(self) -> str:
        """Get accumulated buffer text"""
        return self._accumulated_text

    @staticmethod
    def parse_files_from_xml(xml_string: str, ignore_attributes: bool = False) -> List[Dict[str, str]]:
        """
        Parse <file> tags from XML (Bolt.new style)

        Similar to Bolt's file parser:
        ```javascript
        function parseFile(xmlChunk) {
          const ast = parser.parse(xmlChunk);
          return ast.file.map(f => ({
            path: f.path,
            content: f["#text"]
          }));
        }
        ```

        Handles:
        - Nested <file> tags
        - Multi-line content
        - Large files
        - Partial chunks

        Args:
            xml_string: XML string containing <file> tags
            ignore_attributes: Whether to ignore attributes (default: False)

        Returns:
            List of {path, content} dicts
        """
        files = []

        try:
            # Parse XML using lxml
            parser = etree.XMLParser(recover=True, remove_blank_text=False)

            # Wrap in root if multiple <file> tags
            if xml_string.count('<file') > 1:
                xml_string = f'<files>{xml_string}</files>'

            root = etree.fromstring(xml_string.encode('utf-8'), parser)

            # Find all <file> elements
            file_elements = root.findall('.//file') if root.tag == 'files' else [root]

            for file_elem in file_elements:
                # Extract path attribute
                path = file_elem.get('path', '')

                # Extract content (handle both text and tail)
                content = file_elem.text or ''

                if path:
                    files.append({
                        'path': path.strip(),
                        'content': content
                    })
                    logger.debug(f"[Bolt File Parser] Extracted file: {path}")

            logger.info(f"[Bolt File Parser] [OK] Parsed {len(files)} files using lxml")

        except etree.XMLSyntaxError as e:
            logger.error(f"[Bolt File Parser] XML syntax error: {e}")

        return files


class TokenBuffer:
    """
    Simple token accumulator (used alongside StreamingXMLParser)

    Flow: Claude Stream → Token Buffer → Streaming XML Parser → DOM Builder
    """

    def __init__(self, max_buffer_size: int = 50000):
        self.buffer = []
        self.max_buffer_size = max_buffer_size
        self.total_tokens = 0

    def append(self, token: str):
        """Add token to buffer"""
        self.buffer.append(token)
        self.total_tokens += 1

        # Prevent memory issues
        if len(self.get_text()) > self.max_buffer_size:
            logger.warning(f"[TokenBuffer] Buffer exceeded {self.max_buffer_size} chars")

    def get_text(self) -> str:
        """Get accumulated text from buffer"""
        return "".join(self.buffer)

    def clear(self):
        """Clear buffer"""
        self.buffer.clear()
        self.total_tokens = 0

    def has_complete_xml(self, tag: str = 'plan') -> bool:
        """Check if buffer contains complete XML tag"""
        text = self.get_text()
        return f'<{tag}>' in text and f'</{tag}>' in text

    def extract_xml(self, tag: str = 'plan') -> Optional[str]:
        """Extract complete XML from buffer"""
        text = self.get_text()
        if not self.has_complete_xml(tag):
            return None

        start_tag = f'<{tag}>'
        end_tag = f'</{tag}>'

        start = text.find(start_tag)
        end = text.find(end_tag) + len(end_tag)

        if start >= 0 and end > start:
            return text[start:end]

        return None


class AgentType(str, Enum):
    """Available agent types"""
    PLANNER = "planner"
    WRITER = "writer"
    VERIFIER = "verifier"  # NEW: Verification agent
    FIXER = "fixer"
    RUNNER = "runner"
    TESTER = "tester"
    DOCUMENTER = "documenter"
    ENHANCER = "enhancer"
    ANALYZER = "analyzer"
    BOLT_INSTANT = "bolt_instant"  # FAST: Single-call generator like Bolt.new
    MEMORY = "memory"  # NEW: Memory Agent for context/file awareness (like Claude Code)


class EventType(str, Enum):
    """SSE Event types for frontend"""
    STATUS = "status"
    THINKING_STEP = "thinking_step"
    PLAN_CREATED = "plan_created"
    FILE_OPERATION = "file_operation"
    FILE_CONTENT = "file_content"
    COMMAND_EXECUTE = "command_execute"
    COMMAND_OUTPUT = "command_output"
    ERROR = "error"
    WARNING = "warning"
    COMPLETE = "complete"
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"
    VERIFICATION_RESULT = "verification_result"  # NEW: Verification results


@dataclass
class OrchestratorEvent:
    """Event emitted by orchestrator"""
    type: EventType
    data: Dict[str, Any]
    timestamp: str = None
    agent: Optional[str] = None
    step: Optional[int] = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class AgentConfig:
    """Configuration for an agent"""
    name: str
    agent_type: AgentType
    system_prompt: Optional[str] = None
    model: str = "sonnet"  # haiku, sonnet, opus
    temperature: float = 0.7
    max_tokens: int = 4096
    capabilities: List[str] = None
    enabled: bool = True

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []


@dataclass
class WorkflowStep:
    """A step in the workflow"""
    agent_type: AgentType
    name: str
    description: str = ""
    condition: Optional[Callable] = None  # Optional condition to execute this step
    retry_count: int = 3
    timeout: int = 120  # seconds
    stream_output: bool = False  # Whether to stream output in real-time
    hidden: bool = False  # If True, step runs but doesn't show in UI progress


# Per-file generation timeout (prevents indefinite hangs on complex files)
# Complex files like cart.tsx, dashboard.tsx can take longer, but should never hang forever
SINGLE_FILE_GENERATION_TIMEOUT = 120  # seconds (2 minutes per file max)
SINGLE_FILE_RETRY_COUNT = 2  # Number of retries before marking as failed


@dataclass
class ExecutionContext:
    """Shared context across workflow execution"""
    project_id: str
    user_request: str
    user_id: Optional[str] = None  # User ID for file operations (user_id/project_id path structure)
    current_step: int = 0
    total_steps: int = 0
    files_created: List[Dict[str, Any]] = None
    files_modified: List[Dict[str, Any]] = None
    commands_executed: List[Dict[str, Any]] = None
    errors: List[Dict[str, Any]] = None
    plan: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    project_type: Optional[str] = None  # Commercial, Academic, Research, Prototype, etc.
    tech_stack: Optional[Dict[str, Any]] = None  # Detected tech stack from Planner
    workflow_steps: List[Dict[str, Any]] = None  # Workflow steps for frontend UI display
    project_name: Optional[str] = None  # Human-readable project name from Planner
    project_description: Optional[str] = None  # Project description from Planner
    features: Optional[List[str]] = None  # Project features from Planner

    # Token usage tracking
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    token_usage_by_model: Dict[str, Dict[str, int]] = None  # {"haiku": {"input": 0, "output": 0}}
    token_usage_by_agent: Dict[str, Dict[str, int]] = None  # {"planner": {"input": 0, "output": 0}}
    pending_token_transactions: List[Dict[str, Any]] = None  # Transactions to save at end

    def __post_init__(self):
        if self.files_created is None:
            self.files_created = []
        if self.files_modified is None:
            self.files_modified = []
        if self.commands_executed is None:
            self.commands_executed = []
        if self.errors is None:
            self.errors = []
        if self.metadata is None:
            self.metadata = {}
        if self.workflow_steps is None:
            self.workflow_steps = []
        if self.token_usage_by_model is None:
            self.token_usage_by_model = {}
        if self.token_usage_by_agent is None:
            self.token_usage_by_agent = {}
        if self.pending_token_transactions is None:
            self.pending_token_transactions = []

    def track_tokens(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str,
        agent_type: str = "other",
        operation: str = "other",
        file_path: str = None
    ):
        """
        Track token usage from a Claude API call.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Model used (haiku, sonnet, opus)
            agent_type: Agent type (planner, writer, fixer, etc.)
            operation: Operation type (plan_project, generate_file, etc.)
            file_path: File path for file operations
        """
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

        # Track by model
        if model not in self.token_usage_by_model:
            self.token_usage_by_model[model] = {"input": 0, "output": 0}
        self.token_usage_by_model[model]["input"] += input_tokens
        self.token_usage_by_model[model]["output"] += output_tokens

        # Track by agent
        if agent_type not in self.token_usage_by_agent:
            self.token_usage_by_agent[agent_type] = {"input": 0, "output": 0}
        self.token_usage_by_agent[agent_type]["input"] += input_tokens
        self.token_usage_by_agent[agent_type]["output"] += output_tokens

        # Store transaction for saving later
        self.pending_token_transactions.append({
            "agent_type": agent_type,
            "operation": operation,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "file_path": file_path
        })

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens


class AgentRegistry:
    """
    Dynamic agent registry
    Agents can be registered, discovered, and configured at runtime
    Loads configurations from YAML files
    """

    def __init__(self, use_yaml: bool = True):
        """
        Initialize AgentRegistry

        Args:
            use_yaml: If True, load agents from YAML config. If False, use defaults.
        """
        self._agents: Dict[AgentType, AgentConfig] = {}
        self._use_yaml = use_yaml

        if use_yaml:
            self._load_from_yaml()
        else:
            self._load_default_agents()

    def _load_from_yaml(self):
        """Load agent configurations from YAML file"""
        try:
            from app.config.config_loader import get_config_loader

            config_loader = get_config_loader()
            self._agents = config_loader.load_agents()
            logger.info(f"Loaded {len(self._agents)} agents from YAML config")

        except Exception as e:
            logger.error(f"Failed to load agents from YAML: {e}")
            logger.warning("Falling back to default agent configurations")
            self._load_default_agents()

    def _load_default_agents(self):
        """Load default agent configurations (fallback)"""
        default_agents = [
            AgentConfig(
                name="Planner Agent",
                agent_type=AgentType.PLANNER,
                model="sonnet",
                temperature=0.7,
                max_tokens=4096,
                capabilities=["planning", "architecture_design", "task_breakdown"]
            ),
            AgentConfig(
                name="Writer Agent",
                agent_type=AgentType.WRITER,
                model="sonnet",
                temperature=0.3,
                max_tokens=8192,
                capabilities=["code_generation", "file_creation"]
            ),
            AgentConfig(
                name="Fixer Agent",
                agent_type=AgentType.FIXER,
                model="sonnet",
                temperature=0.5,
                max_tokens=4096,
                capabilities=["debugging", "error_fixing", "code_modification"]
            ),
            AgentConfig(
                name="Runner Agent",
                agent_type=AgentType.RUNNER,
                model="haiku",
                temperature=0.1,
                max_tokens=2048,
                capabilities=["command_execution", "testing"]
            ),
            AgentConfig(
                name="Tester Agent",
                agent_type=AgentType.TESTER,
                model="haiku",
                temperature=0.5,
                max_tokens=4096,
                capabilities=["test_generation", "quality_assurance"]
            ),
            AgentConfig(
                name="Documenter Agent",
                agent_type=AgentType.DOCUMENTER,
                model="haiku",
                temperature=0.5,
                max_tokens=4096,
                capabilities=["documentation", "readme_generation", "api_docs"]
            ),
            AgentConfig(
                name="Verification Agent",
                agent_type=AgentType.VERIFIER,
                model="haiku",
                temperature=0.3,
                max_tokens=2048,
                capabilities=["file_verification", "completeness_check", "syntax_validation"]
            ),
            # BOLT INSTANT - Fast single-call generator like Bolt.new
            AgentConfig(
                name="Bolt Instant Generator",
                agent_type=AgentType.BOLT_INSTANT,
                model="sonnet",
                temperature=0.5,
                max_tokens=32000,  # Very large for complete project generation
                capabilities=["instant_generation", "planning", "code_generation", "file_creation"]
            ),
            # MEMORY AGENT - Context and file awareness (like Claude Code)
            AgentConfig(
                name="Memory Agent",
                agent_type=AgentType.MEMORY,
                model="haiku",  # Fast model for context summarization
                temperature=0.3,
                max_tokens=2048,
                capabilities=["context_tracking", "file_awareness", "conversation_memory", "project_state"]
            ),
        ]

        for agent_config in default_agents:
            self._agents[agent_config.agent_type] = agent_config

    def register_agent(self, config: AgentConfig):
        """Register or update an agent configuration"""
        self._agents[config.agent_type] = config
        logger.info(f"Registered agent: {config.name} ({config.agent_type})")

    def get_agent(self, agent_type: AgentType) -> Optional[AgentConfig]:
        """Get agent configuration"""
        return self._agents.get(agent_type)

    def update_agent_prompt(self, agent_type: AgentType, system_prompt: str):
        """Dynamically update agent's system prompt"""
        if agent_type in self._agents:
            self._agents[agent_type].system_prompt = system_prompt
            logger.info(f"Updated prompt for {agent_type}")

    def update_agent_model(self, agent_type: AgentType, model: str):
        """Dynamically update agent's model"""
        if agent_type in self._agents:
            self._agents[agent_type].model = model
            logger.info(f"Updated model for {agent_type} to {model}")

    def list_agents(self) -> Dict[AgentType, AgentConfig]:
        """List all registered agents"""
        return self._agents


class WorkflowEngine:
    """
    Configurable workflow engine
    Supports different workflow patterns (not hardcoded)
    """

    def __init__(self):
        self._workflows: Dict[str, List[WorkflowStep]] = {}
        self._load_default_workflows()

    def _load_default_workflows(self):
        """Load default workflow patterns"""

        # Bolt.new standard workflow with run → fix → run loop
        # Simplified step names for students - shows only essential progress
        self._workflows["bolt_standard"] = [
            WorkflowStep(
                agent_type=AgentType.PLANNER,
                name="Planning Project",
                description="Analyzing your request and designing the project structure",
                timeout=120,
                retry_count=2
            ),
            WorkflowStep(
                agent_type=AgentType.WRITER,
                name="Writing Code",
                description="Creating all project files and code",
                timeout=300,
                retry_count=2,
                stream_output=True
            ),
            WorkflowStep(
                agent_type=AgentType.VERIFIER,
                name="Checking Files",
                description="Verifying all files are complete",
                timeout=120,
                retry_count=1,
                stream_output=False,
                hidden=True  # Hide from UI - internal step
            ),
            # Runner: Run npm install / npm run build to check for compilation errors
            # ALWAYS runs if files are created (fixed condition to check file paths properly)
            WorkflowStep(
                agent_type=AgentType.RUNNER,
                name="Building Project",
                description="Installing dependencies and building your project",
                timeout=180,
                retry_count=1,
                stream_output=True,
                # Run for any project with build files (improved condition with type safety)
                condition=lambda ctx: isinstance(ctx.files_created, list) and len(ctx.files_created) > 0 and any(
                    any(build_file in (f.get("path") or "" if isinstance(f, dict) else str(f)) for build_file in
                        ["package.json", "requirements.txt", "pom.xml", "build.gradle", "Cargo.toml", "go.mod"])
                    for f in ctx.files_created
                )
            ),
            # Fixer: Fix any errors found during build
            WorkflowStep(
                agent_type=AgentType.FIXER,
                name="Fixing Issues",
                description="Automatically fixing any errors found",
                timeout=300,
                retry_count=2,
                stream_output=True,
                condition=lambda ctx: isinstance(ctx.errors, list) and len(ctx.errors) > 0
            ),
            # Re-run after fixes to verify they work - Hidden from UI
            WorkflowStep(
                agent_type=AgentType.RUNNER,
                name="Verifying Build",
                description="Confirming all issues are resolved",
                timeout=180,
                retry_count=1,
                stream_output=True,
                hidden=True,  # Hide from UI - internal verification
                condition=lambda ctx: isinstance(ctx.files_modified, list) and len(ctx.files_modified) > 0 and any(f.get("operation") == "fix" for f in ctx.files_modified if isinstance(f, dict))
            ),
            # Documenter: Generate documentation (SRS, UML, Reports, etc.)
            # For students: Full docs (Project Report, SRS, PPT, Viva Q&A)
            WorkflowStep(
                agent_type=AgentType.DOCUMENTER,
                name="Creating Documents",
                description="Generating Project Report, SRS, Presentation, and Viva Q&A",
                timeout=300,
                retry_count=2,
                stream_output=True,
                # Run for ALL projects that have files created (safely handle bool/None)
                condition=lambda ctx: isinstance(ctx.files_created, list) and len(ctx.files_created) > 0
            ),
        ]

        # Quick iteration workflow (no docs)
        self._workflows["quick_iteration"] = [
            WorkflowStep(
                agent_type=AgentType.PLANNER,
                name="Quick Plan",
                description="Create simple plan"
            ),
            WorkflowStep(
                agent_type=AgentType.WRITER,
                name="Generate Code",
                description="Write code"
            ),
            WorkflowStep(
                agent_type=AgentType.RUNNER,
                name="Test",
                description="Quick test"
            ),
        ]

        # Debug workflow (fix existing code)
        self._workflows["debug"] = [
            WorkflowStep(
                agent_type=AgentType.ANALYZER,
                name="Analyze Error",
                description="Understand the error"
            ),
            WorkflowStep(
                agent_type=AgentType.FIXER,
                name="Fix Code",
                description="Apply fixes"
            ),
            WorkflowStep(
                agent_type=AgentType.RUNNER,
                name="Verify Fix",
                description="Test the fix"
            ),
        ]

        # ⚡ BOLT INSTANT workflow - Single API call like Bolt.new (FASTEST)
        # This is the key to showing only 3 steps to user instead of 18+ tasks
        self._workflows["bolt_instant"] = [
            WorkflowStep(
                agent_type=AgentType.BOLT_INSTANT,
                name="Generate Complete Project",
                description="Single-call instant generation (like Bolt.new)",
                timeout=180,
                retry_count=2,
                stream_output=True
            ),
            # DOCUMENTER: Generate academic docs for ALL users
            # This is a student-focused platform, so always generate docs
            WorkflowStep(
                agent_type=AgentType.DOCUMENTER,
                name="Creating Documents",
                description="Create Project Report, SRS, PPT, Viva Q&A",
                timeout=300,
                retry_count=2,
                stream_output=True,
                # Run for ALL projects that created files (safely handle bool/None)
                condition=lambda ctx: isinstance(ctx.files_created, list) and len(ctx.files_created) > 0
            ),
        ]

    def register_workflow(self, name: str, steps: List[WorkflowStep]):
        """Register custom workflow"""
        self._workflows[name] = steps
        logger.info(f"Registered workflow: {name} with {len(steps)} steps")

    def get_workflow(self, name: str) -> List[WorkflowStep]:
        """Get workflow by name"""
        return self._workflows.get(name, self._workflows["bolt_standard"])

    def list_workflows(self) -> List[str]:
        """List available workflows"""
        return list(self._workflows.keys())


class DynamicOrchestrator:
    """
    Central Dynamic Orchestrator

    Features:
    - Multi-agent routing based on registry
    - Dynamic prompts and models (configurable)
    - Flexible workflow patterns
    - File patching support
    - Real-time event streaming
    - State management across steps
    - Ephemeral temp storage (like Bolt.new) - auto-cleanup after download
    """

    def __init__(self, project_root: str = None, use_temp_storage: bool = False):
        # Use configured path from settings if not provided
        if project_root is None:
            from app.core.config import settings
            project_root = str(settings.USER_PROJECTS_DIR)
        self.agent_registry = AgentRegistry()
        self.workflow_engine = WorkflowEngine()
        self.claude_client = ClaudeClient()
        self.file_manager = FileManager(project_root)
        self._event_queue: asyncio.Queue = None

        # Ephemeral storage mode (like Bolt.new)
        self.use_temp_storage = use_temp_storage
        self._temp_storage = None
        if use_temp_storage:
            from app.services.temp_session_storage import temp_storage
            self._temp_storage = temp_storage

        # 3-Layer Unified Storage (sandbox + S3 + PostgreSQL)
        self._unified_storage = UnifiedStorageService()

    # ==================== Ephemeral Storage Methods ====================

    def create_session(self, user_id: str = None, project_name: str = None) -> str:
        """Create a temp session for project generation (returns session_id)"""
        if self._temp_storage:
            return self._temp_storage.create_session(user_id, project_name)
        return None

    async def write_file_to_session(self, session_id: str, file_path: str, content: str) -> bool:
        """Write file to temp session (ephemeral storage)"""
        if self._temp_storage and session_id:
            return await self._temp_storage.write_file_async(session_id, file_path, content)
        return False

    async def update_file_generation_status(
        self,
        project_id: str,
        file_path: str,
        status: str,
        s3_key: str = None,
        content_hash: str = None,
        size_bytes: int = 0,
        error_message: str = None,
        max_retries: int = 3
    ) -> bool:
        """
        Update the generation status of a file in the database with retry logic.

        Args:
            project_id: Project UUID
            file_path: File path
            status: Status string (PLANNED, GENERATING, COMPLETED, FAILED, SKIPPED)
            s3_key: S3 key if file was uploaded
            content_hash: Content hash if file was saved
            size_bytes: File size in bytes
            error_message: Error message if status is FAILED
            max_retries: Maximum retry attempts for transient failures

        Returns:
            True if status was updated successfully
        """
        import asyncio

        # Validate inputs
        if not project_id or not file_path:
            logger.error(f"[FileStatus] Invalid input: project_id={project_id}, file_path={file_path}")
            return False

        # Validate and normalize status
        valid_statuses = ['planned', 'generating', 'completed', 'failed', 'skipped']
        status_lower = status.lower() if status else 'failed'
        if status_lower not in valid_statuses:
            logger.warning(f"[FileStatus] Invalid status '{status}', defaulting to 'failed'")
            status_lower = 'failed'

        last_error = None

        for attempt in range(max_retries):
            try:
                from app.core.database import AsyncSessionLocal
                from app.models.project_file import ProjectFile, FileGenerationStatus
                from sqlalchemy import select
                from sqlalchemy.exc import IntegrityError, OperationalError

                # Map string to enum
                status_enum = FileGenerationStatus(status_lower)

                async with AsyncSessionLocal() as session:
                    try:
                        # Find the file record
                        result = await session.execute(
                            select(ProjectFile)
                            .where(ProjectFile.project_id == project_id)
                            .where(ProjectFile.path == file_path)
                        )
                        file_record = result.scalar_one_or_none()

                        if file_record:
                            # Update existing record
                            file_record.generation_status = status_enum
                            if s3_key:
                                file_record.s3_key = s3_key
                            if content_hash:
                                file_record.content_hash = content_hash
                            if size_bytes:
                                file_record.size_bytes = size_bytes

                            await session.commit()
                            logger.debug(f"[FileStatus] ✓ Updated {file_path} to {status}")
                            return True
                        else:
                            # Create new record if not found (edge case: file not in plan)
                            logger.info(f"[FileStatus] File record not found for {file_path}, creating new")
                            new_file = ProjectFile(
                                project_id=project_id,
                                path=file_path,
                                name=file_path.split('/')[-1] if '/' in file_path else file_path,
                                generation_status=status_enum,
                                s3_key=s3_key,
                                content_hash=content_hash,
                                size_bytes=size_bytes or 0,
                                is_folder=False
                            )
                            session.add(new_file)
                            await session.commit()
                            logger.debug(f"[FileStatus] ✓ Created and set {file_path} to {status}")
                            return True

                    except IntegrityError as ie:
                        await session.rollback()
                        logger.warning(f"[FileStatus] IntegrityError for {file_path}, may already exist: {ie}")
                        # Try to update existing on integrity error (race condition)
                        if attempt < max_retries - 1:
                            await asyncio.sleep(0.5)
                            continue
                        return False

                    except OperationalError as oe:
                        await session.rollback()
                        last_error = oe
                        if attempt < max_retries - 1:
                            delay = 0.5 * (2 ** attempt)
                            logger.warning(f"[FileStatus] DB operational error, retrying in {delay}s: {oe}")
                            await asyncio.sleep(delay)
                            continue
                        logger.error(f"[FileStatus] ✗ DB operational error after {max_retries} attempts: {oe}")
                        return False

            except ValueError as ve:
                logger.error(f"[FileStatus] Invalid status enum value '{status}': {ve}")
                return False

            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = 0.5 * (2 ** attempt)
                    logger.warning(f"[FileStatus] Attempt {attempt + 1}/{max_retries} failed for {file_path}: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"[FileStatus] ✗ Failed to update status for {file_path} after {max_retries} attempts: {e}")

        return False

    async def save_file(self, project_id: str, file_path: str, content: str, session_id: str = None, user_id: str = None) -> bool:
        """
        Save file - routes to all configured storage layers with retry logic.

        4-Layer Storage:
        - Layer 1: Sandbox (EC2: /tmp/sandbox/workspace/{user_id}/{project_id}/) - for runtime/preview
        - Layer 2: Permanent storage (USER_PROJECTS_PATH) or temp session
        - Layer 3: Database (PostgreSQL) + S3 - for project recovery after sandbox cleanup
        - Layer 4: Checkpoint tracking for resume capability

        Args:
            project_id: Project identifier (UUID string)
            file_path: Relative file path
            content: File content
            session_id: Temp session ID (for ephemeral mode)
            user_id: User identifier for user-scoped storage (like Bolt.new)

        Returns:
            True if saved successfully to all critical layers
        """
        import asyncio

        layer1_success = False
        layer2_success = False
        layer3_success = False

        # LAYER 1: Always write to sandbox for runtime/preview
        # Path: /workspace/{user_id}/{project_id}/ (like Bolt.new)
        # This is CRITICAL for immediate preview functionality
        max_retries = 3
        for attempt in range(max_retries):
            try:
                layer1_success = await self._unified_storage.write_to_sandbox(project_id, file_path, content, user_id)
                if layer1_success:
                    logger.info(f"[Layer1-Sandbox] ✓ Saved: {user_id or 'anon'}/{project_id}/{file_path}")
                    break
                else:
                    logger.warning(f"[Layer1-Sandbox] Attempt {attempt + 1}/{max_retries} returned False for {file_path}")
            except Exception as e:
                logger.warning(f"[Layer1-Sandbox] Attempt {attempt + 1}/{max_retries} failed for {file_path}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff

        if not layer1_success:
            logger.error(f"[Layer1-Sandbox] ✗ FAILED after {max_retries} attempts: {file_path}")

        # LAYER 2: Write to permanent storage or temp session
        try:
            if self.use_temp_storage and session_id and self._temp_storage:
                # Ephemeral mode - write to temp session
                layer2_success = await self._temp_storage.write_file_async(session_id, file_path, content)
            else:
                # Permanent mode - write to file_manager (USER_PROJECTS_PATH)
                result = await self.file_manager.create_file(project_id, file_path, content, user_id=user_id)
                layer2_success = result.get('success', False) if isinstance(result, dict) else True

            if layer2_success:
                logger.debug(f"[Layer2-Storage] ✓ Saved: {project_id}/{file_path}")
        except Exception as e:
            logger.warning(f"[Layer2-Storage] ✗ Failed to save {file_path}: {e}")

        # LAYER 3: Save to database + S3 for project recovery
        # This is CRITICAL for project switching and restoration
        # Retry with exponential backoff
        for attempt in range(max_retries):
            try:
                logger.info(f"[Layer3-DB+S3] Attempt {attempt + 1}/{max_retries}: project_id={project_id}, path={file_path}, size={len(content)} bytes")
                layer3_success = await self._unified_storage.save_to_database(project_id, file_path, content)

                if layer3_success:
                    logger.info(f"[Layer3-DB+S3] ✓ SUCCESS: {project_id}/{file_path}")
                    break
                else:
                    logger.warning(f"[Layer3-DB+S3] Attempt {attempt + 1}/{max_retries} returned False for {file_path}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1.0 * (attempt + 1))  # Longer backoff for DB/S3
            except Exception as db_err:
                logger.error(f"[Layer3-DB+S3] Attempt {attempt + 1}/{max_retries} exception for {file_path}: {db_err}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))

        if not layer3_success:
            logger.error(f"[Layer3-DB+S3] ✗ FAILED after {max_retries} attempts: {file_path} - PROJECT RESTORE WILL FAIL!")

        # LAYER 4: Track file in checkpoint for resume capability
        try:
            file_type = "config" if file_path.endswith(('.json', '.yml', '.yaml', '.env')) else \
                       "backend" if '/backend/' in file_path or file_path.endswith('.py') else \
                       "frontend" if '/frontend/' in file_path or file_path.endswith(('.tsx', '.jsx', '.ts', '.js')) else \
                       "other"
            await checkpoint_service.add_generated_file(
                project_id=project_id,
                file_path=file_path,
                file_type=file_type,
                size_bytes=len(content.encode('utf-8'))
            )
            logger.debug(f"[Layer4-Checkpoint] ✓ Tracked: {file_path}")
        except Exception as cp_err:
            logger.debug(f"[Layer4-Checkpoint] Failed to track file {file_path}: {cp_err}")

        # Log overall status
        overall_success = layer1_success and layer3_success  # Layer 1 & 3 are critical
        if overall_success:
            logger.info(f"[SaveFile] ✓ Complete: {file_path} (L1={layer1_success}, L2={layer2_success}, L3={layer3_success})")
        else:
            logger.error(f"[SaveFile] ✗ Incomplete: {file_path} (L1={layer1_success}, L2={layer2_success}, L3={layer3_success})")

        return overall_success

    def get_session_files(self, session_id: str) -> list:
        """Get list of files in a temp session"""
        if self._temp_storage:
            return self._temp_storage.list_files(session_id)
        return []

    def _detect_project_complexity(self, user_request: str) -> Dict[str, Any]:
        """
        Detect project complexity from user request to control file generation.
        Supports multiple technologies with appropriate file limits.

        Configuration loaded from:
        1. agent_config.yml (keywords, tech stacks)
        2. .env file (file limits - takes priority)

        Returns:
            Dict with complexity level, max_files, and tech recommendations
        """
        from app.core.config import settings

        # Load configuration
        config = settings.get_complexity_config()
        file_limits = config.get('file_limits', {})
        tech_limits = config.get('technology_limits', {})
        keywords = config.get('keywords', {})
        tech_keywords = config.get('technology_keywords', {})
        stacks = config.get('recommended_stacks', {})

        request_lower = user_request.lower()

        # ============== TECHNOLOGY DETECTION ==============
        # Mobile Apps (Flutter/React Native)
        mobile_kw = tech_keywords.get('mobile', ["flutter", "react native", "mobile app", "android app", "ios app"])
        is_mobile = any(kw in request_lower for kw in mobile_kw)

        # Java/Spring Boot
        java_kw = tech_keywords.get('java', ["spring boot", "java", "spring", "maven", "gradle"])
        is_java = any(kw in request_lower for kw in java_kw)

        # Django
        django_kw = tech_keywords.get('django', ["django", "python web"])
        is_django = any(kw in request_lower for kw in django_kw)

        # AI/ML
        ml_kw = tech_keywords.get('ai_ml', ["machine learning", "ml", "ai", "deep learning", "tensorflow", "pytorch"])
        is_ml = any(kw in request_lower for kw in ml_kw)

        # ============== COMPLEXITY KEYWORDS ==============
        minimal_keywords = keywords.get('minimal', ["landing page", "landing", "single page"])
        simple_keywords = keywords.get('simple', ["simple", "basic", "quick", "portfolio", "mvp"])
        complex_keywords = keywords.get('complex', [
            "full platform", "full stack", "with auth", "enterprise",
            "marketplace", "multi-vendor", "vendor platform", "seller platform",
            "admin dashboard", "user management", "payment", "checkout",
            "orders", "cart", "inventory", "multi-user", "saas",
            "e-commerce platform", "ecommerce platform", "online store platform",
            "multi-role", "authentication", "authorization"
        ])

        # ============== MOBILE APPS (Flutter/React Native) ==============
        if is_mobile:
            flutter_limits = tech_limits.get('flutter', {'simple': 20, 'complex': 40})
            rn_limits = tech_limits.get('react_native', {'simple': 20, 'complex': 40})

            if any(kw in request_lower for kw in simple_keywords):
                logger.info(f"[ComplexityDetection] Detected SIMPLE mobile app")
                max_files = flutter_limits.get('simple', 20) if "flutter" in request_lower else rn_limits.get('simple', 20)
                return {
                    "complexity": "simple",
                    "max_files": max_files,
                    "recommended_stack": stacks.get('flutter_simple', "Flutter + Dart") if "flutter" in request_lower else stacks.get('react_native_simple', "React Native + TypeScript"),
                    "include_frontend": True,  # Mobile apps are "frontend"
                    "include_backend": False,
                    "include_docker": False,
                    "hint": "Simple mobile app. Include screens, widgets, models."
                }
            else:
                logger.info(f"[ComplexityDetection] Detected FULL mobile app")
                max_files = flutter_limits.get('complex', 40) if "flutter" in request_lower else rn_limits.get('complex', 40)
                return {
                    "complexity": "complex",
                    "max_files": max_files,
                    "recommended_stack": stacks.get('flutter_complex', "Flutter + Dart + Provider/Bloc") if "flutter" in request_lower else stacks.get('react_native_complex', "React Native + TypeScript + Redux"),
                    "include_frontend": True,  # Mobile apps are "frontend"
                    "include_backend": "backend" in request_lower or "api" in request_lower,
                    "include_docker": False,
                    "hint": "Full mobile app. Include all screens, widgets, models, services, state management needed."
                }

        # ============== JAVA/SPRING BOOT ==============
        if is_java:
            spring_limits = tech_limits.get('spring_boot', {'simple': 20, 'complex': 50, 'fullstack': 60})

            # Check if user explicitly wants "backend only" (no frontend)
            # NOTE: "backend use spring boot" means "use spring boot FOR backend", not "only backend"
            backend_only_keywords = ["backend only", "api only", "rest api only", "no frontend", "only backend", "just backend", "backend api only"]
            is_backend_only = any(kw in request_lower for kw in backend_only_keywords)

            # Check if user wants fullstack (app, application, platform, ecommerce, etc.)
            fullstack_keywords = ["app", "application", "platform", "website", "fullstack", "full-stack", "full stack", "with frontend", "with react", "with angular", "with vue"]
            wants_fullstack = any(kw in request_lower for kw in fullstack_keywords) and not is_backend_only

            if any(kw in request_lower for kw in simple_keywords):
                logger.info(f"[ComplexityDetection] Detected SIMPLE Spring Boot project")
                max_files = spring_limits.get('simple', 20)
                return {
                    "complexity": "simple",
                    "max_files": max_files,
                    "recommended_stack": stacks.get('spring_boot_simple', "Spring Boot + Java + Maven + PostgreSQL"),
                    "include_backend": True,
                    "include_frontend": False,
                    "include_docker": False,
                    "hint": "Simple Spring Boot API. Include controllers, services, repositories, models."
                }
            elif wants_fullstack:
                # Fullstack: Spring Boot backend + React/Vue frontend
                logger.info(f"[ComplexityDetection] Detected FULLSTACK Spring Boot + React project")
                max_files = spring_limits.get('fullstack', 60)
                return {
                    "complexity": "complex",
                    "max_files": max_files,
                    "recommended_stack": stacks.get('spring_boot_fullstack', "Spring Boot + Java + Maven + PostgreSQL + React + Vite + TypeScript"),
                    "include_backend": True,
                    "include_frontend": True,
                    "include_docker": True,
                    "hint": "Full-stack application with Spring Boot backend and React frontend. Structure: backend/ folder with Spring Boot (controllers, services, repositories, models, DTOs, configs, security) AND frontend/ folder with React (components, pages, hooks, services, styles). Include docker-compose.yml for both services."
                }
            else:
                logger.info(f"[ComplexityDetection] Detected FULL Spring Boot backend-only project")
                max_files = spring_limits.get('complex', 50)
                return {
                    "complexity": "complex",
                    "max_files": max_files,
                    "recommended_stack": stacks.get('spring_boot_complex', "Spring Boot + Java + Maven + PostgreSQL + Spring Security"),
                    "include_backend": True,
                    "include_frontend": False,
                    "include_docker": True,
                    "hint": "Full Spring Boot backend application. Include controllers, services, repositories, models, DTOs, configs, security."
                }

        # ============== DJANGO ==============
        if is_django:
            django_limits = tech_limits.get('django', {'simple': 18, 'complex': 35})

            if any(kw in request_lower for kw in simple_keywords):
                logger.info(f"[ComplexityDetection] Detected SIMPLE Django project")
                max_files = django_limits.get('simple', 18)
                return {
                    "complexity": "simple",
                    "max_files": max_files,
                    "recommended_stack": stacks.get('django_simple', "Django + Python + PostgreSQL"),
                    "include_frontend": True,  # Django includes templates (frontend)
                    "include_backend": True,
                    "include_docker": False,
                    "hint": "Simple Django app. Include models, views, urls, templates."
                }
            else:
                logger.info(f"[ComplexityDetection] Detected FULL Django project")
                max_files = django_limits.get('complex', 35)
                return {
                    "complexity": "complex",
                    "max_files": max_files,
                    "recommended_stack": stacks.get('django_complex', "Django + DRF + PostgreSQL + Celery"),
                    "include_frontend": True,  # Django includes templates (frontend)
                    "include_backend": True,
                    "include_docker": True,
                    "hint": "Full Django application. Include models, views, serializers, urls, templates, admin, celery tasks."
                }

        # ============== AI/ML ==============
        if is_ml:
            ml_limits = tech_limits.get('ai_ml', {'default': 18})
            max_files = ml_limits.get('default', 18)
            logger.info(f"[ComplexityDetection] Detected AI/ML project")
            return {
                "complexity": "intermediate",
                "max_files": max_files,
                "recommended_stack": stacks.get('ai_ml', "Python + TensorFlow/PyTorch + Streamlit + Jupyter"),
                "include_frontend": True,  # Includes Streamlit/Gradio UI
                "include_backend": False,
                "include_docker": False,
                "hint": "AI/ML project. Include model, preprocessing, training, inference, notebooks, Streamlit/Gradio interface."
            }

        # ============== WEB APPS (React/Next.js/Vue) ==============
        # Check for MINIMAL first (highest priority)
        if any(kw in request_lower for kw in minimal_keywords):
            max_files = file_limits.get('minimal', 5)
            logger.info(f"[ComplexityDetection] Detected MINIMAL project (landing page)")
            return {
                "complexity": "minimal",
                "max_files": max_files,
                "recommended_stack": stacks.get('minimal', "HTML + CSS + JavaScript OR React + Vite"),
                "include_frontend": True,
                "include_backend": False,
                "include_docker": False,
                "hint": "Frontend only landing page. NO backend, NO Docker."
            }

        # Check for SIMPLE
        if any(kw in request_lower for kw in simple_keywords):
            max_files = file_limits.get('simple', 8)
            logger.info(f"[ComplexityDetection] Detected SIMPLE project")
            return {
                "complexity": "simple",
                "max_files": max_files,
                "recommended_stack": stacks.get('simple', "React + Vite + TypeScript + Tailwind"),
                "include_frontend": True,
                "include_backend": False,
                "include_docker": False,
                "hint": "Simple frontend app. Include only backend if explicitly requested."
            }

        # Check for COMPLEX (must be explicit)
        if any(kw in request_lower for kw in complex_keywords):
            max_files = file_limits.get('complex', 40)
            logger.info(f"[ComplexityDetection] Detected COMPLEX project")
            return {
                "complexity": "complex",
                "max_files": max_files,
                "recommended_stack": stacks.get('complex', "Next.js + FastAPI + PostgreSQL"),
                "include_frontend": True,
                "include_backend": True,
                "include_docker": True,
                "hint": "Full-stack project. Structure: frontend/ folder with React/Next.js AND backend/ folder with FastAPI/Node.js. Include ALL necessary files, database models and Docker setup."
            }

        # Check if "e-commerce" without "platform" or "full"
        if "e-commerce" in request_lower or "ecommerce" in request_lower:
            if not any(kw in request_lower for kw in ["platform", "full", "complete"]):
                max_files = file_limits.get('simple', 8)
                logger.info(f"[ComplexityDetection] Detected e-commerce landing (SIMPLE)")
                return {
                    "complexity": "simple",
                    "max_files": max_files,
                    "recommended_stack": stacks.get('simple', "React + Vite + TypeScript + Tailwind"),
                    "include_frontend": True,
                    "include_backend": False,
                    "include_docker": False,
                    "hint": "E-commerce landing page. Frontend only with mock data."
                }

        # Default to intermediate
        logger.info(f"[ComplexityDetection] Detected INTERMEDIATE project (default)")
        needs_backend = "backend" in request_lower or "api" in request_lower or "database" in request_lower or "crud" in request_lower
        max_files = file_limits.get('intermediate_with_backend', 20) if needs_backend else file_limits.get('intermediate', 15)
        return {
            "complexity": "intermediate",
            "max_files": max_files,
            "recommended_stack": stacks.get('intermediate_with_backend', "React + FastAPI + PostgreSQL") if needs_backend else stacks.get('intermediate', "React + Vite + TypeScript"),
            "include_frontend": True,
            "include_backend": needs_backend,
            "include_docker": needs_backend,
            "hint": f"{'Structure: frontend/ and backend/ folders. Include backend and database.' if needs_backend else 'Frontend focused project.'}"
        }

    def _parse_xml_plan(self, plan_text: str) -> Dict[str, Any]:
        """
        Parse plan XML using proper XML AST parsing (not regex)

        Handles both clean XML and XML with surrounding text.
        Falls back gracefully if XML parsing fails.

        Args:
            plan_text: Raw plan text from agent (may contain XML)

        Returns:
            Dict with parsed tasks, project_type, tech_stack
        """
        result = {
            'tasks': [],
            'project_type': None,
            'tech_stack': None
        }

        # Extract XML content if wrapped in other text
        xml_content = plan_text.strip()

        # Find <plan>...</plan> block if present
        if '<plan>' in xml_content and '</plan>' in xml_content:
            start = xml_content.find('<plan>')
            end = xml_content.find('</plan>') + len('</plan>')
            xml_content = xml_content[start:end]

        try:
            # Parse XML using ElementTree
            root = ET.fromstring(xml_content)

            # Extract tasks using XML parsing
            tasks_elem = root.find('tasks')
            if tasks_elem is not None:
                # Parse <step id="1">Task name</step> elements
                steps = tasks_elem.findall('step')
                for i, step in enumerate(steps):
                    step_id = step.get('id', str(i + 1))
                    step_text = step.text or ''
                    result['tasks'].append({
                        "number": int(step_id) if step_id.isdigit() else i + 1,
                        "name": step_text.strip(),
                        "status": "pending"
                    })
                logger.info(f"[XML Parser] Extracted {len(result['tasks'])} tasks using XML AST")

            # Extract project_type using XML parsing
            project_type_elem = root.find('project_type')
            if project_type_elem is not None:
                result['project_type'] = project_type_elem.text.strip() if project_type_elem.text else None

            # Extract tech_stack using XML parsing
            tech_stack_elem = root.find('tech_stack')
            if tech_stack_elem is not None:
                tech_stack_data = {}

                # Parse frontend/backend/database tags
                frontend = tech_stack_elem.find('frontend')
                if frontend is not None and frontend.text:
                    tech_stack_data['frontend'] = frontend.text.strip()

                backend = tech_stack_elem.find('backend')
                if backend is not None and backend.text:
                    tech_stack_data['backend'] = backend.text.strip()

                database = tech_stack_elem.find('database')
                if database is not None and database.text:
                    tech_stack_data['database'] = database.text.strip()

                result['tech_stack'] = tech_stack_data if tech_stack_data else None

        except ET.ParseError as e:
            logger.warning(f"[XML Parser] Failed to parse XML: {e}")
            logger.info("[XML Parser] Falling back to text-based parsing")

            # Fallback: try to parse tasks from text format
            result['tasks'] = self._parse_tasks_fallback(plan_text)

        except Exception as e:
            logger.error(f"[XML Parser] Unexpected error: {e}")
            result['tasks'] = self._parse_tasks_fallback(plan_text)

        return result

    def _parse_xml_from_lxml_dom(self, dom: etree._Element) -> Dict[str, Any]:
        """
        Parse XML data from lxml Element (from BoltXMLParser)

        NEW: Supports file-based plan format with <files> tag.
        File-by-file generation like Bolt.new.

        Args:
            dom: lxml.etree._Element (not xml.etree.ElementTree.Element)

        Returns:
            Dict with parsed files, project_name, project_type, tech_stack, features
        """
        result = {
            'files': [],  # NEW: file list for file-by-file generation
            'tasks': [],  # Legacy: task list for backward compatibility
            'project_name': None,
            'project_description': None,
            'project_type': None,
            'complexity': None,
            'tech_stack': None,
            'features': []
        }

        try:
            # NEW: First check for <files> tag (file-based plan format)
            files_elem = dom.find('files')
            if files_elem is not None:
                for i, file_elem in enumerate(files_elem.findall('file')):
                    file_path = file_elem.get('path', '')
                    priority = file_elem.get('priority', str(i + 1))

                    # Get description from nested <description> tag
                    desc_elem = file_elem.find('description')
                    description = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ''

                    if file_path:
                        result['files'].append({
                            "path": file_path.strip(),
                            "description": description,
                            "priority": int(priority) if priority.isdigit() else i + 1,
                            "status": "pending"
                        })

                # Sort files by priority
                result['files'].sort(key=lambda x: x['priority'])
                logger.info(f"[lxml DOM Parser] [OK] Extracted {len(result['files'])} files from plan (file-by-file mode)")

            # LEGACY: Check for <tasks> tag (old task-based format)
            tasks_elem = dom.find('tasks')
            if tasks_elem is not None and not result['files']:
                steps = tasks_elem.findall('step')

                # If <step> tags exist, parse them
                if steps:
                    for i, step in enumerate(steps):
                        step_id = step.get('id', str(i + 1))
                        step_text = step.text or ''
                        result['tasks'].append({
                            "number": int(step_id) if step_id.isdigit() else i + 1,
                            "name": step_text.strip(),
                            "status": "pending"
                        })
                else:
                    # No <step> tags found, parse text content (Phase 1:, Phase 2: format)
                    tasks_text = etree.tostring(tasks_elem, encoding='unicode', method='text').strip()
                    if tasks_text:
                        lines = tasks_text.split('\n')
                        task_num = 1
                        for line in lines:
                            line = line.strip()
                            if not line or line.startswith('-') or len(line) < 5:
                                continue

                            # Match "Phase 1: Name" or "Step 1: Name" or similar
                            match = re.match(r'(?:Phase|Step|Task)\s+(\d+):\s*(.+)', line, re.IGNORECASE)
                            if match:
                                num, name = match.groups()
                                result['tasks'].append({
                                    "number": int(num),
                                    "name": name.strip(),
                                    "status": "pending"
                                })
                            else:
                                # If no pattern match, treat whole line as task name
                                if not line.startswith('<!--'):
                                    result['tasks'].append({
                                        "number": task_num,
                                        "name": line,
                                        "status": "pending"
                                    })
                                    task_num += 1

                logger.info(f"[lxml DOM Parser] Extracted {len(result['tasks'])} tasks from lxml DOM (legacy mode)")

            # PRODUCTION FIX: Fallback to <project_structure> if no <files> extracted
            # This ensures we always have file paths for the writer agent
            if not result['files']:
                structure_elem = dom.find('project_structure')
                if structure_elem is not None and structure_elem.text:
                    structure_text = structure_elem.text.strip()
                    result['files'] = PlanXMLSchema._extract_files_from_structure(structure_text)
                    if result['files']:
                        logger.info(f"[lxml DOM Parser] [FALLBACK] Extracted {len(result['files'])} files from <project_structure>")
                    else:
                        logger.warning("[lxml DOM Parser] No files found in <project_structure>")

            # Extract project_name from lxml DOM
            project_name_elem = dom.find('project_name')
            if project_name_elem is not None:
                raw_name = project_name_elem.text
                if raw_name:
                    result['project_name'] = raw_name.strip()
                    logger.info(f"[lxml DOM Parser] Extracted project_name: '{result['project_name']}' (raw: '{raw_name[:50]}...' len={len(raw_name)})")
                else:
                    result['project_name'] = None
                    logger.warning(f"[lxml DOM Parser] project_name element found but text is None/empty")

            # Extract project_description from lxml DOM
            project_desc_elem = dom.find('project_description')
            if project_desc_elem is not None:
                result['project_description'] = project_desc_elem.text.strip() if project_desc_elem.text else None

            # Extract project_type from lxml DOM
            project_type_elem = dom.find('project_type')
            if project_type_elem is not None:
                result['project_type'] = project_type_elem.text.strip() if project_type_elem.text else None

            # Extract complexity from lxml DOM
            complexity_elem = dom.find('complexity')
            if complexity_elem is not None:
                result['complexity'] = complexity_elem.text.strip() if complexity_elem.text else None

            # Extract tech_stack from lxml DOM - NEW: supports <category> format
            tech_stack_elem = dom.find('tech_stack')
            if tech_stack_elem is not None:
                tech_stack_data = {}

                # New format: <category name="Frontend">React, Vite, TypeScript</category>
                categories = tech_stack_elem.findall('category')
                if categories:
                    for cat in categories:
                        cat_name = cat.get('name', 'unknown')
                        cat_value = cat.text.strip() if cat.text else ''
                        tech_stack_data[cat_name.lower()] = cat_value
                else:
                    # Legacy format: <frontend>, <backend>, <database>
                    frontend = tech_stack_elem.find('frontend')
                    if frontend is not None and frontend.text:
                        tech_stack_data['frontend'] = frontend.text.strip()

                    backend = tech_stack_elem.find('backend')
                    if backend is not None and backend.text:
                        tech_stack_data['backend'] = backend.text.strip()

                    database = tech_stack_elem.find('database')
                    if database is not None and database.text:
                        tech_stack_data['database'] = database.text.strip()

                result['tech_stack'] = tech_stack_data if tech_stack_data else None

            # Extract features from lxml DOM
            features_elem = dom.find('features')
            if features_elem is not None:
                for feature_elem in features_elem.findall('feature'):
                    icon = feature_elem.get('icon', '✨')
                    name = feature_elem.get('name', '')
                    description = feature_elem.text.strip() if feature_elem.text else ''
                    if name:
                        result['features'].append({
                            'icon': icon,
                            'name': name,
                            'description': description
                        })

        except Exception as e:
            logger.error(f"[lxml DOM Parser] Error parsing lxml DOM: {e}")

        return result

    def _parse_xml_from_dom(self, dom: ET.Element) -> Dict[str, Any]:
        """
        Parse XML data from pre-built DOM element (from SAX parser)

        Args:
            dom: ElementTree Element (already parsed DOM)

        Returns:
            Dict with parsed tasks, project_type, tech_stack
        """
        result = {
            'tasks': [],
            'project_type': None,
            'tech_stack': None
        }

        try:
            # Extract tasks from DOM
            tasks_elem = dom.find('tasks')
            if tasks_elem is not None:
                steps = tasks_elem.findall('step')
                for i, step in enumerate(steps):
                    step_id = step.get('id', str(i + 1))
                    step_text = step.text or ''
                    result['tasks'].append({
                        "number": int(step_id) if step_id.isdigit() else i + 1,
                        "name": step_text.strip(),
                        "status": "pending"
                    })
                logger.info(f"[DOM Parser] Extracted {len(result['tasks'])} tasks from DOM")

            # Extract project_type from DOM
            project_type_elem = dom.find('project_type')
            if project_type_elem is not None:
                result['project_type'] = project_type_elem.text.strip() if project_type_elem.text else None

            # Extract tech_stack from DOM
            tech_stack_elem = dom.find('tech_stack')
            if tech_stack_elem is not None:
                tech_stack_data = {}

                frontend = tech_stack_elem.find('frontend')
                if frontend is not None and frontend.text:
                    tech_stack_data['frontend'] = frontend.text.strip()

                backend = tech_stack_elem.find('backend')
                if backend is not None and backend.text:
                    tech_stack_data['backend'] = backend.text.strip()

                database = tech_stack_elem.find('database')
                if database is not None and database.text:
                    tech_stack_data['database'] = database.text.strip()

                result['tech_stack'] = tech_stack_data if tech_stack_data else None

        except Exception as e:
            logger.error(f"[DOM Parser] Error parsing DOM: {e}")

        return result

    def _parse_tasks_fallback(self, plan_text: str) -> List[Dict[str, Any]]:
        """
        Fallback text-based task parsing when XML parsing fails

        Args:
            plan_text: Raw plan text

        Returns:
            List of parsed tasks
        """
        tasks = []

        # Try to find task section
        if '<tasks>' in plan_text and '</tasks>' in plan_text:
            start = plan_text.find('<tasks>') + len('<tasks>')
            end = plan_text.find('</tasks>')
            tasks_text = plan_text[start:end].strip()

            # Parse line by line
            lines = tasks_text.split('\n')
            task_num = 1
            for line in lines:
                line = line.strip()
                if not line or line.startswith('<!--') or line.startswith('//'):
                    continue

                # Try to extract step number and name
                # Formats: "STEP 1: Name", "Step 1: Name", "1. Name", etc.
                import re
                patterns = [
                    r'(?:STEP|Step|step)\s+(\d+):\s*(.+)',
                    r'<step[^>]*id=["\'](\d+)["\'][^>]*>(.+?)</step>',
                    r'(\d+)\.\s+(.+)',
                ]

                for pattern in patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        num, name = match.groups()
                        tasks.append({
                            "number": int(num),
                            "name": name.strip(),
                            "status": "pending"
                        })
                        break
                else:
                    # No pattern matched, use line as-is
                    if len(line) > 5:  # Skip very short lines
                        tasks.append({
                            "number": task_num,
                            "name": line,
                            "status": "pending"
                        })
                        task_num += 1

        logger.info(f"[Fallback Parser] Extracted {len(tasks)} tasks")
        return tasks

    def _extract_file_path_from_chunk(self, accumulated_buffer: str) -> Optional[str]:
        """
        Streaming-based tag reconstruction for <file path="...">

        Handles partial XML in streaming chunks without regex.
        Reconstructs tags character-by-character.

        Args:
            accumulated_buffer: Accumulated stream buffer

        Returns:
            File path if complete tag found, None otherwise
        """
        # Look for complete <file path="..."> tag in buffer
        if '<file path="' in accumulated_buffer and '">' in accumulated_buffer:
            start = accumulated_buffer.find('<file path="') + len('<file path="')
            end = accumulated_buffer.find('">', start)

            if end > start:
                return accumulated_buffer[start:end]

        return None

    async def execute_workflow(
        self,
        user_request: str,
        project_id: str,
        workflow_name: str = "bolt_standard",
        metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute a workflow with real-time event streaming

        Args:
            user_request: User's request
            project_id: Project identifier
            workflow_name: Which workflow to execute
            metadata: Additional context

        Yields:
            OrchestratorEvent: Real-time events for SSE streaming
        """
        # Create temp session for ephemeral storage (like Bolt.new)
        session_id = None
        if self.use_temp_storage:
            user_id = metadata.get("user_id") if metadata else None
            project_name = metadata.get("project_name") if metadata else None
            session_id = self.create_session(user_id, project_name)
            logger.info(f"[TempStorage] Created session: {session_id}")

        # Initialize Memory Agent for context tracking (like Claude Code)
        from app.modules.agents.memory_agent import get_memory_agent
        from app.core.config import settings

        # Get user_id for correct sandbox path (user_id/project_id structure)
        user_id = metadata.get("user_id") if metadata else None
        logger.info(f"[MemoryAgent Debug] user_id={user_id}, project_id={project_id}, metadata_keys={list(metadata.keys()) if metadata else 'None'}")

        # Use sandbox path with user_id (like Bolt.new: {user_id}/{project_id})
        sandbox_project_path = str(self._unified_storage.get_sandbox_path(project_id, user_id))
        project_path = metadata.get("working_directory", sandbox_project_path) if metadata else sandbox_project_path
        logger.info(f"[MemoryAgent Debug] sandbox_project_path={sandbox_project_path}, project_path={project_path}")
        memory_agent = get_memory_agent(project_id, project_path)

        # Initialize memory agent (scan project files)
        try:
            memory_info = await memory_agent.initialize()
            logger.info(f"[MemoryAgent] Initialized: {memory_info.get('total_files')} files, type: {memory_info.get('project_type')}")
        except Exception as e:
            logger.warning(f"[MemoryAgent] Initialization warning: {e}")

        # Record user request in conversation history
        memory_agent.add_conversation_turn(
            role="user",
            content=user_request,
            files_mentioned=memory_agent.get_relevant_files(user_request)
        )

        # Initialize execution context with memory context
        context = ExecutionContext(
            project_id=project_id,
            user_request=user_request,
            user_id=user_id,  # Pass user_id for file operations
            metadata=metadata or {}
        )

        # Add session_id to context for file operations
        context.metadata["session_id"] = session_id

        # Add memory context to metadata for other agents
        context.metadata["memory_context"] = memory_agent.get_context_for_agent("planner")
        context.metadata["project_type"] = memory_agent.context.project_type
        context.metadata["tech_stack"] = memory_agent.context.tech_stack

        # Store memory agent reference for file change tracking
        self._current_memory_agent = memory_agent

        # ============================================================
        # RESUME FLOW: Load saved plan from database if resuming
        # This allows writer to continue with original plan and file descriptions
        # ============================================================
        if metadata and metadata.get("is_resume"):
            saved_plan = metadata.get("saved_plan")
            if saved_plan:
                context.plan = saved_plan
                context.project_name = metadata.get("project_name", "")
                context.project_description = metadata.get("project_description", "")
                logger.info(f"[Resume] Loaded saved plan with {len(saved_plan.get('files', []))} files")

                # Also load existing files into context for reference
                existing_files = metadata.get("existing_files", [])
                if existing_files:
                    context.files_created = [{"path": f} for f in existing_files]
                    logger.info(f"[Resume] Pre-loaded {len(existing_files)} completed files into context")

        # ============================================================
        # AUTO-FIX FLOW: Handle FIX intent with auto-collected context
        # This is triggered when user reports a problem in simple terms
        # (e.g., "page is blank", "it's not working", "fix this error")
        # The frontend automatically collects all errors, logs, and files
        # ============================================================
        if metadata and metadata.get("intent") == "FIX":
            auto_fix_context = metadata.get("auto_fix_context", {})
            collected_errors = auto_fix_context.get("collected_errors", [])
            terminal_logs = auto_fix_context.get("terminal_logs", [])
            project_files = auto_fix_context.get("project_files", [])
            user_problem = auto_fix_context.get("user_problem_description", user_request)

            logger.info(f"[AUTO-FIX] FIX intent detected!")
            logger.info(f"[AUTO-FIX] User problem: {user_problem}")
            logger.info(f"[AUTO-FIX] Collected errors: {len(collected_errors)}")
            logger.info(f"[AUTO-FIX] Terminal logs: {len(terminal_logs)}")
            logger.info(f"[AUTO-FIX] Project files: {len(project_files)}")

            # Populate context with auto-collected errors
            context.errors = collected_errors
            context.metadata["terminal_logs"] = terminal_logs
            context.metadata["auto_fix_mode"] = True
            context.metadata["user_problem"] = user_problem

            # Store project files in context if provided
            if project_files:
                context.files_created = [
                    {"path": f["path"], "content": f["content"]}
                    for f in project_files if f.get("content")
                ]

            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={
                    "message": f"Auto-fixing: {user_problem}",
                    "errors_count": len(collected_errors),
                    "mode": "auto_fix"
                }
            )

            # Send thinking step for UI
            yield OrchestratorEvent(
                type=EventType.THINKING_STEP,
                data={
                    "step": "analyzing",
                    "status": "active",
                    "user_visible": True,
                    "detail": "Analyzing problem and collected context...",
                    "icon": "search"
                }
            )

            # Execute fixer directly (bypass normal workflow)
            fixer_config = AgentConfig(
                name="fixer",
                agent_type="fixer",
                model=settings.DEFAULT_LLM_MODEL,
                description="Auto-fix agent"
            )

            async for event in self._execute_auto_fixer(fixer_config, context):
                yield event

            # Complete the workflow
            yield OrchestratorEvent(
                type=EventType.COMPLETE,
                data={
                    "message": "Auto-fix completed!",
                    "session_id": session_id,
                    "files_fixed": len(context.files_modified)
                }
            )
            return  # Exit early - no need to run normal workflow

        # Get workflow steps
        workflow = self.workflow_engine.get_workflow(workflow_name)
        context.total_steps = len(workflow)

        # Store workflow steps as tasks for frontend UI display
        # Filter out hidden steps - only show user-facing steps to keep UI clean
        visible_steps = [(idx, step) for idx, step in enumerate(workflow) if not getattr(step, 'hidden', False)]
        context.workflow_steps = [
            {
                "number": visible_idx + 1,  # Renumber visible steps 1, 2, 3...
                "title": step.name,
                "name": step.name,
                "description": step.description,
                "agent_type": step.agent_type,
                "has_condition": step.condition is not None
            }
            for visible_idx, (_, step) in enumerate(visible_steps)
        ]
        logger.info(f"[Workflow] Prepared {len(context.workflow_steps)} visible workflow steps for frontend UI (hidden {len(workflow) - len(visible_steps)} internal steps)")

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={
                "message": f"Starting {workflow_name} workflow",
                "total_steps": context.total_steps
            }
        )

        # Get user_id for user-scoped paths (Bolt.new structure: {user_id}/{project_id}/)
        user_id = metadata.get("user_id") if metadata else None
        logger.info(f"[UserID Debug] From metadata: user_id={user_id}, metadata keys={list(metadata.keys()) if metadata else 'None'}")

        # FALLBACK: If user_id not in metadata, try to get from database
        if not user_id:
            logger.warning(f"[UserID Debug] No user_id in metadata, attempting database lookup for project {project_id}")
            try:
                from app.core.database import AsyncSessionLocal
                from app.models.project import Project
                from sqlalchemy import select
                from uuid import UUID

                async with AsyncSessionLocal() as session:
                    project_uuid = UUID(project_id)
                    result = await session.execute(
                        select(Project.user_id).where(Project.id == project_uuid)
                    )
                    db_user_id = result.scalar_one_or_none()
                    if db_user_id:
                        user_id = str(db_user_id)
                        logger.info(f"[UserID Debug] Got user_id from database: {user_id}")
                    else:
                        logger.warning(f"[UserID Debug] Project {project_id} not found in database or has no user_id")
            except Exception as e:
                logger.warning(f"[UserID Debug] Database lookup failed: {e}")

        # Create sandbox workspace (Layer 1 of 3-Layer Storage)
        # Path: C:/tmp/sandbox/workspace/{user_id}/{project_id}/
        try:
            await self._unified_storage.create_sandbox(project_id, user_id)
            logger.info(f"[Layer1-Sandbox] Created sandbox for user {user_id or 'anon'}, project {project_id}")
        except Exception as e:
            logger.warning(f"[Layer1-Sandbox] Failed to create sandbox: {e}")

        # Create checkpoint for resume capability (Layer 3)
        try:
            await checkpoint_service.create_checkpoint(
                project_id=project_id,
                user_id=str(user_id) if user_id else "anonymous",
                workflow_type=workflow_name,
                initial_request={
                    "user_request": user_request,
                    "metadata": metadata or {},
                    "workflow_name": workflow_name
                }
            )
            logger.info(f"[Layer3-Checkpoint] Created checkpoint for project {project_id}")
        except Exception as e:
            logger.warning(f"[Layer3-Checkpoint] Failed to create checkpoint: {e}")

        # Send workflow_started event with all tasks IMMEDIATELY so UI shows all 7 steps from the start
        # This fixes the issue where only 1 task was showing (because plan_created comes after planner completes)
        yield OrchestratorEvent(
            type=EventType.PLAN_CREATED,
            data={
                "tasks": context.workflow_steps,  # All 7 workflow steps
                "mode": "workflow_started",  # Signal this is initial tasks, not plan completion
                "message": f"Workflow '{workflow_name}' started with {len(context.workflow_steps)} steps"
            }
        )
        logger.info(f"[WORKFLOW_STARTED] Sent initial plan_created event with {len(context.workflow_steps)} workflow tasks")

        try:
            # Import cancellation check from API layer
            from app.api.v1.endpoints.orchestrator import is_project_cancelled

            # Execute each step in workflow
            for step_index, step in enumerate(workflow, 1):
                # Check for cancellation before each step
                if is_project_cancelled(project_id):
                    logger.info(f"[Workflow] Project {project_id} cancelled, stopping at step {step_index}")
                    yield OrchestratorEvent(
                        type=EventType.STATUS,
                        data={"message": "Generation cancelled by user"}
                    )
                    return  # Exit workflow

                context.current_step = step_index

                # Check step condition (if any) with error handling
                if step.condition:
                    try:
                        condition_result = step.condition(context)
                    except Exception as cond_err:
                        logger.warning(f"[Workflow] Step {step_index} condition error: {cond_err}, skipping step")
                        condition_result = False  # Skip step if condition evaluation fails

                    if not condition_result:
                        logger.info(f"Skipping step {step_index}: {step.name} (condition not met)")
                        # Send AGENT_COMPLETE event to mark skipped step as complete in UI
                        yield OrchestratorEvent(
                            type=EventType.AGENT_COMPLETE,
                            data={
                                "agent": step.agent_type,
                                "name": step.name,
                                "success": True,
                                "skipped": True,
                                "details": "Skipped - not needed for this project"
                            },
                            agent=step.agent_type,
                            step=step_index
                        )
                        continue

                # Execute step with retries
                step_result = None
                step_timeout = step.timeout or 120  # Default 120 seconds
                step_success = False

                for attempt in range(step.retry_count):
                    try:
                        yield OrchestratorEvent(
                            type=EventType.AGENT_START,
                            data={
                                "agent": step.agent_type,
                                "name": step.name,
                                "description": step.description,
                                "attempt": attempt + 1,
                                "max_attempts": step.retry_count,
                                "timeout": step_timeout
                            },
                            agent=step.agent_type,
                            step=step_index
                        )

                        # Execute agent with timeout tracking
                        # Note: We can't use asyncio.wait_for directly on async generators
                        # Instead, we track start time and check periodically
                        step_start_time = asyncio.get_event_loop().time()
                        event_count = 0
                        last_event_time = step_start_time

                        async for event in self._execute_agent(step.agent_type, context):
                            event.step = step_index
                            event.agent = step.agent_type
                            yield event
                            event_count += 1
                            last_event_time = asyncio.get_event_loop().time()

                            # Check for timeout (only if no events for a while)
                            elapsed = last_event_time - step_start_time
                            if elapsed > step_timeout:
                                raise asyncio.TimeoutError(f"Step {step.name} timed out after {step_timeout}s")

                        step_success = True

                        yield OrchestratorEvent(
                            type=EventType.AGENT_COMPLETE,
                            data={
                                "agent": step.agent_type,
                                "name": step.name,
                                "success": True,
                                "events_processed": event_count,
                                "duration_seconds": round(asyncio.get_event_loop().time() - step_start_time, 2)
                            },
                            agent=step.agent_type,
                            step=step_index
                        )

                        # Update checkpoint after successful step
                        try:
                            await checkpoint_service.update_step(
                                project_id=project_id,
                                step=step.name,
                                status=CheckpointStatus.COMPLETED,
                                context={"files_created": len(context.files_created)}
                            )
                        except Exception as cp_err:
                            logger.warning(f"[Checkpoint] Failed to update step: {cp_err}")

                        break  # Success, exit retry loop

                    except asyncio.TimeoutError as te:
                        logger.error(f"Step {step_index} attempt {attempt + 1} timed out: {te}")

                        if attempt == step.retry_count - 1:
                            # Final attempt timed out
                            context.errors.append({
                                "step": step_index,
                                "agent": step.agent_type,
                                "error": f"Timeout: {str(te)}",
                                "timeout": True
                            })
                            yield OrchestratorEvent(
                                type=EventType.ERROR,
                                data={
                                    "message": f"Step {step.name} timed out after {step.retry_count} attempts",
                                    "error": str(te),
                                    "timeout": True
                                },
                                agent=step.agent_type,
                                step=step_index
                            )
                        else:
                            # Retry with timeout warning
                            yield OrchestratorEvent(
                                type=EventType.WARNING,
                                data={
                                    "message": f"Step {step.name} timed out, retrying...",
                                    "attempt": attempt + 2,
                                    "timeout": True
                                },
                                step=step_index
                            )
                            await asyncio.sleep(min(2 ** attempt, 10))  # Exponential backoff, max 10s

                    except asyncio.CancelledError:
                        logger.warning(f"Step {step_index} was cancelled")
                        yield OrchestratorEvent(
                            type=EventType.WARNING,
                            data={
                                "message": f"Step {step.name} was cancelled",
                                "cancelled": True
                            },
                            step=step_index
                        )
                        raise  # Re-raise to stop the workflow

                    except Exception as e:
                        logger.error(f"Step {step_index} attempt {attempt + 1} failed: {e}", exc_info=True)

                        if attempt == step.retry_count - 1:
                            # Final attempt failed
                            context.errors.append({
                                "step": step_index,
                                "agent": step.agent_type,
                                "error": str(e)
                            })
                            yield OrchestratorEvent(
                                type=EventType.ERROR,
                                data={
                                    "message": f"Step {step.name} failed after {step.retry_count} attempts",
                                    "error": str(e)
                                },
                                agent=step.agent_type,
                                step=step_index
                            )
                        else:
                            # Retry
                            yield OrchestratorEvent(
                                type=EventType.WARNING,
                                data={
                                    "message": f"Retrying {step.name}...",
                                    "attempt": attempt + 2,
                                    "error": str(e)[:100]  # Include brief error in retry message
                                },
                                step=step_index
                            )
                            await asyncio.sleep(min(2 ** attempt, 10))  # Exponential backoff, max 10s

                # Log step completion status
                if step_success:
                    logger.info(f"[Workflow] Step {step_index} ({step.name}) completed successfully")
                else:
                    logger.warning(f"[Workflow] Step {step_index} ({step.name}) failed after {step.retry_count} attempts")

            # LAYER 2: Upload to S3 on completion (if configured)
            # Yield progress event to keep SSE connection alive during S3 upload
            yield OrchestratorEvent(
                type=EventType.PROGRESS,
                data={"message": "Saving project to cloud storage...", "phase": "s3_upload"},
                step=len(workflow.steps)
            )

            s3_zip_key = None
            user_id = metadata.get("user_id") if metadata else None
            if user_id:
                try:
                    s3_zip_key = await self._unified_storage.create_and_upload_zip(
                        user_id=str(user_id),
                        project_id=project_id
                    )
                    if s3_zip_key:
                        logger.info(f"[Layer2-S3] Uploaded project ZIP: {s3_zip_key}")
                        yield OrchestratorEvent(
                            type=EventType.PROGRESS,
                            data={"message": "Project saved to cloud", "phase": "s3_upload_complete", "s3_key": s3_zip_key},
                            step=len(workflow.steps)
                        )
                except Exception as s3_err:
                    logger.warning(f"[Layer2-S3] Failed to upload to S3: {s3_err}")

            # LAYER 3: Update PostgreSQL with metadata
            # Yield progress event to keep SSE connection alive during DB update
            yield OrchestratorEvent(
                type=EventType.PROGRESS,
                data={"message": "Updating project metadata...", "phase": "db_update"},
                step=len(workflow.steps)
            )

            try:
                from app.core.database import async_session
                from app.models.project import Project, ProjectStatus
                from sqlalchemy import select, update

                async with async_session() as db:
                    # Build file index
                    file_index = [
                        {"path": f, "type": "file"}
                        for f in context.files_created
                    ]

                    # Update project record
                    # Check if academic documents were generated - if so, mark as COMPLETED
                    # Otherwise mark as PARTIAL_COMPLETED (code done, documents pending/skipped)
                    academic_docs_generated = context.metadata.get("academic_docs_generated", False) if context.metadata else False
                    final_status = ProjectStatus.COMPLETED if academic_docs_generated else ProjectStatus.PARTIAL_COMPLETED
                    logger.info(f"[Layer3-PostgreSQL] Setting project status to {final_status.value} (academic_docs_generated={academic_docs_generated})")

                    update_values = {
                        'status': final_status,
                        's3_path': self._unified_storage.get_s3_prefix(str(user_id), project_id) if user_id else None,
                        's3_zip_key': s3_zip_key,
                        'plan_json': context.plan if hasattr(context, 'plan') else None,
                        'file_index': file_index,
                        # Set completed_at if project is fully completed
                        'completed_at': datetime.now() if final_status == ProjectStatus.COMPLETED else None,
                        'progress': 100
                    }
                    
                    # Update project metadata from context (extracted from planner)
                    if hasattr(context, 'project_name') and context.project_name:
                        update_values['title'] = context.project_name
                    if hasattr(context, 'project_description') and context.project_description:
                        update_values['description'] = context.project_description
                    if hasattr(context, 'project_type') and context.project_type:
                        update_values['domain'] = context.project_type
                    if hasattr(context, 'tech_stack') and context.tech_stack:
                        update_values['tech_stack'] = context.tech_stack
                    if hasattr(context, 'features') and context.features:
                        update_values['requirements'] = context.features
                    
                    await db.execute(
                        update(Project)
                        .where(Project.id == project_id)
                        .values(**update_values)
                    )
                    await db.commit()
                    logger.info(f"[Layer3-PostgreSQL] Updated project metadata for {project_id}")
            except Exception as db_err:
                logger.warning(f"[Layer3-PostgreSQL] Failed to update project: {db_err}")

            # Yield progress event after DB update
            yield OrchestratorEvent(
                type=EventType.PROGRESS,
                data={"message": "Finalizing project...", "phase": "finalizing"},
                step=len(workflow.steps)
            )

            # Save token usage to database
            if user_id and context.total_tokens > 0:
                try:
                    from app.modules.auth.usage_limits import deduct_tokens
                    from app.models.user import User
                    from app.core.database import async_session
                    from sqlalchemy import select

                    async with async_session() as token_db:
                        # Get user
                        user_result = await token_db.execute(
                            select(User).where(User.id == user_id)
                        )
                        user = user_result.scalar_one_or_none()

                        if user:
                            # Deduct tokens for each model used
                            for model_name, usage in context.token_usage_by_model.items():
                                model_total = usage["input"] + usage["output"]
                                await deduct_tokens(user, token_db, model_total, model_name)
                                logger.info(f"[TokenTracker] Saved {model_total} tokens for model {model_name}")

                            logger.info(f"[TokenTracker] Total tokens saved: {context.total_tokens} (input: {context.total_input_tokens}, output: {context.total_output_tokens})")

                            # Save detailed token transactions
                            if context.pending_token_transactions:
                                from app.services.token_tracker import token_tracker
                                from app.models.usage import AgentType, OperationType

                                for tx in context.pending_token_transactions:
                                    try:
                                        # Map string agent_type to enum
                                        agent_type_str = tx.get("agent_type", "other")
                                        agent_type = AgentType(agent_type_str) if agent_type_str in [e.value for e in AgentType] else AgentType.OTHER

                                        # Map string operation to enum
                                        operation_str = tx.get("operation", "other")
                                        operation = OperationType(operation_str) if operation_str in [e.value for e in OperationType] else OperationType.OTHER

                                        await token_tracker.log_transaction(
                                            db=token_db,
                                            user_id=str(user_id),
                                            project_id=str(project_id),
                                            agent_type=agent_type,
                                            operation=operation,
                                            model=tx.get("model", "haiku"),
                                            input_tokens=tx.get("input_tokens", 0),
                                            output_tokens=tx.get("output_tokens", 0),
                                            file_path=tx.get("file_path"),
                                            metadata=tx.get("metadata")
                                        )
                                    except Exception as tx_err:
                                        logger.warning(f"[TokenTracker] Failed to save transaction: {tx_err}")

                                logger.info(f"[TokenTracker] Saved {len(context.pending_token_transactions)} detailed token transactions")

                except Exception as token_err:
                    logger.warning(f"[TokenTracker] Failed to save token usage: {token_err}")

            # ============================================
            # POST-GENERATION: Smart Fullstack Integration
            # ============================================
            integration_result = None
            if len(context.files_created) > 0:
                try:
                    # Check if this is a fullstack project (has both frontend and backend folders)
                    from pathlib import Path
                    project_path = Path(self._unified_storage.get_sandbox_path(project_id, user_id))
                    frontend_path = project_path / "frontend"
                    backend_path = project_path / "backend"

                    if frontend_path.exists() and backend_path.exists():
                        logger.info(f"[SmartIntegration] Detected fullstack project, running smart integration...")

                        yield OrchestratorEvent(
                            type=EventType.STATUS,
                            data={
                                "message": "Running smart fullstack integration...",
                                "phase": "integration"
                            }
                        )

                        from app.services.fullstack_integrator import FullstackIntegrator

                        integrator = FullstackIntegrator(
                            project_path=project_path,
                            frontend_port=3000,
                            backend_port=4000
                        )
                        integration_result = await integrator.integrate(smart_integration=True)

                        if integration_result.get("success"):
                            logger.info(f"[SmartIntegration] Integration complete: {integration_result.get('actions', [])}")

                            # Report detected endpoints
                            endpoints_count = integration_result.get("endpoints_detected", 0)
                            if endpoints_count > 0:
                                yield OrchestratorEvent(
                                    type=EventType.STATUS,
                                    data={
                                        "message": f"Detected {endpoints_count} backend endpoints",
                                        "endpoints_detected": endpoints_count,
                                        "phase": "integration"
                                    }
                                )

                            # Report generated API files
                            api_files = integration_result.get("api_files_generated", [])
                            if api_files:
                                yield OrchestratorEvent(
                                    type=EventType.STATUS,
                                    data={
                                        "message": f"Generated {len(api_files)} typed API service files",
                                        "files_generated": api_files,
                                        "phase": "integration"
                                    }
                                )

                            # Report validation results
                            validation = integration_result.get("validation")
                            if validation:
                                stats = validation.get("statistics", {})
                                yield OrchestratorEvent(
                                    type=EventType.STATUS,
                                    data={
                                        "message": f"Integration validation: {stats.get('errors', 0)} errors, {stats.get('warnings', 0)} warnings",
                                        "validation": stats,
                                        "phase": "integration"
                                    }
                                )
                        else:
                            logger.warning(f"[SmartIntegration] Integration had issues: {integration_result.get('error')}")
                    else:
                        logger.info(f"[SmartIntegration] Not a fullstack project (frontend: {frontend_path.exists()}, backend: {backend_path.exists()})")

                except Exception as integration_err:
                    logger.warning(f"[SmartIntegration] Failed to run smart integration: {integration_err}")

            # Workflow complete - include session_id for ZIP download
            complete_data = {
                "message": "Workflow completed successfully",
                "files_created": len(context.files_created),
                "files_modified": len(context.files_modified),
                "commands_executed": len(context.commands_executed),
                "errors": len(context.errors),
                "session_id": session_id,  # For ZIP download
                "download_url": f"/api/v1/download/session/{session_id}" if session_id else None,
                "s3_zip_key": s3_zip_key,  # S3 download key
                "token_usage": {
                    "total": context.total_tokens,
                    "input": context.total_input_tokens,
                    "output": context.total_output_tokens,
                    "by_model": context.token_usage_by_model
                }
            }

            # Add integration results if available
            if integration_result:
                complete_data["integration"] = {
                    "success": integration_result.get("success", False),
                    "endpoints_detected": integration_result.get("endpoints_detected", 0),
                    "api_files_generated": len(integration_result.get("api_files_generated", [])),
                    "validation": integration_result.get("validation", {}).get("statistics"),
                }

            yield OrchestratorEvent(
                type=EventType.COMPLETE,
                data=complete_data
            )

            # Mark checkpoint as completed
            try:
                await checkpoint_service.mark_completed(project_id)
                logger.info(f"[Layer3-Checkpoint] Marked project {project_id} as completed")
            except Exception as cp_err:
                logger.warning(f"[Layer3-Checkpoint] Failed to mark completed: {cp_err}")

        except asyncio.CancelledError:
            # Client disconnected - mark as interrupted for resume
            logger.warning(f"[Workflow] Client disconnected during project {project_id}")
            try:
                await checkpoint_service.mark_interrupted(project_id, "Client disconnected")
            except Exception as cp_err:
                logger.warning(f"[Checkpoint] Failed to mark interrupted: {cp_err}")
            raise

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}", exc_info=True)

            # Mark checkpoint as failed/interrupted for resume
            try:
                await checkpoint_service.mark_interrupted(project_id, str(e))
            except Exception as cp_err:
                logger.warning(f"[Checkpoint] Failed to mark interrupted: {cp_err}")

            yield OrchestratorEvent(
                type=EventType.ERROR,
                data={"message": "Workflow failed", "error": str(e), "can_resume": True}
            )

    async def resume_workflow(
        self,
        project_id: str,
        resume_info: Dict[str, Any],
        checkpoint_service: Any = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Resume an interrupted workflow from checkpoint.

        Args:
            project_id: Project identifier
            resume_info: Resume information from checkpoint
            checkpoint_service: Checkpoint service instance

        Yields:
            Dict events for SSE streaming
        """
        logger.info(f"[Resume] Resuming project {project_id} from step: {resume_info.get('next_step')}")

        # Get original request from checkpoint
        initial_request = resume_info.get("initial_request", {})
        user_request = initial_request.get("user_request", "")
        metadata = initial_request.get("metadata", {})
        workflow_name = initial_request.get("workflow_name", "bolt_standard")

        # Get remaining files to generate
        remaining_files = resume_info.get("remaining_files", [])
        completed_steps = resume_info.get("completed_steps", [])

        yield {
            "type": "resume_info",
            "data": {
                "project_id": project_id,
                "remaining_files": len(remaining_files),
                "completed_steps": completed_steps,
                "resuming_from": resume_info.get("next_step")
            }
        }

        # If there are remaining files, generate them directly
        if remaining_files:
            yield {
                "type": "status",
                "data": {
                    "message": f"Resuming file generation - {len(remaining_files)} files remaining"
                }
            }

            # Create context for file generation
            user_id = metadata.get("user_id") if metadata else None
            context = ExecutionContext(
                project_id=project_id,
                user_request=user_request,
                user_id=user_id,  # Pass user_id for file operations
                metadata=metadata
            )
            context.plan = resume_info.get("context", {}).get("plan", {})

            for idx, file_info in enumerate(remaining_files):
                file_path = file_info.get("path", "")
                file_desc = file_info.get("description", "")

                yield {
                    "type": "file_start",
                    "data": {
                        "path": file_path,
                        "index": idx + 1,
                        "total": len(remaining_files)
                    }
                }

                try:
                    # Generate file using writer
                    async for event in self._execute_writer_for_single_file(
                        context=context,
                        file_path=file_path,
                        file_description=file_desc
                    ):
                        if event.type == EventType.FILE_CREATED:
                            yield {
                                "type": "file_created",
                                "data": {
                                    "path": event.data.get("path"),
                                    "content": event.data.get("content"),
                                    "project_id": project_id  # For file isolation
                                }
                            }
                except Exception as e:
                    logger.error(f"[Resume] Failed to generate file {file_path}: {e}")
                    yield {
                        "type": "file_error",
                        "data": {
                            "path": file_path,
                            "error": str(e)
                        }
                    }

        yield {
            "type": "resume_completed",
            "data": {
                "project_id": project_id,
                "message": "Resume completed successfully"
            }
        }

    async def resume_incomplete_files(
        self,
        project_id: str,
        incomplete_files: List[Dict[str, Any]],
        plan: Dict[str, Any],
        user_id: str = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Resume generation of incomplete files only.

        This is called when files exist in DB with status != COMPLETED.
        Uses the saved plan to regenerate only the missing files.

        Args:
            project_id: Project identifier
            incomplete_files: List of files to generate (from get_incomplete_files)
            plan: Saved plan_json from database
            user_id: User identifier for storage paths

        Yields:
            Dict events for SSE streaming
        """
        logger.info(f"[ResumeIncomplete] Starting for {project_id} with {len(incomplete_files)} files")

        yield {
            "type": "status",
            "data": {
                "message": f"Resuming generation of {len(incomplete_files)} incomplete files",
                "files": [f["path"] for f in incomplete_files]
            }
        }

        # Create minimal context for file generation
        context = ExecutionContext(
            project_id=project_id,
            user_request="Resume incomplete file generation",
            user_id=user_id,  # Pass user_id for file operations
            metadata={"user_id": user_id, "is_resume": True}
        )
        context.plan = plan

        # Get file descriptions from plan
        plan_files = plan.get("files", [])
        file_descriptions = {f.get("path"): f.get("description", "") for f in plan_files}

        # Generate each incomplete file
        for idx, file_info in enumerate(incomplete_files):
            file_path = file_info["path"]
            file_status = file_info["status"]

            yield {
                "type": "file_start",
                "data": {
                    "path": file_path,
                    "index": idx + 1,
                    "total": len(incomplete_files),
                    "previous_status": file_status
                }
            }

            # Update status to GENERATING
            try:
                from app.core.database import async_session
                from app.models.project_file import ProjectFile, FileGenerationStatus
                from sqlalchemy import update
                from uuid import UUID as UUID_type

                async with async_session() as db:
                    await db.execute(
                        update(ProjectFile)
                        .where(ProjectFile.project_id == UUID_type(str(project_id)))
                        .where(ProjectFile.path == file_path)
                        .values(generation_status=FileGenerationStatus.GENERATING)
                    )
                    await db.commit()
            except Exception as e:
                logger.warning(f"[ResumeIncomplete] Could not update status: {e}")

            # Get description for this file
            description = file_descriptions.get(file_path, f"Generate {file_path}")

            # Generate file using Claude
            try:
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic()

                # Build prompt for single file generation
                prompt = f"""Generate the complete content for this file:

File: {file_path}
Description: {description}

Project Context:
{plan.get('raw', '')[:2000]}

Generate ONLY the file content, no explanations. Output the complete, working code."""

                file_content = ""
                async with client.messages.stream(
                    model="claude-sonnet-4-20250514",
                    max_tokens=8000,
                    messages=[{"role": "user", "content": prompt}]
                ) as stream:
                    async for text in stream.text_stream:
                        file_content += text
                        yield {
                            "type": "file_chunk",
                            "data": {"path": file_path, "chunk": text}
                        }

                # Save file to all storage layers
                save_success = await self.save_file(
                    project_id=project_id,
                    file_path=file_path,
                    content=file_content,
                    user_id=user_id
                )

                if save_success:
                    # Update status to COMPLETED
                    try:
                        async with async_session() as db:
                            await db.execute(
                                update(ProjectFile)
                                .where(ProjectFile.project_id == UUID_type(str(project_id)))
                                .where(ProjectFile.path == file_path)
                                .values(generation_status=FileGenerationStatus.COMPLETED)
                            )
                            await db.commit()
                    except Exception as e:
                        logger.warning(f"[ResumeIncomplete] Could not update to COMPLETED: {e}")

                    yield {
                        "type": "file_complete",
                        "data": {
                            "path": file_path,
                            "size": len(file_content),
                            "saved": True
                        }
                    }
                    logger.info(f"[ResumeIncomplete] ✓ File completed: {file_path}")
                else:
                    # Update status to FAILED
                    try:
                        async with async_session() as db:
                            await db.execute(
                                update(ProjectFile)
                                .where(ProjectFile.project_id == UUID_type(str(project_id)))
                                .where(ProjectFile.path == file_path)
                                .values(generation_status=FileGenerationStatus.FAILED)
                            )
                            await db.commit()
                    except Exception as e:
                        logger.warning(f"[ResumeIncomplete] Could not update to FAILED: {e}")

                    yield {
                        "type": "file_error",
                        "data": {"path": file_path, "error": "Save failed"}
                    }

            except Exception as gen_err:
                logger.error(f"[ResumeIncomplete] Generation failed for {file_path}: {gen_err}")
                yield {
                    "type": "file_error",
                    "data": {"path": file_path, "error": str(gen_err)}
                }

        yield {
            "type": "resume_completed",
            "data": {
                "project_id": project_id,
                "message": f"Completed generation of {len(incomplete_files)} files"
            }
        }

    async def _execute_agent(
        self,
        agent_type: AgentType,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute a specific agent

        Args:
            agent_type: Which agent to execute
            context: Current execution context

        Yields:
            OrchestratorEvent: Events from agent execution
        """
        # Get agent configuration
        agent_config = self.agent_registry.get_agent(agent_type)

        if not agent_config or not agent_config.enabled:
            raise Exception(f"Agent {agent_type} not found or disabled")

        yield OrchestratorEvent(
            type=EventType.THINKING_STEP,
            data={
                "step": f"Calling {agent_config.name}",
                "status": "active"
            }
        )

        # Route to appropriate handler
        if agent_type == AgentType.PLANNER:
            async for event in self._execute_planner(agent_config, context):
                yield event
        elif agent_type == AgentType.WRITER:
            async for event in self._execute_writer(agent_config, context):
                yield event
        elif agent_type == AgentType.VERIFIER:
            async for event in self._execute_verifier(agent_config, context):
                yield event
        elif agent_type == AgentType.FIXER:
            async for event in self._execute_fixer(agent_config, context):
                yield event
        elif agent_type == AgentType.RUNNER:
            async for event in self._execute_runner(agent_config, context):
                yield event
        elif agent_type == AgentType.DOCUMENTER:
            async for event in self._execute_documenter(agent_config, context):
                yield event
        elif agent_type == AgentType.BOLT_INSTANT:
            # FAST: Single-call generator - combines planning + writing in one call
            async for event in self._execute_bolt_instant(agent_config, context):
                yield event
        else:
            raise Exception(f"No handler for agent type: {agent_type}")

    async def _execute_planner(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute planner agent with SAX-style streaming XML parser

        Architecture (Bolt.new):
        Claude Stream → SAX Parser → DOM Builder (on tag close) → Schema Validator → AST
        """

        # Build dynamic prompt
        system_prompt = config.system_prompt or self._get_default_planner_prompt()

        # Detect project complexity to control file generation
        complexity_info = self._detect_project_complexity(context.user_request)
        logger.info(f"[Planner] Complexity: {complexity_info['complexity']}, Max files: {complexity_info['max_files']}")

        # Build complexity-aware prompt (no hard file limits - planner decides)
        include_frontend = complexity_info.get('include_frontend', True)  # Default to True for backward compatibility
        complexity_hint = f"""
COMPLEXITY DETECTION RESULT:
- Detected Complexity: {complexity_info['complexity'].upper()}
- Recommended Stack: {complexity_info['recommended_stack']}
- Include Frontend: {'YES - Generate frontend/ folder with React/Vue/Angular' if include_frontend else 'NO - Backend only, no frontend files'}
- Include Backend: {'YES' if complexity_info['include_backend'] else 'NO'}
- Include Docker: {'YES' if complexity_info['include_docker'] else 'NO'}

IMPORTANT: Generate ALL files needed for a complete, working project.
Include every file that will be imported by other files.
Do not leave any imports pointing to non-existent files.
"""

        # Build color theme instruction if user specified colors
        color_instruction = self._build_color_instruction(context)

        user_prompt = f"""
USER REQUEST:
{context.user_request}
{color_instruction}
{complexity_hint}

PROJECT CONTEXT:
- Project ID: {context.project_id}
- Existing Files: {len(context.files_created)} files

Analyze this request and create a COMPLETE file list for the project.
Output in <plan> XML tags with <files> containing ALL needed files.
Ensure every import in every file has a corresponding file in the plan.
"""

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": f"Planning {complexity_info['complexity']} project structure..."}
        )

        # Initialize project directory BEFORE any file operations
        # Skip if using temp storage (session already created in execute_workflow)
        if not self.use_temp_storage:
            planner_user_id = context.metadata.get("user_id") if context.metadata else None
            await self.file_manager.create_project(context.project_id, f"Project {context.project_id}", user_id=planner_user_id)
            logger.info(f"[Planner] Initialized project directory: {context.project_id} for user {planner_user_id}")
        else:
            logger.info(f"[Planner] Using temp session: {context.metadata.get('session_id')}")

        # Initialize Bolt.new-style XML parser (lxml-based)
        xml_parser = BoltXMLParser(target_tag='plan')
        plan_dom = None
        plan_xml = None

        # Stream tokens from Claude with keepalive to prevent timeout
        logger.info("[Planner] Starting token stream with Bolt XML parser...")

        # Keepalive settings - send every 1 second to prevent any buffering/timeout issues
        # This is very aggressive but necessary to keep SSE connections alive
        # when Claude is thinking and not producing tokens
        PLANNER_KEEPALIVE_INTERVAL = 1.0  # seconds (very aggressive to prevent any timeout)
        chunk_count = 0
        keepalive_count = 0

        # Use asyncio.Queue for concurrent streaming + keepalive
        # This approach works because the queue.get() can properly timeout
        # unlike asyncio.wait_for on async generator __anext__()
        event_queue: asyncio.Queue = asyncio.Queue()
        streaming_done = asyncio.Event()

        async def stream_claude_chunks():
            """Background task to stream chunks from Claude into the queue"""
            nonlocal chunk_count
            try:
                async for chunk in self.claude_client.generate_stream(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    model=config.model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature
                ):
                    chunk_count += 1
                    await event_queue.put(("chunk", chunk))
                # Signal stream completion
                await event_queue.put(("done", None))
            except Exception as e:
                logger.error(f"[Planner] Claude streaming error: {e}")
                await event_queue.put(("error", str(e)))
            finally:
                streaming_done.set()

        async def send_keepalives():
            """Background task to send periodic keepalive events"""
            nonlocal keepalive_count
            while not streaming_done.is_set():
                try:
                    # Wait for interval or until streaming completes
                    await asyncio.wait_for(
                        streaming_done.wait(),
                        timeout=PLANNER_KEEPALIVE_INTERVAL
                    )
                    # If we get here, streaming completed - stop sending keepalives
                    break
                except asyncio.TimeoutError:
                    # Timeout means we should send a keepalive
                    keepalive_count += 1
                    logger.info(f"[Planner] Sending keepalive #{keepalive_count} (waiting for Claude, chunks: {chunk_count})")
                    await event_queue.put(("keepalive", keepalive_count))

        # Start background tasks
        stream_task = asyncio.create_task(stream_claude_chunks())
        keepalive_task = asyncio.create_task(send_keepalives())

        try:
            streaming_complete = False
            while not streaming_complete:
                try:
                    # Get next event from queue with timeout
                    event_type, event_data = await asyncio.wait_for(
                        event_queue.get(),
                        timeout=PLANNER_KEEPALIVE_INTERVAL * 3  # Longer timeout as backup
                    )

                    if event_type == "keepalive":
                        yield OrchestratorEvent(
                            type=EventType.STATUS,
                            data={
                                "message": f"Planning project structure... (analyzing)",
                                "keepalive": True,
                                "keepalive_count": event_data,
                                "chunks_received": chunk_count,
                                # Large padding (8KB) to force CloudFront HTTP/2 flush immediately
                                "_p": "." * 8192
                            }
                        )
                        continue

                    if event_type == "done":
                        streaming_complete = True
                        logger.info(f"[Planner] Streaming complete, received {chunk_count} chunks")
                        continue

                    if event_type == "error":
                        logger.error(f"[Planner] Stream error: {event_data}")
                        raise Exception(f"Claude streaming failed: {event_data}")

                    # Process chunk
                    chunk = event_data

                    # Check for token usage marker at end of stream
                    if chunk.startswith("__TOKEN_USAGE__:"):
                        parts = chunk.split(":")
                        if len(parts) >= 4:
                            input_tokens = int(parts[1])
                            output_tokens = int(parts[2])
                            model_used = parts[3]
                            context.track_tokens(
                                input_tokens, output_tokens, model_used,
                                agent_type="planner",
                                operation="plan_project"
                            )
                            logger.info(f"[Planner] Token usage tracked: {input_tokens}+{output_tokens}={input_tokens+output_tokens} ({model_used})")
                        continue  # Don't process marker as content

                    # Feed chunk to Bolt XML parser (incremental parsing with lxml)
                    xml_parser.feed(chunk)

                    # Check if <plan> tag has closed (DOM built automatically by lxml)
                    if plan_dom is None and xml_parser.has_complete_tag('plan'):
                        plan_dom = xml_parser.get_element('plan')  # lxml Element
                        plan_xml = xml_parser.get_text()

                        logger.info("[Bolt XML Parser] [OK] <plan> tag closed - DOM built with lxml")

                        # Validate DOM against schema
                        if plan_dom is not None:
                            # Convert lxml Element to string for validation
                            plan_xml_str = etree.tostring(plan_dom, encoding='unicode')
                            validation = PlanXMLSchema.validate(plan_xml_str)

                            if validation['valid']:
                                logger.info("[Schema] [OK] Plan DOM passed schema validation")
                            else:
                                logger.error(f"[Schema] [FAIL] Plan DOM failed validation: {validation['errors']}")

                            # Log warnings
                            for warning in validation.get('warnings', []):
                                logger.warning(f"[Schema] {warning}")

                            # Parse lxml DOM to extract data
                            parsed_data = self._parse_xml_from_lxml_dom(plan_dom)

                except asyncio.TimeoutError:
                    # Backup timeout - queue get timed out
                    keepalive_count += 1
                    logger.warning(f"[Planner] Queue timeout, sending backup keepalive #{keepalive_count}")
                    yield OrchestratorEvent(
                        type=EventType.STATUS,
                        data={
                            "message": f"Planning project structure... (waiting for AI)",
                            "keepalive": True,
                            "keepalive_count": keepalive_count,
                            "chunks_received": chunk_count,
                            # Large padding (8KB) to force CloudFront HTTP/2 flush immediately
                            "_p": "." * 8192
                        }
                    )

        finally:
            # Cleanup: cancel keepalive task and wait for stream task
            keepalive_task.cancel()
            try:
                await keepalive_task
            except asyncio.CancelledError:
                pass
            # Don't cancel stream_task - let it complete naturally or error out

        # If DOM wasn't built during streaming, try full buffer
        if plan_dom is None:
            logger.warning("[Planner] No complete <plan> tag found, parsing full buffer")
            full_text = xml_parser.get_text()
            parsed_data = self._parse_xml_plan(full_text)
            plan_xml = full_text

        # Store parsed plan - NEW: includes 'files' for file-by-file generation
        context.plan = {
            "raw": plan_xml or xml_parser.get_text(),
            "files": parsed_data.get('files', []),  # NEW: file list for file-by-file generation
            "tasks": parsed_data.get('tasks', []),  # Legacy: task list for backward compatibility
            "features": parsed_data.get('features', [])
        }

        # Determine if we're using file-based or task-based plan
        use_file_mode = len(context.plan['files']) > 0
        logger.info(f"[Planner] Plan mode: {'file-by-file' if use_file_mode else 'task-based'}")

        # Extract project_type
        # PRIORITY 1: Check user role from registration (student/faculty = academic)
        user_role = context.metadata.get("user_role", "").lower() if context.metadata else ""
        if user_role in ["student", "faculty"]:
            context.project_type = "Academic"
            logger.info(f"Detected academic project from user role: {user_role}")
        elif parsed_data.get('project_type'):
            project_type_text = parsed_data['project_type'].lower()
            # Detect project type from parsed text
            # Academic keywords: student project, college, university, B.Tech, M.Tech, MCA, PhD, thesis, etc.
            academic_keywords = [
                "academic", "student", "college", "university", "b.tech", "m.tech",
                "btech", "mtech", "mca", "bca", "phd", "thesis", "dissertation",
                "final year", "semester", "mini project", "major project", "capstone"
            ]
            if any(keyword in project_type_text for keyword in academic_keywords):
                context.project_type = "Academic"
            elif "commercial" in project_type_text:
                context.project_type = "Commercial"
            elif "research" in project_type_text:
                context.project_type = "Research"
            elif "prototype" in project_type_text or "mvp" in project_type_text:
                context.project_type = "Prototype"
            else:
                context.project_type = "General"

            logger.info(f"Detected project type: {context.project_type}")

        # Also check user prompt for academic keywords if project_type not set or is General
        if not context.project_type or context.project_type == "General":
            user_prompt_lower = context.user_request.lower()
            academic_prompt_keywords = [
                "student", "college", "university", "b.tech", "m.tech", "btech", "mtech",
                "mca", "bca", "final year", "semester", "academic", "project report",
                "documentation", "viva", "synopsis"
            ]
            if any(keyword in user_prompt_lower for keyword in academic_prompt_keywords):
                context.project_type = "Academic"
                logger.info(f"Detected academic project from user prompt")

        # Extract tech_stack
        if parsed_data.get('tech_stack'):
            context.tech_stack = parsed_data['tech_stack']
        else:
            context.tech_stack = {}

        # Extract project_name and project_description from Claude's plan
        project_name = parsed_data.get('project_name')
        project_description = parsed_data.get('project_description')
        complexity = parsed_data.get('complexity')
        features = context.plan.get('features', []) if context.plan else []

        if project_name:
            logger.info(f"[Planner] Claude suggested project name: '{project_name}' (len={len(project_name)})")
            # Validate project name - check for truncation issues
            if len(project_name) < 3:
                logger.warning(f"[Planner] Project name too short: '{project_name}' - possible truncation")
            context.project_name = project_name  # Save to context for DOCUMENTER
        else:
            # Fallback: extract from user request only if Claude didn't suggest one
            project_name = self._extract_project_name_from_request(context.user_request)
            logger.info(f"[Planner] [FALLBACK] Extracted project name from request: '{project_name}'")
            context.project_name = project_name
        
        # Save project metadata to context for downstream use (DOCUMENTER, etc.)
        if project_description:
            context.project_description = project_description
        context.features = features

        # CRITICAL: Update project metadata in database IMMEDIATELY after planner completes
        # This includes plan_json which is REQUIRED for resume functionality
        # NOTE: We save even if project_name is not extracted - plan_json is more important
        if context.project_id:
            # ============================================================
            # STEP 1: Save project metadata (title, description, plan_json)
            # ============================================================
            # CRITICAL: This MUST succeed to enable resume functionality
            project_saved = False
            max_save_retries = 3

            for save_attempt in range(max_save_retries):
                try:
                    from app.core.database import async_session
                    from app.models.project import Project
                    from sqlalchemy import update
                    from uuid import UUID as UUID_type

                    # Convert project_id to UUID for proper matching
                    try:
                        project_uuid = UUID_type(str(context.project_id))
                    except (ValueError, TypeError) as uuid_err:
                        logger.error(f"[Planner] Invalid project_id format: {context.project_id} - {uuid_err}")
                        break  # Can't proceed without valid UUID

                    async with async_session() as db:
                        # Build update values - plan_json is ALWAYS included if available
                        update_values = {}

                        # Project name (optional but nice to have)
                        if project_name:
                            update_values['title'] = project_name
                            logger.info(f"[Planner] Saving title to DB: '{project_name}' (first_char='{project_name[0] if project_name else 'N/A'}')")

                        # Project description (optional)
                        if project_description:
                            update_values['description'] = project_description

                        # CRITICAL: Save plan_json to database for resume functionality
                        # This is REQUIRED - without this, resume will fail with "no_plan" error
                        if context.plan:
                            update_values['plan_json'] = context.plan
                            logger.info(f"[Planner] Saving plan_json to DB (attempt {save_attempt + 1}): {len(context.plan.get('files', []))} files, {len(context.plan.get('features', []))} features")
                        else:
                            logger.warning(f"[Planner] No plan to save for project {context.project_id}")

                        # Skip DB update if no values to update
                        if not update_values:
                            logger.warning(f"[Planner] No values to update for project {context.project_id}")
                            break

                        result = await db.execute(
                            update(Project)
                            .where(Project.id == project_uuid)
                            .values(**update_values)
                        )
                        await db.commit()

                        # Check if any rows were updated
                        if result.rowcount == 0:
                            logger.warning(f"[Planner] No rows updated for project {project_uuid} - project may not exist in DB")
                            # Try one more thing - maybe project_id doesn't match
                            logger.info(f"[Planner] Checking if project exists with id={project_uuid}")
                        else:
                            project_saved = True
                            logger.info(f"[Planner] ✓ Plan saved to DB: title='{project_name or 'untitled'}', files={len(context.plan.get('files', []))}, rows_affected={result.rowcount}")
                            break  # Success, exit retry loop

                except Exception as e:
                    logger.error(f"[Planner] ✗ Failed to update project metadata (attempt {save_attempt + 1}/{max_save_retries}): {e}", exc_info=True)
                    if save_attempt < max_save_retries - 1:
                        await asyncio.sleep(1)  # Wait before retry
                    # Continue to next retry attempt

            if not project_saved:
                logger.error(f"[Planner] CRITICAL: Failed to save plan_json after {max_save_retries} attempts for project {context.project_id}")
                # Emit warning event so user knows resume might not work
                yield OrchestratorEvent(
                    type=EventType.WARNING,
                    data={
                        "message": "Plan save failed - Resume may not work if disconnected. Please wait for generation to complete.",
                        "critical": True,
                        "can_resume": False
                    }
                )

            # ============================================================
            # STEP 2: Save planned files to ProjectFile table (separate transaction)
            # This is in a separate try block so project metadata save doesn't affect it
            # ============================================================
            if project_saved and context.plan and context.plan.get('files'):
                try:
                    from app.core.database import async_session
                    from app.models.project_file import ProjectFile, FileGenerationStatus
                    from sqlalchemy import select

                    async with async_session() as db:
                        planned_files = context.plan['files']
                        files_saved = 0
                        files_failed = 0

                        for order, file_info in enumerate(planned_files, 1):
                            try:
                                file_path = file_info.get('path', '')
                                if not file_path:
                                    continue

                                # Validate file path
                                if '..' in file_path or file_path.startswith('/'):
                                    logger.warning(f"[Planner] Skipping invalid file path: {file_path}")
                                    continue

                                file_name = file_path.split('/')[-1]
                                if not file_name:
                                    continue

                                # Check if file already exists
                                existing = await db.execute(
                                    select(ProjectFile)
                                    .where(ProjectFile.project_id == context.project_id)
                                    .where(ProjectFile.path == file_path)
                                )
                                existing_file = existing.scalar_one_or_none()

                                if existing_file:
                                    # Update existing to PLANNED status
                                    existing_file.generation_status = FileGenerationStatus.PLANNED
                                    existing_file.generation_order = order
                                else:
                                    # Create new file record with PLANNED status
                                    planned_file = ProjectFile(
                                        project_id=context.project_id,
                                        path=file_path,
                                        name=file_name,
                                        language=self._unified_storage._detect_language(file_name),
                                        generation_status=FileGenerationStatus.PLANNED,
                                        generation_order=order,
                                        is_folder=False,
                                        size_bytes=0
                                    )
                                    db.add(planned_file)
                                files_saved += 1

                            except Exception as file_err:
                                files_failed += 1
                                logger.warning(f"[Planner] Failed to save planned file {file_info.get('path', 'unknown')}: {file_err}")
                                continue  # Continue with next file

                        # Commit all file records
                        await db.commit()
                        logger.info(f"[Planner] ✓ Saved {files_saved} planned files to DB (failed: {files_failed})")

                        # Store planned files count in context for progress tracking
                        context.metadata['total_planned_files'] = files_saved

                except Exception as e:
                    logger.error(f"[Planner] ✗ Failed to save planned files to DB: {e}", exc_info=True)
                    # Continue generation even if file tracking fails

        # NEW: Handle file-based plan format
        if use_file_mode:
            # File-by-file mode: Each file becomes a "task" for the frontend
            logger.info(f"[OK] Extracted {len(context.plan['files'])} files from plan (file-by-file mode)")

            # Send plan created event with file list AND workflow steps as tasks
            # This allows UI to show all workflow steps (Plan, Write, Verify, Run, Fix, Docs)
            yield OrchestratorEvent(
                type=EventType.PLAN_CREATED,
                data={
                    "plan": context.plan,
                    "project_name": project_name,
                    "project_description": project_description,
                    "project_type": context.project_type,
                    "complexity": complexity,
                    "tech_stack": context.tech_stack,
                    "files": context.plan['files'],  # File list for file operations display
                    "features": context.plan['features'],
                    "tasks": context.workflow_steps,  # Workflow steps for UI task list (Plan, Write, Verify, Run, Fix, Docs)
                    "mode": "file-by-file"  # Signal to frontend
                }
            )
            logger.info(f"[PLAN_CREATED] Event yielded with {len(context.plan['files'])} files AND {len(context.workflow_steps)} workflow tasks (file-by-file mode)")

        else:
            # Legacy task-based mode
            logger.info(f"[OK] Extracted {len(context.plan.get('tasks', []))} tasks from plan using XML AST")

            # Enrich tasks with description and details
            enriched_tasks = []
            for task in context.plan.get('tasks', []):
                full_name = task.get('name', '')
                parts = full_name.split(' - ', 1)
                task_title = parts[0].strip()
                task_description = parts[1].strip() if len(parts) > 1 else full_name

                enriched_task = {
                    **task,
                    "title": task_title,
                    "description": task_description,
                    "details": f"{task_description}\n\nFiles will be generated and saved incrementally."
                }
                enriched_tasks.append(enriched_task)

            # Update context with enriched tasks
            if context.plan:
                context.plan['tasks'] = enriched_tasks

            # Send plan created event with workflow steps as tasks (NOT Claude's plan tasks)
            # UI should show workflow steps: Plan → Write → Verify → Run → Fix → Docs
            yield OrchestratorEvent(
                type=EventType.PLAN_CREATED,
                data={
                    "plan": context.plan,
                    "project_name": project_name,
                    "project_type": context.project_type,
                    "tech_stack": context.tech_stack,
                    "tasks": context.workflow_steps,  # Workflow steps for UI task list
                    "plan_tasks": enriched_tasks,  # Claude's plan tasks for reference
                    "mode": "task-based"  # Signal to frontend
                }
            )
            logger.info(f"[PLAN_CREATED] Event yielded with {len(context.workflow_steps)} workflow tasks (task-based mode)")

        # Small delay to ensure frontend processes plan_created before individual events
        await asyncio.sleep(0.1)

    async def _execute_writer(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute writer agent - FILE-BY-FILE generation like Bolt.new

        NEW: If plan has 'files' list, generates ONE FILE at a time per API call.
        This avoids token limits and ensures complete files every time.

        Flow:
        - Plan has files list: Call writer once per file (file-by-file mode)
        - Plan has tasks list: Call writer once per task (legacy mode)
        """

        system_prompt = config.system_prompt or self._get_default_writer_prompt()

        # Check if we're in file-by-file mode (NEW) or task-based mode (legacy)
        files_to_generate = context.plan.get('files', []) if context.plan else []
        tasks = context.plan.get('tasks', []) if context.plan else []

        # ============================================================
        # RESUME HANDLING: Filter out already completed files
        # When resuming, only generate files that haven't been completed
        # ============================================================
        is_resume = context.metadata.get('is_resume', False)
        if is_resume and files_to_generate:
            # Get list of already completed files from metadata
            existing_file_paths = set(context.metadata.get('existing_files', []))
            pending_file_paths = set(context.metadata.get('pending_files', []))

            if existing_file_paths or pending_file_paths:
                # Filter to only pending files (using either explicit pending list or excluding existing)
                if pending_file_paths:
                    # Use explicit pending list if available
                    files_to_generate = [f for f in files_to_generate if f.get('path') in pending_file_paths]
                else:
                    # Otherwise exclude existing files
                    files_to_generate = [f for f in files_to_generate if f.get('path') not in existing_file_paths]

                logger.info(f"[Writer-Resume] Filtered to {len(files_to_generate)} pending files (skipping {len(existing_file_paths)} completed)")

            # Also query database for files that need generation (PLANNED or FAILED status)
            if not files_to_generate:
                try:
                    from app.core.database import AsyncSessionLocal
                    from app.models.project_file import ProjectFile, FileGenerationStatus
                    from sqlalchemy import select

                    async with AsyncSessionLocal() as session:
                        result = await session.execute(
                            select(ProjectFile)
                            .where(ProjectFile.project_id == context.project_id)
                            .where(ProjectFile.generation_status.in_([
                                FileGenerationStatus.PLANNED,
                                FileGenerationStatus.FAILED,
                                FileGenerationStatus.GENERATING  # Retry files that were in progress when interrupted
                            ]))
                            .order_by(ProjectFile.generation_order.asc())
                        )
                        pending_db_files = result.scalars().all()

                        if pending_db_files:
                            files_to_generate = [
                                {"path": f.path, "description": f"Resume: {f.name}"}
                                for f in pending_db_files
                            ]
                            logger.info(f"[Writer-Resume] Found {len(files_to_generate)} pending files from database")

                except Exception as db_err:
                    logger.warning(f"[Writer-Resume] Database query failed, using plan files: {db_err}")

        # PARALLEL FILE GENERATION MODE (FAST - generates 3 files at a time)
        PARALLEL_BATCH_SIZE = 3  # Generate 3 files concurrently

        if files_to_generate:
            logger.info(f"[Writer] ⚡ Parallel mode: generating {len(files_to_generate)} files ({PARALLEL_BATCH_SIZE} at a time)")

            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={
                    "message": f"Generating {len(files_to_generate)} files ({PARALLEL_BATCH_SIZE} in parallel)...",
                    "total_files": len(files_to_generate),
                    "mode": "parallel",
                    "batch_size": PARALLEL_BATCH_SIZE
                }
            )

            # REAL-TIME EVENT STREAMING: Use queue to yield events immediately
            # instead of collecting them (which caused 30s timeout)
            event_queue: asyncio.Queue = asyncio.Queue()

            # Helper function to generate a single file and stream events to queue
            async def generate_single_file(file_info: Dict, file_index: int) -> Dict:
                """Generate a single file and stream events to queue in real-time"""
                file_path = file_info.get('path', '')
                file_description = file_info.get('description', '')
                success = False
                file_content = ""
                error_msg = None

                if not file_path:
                    return {"success": False, "file_path": ""}

                try:
                    # Mark as generating
                    await self.update_file_generation_status(
                        project_id=context.project_id,
                        file_path=file_path,
                        status="generating"
                    )

                    # Stream events to queue in REAL-TIME (not collecting!)
                    async for event in self._execute_writer_for_single_file(
                        config, context, file_path, file_description, system_prompt
                    ):
                        await event_queue.put(("event", event))

                    # Get file content
                    for fc in reversed(context.files_created):
                        if fc.get('path') == file_path:
                            file_content = fc.get('content', '')
                            break

                    # Mark as completed
                    await self.update_file_generation_status(
                        project_id=context.project_id,
                        file_path=file_path,
                        status="completed",
                        size_bytes=len(file_content.encode('utf-8')) if file_content else 0
                    )
                    success = True

                except Exception as e:
                    logger.error(f"[Writer] Error generating {file_path}: {e}")
                    error_msg = str(e)
                    await self.update_file_generation_status(
                        project_id=context.project_id,
                        file_path=file_path,
                        status="failed"
                    )

                return {
                    "success": success,
                    "file_path": file_path,
                    "file_content": file_content,
                    "file_index": file_index,
                    "error": error_msg
                }

            # Process files in batches
            total_files = len(files_to_generate)
            for batch_start in range(0, total_files, PARALLEL_BATCH_SIZE):
                batch_end = min(batch_start + PARALLEL_BATCH_SIZE, total_files)
                batch_files = files_to_generate[batch_start:batch_end]
                batch_indices = list(range(batch_start + 1, batch_end + 1))

                # Emit batch start
                file_paths_in_batch = [f.get('path', '') for f in batch_files]
                yield OrchestratorEvent(
                    type=EventType.STATUS,
                    data={
                        "message": f"Generating batch {batch_start//PARALLEL_BATCH_SIZE + 1}: {', '.join(file_paths_in_batch[:3])}...",
                        "batch_files": file_paths_in_batch,
                        "batch_start": batch_start + 1,
                        "batch_end": batch_end,
                        "total_files": total_files
                    }
                )

                # Emit file start events for all files in batch
                for i, file_info in enumerate(batch_files):
                    file_path = file_info.get('path', '')
                    file_index = batch_start + i + 1
                    yield OrchestratorEvent(
                        type=EventType.FILE_OPERATION,
                        data={
                            "operation": "create",
                            "path": file_path,
                            "operation_status": "in_progress",
                            "file_number": file_index,
                            "total_files": total_files,
                            "description": file_info.get('description', ''),
                            "generation_status": "generating"
                        }
                    )

                # Generate all files in batch IN PARALLEL with REAL-TIME event streaming
                # Use create_task + queue to yield events as they happen (not after batch)
                batch_done = asyncio.Event()
                active_tasks = []
                batch_results = []

                async def run_and_store_result(file_info: Dict, file_index: int):
                    """Run file generation and store result"""
                    result = await generate_single_file(file_info, file_index)
                    batch_results.append(result)
                    return result

                # Start all file generation tasks
                for i, file_info in enumerate(batch_files):
                    task = asyncio.create_task(
                        run_and_store_result(file_info, batch_start + i + 1)
                    )
                    active_tasks.append(task)

                # Signal when all tasks complete
                async def signal_batch_done():
                    await asyncio.gather(*active_tasks, return_exceptions=True)
                    await event_queue.put(("batch_done", None))

                asyncio.create_task(signal_batch_done())

                # Read from queue and yield events in REAL-TIME
                batch_complete = False
                while not batch_complete:
                    try:
                        msg_type, msg_data = await asyncio.wait_for(
                            event_queue.get(),
                            timeout=10.0  # Keepalive timeout - reduced from 15s to 10s
                        )

                        if msg_type == "batch_done":
                            batch_complete = True
                        elif msg_type == "event":
                            yield msg_data

                    except asyncio.TimeoutError:
                        # Send keepalive if queue is empty for too long
                        yield OrchestratorEvent(
                            type=EventType.STATUS,
                            data={
                                "message": f"Generating files... (batch {batch_start//PARALLEL_BATCH_SIZE + 1})",
                                "keepalive": True,
                                "batch": batch_start//PARALLEL_BATCH_SIZE + 1,
                                # Large padding (8KB) to force CloudFront HTTP/2 flush immediately
                                "_p": "." * 8192
                            }
                        )

                # Process results for completion events
                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"[Writer] Batch task failed: {result}")
                        continue

                    file_path = result.get("file_path", "")
                    file_index = result.get("file_index", 0)

                    # Yield completion or error event
                    if result.get("success"):
                        yield OrchestratorEvent(
                            type=EventType.FILE_OPERATION,
                            data={
                                "operation": "create",
                                "path": file_path,
                                "operation_status": "complete",
                                "file_content": result.get("file_content", ""),
                                "file_number": file_index,
                                "total_files": total_files,
                                "generation_status": "completed"
                            }
                        )
                    else:
                        yield OrchestratorEvent(
                            type=EventType.ERROR,
                            data={
                                "message": f"Failed to generate {file_path}",
                                "error": result.get("error", "Unknown error"),
                                "file_path": file_path,
                                "generation_status": "failed"
                            }
                        )

                # Small delay between batches for rate limiting
                if batch_end < total_files:
                    await asyncio.sleep(0.5)

            # ============================================================
            # RETRY FAILED SAVES: Try to save files that failed initially
            # This handles transient S3/DB errors during generation
            # ============================================================
            failed_saves = [f for f in context.files_created if f.get('saved') == False]
            if failed_saves:
                logger.info(f"[Writer] Retrying {len(failed_saves)} files that failed to save...")

                for retry_file in failed_saves:
                    try:
                        retry_path = retry_file.get('path', '')
                        retry_content = retry_file.get('content', '')

                        if retry_path and retry_content:
                            retry_success = await self.save_file(
                                project_id=context.project_id,
                                file_path=retry_path,
                                content=retry_content,
                                session_id=context.metadata.get("session_id"),
                                user_id=context.metadata.get("user_id")
                            )

                            if retry_success:
                                retry_file['saved'] = True
                                logger.info(f"[Writer] ✓ Retry successful for: {retry_path}")

                                # Update file status to completed
                                await self.update_file_generation_status(
                                    project_id=context.project_id,
                                    file_path=retry_path,
                                    status="completed",
                                    size_bytes=len(retry_content.encode('utf-8'))
                                )
                            else:
                                logger.warning(f"[Writer] ✗ Retry failed for: {retry_path}")
                                # Mark as failed so resume can pick it up
                                await self.update_file_generation_status(
                                    project_id=context.project_id,
                                    file_path=retry_path,
                                    status="failed"
                                )
                    except Exception as retry_err:
                        logger.error(f"[Writer] Error during save retry: {retry_err}")

                # Count final results
                still_failed = [f for f in context.files_created if f.get('saved') == False]
                if still_failed:
                    logger.warning(f"[Writer] {len(still_failed)} files still failed after retry")
                    yield OrchestratorEvent(
                        type=EventType.WARNING,
                        data={
                            "message": f"{len(still_failed)} files could not be saved. You can use Resume to retry.",
                            "failed_files": [f.get('path') for f in still_failed],
                            "can_resume": True
                        }
                    )

            logger.info(f"[Writer] ✓ File-by-file generation complete: {len(context.files_created)} files created")
            return

        # TASK-BASED MODE (Legacy - for backward compatibility)
        if not tasks:
            # Fallback: execute writer once for entire request
            logger.warning("No tasks or files found in plan, executing writer for full request")
            async for event in self._execute_writer_for_task(config, context, None, system_prompt):
                yield event
            return

        # Execute writer for each task
        for task_index, task in enumerate(tasks, 1):
            task_title = task.get('title', task.get('name', ''))
            task_description = task.get('description', task.get('name', ''))

            files_created_so_far = len(context.files_created)
            progress_details = f"**Step {task['number']}**: {task_description}\n\n**Files created so far**: {files_created_so_far}\n\nGenerating files incrementally..."

            yield OrchestratorEvent(
                type=EventType.AGENT_START,
                data={
                    "name": task_title,
                    "status": "active",
                    "agent": "writer",
                    "task_number": task['number'],
                    "description": task_description,
                    "details": progress_details
                }
            )

            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": f"Working on {task_title}..."}
            )

            task_files_count_before = len(context.files_created)
            async for event in self._execute_writer_for_task(config, context, task, system_prompt):
                yield event
            task_files_count_after = len(context.files_created)

            files_created_in_task = task_files_count_after - task_files_count_before
            files_in_this_task = context.files_created[task_files_count_before:task_files_count_after]
            file_paths = [f.get('path', 'unknown') for f in files_in_this_task]

            completion_details = self._build_task_completion_details(
                task_title=task_title,
                task_description=task_description,
                task_number=task['number'],
                files_created=file_paths,
                total_files=task_files_count_after
            )

            yield OrchestratorEvent(
                type=EventType.AGENT_COMPLETE,
                data={
                    "name": task_title,
                    "status": "complete",
                    "agent": "writer",
                    "task_number": task['number'],
                    "description": task_description,
                    "details": completion_details,
                    "files_created": file_paths,
                    "files_count": files_created_in_task,
                    "total_files": task_files_count_after
                }
            )

            await asyncio.sleep(0.5)

    async def _execute_writer_for_single_file(
        self,
        config: AgentConfig,
        context: ExecutionContext,
        file_path: str,
        file_description: str,
        system_prompt: str
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute writer agent for a SINGLE FILE (NEW - file-by-file mode)

        This is the key to avoiding token limits:
        - One API call per file
        - Max ~8K output tokens per file (plenty for any single file)
        - No risk of truncation or incomplete files

        TIMEOUT PROTECTION:
        - Each file has a maximum generation time (SINGLE_FILE_GENERATION_TIMEOUT)
        - If timeout occurs, file is marked as FAILED for resume to pick up
        - Prevents indefinite hangs on complex files like cart.tsx
        """

        # Build color theme instruction if user specified colors
        color_instruction = self._build_color_instruction(context)

        # Build prompt for single file generation
        user_prompt = f"""
FILE TO GENERATE:
Path: {file_path}
Description: {file_description}
{color_instruction}
PROJECT CONTEXT:
User Request: {context.user_request}
Project Type: {context.project_type or 'Web Application'}
Tech Stack: {json.dumps(context.tech_stack) if context.tech_stack else 'React + TypeScript + Tailwind'}

FILES ALREADY CREATED:
{chr(10).join([f"- {f.get('path', 'unknown')}" for f in context.files_created[-10:]]) if context.files_created else "None yet"}

Generate ONLY the file: {file_path}
Output using <file path="{file_path}">CONTENT</file> format.
Make sure the file is COMPLETE and PRODUCTION-READY.
"""

        # Initialize Bolt streaming buffer
        streaming_buffer = BoltStreamingBuffer(tag='file')

        logger.info(f"[Writer] Generating single file: {file_path} (timeout: {SINGLE_FILE_GENERATION_TIMEOUT}s)")

        # Track time for keepalive events
        # CloudFront has a 60-second origin read timeout, but browser EventSource may timeout earlier
        # IMPORTANT: Send keepalive every 10 seconds to prevent 30s browser disconnects
        # NOTE: We track time since last YIELDED event (not since last received chunk)
        # because Claude streams tokens continuously but we only yield when file is complete
        import time
        last_event_time = time.time()
        generation_start_time = time.time()
        KEEPALIVE_INTERVAL = 10  # seconds - reduced from 25s to prevent 30s browser timeout
        file_generated = False

        try:
            # Wrap file generation with timeout to prevent indefinite hangs
            async with asyncio.timeout(SINGLE_FILE_GENERATION_TIMEOUT):
                async for chunk in self.claude_client.generate_stream(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    model=config.model,
                    max_tokens=config.max_tokens,
                    temperature=config.temperature
                ):
                    # Check if we need to send keepalive (time since last yielded event)
                    current_time = time.time()
                    if current_time - last_event_time >= KEEPALIVE_INTERVAL:
                        last_event_time = current_time
                        logger.info(f"[Writer] Sending keepalive during {file_path} generation")
                        yield OrchestratorEvent(
                            type=EventType.STATUS,
                            data={
                                "message": f"Generating {file_path}...",
                                "file": file_path,
                                "keepalive": True,
                                # Large padding (8KB) to force CloudFront HTTP/2 flush immediately
                                # CloudFront buffers small HTTP/2 DATA frames, causing 30s timeout
                                "_p": "." * 8192
                            }
                        )
                    # Check for token usage marker at end of stream
                    if chunk.startswith("__TOKEN_USAGE__:"):
                        parts = chunk.split(":")
                        if len(parts) >= 4:
                            input_tokens = int(parts[1])
                            output_tokens = int(parts[2])
                            model_used = parts[3]
                            context.track_tokens(
                                input_tokens, output_tokens, model_used,
                                agent_type="writer",
                                operation="generate_file",
                                file_path=file_path
                            )
                            logger.info(f"[Writer] Token usage tracked: {input_tokens}+{output_tokens}={input_tokens+output_tokens} ({model_used})")
                        continue  # Don't process marker as content

                    # Feed chunk to buffer and extract complete files
                    complete_files = streaming_buffer.feed_chunk(chunk)

                    for file_data in complete_files:
                        extracted_path = file_data['path']
                        file_content = file_data['content']
                        file_generated = True

                        # Save file immediately (uses temp storage if enabled)
                        session_id = context.metadata.get("session_id")
                        user_id = context.metadata.get("user_id")

                        # ============================================================
                        # INCREMENTAL SAVE: Update status to GENERATING before save
                        # This ensures we can resume from this point if disconnected
                        # ============================================================
                        try:
                            from app.core.database import async_session
                            from app.models.project_file import ProjectFile, FileGenerationStatus
                            from sqlalchemy import update
                            from uuid import UUID as UUID_type

                            async with async_session() as status_db:
                                await status_db.execute(
                                    update(ProjectFile)
                                    .where(ProjectFile.project_id == UUID_type(str(context.project_id)))
                                    .where(ProjectFile.path == extracted_path)
                                    .values(generation_status=FileGenerationStatus.GENERATING)
                                )
                                await status_db.commit()
                        except Exception as status_err:
                            logger.warning(f"[Writer] Could not update status to GENERATING: {status_err}")

                        # CRITICAL: Check if save was successful
                        save_success = await self.save_file(
                            project_id=context.project_id,
                            file_path=extracted_path,
                            content=file_content,
                            session_id=session_id,
                            user_id=user_id
                        )

                        if save_success:
                            context.files_created.append({
                                'path': extracted_path,
                                'content': file_content,
                                'saved': True
                            })

                            # ============================================================
                            # INCREMENTAL SAVE: Update status to COMPLETED after save
                            # File is now safely stored in S3 and can be restored
                            # ============================================================
                            try:
                                async with async_session() as status_db:
                                    await status_db.execute(
                                        update(ProjectFile)
                                        .where(ProjectFile.project_id == UUID_type(str(context.project_id)))
                                        .where(ProjectFile.path == extracted_path)
                                        .values(generation_status=FileGenerationStatus.COMPLETED)
                                    )
                                    await status_db.commit()
                                logger.info(f"[Writer] ✓ File status COMPLETED: {extracted_path}")
                            except Exception as status_err:
                                logger.warning(f"[Writer] Could not update status to COMPLETED: {status_err}")

                            # Emit file content event with project_id for proper isolation
                            yield OrchestratorEvent(
                                type=EventType.FILE_CONTENT,
                                data={
                                    "path": extracted_path,
                                    "content": file_content,
                                    "status": "complete",
                                    "project_id": context.project_id  # For file isolation in frontend
                                }
                            )
                            # Reset keepalive timer after yielding an event
                            last_event_time = time.time()
                            logger.info(f"[Writer] ✓ File saved: {extracted_path} ({len(file_content)} chars)")
                        else:
                            # Save failed - still add to context but mark as not saved
                            context.files_created.append({
                                'path': extracted_path,
                                'content': file_content,
                                'saved': False
                            })

                            # Emit warning but don't fail the entire generation
                            yield OrchestratorEvent(
                                type=EventType.WARNING,
                                data={
                                    "message": f"File {extracted_path} generated but save failed - will retry",
                                    "path": extracted_path,
                                    "can_retry": True
                                }
                            )
                            last_event_time = time.time()
                            logger.warning(f"[Writer] ✗ File generated but save failed: {extracted_path}")

            # Log successful generation
            generation_time = time.time() - generation_start_time
            logger.info(f"[Writer] ✓ File {file_path} generated in {generation_time:.1f}s")

        except asyncio.TimeoutError:
            # ============================================================
            # TIMEOUT HANDLING: Mark file as FAILED for resume to pick up
            # This prevents indefinite hangs on complex files
            # ============================================================
            generation_time = time.time() - generation_start_time
            logger.error(f"[Writer] ✗ TIMEOUT generating {file_path} after {generation_time:.1f}s (limit: {SINGLE_FILE_GENERATION_TIMEOUT}s)")

            # Mark file as FAILED in database so resume can regenerate it
            try:
                from app.core.database import async_session
                from app.models.project_file import ProjectFile, FileGenerationStatus
                from sqlalchemy import update
                from uuid import UUID as UUID_type

                async with async_session() as status_db:
                    await status_db.execute(
                        update(ProjectFile)
                        .where(ProjectFile.project_id == UUID_type(str(context.project_id)))
                        .where(ProjectFile.path == file_path)
                        .values(generation_status=FileGenerationStatus.FAILED)
                    )
                    await status_db.commit()
                logger.info(f"[Writer] Marked {file_path} as FAILED for resume")
            except Exception as status_err:
                logger.warning(f"[Writer] Could not mark file as FAILED: {status_err}")

            # Emit timeout error event
            yield OrchestratorEvent(
                type=EventType.WARNING,
                data={
                    "message": f"File {file_path} generation timed out after {SINGLE_FILE_GENERATION_TIMEOUT}s. Use Resume to retry.",
                    "path": file_path,
                    "timeout": True,
                    "can_resume": True
                }
            )

            # Don't raise - continue with next file
            return

        # Check for incomplete file in buffer
        if streaming_buffer.has_partial_tag():
            partial_buffer = streaming_buffer.get_buffer()
            logger.warning(f"[Writer] Partial file detected for {file_path}, attempting salvage...")

            # Try to salvage partial content
            if '<file path="' in partial_buffer:
                try:
                    path_start = partial_buffer.find('<file path="') + len('<file path="')
                    path_end = partial_buffer.find('"', path_start)
                    if path_end > path_start:
                        partial_path = partial_buffer[path_start:path_end]
                        content_start = partial_buffer.find('>', path_end) + 1
                        partial_content = partial_buffer[content_start:] if content_start > 0 else ""

                        if partial_content.strip():
                            cleaned_content = partial_content.strip('\n')
                            salvaged_content = f"// WARNING: This file may be incomplete\n{cleaned_content}"

                            # Check save result for partial file
                            salvage_success = await self.save_file(
                                project_id=context.project_id,
                                file_path=partial_path,
                                content=salvaged_content,
                                session_id=context.metadata.get("session_id"),
                                user_id=context.metadata.get("user_id")
                            )

                            context.files_created.append({
                                'path': partial_path,
                                'content': salvaged_content,
                                'partial': True,
                                'saved': salvage_success
                            })

                            yield OrchestratorEvent(
                                type=EventType.WARNING,
                                data={
                                    "message": f"File {partial_path} may be incomplete" + (" (save failed)" if not salvage_success else ""),
                                    "path": partial_path,
                                    "partial": True,
                                    "saved": salvage_success
                                }
                            )
                except Exception as e:
                    logger.error(f"[Writer] Failed to salvage partial file: {e}")

    async def _execute_writer_for_task(
        self,
        config: AgentConfig,
        context: ExecutionContext,
        task: Optional[Dict[str, Any]],
        system_prompt: str
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """Execute writer agent for a single task"""

        # Build color theme instruction if user specified colors
        color_instruction = self._build_color_instruction(context)

        if task:
            user_prompt = f"""
CURRENT TASK:
Step {task['number']}: {task['name']}

FULL PLAN CONTEXT:
{context.plan.get('raw', 'No plan available')}

USER REQUEST:
{context.user_request}
{color_instruction}
Generate ONLY the files needed for THIS SPECIFIC TASK (Step {task['number']}).
Use <file path="...">CONTENT</file> tags.
Do NOT generate files for other steps - focus only on Step {task['number']}.
"""
        else:
            user_prompt = f"""
TASK:
{context.user_request}
{color_instruction}
PLAN:
{context.plan.get('raw', 'No plan available') if context.plan else 'No plan available'}

Generate files using <file path="...">CONTENT</file> tags.
Stream code in chunks for real-time display.
"""

        # Initialize Bolt streaming buffer (EXACT Bolt.new technique)
        streaming_buffer = BoltStreamingBuffer(tag='file')

        # Capture full response to extract plan block (project_name, description)
        full_response_buffer = ""
        plan_extracted = False

        logger.info("[Writer] Starting streaming with Bolt buffer...")

        async for chunk in self.claude_client.generate_stream(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=config.model,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        ):
            # Check for token usage marker at end of stream
            if chunk.startswith("__TOKEN_USAGE__:"):
                parts = chunk.split(":")
                if len(parts) >= 4:
                    input_tokens = int(parts[1])
                    output_tokens = int(parts[2])
                    model_used = parts[3]
                    context.track_tokens(
                        input_tokens, output_tokens, model_used,
                        agent_type="writer",
                        operation="generate_batch"
                    )
                    logger.info(f"[Writer] Token usage tracked: {input_tokens}+{output_tokens}={input_tokens+output_tokens} ({model_used})")
                continue  # Don't process marker as content

            # Accumulate full response for plan extraction
            full_response_buffer += chunk

            # Extract plan block (project_name, description) as soon as it's complete
            # This runs only once when </plan> is found
            if not plan_extracted and "</plan>" in full_response_buffer:
                try:
                    plan_start = full_response_buffer.find("<plan>")
                    plan_end = full_response_buffer.find("</plan>") + len("</plan>")
                    if plan_start >= 0 and plan_end > plan_start:
                        plan_block = full_response_buffer[plan_start:plan_end]

                        # Extract project_name
                        name_match = re.search(r'<project_name>([^<]+)</project_name>', plan_block)
                        if name_match:
                            context.project_name = name_match.group(1).strip()
                            logger.info(f"[Writer] Extracted project_name from plan: {context.project_name}")

                        # Extract description
                        desc_match = re.search(r'<description>([^<]+)</description>', plan_block)
                        if desc_match:
                            context.project_description = desc_match.group(1).strip()
                            logger.info(f"[Writer] Extracted description from plan: {context.project_description[:50]}...")

                        # Extract tech_stack
                        tech_match = re.search(r'<tech_stack>([^<]+)</tech_stack>', plan_block)
                        if tech_match:
                            context.tech_stack = {"stack": tech_match.group(1).strip()}
                            logger.info(f"[Writer] Extracted tech_stack from plan: {context.tech_stack}")

                        plan_extracted = True

                        # CRITICAL: Update project title in database IMMEDIATELY
                        # This fixes the bug where dropdown shows "New App" instead of actual project name
                        if context.project_name and context.project_id:
                            try:
                                from app.core.database import async_session
                                from app.models.project import Project
                                from sqlalchemy import update as sql_update

                                async with async_session() as db:
                                    update_values = {'title': context.project_name}
                                    if context.project_description:
                                        update_values['description'] = context.project_description

                                    await db.execute(
                                        sql_update(Project)
                                        .where(Project.id == context.project_id)
                                        .values(**update_values)
                                    )
                                    await db.commit()
                                    logger.info(f"[Writer] Updated project title in DB: '{context.project_name}' for {context.project_id}")
                            except Exception as db_err:
                                logger.warning(f"[Writer] Failed to update project title in DB: {db_err}")

                except Exception as e:
                    logger.warning(f"[Writer] Failed to extract plan block: {e}")
                    plan_extracted = True  # Don't retry on error

            # EXACT Bolt.new technique:
            # buffer += chunk
            # while "</file>" in buffer: extract, parse, save
            complete_files = streaming_buffer.feed_chunk(chunk)

            # Process each complete file immediately (Bolt.new flow)
            for file_data in complete_files:
                file_path = file_data['path']
                file_content = file_data['content']

                # Save file to ALL 4 layers (sandbox, S3, database, checkpoint)
                # This ensures files persist after sandbox cleanup
                await self.save_file(
                    project_id=context.project_id,
                    file_path=file_path,
                    content=file_content,
                    user_id=context.user_id
                )

                context.files_created.append({
                    'path': file_path,
                    'content': file_content
                })

                # SSE Emit (file created & content) - Bolt.new exact behavior
                yield OrchestratorEvent(
                    type=EventType.FILE_OPERATION,
                    data={
                        "operation": "create",
                        "path": file_path,
                        "status": "complete",
                        "file_content": file_content,
                        "project_id": context.project_id  # For file isolation
                    }
                )

                logger.info(f"[Bolt Buffer] [OK] File saved & emitted: {file_path}")

        # After stream ends, check for any remaining partial content
        incomplete_files = []
        if streaming_buffer.has_partial_tag():
            partial_buffer = streaming_buffer.get_buffer()
            logger.warning(f"[Streaming Buffer] Partial tag remaining in buffer: {partial_buffer[:200]}...")

            # Try to salvage partial file if possible
            if '<file path="' in partial_buffer:
                try:
                    # Extract path from partial tag
                    path_start = partial_buffer.find('<file path="') + len('<file path="')
                    path_end = partial_buffer.find('"', path_start)
                    if path_end > path_start:
                        partial_path = partial_buffer[path_start:path_end]
                        # Extract whatever content we have
                        content_start = partial_buffer.find('>', path_end) + 1
                        partial_content = partial_buffer[content_start:] if content_start > 0 else ""

                        if partial_content.strip():
                            logger.info(f"[Streaming Buffer] Salvaging partial file: {partial_path}")
                            # Save partial file with warning comment
                            cleaned_content = partial_content.strip('\n')
                            salvaged_content = f"// WARNING: This file may be incomplete due to stream interruption\n{cleaned_content}"
                            await self.save_file(
                                project_id=context.project_id,
                                file_path=partial_path,
                                content=salvaged_content,
                                user_id=context.user_id
                            )
                            context.files_created.append({
                                'path': partial_path,
                                'content': salvaged_content,
                                'partial': True
                            })
                            incomplete_files.append(partial_path)
                            yield OrchestratorEvent(
                                type=EventType.WARNING,
                                data={
                                    "message": f"File {partial_path} may be incomplete",
                                    "path": partial_path
                                }
                            )
                except Exception as e:
                    logger.error(f"[Streaming Buffer] Failed to salvage partial file: {e}")

        # Validate files were created successfully
        files_in_task = [f for f in context.files_created if not f.get('partial', False)]
        partial_files = [f for f in context.files_created if f.get('partial', False)]

        # Emit validation status
        if incomplete_files or partial_files:
            yield OrchestratorEvent(
                type=EventType.WARNING,
                data={
                    "message": f"Some files may be incomplete: {len(partial_files)} partial files",
                    "incomplete_files": incomplete_files,
                    "suggestion": "You can regenerate incomplete files by asking: 'Please regenerate the incomplete files'"
                }
            )
        else:
            logger.info(f"[Validation] [OK] All files created successfully for task")

        # Fallback: If no project_name was extracted from plan block, extract from user request
        if not plan_extracted or not getattr(context, 'project_name', None):
            fallback_name = self._extract_project_name_from_request(context.user_request)
            if fallback_name and fallback_name != "My Project":
                context.project_name = fallback_name
                logger.info(f"[Writer] Fallback project_name from request: {context.project_name}")

        logger.info(f"[Streaming Buffer] [OK] Streaming complete, {len(context.files_created)} files created")

    async def _execute_bolt_instant(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute BOLT INSTANT agent - generates complete project in single call

        This is the FAST mode like Bolt.new - combines planning and code generation
        in one API call for maximum speed (~60-90 seconds vs 5+ minutes)

        Shows only 3 simple steps to user (no confusion):
        1. Understanding request
        2. Building project
        3. Done
        """
        logger.info("[Bolt Instant] ⚡ Starting fast single-call generation...")

        # Step 1: Understanding (shown to user)
        yield OrchestratorEvent(
            type=EventType.THINKING_STEP,
            data={
                "step": "understanding",
                "detail": "Understanding your request...",
                "icon": "🧠",
                "user_visible": True
            }
        )

        # Step 2: Building (shown to user)
        yield OrchestratorEvent(
            type=EventType.THINKING_STEP,
            data={
                "step": "building",
                "detail": "Building your project...",
                "icon": "🔨",
                "user_visible": True
            }
        )

        # Stream the response and extract files (internal - files show individually)
        async for event in self._execute_writer_for_task(config, context, None, config.system_prompt):
            # Only yield file events, filter out noisy thinking steps
            if event.type in [EventType.FILE_OPERATION, EventType.FILE_CONTENT, EventType.ERROR, EventType.WARNING]:
                yield event
            # Skip internal thinking steps to keep UI clean

        # Step 3: Done (shown to user)
        yield OrchestratorEvent(
            type=EventType.THINKING_STEP,
            data={
                "step": "complete",
                "detail": f"Done! Created {len(context.files_created)} files",
                "icon": "✅",
                "user_visible": True
            }
        )

        # IMPORTANT: Create plan_json from generated files
        # This allows the project to be loaded later from the dropdown
        # Without this, plan_json is NULL and the project can't be restored
        context.plan = {
            "raw": f"<!-- Auto-generated from bolt_instant mode -->\n<project>\n  <name>{context.project_name or 'Project'}</name>\n  <files>{len(context.files_created)}</files>\n</project>",
            "files": [
                {
                    "path": f,
                    "type": "code",
                    "description": f"Generated file: {f}"
                }
                for f in context.files_created
            ],
            "tasks": [],  # No tasks in bolt_instant mode
            "features": []
        }
        logger.info(f"[Bolt Instant] Created plan_json with {len(context.files_created)} files for database storage")

        logger.info(f"[Bolt Instant] [OK] Fast generation complete, {len(context.files_created)} files created")

    async def _execute_verifier(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute verification agent - check if all files are complete

        This agent:
        1. Verifies all expected files from plan were generated
        2. Checks files have sufficient/complete code
        3. Identifies missing or incomplete files
        4. Can regenerate incomplete files automatically
        """
        from app.modules.agents.verification_agent import VerificationAgent

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": "Verifying generated files..."}
        )

        # Initialize verification agent
        verifier = VerificationAgent(model=config.model)

        # Run verification
        verification_result = await verifier.verify_project(
            project_id=context.project_id,
            plan=context.plan or {},
            files_created=context.files_created,
            tech_stack=context.tech_stack
        )

        # Emit verification result
        yield OrchestratorEvent(
            type=EventType.VERIFICATION_RESULT,
            data={
                "status": verification_result["status"],
                "summary": verification_result["summary"],
                "statistics": verification_result["statistics"],
                "missing_files": verification_result["missing_files"],
                "incomplete_files": verification_result["incomplete_files"],
                "empty_files": verification_result["empty_files"]
            }
        )

        # If verification failed or partial, regenerate incomplete files
        files_to_regenerate = verification_result.get("regenerate_files", [])

        if files_to_regenerate and verification_result["status"] != "pass":
            logger.info(f"[Verifier] Need to regenerate {len(files_to_regenerate)} files: {files_to_regenerate}")

            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={
                    "message": f"Regenerating {len(files_to_regenerate)} incomplete/missing files...",
                    "files": files_to_regenerate
                }
            )

            # Generate prompt for missing/incomplete files
            if verification_result["missing_files"]:
                regenerate_prompt = await verifier.generate_missing_files_prompt(
                    missing_files=verification_result["missing_files"],
                    plan=context.plan or {},
                    existing_files=context.files_created
                )
            else:
                regenerate_prompt = await verifier.generate_regenerate_prompt(
                    files_to_regenerate=files_to_regenerate,
                    plan=context.plan or {},
                    existing_files=context.files_created,
                    issues={"file_details": verification_result.get("files_verified", [])}
                )

            # Use writer to regenerate files
            system_prompt = self._get_default_writer_prompt()

            # Initialize Bolt streaming buffer for regeneration
            streaming_buffer = BoltStreamingBuffer(tag='file')

            logger.info("[Verifier] Starting file regeneration...")

            async for chunk in self.claude_client.generate_stream(
                prompt=regenerate_prompt,
                system_prompt=system_prompt,
                model="sonnet",  # Use sonnet for better quality regeneration
                max_tokens=8192,
                temperature=0.3
            ):
                # Check for token usage marker at end of stream
                if chunk.startswith("__TOKEN_USAGE__:"):
                    parts = chunk.split(":")
                    if len(parts) >= 4:
                        input_tokens = int(parts[1])
                        output_tokens = int(parts[2])
                        model_used = parts[3]
                        context.track_tokens(
                            input_tokens, output_tokens, model_used,
                            agent_type="verifier",
                            operation="regenerate_file"
                        )
                        logger.info(f"[Verifier] Token usage tracked: {input_tokens}+{output_tokens}={input_tokens+output_tokens} ({model_used})")
                    continue  # Don't process marker as content

                complete_files = streaming_buffer.feed_chunk(chunk)

                for file_data in complete_files:
                    file_path = file_data['path']
                    file_content = file_data['content']

                    # Save regenerated file to ALL 4 layers
                    await self.save_file(
                        project_id=context.project_id,
                        file_path=file_path,
                        content=file_content,
                        user_id=context.user_id
                    )

                    # Update context
                    # Check if file already exists in files_created
                    existing_idx = next(
                        (i for i, f in enumerate(context.files_created) if f.get('path') == file_path),
                        None
                    )

                    if existing_idx is not None:
                        # Update existing file
                        context.files_created[existing_idx] = {
                            'path': file_path,
                            'content': file_content,
                            'regenerated': True
                        }
                    else:
                        # Add new file
                        context.files_created.append({
                            'path': file_path,
                            'content': file_content,
                            'regenerated': True
                        })

                    # Emit file operation event
                    yield OrchestratorEvent(
                        type=EventType.FILE_OPERATION,
                        data={
                            "operation": "regenerate",
                            "path": file_path,
                            "status": "complete",
                            "file_content": file_content
                        }
                    )

                    logger.info(f"[Verifier] [OK] Regenerated: {file_path}")

            # Update verification status after regeneration
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={
                    "message": f"Regeneration complete. {len(files_to_regenerate)} files updated.",
                    "verification_status": "regenerated"
                }
            )

        elif verification_result["status"] == "pass":
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={
                    "message": f"[OK] All {verification_result['statistics']['total_files']} files verified successfully",
                    "verification_status": "pass"
                }
            )

        else:
            # Log issues but don't block
            yield OrchestratorEvent(
                type=EventType.WARNING,
                data={
                    "message": f"Verification found issues: {verification_result['summary']}",
                    "verification_status": verification_result["status"],
                    "issues": verification_result.get("critical_issues", [])
                }
            )

    async def _execute_fixer(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute fixer agent - apply patches for errors
        """
        from app.modules.agents.fixer_agent import FixerAgent
        from app.utils.response_parser import PlainTextParser

        if not context.errors:
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": "No errors to fix"}
            )
            return

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": f"Fixing {len(context.errors)} error(s)..."}
        )

        # Initialize fixer
        fixer = FixerAgent(model=config.model)
        fixer.reset_token_tracking()  # Reset token tracking for this fix session
        file_manager = FileManager()

        # Process each error
        for error_idx, error in enumerate(context.errors, 1):
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": f"Fixing error {error_idx}/{len(context.errors)}: {error.get('message', 'Unknown error')}"}
            )

            # Build context for fixer
            agent_context = AgentContext(
                user_request=f"Fix error: {error.get('message')}",
                project_id=context.project_id,
                metadata={
                    "error": error,
                    "files": [f["path"] for f in context.files_created],
                    "project_type": context.project_type
                }
            )

            # Call fixer to generate fix
            fix_result = await fixer.fix_error(
                error=error,
                project_id=context.project_id,
                file_context={
                    "files_created": context.files_created,
                    "tech_stack": context.tech_stack
                }
            )

            # Handle file requests - fixer may need more context (max 2 retries)
            max_file_request_retries = 2
            for retry in range(max_file_request_retries):
                requested_files = fix_result.get("requested_files", [])
                if not requested_files:
                    break

                yield OrchestratorEvent(
                    type=EventType.STATUS,
                    data={"message": f"Fixer requested {len(requested_files)} additional file(s) for context"}
                )

                # Read requested files and add to context
                additional_files = {}
                project_path = file_manager.get_project_path(context.project_id)
                for req_file in requested_files:
                    try:
                        full_path = project_path / req_file
                        if full_path.exists():
                            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                additional_files[req_file] = f.read()
                                logger.info(f"[Fixer] Loaded requested file: {req_file}")
                    except Exception as read_err:
                        logger.warning(f"[Fixer] Could not read requested file {req_file}: {read_err}")

                if additional_files:
                    # Retry fix with additional context
                    enriched_context = {
                        "files_created": context.files_created,
                        "tech_stack": context.tech_stack,
                        "additional_files": additional_files
                    }
                    fix_result = await fixer.fix_error(
                        error=error,
                        project_id=context.project_id,
                        file_context=enriched_context
                    )
                else:
                    break

            # Get patches and full files from fix result
            patches = fix_result.get("patches", [])
            fixed_files = fix_result.get("fixed_files", [])

            # Also try parsing from response (fallback for PlainTextParser)
            parsed = PlainTextParser.parse_bolt_response(fix_result.get("response", ""))

            # PRIORITY 1: Apply patches (preferred - minimal changes)
            if patches:
                from app.modules.bolt.patch_applier import apply_unified_patch, apply_patch_fuzzy

                for patch_info in patches:
                    file_path = patch_info.get("path")
                    patch_content = patch_info.get("patch")

                    if file_path and patch_content:
                        yield OrchestratorEvent(
                            type=EventType.FILE_OPERATION,
                            data={
                                "path": file_path,
                                "operation": "patching",
                                "status": "in_progress"
                            }
                        )

                        try:
                            # Read original file
                            project_path = file_manager.get_project_path(context.project_id)
                            full_path = project_path / file_path

                            if full_path.exists():
                                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    original_content = f.read()

                                # Try exact patch first, then fuzzy
                                result = apply_unified_patch(original_content, patch_content)

                                if not result.get("success"):
                                    # Try fuzzy matching (allows line number drift)
                                    result = apply_patch_fuzzy(original_content, patch_content, fuzziness=3)

                                if result.get("success"):
                                    # Write patched content
                                    await file_manager.update_file(
                                        project_id=context.project_id,
                                        file_path=file_path,
                                        content=result["new_content"]
                                    )

                                    yield OrchestratorEvent(
                                        type=EventType.FILE_OPERATION,
                                        data={
                                            "path": file_path,
                                            "operation": "patched",
                                            "status": "complete"
                                        }
                                    )

                                    context.files_modified.append({
                                        "path": file_path,
                                        "operation": "patch",
                                        "error": error.get("message")
                                    })
                                    logger.info(f"[Fixer] Successfully applied patch to {file_path}")
                                else:
                                    logger.warning(f"[Fixer] Patch failed for {file_path}: {result.get('error')}")
                                    # Will fall through to full file replacement if available
                            else:
                                logger.warning(f"[Fixer] File not found for patching: {file_path}")

                        except Exception as patch_err:
                            logger.error(f"[Fixer] Patch application error for {file_path}: {patch_err}")

            # PRIORITY 2: Apply full file replacements (fallback or new files)
            files_to_apply = fixed_files or parsed.get("files", [])
            for file_info in files_to_apply:
                file_path = file_info.get("path")
                file_content = file_info.get("content")

                # Skip if we already patched this file
                already_patched = any(
                    m.get("path") == file_path and m.get("operation") == "patch"
                    for m in context.files_modified
                )

                if file_path and file_content and not already_patched:
                    # Update file (full replacement)
                    await file_manager.update_file(
                        project_id=context.project_id,
                        file_path=file_path,
                        content=file_content
                    )

                    yield OrchestratorEvent(
                        type=EventType.FILE_OPERATION,
                        data={
                            "path": file_path,
                            "operation": "fixed",
                            "status": "complete"
                        }
                    )

                    # Track modification
                    context.files_modified.append({
                        "path": file_path,
                        "operation": "fix",
                        "error": error.get("message")
                    })

            # Handle additional instructions (e.g., install missing deps)
            if "instructions" in parsed:
                for instruction in parsed.get("instructions", []):
                    yield OrchestratorEvent(
                        type=EventType.COMMAND_EXECUTE,
                        data={"command": instruction}
                    )

        # Track fixer token usage
        fixer_tokens = fixer.get_token_usage()
        if fixer_tokens.get("total_tokens", 0) > 0:
            context.track_tokens(
                fixer_tokens.get("input_tokens", 0),
                fixer_tokens.get("output_tokens", 0),
                fixer_tokens.get("model", "haiku"),
                agent_type="fixer",
                operation="fix_error"
            )
            logger.info(f"[Fixer] Token usage tracked: {fixer_tokens.get('total_tokens', 0)} tokens ({fixer_tokens.get('call_count', 0)} calls)")

        # Clear errors after fixing
        fixed_count = len(context.errors)
        context.errors = []

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": f"Fixed {fixed_count} error(s) successfully"}
        )

        # Emit server restart event if files were modified
        if context.files_modified:
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={
                    "message": "Reloading preview...",
                    "action": "preview_reload",
                    "files_fixed": [f["path"] for f in context.files_modified]
                }
            )

            # Trigger server restart for hot reload
            try:
                from app.modules.automation.preview_server import preview_server_manager
                restart_result = await preview_server_manager.hot_reload_trigger(context.project_id)
                if restart_result.get("success"):
                    yield OrchestratorEvent(
                        type=EventType.STATUS,
                        data={"message": "Preview reloaded", "action": "preview_reloaded"}
                    )
            except Exception as e:
                logger.warning(f"Failed to trigger hot reload: {e}")

    async def _execute_auto_fixer(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute AUTO-FIX flow - handles FIX intent with auto-collected context.
        This is triggered when user reports a problem in simple terms like:
        - "page is blank"
        - "it's not working"
        - "fix this error"

        The frontend automatically collects all context (errors, logs, files)
        and sends it here for intelligent fixing.
        """
        from app.modules.agents.fixer_agent import FixerAgent
        from app.utils.response_parser import PlainTextParser

        user_problem = context.metadata.get("user_problem", context.user_request)
        terminal_logs = context.metadata.get("terminal_logs", [])
        collected_errors = context.errors or []

        logger.info(f"[AUTO-FIX] Starting auto-fix for: {user_problem}")
        logger.info(f"[AUTO-FIX] Errors: {len(collected_errors)}, Logs: {len(terminal_logs)}, Files: {len(context.files_created)}")

        # Build comprehensive error context from all sources
        error_context_parts = []

        # 1. User's problem description (most important!)
        error_context_parts.append(f"User's Problem: {user_problem}")

        # 2. Collected errors from error collector
        if collected_errors:
            error_context_parts.append("\n--- Collected Errors ---")
            for i, err in enumerate(collected_errors, 1):
                err_str = f"Error {i}: {err.get('message', 'Unknown error')}"
                if err.get('file'):
                    err_str += f" (in {err.get('file')}"
                    if err.get('line'):
                        err_str += f":{err.get('line')}"
                    err_str += ")"
                if err.get('stack'):
                    err_str += f"\n  Stack: {err.get('stack')[:500]}"
                error_context_parts.append(err_str)

        # 3. Recent terminal logs (look for errors)
        if terminal_logs:
            error_logs = [log for log in terminal_logs if log.get('type') in ['error', 'stderr']]
            if error_logs:
                error_context_parts.append("\n--- Terminal Errors ---")
                for log in error_logs[-10:]:  # Last 10 error logs
                    error_context_parts.append(f"  {log.get('content', '')[:300]}")

        combined_error_context = "\n".join(error_context_parts)

        yield OrchestratorEvent(
            type=EventType.THINKING_STEP,
            data={
                "step": "fixing",
                "status": "active",
                "user_visible": True,
                "detail": "Fixing the issue...",
                "icon": "wrench"
            }
        )

        # Initialize fixer agent
        fixer = FixerAgent(model=config.model)
        fixer.reset_token_tracking()  # Reset token tracking for this fix session
        file_manager = FileManager()

        # Build file context from collected files
        file_context = {
            "files_created": context.files_created,
            "tech_stack": context.tech_stack or [],
            "terminal_logs": terminal_logs
        }

        try:
            # Call fixer with comprehensive context
            fix_result = await fixer.fix_error(
                error={
                    "message": combined_error_context,
                    "source": "auto_fix",
                    "severity": "error",
                    "user_problem": user_problem
                },
                project_id=context.project_id,
                file_context=file_context
            )

            # Parse the fix response
            response_text = fix_result.get("response", "")
            parsed = PlainTextParser.parse_bolt_response(response_text)

            # Apply fixes to files
            if "files" in parsed:
                for file_info in parsed["files"]:
                    file_path = file_info.get("path")
                    file_content = file_info.get("content")

                    if file_path and file_content:
                        yield OrchestratorEvent(
                            type=EventType.FILE_OPERATION,
                            data={
                                "path": file_path,
                                "operation": "modify",
                                "status": "in_progress"
                            }
                        )

                        # Save the fixed file
                        session_id = context.metadata.get("session_id")
                        user_id = context.metadata.get("user_id")
                        try:
                            await self.save_file(context.project_id, file_path, file_content, session_id, user_id=user_id)
                            logger.info(f"[AUTO-FIX] Fixed file: {file_path}")

                            yield OrchestratorEvent(
                                type=EventType.FILE_OPERATION,
                                data={
                                    "path": file_path,
                                    "operation": "modify",
                                    "status": "complete",
                                    "content": file_content
                                }
                            )

                            context.files_modified.append({
                                "path": file_path,
                                "operation": "auto_fix",
                                "reason": user_problem
                            })

                        except Exception as save_err:
                            logger.error(f"[AUTO-FIX] Failed to save file {file_path}: {save_err}")

            yield OrchestratorEvent(
                type=EventType.THINKING_STEP,
                data={
                    "step": "fixed",
                    "status": "complete",
                    "user_visible": True,
                    "detail": f"Fixed {len(context.files_modified)} file(s)",
                    "icon": "check"
                }
            )

            # Clear the errors since they're fixed
            context.errors = []

            # Return success summary
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={
                    "message": f"Auto-fix complete! Modified {len(context.files_modified)} file(s).",
                    "files_fixed": [f["path"] for f in context.files_modified]
                }
            )

            # Track fixer token usage
            fixer_tokens = fixer.get_token_usage()
            if fixer_tokens.get("total_tokens", 0) > 0:
                context.track_tokens(
                    fixer_tokens.get("input_tokens", 0),
                    fixer_tokens.get("output_tokens", 0),
                    fixer_tokens.get("model", "haiku"),
                    agent_type="fixer",
                    operation="auto_fix"
                )
                logger.info(f"[AUTO-FIX] Token usage tracked: {fixer_tokens.get('total_tokens', 0)} tokens ({fixer_tokens.get('call_count', 0)} calls)")

            # Emit server restart/reload event if files were modified
            if context.files_modified:
                yield OrchestratorEvent(
                    type=EventType.STATUS,
                    data={
                        "message": "Reloading preview...",
                        "action": "preview_reload",
                        "files_fixed": [f["path"] for f in context.files_modified]
                    }
                )

                # Trigger hot reload for preview
                try:
                    from app.modules.automation.preview_server import preview_server_manager
                    restart_result = await preview_server_manager.hot_reload_trigger(context.project_id)
                    if restart_result.get("success"):
                        yield OrchestratorEvent(
                            type=EventType.STATUS,
                            data={"message": "Preview reloaded", "action": "preview_reloaded"}
                        )
                except Exception as e:
                    logger.warning(f"[AUTO-FIX] Failed to trigger hot reload: {e}")

        except Exception as e:
            logger.error(f"[AUTO-FIX] Error during fix: {e}")
            yield OrchestratorEvent(
                type=EventType.ERROR,
                data={
                    "error": f"Failed to auto-fix: {str(e)}",
                    "user_problem": user_problem
                }
            )

    async def _execute_runner(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute runner agent - install dependencies and run preview/build
        """
        from app.modules.agents.runner_agent import RunnerAgent

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": "Executing install and build commands..."}
        )

        # Initialize runner
        runner = RunnerAgent(model=config.model)

        # Auto-detect commands from files created
        commands = self._detect_commands(context)

        if not commands:
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": "No commands detected, skipping runner"}
            )
            return

        # Execute each command
        for command in commands:
            yield OrchestratorEvent(
                type=EventType.COMMAND_EXECUTE,
                data={"command": command}
            )

            # Build project context for runner
            # CRITICAL: Use sandbox path where files are actually saved, not USER_PROJECTS_DIR
            from app.core.config import settings

            # Get user_id from context metadata for correct sandbox path
            user_id = context.metadata.get("user_id") if context.metadata else None

            # Try sandbox first (where files are saved during generation)
            sandbox_path = self._unified_storage.get_sandbox_path(context.project_id, user_id)
            if sandbox_path.exists():
                working_dir = str(sandbox_path)
            else:
                # Try legacy path without user_id for backward compatibility
                legacy_sandbox_path = self._unified_storage.get_sandbox_path(context.project_id)
                if legacy_sandbox_path.exists():
                    logger.warning(f"[Runner] Using legacy sandbox path (missing user_id prefix)")
                    working_dir = str(legacy_sandbox_path)
                else:
                    # Fallback to permanent storage
                    working_dir = str(settings.USER_PROJECTS_DIR / context.project_id)

            logger.info(f"[Runner] Working directory: {working_dir}")

            project_context = {
                "tech_stack": context.tech_stack or {},
                "files": [f["path"] for f in context.files_created],
                "working_directory": working_dir,
                "project_type": context.project_type,
                "timeout": 300  # 5 minutes timeout for build commands
            }

            # Execute command using process method
            agent_context = AgentContext(
                user_request=command,
                project_id=context.project_id,
                metadata={
                    "project_context": project_context,
                    "execution_mode": "actual"  # Actually compile and run commands
                }
            )

            result = await runner.process(agent_context)

            # Stream output
            yield OrchestratorEvent(
                type=EventType.COMMAND_OUTPUT,
                data={
                    "command": command,
                    "output": result.get("terminal_output", ""),
                    "success": result.get("success", True)
                }
            )

            # Detect errors
            if result.get("has_errors") or not result.get("success"):
                # Parse errors from terminal output
                errors = self._parse_errors_from_output(
                    terminal_output=result.get("terminal_output", ""),
                    command=command
                )

                if errors:
                    context.errors.extend(errors)

                    yield OrchestratorEvent(
                        type=EventType.ERROR,
                        data={
                            "message": f"Command '{command}' failed",
                            "errors": errors
                        }
                    )

            # Detect preview URL
            preview_url = self._detect_preview_url(result.get("terminal_output", ""))
            if preview_url:
                yield OrchestratorEvent(
                    type=EventType.STATUS,
                    data={"message": f"Preview ready at {preview_url}", "preview_url": preview_url}
                )

            # Track command execution
            context.commands_executed.append({
                "command": command,
                "success": result.get("success", True),
                "output": result.get("terminal_output", "")
            })

    def _detect_commands(self, context: ExecutionContext) -> List[str]:
        """
        Auto-detect commands based on files created and tech stack
        Supports: Docker, JavaScript/TypeScript, Python, Java, Go, Rust, Ruby, PHP, C/C++
        """
        commands = []
        file_paths = [f["path"] for f in context.files_created]
        file_names = [path.split("/")[-1] for path in file_paths]

        # ============ Docker / Docker Compose (PRIORITY - runs entire stack) ============
        # If docker-compose.yml exists, use it to run the entire project
        if any("docker-compose.yml" in path or "docker-compose.yaml" in path for path in file_paths):
            commands.append("docker compose up --build")
            # Don't add other commands - docker-compose handles everything
            return commands

        # If Dockerfile exists but no docker-compose, build and run the container
        if any("Dockerfile" in path for path in file_paths):
            commands.append("docker build -t project-app .")
            commands.append("docker run -p 3000:3000 project-app")
            return commands

        # ============ JavaScript/TypeScript ============
        if any("package.json" in path for path in file_paths):
            commands.append("npm install")
            # Build TypeScript projects
            if any(path.endswith(".ts") and not path.endswith(".d.ts") for path in file_paths):
                commands.append("npm run build")
            # Dev server for React/Vue/Next.js
            if any(path.endswith((".tsx", ".jsx", ".vue")) for path in file_paths):
                commands.append("npm run dev")

        # ============ Python ============
        if any("requirements.txt" in path for path in file_paths):
            commands.append("pip install -r requirements.txt")
        if any("setup.py" in path for path in file_paths):
            commands.append("pip install -e .")
        if any("pyproject.toml" in path for path in file_paths):
            commands.append("pip install .")
        # Run Python app
        if any("main.py" in name or "app.py" in name for name in file_names):
            if any("fastapi" in str(context.tech_stack).lower() or "uvicorn" in str(context.tech_stack).lower() for _ in [1]):
                commands.append("python -m uvicorn main:app --host 0.0.0.0 --port 8000")
            elif any("flask" in str(context.tech_stack).lower() for _ in [1]):
                commands.append("python -m flask run --host 0.0.0.0 --port 5000")
            elif any("django" in str(context.tech_stack).lower() for _ in [1]):
                commands.append("python manage.py runserver 0.0.0.0:8000")

        # ============ Java ============
        if any("pom.xml" in path for path in file_paths):
            commands.append("mvn clean install")
            commands.append("mvn package")
        if any("build.gradle" in path for path in file_paths):
            commands.append("gradle build")
        # Compile single Java files
        if any(path.endswith(".java") for path in file_paths) and not any("pom.xml" in path or "build.gradle" in path for path in file_paths):
            java_files = [p for p in file_paths if p.endswith(".java")]
            if java_files:
                commands.append(f"javac {' '.join(java_files)}")

        # ============ Go ============
        if any("go.mod" in path for path in file_paths):
            commands.append("go mod tidy")
            commands.append("go build ./...")
        if any(path.endswith(".go") for path in file_paths) and not any("go.mod" in path for path in file_paths):
            commands.append("go build")

        # ============ Rust ============
        if any("Cargo.toml" in path for path in file_paths):
            commands.append("cargo build")
            commands.append("cargo test")

        # ============ Ruby ============
        if any("Gemfile" in path for path in file_paths):
            commands.append("bundle install")
        if any("Rakefile" in path for path in file_paths):
            commands.append("rake")
        # Rails
        if any("config/routes.rb" in path for path in file_paths):
            commands.append("rails db:migrate")
            commands.append("rails server -b 0.0.0.0 -p 3000")

        # ============ PHP ============
        if any("composer.json" in path for path in file_paths):
            commands.append("composer install")
        # Laravel
        if any("artisan" in path for path in file_paths):
            commands.append("php artisan key:generate")
            commands.append("php artisan migrate")
            commands.append("php artisan serve --host=0.0.0.0 --port=8000")

        # ============ C/C++ ============
        if any("CMakeLists.txt" in path for path in file_paths):
            commands.append("mkdir -p build && cd build && cmake .. && make")
        if any("Makefile" in path for path in file_paths):
            commands.append("make")
        # Compile single C/C++ files
        if any(path.endswith(".c") for path in file_paths) and not any("Makefile" in path or "CMakeLists.txt" in path for path in file_paths):
            c_files = [p for p in file_paths if p.endswith(".c")]
            if c_files:
                commands.append(f"gcc -o program {' '.join(c_files)}")
        if any(path.endswith(".cpp") for path in file_paths) and not any("Makefile" in path or "CMakeLists.txt" in path for path in file_paths):
            cpp_files = [p for p in file_paths if p.endswith(".cpp")]
            if cpp_files:
                commands.append(f"g++ -o program {' '.join(cpp_files)}")

        # ============ .NET / C# ============
        if any(path.endswith(".csproj") for path in file_paths):
            commands.append("dotnet restore")
            commands.append("dotnet build")

        return commands

    def _parse_errors_from_output(self, terminal_output: str, command: str) -> List[Dict[str, Any]]:
        """
        Parse errors from terminal output
        """
        errors = []

        # Common error patterns
        error_patterns = [
            r"Error: (.+)",
            r"ERROR: (.+)",
            r"TypeError: (.+)",
            r"ModuleNotFoundError: (.+)",
            r"SyntaxError: (.+)",
            r"Failed to compile",
            r"Command failed with exit code (\d+)"
        ]

        for pattern in error_patterns:
            matches = re.findall(pattern, terminal_output, re.MULTILINE)
            for match in matches:
                # Try to extract file path and line number
                file_match = re.search(r'File "([^"]+)", line (\d+)', terminal_output)
                file_path = file_match.group(1) if file_match else "unknown"
                line_number = int(file_match.group(2)) if file_match else 0

                errors.append({
                    "type": "runtime_error",
                    "message": match if isinstance(match, str) else match,
                    "file": file_path,
                    "line": line_number,
                    "command": command
                })

        return errors

    def _detect_preview_url(self, terminal_output: str) -> Optional[str]:
        """
        Detect preview URL from terminal output
        """
        # Common patterns for preview URLs
        url_patterns = [
            r"http://localhost:(\d+)",
            r"http://127\.0\.0\.1:(\d+)",
            r"https?://[^\s]+",
            r"Local:\s+(https?://[^\s]+)",
            r"ready at (https?://[^\s]+)"
        ]

        for pattern in url_patterns:
            match = re.search(pattern, terminal_output, re.IGNORECASE)
            if match:
                if match.groups():
                    # If port number matched, convert to public URL
                    port = int(match.group(1))
                    return _get_preview_url(port)
                else:
                    # Full URL matched - check if it's localhost and convert
                    url = match.group(0)
                    localhost_match = re.search(r"https?://(?:localhost|127\.0\.0\.1):(\d+)", url)
                    if localhost_match:
                        port = int(localhost_match.group(1))
                        return _get_preview_url(port)
                    return url

        return None

    def _build_task_completion_details(
        self,
        task_title: str,
        task_description: str,
        task_number: int,
        files_created: List[str],
        total_files: int
    ) -> str:
        """
        Build comprehensive task completion details for students.
        Explains what was built, files created, and their purpose.
        """
        details_parts = []

        # Header
        details_parts.append(f"## ✅ Task {task_number} Completed: {task_title}\n")
        details_parts.append(f"**Description**: {task_description}\n")

        # Files created section
        if files_created:
            details_parts.append(f"\n### 📁 Files Created ({len(files_created)} files)\n")

            # Categorize files by type
            config_files = []
            component_files = []
            style_files = []
            utility_files = []
            type_files = []
            other_files = []

            for file_path in files_created:
                file_name = file_path.split('/')[-1].lower()
                file_lower = file_path.lower()

                if any(cfg in file_name for cfg in ['config', 'package.json', 'tsconfig', 'vite.config', '.env', 'tailwind', 'postcss', '.eslint', '.gitignore']):
                    config_files.append(file_path)
                elif any(ext in file_lower for ext in ['.tsx', '.jsx']) and 'component' in file_lower or file_path.startswith('src/components'):
                    component_files.append(file_path)
                elif any(ext in file_name for ext in ['.css', '.scss', '.sass', '.less']):
                    style_files.append(file_path)
                elif 'utils' in file_lower or 'helper' in file_lower or 'hooks' in file_lower:
                    utility_files.append(file_path)
                elif 'types' in file_lower or file_name.endswith('.d.ts'):
                    type_files.append(file_path)
                else:
                    other_files.append(file_path)

            # Add categorized files with explanations
            if config_files:
                details_parts.append("\n**⚙️ Configuration Files:**")
                for f in config_files:
                    explanation = self._get_file_explanation(f)
                    details_parts.append(f"  • `{f}` - {explanation}")

            if component_files:
                details_parts.append("\n**🧩 Components:**")
                for f in component_files:
                    explanation = self._get_file_explanation(f)
                    details_parts.append(f"  • `{f}` - {explanation}")

            if style_files:
                details_parts.append("\n**🎨 Styles:**")
                for f in style_files:
                    explanation = self._get_file_explanation(f)
                    details_parts.append(f"  • `{f}` - {explanation}")

            if utility_files:
                details_parts.append("\n**🔧 Utilities & Hooks:**")
                for f in utility_files:
                    explanation = self._get_file_explanation(f)
                    details_parts.append(f"  • `{f}` - {explanation}")

            if type_files:
                details_parts.append("\n**📝 Type Definitions:**")
                for f in type_files:
                    explanation = self._get_file_explanation(f)
                    details_parts.append(f"  • `{f}` - {explanation}")

            if other_files:
                details_parts.append("\n**📄 Other Files:**")
                for f in other_files:
                    explanation = self._get_file_explanation(f)
                    details_parts.append(f"  • `{f}` - {explanation}")

        # Summary
        details_parts.append(f"\n### 📊 Summary")
        details_parts.append(f"  • Files created in this step: **{len(files_created)}**")
        details_parts.append(f"  • Total files in project: **{total_files}**")

        # Learning note based on task type
        learning_note = self._get_learning_note(task_title, task_description)
        if learning_note:
            details_parts.append(f"\n### 💡 Learning Note")
            details_parts.append(f"  {learning_note}")

        return "\n".join(details_parts)

    def _get_file_explanation(self, file_path: str) -> str:
        """
        Get a detailed, educational explanation of what a file does.
        Provides context about the file's role in the project architecture.
        """
        file_name = file_path.split('/')[-1].lower()
        file_lower = file_path.lower()
        dir_path = '/'.join(file_path.split('/')[:-1]).lower()

        # ===== CONFIGURATION FILES =====
        if 'package.json' in file_name:
            return "Defines project metadata, dependencies (React, Vite, etc.), and npm scripts (dev, build, preview). This is the heart of any Node.js project."

        if 'tsconfig' in file_name:
            if 'node' in file_name:
                return "TypeScript config for Node.js environment - sets module resolution and compile target for server-side code."
            if 'app' in file_name:
                return "TypeScript config for the application - defines strict type checking, JSX support, and path aliases."
            return "TypeScript compiler settings - controls how .ts/.tsx files are compiled to JavaScript. Enables type safety."

        if 'vite.config' in file_name:
            return "Vite bundler configuration - sets up React plugin, dev server port, build optimizations, and path aliases (@/ imports)."

        if 'tailwind.config' in file_name:
            return "Tailwind CSS configuration - defines custom colors, fonts, breakpoints, and which files to scan for utility classes."

        if 'postcss.config' in file_name:
            return "PostCSS configuration - enables CSS processing with Tailwind CSS and autoprefixer for cross-browser compatibility."

        if '.eslint' in file_name:
            return "ESLint configuration - enforces code style rules and catches common errors. Improves code quality and consistency."

        if '.prettierrc' in file_name or 'prettier' in file_name:
            return "Prettier configuration - defines code formatting rules (indentation, quotes, semicolons) for consistent style."

        if '.gitignore' in file_name:
            return "Git ignore rules - excludes node_modules, build outputs, and sensitive files from version control."

        if '.env' in file_name:
            if 'example' in file_name or 'sample' in file_name:
                return "Environment variables template - shows required variables without exposing actual secrets. Copy to .env for local setup."
            return "Environment variables - stores API keys, database URLs, and other config that shouldn't be in code."

        # ===== ENTRY POINTS =====
        if file_name == 'main.tsx' or file_name == 'main.ts':
            return "Application entry point - mounts the React app to the DOM. This is where React.StrictMode wraps the app."

        if file_name == 'index.tsx' and 'src' in dir_path:
            return "Main index file - exports the primary module or bootstraps the application."

        if file_name in ['app.tsx', 'app.jsx']:
            return "Root App component - the top-level component that sets up routing, providers, and the overall app structure."

        if file_name == 'index.html':
            return "HTML template - the single HTML file that loads the React app. Contains the root div and script imports."

        # ===== STYLES =====
        if file_name == 'index.css':
            return "Global CSS - imports Tailwind directives (@tailwind base/components/utilities) and defines CSS custom properties."

        if file_name == 'app.css':
            return "App-level styles - contains component-specific styles and CSS animations used throughout the app."

        if file_name in ['global.css', 'globals.css']:
            return "Global styles - resets default browser styles and sets up base typography and color schemes."

        if 'module' in file_name and file_name.endswith('.css'):
            component_name = file_name.replace('.module.css', '').title()
            return f"CSS Module for {component_name} - scoped styles that won't leak to other components. Enables className isolation."

        # ===== COMPONENTS - LAYOUT =====
        if 'navbar' in file_lower or 'navigation' in file_lower:
            return "Navigation component - renders the site header with logo, menu links, and mobile hamburger menu. Usually sticky at top."

        if 'header' in file_lower and 'component' in dir_path:
            return "Header component - contains branding, navigation, and user actions. Typically includes responsive mobile menu."

        if 'footer' in file_lower:
            return "Footer component - displays copyright, links, social icons, and newsletter signup. Appears at bottom of every page."

        if 'sidebar' in file_lower:
            return "Sidebar component - secondary navigation or content panel. Often collapsible on mobile devices."

        if 'layout' in file_lower:
            return "Layout component - wraps pages with consistent header, footer, and container. Defines the page structure template."

        # ===== COMPONENTS - SECTIONS =====
        if 'hero' in file_lower:
            return "Hero section - the prominent banner at the top of the page with headline, subtext, and call-to-action buttons."

        if 'feature' in file_lower:
            return "Features section - showcases product/service benefits with icons, titles, and descriptions in a grid layout."

        if 'testimonial' in file_lower:
            return "Testimonials section - displays customer reviews with quotes, names, and photos to build social proof."

        if 'pricing' in file_lower:
            return "Pricing section - shows subscription tiers or product prices with feature comparisons and buy buttons."

        if 'cta' in file_lower or 'calltoaction' in file_lower:
            return "Call-to-Action section - prompts users to take action (signup, download, contact) with compelling copy and buttons."

        if 'about' in file_lower:
            return "About section/page - tells the company story, mission, team info, and builds brand connection with visitors."

        if 'contact' in file_lower:
            return "Contact section/page - provides contact form, email, phone, address, and possibly an embedded map."

        if 'faq' in file_lower:
            return "FAQ section - answers common questions with expandable accordion items. Reduces support inquiries."

        # ===== COMPONENTS - UI ELEMENTS =====
        if 'button' in file_lower:
            return "Button component - reusable button with variants (primary, secondary, outline), sizes, and loading states."

        if 'card' in file_lower:
            return "Card component - container for content with image, title, description. Used for products, blog posts, team members."

        if 'modal' in file_lower or 'dialog' in file_lower:
            return "Modal component - overlay dialog for confirmations, forms, or detailed views. Traps focus for accessibility."

        if 'input' in file_lower and 'component' in dir_path:
            return "Input component - styled form input with label, validation states, and error messages. Supports various types."

        if 'form' in file_lower:
            return "Form component - handles user input with validation, error display, and submission. May use react-hook-form."

        if 'dropdown' in file_lower or 'select' in file_lower:
            return "Dropdown/Select component - custom styled select menu with options, search, and keyboard navigation."

        if 'tooltip' in file_lower:
            return "Tooltip component - shows helpful text on hover. Positioned automatically based on available space."

        if 'avatar' in file_lower:
            return "Avatar component - displays user profile image or initials fallback. Often used in cards and comments."

        if 'badge' in file_lower or 'tag' in file_lower:
            return "Badge/Tag component - small label for status, categories, or counts. Useful for filtering and categorization."

        if 'spinner' in file_lower or 'loader' in file_lower or 'loading' in file_lower:
            return "Loading component - animated spinner or skeleton shown while data is being fetched."

        if 'toast' in file_lower or 'notification' in file_lower:
            return "Toast/Notification component - brief messages that appear and auto-dismiss. For success, error, info alerts."

        if 'tabs' in file_lower:
            return "Tabs component - organizes content into switchable panels. Good for settings pages or data views."

        if 'accordion' in file_lower:
            return "Accordion component - expandable/collapsible content sections. Perfect for FAQs and long content."

        # ===== COMPONENTS - DATA DISPLAY =====
        if 'list' in file_lower:
            return "List component - renders arrays of items with consistent styling. May include sorting and filtering."

        if 'table' in file_lower:
            return "Table component - displays tabular data with sorting, pagination, and row actions."

        if 'product' in file_lower:
            return "Product component - displays product info with image, price, description, and add-to-cart functionality."

        if 'category' in file_lower or 'categories' in file_lower:
            return "Category component - shows product/content categories with icons and navigation links."

        # ===== HOOKS =====
        if file_name.startswith('use'):
            hook_name = file_name.replace('.ts', '').replace('.tsx', '')

            if 'scroll' in file_lower:
                return f"{hook_name} - tracks scroll position for animations, sticky headers, or infinite scroll pagination."
            if 'media' in file_lower or 'responsive' in file_lower:
                return f"{hook_name} - detects screen size breakpoints for responsive component behavior."
            if 'intersection' in file_lower:
                return f"{hook_name} - observes when elements enter viewport. Used for lazy loading and scroll animations."
            if 'localstorage' in file_lower or 'storage' in file_lower:
                return f"{hook_name} - persists state to localStorage with automatic serialization and sync across tabs."
            if 'fetch' in file_lower or 'query' in file_lower:
                return f"{hook_name} - handles data fetching with loading, error states, and caching logic."
            if 'form' in file_lower:
                return f"{hook_name} - manages form state, validation, and submission with field-level error tracking."
            if 'auth' in file_lower:
                return f"{hook_name} - provides authentication state and methods (login, logout, user info)."
            if 'theme' in file_lower or 'darkmode' in file_lower:
                return f"{hook_name} - manages theme preference with system detection and localStorage persistence."
            if 'debounce' in file_lower:
                return f"{hook_name} - delays function execution until input stops. Essential for search inputs."
            if 'toggle' in file_lower:
                return f"{hook_name} - simple boolean state toggle for modals, menus, and visibility controls."
            if 'click' in file_lower and 'outside' in file_lower:
                return f"{hook_name} - detects clicks outside an element. Used to close dropdowns and modals."
            if 'keyboard' in file_lower or 'key' in file_lower:
                return f"{hook_name} - handles keyboard shortcuts and key press events for accessibility."
            if 'window' in file_lower and 'size' in file_lower:
                return f"{hook_name} - tracks window dimensions for responsive layouts and calculations."
            if 'previous' in file_lower:
                return f"{hook_name} - stores the previous value of a state. Useful for comparing changes."
            if 'mounted' in file_lower:
                return f"{hook_name} - tracks if component is mounted. Prevents state updates after unmount."
            if 'copy' in file_lower or 'clipboard' in file_lower:
                return f"{hook_name} - copies text to clipboard with success/error feedback."
            if 'hover' in file_lower:
                return f"{hook_name} - tracks mouse hover state for interactive elements."

            return f"{hook_name} - custom React hook that encapsulates reusable stateful logic. Follows the 'use' naming convention."

        # ===== UTILITIES =====
        if 'util' in dir_path or 'utils' in dir_path or 'lib' in dir_path:
            if 'format' in file_lower:
                return "Formatting utilities - functions for dates, numbers, currency, and text formatting."
            if 'validate' in file_lower or 'validation' in file_lower:
                return "Validation utilities - reusable validation functions for forms and data integrity."
            if 'storage' in file_lower:
                return "Storage utilities - wrapper around localStorage/sessionStorage with type safety and error handling."
            if 'api' in file_lower or 'fetch' in file_lower or 'http' in file_lower:
                return "API utilities - configured fetch/axios instance with base URL, interceptors, and error handling."
            if 'helper' in file_lower:
                return "Helper functions - miscellaneous utility functions used across the application."
            if 'constant' in file_lower:
                return "Constants - application-wide constant values like API URLs, magic numbers, and config."
            if 'cn' in file_name or 'classname' in file_lower:
                return "className utility - merges Tailwind classes conditionally using clsx/tailwind-merge."
            return "Utility module - helper functions that provide reusable functionality across components."

        # ===== TYPES =====
        if 'types' in file_lower or file_name.endswith('.d.ts'):
            if 'api' in file_lower:
                return "API type definitions - TypeScript interfaces for API request/response data structures."
            if 'component' in file_lower:
                return "Component prop types - TypeScript interfaces defining the props each component accepts."
            if 'global' in file_lower:
                return "Global type definitions - augments built-in types and declares global interfaces."
            return "Type definitions - TypeScript interfaces and types for type safety and IDE autocompletion."

        # ===== CONTEXT / STATE =====
        if 'context' in file_lower:
            context_name = file_name.replace('context', '').replace('.tsx', '').replace('.ts', '').title() or 'App'
            return f"{context_name} Context - React Context provider for sharing {context_name.lower()} state without prop drilling."

        if 'store' in file_lower:
            return "State store - centralized state management (Zustand/Redux). Single source of truth for app data."

        if 'reducer' in file_lower:
            return "State reducer - pure function that handles state transitions based on action types."

        if 'slice' in file_lower:
            return "Redux slice - combines reducer logic and actions for a specific feature domain."

        # ===== PAGES / ROUTES =====
        if 'page' in dir_path or 'pages' in dir_path or 'routes' in dir_path:
            page_name = file_name.replace('.tsx', '').replace('.jsx', '').replace('.ts', '').title()
            return f"{page_name} page - route component that combines layout and data fetching for this URL path."

        # ===== SERVICES =====
        if 'service' in file_lower or 'services' in dir_path:
            return "Service module - handles business logic and API interactions. Separates data layer from UI components."

        # ===== DEFAULT FALLBACKS =====
        if file_name.endswith('.tsx') or file_name.endswith('.jsx'):
            component_name = file_name.replace('.tsx', '').replace('.jsx', '')
            return f"React component ({component_name}) - renders UI based on props and state."

        if file_name.endswith('.ts') or file_name.endswith('.js'):
            return "TypeScript/JavaScript module - contains logic, utilities, or configuration."

        if file_name.endswith('.css'):
            return "Stylesheet - defines visual appearance using CSS rules."

        if file_name.endswith('.json'):
            return "JSON data file - structured data used by the application."

        if file_name.endswith('.md'):
            return "Markdown documentation - provides instructions, API docs, or project information."

        if file_name.endswith('.svg'):
            return "SVG icon/graphic - scalable vector image that can be styled with CSS."

        return "Project file - part of the application structure."

    def _get_learning_note(self, task_title: str, task_description: str) -> str:
        """
        Get an educational learning note based on task type.
        Provides practical insights and best practices for students.
        """
        combined = f"{task_title} {task_description}".lower()

        # ===== PROJECT SETUP & CONFIGURATION =====
        if 'initialization' in combined or 'setup' in combined or 'foundation' in combined or 'scaffold' in combined:
            return """**Project Structure Best Practices:**
- `src/` contains all source code, keeping root clean for config files
- `components/` folder organizes reusable UI pieces by feature or type
- `package.json` is your project manifest - always review dependencies before adding new ones
- Use consistent file naming (PascalCase for components, camelCase for utilities)

💡 **Pro Tip:** Run `npm install` to download dependencies, then `npm run dev` to start development server."""

        if 'config' in combined or 'configuration' in combined:
            return """**Configuration Files Explained:**
- **vite.config.ts**: Controls build process, dev server, and plugins
- **tsconfig.json**: TypeScript settings - `strict: true` catches more bugs
- **tailwind.config.js**: Customize colors, spacing, and add plugins
- **postcss.config.js**: CSS processing pipeline

💡 **Pro Tip:** Keep config files at the root - bundlers look there by default."""

        # ===== COMPONENTS =====
        if 'component' in combined and ('reusable' in combined or 'ui' in combined or 'element' in combined):
            return """**Building Reusable Components:**
- Accept **props** for customization (color, size, variant)
- Use **TypeScript interfaces** to define prop types
- Provide **default values** for optional props
- Keep components **single-responsibility** - one component, one job

💡 **Pro Tip:** If a component exceeds 200 lines, consider splitting it into smaller pieces."""

        if 'layout' in combined or 'structure' in combined:
            return """**Layout Component Pattern:**
- Layouts wrap pages with consistent header, footer, and navigation
- Use **CSS Grid** or **Flexbox** for page structure
- `children` prop allows any content to be rendered inside
- Consider **named slots** for complex layouts (sidebar, main, aside)

💡 **Pro Tip:** Layout components shouldn't contain business logic - keep them purely presentational."""

        if 'navigation' in combined or 'navbar' in combined or 'header' in combined:
            return """**Navigation Best Practices:**
- Use semantic `<nav>` element for accessibility
- Add **aria-current="page"** to active links
- Implement **responsive design** - hamburger menu on mobile
- Keep navigation items to 5-7 max for usability
- Use `position: sticky` for sticky headers

💡 **Pro Tip:** Test navigation with keyboard only (Tab, Enter, Escape) for accessibility."""

        if 'footer' in combined:
            return """**Footer Design Tips:**
- Include **copyright**, **legal links**, and **social media**
- Organize content into columns for desktop, stack for mobile
- Add **newsletter signup** for engagement
- Keep important links visible (Privacy, Terms, Contact)

💡 **Pro Tip:** The footer is a great place for secondary navigation and trust signals."""

        # ===== SECTIONS =====
        if 'hero' in combined:
            return """**Hero Section Psychology:**
- **Headline**: Clear value proposition in 6-10 words
- **Subheadline**: Elaborate on the benefit in 1-2 sentences
- **CTA Button**: Action-oriented text ("Get Started", "Try Free")
- **Visual**: Support the message, don't distract from it

💡 **Pro Tip:** A/B test your headlines - small changes can significantly impact conversion."""

        if 'feature' in combined:
            return """**Features Section Strategy:**
- Highlight **3-4 key features** maximum (cognitive limit)
- Use **icons** for quick visual recognition
- Benefits over features: "Save 5 hours/week" vs "Automated reports"
- Consider a **grid layout** for visual balance

💡 **Pro Tip:** Order features by importance - users scan in F-pattern (top-left to bottom-right)."""

        if 'testimonial' in combined:
            return """**Testimonials That Convert:**
- Include **photo**, **name**, and **title/company**
- Highlight **specific results** ("Increased sales by 40%")
- Use **star ratings** for quick credibility scan
- Carousel for multiple testimonials saves space

💡 **Pro Tip:** Video testimonials convert 25% better than text alone."""

        if 'pricing' in combined:
            return """**Pricing Page Psychology:**
- **3 tiers** work best (Good-Better-Best)
- **Highlight recommended** plan with visual emphasis
- Show **annual savings** to encourage longer commitment
- Include **feature comparison table** for clarity
- Add **money-back guarantee** to reduce perceived risk

💡 **Pro Tip:** Use odd pricing ($49 vs $50) - it feels more calculated and fair."""

        if 'faq' in combined:
            return """**FAQ Section Best Practices:**
- Group questions by **category** for easier scanning
- Use **accordion pattern** to save space
- Answer in **2-3 sentences** - link to docs for details
- Include **search functionality** for large FAQs
- Add **schema markup** for Google rich results

💡 **Pro Tip:** FAQ content often ranks well in Google - include common search queries."""

        if 'contact' in combined:
            return """**Contact Form UX:**
- Ask only **essential fields** (name, email, message)
- Show **expected response time** ("We reply within 24 hours")
- Include **alternative contact methods** (email, phone, chat)
- Add **success message** after submission
- Consider **captcha** for spam protection

💡 **Pro Tip:** Forms with 3 fields have 25% higher completion than forms with 6+ fields."""

        if 'about' in combined:
            return """**About Page Strategy:**
- Tell your **story** - people connect with narratives
- Include **team photos** with real humans
- State your **mission and values** clearly
- Show **milestones** and achievements
- Add **trust signals** (certifications, press mentions)

💡 **Pro Tip:** The About page is often the 2nd most visited page - make it memorable."""

        # ===== FORMS & INPUTS =====
        if 'form' in combined:
            return """**Form Design Principles:**
- **Label every input** - placeholder text is not a label
- Show **validation errors inline** near the field
- Use **proper input types** (email, tel, number)
- Add **autocomplete attributes** for faster filling
- Disable submit button during processing

💡 **Pro Tip:** Use react-hook-form or Formik for complex forms - they handle validation elegantly."""

        if 'input' in combined or 'field' in combined:
            return """**Input Field Best Practices:**
- **Clear labels** above or to the left of fields
- Show **character count** for limited fields
- Use **helper text** for format requirements
- Highlight **focus state** with border color
- Mark **required fields** with asterisk

💡 **Pro Tip:** Never rely on color alone for validation - add icons or text for colorblind users."""

        if 'button' in combined:
            return """**Button Design System:**
- **Primary**: Main action (Submit, Buy, Continue)
- **Secondary**: Alternative action (Cancel, Skip)
- **Ghost/Outline**: Tertiary actions
- **Destructive**: Delete, remove (use red sparingly)
- Add **loading spinner** for async actions

💡 **Pro Tip:** Buttons should look clickable - use shadow, hover effects, and cursor: pointer."""

        if 'modal' in combined or 'dialog' in combined:
            return """**Modal/Dialog Accessibility:**
- **Trap focus** inside modal when open
- Close on **Escape key** press
- Add **backdrop click** to close (optional)
- Return focus to **trigger element** on close
- Use **aria-modal="true"** and **role="dialog"**

💡 **Pro Tip:** Modals interrupt user flow - use sparingly and only for critical actions."""

        # ===== STYLING =====
        if 'style' in combined or 'styling' in combined or 'css' in combined or 'tailwind' in combined:
            return """**Tailwind CSS Productivity:**
- Use **@apply** to extract repeated utility patterns
- Define **custom colors** in tailwind.config.js
- Responsive: mobile-first with `md:`, `lg:` prefixes
- Dark mode: add `dark:` prefix to any utility
- Install **Tailwind CSS IntelliSense** VS Code extension

💡 **Pro Tip:** Run `npx tailwindcss --help` to see all CLI options including CSS minification."""

        if 'theme' in combined or 'dark mode' in combined or 'color' in combined:
            return """**Theming Best Practices:**
- Use **CSS custom properties** for theme values
- Store preference in **localStorage**
- Respect **system preference** with prefers-color-scheme
- Provide **manual toggle** override
- Test **contrast ratios** for accessibility (4.5:1 minimum)

💡 **Pro Tip:** Add `class="dark"` to `<html>` element for Tailwind dark mode to work."""

        # ===== HOOKS & STATE =====
        if 'hook' in combined:
            return """**Custom Hooks Guidelines:**
- Start name with **"use"** (React convention)
- Hooks can call **other hooks** inside them
- Return **array** [value, setter] or **object** { value, setValue }
- Keep hooks **focused** - one responsibility each
- Test hooks with **@testing-library/react-hooks**

💡 **Pro Tip:** Extract logic to hooks when 2+ components need the same stateful behavior."""

        if 'state' in combined or 'context' in combined:
            return """**State Management Decision Tree:**
1. **Local state** (useState): UI state, form inputs
2. **Lifted state**: Shared between siblings, lift to parent
3. **Context**: Theme, auth, shared across many components
4. **External store** (Zustand/Redux): Complex state, persistence

💡 **Pro Tip:** Start with useState, add complexity only when needed - premature optimization is the root of evil."""

        # ===== DATA & API =====
        if 'api' in combined or 'fetch' in combined or 'data' in combined:
            return """**Data Fetching Patterns:**
- Use **async/await** for cleaner code
- Handle **loading**, **error**, and **success** states
- Implement **retry logic** for failed requests
- Cache responses when appropriate
- Consider **react-query** or **SWR** for caching

💡 **Pro Tip:** Always show loading indicators - users assume "broken" if nothing happens within 1 second."""

        if 'service' in combined:
            return """**Service Layer Pattern:**
- **Centralize** API calls in service files
- **Abstract** the HTTP client (axios, fetch)
- Handle **authentication tokens** in interceptors
- **Transform** API responses to app-friendly format
- Easy to **mock** for testing

💡 **Pro Tip:** Service layer makes it easy to switch backends or add caching without touching components."""

        # ===== TYPES =====
        if 'type' in combined or 'interface' in combined or 'typescript' in combined:
            return """**TypeScript Type Safety:**
- Use **interfaces** for object shapes (extendable)
- Use **type** for unions and intersections
- **Export types** from a central types file
- Use **generics** for reusable type patterns
- Enable **strict mode** in tsconfig.json

💡 **Pro Tip:** Hover over variables in VS Code - TypeScript shows inferred types. Add explicit types when inference fails."""

        # ===== TESTING =====
        if 'test' in combined:
            return """**Testing Strategy:**
- **Unit tests**: Individual functions and hooks
- **Component tests**: Render and interact with components
- **Integration tests**: Multiple components working together
- **E2E tests**: Full user flows (Cypress, Playwright)
- Aim for **80% coverage** on critical paths

💡 **Pro Tip:** Test behavior, not implementation. Ask "what should happen?" not "how does it work?"."""

        # ===== RESPONSIVE =====
        if 'responsive' in combined or 'mobile' in combined:
            return """**Responsive Design Strategy:**
- **Mobile-first**: Start with mobile, enhance for larger screens
- Use **relative units** (rem, %, vh/vw) over pixels
- **Test on real devices** - emulators miss touch interactions
- Consider **touch targets** (44x44px minimum)
- Breakpoints: 640px (sm), 768px (md), 1024px (lg), 1280px (xl)

💡 **Pro Tip:** Use Chrome DevTools device toolbar (Ctrl+Shift+M) to test responsive layouts."""

        # ===== ANIMATION =====
        if 'animation' in combined or 'transition' in combined:
            return """**Animation Best Practices:**
- Use **CSS transitions** for simple state changes
- Use **CSS animations** or Framer Motion for complex sequences
- Keep animations **under 300ms** for snappy feel
- Respect **prefers-reduced-motion** for accessibility
- Animate **transform** and **opacity** (GPU accelerated)

💡 **Pro Tip:** Animation should guide attention, not distract. Less is more."""

        # ===== ACCESSIBILITY =====
        if 'accessibility' in combined or 'a11y' in combined or 'aria' in combined:
            return """**Accessibility Essentials:**
- Use **semantic HTML** (nav, main, article, button)
- Add **alt text** to all meaningful images
- Ensure **keyboard navigation** works throughout
- Maintain **color contrast** ratios (4.5:1)
- Test with **screen reader** (VoiceOver, NVDA)

💡 **Pro Tip:** Install axe DevTools browser extension to audit accessibility issues automatically."""

        # ===== PERFORMANCE =====
        if 'performance' in combined or 'optimization' in combined or 'lazy' in combined:
            return """**Performance Optimization:**
- **Lazy load** below-fold images and components
- Use **React.memo** to prevent unnecessary re-renders
- **Code split** with dynamic imports
- **Optimize images** (WebP format, proper sizing)
- **Minimize bundle** size with tree shaking

💡 **Pro Tip:** Run Lighthouse audit (Chrome DevTools) to identify performance bottlenecks."""

        # ===== DEFAULT =====
        return """**Building Quality Software:**
- Each file has a **specific purpose** in the architecture
- **Small, focused modules** are easier to test and maintain
- **Consistent naming** conventions improve code readability
- **Documentation** in code comments helps future developers
- **Version control** (git) tracks changes and enables collaboration

💡 **Pro Tip:** Read the generated code to understand patterns - modify and experiment to learn faster."""


    async def _get_user_details(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch user details from database for document generation.
        Returns student academic details like college name, roll number, etc.
        """
        if not user_id:
            logger.warning("[Orchestrator] No user_id provided for document generation - using defaults")
            return self._get_default_user_details()

        try:
            from app.core.database import get_session_local
            from app.models.user import User
            from sqlalchemy import select
            import traceback

            session_factory = get_session_local()
            async with session_factory() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()

                if not user:
                    logger.warning(f"[Orchestrator] User not found for document generation: {user_id}")
                    return self._get_default_user_details()

                # Log what fields are populated vs using defaults
                user_details = {
                    "full_name": user.full_name or "Student Name",
                    "roll_number": user.roll_number or "ROLL001",
                    "college_name": user.college_name or "College Name",
                    "university_name": user.university_name or "Autonomous Institution",
                    "department": user.department or "Department of Computer Science and Engineering",
                    "course": user.course or "B.Tech",
                    "year_semester": user.year_semester or "4th Year",
                    "batch": user.batch or "2024-2025",
                    "guide_name": user.guide_name or "Dr. Guide Name",
                    "guide_designation": user.guide_designation or "Assistant Professor",
                    "hod_name": user.hod_name or "Dr. HOD Name",
                }

                # Log which fields are using defaults (user hasn't set them)
                defaults_used = [k for k, v in {
                    "full_name": user.full_name,
                    "roll_number": user.roll_number,
                    "college_name": user.college_name,
                }.items() if not v]

                if defaults_used:
                    logger.info(f"[Orchestrator] User {user_id} missing profile fields: {defaults_used}")

                logger.debug(f"[Orchestrator] User details fetched for {user_id}: college={user_details['college_name']}")
                return user_details

        except Exception as e:
            logger.error(f"[Orchestrator] Failed to fetch user details for {user_id}: {type(e).__name__}: {e}")
            logger.error(f"[Orchestrator] Traceback: {traceback.format_exc()}")
            return self._get_default_user_details()

    def _get_default_user_details(self) -> Dict[str, Any]:
        """Return default user details when unable to fetch from database"""
        return {
            "full_name": "Student Name",
            "roll_number": "ROLL001",
            "college_name": "College Name",
            "university_name": "Autonomous Institution",
            "department": "Department of Computer Science and Engineering",
            "course": "B.Tech",
            "year_semester": "4th Year",
            "batch": "2024-2025",
            "guide_name": "Dr. Guide Name",
            "guide_designation": "Assistant Professor",
            "hod_name": "Dr. HOD Name",
        }

    def _extract_project_name_from_request(self, user_request: str) -> str:
        """
        Extract a human-readable project name from the user's request.
        Examples:
          'create an ecommerce application' -> 'Ecommerce Application'
          'build a task management app' -> 'Task Management App'
          'make a weather dashboard' -> 'Weather Dashboard'
        """
        import re
        
        # Common patterns for extracting project type
        patterns = [
            r'(?:create|build|make|develop|generate)\s+(?:an?\s+)?(.+?)\s*(?:app(?:lication)?|system|platform|website|dashboard|portal|project)?$',
            r'(?:create|build|make|develop|generate)\s+(?:an?\s+)?(.+?)$',
            r'^(.+?)\s*(?:app(?:lication)?|system|platform|website|dashboard|portal|project)$',
        ]
        
        request_lower = user_request.lower().strip()
        
        for pattern in patterns:
            match = re.search(pattern, request_lower, re.IGNORECASE)
            if match:
                project_name = match.group(1).strip()
                # Title case and clean up
                project_name = ' '.join(word.capitalize() for word in project_name.split())
                # Remove common filler words
                project_name = re.sub(r'^(?:A|An|The)\s+', '', project_name)
                if len(project_name) > 3:  # Reasonable length
                    return project_name
        
        # Fallback: Extract key words from request
        words = re.findall(r'[a-zA-Z]{3,}', user_request)
        # Filter out common verbs
        stop_words = {'create', 'build', 'make', 'develop', 'generate', 'with', 'using', 'the', 'and', 'for'}
        key_words = [w for w in words if w.lower() not in stop_words][:3]
        if key_words:
            return ' '.join(word.capitalize() for word in key_words) + ' Project'
        
        return 'My Project'

    def _extract_api_endpoints_from_files(self, files_created: List) -> List[Dict]:
        """
        Extract API endpoints from generated code files.
        Looks for route decorators like @app.get, @router.post, etc.
        """
        import re
        endpoints = []

        # Type safety: handle bool/None/invalid types
        if not isinstance(files_created, list):
            logger.warning(f"[Documenter] _extract_api_endpoints_from_files received non-list: {type(files_created)}")
            return endpoints

        # Patterns for different frameworks
        patterns = [
            # FastAPI/Flask patterns
            r'@(?:app|router|api)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            # Express.js patterns
            r'(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            # Spring Boot patterns
            r'@(?:Get|Post|Put|Delete|Patch)Mapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']',
            # Django patterns
            r'path\s*\(\s*["\']([^"\']+)["\']',
        ]

        for file_info in files_created:
            if isinstance(file_info, dict):
                file_path = file_info.get('path', '')
                content = file_info.get('content', '')
            elif isinstance(file_info, str):
                file_path = file_info
                content = ''
            else:
                continue

            # Only check relevant files
            if not any(ext in file_path for ext in ['.py', '.js', '.ts', '.java', '.go']):
                continue

            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if len(match) == 2:
                        method, path = match
                        endpoints.append({
                            "method": method.upper(),
                            "path": path,
                            "file": file_path
                        })
                    elif len(match) == 1:
                        endpoints.append({
                            "method": "GET",
                            "path": match[0],
                            "file": file_path
                        })

        return endpoints[:20]  # Limit to 20 endpoints

    def _extract_database_tables_from_files(self, files_created: List) -> List[Dict]:
        """
        Extract database table/model definitions from generated code files.
        Looks for model classes, table definitions, etc.
        """
        import re
        tables = []

        # Type safety: handle bool/None/invalid types
        if not isinstance(files_created, list):
            logger.warning(f"[Documenter] _extract_database_tables_from_files received non-list: {type(files_created)}")
            return tables

        # Patterns for different ORMs/frameworks
        patterns = [
            # SQLAlchemy
            (r'class\s+(\w+)\s*\([^)]*(?:Base|Model)[^)]*\)', 'sqlalchemy'),
            # Django
            (r'class\s+(\w+)\s*\(models\.Model\)', 'django'),
            # Prisma
            (r'model\s+(\w+)\s*\{', 'prisma'),
            # TypeORM
            (r'@Entity\s*\([^)]*\)\s*(?:export\s+)?class\s+(\w+)', 'typeorm'),
            # Mongoose
            (r'const\s+(\w+)Schema\s*=\s*new\s+(?:mongoose\.)?Schema', 'mongoose'),
            # SQL CREATE TABLE
            (r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?', 'sql'),
        ]

        for file_info in files_created:
            if isinstance(file_info, dict):
                file_path = file_info.get('path', '')
                content = file_info.get('content', '')
            elif isinstance(file_info, str):
                file_path = file_info
                content = ''
            else:
                continue

            # Only check relevant files
            if not any(ext in file_path for ext in ['.py', '.js', '.ts', '.java', '.prisma', '.sql']):
                continue

            for pattern, orm_type in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for table_name in matches:
                    # Skip common base classes
                    if table_name.lower() in ['base', 'model', 'basemodel', 'entity']:
                        continue
                    tables.append({
                        "name": table_name,
                        "type": orm_type,
                        "file": file_path
                    })

        # Remove duplicates
        seen = set()
        unique_tables = []
        for table in tables:
            if table['name'] not in seen:
                seen.add(table['name'])
                unique_tables.append(table)

        return unique_tables[:15]  # Limit to 15 tables

    async def _execute_documenter(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Execute documenter agent - Generate documentation for ALL projects

        For Academic projects (student/faculty users): Full docs using ChunkedDocumentAgent (Word, PDF, PPT)
        For Other projects: Basic docs (README, API docs if applicable)
        """
        import asyncio

        # Determine documentation type based on subscription tier AND user role
        # Documents are ONLY generated for PRO plan students/faculty
        user_role = context.metadata.get("user_role", "").lower() if context.metadata else ""
        subscription_tier = context.metadata.get("subscription_tier", "FREE").upper() if context.metadata else "FREE"
        plan_type = context.metadata.get("plan_type", "free").lower() if context.metadata else "free"

        # Check if user is a student or faculty
        is_student = user_role in ["student", "faculty"]

        # Check for PRO/Premium plan - handle various plan name formats
        # Check both plan_type (enum: 'pro', 'enterprise') and subscription_tier (name: 'PRO', 'Premium', etc.)
        is_pro_plan = (
            plan_type in ["pro", "enterprise"] or
            subscription_tier in ["PRO", "PREMIUM", "ENTERPRISE", "UNLIMITED"] or
            "PREMIUM" in subscription_tier.upper() or
            "PRO" in subscription_tier.upper()
        )

        # Academic documents only for PRO plan students/faculty
        is_academic = is_student and is_pro_plan

        logger.info(f"[Documenter] Subscription check - tier={subscription_tier}, plan_type={plan_type}, role={user_role}, is_pro={is_pro_plan}, is_student={is_student}")

        # Update context.project_type if generating academic docs
        if is_academic:
            context.project_type = "Academic"
            logger.info(f"[Documenter] Set project_type to Academic (PRO student)")

        logger.info(f"[Documenter] Generating documentation - is_academic={is_academic}, tier={subscription_tier}, role={user_role}")

        if is_academic:
            # Use ChunkedDocumentAgent for PRO plan students (Word, PDF, PPT)
            async for event in self._execute_academic_documenter(config, context):
                yield event
        else:
            # Non-PRO users: Generate basic documentation (Dockerfile, docker-compose)
            logger.info(f"[Documenter] Generating basic docs for non-PRO user (tier={subscription_tier}, role={user_role})")
            async for event in self._execute_basic_documenter(config, context):
                yield event

            # Also notify about PRO features
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": "Upgrade to PRO for academic documents (SRS, PPT, VIVA Q&A)"}
            )

    async def _execute_basic_documenter(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Generate basic documentation for non-academic projects.
        Includes: Dockerfile, docker-compose.yml
        """
        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": "Generating project documentation (Docker files)..."}
        )

        # Detect project type for Docker generation
        # Handle cases where tech_stack or files_created might be None, bool, or unexpected types
        tech_stack = context.tech_stack if isinstance(context.tech_stack, (dict, list)) else {}
        files_created = context.files_created if isinstance(context.files_created, list) else []
        file_paths = [f.get("path", "") if isinstance(f, dict) else str(f) for f in files_created]

        # Detect framework
        has_package_json = any("package.json" in p for p in file_paths)
        has_requirements = any("requirements.txt" in p for p in file_paths)
        has_pom_xml = any("pom.xml" in p for p in file_paths)
        has_vite = any("vite" in str(tech_stack).lower()) or any("vite.config" in p for p in file_paths)
        has_next = any("next" in str(tech_stack).lower()) or any("next.config" in p for p in file_paths)
        has_fastapi = any("fastapi" in str(tech_stack).lower())
        has_django = any("django" in str(tech_stack).lower())

        docs_generated = 0

        # Generate Dockerfile
        dockerfile_content = self._generate_dockerfile(
            has_package_json=has_package_json,
            has_requirements=has_requirements,
            has_pom_xml=has_pom_xml,
            has_vite=has_vite,
            has_next=has_next,
            has_fastapi=has_fastapi,
            has_django=has_django
        )

        try:
            await self.file_manager.write_file(context.project_id, "Dockerfile", dockerfile_content)
            docs_generated += 1
            yield OrchestratorEvent(
                type=EventType.FILE_OPERATION,
                data={"path": "Dockerfile", "operation": "create", "status": "complete"}
            )
            context.files_created.append({"path": "Dockerfile", "type": "documentation"})
            logger.info(f"[Documenter] Generated Dockerfile")
        except Exception as e:
            logger.error(f"[Documenter] Failed to create Dockerfile: {e}")

        # Generate docker-compose.yml
        compose_content = self._generate_docker_compose(
            project_id=context.project_id,
            has_package_json=has_package_json,
            has_requirements=has_requirements,
            has_vite=has_vite,
            has_next=has_next,
            has_fastapi=has_fastapi,
            has_django=has_django
        )

        try:
            await self.file_manager.write_file(context.project_id, "docker-compose.yml", compose_content)
            docs_generated += 1
            yield OrchestratorEvent(
                type=EventType.FILE_OPERATION,
                data={"path": "docker-compose.yml", "operation": "create", "status": "complete"}
            )
            context.files_created.append({"path": "docker-compose.yml", "type": "documentation"})
            logger.info(f"[Documenter] Generated docker-compose.yml")
        except Exception as e:
            logger.error(f"[Documenter] Failed to create docker-compose.yml: {e}")

        # Generate .dockerignore
        dockerignore_content = self._generate_dockerignore()
        try:
            await self.file_manager.write_file(context.project_id, ".dockerignore", dockerignore_content)
            docs_generated += 1
            yield OrchestratorEvent(
                type=EventType.FILE_OPERATION,
                data={"path": ".dockerignore", "operation": "create", "status": "complete"}
            )
            context.files_created.append({"path": ".dockerignore", "type": "documentation"})
        except Exception as e:
            logger.error(f"[Documenter] Failed to create .dockerignore: {e}")

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": f"Generated {docs_generated} documentation files"}
        )

    def _generate_dockerfile(
        self,
        has_package_json: bool,
        has_requirements: bool,
        has_pom_xml: bool,
        has_vite: bool,
        has_next: bool,
        has_fastapi: bool,
        has_django: bool
    ) -> str:
        """Generate appropriate Dockerfile based on project type"""

        if has_next:
            return '''# Next.js Dockerfile
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM node:18-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["npm", "start"]
'''

        if has_vite or has_package_json:
            return '''# Node.js / React / Vite Dockerfile
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source files
COPY . .

# Expose port
EXPOSE 5173 3000

# Start development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
'''

        if has_fastapi:
            return '''# FastAPI Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY . .

# Expose port
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
'''

        if has_django:
            return '''# Django Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY . .

# Expose port
EXPOSE 8000

# Start Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
'''

        if has_requirements:
            return '''# Python Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
'''

        if has_pom_xml:
            return '''# Spring Boot Dockerfile
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn package -DskipTests

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
EXPOSE 8080
CMD ["java", "-jar", "app.jar"]
'''

        # Default Node.js
        return '''# Default Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY . .

RUN if [ -f package.json ]; then npm install; fi

EXPOSE 3000

CMD ["npm", "start"]
'''

    def _generate_docker_compose(
        self,
        project_id: str,
        has_package_json: bool,
        has_requirements: bool,
        has_vite: bool,
        has_next: bool,
        has_fastapi: bool,
        has_django: bool
    ) -> str:
        """Generate docker-compose.yml based on project type"""

        service_name = project_id.replace("-", "_")[:20]

        if has_vite:
            port = "5173:5173"
        elif has_next:
            port = "3000:3000"
        elif has_fastapi or has_django:
            port = "8000:8000"
        else:
            port = "3000:3000"

        return f'''version: '3.8'

services:
  {service_name}:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "{port}"
    volumes:
      - .:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
    restart: unless-stopped

# Optional: Add database service if needed
#  db:
#    image: postgres:15-alpine
#    environment:
#      POSTGRES_USER: user
#      POSTGRES_PASSWORD: password
#      POSTGRES_DB: mydb
#    volumes:
#      - postgres_data:/var/lib/postgresql/data
#    ports:
#      - "5432:5432"

#volumes:
#  postgres_data:
'''

    def _generate_dockerignore(self) -> str:
        """Generate .dockerignore file"""
        return '''# Dependencies
node_modules
__pycache__
*.pyc
.venv
venv
env

# Build outputs
dist
build
.next
target
*.class

# IDE
.idea
.vscode
*.swp
*.swo

# Git
.git
.gitignore

# Env files
.env
.env.local
.env.*.local

# Logs
*.log
npm-debug.log*

# OS
.DS_Store
Thumbs.db

# Test
coverage
.pytest_cache
htmlcov
'''

    async def _execute_academic_documenter(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Generate academic documentation using ChunkedDocumentAgent.
        Generates: Project Report (Word/PDF), SRS (Word/PDF), PPT
        """
        import asyncio
        from app.modules.agents.chunked_document_agent import ChunkedDocumentAgent, DocumentType, CollegeInfo
        from app.modules.agents.base_agent import AgentContext
        from app.modules.automation.pdf_generator import PDFGenerator

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": "Generating academic documentation (Project Report, SRS, PPT)..."}
        )

        # Initialize ChunkedDocumentAgent (no model param - uses claude client internally)
        chunked_agent = ChunkedDocumentAgent()

        # Build agent context
        # IMPORTANT: Include user_id for document storage to S3 and PostgreSQL
        user_id = context.metadata.get("user_id") if context.metadata else None
        agent_context = AgentContext(
            user_request=context.user_request,
            project_id=context.project_id,
            user_id=user_id,  # Required for saving documents to S3 and database
            metadata={
                "plan": context.plan,
                "files_created": context.files_created,
                "tech_stack": context.tech_stack,
                "project_type": context.project_type,
                "user_id": user_id  # Also pass in metadata for compatibility
            }
        )

        # Build project data for content generation
        # Use context.project_name if available (from Planner), fallback to extracting from user_request
        actual_project_name = context.project_name or self._extract_project_name_from_request(context.user_request)

        # Extract API endpoints from generated files (look for route definitions)
        api_endpoints = getattr(context, 'api_endpoints', []) or []
        if not api_endpoints and isinstance(context.files_created, list) and len(context.files_created) > 0:
            api_endpoints = self._extract_api_endpoints_from_files(context.files_created)

        # Extract database tables from generated files (look for model definitions)
        database_tables = getattr(context, 'database_tables', []) or []
        if not database_tables and isinstance(context.files_created, list) and len(context.files_created) > 0:
            database_tables = self._extract_database_tables_from_files(context.files_created)

        # Safely get files_created as list (handle bool/None cases)
        safe_files_created = context.files_created if isinstance(context.files_created, list) else []
        safe_tech_stack = context.tech_stack if isinstance(context.tech_stack, (dict, list)) else {}
        safe_features = context.features if isinstance(context.features, list) else []

        project_data = {
            "project_name": actual_project_name,
            "project_type": context.project_type or "web_application",
            "description": context.project_description or context.user_request,
            "plan": context.plan.get("raw", "") if context.plan else "",
            "files": safe_files_created,
            "tech_stack": safe_tech_stack,
            "technologies": safe_tech_stack,  # Alias for compatibility
            "features": safe_features,
            "api_endpoints": api_endpoints,
            "database_tables": database_tables,
            "code_files": safe_files_created
        }

        # Fetch user details for document generation
        user_details = await self._get_user_details(user_id)

        # Create college info from user's registration details
        college_info = CollegeInfo(
            project_title=actual_project_name,
            college_name=user_details.get("college_name", "College Name"),
            affiliated_to=user_details.get("university_name", "Autonomous Institution"),
            department=user_details.get("department", "Department of Computer Science and Engineering"),
            academic_year=user_details.get("batch", "2024-2025"),
            guide_name=user_details.get("guide_name", "Dr. Guide Name"),
            hod_name=user_details.get("hod_name", "Dr. HOD Name"),
            students=[{
                "name": user_details.get("full_name", "Student Name"),
                "roll_number": user_details.get("roll_number", "ROLL001")
            }]
        )

        doc_count = 0
        docs_dir = f"docs"

        try:
            # ============================================================
            # PARALLEL DOCUMENT GENERATION - All docs generated at once!
            # ============================================================
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": "Generating all documents in PARALLEL (Project Report, SRS, PPT, Viva Q&A)..."}
            )

            # Helper function to generate a single document and return its path
            async def generate_single_doc(doc_type: DocumentType, doc_name: str) -> Optional[str]:
                """Generate a single document and return its file path"""
                try:
                    file_path = None
                    async for event in chunked_agent.generate_document(
                        context=agent_context,
                        document_type=doc_type,
                        project_data=project_data,
                        college_info=college_info,
                        parallel=True
                    ):
                        if event.get("type") == "complete":
                            file_path = event.get("file_path")
                            logger.info(f"[Documenter] {doc_name} generated: {file_path}")
                    return file_path
                except Exception as e:
                    logger.error(f"[Documenter] Failed to generate {doc_name}: {e}")
                    return None

            # Run ALL document generations in parallel
            logger.info("[Documenter] Starting PARALLEL generation of all 4 documents...")
            start_time = asyncio.get_event_loop().time()

            results = await asyncio.gather(
                generate_single_doc(DocumentType.PROJECT_REPORT, "Project Report"),
                generate_single_doc(DocumentType.SRS, "SRS"),
                generate_single_doc(DocumentType.PPT, "PPT"),
                generate_single_doc(DocumentType.VIVA_QA, "Viva Q&A"),
                return_exceptions=True
            )

            elapsed = asyncio.get_event_loop().time() - start_time
            logger.info(f"[Documenter] PARALLEL generation completed in {elapsed:.1f}s")

            # Unpack results
            report_path, srs_path, ppt_path, viva_path = results

            # Helper to process results and log exceptions
            doc_names = ["Project Report", "SRS", "PPT", "Viva Q&A"]
            doc_results = [report_path, srs_path, ppt_path, viva_path]
            failed_docs = []

            for doc_name, result in zip(doc_names, doc_results):
                if isinstance(result, Exception):
                    logger.error(f"[Documenter] {doc_name} generation failed: {type(result).__name__}: {result}")
                    failed_docs.append(doc_name)

            if failed_docs:
                logger.warning(f"[Documenter] Failed documents: {', '.join(failed_docs)}")

            # Process Project Report
            if report_path and not isinstance(report_path, Exception):
                doc_count += 1
                yield OrchestratorEvent(
                    type=EventType.FILE_OPERATION,
                    data={"path": report_path, "operation": "documentation", "status": "complete"}
                )
                context.files_created.append({"path": report_path, "type": "documentation"})

            # Process SRS
            if srs_path and not isinstance(srs_path, Exception):
                doc_count += 1
                yield OrchestratorEvent(
                    type=EventType.FILE_OPERATION,
                    data={"path": srs_path, "operation": "documentation", "status": "complete"}
                )
                context.files_created.append({"path": srs_path, "type": "documentation"})

            # Process PPT
            if ppt_path and not isinstance(ppt_path, Exception):
                doc_count += 1
                yield OrchestratorEvent(
                    type=EventType.FILE_OPERATION,
                    data={"path": ppt_path, "operation": "documentation", "status": "complete"}
                )
                context.files_created.append({"path": ppt_path, "type": "documentation"})

            # Process Viva Q&A
            if viva_path and not isinstance(viva_path, Exception):
                doc_count += 1
                yield OrchestratorEvent(
                    type=EventType.FILE_OPERATION,
                    data={"path": viva_path, "operation": "documentation", "status": "complete"}
                )
                context.files_created.append({"path": viva_path, "type": "documentation"})

            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": f"Academic documentation complete ({doc_count} documents in {elapsed:.0f}s - PARALLEL mode)"}
            )

            # Set flag to indicate academic documents were generated
            # This is used to mark project as COMPLETED instead of PARTIAL_COMPLETED
            if doc_count > 0:
                context.metadata["academic_docs_generated"] = True
                context.metadata["doc_count"] = doc_count
                logger.info(f"[Documenter] Set academic_docs_generated=True, doc_count={doc_count}")

        except asyncio.TimeoutError:
            logger.error("[Documenter] Academic documentation generation timed out")
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": "Academic documentation generation timed out - skipping"}
            )
        except Exception as e:
            logger.error(f"[Documenter] Academic documentation generation failed: {e}")
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": f"Academic documentation failed: {str(e)[:100]} - skipping"}
            )

    async def _execute_standard_documenter(
        self,
        config: AgentConfig,
        context: ExecutionContext
    ) -> AsyncGenerator[OrchestratorEvent, None]:
        """
        Generate standard documentation using DocsPackAgent.
        Generates: README, API docs, Architecture docs
        """
        import asyncio
        from app.modules.agents.docspack_agent import DocsPackAgent
        from app.utils.response_parser import PlainTextParser

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": "Generating project documentation (README, API docs, Architecture)..."}
        )

        # Initialize DocsPack agent
        docspack = DocsPackAgent(model=config.model)

        try:
            # Generate documents with timeout
            docs_result = await asyncio.wait_for(
                docspack.generate_all_documents(
                    plan=context.plan.get("raw", "") if context.plan else "",
                    project_id=context.project_id,
                    files=context.files_created,
                    doc_type="standard"
                ),
                timeout=300  # 5 minute timeout
            )
        except asyncio.TimeoutError:
            logger.error("[Documenter] Standard documentation generation timed out after 5 minutes")
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": "Documentation generation timed out - skipping"}
            )
            return
        except Exception as e:
            logger.error(f"[Documenter] Standard documentation generation failed: {e}")
            yield OrchestratorEvent(
                type=EventType.STATUS,
                data={"message": f"Documentation generation failed: {str(e)[:100]} - skipping"}
            )
            return

        # Parse generated documents - try both parsers for robustness
        response_text = docs_result.get("response", "")
        logger.info(f"[Documenter] Response length: {len(response_text)} chars")

        # First try BoltXMLParser (more robust)
        parsed_files = BoltXMLParser.parse_files_from_xml(response_text)
        logger.info(f"[Documenter] BoltXMLParser found {len(parsed_files)} files")

        # Fallback to PlainTextParser if BoltXMLParser found nothing
        if not parsed_files:
            parsed = PlainTextParser.parse_bolt_response(response_text)
            if "files" in parsed:
                parsed_files = [{"path": f.get("path"), "content": f.get("content")} for f in parsed["files"]]
                logger.info(f"[Documenter] PlainTextParser found {len(parsed_files)} files")

        # Save each document
        doc_count = 0
        for doc_info in parsed_files:
            doc_path = doc_info.get("path")
            doc_content = doc_info.get("content")

            if doc_path and doc_content:
                logger.info(f"[Documenter] Saving document: {doc_path} ({len(doc_content)} chars)")

                # Create document file - save to ALL 4 layers for persistence
                await self.save_file(
                    project_id=context.project_id,
                    file_path=doc_path,
                    content=doc_content,
                    user_id=context.user_id
                )

                doc_count += 1
                # Send file_operation event WITH content so frontend can display it
                yield OrchestratorEvent(
                    type=EventType.FILE_OPERATION,
                    data={
                        "path": doc_path,
                        "operation": "documentation",
                        "operation_status": "complete",
                        "status": "complete",
                        "file_content": doc_content  # Include content for frontend display
                    }
                )

                context.files_created.append({
                    "path": doc_path,
                    "type": "documentation",
                    "content": doc_content
                })
            else:
                logger.warning(f"[Documenter] Skipping invalid doc: path={doc_path}, has_content={bool(doc_content)}")

        logger.info(f"[Documenter] Successfully saved {doc_count} documentation files")

        yield OrchestratorEvent(
            type=EventType.STATUS,
            data={"message": f"Documentation generated successfully ({doc_count} documents)"}
        )

    def _extract_files_from_response(self, response: str) -> List[Dict[str, str]]:
        """
        Extract files from <file> tags using Bolt.new-style parser (lxml)

        Uses BoltXMLParser.parse_files_from_xml() which handles:
        - Nested <file> tags
        - Multi-line content
        - Large files
        - Partial chunks

        Falls back to regex if lxml parsing fails
        """
        # Use Bolt.new-style file parser (lxml-based)
        try:
            files = BoltXMLParser.parse_files_from_xml(response)

            if files:
                logger.info(f"[Bolt File Parser] [OK] Extracted {len(files)} files using lxml")
                return files

        except Exception as e:
            logger.warning(f"[Bolt File Parser] lxml parsing failed: {e}")

        # Fallback to regex for incomplete/streaming XML
        logger.info("[File Extraction] Falling back to regex")
        files = []

        try:
            import re
            pattern = r'<file path="([^"]+)">(.*?)</file>'
            matches = re.findall(pattern, response, re.DOTALL)

            for path, content in matches:
                files.append({
                    "path": path.strip(),
                    "content": content.strip()
                })

            logger.info(f"[Fallback Parser] Extracted {len(files)} files using regex")

        except Exception as e:
            logger.error(f"[File Extraction] Fallback failed: {e}")

        return files

    # =========================================================================
    # BOLT.NEW STYLE - Use embedded SYSTEM_PROMPT from Agent Classes
    # =========================================================================
    # Following Bolt.new architecture: prompts are embedded in agent classes,
    # not loaded from external files. This ensures consistency and makes
    # the codebase self-contained.

    def _get_default_planner_prompt(self) -> str:
        """Get planner prompt from PlannerAgent class (Bolt.new style)"""
        return PlannerAgent.SYSTEM_PROMPT

    def _get_default_writer_prompt(self) -> str:
        """Get writer prompt from WriterAgent class (Bolt.new style)"""
        return WriterAgent.SYSTEM_PROMPT

    def _get_default_fixer_prompt(self) -> str:
        """Get fixer prompt from FixerAgent class (Bolt.new style)"""
        return FixerAgent.SYSTEM_PROMPT

    def _get_default_documenter_prompt(self) -> str:
        """Get documenter prompt from DocumentGeneratorAgent class (Bolt.new style)"""
        return DocumentGeneratorAgent.SYSTEM_PROMPT

    def _get_default_runner_prompt(self) -> str:
        """Get runner prompt from RunnerAgent class (Bolt.new style)"""
        return RunnerAgent.SYSTEM_PROMPT

    def _get_default_verifier_prompt(self) -> str:
        """Get verifier prompt from VerificationAgent class (Bolt.new style)"""
        return VerificationAgent.SYSTEM_PROMPT

    def _get_bolt_instant_prompt(self) -> str:
        """Get BoltInstant prompt for beautiful UI-only projects (Bolt.new style)"""
        return BoltInstantAgent.SYSTEM_PROMPT

    def _get_summarizer_prompt(self) -> str:
        """Get Summarizer prompt for context management (Bolt.new Agent 5)"""
        return SummarizerAgent.SYSTEM_PROMPT

    # =========================================================================
    # COLOR THEME SUPPORT - User-selectable colors for UI projects
    # =========================================================================

    # Color presets for user-selectable themes
    COLOR_PRESETS = {
        "ecommerce": {"primary": "orange", "secondary": "amber"},
        "healthcare": {"primary": "teal", "secondary": "emerald"},
        "finance": {"primary": "blue", "secondary": "indigo"},
        "education": {"primary": "purple", "secondary": "violet"},
        "social": {"primary": "pink", "secondary": "rose"},
        "ai": {"primary": "cyan", "secondary": "sky"},
        "blockchain": {"primary": "lime", "secondary": "green"},
        "gaming": {"primary": "red", "secondary": "orange"},
        "portfolio": {"primary": "purple", "secondary": "cyan"},
        "food": {"primary": "orange", "secondary": "yellow"},
        "travel": {"primary": "cyan", "secondary": "teal"},
        "fitness": {"primary": "green", "secondary": "lime"},
    }

    def _build_color_instruction(self, context: ExecutionContext) -> str:
        """
        Build color theme instruction from context.metadata.color_theme.

        Args:
            context: ExecutionContext containing metadata with optional color_theme

        Returns:
            Color instruction string to include in prompts, or empty string
        """
        if not context.metadata:
            return ""

        color_theme = context.metadata.get("color_theme")
        if not color_theme:
            return ""

        primary = None
        secondary = None

        # Check for preset first
        preset = color_theme.get("preset") if isinstance(color_theme, dict) else None
        if preset and preset.lower() in self.COLOR_PRESETS:
            preset_colors = self.COLOR_PRESETS[preset.lower()]
            primary = preset_colors["primary"]
            secondary = preset_colors["secondary"]
            logger.info(f"[ColorTheme] Using preset '{preset}': {primary}/{secondary}")

        # Override with explicit colors if provided
        if isinstance(color_theme, dict):
            if color_theme.get("primary"):
                primary = color_theme["primary"]
            if color_theme.get("secondary"):
                secondary = color_theme["secondary"]

        if not primary and not secondary:
            return ""

        # Build the instruction
        instruction = f"""
🎨 USER-SELECTED COLOR THEME - USE THESE COLORS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRIMARY COLOR: {primary}
SECONDARY COLOR: {secondary or primary}

Apply these colors to ALL UI elements:
• Gradients: from-{primary}-600 to-{secondary or primary}-600
• Buttons: bg-gradient-to-r from-{primary}-600 to-{secondary or primary}-600
• Glows/Shadows: shadow-{primary}-500/25
• Hover states: hover:border-{primary}-500/50
• Focus rings: focus:ring-{primary}-500
• Animated orbs: bg-{primary}-500 and bg-{secondary or primary}-500
• Text accents: text-{primary}-400, text-{secondary or primary}-400

⚠️ IMPORTANT: Use THESE colors instead of auto-detecting from project type!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        logger.info(f"[ColorTheme] Color instruction built: primary={primary}, secondary={secondary}")
        return instruction


# Singleton instance
dynamic_orchestrator = DynamicOrchestrator()
