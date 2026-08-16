"""
Robust Output Parser for LLM Responses

Handles JSON and XML extraction from Claude responses with multiple
fallback strategies to handle common LLM output quirks.
"""

import json
import re
from typing import Dict, Any, Optional, List, Tuple

from app.core.logging_config import logger


class OutputParser:
    """
    Robust parser for LLM output with multiple fallback strategies.

    Handles:
    - JSON wrapped in markdown code blocks
    - JSON with trailing/leading text
    - Truncated JSON (attempts partial recovery)
    - XML tags embedded in mixed content
    - Common JSON formatting errors from LLMs
    """

    @staticmethod
    def parse_json(response: str, required_keys: Optional[List[str]] = None) -> Tuple[Optional[Dict], str]:
        """
        Extract and parse JSON from an LLM response with multiple fallback strategies.

        Args:
            response: Raw response text from LLM
            required_keys: Optional list of keys the result must contain

        Returns:
            Tuple of (parsed_dict_or_None, error_message)
        """
        if not response or not response.strip():
            return None, "Empty response"

        strategies = [
            ("markdown_code_block", OutputParser._extract_from_markdown_block),
            ("direct_parse", OutputParser._direct_parse),
            ("find_json_object", OutputParser._find_json_object),
            ("fix_common_errors", OutputParser._fix_and_parse),
            ("partial_recovery", OutputParser._partial_recovery),
        ]

        last_error = ""
        for strategy_name, strategy_fn in strategies:
            try:
                result = strategy_fn(response)
                if result is not None:
                    # Validate required keys
                    if required_keys:
                        missing = [k for k in required_keys if k not in result]
                        if missing:
                            last_error = f"Strategy '{strategy_name}' parsed JSON but missing keys: {missing}"
                            continue
                    logger.debug(f"[OutputParser] JSON parsed successfully with strategy: {strategy_name}")
                    return result, ""
            except Exception as e:
                last_error = f"Strategy '{strategy_name}' failed: {str(e)}"
                continue

        return None, f"All JSON parsing strategies failed. Last error: {last_error}"

    @staticmethod
    def _extract_from_markdown_block(response: str) -> Optional[Dict]:
        """Strategy 1: Extract JSON from ```json ... ``` blocks."""
        # Match ```json or ``` followed by JSON
        pattern = r'```(?:json)?\s*\n?([\s\S]*?)\n?\s*```'
        matches = re.findall(pattern, response)

        for match in matches:
            match = match.strip()
            if match.startswith('{'):
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        return None

    @staticmethod
    def _direct_parse(response: str) -> Optional[Dict]:
        """Strategy 2: Try direct JSON parse of the entire response."""
        stripped = response.strip()
        if stripped.startswith('{') and stripped.endswith('}'):
            return json.loads(stripped)
        return None

    @staticmethod
    def _find_json_object(response: str) -> Optional[Dict]:
        """Strategy 3: Find the outermost balanced JSON object."""
        # Find the first '{' and track brace depth
        start = -1
        depth = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(response):
            if escape_next:
                escape_next = False
                continue

            if char == '\\' and in_string:
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if char == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0 and start >= 0:
                    json_str = response[start:i + 1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        # Try next object
                        start = -1
                        continue

        return None

    @staticmethod
    def _fix_and_parse(response: str) -> Optional[Dict]:
        """Strategy 4: Fix common LLM JSON errors and retry."""
        # Extract potential JSON region
        start = response.find('{')
        end = response.rfind('}')
        if start == -1 or end == -1 or end <= start:
            return None

        json_str = response[start:end + 1]

        # Fix 1: Remove trailing commas before } or ]
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

        # Fix 2: Fix unescaped newlines in strings (common LLM error)
        # This is tricky — only replace \n that are inside string values
        json_str = re.sub(r'(?<!\\)\n(?=[^"]*"[^"]*$)', r'\\n', json_str)

        # Fix 3: Replace single quotes used as JSON delimiters (not within strings)
        # Only do this if standard parse fails
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # Fix 4: Try replacing Python-style None/True/False
        json_str2 = json_str.replace(': None', ': null')
        json_str2 = json_str2.replace(': True', ': true')
        json_str2 = json_str2.replace(': False', ': false')
        try:
            return json.loads(json_str2)
        except json.JSONDecodeError:
            pass

        return None

    @staticmethod
    def _partial_recovery(response: str) -> Optional[Dict]:
        """Strategy 5: Attempt partial JSON recovery for truncated responses."""
        start = response.find('{')
        if start == -1:
            return None

        json_str = response[start:]

        # Count unmatched braces/brackets
        depth_brace = 0
        depth_bracket = 0
        in_string = False
        escape_next = False

        for char in json_str:
            if escape_next:
                escape_next = False
                continue
            if char == '\\' and in_string:
                escape_next = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == '{':
                depth_brace += 1
            elif char == '}':
                depth_brace -= 1
            elif char == '[':
                depth_bracket += 1
            elif char == ']':
                depth_bracket -= 1

        # Try closing unclosed braces/brackets
        if depth_brace > 0 or depth_bracket > 0:
            # Remove any trailing incomplete key-value pair
            json_str = re.sub(r',\s*"[^"]*"?\s*:?\s*$', '', json_str)
            json_str = re.sub(r',\s*$', '', json_str)

            # Close open brackets and braces
            json_str += ']' * depth_bracket
            json_str += '}' * depth_brace

            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass

        return None

    # =========================================================================
    # XML TAG PARSING
    # =========================================================================

    @staticmethod
    def parse_xml_tags(
        response: str,
        tag_name: str,
        allow_nested_close: bool = False
    ) -> List[Dict[str, str]]:
        """
        Safely parse XML-like tags from LLM responses.

        Unlike naive regex, this handles:
        - Content containing literal </tag> strings (by tracking depth)
        - Tags with attributes
        - Multiple occurrences

        Args:
            response: Raw response text
            tag_name: Tag name to extract (e.g., 'file', 'plan')
            allow_nested_close: If True, handles nested same-name tags

        Returns:
            List of dicts with 'content' and any attributes
        """
        results = []
        pos = 0

        while pos < len(response):
            # Find opening tag
            open_pattern = re.compile(
                rf'<{re.escape(tag_name)}(\s[^>]*)?>',
                re.IGNORECASE
            )
            open_match = open_pattern.search(response, pos)
            if not open_match:
                break

            # Parse attributes from opening tag
            attrs = {}
            attrs_str = open_match.group(1) or ""
            if attrs_str:
                attr_pattern = r'(\w+)\s*=\s*["\']([^"\']*)["\']'
                for attr_match in re.finditer(attr_pattern, attrs_str):
                    attrs[attr_match.group(1)] = attr_match.group(2)

            content_start = open_match.end()

            # Find matching closing tag (handle nesting)
            close_tag = f'</{tag_name}>'
            if allow_nested_close:
                # Track nesting depth
                depth = 1
                search_pos = content_start
                open_tag_pattern = re.compile(rf'<{re.escape(tag_name)}(\s[^>]*)?>|</{re.escape(tag_name)}>')

                while depth > 0 and search_pos < len(response):
                    next_match = open_tag_pattern.search(response, search_pos)
                    if not next_match:
                        break
                    if next_match.group(0).startswith('</'):
                        depth -= 1
                        if depth == 0:
                            content_end = next_match.start()
                            pos = next_match.end()
                    else:
                        depth += 1
                    search_pos = next_match.end()

                if depth > 0:
                    # Unclosed tag — take everything until end
                    content_end = len(response)
                    pos = len(response)
            else:
                # Simple: find first closing tag
                close_pos = response.find(close_tag, content_start)
                if close_pos == -1:
                    # No closing tag — take everything to end
                    content_end = len(response)
                    pos = len(response)
                else:
                    content_end = close_pos
                    pos = close_pos + len(close_tag)

            content = response[content_start:content_end].strip()
            results.append({'content': content, **attrs})

        return results

    @staticmethod
    def extract_file_blocks(response: str) -> List[Dict[str, str]]:
        """
        Extract file blocks from LLM response.
        Handles both <file path="...">...</file> and ```lang:path ... ``` formats.

        Returns:
            List of dicts with 'path' and 'content' keys
        """
        files = []

        # Strategy 1: XML-style file tags
        xml_files = OutputParser.parse_xml_tags(response, 'file')
        for f in xml_files:
            if 'path' in f and 'content' in f:
                files.append({'path': f['path'], 'content': f['content']})

        # Strategy 2: Also try <newfile> tags
        newfiles = OutputParser.parse_xml_tags(response, 'newfile')
        for f in newfiles:
            if 'path' in f and 'content' in f:
                files.append({'path': f['path'], 'content': f['content']})

        # Strategy 3: Markdown code blocks with file path comments
        # Pattern: ```lang\n// filepath: path/to/file\n...```
        md_pattern = r'```\w*\n(?://|#)\s*(?:filepath|file):\s*([^\n]+)\n([\s\S]*?)```'
        for match in re.finditer(md_pattern, response):
            files.append({'path': match.group(1).strip(), 'content': match.group(2).strip()})

        return files

    @staticmethod
    def extract_patch_blocks(response: str) -> List[Dict[str, str]]:
        """
        Extract patch/diff blocks from LLM response.

        Returns:
            List of dicts with 'path' and 'diff' keys
        """
        patches = []

        # XML-style patch tags
        xml_patches = OutputParser.parse_xml_tags(response, 'patch')
        for p in xml_patches:
            content = p.get('content', '')
            path = p.get('path', '')

            # Extract path from diff headers if not in attributes
            if not path:
                path_match = re.search(r'^(?:\+\+\+|---)\s+[ab]/(.+)$', content, re.MULTILINE)
                if path_match:
                    path = path_match.group(1)

            if path and content:
                patches.append({'path': path, 'diff': content})

        return patches
