from __future__ import annotations

from labcrew.agents.base import BaseAgent
from labcrew.schemas import ExperimentPlan, Paper, PaperCardReport, PaperReadingReport, ResearchProposal, Task, TaskResult


class ProposalAgent(BaseAgent):
    name = "proposal"

    def run(self, task: Task) -> TaskResult:
        paper = task.payload.get("paper")
        report = task.payload.get("report")
        card_report = task.payload.get("card_report")
        question = str(task.payload.get("research_question") or task.payload.get("question") or "")

        if isinstance(paper, Paper):
            proposal = self._proposal_from_paper(paper, report, card_report, question)
            return TaskResult(task_id=task.task_id, agent_name=self.name, data=proposal)

        if question:
            proposal = self._proposal_from_question(question, task.payload)
            return TaskResult(task_id=task.task_id, agent_name=self.name, data=proposal)

        raise ValueError("ProposalAgent requires a Paper payload or a research question.")

    def _proposal_from_paper(
        self,
        paper: Paper,
        report: object,
        card_report: object,
        question: str,
    ) -> ResearchProposal:
        summary = self._summary_text(report, card_report)
        research_area = question or self._research_area_from_paper(paper, report, card_report)
        unresolved_problem = self._gap_from_report(report, card_report)
        unexplored_direction = self._direction_from_paper(paper, unresolved_problem)
        evidence = self._evidence_from_report(report, card_report, paper)
        critique = self._checks_for_gap_claim(report, card_report)
        research_question = f"Can {unexplored_direction.lower()} address: {unresolved_problem.lower()}?"
        experiment_plan = self._experiment_plan(
            research_question=research_question,
            hypothesis=f"If this underexplored direction is real, a focused prototype should improve or clarify the unresolved problem observed around {paper.title}.",
            candidate_methods=[paper.title],
            baseline_methods=["Strong recent baseline", "Simple controlled baseline"],
            metrics=["Primary task metric", "Robustness metric", "Efficiency or cost metric"],
            constraints=["Keep the first experiment small enough to run manually before automation."],
        )
        return ResearchProposal(
            title=f"Research gap from: {paper.title}",
            source_title=paper.title,
            research_area=research_area,
            current_state=summary,
            unresolved_problem=unresolved_problem,
            unexplored_direction=unexplored_direction,
            evidence=evidence,
            why_now="The read paper supplies enough method and experiment evidence to form a candidate gap, but the claim still needs validation against broader literature.",
            validation_status="candidate_gap_from_read_paper",
            motivation=summary,
            proposal=f"Treat the gap as a new task direction: {unexplored_direction}. Build a small benchmark slice or prototype that makes the missing capability measurable.",
            novelty_angle="The novelty is the problem framing and evaluation target first; method changes should stay minimal until the gap is confirmed.",
            critique=critique,
            experiment_plan=experiment_plan,
            next_steps=[
                "Check Zotero or a paper search source for recent work that may already cover this gap.",
                "Turn the gap into one falsifiable task definition and one success metric.",
                "Pick one dataset slice and one strong baseline before designing a larger study.",
            ],
        )

    def _proposal_from_question(self, question: str, payload: dict[str, object]) -> ResearchProposal:
        research_area = str(payload.get("research_area") or question)
        current_state = str(
            payload.get("current_state")
            or "Literature state is not attached yet. Treat this as a seed area that needs Zotero/search-backed validation."
        )
        unresolved_problem = str(
            payload.get("unresolved_problem")
            or f"What important capability, setting, or evaluation target is still weakly covered in: {question}?"
        )
        unexplored_direction = str(
            payload.get("unexplored_direction")
            or f"Define a concrete missing task direction inside {question}, then verify whether recent work has already solved it."
        )
        experiment_plan = self._experiment_plan(
            research_question=unresolved_problem,
            hypothesis=str(payload.get("hypothesis") or ""),
            target_dataset=str(payload.get("target_dataset") or ""),
            candidate_methods=list(payload.get("candidate_methods", [])),
            baseline_methods=list(payload.get("baseline_methods", [])),
            metrics=list(payload.get("metrics", [])),
            constraints=list(payload.get("constraints", [])),
        )
        return ResearchProposal(
            title=f"Research direction: {question}",
            research_area=research_area,
            current_state=current_state,
            unresolved_problem=unresolved_problem,
            unexplored_direction=unexplored_direction,
            evidence=list(payload.get("evidence", [])),
            why_now=str(payload.get("why_now") or "This is a candidate direction until connected literature evidence confirms the gap."),
            validation_status="seed_direction_needs_literature_check",
            motivation=f"Use the seed area to discover a missing task or unresolved problem before locking onto a method.",
            proposal=f"Validate whether the direction is genuinely underexplored, then design a minimal study around: {unexplored_direction}",
            novelty_angle="The first novelty test is whether the task framing is new and useful; only then should the method become more ambitious.",
            critique=[
                "Do not claim nobody has done this until Zotero/search evidence is checked.",
                "Narrow the seed area into a task that can be measured in one experiment.",
                "Confirm that existing baselines would make a positive result meaningful.",
            ],
            experiment_plan=experiment_plan,
            next_steps=[
                "Attach 5-10 recent papers as the current-state evidence set.",
                "Write the missing task definition in one paragraph.",
                "Draft a metric table before writing experiment code.",
            ],
        )

    def _experiment_plan(
        self,
        research_question: str,
        hypothesis: str = "",
        target_dataset: str = "",
        candidate_methods: list[str] | None = None,
        baseline_methods: list[str] | None = None,
        metrics: list[str] | None = None,
        constraints: list[str] | None = None,
    ) -> ExperimentPlan:
        return ExperimentPlan(
            research_question=research_question,
            hypothesis=hypothesis,
            target_dataset=target_dataset,
            candidate_methods=candidate_methods or [],
            baseline_methods=baseline_methods or [],
            metrics=metrics or [],
            constraints=constraints or [],
            experiment_goal=f"Evaluate a concrete research proposal for: {research_question}",
            experimental_setup="Placeholder setup. Implementation hooks will be added in a later phase.",
            ablation_plan=["Test the smallest meaningful component or assumption change."],
            risk_notes=["This proposal module is intentionally scaffolded before real experiment automation."],
        )

    def _summary_text(self, report: object, card_report: object) -> str:
        if isinstance(card_report, PaperCardReport):
            return card_report.one_sentence_summary
        if isinstance(report, PaperReadingReport):
            return report.research_problem
        return "Use the read paper as evidence for a research proposal."

    def _research_area_from_paper(self, paper: Paper, report: object, card_report: object) -> str:
        if isinstance(report, PaperReadingReport) and report.research_problem:
            return report.research_problem
        if isinstance(card_report, PaperCardReport) and card_report.problem:
            return card_report.problem
        return paper.title

    def _gap_from_report(self, report: object, card_report: object) -> str:
        if isinstance(card_report, PaperCardReport) and card_report.limitations:
            return card_report.limitations
        if isinstance(report, PaperReadingReport) and report.limitations:
            return report.limitations
        if isinstance(report, PaperReadingReport) and report.experiments:
            return f"Existing experiments may not fully cover robustness, generalization, or realistic deployment around: {report.experiments}"
        return "The exact unresolved problem is not confirmed yet; use this paper as one evidence point and validate the gap with more literature."

    def _direction_from_paper(self, paper: Paper, unresolved_problem: str) -> str:
        if unresolved_problem and "not confirmed" not in unresolved_problem:
            return f"A benchmarked task that directly tests the limitation surfaced by {paper.title}"
        return f"An evidence-backed missing task direction adjacent to {paper.title}"

    def _evidence_from_report(self, report: object, card_report: object, paper: Paper) -> list[str]:
        evidence = [f"Seed paper: {paper.title}"]
        if isinstance(report, PaperReadingReport):
            if report.method:
                evidence.append(f"Method evidence: {report.method}")
            if report.experiments:
                evidence.append(f"Experiment evidence: {report.experiments}")
            if report.limitations:
                evidence.append(f"Limitation evidence: {report.limitations}")
        if isinstance(card_report, PaperCardReport) and card_report.limitations:
            evidence.append(f"Card limitation: {card_report.limitations}")
        return evidence

    def _checks_for_gap_claim(self, report: object, card_report: object) -> list[str]:
        checks = [
            "Validate the gap against recent related work before claiming novelty.",
            "Check whether baselines are recent, tuned, and fairly compared.",
            "Record code, dataset, hyperparameter, and compute availability.",
        ]
        if isinstance(card_report, PaperCardReport) and card_report.limitations:
            checks.insert(0, f"Seed limitation: {card_report.limitations}")
        elif isinstance(report, PaperReadingReport) and report.limitations:
            checks.insert(0, f"Seed limitation: {report.limitations}")
        return checks
