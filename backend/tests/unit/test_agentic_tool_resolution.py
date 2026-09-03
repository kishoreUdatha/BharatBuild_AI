"""
The agentic endpoint used to ignore the tool definitions and system prompt the
client sent — neither field existed on AgenticRequest, so pydantic dropped them
and every call fell back to the hardcoded AGENTIC_TOOLS.

The CLI is the process that actually executes tools, so the model was being
offered a toolset the CLI had never registered: calls to `edit_file` and
`list_directory` came back to the user as "Unknown tool", while the CLI's own
tools were never offered at all.
"""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.endpoints.agentic import (
    AGENTIC_TOOLS,
    MAX_CLIENT_TOOLS,
    MAX_CLIENT_SYSTEM_CHARS,
    AgenticRequest,
    resolve_tools,
    resolve_system_prompt,
)


def make_request(**kwargs) -> AgenticRequest:
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    payload.update(kwargs)
    return AgenticRequest(**payload)


def tool(name: str, **schema) -> dict:
    return {
        "name": name,
        "description": f"{name} tool",
        "input_schema": schema or {"type": "object", "properties": {}},
    }


class TestRequestModel:
    def test_tools_and_system_survive_parsing(self):
        # Previously dropped silently because the fields were not declared.
        req = make_request(tools=[tool("my_tool")], system="custom prompt")
        assert req.tools is not None
        assert req.tools[0]["name"] == "my_tool"
        assert req.system == "custom prompt"

    def test_both_default_to_none(self):
        req = make_request()
        assert req.tools is None
        assert req.system is None


class TestResolveTools:
    def test_client_tools_win(self):
        req = make_request(tools=[tool("bb_custom_writer")])
        assert [t["name"] for t in resolve_tools(req)] == ["bb_custom_writer"]

    def test_falls_back_to_server_defaults(self):
        # The web UI sends no tools; it must keep working unchanged.
        assert resolve_tools(make_request()) is AGENTIC_TOOLS

    def test_empty_list_falls_back(self):
        assert resolve_tools(make_request(tools=[])) is AGENTIC_TOOLS

    def test_rejects_duplicate_names(self):
        # Providers reject repeated tool names without saying which one.
        req = make_request(tools=[tool("dup"), tool("dup")])
        with pytest.raises(HTTPException) as exc:
            resolve_tools(req)
        assert exc.value.status_code == 400
        assert "dup" in exc.value.detail

    def test_rejects_missing_name(self):
        req = make_request(tools=[{"input_schema": {"type": "object"}}])
        with pytest.raises(HTTPException) as exc:
            resolve_tools(req)
        assert exc.value.status_code == 400
        assert "name" in exc.value.detail

    def test_rejects_missing_input_schema(self):
        req = make_request(tools=[{"name": "bad"}])
        with pytest.raises(HTTPException) as exc:
            resolve_tools(req)
        assert exc.value.status_code == 400
        assert "input_schema" in exc.value.detail

    def test_rejects_non_object_entry_at_the_model_layer(self):
        # pydantic's List[Dict[str, Any]] already refuses this, so the request
        # never reaches resolve_tools. Assert that contract rather than the
        # unreachable defensive branch inside it.
        with pytest.raises(ValidationError):
            make_request(tools=["not-a-tool"])

    def test_rejects_oversized_toolset(self):
        req = make_request(tools=[tool(f"t{i}") for i in range(MAX_CLIENT_TOOLS + 1)])
        with pytest.raises(HTTPException) as exc:
            resolve_tools(req)
        assert exc.value.status_code == 400
        assert "Too many tools" in exc.value.detail

    def test_accepts_a_full_sized_toolset(self):
        req = make_request(tools=[tool(f"t{i}") for i in range(MAX_CLIENT_TOOLS)])
        assert len(resolve_tools(req)) == MAX_CLIENT_TOOLS


class TestResolveSystemPrompt:
    def test_client_prompt_wins(self):
        # The client's prompt describes the tools it actually has.
        req = make_request(system="You are a test agent.")
        assert resolve_system_prompt(req) == "You are a test agent."

    def test_falls_back_and_interpolates_working_dir(self):
        req = make_request(working_dir="/srv/project")
        resolved = resolve_system_prompt(req)
        assert "/srv/project" in resolved
        assert "{working_dir}" not in resolved

    def test_rejects_an_oversized_prompt(self):
        req = make_request(system="x" * (MAX_CLIENT_SYSTEM_CHARS + 1))
        with pytest.raises(HTTPException) as exc:
            resolve_system_prompt(req)
        assert exc.value.status_code == 400


class TestServerDefaults:
    def test_defaults_are_still_well_formed(self):
        names = set()
        for entry in AGENTIC_TOOLS:
            assert entry["name"] not in names, f"duplicate default tool {entry['name']}"
            names.add(entry["name"])
            assert isinstance(entry["input_schema"], dict)
