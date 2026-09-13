"""Reporter agent: executive summary for recruiters."""

from pydantic import BaseModel, Field
from agents import Agent

from model_env import DEFAULT_MODEL

INSTRUCTIONS = (
    "Role: Candidate Reporting Specialist.\n"
    "Goal: Report the best candidates to the recruiters.\n"
    "Backstory: You are proficient at compiling and presenting detailed reports for "
    "recruiters. Your reports provide clear insights into the best candidates to pursue.\n\n"
    "Task: Compile a comprehensive report for recruiters on the best candidates to put "
    "forward. Summarize the findings from the previous steps and provide clear "
    "recommendations based on the job requirements.\n\n"
    "Expected output: A detailed report with the best candidates to pursue, formatted "
    "as markdown without fenced code blocks (no ```). Include profiles, scores, and "
    "outreach strategies. Do not paste the full job requirements verbatim—summarize. "
    "markdown_report should include an executive summary, top candidates, scores and "
    "justifications, outreach angles, and recommended next steps."
)


class RecruitmentReport(BaseModel):
    short_summary: str = Field(description="Short summary, 2–4 sentences.")
    markdown_report: str = Field(description="Final executive report in markdown.")
    top_candidates: list[str] = Field(
        description="Names of up to 5 priority candidates.",
    )
    follow_up_questions: list[str] = Field(
        default_factory=list,
        description="Topics for the recruiter to clarify.",
    )


reporter_agent = Agent(
    name="ReporterAgent",
    instructions=INSTRUCTIONS,
    model=DEFAULT_MODEL,
    output_type=RecruitmentReport,
)
