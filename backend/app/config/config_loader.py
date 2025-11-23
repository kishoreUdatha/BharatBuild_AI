"""
Configuration Loader for Agent System

Loads agent configurations from YAML files or database.
This allows dynamic prompt/model updates without code changes.
"""

from typing import Dict, Optional, List
from pathlib import Path
import yaml
import logging

from app.modules.orchestrator.dynamic_orchestrator import AgentType, AgentConfig, WorkflowStep

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Load agent configurations from YAML files"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize ConfigLoader

        Args:
            config_path: Path to agent_config.yml (defaults to app/config/agent_config.yml)
        """
        if config_path is None:
            # Default to app/config/agent_config.yml
            self.config_path = Path(__file__).parent / "agent_config.yml"
        else:
            self.config_path = Path(config_path)

        self.prompts_dir = self.config_path.parent / "prompts"

        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        logger.info(f"ConfigLoader initialized with config: {self.config_path}")

    def load_agents(self) -> Dict[AgentType, AgentConfig]:
        """
        Load all agent configurations from YAML

        Returns:
            Dict mapping AgentType to AgentConfig
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            agents = {}
            agent_configs = config.get('agents', {})

            for agent_key, agent_data in agent_configs.items():
                try:
                    # Map string to AgentType enum
                    agent_type = AgentType(agent_key)

                    # Load system prompt from file
                    system_prompt = self._load_prompt(agent_data['system_prompt_file'])

                    # Create AgentConfig
                    agent_config = AgentConfig(
                        name=agent_data['name'],
                        agent_type=agent_type,
                        system_prompt=system_prompt,
                        model=agent_data.get('model', 'sonnet'),
                        temperature=agent_data.get('temperature', 0.7),
                        max_tokens=agent_data.get('max_tokens', 4096),
                        capabilities=agent_data.get('capabilities', []),
                        enabled=agent_data.get('enabled', True)
                    )

                    agents[agent_type] = agent_config
                    logger.info(f"Loaded agent config: {agent_key} ({agent_data['name']})")

                except ValueError as e:
                    logger.warning(f"Skipping unknown agent type: {agent_key}")
                except Exception as e:
                    logger.error(f"Error loading agent {agent_key}: {e}")

            logger.info(f"Loaded {len(agents)} agent configurations")
            return agents

        except Exception as e:
            logger.error(f"Failed to load agent configs: {e}", exc_info=True)
            raise

    def _load_prompt(self, prompt_file: str) -> str:
        """
        Load system prompt from file

        Args:
            prompt_file: Relative path to prompt file (e.g., "prompts/planner.txt")

        Returns:
            System prompt content
        """
        prompt_path = self.config_path.parent / prompt_file

        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read().strip()

        logger.debug(f"Loaded prompt from {prompt_file} ({len(prompt)} chars)")
        return prompt

    def load_workflows(self) -> Dict[str, List[WorkflowStep]]:
        """
        Load workflow definitions from YAML

        Returns:
            Dict mapping workflow name to list of WorkflowSteps
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            workflows = {}
            workflow_configs = config.get('workflows', {})

            for workflow_name, workflow_data in workflow_configs.items():
                steps = []

                for step_data in workflow_data.get('steps', []):
                    try:
                        agent_type = AgentType(step_data['agent'])

                        step = WorkflowStep(
                            agent_type=agent_type,
                            name=step_data['name'],
                            description=step_data.get('description', ''),
                            timeout=step_data.get('timeout', 300),
                            retry_count=step_data.get('retry_count', 2),
                            stream_output=step_data.get('stream_output', False),
                            # Condition will be set programmatically
                            condition=None
                        )

                        steps.append(step)

                    except ValueError:
                        logger.warning(f"Unknown agent type in workflow {workflow_name}: {step_data.get('agent')}")

                workflows[workflow_name] = steps
                logger.info(f"Loaded workflow: {workflow_name} ({len(steps)} steps)")

            logger.info(f"Loaded {len(workflows)} workflow definitions")
            return workflows

        except Exception as e:
            logger.error(f"Failed to load workflows: {e}", exc_info=True)
            raise

    def update_agent_prompt(self, agent_type: AgentType, new_prompt: str) -> None:
        """
        Update an agent's system prompt

        Args:
            agent_type: Which agent to update
            new_prompt: New system prompt content
        """
        # Get the prompt file path from config
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        agent_key = agent_type.value
        if agent_key not in config.get('agents', {}):
            raise ValueError(f"Agent {agent_key} not found in config")

        prompt_file = config['agents'][agent_key]['system_prompt_file']
        prompt_path = self.config_path.parent / prompt_file

        # Write new prompt
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(new_prompt)

        logger.info(f"Updated prompt for {agent_key} in {prompt_file}")

    def update_agent_model(self, agent_type: AgentType, new_model: str) -> None:
        """
        Update an agent's model in YAML config

        Args:
            agent_type: Which agent to update
            new_model: New model name (haiku, sonnet, opus)
        """
        if new_model not in ['haiku', 'sonnet', 'opus']:
            raise ValueError(f"Invalid model: {new_model}")

        # Load config
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        agent_key = agent_type.value
        if agent_key not in config.get('agents', {}):
            raise ValueError(f"Agent {agent_key} not found in config")

        # Update model
        config['agents'][agent_key]['model'] = new_model

        # Save config
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(config, f, default_flow_style=False)

        logger.info(f"Updated model for {agent_key} to {new_model}")

    def get_agent_config(self, agent_type: AgentType) -> Optional[Dict]:
        """
        Get configuration for a specific agent

        Args:
            agent_type: Which agent to get config for

        Returns:
            Agent configuration dict or None
        """
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        return config.get('agents', {}).get(agent_type.value)


# Global instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """
    Get global ConfigLoader instance (singleton)

    Returns:
        ConfigLoader instance
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def reload_config():
    """Force reload of configuration"""
    global _config_loader
    _config_loader = None
    return get_config_loader()
