"""Streaming chat example."""

from jimmy import Jimmy


def main() -> None:
    client = Jimmy()
    stream = client.chat.completions.create(
        model="llama3.1-8B",
        messages=[{"role": "user", "content": "Count from 1 to 8, one number per line."}],
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            print(delta, end="", flush=True)
    print()
    client.close()


if __name__ == "__main__":
    main()
