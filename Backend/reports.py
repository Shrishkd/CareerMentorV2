"""PDF reports: interview assessment, activity (camera) report and ATS analysis."""
import os
import tempfile
from datetime import datetime
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import (  # noqa: E402
    Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

INK = colors.HexColor("#1c1b19")
MUTED = colors.HexColor("#6b675f")
RULE = colors.HexColor("#dcd7cc")
PAPER = colors.HexColor("#f5f2ea")
ACCENT = colors.HexColor("#1f5c4a")
WARN = colors.HexColor("#b4622a")
BAD = colors.HexColor("#a23a2e")

_base = getSampleStyleSheet()
STYLES = {
    "title": ParagraphStyle("title", parent=_base["Title"], fontName="Times-Bold", fontSize=24, leading=28,
                            textColor=INK, alignment=TA_LEFT, spaceAfter=4),
    "kicker": ParagraphStyle("kicker", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=ACCENT,
                             spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="Times-Bold", fontSize=15, leading=19, textColor=INK, spaceBefore=14,
                         spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=INK, spaceBefore=8,
                         spaceAfter=3),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, leading=13.5, textColor=INK),
    "muted": ParagraphStyle("muted", fontName="Helvetica", fontSize=8.5, leading=12, textColor=MUTED),
    "quote": ParagraphStyle("quote", fontName="Helvetica-Oblique", fontSize=9, leading=13, textColor=MUTED,
                            leftIndent=8, borderPadding=(4, 4, 4, 8)),
    "mono": ParagraphStyle("mono", fontName="Courier", fontSize=8, leading=10.5, textColor=INK),
}

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def _p(text, style="body"):
    return Paragraph(escape(str(text or "")).replace("\n", "<br/>"), STYLES[style])


def _bullets(items, style="body"):
    return [Paragraph(f"&#8226;&nbsp;&nbsp;{escape(str(i))}", STYLES[style]) for i in items if str(i).strip()]


def _hex(color):
    return "#" + color.hexval()[2:]


def _pct(value):
    return "n/a" if value is None else f"{value}%"


def _score_color(score):
    if score is None:
        return MUTED
    if score >= 70:
        return ACCENT
    if score >= 45:
        return WARN
    return BAD


def _footer(title):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.line(18 * mm, 14 * mm, A4[0] - 18 * mm, 14 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 10 * mm, f"Career Mentor  |  {title}")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()
    return draw


def _doc(path):
    return SimpleDocTemplate(path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                             topMargin=18 * mm, bottomMargin=20 * mm)


def _stat_table(stats, col_width=None):
    """A row of big-number stat cells: [(label, value, color), ...]"""
    col_width = col_width or (A4[0] - 36 * mm) / len(stats)
    def value_cell(v, c):
        # Numbers read best large; words like "Not Yet Ready" need to wrap.
        size = 22 if len(str(v)) <= 7 else 14
        style = ParagraphStyle("stat", parent=STYLES["body"], fontName="Times-Bold", fontSize=size,
                               leading=size * 1.15, textColor=c or INK)
        return Paragraph(escape(str(v)), style)

    values = [value_cell(v, c) for _, v, c in stats]
    labels = [Paragraph(escape(label.upper()), STYLES["kicker"]) for label, _, _ in stats]
    t = Table([labels, values], colWidths=[col_width] * len(stats))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAPER),
        ("LINEAFTER", (0, 0), (-2, -1), 0.5, RULE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return t


def _kv_table(rows, widths=(55 * mm, None)):
    width = widths[1] or (A4[0] - 36 * mm - widths[0])
    data = [[_p(k, "muted"), _p(v)] for k, v in rows]
    t = Table(data, colWidths=[widths[0], width])
    t.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def _chart_scores(scores, path):
    fig, ax = plt.subplots(figsize=(7.2, 2.6), dpi=200)
    labels = [f"Q{i + 1}" for i in range(len(scores))]
    bar_colors = ["#1f5c4a" if s >= 70 else "#b4622a" if s >= 45 else "#a23a2e" for s in scores]
    bars = ax.bar(labels, scores, color=bar_colors, width=0.55)
    for b, s in zip(bars, scores):
        ax.text(b.get_x() + b.get_width() / 2, s + 2, str(s), ha="center", fontsize=8, color="#1c1b19")
    ax.set_ylim(0, 105)
    ax.axhline(70, color="#6b675f", linewidth=0.6, linestyle=(0, (3, 3)))
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#dcd7cc")
    ax.tick_params(axis="both", labelsize=8, colors="#6b675f", length=0)
    ax.set_yticks([0, 50, 100])
    ax.grid(axis="y", color="#ece8df", linewidth=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(path, transparent=True)
    plt.close(fig)


def _qtext(q):
    return q["question"] if isinstance(q, dict) else str(q)


def _qtype(q):
    return q.get("type", "theory") if isinstance(q, dict) else "theory"


# ---------------------------------------------------------------------------
# Interview report
# ---------------------------------------------------------------------------

def interview_report(session):
    questions = session["questions"]
    answers = session["answers"]
    evaluations = session["evaluations"]
    fa = session.get("final_assessment") or {}
    candidate = session.get("candidate_name") or "Candidate"
    path = os.path.join(REPORTS_DIR, f"interview_{session['session_id']}.pdf")

    story = [
        _p("INTERVIEW ASSESSMENT", "kicker"),
        _p(f"{candidate}", "title"),
        _p(f"{datetime.now().strftime('%d %B %Y, %H:%M')}  |  {len(questions)} questions  |  "
           f"graded by {session.get('model', 'local model')}", "muted"),
        Spacer(1, 10),
    ]

    avg = fa.get("average_score", 0)
    story.append(_stat_table([
        ("Average score", f"{avg:.0f}/100", _score_color(avg)),
        ("Recommendation", fa.get("final_recommendation", "-"), None),
        ("Level", fa.get("technical_level", "-"), None),
        ("Answered", f"{fa.get('questions_answered', 0)}/{fa.get('questions_total', len(questions))}", None),
    ]))

    story += [_p("Summary", "h2"), _p(fa.get("overall_assessment", ""))]

    scores = [e.get("overall_score", 0) for e in evaluations]
    if scores:
        chart = os.path.join(tempfile.gettempdir(), f"chart_{session['session_id']}.png")
        _chart_scores(scores, chart)
        story += [_p("Score by question", "h2"), Image(chart, width=A4[0] - 36 * mm, height=(A4[0] - 36 * mm) * 2.6 / 7.2)]

    two_col = Table([[
        [_p("Strengths", "h3")] + _bullets(fa.get("key_strengths", [])),
        [_p("Focus areas", "h3")] + _bullets(fa.get("development_areas", [])),
    ]], colWidths=[(A4[0] - 36 * mm) / 2] * 2)
    two_col.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [Spacer(1, 6), two_col]

    ratings = [
        ("Communication", f"{fa.get('communication_rating', '-')}/10"),
        ("Problem solving", f"{fa.get('problem_solving_rating', '-')}/10"),
        ("Next steps", fa.get("next_steps", "")),
    ]
    activity = session.get("activity_summary")
    if activity:
        ratings.insert(2, ("Camera activity",
                           f"Eye contact {_pct(activity.get('eye_contact_pct'))}, upright posture "
                           f"{_pct(activity.get('posture_pct'))}, tab switches {activity.get('tab_switches', 0)}"))
    story += [Spacer(1, 8), _kv_table(ratings)]

    story.append(PageBreak())
    story.append(_p("Question by question", "h2"))
    for i, (q, a, e) in enumerate(zip(questions, answers, evaluations), 1):
        score = e.get("overall_score", 0)
        block = [
            Table([[_p(f"Q{i}  |  {_qtype(q).upper()}", "kicker"),
                    Paragraph(f'<para alignment="right"><font name="Times-Bold" size="14" '
                              f'color="{_hex(_score_color(score))}">{score}/100</font></para>', STYLES["body"])]],
                  colWidths=[(A4[0] - 36 * mm) * 0.7, (A4[0] - 36 * mm) * 0.3],
                  style=[("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                         ("LINEABOVE", (0, 0), (-1, 0), 0.8, INK), ("TOPPADDING", (0, 0), (-1, -1), 6)]),
            _p(_qtext(q), "h3"),
        ]
        answer_style = "mono" if _qtype(q) == "coding" else "quote"
        answer_text = a if a else "(no answer)"
        block += [_p("Your answer", "muted"), _p(answer_text[:1800], answer_style), Spacer(1, 4)]
        cats = e.get("category_scores") or {}
        if cats:
            block.append(_p("  |  ".join(f"{k.replace('_', ' ').title()} {v}" for k, v in cats.items()), "muted"))
        if e.get("detailed_feedback"):
            block += [Spacer(1, 3), _p(e["detailed_feedback"])]
        story.append(KeepTogether(block))
        detail_rows = []
        if e.get("strengths"):
            detail_rows.append(("What worked", "\n".join(f"- {s}" for s in e["strengths"])))
        if e.get("weaknesses"):
            detail_rows.append(("What was missing", "\n".join(f"- {s}" for s in e["weaknesses"])))
        if e.get("improvement_suggestions"):
            detail_rows.append(("To improve", "\n".join(f"- {s}" for s in e["improvement_suggestions"])))
        if e.get("model_answer"):
            detail_rows.append(("A strong answer", e["model_answer"]))
        if detail_rows:
            story += [Spacer(1, 4), _kv_table(detail_rows, widths=(34 * mm, None))]
        story.append(Spacer(1, 14))

    _doc(path).build(story, onFirstPage=_footer("Interview assessment"), onLaterPages=_footer("Interview assessment"))
    return path


# ---------------------------------------------------------------------------
# Activity report
# ---------------------------------------------------------------------------

def activity_report(session, summary, evidence):
    path = os.path.join(REPORTS_DIR, f"activity_{session['session_id']}.pdf")
    story = [
        _p("ACTIVITY REPORT", "kicker"),
        _p("Camera & focus monitoring", "title"),
        _p(f"{datetime.now().strftime('%d %B %Y, %H:%M')}  |  {summary['duration_min']} min observed  |  "
           f"{summary['frames']} frames analysed", "muted"),
        Spacer(1, 10),
        _stat_table([
            ("Eye contact", _pct(summary["eye_contact_pct"]), _score_color(summary["eye_contact_pct"])),
            ("Upright posture", _pct(summary["posture_pct"]), _score_color(summary["posture_pct"])),
            ("Face visible", f"{summary['face_visible_pct']}%", _score_color(summary["face_visible_pct"])),
            ("Tab switches", str(summary["tab_switches"]),
             ACCENT if summary["tab_switches"] == 0 else BAD),
        ]),
        _p("Observations", "h2"),
    ]
    story += _bullets(summary["observations"])
    story += [_p("How to improve", "h2")] + _bullets(summary["tips"])

    story += [_p("Breakdown", "h2"), _kv_table([
        ("Looking at screen", f"{summary['counts']['gaze_center']} frames"),
        ("Looking away (left/right)", f"{summary['counts']['gaze_side']} frames"),
        ("Looking down", f"{summary['counts']['gaze_down']} frames"),
        ("Face not in frame", f"{summary['counts']['no_face']} frames"),
        ("More than one person", f"{summary['counts']['multiple_faces']} frames"),
        ("Slouched or tilted posture", f"{summary['counts']['posture_bad']} frames"),
        ("Frequent hand movement", f"{summary['counts']['hand_motion']} frames"),
    ])]

    if summary.get("tab_events"):
        story += [_p("Tab switch log", "h2"), _kv_table(
            [(f"#{i + 1}", t) for i, t in enumerate(summary["tab_events"][:20])], widths=(20 * mm, None))]

    shots = [(label, p) for label, p in evidence if os.path.exists(p)][:9]
    if shots:
        story += [PageBreak(), _p("Evidence frames", "h2"),
                  _p("Sample frames captured when an issue was detected.", "muted"), Spacer(1, 6)]
        cell_w = (A4[0] - 36 * mm) / 3 - 4
        rows, row = [], []
        for label, p in shots:
            row.append([Image(p, width=cell_w, height=cell_w * 0.75), _p(label, "muted")])
            if len(row) == 3:
                rows.append(row)
                row = []
        if row:
            rows.append(row + [""] * (3 - len(row)))
        grid = Table(rows, colWidths=[cell_w + 4] * 3)
        grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
        story.append(grid)

    _doc(path).build(story, onFirstPage=_footer("Activity report"), onLaterPages=_footer("Activity report"))
    return path


# ---------------------------------------------------------------------------
# ATS report
# ---------------------------------------------------------------------------

def ats_report(result, session_id):
    path = os.path.join(REPORTS_DIR, f"ats_{session_id}.pdf")
    d = result.get("details", {})
    m = d.get("metrics", {})
    s = result["sections"]
    story = [
        _p("RESUME ANALYSIS", "kicker"),
        _p(d.get("name") or "ATS compatibility report", "title"),
        _p(datetime.now().strftime("%d %B %Y, %H:%M")
           + ("  |  checked against a job description" if d.get("job_description_used") else ""), "muted"),
        Spacer(1, 10),
        _stat_table([
            ("Overall", f"{result['overallScore']}", _score_color(result["overallScore"])),
            ("Keywords", str(s["keywords"]["score"]), _score_color(s["keywords"]["score"])),
            ("Impact", str(s["experience"]["score"]), _score_color(s["experience"]["score"])),
            ("Structure", str(s["formatting"]["score"]), _score_color(s["formatting"]["score"])),
            ("Skills", str(s["skills"]["score"]), _score_color(s["skills"]["score"])),
        ]),
        Spacer(1, 8),
        _p(result.get("summary", "")),
        _p("Priority fixes", "h2"),
    ]
    story += [Paragraph(f"<b>{i}.</b>&nbsp;&nbsp;{escape(t)}", STYLES["body"])
              for i, t in enumerate(result.get("suggestions", []), 1)]

    if result.get("bullet_rewrites"):
        story.append(_p("Bullet rewrites", "h2"))
        for r in result["bullet_rewrites"]:
            story.append(KeepTogether([_p("Before", "muted"), _p(r["original"], "quote"),
                                       _p("After", "muted"), _p(r["improved"]), Spacer(1, 8)]))

    labels = {"keywords": "Keywords", "experience": "Impact & experience", "formatting": "Structure & contact",
              "skills": "Skills"}
    story.append(_p("Section detail", "h2"))
    for key in ("keywords", "experience", "formatting", "skills"):
        story.append(KeepTogether([_p(f"{labels[key]}  -  {s[key]['score']}/100", "h3")] + _bullets(s[key]["feedback"])))

    rows = [
        ("Sections found", ", ".join(d.get("sections_found", [])) or "-"),
        ("Sections missing", ", ".join(d.get("sections_missing", [])) or "none"),
        ("Words / pages", f"{m.get('word_count', 0)} words, {m.get('pages', 0)} page(s)"),
        ("Bullet points", f"{m.get('bullets', 0)} ({m.get('quantified_bullets', 0)} quantified, "
                          f"{m.get('action_verb_bullets', 0)} start with an action verb)"),
    ]
    for cat, skills in (d.get("skills_by_category") or {}).items():
        rows.append((cat, ", ".join(skills)))
    if d.get("missing_keywords"):
        rows.append(("Missing keywords", ", ".join(d["missing_keywords"])))
    story += [_p("Parsed data", "h2"), _kv_table(rows)]

    _doc(path).build(story, onFirstPage=_footer("Resume analysis"), onLaterPages=_footer("Resume analysis"))
    return path
