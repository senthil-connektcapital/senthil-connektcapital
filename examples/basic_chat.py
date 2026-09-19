"""Basic chat example."""

from jimmy import Jimmy


def main() -> None:
    client = Jimmy()
    completion = client.chat.completions.create(
        model="llama3.1-8B",
        messages=[
            {"role": "system", "content": "You are a concise assistant."},
            {"role": "user", "content": "Explain what an LLM is in one sentence."},
        ],
    )
    print(completion.choices[0].message.content)
    if completion.usage:
        print(
            f"tokens: prompt={completion.usage.prompt_tokens} "
            f"completion={completion.usage.completion_tokens} "
            f"total={completion.usage.total_tokens}"
        )
    client.close()


if __name__ == "__main__":
    main()
