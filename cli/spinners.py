"""
BharatBuild CLI Spinners & Loading Messages

Provides rotating loading phrases like Claude Code:
- "Thinking..."
- "Analyzing code..."
- "Working on it..."
- etc.
"""

import random
from typing import List, Optional
from dataclasses import dataclass


# ==================== Thinking Messages ====================
# Shown when AI is processing user request

THINKING_MESSAGES = [
    "Thinking...",
    "Analyzing...",
    "Processing...",
    "Working on it...",
    "Let me think...",
    "Considering options...",
    "Examining the code...",
    "Looking into this...",
    "Figuring this out...",
    "Understanding your request...",
    "Evaluating approaches...",
    "Reasoning through this...",
]

# ==================== Code Analysis Messages ====================
# Shown when analyzing code/files

CODE_ANALYSIS_MESSAGES = [
    "Reading the codebase...",
    "Analyzing code structure...",
    "Examining files...",
    "Understanding the architecture...",
    "Scanning dependencies...",
    "Parsing code...",
    "Looking at the implementation...",
    "Reviewing the code...",
    "Checking file contents...",
    "Exploring the project...",
]

# ==================== Generation Messages ====================
# Shown when generating code/files

GENERATION_MESSAGES = [
    "Generating code...",
    "Writing files...",
    "Creating components...",
    "Building the structure...",
    "Crafting the solution...",
    "Putting it together...",
    "Assembling the pieces...",
    "Constructing the code...",
    "Developing the feature...",
    "Implementing the solution...",
]

# ==================== Planning Messages ====================
# Shown when planning/strategizing

PLANNING_MESSAGES = [
    "Planning the approach...",
    "Strategizing...",
    "Mapping out the solution...",
    "Designing the architecture...",
    "Outlining the steps...",
    "Preparing the plan...",
    "Organizing the tasks...",
    "Structuring the work...",
    "Breaking down the problem...",
    "Formulating a strategy...",
]

# ==================== Search Messages ====================
# Shown when searching files/code

SEARCH_MESSAGES = [
    "Searching...",
    "Looking for matches...",
    "Scanning files...",
    "Finding references...",
    "Locating code...",
    "Searching the codebase...",
    "Hunting for patterns...",
    "Exploring directories...",
    "Checking for occurrences...",
    "Digging through files...",
]

# ==================== Fix/Debug Messages ====================
# Shown when fixing bugs/errors

FIX_MESSAGES = [
    "Fixing the issue...",
    "Debugging...",
    "Resolving the problem...",
    "Patching the code...",
    "Addressing the error...",
    "Working on a fix...",
    "Troubleshooting...",
    "Correcting the bug...",
    "Repairing the code...",
    "Finding the solution...",
]

# ==================== Test Messages ====================
# Shown when running/writing tests

TEST_MESSAGES = [
    "Running tests...",
    "Checking results...",
    "Validating code...",
    "Verifying functionality...",
    "Testing the solution...",
    "Executing test suite...",
    "Checking for errors...",
    "Confirming behavior...",
    "Assessing quality...",
    "Evaluating output...",
]

# ==================== Build Messages ====================
# Shown when building/compiling

BUILD_MESSAGES = [
    "Building...",
    "Compiling code...",
    "Bundling assets...",
    "Packaging...",
    "Installing dependencies...",
    "Setting up environment...",
    "Preparing build...",
    "Assembling project...",
    "Processing modules...",
    "Linking components...",
]

# ==================== Git Messages ====================
# Shown during git operations

GIT_MESSAGES = [
    "Checking git status...",
    "Reviewing changes...",
    "Preparing commit...",
    "Analyzing diff...",
    "Looking at history...",
    "Checking branches...",
    "Examining commits...",
    "Staging files...",
    "Updating repository...",
    "Syncing changes...",
]

# ==================== Document Messages ====================
# Shown when generating documents

DOCUMENT_MESSAGES = [
    "Writing documentation...",
    "Generating report...",
    "Creating document...",
    "Formatting content...",
    "Building sections...",
    "Compiling pages...",
    "Structuring document...",
    "Adding diagrams...",
    "Finalizing content...",
    "Polishing the document...",
]

# ==================== Completion Messages ====================
# Shown when task is complete

COMPLETION_MESSAGES = [
    "Done!",
    "Complete!",
    "Finished!",
    "All done!",
    "That's done!",
    "Task complete!",
    "Successfully completed!",
    "Wrapped up!",
    "Mission accomplished!",
    "All set!",
]

# ==================== Error Messages ====================
# Shown when something fails

ERROR_PREFIXES = [
    "Oops!",
    "Hmm,",
    "Encountered an issue:",
    "Something went wrong:",
    "Hit a snag:",
    "Ran into a problem:",
    "Error:",
    "Failed:",
    "Unable to complete:",
    "Issue detected:",
]


@dataclass
class SpinnerConfig:
    """Configuration for spinner display"""
    messages: List[str]
    icon: str = "⠋"
    style: str = "cyan"
    rotate: bool = True  # Whether to rotate through messages


class MessageRotator:
    """
    Rotates through loading messages for variety.

    Usage:
        rotator = MessageRotator()

        # Get a thinking message
        msg = rotator.thinking()  # "Analyzing..."

        # Get another (different) one
        msg = rotator.thinking()  # "Working on it..."

        # Get contextual message
        msg = rotator.for_action("generate")  # "Writing files..."
    """

    def __init__(self):
        self._last_messages = {}  # Track last used message per category
        self._use_count = {}  # Track usage to ensure variety

    def _get_random(self, messages: List[str], category: str) -> str:
        """Get a random message, avoiding repeats"""
        last = self._last_messages.get(category)

        # Filter out last used message for variety
        available = [m for m in messages if m != last]
        if not available:
            available = messages

        message = random.choice(available)
        self._last_messages[category] = message
        return message

    def thinking(self) -> str:
        """Get a thinking/processing message"""
        return self._get_random(THINKING_MESSAGES, "thinking")

    def analyzing(self) -> str:
        """Get a code analysis message"""
        return self._get_random(CODE_ANALYSIS_MESSAGES, "analyzing")

    def generating(self) -> str:
        """Get a code generation message"""
        return self._get_random(GENERATION_MESSAGES, "generating")

    def planning(self) -> str:
        """Get a planning message"""
        return self._get_random(PLANNING_MESSAGES, "planning")

    def searching(self) -> str:
        """Get a search message"""
        return self._get_random(SEARCH_MESSAGES, "searching")

    def fixing(self) -> str:
        """Get a fix/debug message"""
        return self._get_random(FIX_MESSAGES, "fixing")

    def testing(self) -> str:
        """Get a test message"""
        return self._get_random(TEST_MESSAGES, "testing")

    def building(self) -> str:
        """Get a build message"""
        return self._get_random(BUILD_MESSAGES, "building")

    def git(self) -> str:
        """Get a git operation message"""
        return self._get_random(GIT_MESSAGES, "git")

    def documenting(self) -> str:
        """Get a documentation message"""
        return self._get_random(DOCUMENT_MESSAGES, "documenting")

    def completion(self) -> str:
        """Get a completion message"""
        return self._get_random(COMPLETION_MESSAGES, "completion")

    def error_prefix(self) -> str:
        """Get an error prefix"""
        return self._get_random(ERROR_PREFIXES, "error")

    def for_action(self, action: str) -> str:
        """
        Get contextual message based on action type.

        Args:
            action: Type of action (think, analyze, generate, plan, search, fix, test, build, git, document)
        """
        action_map = {
            "think": self.thinking,
            "thinking": self.thinking,
            "analyze": self.analyzing,
            "analyzing": self.analyzing,
            "read": self.analyzing,
            "generate": self.generating,
            "generating": self.generating,
            "write": self.generating,
            "create": self.generating,
            "plan": self.planning,
            "planning": self.planning,
            "search": self.searching,
            "searching": self.searching,
            "find": self.searching,
            "fix": self.fixing,
            "fixing": self.fixing,
            "debug": self.fixing,
            "test": self.testing,
            "testing": self.testing,
            "build": self.building,
            "building": self.building,
            "compile": self.building,
            "install": self.building,
            "git": self.git,
            "commit": self.git,
            "document": self.documenting,
            "documenting": self.documenting,
            "doc": self.documenting,
        }

        getter = action_map.get(action.lower(), self.thinking)
        return getter()


# Global instance for convenience
_rotator = MessageRotator()


def get_thinking_message() -> str:
    """Get a random thinking message"""
    return _rotator.thinking()


def get_message_for_action(action: str) -> str:
    """Get contextual message for an action"""
    return _rotator.for_action(action)


def get_completion_message() -> str:
    """Get a random completion message"""
    return _rotator.completion()


def get_error_prefix() -> str:
    """Get a random error prefix"""
    return _rotator.error_prefix()


# Spinner frames for different styles
SPINNER_FRAMES = {
    "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
    "dots2": ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"],
    "line": ["-", "\\", "|", "/"],
    "arc": ["◜", "◠", "◝", "◞", "◡", "◟"],
    "circle": ["◐", "◓", "◑", "◒"],
    "square": ["◰", "◳", "◲", "◱"],
    "bounce": ["⠁", "⠂", "⠄", "⠂"],
    "grow": ["▁", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃"],
    "pulse": ["█", "▓", "▒", "░", "▒", "▓"],
}
