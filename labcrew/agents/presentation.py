from __future__ import annotations

from labcrew.agents.base import BaseAgent
from labcrew.schemas import LiteratureCard, Slide, SlideMaterialLibrary, SlidePlan, Task, TaskResult


class PresentationAgent(BaseAgent):
    name = "presentation"

    def run(self, task: Task) -> TaskResult:
        card = task.payload.get("card")
        if not isinstance(card, LiteratureCard):
            raise ValueError("PresentationAgent requires a LiteratureCard payload.")
        material_library = task.payload.get("material_library")
        material_ids = self._material_ids(material_library)
        profile = str(task.payload.get("profile", "standard"))

        if profile == "ai-research":
            plan = self._ai_research_plan(task, card, material_library, material_ids)
            return TaskResult(task_id=task.task_id, agent_name=self.name, data=plan)
        if profile == "ai-survey":
            plan = self._ai_survey_plan(task, card, material_library, material_ids)
            return TaskResult(task_id=task.task_id, agent_name=self.name, data=plan)

        plan = SlidePlan(
            title=f"Paper Brief: {card.title}",
            audience=str(task.payload.get("audience", "research group")),
            duration_minutes=int(task.payload.get("duration_minutes", 10)),
            source_papers=[card.title],
            slides=[
                Slide(
                    title="Motivation",
                    purpose="Set up the research problem.",
                    key_message=self._compact(card.problem or card.one_sentence_summary),
                    bullets=self._compact_list([card.one_sentence_summary]),
                    layout="section",
                    material_ids=material_ids("problem", "motivation"),
                    presenter_checklist=[
                        "Can you explain why this problem matters without reading the slide?",
                        "Do you have one concrete example or failure case ready?",
                    ],
                ),
                Slide(
                    title="Method",
                    purpose="Explain the central technical idea.",
                    key_message=self._compact(card.method),
                    bullets=self._compact_list([card.method]),
                    layout="figure-focus",
                    material_ids=material_ids("method", "figure"),
                    presenter_checklist=[
                        "Choose the one diagram, equation, or toy example that best explains the method.",
                        "Remove implementation details you cannot defend in Q&A.",
                    ],
                ),
                Slide(
                    title="Discussion",
                    purpose="Prepare group discussion.",
                    key_message="Connect the paper to future work.",
                    bullets=self._compact_list(card.open_questions or ["What should we test next?"], limit=5),
                    layout="comparison",
                    material_ids=material_ids("experiments", "limitations", "takeaway"),
                    presenter_checklist=[
                        "Separate paper claims from your own interpretation.",
                        "Mark any novelty or limitation claim that still needs literature checking.",
                    ],
                ),
            ],
        )
        return TaskResult(task_id=task.task_id, agent_name=self.name, data=plan)

    def _ai_research_plan(self, task: Task, card: LiteratureCard, library: object, material_ids) -> SlidePlan:
        slides = [
            Slide(
                title="Why This Paper Matters",
                purpose="Frame the motivation and the concrete gap.",
                key_message=self._compact(card.problem or card.one_sentence_summary),
                bullets=self._compact_list([
                    card.one_sentence_summary,
                    self._first_user_material(library, ("motivation", "problem")),
                ]),
                layout="section",
                material_ids=material_ids("problem", "motivation", "note"),
                presenter_checklist=[
                    "State the failure point in the previous approach, not just the broad topic.",
                    "Use your own example or screenshot if it makes the gap easier to feel.",
                ],
            ),
            Slide(
                title="Method Intuition",
                purpose="Explain the core idea before details.",
                key_message=self._compact(card.method),
                bullets=self._compact_list([
                    card.method,
                    self._first_user_material(library, ("method", "algorithm", "objective")),
                ]),
                layout="figure-focus",
                material_ids=material_ids("method", "figure", "screenshot", "algorithm", "objective"),
                presenter_checklist=[
                    "Explain the pipeline in your words before showing equations or implementation details.",
                    "Pick one figure, screenshot, or toy example as the anchor for this slide.",
                ],
            ),
            Slide(
                title="What To Remember",
                purpose="Close with the useful takeaway for future work.",
                key_message="Keep the method insight, and treat experiments as supporting evidence.",
                bullets=self._compact_list(card.useful_for or card.open_questions or ["What would I reuse or test next?"], limit=4),
                layout="comparison",
                material_ids=material_ids("takeaway", "experiments", "my_interpretation", "question_for_group"),
                presenter_checklist=[
                    "Mention experiments briefly unless there is a special trick or surprising result.",
                    "Use limitations only if you have your own concrete interpretation.",
                ],
            ),
        ]

        limitation = self._first_user_material(library, ("limitation", "failure_case", "my_interpretation"))
        if limitation:
            slides.append(
                Slide(
                    title="My Take",
                    purpose="Add personal interpretation or limitation when it is useful.",
                    key_message=self._compact(limitation),
                    bullets=self._compact_list([limitation], limit=2),
                    layout="section",
                    material_ids=material_ids("limitation", "failure_case", "my_interpretation"),
                    presenter_checklist=[
                        "Make clear which part is your interpretation rather than the paper's claim.",
                    ],
                )
            )

        return SlidePlan(
            title=f"Paper Brief: {card.title}",
            audience=str(task.payload.get("audience", "research group")),
            duration_minutes=int(task.payload.get("duration_minutes", 10)),
            source_papers=[card.title],
            slides=slides,
        )

    def _ai_survey_plan(self, task: Task, card: LiteratureCard, library: object, material_ids) -> SlidePlan:
        trend = self._first_user_material(library, ("timeline", "trend", "progress", "industry"))
        taxonomy = self._first_user_material(library, ("taxonomy", "method_family", "category"))
        representative = self._representative_papers(library)
        slides = [
            Slide(
                title="Field Timeline",
                purpose="Show how the area evolved and why this moment matters.",
                key_message=self._compact(trend or card.problem or card.one_sentence_summary),
                bullets=self._compact_list([
                    trend,
                    "Group papers by time, method family, or capability jump instead of explaining every paper.",
                ]),
                layout="timeline",
                material_ids=material_ids("timeline", "trend", "progress", "industry", "note"),
                presenter_checklist=[
                    "Make the timeline explain a shift in the field, not just a list of dates.",
                    "Keep each paper to one role in the story.",
                ],
            ),
            Slide(
                title="Method Landscape",
                purpose="Organize methods into families and tradeoffs.",
                key_message=self._compact(taxonomy or card.method),
                bullets=self._compact_list([
                    taxonomy,
                    card.method,
                ], limit=4),
                layout="comparison",
                material_ids=material_ids("taxonomy", "method_family", "method", "screenshot"),
                presenter_checklist=[
                    "Compare method families, not individual implementation trivia.",
                    "Name the axis: data, architecture, objective, inference, or system constraint.",
                ],
            ),
            Slide(
                title="Representative Papers",
                purpose="Give each paper a compact role in the survey.",
                key_message="Each paper gets one contribution and one reason it matters.",
                bullets=self._compact_list(representative or ["Add representative papers through user notes or survey materials."], limit=6),
                layout="comparison",
                material_ids=material_ids("paper", "claim", "takeaway", "main_result"),
                presenter_checklist=[
                    "Do not deep-dive every method; pick one or two representative mechanisms if needed.",
                    "Avoid giving more than one slide to a paper unless it anchors the whole survey.",
                ],
            ),
            Slide(
                title="Takeaways And Open Directions",
                purpose="Close with progress, bottlenecks, and what to watch next.",
                key_message="Summarize the direction of travel and the remaining bottlenecks.",
                bullets=self._compact_list(card.open_questions or card.useful_for or ["What changed in the field, and what remains unresolved?"], limit=5),
                layout="section",
                material_ids=material_ids("question_for_group", "limitation", "failure_case", "my_interpretation"),
                presenter_checklist=[
                    "Focus on field-level open problems rather than one paper's limitations.",
                    "Add your own view only where it changes the audience's understanding of the trend.",
                ],
            ),
        ]
        return SlidePlan(
            title=f"Survey Brief: {card.title}",
            audience=str(task.payload.get("audience", "research group")),
            duration_minutes=int(task.payload.get("duration_minutes", 10)),
            source_papers=[card.title],
            slides=slides,
        )

    @staticmethod
    def _compact(text: str, limit: int = 220) -> str:
        compact = " ".join(str(text).split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3].rstrip() + "..."

    def _compact_list(self, items: list[str], limit: int = 3) -> list[str]:
        return [self._compact(item, limit=180) for item in items if item][:limit]

    def _first_user_material(self, library: object, kinds: tuple[str, ...]) -> str:
        if not isinstance(library, SlideMaterialLibrary):
            return ""
        for material in library.materials:
            if material.user_provided and (material.kind in kinds or set(material.tags).intersection(kinds)):
                return self._compact(material.content, limit=220)
        return ""

    def _representative_papers(self, library: object) -> list[str]:
        if not isinstance(library, SlideMaterialLibrary):
            return []
        papers = [
            f"{material.title}: {material.content}"
            for material in library.materials
            if material.user_provided and (material.kind in {"paper", "claim", "main_result"} or {"paper", "survey"}.intersection(material.tags))
        ]
        return papers[:6]

    @staticmethod
    def _material_ids(library: object):
        if not isinstance(library, SlideMaterialLibrary):
            return lambda *kinds: []
        by_kind: dict[str, list[str]] = {}
        for material in library.materials:
            by_kind.setdefault(material.kind, []).append(material.material_id)

        def select(*kinds: str) -> list[str]:
            ids: list[str] = []
            for kind in kinds:
                ids.extend(by_kind.get(kind, []))
            return ids

        return select
