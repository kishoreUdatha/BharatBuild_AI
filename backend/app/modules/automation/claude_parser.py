"""
Claude Response Parser
Extracts structured actions from Claude's responses
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

from app.core.logging_config import logger


class ClaudeResponseParser:
    """Parses Claude's responses to extract actionable items"""

    def parse_response(self, response: str) -> Dict:
        """
        Parse Claude's response for actions

        Supports multiple formats:
        - XML format: <file>, <install>, <command>
        - Code blocks: ```create:path``` or ```modify:path```
        - Markdown sections

        Returns:
            Dict with actions, thinking, explanations
        """
        result = {
            "actions": [],
            "thinking": "",
            "explanation": "",
            "raw_response": response
        }

        # Try XML format first
        xml_actions = self._parse_xml_format(response)
        if xml_actions:
            result["actions"].extend(xml_actions)

        # Try code block format
        code_actions = self._parse_code_blocks(response)
        if code_actions:
            result["actions"].extend(code_actions)

        # Extract thinking
        result["thinking"] = self._extract_thinking(response)

        # Extract explanation
        result["explanation"] = self._extract_explanation(response)

        return result

    def _parse_xml_format(self, response: str) -> List[Dict]:
        """
        Parse XML format responses

        Example:
        <file operation="create" path="src/App.tsx">
        content here
        </file>
        <install packages="react axios" />
        <command>npm run dev</command>
        """
        actions = []

        try:
            # Extract <file> tags
            file_pattern = r'<file\s+operation="(create|modify|delete)"\s+path="([^"]+)">([^<]*)</file>'
            for match in re.finditer(file_pattern, response, re.DOTALL):
                operation, path, content = match.groups()
                actions.append({
                    "type": f"{operation}_file",
                    "path": path.strip(),
                    "content": content.strip() if operation != "delete" else None
                })

            # Extract <install> tags
            install_pattern = r'<install\s+packages="([^"]+)"(?:\s+manager="([^"]+)")?\s*/?>'
            for match in re.finditer(install_pattern, response):
                packages, manager = match.groups()
                actions.append({
                    "type": "install_packages",
                    "packages": [p.strip() for p in packages.split()],
                    "manager": manager or "npm"
                })

            # Extract <command> tags
            command_pattern = r'<command>([^<]+)</command>'
            for match in re.finditer(command_pattern, response):
                actions.append({
                    "type": "run_command",
                    "command": match.group(1).strip()
                })

            # Extract <build> tags
            if '<build' in response:
                actions.append({
                    "type": "run_build"
                })

            # Extract <preview> tags
            preview_pattern = r'<preview(?:\s+port="(\d+)")?\s*/?>'
            match = re.search(preview_pattern, response)
            if match:
                port = match.group(1)
                actions.append({
                    "type": "start_preview",
                    "port": int(port) if port else None
                })

        except Exception as e:
            logger.error(f"Error parsing XML format: {e}")

        return actions

    def _parse_code_blocks(self, response: str) -> List[Dict]:
        """
        Parse code block format

        Example:
        ```create:src/App.tsx
        content here
        ```

        ```modify:package.json
        diff content
        ```
        """
        actions = []

        try:
            # Pattern for create/modify blocks
            code_block_pattern = r'```(create|modify):([^\n]+)\n(.*?)```'
            for match in re.finditer(code_block_pattern, response, re.DOTALL):
                operation, path, content = match.groups()
                actions.append({
                    "type": f"{operation}_file",
                    "path": path.strip(),
                    "content": content.strip()
                })

            # Pattern for diff blocks
            diff_pattern = r'```diff\n(.*?)```'
            for match in re.finditer(diff_pattern, response, re.DOTALL):
                diff_content = match.group(1)

                # Extract file path from diff
                file_match = re.search(r'\+\+\+ b/(.+?)(?:\n|$)', diff_content)
                if file_match:
                    actions.append({
                        "type": "apply_patch",
                        "path": file_match.group(1).strip(),
                        "patch": diff_content
                    })

        except Exception as e:
            logger.error(f"Error parsing code blocks: {e}")

        return actions

    def _extract_thinking(self, response: str) -> str:
        """Extract thinking section"""
        # Try XML format
        match = re.search(r'<thinking>(.*?)</thinking>', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try markdown format
        match = re.search(r'## Thinking\n(.*?)(?:\n##|$)', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        return ""

    def _extract_explanation(self, response: str) -> str:
        """Extract explanation section"""
        # Try XML format
        match = re.search(r'<explanation>(.*?)</explanation>', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Try markdown format
        match = re.search(r'## Explanation\n(.*?)(?:\n##|$)', response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # If no specific section, use everything that's not actions
        # This is a fallback
        return ""

    def extract_file_operations(self, response: str) -> List[Dict]:
        """
        Extract only file operations (create, modify, delete)
        Useful for showing file changes in UI
        """
        parsed = self.parse_response(response)
        return [
            action for action in parsed["actions"]
            if action["type"] in ["create_file", "modify_file", "delete_file", "apply_patch"]
        ]

    def extract_commands(self, response: str) -> List[str]:
        """
        Extract commands to run
        Useful for terminal execution
        """
        parsed = self.parse_response(response)
        commands = []

        for action in parsed["actions"]:
            if action["type"] == "run_command":
                commands.append(action["command"])
            elif action["type"] == "install_packages":
                manager = action.get("manager", "npm")
                packages = " ".join(action["packages"])
                if manager == "npm":
                    commands.append(f"npm install {packages}")
                elif manager == "pip":
                    commands.append(f"pip install {packages}")

        return commands


# Singleton instance
claude_parser = ClaudeResponseParser()
