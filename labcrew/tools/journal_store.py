from __future__ import annotations

from datetime import date, timedelta
from hashlib import sha1
from pathlib import Path
import re

from labcrew.schemas import Paper, PaperCardReport, PaperJournalRecord


class JournalStore:
    """Persist paper card reports into period-based Markdown journals."""

    def __init__(self, root_dir: Path | None = None, today: date | None = None) -> None:
        self.root_dir = root_dir or Path("data/journals")
        self.today = today

    def list_entry_titles(self) -> set[str]:
        """Return the set of paper titles found across all journal entries."""
        titles: set[str] = set()
        if not self.root_dir.exists():
            return titles
        for journal_path in self.root_dir.rglob("*.md"):
            content = journal_path.read_text(encoding="utf-8")
            for match in re.finditer(r"<!-- labcrew-card:.*? -->\n## (.+)", content):
                titles.add(match.group(1).strip())
        return titles

    def save_paper_card(
        self,
        paper: Paper,
        card_report: PaperCardReport,
        project: str = "general",
        period: str = "weekly",
    ) -> PaperJournalRecord:
        current_date = self.today or date.today()
        normalized_period = self._normalize_period(period)
        period_start, period_end, label = self._period_window(current_date, normalized_period)
        journal_dir = self.root_dir / self._slug(project)
        journal_dir.mkdir(parents=True, exist_ok=True)

        path = journal_dir / f"paper-journal-{label}.md"
        entry_id = self._entry_id(paper)
        entry = self._render_entry(entry_id, paper, card_report)
        self._upsert_entry(path, project, normalized_period, period_start, period_end, entry_id, entry)
        return PaperJournalRecord(
            entry_id=entry_id,
            path=str(path),
            period=normalized_period,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
        )

    def _normalize_period(self, period: str) -> str:
        normalized = period.strip().lower().replace("_", "-")
        aliases = {
            "day": "daily",
            "daily": "daily",
            "week": "weekly",
            "weekly": "weekly",
            "month": "monthly",
            "monthly": "monthly",
            "quarter": "quarterly",
            "quarterly": "quarterly",
            "year": "yearly",
            "yearly": "yearly",
        }
        if normalized in aliases:
            return aliases[normalized]
        match = re.fullmatch(r"(\d+)\s*(d|day|days)", normalized)
        if match:
            days = int(match.group(1))
            if days <= 0:
                raise ValueError("Journal period days must be greater than zero.")
            return f"{days}d"
        raise ValueError("Journal period must be daily, weekly, monthly, quarterly, yearly, or a value like 14d.")

    def _period_window(self, current_date: date, period: str) -> tuple[date, date, str]:
        if period == "daily":
            return current_date, current_date, current_date.isoformat()
        if period == "weekly":
            start = current_date - timedelta(days=current_date.weekday())
            end = start + timedelta(days=6)
            iso_year, iso_week, _ = current_date.isocalendar()
            return start, end, f"{iso_year}-W{iso_week:02d}"
        if period == "monthly":
            start = current_date.replace(day=1)
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            return start, next_month - timedelta(days=1), f"{current_date:%Y-%m}"
        if period == "quarterly":
            quarter = (current_date.month - 1) // 3 + 1
            start = date(current_date.year, 3 * (quarter - 1) + 1, 1)
            next_start = date(current_date.year + 1, 1, 1) if quarter == 4 else date(current_date.year, 3 * quarter + 1, 1)
            return start, next_start - timedelta(days=1), f"{current_date.year}-Q{quarter}"
        if period == "yearly":
            start = date(current_date.year, 1, 1)
            return start, date(current_date.year, 12, 31), f"{current_date.year}"

        days = int(period.removesuffix("d"))
        bucket_start_ordinal = ((current_date.toordinal() - 1) // days) * days + 1
        start = date.fromordinal(bucket_start_ordinal)
        end = start + timedelta(days=days - 1)
        return start, end, f"{period}-{start.isoformat()}"

    def _render_entry(self, entry_id: str, paper: Paper, card_report: PaperCardReport) -> str:
        lines = [
            f"<!-- labcrew-card:{entry_id} -->",
            f"## {card_report.title}",
            "",
            f"- One sentence: {card_report.one_sentence_summary}",
            f"- Problem: {card_report.problem}",
            f"- Method: {card_report.method_snapshot}",
            f"- Experiments: {card_report.experiment_snapshot}",
            f"- Limitations: {card_report.limitations}",
        ]
        if card_report.useful_for:
            lines.append(f"- Useful for: {', '.join(card_report.useful_for)}")
        if card_report.follow_up_questions:
            lines.append("- Follow-up questions:")
            lines.extend(f"  - {question}" for question in card_report.follow_up_questions)
        if paper.figures:
            lines.append("- Figures:")
            lines.extend(f"  - p{figure.page_number}: {figure.image_path}" for figure in paper.figures[:3])
        source = paper.pdf_path or paper.source_url
        if source:
            lines.append(f"- Source: {source}")
        lines.extend(["", f"<!-- /labcrew-card:{entry_id} -->", ""])
        return "\n".join(lines)

    def _upsert_entry(
        self,
        path: Path,
        project: str,
        period: str,
        period_start: date,
        period_end: date,
        entry_id: str,
        entry: str,
    ) -> None:
        header = self._render_header(project, period, period_start, period_end)
        if not path.exists():
            path.write_text(header + entry, encoding="utf-8")
            return

        content = path.read_text(encoding="utf-8")
        pattern = re.compile(
            rf"<!-- labcrew-card:{re.escape(entry_id)} -->.*?<!-- /labcrew-card:{re.escape(entry_id)} -->\n?",
            re.DOTALL,
        )
        if pattern.search(content):
            updated = pattern.sub(entry, content)
        else:
            updated = content.rstrip() + "\n\n" + entry
        path.write_text(updated, encoding="utf-8")

    def _render_header(self, project: str, period: str, period_start: date, period_end: date) -> str:
        return (
            f"# Paper Journal: {project}\n\n"
            f"- Period: {period}\n"
            f"- Window: {period_start.isoformat()} to {period_end.isoformat()}\n\n"
        )

    def _entry_id(self, paper: Paper) -> str:
        identity = paper.pdf_path or paper.source_url or paper.title
        digest = sha1(identity.encode("utf-8")).hexdigest()[:12]
        return f"{self._slug(paper.title)[:48]}-{digest}"

    def _slug(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return slug or "general"
