"""Structured JSON / Pydantic parse examples."""

from typing import List, Literal

from pydantic import BaseModel, Field

from jimmy import Jimmy


class CalendarEvent(BaseModel):
    name: str
    date: str = Field(description="ISO date YYYY-MM-DD")
    participants: List[str]
    location: str


class Sentiment(BaseModel):
    label: Literal["positive", "neutral", "negative"]
    confidence: float = Field(ge=0, le=1)
    rationale: str


def main() -> None:
    client = Jimmy()

    print("=== json_object ===")
    r = client.chat.completions.create(
        model="llama3.1-8B",
        messages=[
            {
                "role": "user",
                "content": 'Return JSON with keys "city" and "country" for the capital of France.',
            }
        ],
        response_format={"type": "json_object"},
    )
    print(r.choices[0].message.content)
    print("parsed:", r.choices[0].message.parsed)

    print("\n=== json_schema ===")
    r2 = client.chat.completions.create(
        model="llama3.1-8B",
        messages=[{"role": "user", "content": "Classify: 'I love this SDK!'"}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "sentiment",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "enum": ["positive", "neutral", "negative"]},
                        "confidence": {"type": "number"},
                        "rationale": {"type": "string"},
                    },
                    "required": ["label", "confidence", "rationale"],
                    "additionalProperties": False,
                },
            },
        },
    )
    print(r2.choices[0].message.parsed)

    print("\n=== parse(Pydantic) ===")
    r3 = client.chat.completions.parse(
        model="llama3.1-8B",
        messages=[
            {
                "role": "user",
                "content": "Extract event: Alice and Bob meet for Product sync on 2026-08-01 in SF.",
            }
        ],
        response_format=CalendarEvent,
    )
    event = r3.choices[0].message.parsed
    assert isinstance(event, CalendarEvent)
    print(event.model_dump())

    client.close()


if __name__ == "__main__":
    main()
