from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExperimentPlan:
    research_question: str
    hypothesis: str = ""
    target_dataset: str = ""
    candidate_methods: list[str] = field(default_factory=list)
    baseline_methods: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    experiment_goal: str = ""
    experimental_setup: str = ""
    ablation_plan: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)
    implementation_status: str = "placeholder"


@dataclass
class ResearchProposal:
    title: str
    source_title: str | None = None
    research_area: str = ""
    current_state: str = ""
    unresolved_problem: str = ""
    unexplored_direction: str = ""
    evidence: list[str] = field(default_factory=list)
    why_now: str = ""
    validation_status: str = "needs_literature_check"
    motivation: str = ""
    proposal: str = ""
    novelty_angle: str = ""
    critique: list[str] = field(default_factory=list)
    experiment_plan: ExperimentPlan | None = None
    next_steps: list[str] = field(default_factory=list)
