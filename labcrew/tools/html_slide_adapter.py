from __future__ import annotations

import base64
import mimetypes
import re
from pathlib import Path
from typing import Any

from labcrew.schemas.presentation import SlideMaterial, SlidePlan

# ---------------------------------------------------------------------------
# themes
# ---------------------------------------------------------------------------

_THEMES: dict[str, str] = {
    "light": """\
:root {
  --bg: #fafaf8; --text: #1a1a1a; --accent: #2563eb;
  --slide-bg: #fff; --notes-bg: #fdf6e3; --muted: #6b7280;
  --section-bg: #f8fafc; --key-bg: #eff6ff; --border: #e5e7eb;
}""",
    "dark": """\
:root {
  --bg: #0f172a; --text: #e2e8f0; --accent: #60a5fa;
  --slide-bg: #1e293b; --notes-bg: #334155; --muted: #94a3b8;
  --section-bg: #1a2332; --key-bg: #1e3a5f; --border: #334155;
}""",
    "blue": """\
:root {
  --bg: #eff6ff; --text: #1e3a5f; --accent: #1d4ed8;
  --slide-bg: #fff; --notes-bg: #dbeafe; --muted: #64748b;
  --section-bg: #dbeafe; --key-bg: #bfdbfe; --border: #bfdbfe;
}""",
}

# ---------------------------------------------------------------------------
# shared CSS / JS
# ---------------------------------------------------------------------------

_BASE_STYLE = """\
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); overflow: hidden; height: 100dvh; }
#deck { width:100%; height:100%; position:relative; }
.slide { display:none; width:100%; height:100%; padding: 3rem 5vw; position:absolute; inset:0; background:var(--slide-bg); overflow-y:auto; }
.slide.active { display:flex; flex-direction:column; justify-content:center; }

/* ---- layout: title-slide ---- */
.slide.layout-title-slide { align-items:center; text-align:center; justify-content:center; }
.slide.layout-title-slide h1 { font-size:clamp(2rem, 5vw, 3.5rem); margin-bottom:.3em; }
.slide.layout-title-slide .subtitle { font-size:clamp(1rem, 2.5vw, 1.5rem); color:var(--muted); margin-bottom:1rem; }
.slide.layout-title-slide .key-message { font-size:clamp(1rem, 2vw, 1.25rem); border-left:none; background:transparent; padding:0; }

/* ---- layout: section ---- */
.slide.layout-section { align-items:center; justify-content:center; text-align:center; background:var(--section-bg); }
.slide.layout-section h1 { font-size:clamp(2rem, 5vw, 3rem); margin-bottom:.3em; }
.slide.layout-section .subtitle { font-size:clamp(.95rem, 2vw, 1.2rem); color:var(--muted); }

/* ---- layout: figure-focus ---- */
.slide.layout-figure-focus.active { display:grid; grid-template-columns:minmax(0,1fr) minmax(16rem,.75fr); align-items:center; gap:2rem; }
.slide.layout-figure-focus .figure { width:100%; max-height:70vh; object-fit:contain; border-radius:6px; box-shadow:0 2px 12px rgba(0,0,0,.08); }
.slide.layout-figure-focus .caption { margin-top:.5rem; font-size:.8rem; color:var(--muted); text-align:center; }

/* ---- layout: comparison ---- */
.slide.layout-comparison.active { display:grid; grid-template-columns:1fr 1fr; gap:2rem; align-items:start; }
.slide.layout-comparison .column { min-width:0; }
.slide.layout-comparison .column h2 { font-size:1.1rem; color:var(--accent); margin-bottom:.75rem; }

/* ---- layout: two-column ---- */
.slide.layout-two-column.active { display:grid; grid-template-columns:1fr 1fr; gap:2rem; align-items:start; }
.slide.layout-two-column .column { min-width:0; }
.slide.layout-two-column .column h2 { font-size:1.1rem; color:var(--accent); margin-bottom:.75rem; }

/* ---- shared ---- */
.slide h1 { font-size:clamp(1.5rem, 4vw, 2.5rem); margin-bottom:.5em; line-height:1.25; }
.slide h2 { font-size:clamp(1rem, 2vw, 1.25rem); color:var(--muted); font-weight:400; margin-bottom:1.5rem; }
.slide .purpose { font-size:.9rem; color:var(--accent); text-transform:uppercase; letter-spacing:.05em; margin-bottom:.75rem; font-weight:600; }
.slide .key-message { font-size:clamp(1.1rem, 2.5vw, 1.5rem); margin-bottom:1.5rem; line-height:1.5; padding:.75rem 1rem; border-left:3px solid var(--accent); background:var(--key-bg); border-radius:0 4px 4px 0; }
.slide ul { list-style:none; font-size:clamp(.95rem, 2vw, 1.15rem); line-height:1.7; }
.slide ul li::before { content:"\\2022"; color:var(--accent); margin-right:.5em; }
.slide .visual { margin-top:1.5rem; font-size:.85rem; color:var(--muted); font-style:italic; }
.slide .checklist { margin-top:1.25rem; color:var(--muted); font-size:.8rem; }
.slide .checklist strong { color:var(--text); }
.speaker-notes { display:none; margin-top:1.5rem; padding:1rem; background:var(--notes-bg); border-radius:6px; font-size:.85rem; color:var(--text); line-height:1.5; }
.speaker-notes::before { content:"Notes"; display:block; font-weight:600; font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; margin-bottom:.5rem; color:var(--muted); }
.show-notes .speaker-notes { display:block; }
#controls { position:fixed; bottom:1.25rem; left:50%; transform:translateX(-50%); display:flex; align-items:center; gap:.75rem; background:var(--slide-bg); padding:.5rem 1rem; border-radius:999px; box-shadow:0 2px 12px rgba(0,0,0,.08); z-index:100; border:1px solid var(--border); }
#controls button { border:none; background:none; font-size:1.25rem; cursor:pointer; padding:.25rem .5rem; border-radius:4px; color:var(--text); transition:background .15s; }
#controls button:hover { background:var(--border); }
#counter { font-size:.85rem; font-variant-numeric:tabular-nums; color:var(--muted); min-width:4ch; text-align:center; }
#hint { position:fixed; bottom:4.5rem; left:50%; transform:translateX(-50%); font-size:.75rem; color:var(--muted); opacity:0; transition:opacity .3s; }
#hint.visible { opacity:1; }

@media print {
  body { overflow:visible; height:auto; background:#fff; }
  .slide { display:flex !important; flex-direction:column; justify-content:center; position:relative; height:100vh; page-break-after:always; }
  .slide.layout-figure-focus { display:grid !important; }
  .slide.layout-comparison { display:grid !important; }
  .slide.layout-two-column { display:grid !important; }
  .slide:last-child { page-break-after:avoid; }
  .speaker-notes { display:block !important; }
  #controls { display:none; }
  #hint { display:none; }
}
@media (max-width:600px) {
  .slide { padding:2rem 1.25rem; }
  .slide.layout-figure-focus.active,
  .slide.layout-comparison.active,
  .slide.layout-two-column.active { display:flex; flex-direction:column; }
  #controls { bottom:.75rem; gap:.5rem; padding:.4rem .75rem; }
}
"""

_SCRIPT = """\
(function(){
  var slides=document.querySelectorAll('.slide');
  if(!slides.length){
    document.getElementById('counter').textContent='0 / 0';
    return;
  }
  var i=0;
  function show(n){
    slides[i].classList.remove('active');
    i=(n+slides.length)%slides.length;
    slides[i].classList.add('active');
    document.getElementById('counter').textContent=(i+1)+' / '+slides.length;
  }
  document.getElementById('prev').addEventListener('click',function(){show(i-1)});
  document.getElementById('next').addEventListener('click',function(){show(i+1)});
  document.addEventListener('keydown',function(e){
    if(e.key==='ArrowLeft'){show(i-1);e.preventDefault();}
    else if(e.key==='ArrowRight'){show(i+1);e.preventDefault();}
    else if(e.key==='n'||e.key==='N'){document.body.classList.toggle('show-notes');}
  });
  var startX=0;
  document.addEventListener('touchstart',function(e){startX=e.touches[0].clientX});
  document.addEventListener('touchend',function(e){
    var dx=e.changedTouches[0].clientX-startX;
    if(Math.abs(dx)>50){show(dx<0?i+1:i-1);}
  });
  show(0);
  var hint=document.getElementById('hint');
  hint.classList.add('visible');
  setTimeout(function(){hint.classList.remove('visible')},4000);
})();
"""

_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
{theme}
{style}
</style>
</head>
<body>
<div id="deck">
{slides}
</div>
<nav id="controls">
  <button id="prev" aria-label="Previous slide">&#8592;</button>
  <span id="counter"></span>
  <button id="next" aria-label="Next slide">&#8594;</button>
</nav>
<div id="hint">&#8592; &#8594; arrows to navigate &middot; N to toggle notes</div>
<script>
{script}
</script>
</body>
</html>
"""

_IMG_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp"}


class HtmlSlideAdapter:
    """Render a SlidePlan as a self-contained HTML presentation."""

    def __init__(self, output_dir: str | Path = "data/artifacts/slides") -> None:
        self.output_dir = Path(output_dir)

    def create_deck(
        self,
        slide_plan: SlidePlan,
        slug: str | None = None,
        materials: list[SlideMaterial] | None = None,
        theme: str = "light",
    ) -> dict[str, Any]:
        slug = slug or self._slug(slide_plan.title)
        out_dir = self.output_dir / slug
        out_dir.mkdir(parents=True, exist_ok=True)

        mat_map = self._build_material_map(materials or [])
        slides_html = "\n".join(self._render_slide(s, mat_map) for s in slide_plan.slides)
        theme_css = _THEMES.get(theme, _THEMES["light"])
        html = _TEMPLATE.format(
            title=self._esc(slide_plan.title),
            theme=theme_css,
            style=_BASE_STYLE,
            slides=slides_html,
            script=_SCRIPT,
        )
        html_path = out_dir / "index.html"
        html_path.write_text(html, encoding="utf-8")

        return {
            "provider": "html_slide_adapter",
            "status": "created",
            "html_path": str(html_path),
            "file_url": html_path.resolve().as_uri(),
            "slide_count": len(slide_plan.slides),
            "source_title": slide_plan.title,
        }

    # ------------------------------------------------------------------
    # internal — material lookup & image bundling
    # ------------------------------------------------------------------

    @staticmethod
    def _build_material_map(materials: list[SlideMaterial]) -> dict[str, SlideMaterial]:
        return {m.material_id: m for m in materials}

    def _resolve_image_data_uri(self, material: SlideMaterial) -> str | None:
        """Return a base64 data URI for a figure/screenshot material, or None."""
        path = Path(material.content)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            return None
        suffix = path.suffix.lower()
        if suffix not in _IMG_EXTENSIONS:
            return None
        mime, _ = mimetypes.guess_type(str(path))
        if not mime:
            mime = "image/" + (suffix.lstrip(".").replace("jpg", "jpeg"))
        try:
            data = path.read_bytes()
            encoded = base64.b64encode(data).decode()
            return f"data:{mime};base64,{encoded}"
        except OSError:
            return None

    def _render_image_for_material(self, material: SlideMaterial) -> str:
        data_uri = self._resolve_image_data_uri(material)
        alt = self._esc(material.title)
        if data_uri:
            return f'<img class="figure" src="{data_uri}" alt="{alt}">'
        return f'<div class="visual">Figure: {alt}</div>'

    # ------------------------------------------------------------------
    # internal — slide rendering
    # ------------------------------------------------------------------

    def _render_slide(self, slide, mat_map: dict[str, SlideMaterial] | None = None) -> str:
        mat_map = mat_map or {}
        layout = self._layout_class(getattr(slide, "layout", "title-and-bullets"))
        parts = [f'<section class="slide {layout}">']

        if layout == "layout-title-slide":
            parts.extend(self._render_title_slide(slide))
        elif layout == "layout-section":
            parts.extend(self._render_section_slide(slide))
        elif layout == "layout-figure-focus":
            parts.extend(self._render_figure_focus_slide(slide, mat_map))
        elif layout in ("layout-comparison", "layout-two-column"):
            parts.extend(self._render_column_slide(slide, layout == "layout-comparison"))
        else:
            parts.extend(self._render_default_slide(slide, mat_map))

        parts.append("</section>")
        return "\n".join(parts)

    def _render_default_slide(self, slide, mat_map: dict[str, SlideMaterial]) -> list[str]:
        parts: list[str] = []
        parts.append(f'<h1>{self._esc(slide.title)}</h1>')
        if slide.purpose:
            parts.append(f'<div class="purpose">{self._esc(slide.purpose)}</div>')
        if slide.key_message:
            parts.append(f'<div class="key-message">{self._esc(slide.key_message)}</div>')
        if slide.bullets:
            parts.append("<ul>")
            for b in slide.bullets:
                parts.append(f"<li>{self._esc(b)}</li>")
            parts.append("</ul>")
        parts.extend(self._render_linked_images(slide, mat_map))
        if slide.visual_suggestion:
            parts.append(f'<div class="visual">Visual: {self._esc(slide.visual_suggestion)}</div>')
        parts.extend(self._render_checklist(slide))
        parts.extend(self._render_speaker_notes(slide))
        return parts

    def _render_title_slide(self, slide) -> list[str]:
        parts: list[str] = []
        parts.append(f'<h1>{self._esc(slide.title)}</h1>')
        if slide.purpose:
            parts.append(f'<div class="subtitle">{self._esc(slide.purpose)}</div>')
        if slide.key_message:
            parts.append(f'<div class="key-message">{self._esc(slide.key_message)}</div>')
        parts.extend(self._render_speaker_notes(slide))
        return parts

    def _render_section_slide(self, slide) -> list[str]:
        parts: list[str] = []
        parts.append(f'<h1>{self._esc(slide.title)}</h1>')
        if slide.key_message:
            parts.append(f'<div class="subtitle">{self._esc(slide.key_message)}</div>')
        parts.extend(self._render_speaker_notes(slide))
        return parts

    def _render_figure_focus_slide(self, slide, mat_map: dict[str, SlideMaterial]) -> list[str]:
        parts: list[str] = []
        parts.append('<div class="column">')
        parts.append(f'<h1>{self._esc(slide.title)}</h1>')
        if slide.purpose:
            parts.append(f'<div class="purpose">{self._esc(slide.purpose)}</div>')
        if slide.key_message:
            parts.append(f'<div class="key-message">{self._esc(slide.key_message)}</div>')
        if slide.bullets:
            parts.append("<ul>")
            for b in slide.bullets:
                parts.append(f"<li>{self._esc(b)}</li>")
            parts.append("</ul>")
        parts.extend(self._render_checklist(slide))
        parts.extend(self._render_speaker_notes(slide))
        parts.append("</div>")
        parts.append('<div class="column">')
        images = self._render_linked_images(slide, mat_map)
        if images:
            parts.extend(images)
        elif slide.visual_suggestion:
            parts.append(f'<div class="visual">Visual: {self._esc(slide.visual_suggestion)}</div>')
        parts.append("</div>")
        return parts

    def _render_column_slide(self, slide, comparison: bool) -> list[str]:
        """Render a two-column or comparison slide.

        Splits *bullets* into two groups. For comparison mode the bullets are
        split on a ``---`` sentinel; for two-column they are split evenly.
        """
        parts: list[str] = []
        parts.append(f'<h1>{self._esc(slide.title)}</h1>')
        if slide.purpose:
            parts.append(f'<div class="purpose">{self._esc(slide.purpose)}</div>')
        if slide.key_message:
            parts.append(f'<div class="key-message">{self._esc(slide.key_message)}</div>')

        left, right = self._split_bullets(slide.bullets, comparison)
        parts.append('<div style="display:grid;grid-template-columns:1fr 1fr;gap:2rem;">')
        parts.append('<div class="column">')
        if left:
            parts.append("<ul>")
            for b in left:
                parts.append(f"<li>{self._esc(b)}</li>")
            parts.append("</ul>")
        parts.append("</div>")
        parts.append('<div class="column">')
        if right:
            parts.append("<ul>")
            for b in right:
                parts.append(f"<li>{self._esc(b)}</li>")
            parts.append("</ul>")
        parts.append("</div>")
        parts.append("</div>")

        if slide.visual_suggestion:
            parts.append(f'<div class="visual">Visual: {self._esc(slide.visual_suggestion)}</div>')
        parts.extend(self._render_checklist(slide))
        parts.extend(self._render_speaker_notes(slide))
        return parts

    # ------------------------------------------------------------------
    # internal — helpers
    # ------------------------------------------------------------------

    def _render_linked_images(self, slide, mat_map: dict[str, SlideMaterial]) -> list[str]:
        parts: list[str] = []
        for mid in getattr(slide, "material_ids", []) or []:
            mat = mat_map.get(mid)
            if mat and mat.kind in ("figure", "screenshot"):
                parts.append(self._render_image_for_material(mat))
        return parts

    def _render_checklist(self, slide) -> list[str]:
        checklist = getattr(slide, "presenter_checklist", []) or []
        if not checklist:
            return []
        parts = ['<div class="checklist"><strong>Presenter check:</strong><ul>']
        for item in checklist:
            parts.append(f"<li>{self._esc(item)}</li>")
        parts.append("</ul></div>")
        return parts

    def _render_speaker_notes(self, slide) -> list[str]:
        if not slide.speaker_notes:
            return []
        return [f'<div class="speaker-notes">{self._esc(slide.speaker_notes)}</div>']

    @staticmethod
    def _split_bullets(bullets: list[str], comparison: bool) -> tuple[list[str], list[str]]:
        if not bullets:
            return [], []
        if comparison:
            try:
                idx = bullets.index("---")
            except ValueError:
                idx = (len(bullets) + 1) // 2
            return bullets[:idx], bullets[idx + 1:] if "---" in bullets else bullets[idx:]
        mid = (len(bullets) + 1) // 2
        return bullets[:mid], bullets[mid:]

    @staticmethod
    def _slug(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return slug or "slides"

    @staticmethod
    def _layout_class(value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
        return f"layout-{slug or 'title-and-bullets'}"

    @staticmethod
    def _esc(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
