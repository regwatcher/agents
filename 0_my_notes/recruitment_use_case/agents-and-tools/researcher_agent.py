"""Researcher agent: discover candidates (Serper, scrape sites, LinkedIn profile scrape)."""

from pydantic import BaseModel, Field
from agents import Agent

from linkedin_tool import scrape_linkedin_profiles
from model_env import DEFAULT_MODEL
from scrape_website_tool import scrape_website
from serper_tool import serper_search

INSTRUCTIONS = (
    "Role: Job Candidate Researcher.\n"
    "Goal: Find potential candidates for the job.\n"
    "Backstory: You are adept at finding the right candidates by exploring various "
    "online resources. Your skill in identifying suitable candidates ensures the "
    "best match for job positions.\n\n"
    "Task: Conduct thorough research to find potential candidates for the specified "
    "job. Utilize various online resources and databases to gather a comprehensive "
    "list of potential candidates. Ensure that the candidates meet the job "
    "requirements provided.\n\n"
    "Tools available:\n"
    "- serper_search: Google search via Serper (e.g. site:linkedin.com/in plus role keywords).\n"
    "- scrape_website: fetch and extract text from public web pages (not for bypassing LinkedIn login).\n"
    "- scrape_linkedin_profiles: after you have https://www.linkedin.com/in/... URLs, "
    "pass them (comma or newline separated) to enrich profiles.\n\n"
    "Expected output: As many potential candidates as the **target count** given in "
    "the user message for this run, with contact information where available and brief "
    "profiles highlighting their suitability. Produce "
    "markdown_candidates as a summary table plus one short section per candidate, "
    "and fill the structured candidates list to match."
)


class EnrichedCandidate(BaseModel):
    name: str = Field(description="Candidate name after enrichment.")
    title: str = Field(description="Professional title.")
    location: str = Field(default="", description="Location.")
    linkedin_url: str = Field(description="LinkedIn profile URL.")
    key_experience: str = Field(
        default="",
        description="Brief summary of relevant experience.",
    )


class CandidateList(BaseModel):
    markdown_candidates: str = Field(
        description="Markdown: summary table and brief profiles for each candidate (match target count in prompt)."
    )
    candidates: list[EnrichedCandidate] = Field(
        description="Structured list matching the target candidate count from the user message.",
    )


researcher_agent = Agent(
    name="ResearcherAgent",
    instructions=INSTRUCTIONS,
    tools=[serper_search, scrape_website, scrape_linkedin_profiles],
    model=DEFAULT_MODEL,
    output_type=CandidateList,
)
