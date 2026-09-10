from pydantic import BaseModel, Field


class TranscriptRequest(BaseModel):
    """Incoming meeting transcript to analyze."""

    transcript: str = Field(..., min_length=1, description="Raw meeting transcript text.")
    meeting_title: str | None = Field(None, description="Optional meeting title for context.")


class ActionItem(BaseModel):
    task: str = Field(..., description="What needs to be done.")
    owner: str | None = Field(None, description="Person responsible, if identified.")
    deadline: str | None = Field(None, description="Due date or timeframe, if mentioned.")


class Deadline(BaseModel):
    description: str = Field(..., description="What the deadline is for.")
    due: str = Field(..., description="The date or timeframe mentioned.")


class MeetingNotes(BaseModel):
    """Structured notes extracted from a meeting transcript."""

    summary: str = Field(..., description="Concise summary of the meeting.")
    participants: list[str] = Field(default_factory=list, description="People who took part.")
    decisions: list[str] = Field(default_factory=list, description="Decisions that were made.")
    action_items: list[ActionItem] = Field(default_factory=list, description="Tasks with owners.")
    deadlines: list[Deadline] = Field(default_factory=list, description="Dates to track.")
    follow_up_email: str = Field(..., description="Draft follow-up email to send to attendees.")
