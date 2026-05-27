from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from labcrew.schemas.presentation import SlidePlan

_STYLE = """\
* { margin:0; padding:0; box-sizing:border-box; }
:root {
  --bg: #fafaf8; --text: #1a1a1a; --accent: #2563eb;
  --slide-bg: #fff; --notes-bg: #fdf6e3; --muted: #6b7280;
}
body { font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); overflow: hidden; height: 100dvh; }
#deck { width:100%; height:100%; position:relative; }
.slide { display:none; flex-direction:column; justify-content:center; width:100%; height:100%; padding: 3rem 5vw; position:absolute; inset:0; background:var(--slide-bg); overflow-y:auto; }
.slide.active { display:flex; }
.slide.layout-section { align-items:flex-start; justify-content:center; background:#f8fafc; }
.slide.layout-figure-focus { display:none; grid-template-columns:minmax(0,1fr) minmax(18rem,.8fr); align-items:center; gap:2rem; }
.slide.layout-figure-focus.active { display:grid; }
.slide.layout-comparison ul { columns:2; column-gap:2.5rem; }
.slide h1 { font-size:clamp(1.5rem, 4vw, 2.5rem); margin-bottom:.5em; line-height:1.25; }
.slide h2 { font-size:clamp(1rem, 2vw, 1.25rem); color:var(--muted); font-weight:400; margin-bottom:1.5rem; }
.slide .purpose { font-size:.9rem; color:var(--accent); text-transform:uppercase; letter-spacing:.05em; margin-bottom:.75rem; font-weight:600; }
.slide .key-message { font-size:clamp(1.1rem, 2.5vw, 1.5rem); margin-bottom:1.5rem; line-height:1.5; padding:.75rem 1rem; border-left:3px solid var(--accent); background:#eff6ff; border-radius:0 4px 4px 0; }
.slide ul { list-style:none; font-size:clamp(.95rem, 2vw, 1.15rem); line-height:1.7; }
.slide ul li::before { content:"\\2022"; color:var(--accent); margin-right:.5em; }
.slide .visual { margin-top:1.5rem; font-size:.85rem; color:var(--muted); font-style:italic; }
.slide .checklist { margin-top:1.25rem; color:var(--muted); font-size:.8rem; }
.slide .checklist strong { color:var(--text); }
.speaker-notes { display:none; margin-top:1.5rem; padding:1rem; background:var(--notes-bg); border-radius:6px; font-size:.85rem; color:#555; line-height:1.5; }
.speaker-notes::before { content:"Notes"; display:block; font-weight:600; font-size:.75rem; text-transform:uppercase; letter-spacing:.08em; margin-bottom:.5rem; color:var(--muted); }
.show-notes .speaker-notes { display:block; }
#controls { position:fixed; bottom:1.25rem; left:50%; transform:translateX(-50%); display:flex; align-items:center; gap:.75rem; background:var(--slide-bg); padding:.5rem 1rem; border-radius:999px; box-shadow:0 2px 12px rgba(0,0,0,.08); z-index:100; }
#controls button { border:none; background:none; font-size:1.25rem; cursor:pointer; padding:.25rem .5rem; border-radius:4px; color:var(--text); transition:background .15s; }
#controls button:hover { background:#e5e7eb; }
#counter { font-size:.85rem; font-variant-numeric:tabular-nums; color:var(--muted); min-width:4ch; text-align:center; }
#hint { position:fixed; bottom:4.5rem; left:50%; transform:translateX(-50%); font-size:.75rem; color:var(--muted); opacity:0; transition:opacity .3s; }
#hint.visible { opacity:1; }

@media print {
  body { overflow:visible; height:auto; background:#fff; }
  .slide { display:flex !important; position:relative; height:100vh; page-break-after:always; }
  .slide:last-child { page-break-after:avoid; }
  .speaker-notes { display:block !important; }
  #controls { display:none; }
  #hint { display:none; }
}
@media (max-width:600px) {
  .slide { padding:2rem 1.25rem; }
  .slide.layout-figure-focus.active { display:flex; }
  .slide.layout-comparison ul { columns:1; }
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


class HtmlSlideAdapter:
    """Render a SlidePlan as a self-contained HTML presentation."""

    def __init__(self, output_dir: str | Path = "data/artifacts/slides") -> None:
        self.output_dir = Path(output_dir)

    def create_deck(self, slide_plan: SlidePlan, slug: str | None = None) -> dict[str, Any]:
        slug = slug or self._slug(slide_plan.title)
        out_dir = self.output_dir / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        html_path = out_dir / "index.html"

        slides_html = "\n".join(self._render_slide(s) for s in slide_plan.slides)
        html = _TEMPLATE.format(
            title=self._esc(slide_plan.title),
            style=_STYLE,
            slides=slides_html,
            script=_SCRIPT,
        )
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
    # internal
    # ------------------------------------------------------------------

    def _render_slide(self, slide) -> str:
        layout = self._layout_class(getattr(slide, "layout", "title-and-bullets"))
        parts = [f'<section class="slide {layout}">']
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
        if slide.visual_suggestion:
            parts.append(f'<div class="visual">Visual: {self._esc(slide.visual_suggestion)}</div>')
        checklist = getattr(slide, "presenter_checklist", [])
        if checklist:
            parts.append('<div class="checklist"><strong>Presenter check:</strong><ul>')
            for item in checklist:
                parts.append(f"<li>{self._esc(item)}</li>")
            parts.append("</ul></div>")
        if slide.speaker_notes:
            parts.append(f'<div class="speaker-notes">{self._esc(slide.speaker_notes)}</div>')
        parts.append("</section>")
        return "\n".join(parts)

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
