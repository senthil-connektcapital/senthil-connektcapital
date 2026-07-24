from jimmy.tools import parse_tool_calls, strip_tool_call_markup, build_tools_system_prompt
from jimmy._parsing import split_stats, build_completion


def test_parse_tool_call_xml():
    text = """<tool_call>
{"name": "get_weather", "arguments": {"city": "Paris"}}
</tool_call>"""
    calls = parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].function.name == "get_weather"
    assert '"city": "Paris"' in calls[0].function.arguments or '"city":"Paris"' in calls[0].function.arguments.replace(
        " ", ""
    )


def test_parse_multiple_tool_calls():
    text = """
<tool_call>
{"name": "add", "arguments": {"a": 1, "b": 2}}
</tool_call>
<tool_call>
{"name": "get_weather", "parameters": {"city": "Tokyo"}}
</tool_call>
"""
    calls = parse_tool_calls(text)
    assert len(calls) == 2
    names = {c.function.name for c in calls}
    assert names == {"add", "get_weather"}


def test_parse_python_tag():
    text = '<|python_tag|>{"name": "add", "parameters": {"a": 3, "b": 4}}'
    calls = parse_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].function.name == "add"


def test_strip_markup():
    text = 'Sure.\n<tool_call>\n{"name": "x", "arguments": {}}\n</tool_call>'
    assert "tool_call" not in strip_tool_call_markup(text)
    assert "Sure." in strip_tool_call_markup(text)


def test_split_stats():
    body = 'Hello world\n<|stats|>{"prefill_tokens":10,"decode_tokens":2,"total_tokens":12}<|/stats|>'
    text, stats = split_stats(body)
    assert text == "Hello world"
    assert stats["prefill_tokens"] == 10


def test_build_completion_with_tools():
    text = '<tool_call>\n{"name": "add", "arguments": {"a": 1, "b": 2}}\n</tool_call>'
    c = build_completion(model="llama3.1-8B", text=text, raw_body=text, enable_tools=True)
    assert c.choices[0].finish_reason == "tool_calls"
    assert c.choices[0].message.tool_calls
    assert c.choices[0].message.tool_calls[0].function.name == "add"


def test_build_completion_plain():
    c = build_completion(model="llama3.1-8B", text="hi", raw_body="hi", enable_tools=False)
    assert c.choices[0].finish_reason == "stop"
    assert c.choices[0].message.content == "hi"
    assert c.choices[0].message.tool_calls is None


def test_tools_system_prompt_contains_schema():
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "weather",
                "parameters": {"type": "object", "properties": {"city": {"type": "string"}}},
            },
        }
    ]
    prompt = build_tools_system_prompt(tools)
    assert "get_weather" in prompt
    assert "<tool_call>" in prompt
