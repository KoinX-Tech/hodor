import importlib

import pytest

pytest.importorskip("openhands.sdk", reason="OpenHands SDK is required to import openhands_client module")

from hodor.llm.openhands_client import (
    _detect_model_family,
    _MODEL_FAMILY_CANONICAL,
    describe_model,
    get_api_key,
)

# pytest's assertion rewriter can interfere with sub-module resolution for
# namespace-style packages.  Use importlib to bypass this and register the
# sub-modules in sys.modules before accessing them by name.
_llm_message = importlib.import_module("openhands.sdk.llm.message")
Message = _llm_message.Message
ReasoningItemModel = _llm_message.ReasoningItemModel
TextContent = _llm_message.TextContent
MessageToolCall = _llm_message.MessageToolCall

_responses_opts = importlib.import_module("openhands.sdk.llm.options.responses_options")
select_responses_options = _responses_opts.select_responses_options

_reasoning_item = importlib.import_module("openai.types.responses.response_reasoning_item")
ResponseReasoningItem = _reasoning_item.ResponseReasoningItem
Summary = _reasoning_item.Summary

_output_message = importlib.import_module("openai.types.responses.response_output_message")
ResponseOutputMessage = _output_message.ResponseOutputMessage

_output_text = importlib.import_module("openai.types.responses.response_output_text")
ResponseOutputText = _output_text.ResponseOutputText

_function_tool_call = importlib.import_module("openai.types.responses.response_function_tool_call")
ResponseFunctionToolCall = _function_tool_call.ResponseFunctionToolCall


@pytest.fixture(autouse=True)
def clear_llm_env(monkeypatch):
    """Ensure API key environment variables do not leak between tests."""
    for var in ("LLM_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION_NAME", "AWS_PROFILE"):
        monkeypatch.delenv(var, raising=False)


@pytest.mark.parametrize(
    "model,normalized,supports_reasoning,effort",
    [
        ("gpt-5", "openai/gpt-5", True, "medium"),
        ("openai/gpt-5-2025-08-07", "openai/gpt-5-2025-08-07", True, "medium"),
        ("gpt-5-codex", "openai/gpt-5-codex", True, "medium"),
        ("openai/gpt-5-codex-latest", "openai/gpt-5-codex-latest", True, "medium"),
        ("gpt-5.1-codex", "openai/gpt-5.1-codex", True, "medium"),
        ("gpt-5.1-codex-mini", "openai/gpt-5.1-codex-mini", True, "medium"),
        ("gpt-5-mini", "openai/gpt-5-mini", True, "medium"),
        ("openai/responses/gpt-5-mini", "openai/gpt-5-mini", True, "medium"),
        ("o3-mini", "openai/o3-mini", True, "medium"),
        ("o1-preview", "openai/o1-preview", True, "medium"),
        ("anthropic/claude-sonnet-4-5", "anthropic/claude-sonnet-4-5", False, "none"),
        ("bedrock/anthropic.claude-opus-4-6-v1", "bedrock/anthropic.claude-opus-4-6-v1", False, "none"),
        ("bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0", "bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0", False, "none"),
    ],
)
def test_describe_model_normalization(model, normalized, supports_reasoning, effort):
    metadata = describe_model(model)
    assert metadata.normalized == normalized
    assert metadata.supports_reasoning == supports_reasoning
    assert metadata.default_reasoning_effort == effort


def test_describe_model_requires_value():
    with pytest.raises(ValueError):
        describe_model("")


def test_get_api_key_prefers_llm_override(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-universal")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")

    assert get_api_key("openai/gpt-4o") == "sk-universal"


def test_get_api_key_prefers_openai_for_openai_models(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")

    assert get_api_key("openai/gpt-4o") == "sk-openai"


def test_get_api_key_prefers_anthropic_for_anthropic_models(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")

    assert get_api_key("anthropic/claude-sonnet-4-5") == "sk-anthropic"


def test_get_api_key_fallback_order_without_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")

    assert get_api_key() == "sk-anthropic"


def test_get_api_key_returns_none_for_bedrock():
    """Bedrock uses AWS credentials, not an API key."""
    assert get_api_key("bedrock/anthropic.claude-opus-4-6-v1") is None


def test_get_api_key_raises_when_missing(monkeypatch):
    with pytest.raises(RuntimeError):
        get_api_key("openai/gpt-4o")


class _DummyLLM:
    def __init__(self, enable_encrypted_reasoning: bool):
        self.max_output_tokens = None
        self.extra_headers = None
        self.reasoning_effort = None
        self.reasoning_summary = None
        self.model = "openai/gpt-5"
        self.litellm_extra_body = None
        self.enable_encrypted_reasoning = enable_encrypted_reasoning
        self.is_subscription = False
        self.prompt_cache_retention = None


def test_responses_options_respects_encrypted_flag():
    opts_enabled = select_responses_options(
        _DummyLLM(True), {}, include=None, store=None
    )
    assert "reasoning.encrypted_content" in opts_enabled.get("include", [])

    opts_disabled = select_responses_options(
        _DummyLLM(False), {}, include=None, store=None
    )
    assert "reasoning.encrypted_content" not in opts_disabled.get("include", [])


# --- _detect_model_family tests ---


@pytest.mark.parametrize(
    "model,expected",
    [
        ("anthropic/claude-opus-4-5", "opus"),
        ("bedrock/anthropic.claude-opus-4-6-v1", "opus"),
        ("anthropic/claude-sonnet-4-5", "sonnet"),
        ("bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0", "sonnet"),
        ("bedrock/converse/arn:aws:bedrock:us-west-2:123:inference-profile/sonnet", "sonnet"),
        ("anthropic/claude-haiku-4-5", "haiku"),
        ("bedrock/converse/arn:aws:bedrock:us-west-2:123:inference-profile/haiku", "haiku"),
        ("openai/gpt-4o", None),
        ("bedrock/converse/arn:aws:bedrock:us-west-2:123:inference-profile/unknown", None),
    ],
)
def test_detect_model_family(model, expected):
    assert _detect_model_family(model) == expected


def test_model_family_canonical_covers_all_families():
    """Every detected family must have a canonical name mapping."""
    for family in ("opus", "sonnet", "haiku"):
        assert family in _MODEL_FAMILY_CANONICAL, f"{family} missing from _MODEL_FAMILY_CANONICAL"
        assert isinstance(_MODEL_FAMILY_CANONICAL[family], str)


# --- Responses API reasoning item regression tests ---


def test_reasoning_item_stripped_at_parse_time():
    """Regression: reasoning items from the API response must not survive into
    the Message, otherwise to_responses_dict() replays them on subsequent turns.
    With store=False this causes 'Item with id rs_... not found' errors."""
    reasoning = ResponseReasoningItem(
        id="rs_test_regression",
        type="reasoning",
        summary=[Summary(text="thinking step", type="summary_text")],
    )
    msg_output = ResponseOutputMessage.model_construct(
        id="m1",
        type="message",
        role="assistant",
        status="completed",
        content=[ResponseOutputText(type="output_text", text="review result", annotations=[])],
    )

    parsed = Message.from_llm_responses_output(output=[reasoning, msg_output])

    # Reasoning item must be stripped at parse time
    assert parsed.responses_reasoning_item is None
    # Assistant text must be preserved
    assert any(c.text == "review result" for c in parsed.content)


def test_reasoning_strip_preserves_tool_calls():
    """Verify that stripping reasoning items does not affect tool call parsing."""
    reasoning = ResponseReasoningItem(
        id="rs_tool_test", type="reasoning", summary=[],
    )
    tool_call = ResponseFunctionToolCall(
        type="function_call", name="terminal", arguments='{"command": "ls"}',
        call_id="fc_1", id="fc_1",
    )

    parsed = Message.from_llm_responses_output(output=[reasoning, tool_call])

    assert parsed.responses_reasoning_item is None
    assert parsed.tool_calls is not None
    assert len(parsed.tool_calls) == 1
    assert parsed.tool_calls[0].name == "terminal"


def test_no_reasoning_items_in_serialized_output():
    """End-to-end: after parse-time stripping, to_responses_dict must not
    contain any reasoning items."""
    reasoning = ResponseReasoningItem(
        id="rs_serial_test", type="reasoning", summary=[],
    )
    msg_output = ResponseOutputMessage.model_construct(
        id="m1",
        type="message",
        role="assistant",
        status="completed",
        content=[ResponseOutputText(type="output_text", text="hello", annotations=[])],
    )

    parsed = Message.from_llm_responses_output(output=[reasoning, msg_output])
    items = parsed.to_responses_dict(vision_enabled=False)

    reasoning_items = [
        i for i in items if isinstance(i, dict) and i.get("type") == "reasoning"
    ]
    assert reasoning_items == [], f"Expected no reasoning items, got {reasoning_items}"
    # Other items should still be present
    assert len(items) > 0
