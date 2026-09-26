"""Tool calling + agentic loop example."""

from jimmy import Jimmy


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name"},
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add",
            "description": "Add two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                },
                "required": ["a", "b"],
            },
        },
    },
]


def get_weather(city: str, unit: str = "celsius") -> dict:
    temp = 22 if unit == "celsius" else 72
    return {"city": city, "temp": temp, "unit": unit, "conditions": "sunny"}


def add(a: float, b: float) -> float:
    return a + b


def main() -> None:
    client = Jimmy()

    # Single-shot: ask model to call a tool
    print("=== single completion with tools ===")
    r = client.chat.completions.create(
        model="llama3.1-8B",
        messages=[{"role": "user", "content": "What is the weather in Paris in celsius?"}],
        tools=TOOLS,
        tool_choice="auto",
    )
    msg = r.choices[0].message
    print("finish_reason:", r.choices[0].finish_reason)
    print("content:", msg.content)
    if msg.tool_calls:
        for tc in msg.tool_calls:
            print("tool_call:", tc.function.name, tc.function.arguments)

    # Agentic loop: SDK executes tools until a final answer
    print("\n=== run_tools agent loop ===")
    final = client.chat.completions.run_tools(
        model="llama3.1-8B",
        messages=[{"role": "user", "content": "What's 41 + 1, then tell me weather in Tokyo?"}],
        tools=TOOLS,
        functions={"get_weather": get_weather, "add": add},
        max_rounds=5,
    )
    print(final.choices[0].message.content)
    client.close()


if __name__ == "__main__":
    main()
