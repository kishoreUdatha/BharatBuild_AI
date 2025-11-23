"""
Bolt.new XML Tag Parser
Parses Claude's Bolt.new-style XML-tagged responses to Python dictionaries
High performance alternative to JSON parsing - matches Bolt.new format exactly
"""

from typing import Dict, Any, List
import re
from app.core.logging_config import logger


class PlainTextParser:
    """Parse Bolt.new-style XML-tagged responses from Claude for better performance"""

    @staticmethod
    def parse_xml_tags(response: str, tag_name: str) -> List[Dict[str, str]]:
        """
        Parse Bolt.new XML-style tags from response

        Examples:
        <plan>...</plan>
        <file path="src/App.tsx">...</file>
        <terminal>...</terminal>
        <error>...</error>
        <thinking>...</thinking>

        Args:
            response: Response text from Claude
            tag_name: Tag name to extract (e.g., 'plan', 'file', 'terminal')

        Returns:
            List of dicts with tag content and attributes
        """
        results = []

        # Pattern to match tags with optional attributes
        # Matches: <tag attr="value">content</tag>
        pattern = rf'<{tag_name}([^>]*)>(.*?)</{tag_name}>'
        matches = re.finditer(pattern, response, re.DOTALL)

        for match in matches:
            attrs_str = match.group(1).strip()
            content = match.group(2).strip()

            # Parse attributes (e.g., path="src/App.tsx")
            attrs = {}
            if attrs_str:
                attr_pattern = r'(\w+)="([^"]*)"'
                for attr_match in re.finditer(attr_pattern, attrs_str):
                    attrs[attr_match.group(1)] = attr_match.group(2)

            results.append({
                'content': content,
                **attrs
            })

        return results

    @staticmethod
    def parse_bolt_response(response: str) -> Dict[str, Any]:
        """
        Parse complete Bolt.new formatted response

        Extracts all Bolt.new tags:
        - <plan>...</plan>
        - <file path="...">...</file>
        - <terminal>...</terminal>
        - <error>...</error>
        - <thinking>...</thinking>

        Args:
            response: Full response from Claude

        Returns:
            Dict with parsed sections
        """
        parsed = {}

        # Parse plan
        plans = PlainTextParser.parse_xml_tags(response, 'plan')
        if plans:
            parsed['plan'] = plans[0]['content']

        # Parse files
        files = PlainTextParser.parse_xml_tags(response, 'file')
        if files:
            parsed['files'] = files

        # Parse terminal commands
        terminals = PlainTextParser.parse_xml_tags(response, 'terminal')
        if terminals:
            parsed['terminal'] = terminals[0]['content'] if len(terminals) == 1 else [t['content'] for t in terminals]

        # Parse errors
        errors = PlainTextParser.parse_xml_tags(response, 'error')
        if errors:
            parsed['errors'] = [e['content'] for e in errors]

        # Parse thinking
        thinking = PlainTextParser.parse_xml_tags(response, 'thinking')
        if thinking:
            parsed['thinking'] = thinking[0]['content'] if len(thinking) == 1 else [t['content'] for t in thinking]

        logger.debug(f"[PlainTextParser] Parsed Bolt.new response with {len(parsed)} sections")
        return parsed

    @staticmethod
    def parse_sections(response: str) -> Dict[str, str]:
        """
        Parse response into sections based on ===SECTION=== markers

        Args:
            response: Plain text response from Claude

        Returns:
            Dict mapping section names to their content
        """
        sections = {}
        current_section = None
        current_content = []

        for line in response.split('\n'):
            # Check for section marker
            section_match = re.match(r'===([A-Z_]+)===', line.strip())

            if section_match:
                # Save previous section
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content).strip()

                # Start new section
                current_section = section_match.group(1).lower()
                current_content = []

            elif line.strip() == '===END===':
                # End marker - save final section
                if current_section and current_content:
                    sections[current_section] = '\n'.join(current_content).strip()
                break

            elif current_section:
                current_content.append(line)

        # Save last section if no END marker
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()

        logger.debug(f"[PlainTextParser] Parsed {len(sections)} sections")
        return sections

    @staticmethod
    def parse_key_value_pairs(text: str) -> Dict[str, str]:
        """
        Parse key-value pairs from text

        Format:
        Key: Value
        Another Key: Another Value

        Args:
            text: Text containing key-value pairs

        Returns:
            Dict with parsed key-value pairs
        """
        pairs = {}
        for line in text.split('\n'):
            if ':' in line and not line.strip().startswith('-'):
                key, value = line.split(':', 1)
                key_normalized = key.strip().lower().replace(' ', '_')
                pairs[key_normalized] = value.strip()
        return pairs

    @staticmethod
    def parse_list_items(text: str, marker: str = '-') -> List[str]:
        """
        Parse list items from text

        Format:
        - Item 1
        - Item 2

        Args:
            text: Text containing list items
            marker: List item marker (default: -)

        Returns:
            List of items
        """
        items = []
        for line in text.split('\n'):
            stripped = line.strip()
            if stripped.startswith(marker + ' '):
                items.append(stripped[len(marker):].strip())
        return items

    @staticmethod
    def parse_features(text: str) -> List[Dict[str, Any]]:
        """
        Parse features from structured text

        Format:
        FEATURE: Name
        Priority: High
        Description: ...
        Components:
        - Component 1
        - Component 2
        Learning Outcomes:
        - Outcome 1

        Args:
            text: Text containing feature descriptions

        Returns:
            List of feature dictionaries
        """
        features = []
        current_feature = {}
        current_list_key = None

        for line in text.split('\n'):
            line = line.strip()

            if line.startswith('FEATURE:'):
                # Save previous feature
                if current_feature:
                    features.append(current_feature)

                # Start new feature
                current_feature = {
                    'name': line.split(':', 1)[1].strip()
                }
                current_list_key = None

            elif ':' in line and not line.startswith('-'):
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()

                # Check if this starts a list
                if value == '':
                    current_list_key = key
                    current_feature[key] = []
                else:
                    current_feature[key] = value
                    current_list_key = None

            elif line.startswith('-') and current_list_key:
                current_feature[current_list_key].append(line[1:].strip())

        # Save last feature
        if current_feature:
            features.append(current_feature)

        return features

    @staticmethod
    def parse_entities(text: str) -> List[Dict[str, Any]]:
        """
        Parse database entities

        Format:
        ENTITY: User
        Purpose: Store user accounts
        Fields:
        - id (primary key)
        - email (unique)
        """
        entities = []
        current_entity = {}
        current_list_key = None

        for line in text.split('\n'):
            line = line.strip()

            if line.startswith('ENTITY:'):
                if current_entity:
                    entities.append(current_entity)
                current_entity = {'name': line.split(':', 1)[1].strip()}
                current_list_key = None

            elif ':' in line and not line.startswith('-'):
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()

                if value == '':
                    current_list_key = key
                    current_entity[key] = []
                else:
                    current_entity[key] = value
                    current_list_key = None

            elif line.startswith('-') and current_list_key:
                current_entity[current_list_key].append(line[1:].strip())

        if current_entity:
            entities.append(current_entity)

        return entities

    @staticmethod
    def parse_endpoints(text: str) -> List[Dict[str, str]]:
        """Parse API endpoints"""
        endpoints = []
        current_endpoint = {}

        for line in text.split('\n'):
            line = line.strip()

            if line.startswith('ENDPOINT:'):
                if current_endpoint:
                    endpoints.append(current_endpoint)
                current_endpoint = {'path': line.split(':', 1)[1].strip()}

            elif ':' in line and not line.startswith('-'):
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                current_endpoint[key] = value.strip()

        if current_endpoint:
            endpoints.append(current_endpoint)

        return endpoints

    @staticmethod
    def parse_phases(text: str) -> List[Dict[str, Any]]:
        """Parse implementation phases"""
        phases = []
        current_phase = {}
        current_list_key = None

        for line in text.split('\n'):
            line = line.strip()

            if line.startswith('PHASE:'):
                if current_phase:
                    phases.append(current_phase)
                current_phase = {'name': line.split(':', 1)[1].strip()}
                current_list_key = None

            elif ':' in line and not line.startswith('-'):
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()

                if value == '':
                    current_list_key = key
                    current_phase[key] = []
                else:
                    current_phase[key] = value
                    current_list_key = None

            elif line.startswith('-') and current_list_key:
                current_phase[current_list_key].append(line[1:].strip())

        if current_phase:
            phases.append(current_phase)

        return phases

    @staticmethod
    def parse_challenges(text: str) -> List[Dict[str, str]]:
        """Parse challenges and solutions"""
        challenges = []
        current_challenge = {}

        for line in text.split('\n'):
            line = line.strip()

            if line.startswith('CHALLENGE:'):
                if current_challenge:
                    challenges.append(current_challenge)
                current_challenge = {'challenge': line.split(':', 1)[1].strip()}

            elif ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                current_challenge[key] = value.strip()

        if current_challenge:
            challenges.append(current_challenge)

        return challenges

    @staticmethod
    def parse_planner_response(response: str) -> Dict[str, Any]:
        """
        Parse Planner Agent plain text response

        Args:
            response: Plain text response from Planner Agent

        Returns:
            Structured dict with plan data
        """
        sections = PlainTextParser.parse_sections(response)
        result = {'plan': {}}

        # Parse project understanding
        if 'project_understanding' in sections:
            result['plan']['project_understanding'] = PlainTextParser.parse_key_value_pairs(
                sections['project_understanding']
            )

        # Parse technology stack
        if 'technology_stack' in sections:
            tech_lines = sections['technology_stack'].split('\n')
            tech_stack = {}
            current_category = None

            for line in tech_lines:
                line = line.strip()
                if line and ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower().replace(' ', '_')
                    value = value.strip()

                    # Check if it's a category header
                    if key in ['frontend', 'backend', 'database', 'authentication']:
                        # This is a category value (e.g., "Frontend Framework: Next.js")
                        if len(key.split('_')) > 1:
                            category = key.split('_')[0]
                            if category not in tech_stack:
                                tech_stack[category] = {}
                            field = '_'.join(key.split('_')[1:])
                            tech_stack[category][field] = value
                    else:
                        # Regular key-value in current context
                        if current_category:
                            tech_stack[current_category][key] = value

            result['plan']['technology_stack'] = tech_stack

        # Parse core features
        if 'core_features' in sections:
            result['plan']['core_features'] = PlainTextParser.parse_features(
                sections['core_features']
            )

        # Parse database requirements
        if 'database_requirements' in sections:
            db_section = sections['database_requirements']
            result['plan']['database_requirements'] = {
                'entities': PlainTextParser.parse_entities(db_section),
                'relationships': [
                    line.strip()[2:] for line in db_section.split('\n')
                    if line.strip().startswith('- ') and 'ENTITY' not in line
                ]
            }

        # Parse API requirements
        if 'api_requirements' in sections:
            result['plan']['api_requirements'] = {
                'endpoints': PlainTextParser.parse_endpoints(sections['api_requirements'])
            }

        # Parse implementation steps
        if 'implementation_steps' in sections:
            result['plan']['implementation_steps'] = PlainTextParser.parse_phases(
                sections['implementation_steps']
            )

        # Parse learning goals (simple list)
        if 'learning_goals' in sections:
            result['plan']['learning_goals'] = PlainTextParser.parse_list_items(
                sections['learning_goals']
            )

        # Parse challenges
        if 'potential_challenges' in sections:
            result['plan']['potential_challenges'] = PlainTextParser.parse_challenges(
                sections['potential_challenges']
            )

        # Parse success criteria (simple list)
        if 'success_criteria' in sections:
            result['plan']['success_criteria'] = PlainTextParser.parse_list_items(
                sections['success_criteria']
            )

        # Parse future enhancements (simple list)
        if 'future_enhancements' in sections:
            result['plan']['future_enhancements'] = PlainTextParser.parse_list_items(
                sections['future_enhancements']
            )

        logger.info(f"[PlainTextParser] Successfully parsed planner response with {len(result['plan'])} sections")
        return result


# Singleton instance
plain_text_parser = PlainTextParser()
