"""PDF rendering of evaluation reports with ReportLab (pure Python, works on Windows)."""
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

NAVY = colors.HexColor("#1e2a5a")
VIOLET = colors.HexColor("#6d4fd1")
MUTED = colors.HexColor("#5b6478")
LINE = colors.HexColor("#d9dce6")
LABELS = {"semantic": "Semantic similarity", "required_skills": "Required skills", "preferred_skills": "Preferred skills",
          "experience": "Experience", "education": "Education", "certifications": "Certifications"}


def _p(text, style):
    return Paragraph(escape(str(text)) if text is not None else "—", style)


def build_report_pdf(report: dict, path: Path) -> None:
    ss = getSampleStyleSheet()
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=13)
    small = ParagraphStyle("s", parent=body, fontSize=8, textColor=MUTED, leading=10.5)
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=18, textColor=NAVY, alignment=0, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12, textColor=NAVY, spaceBefore=10, spaceAfter=4)
    tag_ai = ParagraphStyle("ai", parent=small, textColor=VIOLET)
    d = report["report_data"]
    c, job, m, iv = d["candidate"], d["job"], d.get("match"), d.get("interview")
    story = []

    story.append(_p("AgentHire — Candidate Evaluation Report", h1))
    gen = report["generated_at"]
    gen = gen.strftime("%d %b %Y, %H:%M UTC") if isinstance(gen, datetime) else str(gen)
    story.append(_p(f"Generated {gen} · Methodology {report['methodology_version']}", small))
    if c.get("is_synthetic"):
        story.append(_p("SYNTHETIC DEMO DATA — fictional candidate", ParagraphStyle("syn", parent=small,
                                                                                     textColor=colors.red)))
    story.append(Spacer(1, 6))

    rows = [["Candidate", c.get("name") or "—"], ["Job", job["title"]], ["Pipeline stage", d.get("stage", "—")],
            ["Experience", f"{c['total_experience_years']:g} years" if c.get("total_experience_years") is not None
             else "Not stated"],
            ["Match score", f"{m['overall_score']:.1f} / 100" if m else "Not calculated"],
            ["Interview score", f"{iv['total_score']:.1f} / 100" if iv and iv.get("total_score") is not None
             else ("Pending evaluation" if iv else "No interview")]]
    t = Table([[_p(a, body), _p(b, body)] for a, b in rows], colWidths=[40 * mm, 130 * mm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TEXTCOLOR", (0, 0), (0, -1), MUTED)]))
    story.append(t)

    story.append(_p("Resume analysis", h2))
    skills = ", ".join(f"{s['name']}{'*' if s['status'] == 'manually_verified' else ''}" for s in c.get("skills", []))
    story.append(_p(f"Skills: {skills or 'none found'}", body))
    story.append(_p("* = confirmed by a person; others were extracted automatically.", small))
    for e in c.get("education", [])[:3]:
        story.append(_p(f"Education: {e.get('degree') or e.get('level')} — {e.get('institution') or ''} "
                        f"{e.get('end_year') or ''}", body))
    for w in c.get("work_experience", [])[:4]:
        story.append(_p(f"Experience: {w.get('title') or ''} at {w.get('company') or ''} "
                        f"({w.get('start') or '?'} to {w.get('end') or '?'})", body))

    if m:
        ex = m["explanation"]
        story.append(_p("Job compatibility (Resume Matching)", h2))
        story.append(_p(ex.get("disclaimer", ""), small))
        br = [[_p("Component", body), _p("Value", body), _p("Weight", body), _p("Points", body)]]
        for b in ex["breakdown"]:
            br.append([_p(LABELS.get(b["component"], b["component"]), body), _p(f"{b['raw_value']:.2f}", body),
                       _p(f"{b['weight']:g}", body), _p(f"{b['contribution']:.1f}", body)])
        br.append([_p("Total", body), "", "", _p(f"{m['overall_score']:.1f}", body)])
        bt = Table(br, colWidths=[70 * mm, 30 * mm, 30 * mm, 30 * mm])
        bt.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef0f7")),
                                ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE)]))
        story.append(bt)
        story.append(_p(f"Keyword-only baseline for comparison: {m['keyword_baseline_score']:.1f}/100", small))
        story.append(_p("Matching strengths", h2))
        for s in ex.get("strengths", [])[:12] or ["—"]:
            story.append(_p(f"• {s}", body))
        story.append(_p("Skill gaps", h2))
        for g in ex.get("gaps", [])[:12] or ["No gaps found against the listed requirements."]:
            story.append(_p(f"• {g}", body))
        ev = ex.get("required_skills", {}).get("matched", [])[:6]
        if ev:
            story.append(_p("Evidence from the resume", h2))
            for x in ev:
                story.append(_p(f"{x['skill']} ({x.get('evidence_section') or 'profile'}): “{x.get('evidence_text') or ''}”",
                                small))

    if iv:
        story.append(_p("Interview assessment (Rule-Based)", h2))
        s = iv.get("summary", {})
        story.append(_p(f"Answered {s.get('answered', 0)} · evaluated {s.get('evaluated', 0)} · pending "
                        f"{s.get('pending', 0)} · rubric {iv.get('rubric_version')}", small))
        for i, q in enumerate(iv.get("questions", []), start=1):
            a = q.get("answer") or {}
            fb = a.get("feedback") or {}
            block = [_p(f"Q{i}. [{q.get('category_label')} · {q.get('difficulty')}] {q['question']}", body)]
            if a.get("evaluation_status") == "evaluated":
                block.append(_p(f"Score {a.get('weighted_score'):.1f}/100 · verdict: {a.get('verdict')}", tag_ai))
                if fb.get("explanation"):
                    block.append(_p(fb["explanation"], small))
                if fb.get("missing_concepts"):
                    block.append(_p("Missing: " + ", ".join(fb["missing_concepts"]), small))
            else:
                block.append(_p(f"Evaluation: {a.get('evaluation_status', 'not answered')} (no AI score)", small))
            block.append(Spacer(1, 4))
            story.append(KeepTogether(block))

    recs = d.get("learning_recommendations") or []
    if recs:
        story.append(_p("Learning recommendations", h2))
        for r in recs[:8]:
            story.append(_p(f"• {r['skill']}: {r['title']} — {r['url']} ({r['difficulty']})", small))

    story.append(_p("Recruiter comments (written by people, not AI)", h2))
    if report["notes"]:
        for n in report["notes"]:
            when = n["created_at"].strftime("%d %b %Y") if isinstance(n["created_at"], datetime) else n["created_at"]
            story.append(_p(f"{n['author'] or 'Recruiter'} · {when}: {n['text']}", body))
    else:
        story.append(_p("No comments yet.", small))

    story.append(_p("Methodology and limitations", h2))
    story.append(_p("Match score = weighted sum of six components (semantic similarity of embeddings, required and "
                    "preferred skill coverage with synonym/related matching, experience, education, certifications). "
                    "Interview answers are scored 0–10 on five rubric dimensions and combined with the rubric weights.",
                    small))
    for lim in d.get("limitations", []):
        story.append(_p(f"• {lim}", small))

    doc = SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title="AgentHire evaluation report", author="AgentHire")
    doc.build(story)
