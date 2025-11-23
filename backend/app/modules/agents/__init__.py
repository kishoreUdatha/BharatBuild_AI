"""
Multi-Agent System for BharatBuild AI
"""

from app.modules.agents.base_agent import BaseAgent, AgentContext
from app.modules.agents.planner_agent import planner_agent, PlannerAgent
from app.modules.agents.architect_agent import architect_agent, ArchitectAgent
from app.modules.agents.coder_agent import coder_agent, CoderAgent
from app.modules.agents.tester_agent import tester_agent, TesterAgent
from app.modules.agents.debugger_agent import debugger_agent, DebuggerAgent
from app.modules.agents.explainer_agent import explainer_agent, ExplainerAgent
from app.modules.agents.document_generator_agent import document_generator_agent, DocumentGeneratorAgent
from app.modules.agents.orchestrator import orchestrator, MultiAgentOrchestrator, WorkflowMode

__all__ = [
    # Base classes
    'BaseAgent',
    'AgentContext',

    # Singleton instances
    'planner_agent',
    'architect_agent',
    'coder_agent',
    'tester_agent',
    'debugger_agent',
    'explainer_agent',
    'document_generator_agent',
    'orchestrator',

    # Classes
    'PlannerAgent',
    'ArchitectAgent',
    'CoderAgent',
    'TesterAgent',
    'DebuggerAgent',
    'ExplainerAgent',
    'DocumentGeneratorAgent',
    'MultiAgentOrchestrator',

    # Enums
    'WorkflowMode',
]
