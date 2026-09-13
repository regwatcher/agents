"""Communicator agent: outreach strategy and templates."""

from pydantic import BaseModel, Field
from agents import Agent

from model_env import DEFAULT_MODEL
from scrape_website_tool import scrape_website
from serper_tool import serper_search

INSTRUCTIONS = (
    "Role: Candidate Outreach Strategist.\n"
    "Goal: Develop outreach strategies for the selected candidates.\n"
    "Backstory: You are skilled at creating effective outreach strategies and "
    "templates to engage candidates. Your communication tactics ensure high response "
    "rates from potential candidates.\n\n"
    "Task: Develop a comprehensive strategy to reach out to the selected candidates. "
    "Create effective outreach methods and templates that engage candidates and "
    "encourage them to consider the job opportunity. You may use serper_search "
    "and scrape_website for public context only—do not scrape LinkedIn profiles.\n\n"
    "Expected output: A detailed list of outreach methods and templates ready for "
    "implementation, including communication strategies and engagement tactics. "
    "markdown_outreach should include personalized email templates, LinkedIn messages, "
    "call scripts, and a recommended follow-up cadence; per_candidate should cover "
    "each priority candidate."
)


class CandidateOutreach(BaseModel):
    candidate_name: str
    linkedin_url: str = ""
    email_template: str = Field(description="Personalized email body (markdown or plain text).")
    linkedin_message: str
    call_script: str


class OutreachPlan(BaseModel):
    markdown_outreach: str = Field(description="Full outreach strategy in markdown.")
    per_candidate: list[CandidateOutreach] = Field(
        description="Templates per priority candidate.",
    )
    follow_up_calendar: str = Field(
        default="",
        description="Recommended follow-up schedule (text/markdown).",
    )


communicator_agent = Agent(
    name="CommunicatorAgent",
    instructions=INSTRUCTIONS,
    tools=[serper_search, scrape_website],
    model=DEFAULT_MODEL,
    output_type=OutreachPlan,
)
