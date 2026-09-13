"""Matcher agent: score and rank candidates vs job requirements."""

from pydantic import BaseModel, Field
from agents import Agent

from model_env import DEFAULT_MODEL
from scrape_website_tool import scrape_website
from serper_tool import serper_search

INSTRUCTIONS = (
    "Role: Candidate Matcher and Scorer.\n"
    "Goal: Match the candidates to the best jobs and score them.\n"
    "Backstory: You have a knack for matching the right candidates to the right job "
    "positions using advanced algorithms and scoring techniques. Your scores help "
    "prioritize the best candidates for outreach.\n\n"
    "Task: Evaluate and match the candidates to the best job positions based on "
    "their qualifications and suitability. Score each candidate to reflect their "
    "alignment with the job requirements, ensuring a fair and transparent assessment "
    "process. Do not scrape people's LinkedIn profiles—you may use serper_search "
    "and scrape_website for public sources only.\n\n"
    "Expected output: A ranked list of candidates with detailed scores and "
    "justifications for each job position. Provide markdown_scores with a ranking "
    "table and per-candidate analysis."
)


class CriterionScore(BaseModel):
    criterion: str
    score: float = Field(description="Numeric score, e.g. 0–10.")
    comment: str = ""


class RankedCandidate(BaseModel):
    name: str
    linkedin_url: str = ""
    overall_score: float = Field(description="Aggregate overall score.")
    criterion_scores: list[CriterionScore] = Field(default_factory=list)
    justification: str = Field(description="Qualitative analysis.")


class ScoredCandidates(BaseModel):
    markdown_scores: str = Field(description="Ranked markdown with table and analyses.")
    ranked: list[RankedCandidate] = Field(
        description="Candidates ranked from best fit downward.",
    )


matcher_agent = Agent(
    name="MatcherAgent",
    instructions=INSTRUCTIONS,
    tools=[serper_search, scrape_website],
    model=DEFAULT_MODEL,
    output_type=ScoredCandidates,
)
