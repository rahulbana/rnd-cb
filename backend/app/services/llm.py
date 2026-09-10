from openai import OpenAI

from app.config import settings
from app.models import MeetingNotes

SYSTEM_PROMPT = """You are an expert meeting assistant. You read a raw meeting \
transcript and extract structured, useful notes.

Guidelines:
- summary: 3-6 sentences capturing the purpose, key discussion points, and outcomes.
- participants: names of people who spoke or were clearly present. Deduplicate.
- decisions: concrete decisions the group agreed on. Empty list if none.
- action_items: tasks to be done. Include the owner and deadline when they are stated; \
use null when they are not mentioned. Do not invent owners or dates.
- deadlines: any dates or timeframes tied to specific deliverables.
- follow_up_email: a concise, professional follow-up email recapping the meeting, \
the decisions, and each person's action items.

Only use information present in the transcript. Never fabricate facts."""


def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to backend/.env before generating notes."
        )
    return OpenAI(api_key=settings.openai_api_key)


def generate_notes(transcript: str, meeting_title: str | None = None) -> MeetingNotes:
    """Send the transcript to the LLM and parse structured meeting notes."""
    client = _client()

    user_content = transcript
    if meeting_title:
        user_content = f"Meeting title: {meeting_title}\n\nTranscript:\n{transcript}"

    completion = client.beta.chat.completions.parse(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format=MeetingNotes,
        temperature=0.2,
    )

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError("The model did not return structured notes. Please try again.")
    return parsed
