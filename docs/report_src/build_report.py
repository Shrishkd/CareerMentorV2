"""Builds docs/Career_Mentor_Project_Report.pdf from the project's real data."""
import glob
import json
import os
import re
import sys
from datetime import datetime
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak, PageTemplate, Paragraph,
    Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "fig")
SHOTS = os.path.join(ROOT, "docs", "screenshots")
OUT = os.path.join(ROOT, "docs", "Career_Mentor_Project_Report.pdf")
sys.path.insert(0, os.path.join(ROOT, "Backend"))

SESSION = json.load(open(f"{ROOT}/data/sessions/c56dbf04-c8da-42f2-abbf-7b0de1de2b6e.json", encoding="utf-8"))
ATS_SESSION = json.load(open(f"{ROOT}/data/sessions/193ebf83-dabd-432c-90f7-eb3a816229e3.json", encoding="utf-8"))
ATS = ATS_SESSION["ats_result"]

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
ORANGE = colors.HexColor("#F46A3D")
PURPLE = colors.HexColor("#A855F7")
NAVY = colors.HexColor("#1E293B")
SLATE = colors.HexColor("#475569")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#E2E8F0")
TINT = colors.HexColor("#F8FAFC")
ORANGE_TINT = colors.HexColor("#FFF3EE")
PURPLE_TINT = colors.HexColor("#F6EEFF")
GREEN = colors.HexColor("#16A34A")
AMBER = colors.HexColor("#D97706")
RED = colors.HexColor("#DC2626")

W, H = A4
MARGIN = 2.2 * cm
CONTENT_W = W - 2 * MARGIN

S = {
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14.6, textColor=NAVY,
                           alignment=TA_JUSTIFY, spaceAfter=6),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=8.6, leading=12, textColor=SLATE),
    "caption": ParagraphStyle("caption", fontName="Helvetica-Oblique", fontSize=8.4, leading=11, textColor=MUTED,
                              alignment=TA_CENTER, spaceBefore=4, spaceAfter=12),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=21, leading=26, textColor=NAVY, spaceAfter=4),
    "kicker": ParagraphStyle("kicker", fontName="Helvetica-Bold", fontSize=9, leading=12, textColor=ORANGE,
                             spaceAfter=2),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13.5, leading=18, textColor=NAVY, spaceBefore=12,
                         spaceAfter=5),
    "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10.8, leading=14, textColor=PURPLE,
                         spaceBefore=8, spaceAfter=3),
    "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=10, leading=14.2, textColor=NAVY,
                             leftIndent=14, bulletIndent=3, spaceAfter=2),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=8.6, leading=11.4, textColor=NAVY),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=8.6, leading=11.4, textColor=NAVY),
    "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=8.6, leading=11.4, textColor=colors.white),
    "quote": ParagraphStyle("quote", fontName="Helvetica-Oblique", fontSize=9.2, leading=13, textColor=SLATE,
                            leftIndent=10, rightIndent=6),
    "mono": ParagraphStyle("mono", fontName="Courier", fontSize=8, leading=10.4, textColor=NAVY, leftIndent=10),
    "toc1": ParagraphStyle("toc1", fontName="Helvetica-Bold", fontSize=10.5, leading=16, textColor=NAVY),
    "toc2": ParagraphStyle("toc2", fontName="Helvetica", fontSize=9.4, leading=13.5, textColor=SLATE, leftIndent=16),
}


for _k in ("h1", "h2", "h3", "kicker"):
    S[_k].keepWithNext = 1


def clean(text):
    """Standard PDF fonts only cover Windows-1252; map everything else to safe equivalents."""
    text = str(text or "")
    for a, b in {"→": "->", "←": "<-", "✓": "", "✔": "", "✗": "x", "≥": ">=",
                 "≤": "<=", "×": "x", "≈": "~", "‑": "-", " ": " ", " ": " "}.items():
        text = text.replace(a, b)
    return text.encode("cp1252", "replace").decode("cp1252").replace("?", "?")


def P(text, style="body"):
    return Paragraph(clean(text), S[style])


def Pesc(text, style="body"):
    return Paragraph(escape(clean(text)).replace("\n", "<br/>"), S[style])


def bullets(items, style="bullet"):
    return [Paragraph(clean(i), S[style], bulletText="•") for i in items]


def fig(path, width=CONTENT_W, caption=None, max_h=None):
    with PILImage.open(path) as im:
        w, h = im.size
    height = width * h / w
    if max_h and height > max_h:
        width, height = max_h * w / h, max_h
    items = [Image(path, width=width, height=height)]
    if caption:
        items.append(P(caption, "caption"))
    return KeepTogether(items)


def table(rows, widths, header=True, zebra=True, align_top=True):
    data = []
    for r_i, row in enumerate(rows):
        style = "cellh" if header and r_i == 0 else "cell"
        data.append([c if not isinstance(c, str) else Paragraph(clean(c), S[style]) for c in row])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    cmds = [
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP" if align_top else "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        cmds.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                cmds.append(("BACKGROUND", (0, i), (-1, i), TINT))
    t.setStyle(TableStyle(cmds))
    return t


def callout(title, body, tint=ORANGE_TINT, bar=ORANGE):
    inner = [Paragraph(f"<b>{escape(clean(title))}</b>", S["cellb"]), Spacer(1, 2)]
    inner += [b if not isinstance(b, str) else P(b, "cell") for b in (body if isinstance(body, list) else [body])]
    t = Table([[inner]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), tint), ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t


def stat_row(stats):
    """[(label, value, color)] as big-number tiles."""
    cw = CONTENT_W / len(stats)
    def val(v, c):
        size = 19 if len(str(v)) <= 8 else 13
        st = ParagraphStyle("stat", parent=S["cell"], fontName="Helvetica-Bold", fontSize=size,
                            leading=size * 1.15, textColor=colors.HexColor(c))
        return Paragraph(escape(clean(v)), st)
    vals = [val(v, c) for _, v, c in stats]
    labs = [Paragraph(f'<font size="7.5" color="#64748B"><b>{escape(l.upper())}</b></font>', S["cell"])
            for l, _, _ in stats]
    t = Table([labs, vals], colWidths=[cw] * len(stats))
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), TINT), ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                           ("LINEAFTER", (0, 0), (-2, -1), 0.5, LINE), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 1), (-1, 1), 9), ("LEFTPADDING", (0, 0), (-1, -1), 9)]))
    return t


def tone_hex(v):
    return "#16A34A" if v >= 70 else "#D97706" if v >= 45 else "#DC2626"


# ---------------------------------------------------------------------------
# Document template with TOC support, cover page and running header/footer
# ---------------------------------------------------------------------------
class ReportDoc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(path, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=2.3 * cm,
                         bottomMargin=2 * cm, title="Career Mentor - Project Report", author="Shrish Das",
                         subject="AI mock interview platform built on open-source LLMs")
        frame = Frame(MARGIN, 2 * cm, CONTENT_W, H - 4.3 * cm, id="body")
        self.addPageTemplates([
            PageTemplate(id="cover", frames=[Frame(0, 0, W, H, id="c", leftPadding=0, rightPadding=0,
                                                   topPadding=0, bottomPadding=0)], onPage=draw_cover),
            PageTemplate(id="front", frames=[frame], onPage=draw_front),
            PageTemplate(id="main", frames=[frame], onPageEnd=draw_main),
        ])
        self.chapter = ""

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            name = flowable.style.name
            text = flowable.getPlainText()
            if name == "h1":
                self.chapter = text
                key = f"h1-{self.seq.nextf('h1')}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=0)
                self.notify("TOCEntry", (0, text, self.page - 1 - FRONT_PAGES[0], key))
            elif name == "h2":
                key = f"h2-{self.seq.nextf('h2')}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=1)
                self.notify("TOCEntry", (1, text, self.page - 1 - FRONT_PAGES[0], key))

    def handle_pageBegin(self):
        super().handle_pageBegin()


def draw_cover(canvas, doc):
    canvas.saveState()
    # gradient band (orange -> purple), matching the app
    steps = 120
    for i in range(steps):
        t = i / (steps - 1)
        r = 0xF4 + (0xA8 - 0xF4) * t
        g = 0x6A + (0x55 - 0x6A) * t
        b = 0x3D + (0xF7 - 0x3D) * t
        canvas.setFillColorRGB(r / 255, g / 255, b / 255)
        canvas.rect(W * i / steps, H * 0.42, W / steps + 1, H * 0.58, stroke=0, fill=1)
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, W, H * 0.42, stroke=0, fill=1)

    logo = os.path.join(ROOT, "Frontend", "public", "favicon.ico")
    try:
        png = os.path.join(HERE, "logo.png")
        PILImage.open(logo).convert("RGBA").resize((256, 256)).save(png)
        canvas.drawImage(png, MARGIN, H - 5.2 * cm, 2.2 * cm, 2.2 * cm, mask="auto")
    except Exception:
        pass

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(MARGIN, H - 6.4 * cm, "PROJECT REPORT")
    canvas.setFont("Helvetica-Bold", 40)
    canvas.drawString(MARGIN, H - 8.2 * cm, "Career Mentor")
    canvas.setFont("Helvetica", 15)
    y = H - 9.4 * cm
    for line in ["An AI mock interview platform that builds questions", "from your resume, grades answers with open-source",
                 "LLMs and monitors on-camera behaviour"]:
        canvas.drawString(MARGIN, y, line)
        y -= 0.72 * cm
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(MARGIN, H * 0.42 + 1.3 * cm, "Version 2.0   |   Qwen3-4B via Ollama   |   React + Flask")

    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica", 9.5)
    canvas.drawString(MARGIN, H * 0.42 - 1.6 * cm, "SUBMITTED BY")
    canvas.setFont("Helvetica-Bold", 17)
    canvas.drawString(MARGIN, H * 0.42 - 2.4 * cm, "Shrish Das")
    canvas.setFont("Helvetica", 11)
    canvas.setFillColor(SLATE)
    canvas.drawString(MARGIN, H * 0.42 - 3.05 * cm, "B.Tech in Computer Science and Engineering (AI & ML)")
    canvas.drawString(MARGIN, H * 0.42 - 3.65 * cm, "VIT Bhopal University")

    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica", 9.5)
    canvas.drawString(MARGIN, H * 0.42 - 5.1 * cm, "LINKS")
    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(SLATE)
    links = [("Live demo", "https://career-mentor-6ctn.onrender.com"),
             ("Source code", "https://github.com/Shrishkd/CareerMentorV2"),
             ("Portfolio", "https://shrishcraft.vercel.app")]
    y = H * 0.42 - 5.8 * cm
    for label, url in links:
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(MARGIN, y, label)
        canvas.setFont("Helvetica", 10)
        canvas.drawString(MARGIN + 2.6 * cm, y, url)
        canvas.linkURL(url, (MARGIN + 2.6 * cm, y - 2, MARGIN + 11 * cm, y + 10))
        y -= 0.6 * cm

    canvas.setStrokeColor(LINE)
    canvas.line(MARGIN, 2.2 * cm, W - MARGIN, 2.2 * cm)
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 1.6 * cm, datetime(2026, 9, 22).strftime("%B %Y"))
    canvas.drawRightString(W - MARGIN, 1.6 * cm, "Career Mentor v2.0")
    canvas.restoreState()


def _footer(canvas, doc, roman=False):
    canvas.setStrokeColor(LINE)
    canvas.line(MARGIN, 1.5 * cm, W - MARGIN, 1.5 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, 1.05 * cm, "Career Mentor  |  Project Report")
    num = doc.page - 1
    label = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii"][num - 1] if roman else str(num - FRONT_PAGES[0])
    canvas.drawRightString(W - MARGIN, 1.05 * cm, label)


FRONT_PAGES = [0]


def draw_front(canvas, doc):
    canvas.saveState()
    FRONT_PAGES[0] = doc.page - 1
    _footer(canvas, doc, roman=True)
    canvas.restoreState()


def draw_main(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(ORANGE)
    canvas.rect(MARGIN, H - 1.45 * cm, 1.2 * cm, 0.1 * cm, stroke=0, fill=1)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(W - MARGIN, H - 1.42 * cm, clean(doc.chapter)[:80])
    _footer(canvas, doc)
    canvas.restoreState()


def chapter(num, title, kicker=None):
    return [PageBreak(), P(kicker or f"CHAPTER {num}", "kicker"), P(title, "h1"),
            Table([[""]], colWidths=[3 * cm], rowHeights=[0.12 * cm],
                  style=[("BACKGROUND", (0, 0), (-1, -1), ORANGE)]), Spacer(1, 10)]


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------
Q = SESSION["questions"]
EV = SESSION["evaluations"]
AN = SESSION["answers"]
FA = SESSION["final_assessment"]
ACT = SESSION["activity_summary"]
START = datetime.fromisoformat(SESSION["created_at"])
END = datetime.fromisoformat(SESSION["finished_at"])
MAXIMA = {"technical_accuracy": 30, "depth": 25, "clarity": 20, "examples": 15, "relevance": 10,
          "correctness": 40, "efficiency": 20, "code_quality": 15, "edge_cases": 15, "explanation": 10}


def evidence_frames():
    labels = {"gaze_down": "Looking down", "gaze_side": "Looking away", "no_face": "Face not visible",
              "posture_bad": "Slouched / tilted posture", "multiple_faces": "Another person in frame"}
    out = []
    for p in sorted(glob.glob(f"{ROOT}/reports/evidence/{SESSION['session_id']}_*.jpg"),
                    key=lambda p: int(re.search(r"_(\d+)\.jpg$", p).group(1))):
        m = re.search(r"_(gaze_down|gaze_side|no_face|posture_bad|multiple_faces)_(\d+)\.jpg$", p)
        frame = int(m.group(2))
        secs = int(frame * 2.5)
        out.append((p, f"{labels[m.group(1)]} - frame {frame} (~{secs // 60}:{secs % 60:02d})"))
    return out


# Final calibration run of the deterministic scorer (no job description) over the 14 distinct
# resumes that were in Backend/uploads on 22 Sep 2026. Recorded then; that folder has since been cleared.
# (overall, bullets, quantified bullets, bullets starting with an action verb)
CALIBRATION = [(84, 12, 6, 7), (84, 12, 2, 12), (83, 13, 2, 12), (83, 11, 4, 6), (82, 15, 4, 14), (82, 10, 1, 7),
               (81, 13, 4, 5), (79, 14, 1, 8), (75, 11, 0, 9), (75, 11, 0, 9), (71, 5, 1, 1), (71, 8, 1, 3),
               (70, 4, 3, 1), (61, 5, 0, 4)]


def calibration():
    return [(f"R{i+1}", *row) for i, row in enumerate(CALIBRATION)]


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------
def front_matter():
    story = [NextPageTemplate("front"), PageBreak()]
    story += [P("ABSTRACT", "kicker"), Paragraph("Abstract", ParagraphStyle("abs", parent=S["h1"])), Spacer(1, 6)]
    story += [P(t) for t in [
        "Technical interviews reward candidates who can explain their own work clearly under pressure, yet most "
        "students practise with generic question banks that have nothing to do with the projects on their resume, "
        "and rarely receive feedback that explains <i>why</i> an answer was weak. Commercial AI tools that could fill "
        "this gap usually depend on paid cloud APIs, send personal data to third parties, and stop working when a "
        "quota or subscription runs out.",
        "<b>Career Mentor</b> is a full-stack mock interview platform that addresses this. A candidate uploads a "
        "resume (PDF or DOCX); the system parses it, detects sections and skills, and uses a locally hosted "
        "open-source large language model (<b>Qwen3-4B served by Ollama</b>) to generate three conceptual and two "
        "coding questions about the candidate's actual projects. Answers can be spoken (transcribed on-device with "
        "<b>OpenAI Whisper</b>), typed, or written in an integrated code editor. While the candidate answers, the "
        "browser streams webcam frames to the backend, where <b>MediaPipe</b> measures eye contact, posture, face "
        "visibility and hand movement, and tab switches are logged. Each answer is graded against a fixed rubric in "
        "a background queue, so the candidate never waits between questions. The session ends with two PDF "
        "reports: an interview assessment with scores, feedback and a model answer for every question, and an "
        "activity report with evidence frames. A separate ATS resume checker scores resumes deterministically "
        "against a job description and suggests bullet-point rewrites.",
        "Version 2 replaces the Google Gemini API of version 1 with a local model chosen by benchmarking three "
        "candidates on the real grading task on an 8 GB, CPU-only laptop. Structured JSON-schema decoding, few-shot "
        "grading examples and output guards make a 4-billion-parameter model reliable enough for rubric grading. "
        "In the recorded trial described in Chapter 7, the system generated resume-specific questions, transcribed "
        "and graded two spoken answers and one coding answer, analysed 305 webcam frames over 12.8 minutes, and "
        "produced both reports with no cloud services involved. Every model call is logged in chat format so the "
        "model can later be fine-tuned with QLoRA on reviewed interview data.",
    ]]
    story += [Spacer(1, 6), callout("Keywords", "AI mock interview, large language models, Qwen3, Ollama, speech "
                                    "recognition, Whisper, MediaPipe, computer vision, ATS resume analysis, "
                                    "rubric-based grading, QLoRA fine-tuning, React, Flask")]
    story += [PageBreak(), P("CONTENTS", "kicker"), Paragraph("Table of Contents", ParagraphStyle("tochead", parent=S["h1"])), Spacer(1, 8)]
    toc = TableOfContents()
    toc.levelStyles = [S["toc1"], S["toc2"]]
    toc.dotsMinLevel = 0
    story += [toc, NextPageTemplate("main")]
    return story


def ch_introduction():
    s = chapter(1, "Introduction")
    s += [P("1.1 Background", "h2"), P(
        "Campus placements and early-career hiring increasingly rely on technical interviews in which candidates are "
        "asked about the projects listed on their resume, followed by one or two coding problems. Two skills are "
        "tested at once: technical understanding, and the ability to communicate that understanding clearly while "
        "being observed. Many interviews are now conducted online with the camera on, and proctoring software "
        "flags candidates who look away from the screen or switch browser tabs."),
        P("Large language models (LLMs) make it possible to simulate an interviewer that reads a resume, asks "
          "relevant questions and critiques answers. Until recently this required large cloud-hosted models. "
          "Small open-weight models such as Qwen3-4B can now run on an ordinary laptop, which makes a private, "
          "free and offline-capable interview coach practical.")]
    s += [P("1.2 Problem statement", "h2"), P(
        "Students preparing for technical interviews lack a practice environment that (a) asks about <i>their own</i> "
        "projects rather than generic trivia, (b) grades answers consistently and explains what a strong answer looks "
        "like, (c) gives feedback on on-camera behaviour, and (d) is free, private and not dependent on a paid API "
        "that can run out of quota or change its terms.")]
    s += [P("1.3 Objectives", "h2")] + bullets([
        "Generate interview questions tailored to the projects, tools and skills found in an uploaded resume.",
        "Accept answers by voice, text or code, and grade each one against a transparent rubric with actionable "
        "feedback and a model answer.",
        "Monitor eye contact, posture, face visibility, other people in frame and tab switches during the interview.",
        "Produce a detailed interview assessment report and an activity report as downloadable PDFs.",
        "Provide an ATS resume checker with deterministic scoring, keyword matching against a job description and "
        "bullet-point rewrites.",
        "Run all AI on open-source models locally, with no paid APIs and no user accounts.",
        "Keep the LLM reliable on CPU-only hardware, and log interactions so the model can be fine-tuned later.",
    ])
    s += [P("1.4 Scope", "h2"), P(
        "The system targets university students and early-career software engineers preparing for technical rounds. "
        "Each session contains five questions (three conceptual, two data-structures-and-algorithms problems). "
        "HR and behavioural rounds, multi-round interview pipelines and recruiter-side features are outside the "
        "scope of this version and are listed as future work in Chapter 10.")]
    s += [P("1.5 Organisation of the report", "h2"), table([
        ["Chapter", "Contents"],
        ["2  Motivation", "Why the project was built"],
        ["3  Existing approaches", "How candidates practise today, and the gap Career Mentor fills"],
        ["4  System design", "Architecture, workflow, modules, data model, technology stack and API"],
        ["5  Implementation", "Resume analyser, interview engine, grading queue, speech, monitoring, reports, UI"],
        ["6  Model selection and fine-tuning", "Benchmarks, prompt engineering, latency and the QLoRA pipeline"],
        ["7  Trial run summary", "A complete recorded interview and resume check, with captured images"],
        ["8  Testing and validation", "End-to-end tests, grading and ATS calibration, bugs fixed"],
        ["9  Version 1 vs version 2", "What changed and why"],
        ["10 Limitations and future scope", "Known constraints and planned work"],
        ["11 Conclusion", "Summary of outcomes"],
    ], [4.8 * cm, CONTENT_W - 4.8 * cm])]
    return s


def ch_motivation():
    s = chapter(2, "Motivation: Why I Built This")
    s += [P(
        "I kept losing interviews I was technically ready for. I had the skills and the projects, but I did not know "
        "what interviewers were really looking for, and I never got to practise explaining my own work out loud "
        "before it mattered. The anxiety of the unknown, the pressure of the moment and the silence after the "
        "interview were the hardest parts."),
        P("What was missing was a <b>safe place to fail first</b>: somewhere to practise, receive feedback "
          "immediately, and improve without the stakes being life-altering. Career Mentor started as that place. "
          "Version 1 proved the idea, but it depended on a paid cloud API and a hosted authentication service that "
          "paused when the project was inactive, which locked users out. Version 2 was rebuilt around open-source "
          "models running on the user's own machine, so any student can use it for free, without API limits and "
          "without handing their resume to a third party."),
        Spacer(1, 6),
        callout("Guiding principle", "\"We believe that everyone deserves a chance to land their dream job. This "
                "platform is my contribution to that belief.\"", PURPLE_TINT, PURPLE),
        P("2.1 Design goals that follow from this", "h2")]
    s += bullets([
        "<b>Personal:</b> every question must refer to something the candidate actually built.",
        "<b>Honest:</b> scores come from an explicit rubric, and weak answers get specific reasons and a model answer.",
        "<b>Realistic:</b> spoken answers, a real code editor and proctoring-style camera checks.",
        "<b>Accessible:</b> no sign-up, no API key and no cost; usable on a mid-range laptop.",
        "<b>Private:</b> resumes, recordings and camera frames never leave the user's machine.",
    ])
    return s


def ch_existing():
    s = chapter(3, "Existing Approaches and Gap Analysis")
    s += [P(
        "Candidates typically combine several kinds of practice. Each covers part of what a real interview tests, "
        "but none covers all of it. Table 3.1 compares these approaches with both versions of Career Mentor on the "
        "criteria that matter for this project.")]
    y, n, p = "Yes", "No", "Partial"
    s += [table([
        ["Criterion", "Question banks", "Peer mock interviews", "General AI chatbots", "Career Mentor v1",
         "Career Mentor v2"],
        ["Questions from your resume", n, p, p, y, y],
        ["Consistent rubric scoring", n, n, n, p, y],
        ["Model answer for every question", p, n, p, n, y],
        ["Spoken answers", n, y, p, y, y],
        ["Coding round with editor", y, p, n, y, y],
        ["Camera / focus feedback", n, p, n, p, y],
        ["ATS resume analysis", n, n, p, p, y],
        ["Works without paid API", y, y, n, n, y],
        ["Resume stays on your machine", y, n, n, n, y],
        ["No account needed", p, n, n, n, y],
    ], [4.3 * cm] + [(CONTENT_W - 4.3 * cm) / 5] * 5), P(
        "Table 3.1: Comparison of practice approaches. Ratings describe typical products in each category.", "caption")]
    s += [P("3.1 The gap", "h2"), P(
        "The combination that is hard to find is <b>personalised questions + rubric-based feedback with model "
        "answers + behavioural monitoring</b>, delivered <b>privately and at no cost</b>. Career Mentor v2 is designed "
        "around exactly that combination. Running the model locally is the decision that makes the privacy and cost "
        "goals achievable, and most of the engineering in Chapters 5 and 6 goes into making a small local model "
        "behave reliably.")]
    return s


def ch_design():
    s = chapter(4, "System Design")
    s += [P("4.1 Architecture", "h2"), P(
        "The system has three tiers: a React single-page application in the browser, a Flask backend that "
        "orchestrates parsing, grading, monitoring and report generation, and a local AI tier where Ollama serves "
        "the Qwen3-4B model. Whisper and MediaPipe run inside the backend process."),
        fig(f"{FIG}/architecture.png", caption="Figure 4.1: System architecture")]
    s += [P("4.2 Interview workflow", "h2"), fig(f"{FIG}/workflow.png", caption="Figure 4.2: End-to-end interview workflow"),
          P("Answers are submitted to a background queue and the candidate moves straight on. The queue transcribes "
            "spoken answers with Whisper and grades them with the LLM, one job at a time so the CPU stays free for "
            "the model. When the candidate finishes, the results page polls the backend until every answer is graded, "
            "then the final assessment and PDF reports are generated.")]
    s += [P("4.3 Backend modules", "h2"), table([
        ["Module", "Responsibility"],
        ["backend_api.py", "Flask routes; file-backed session store; background grading queue; report orchestration; "
                           "per-user statistics keyed by an anonymous browser id"],
        ["llm.py", "Ollama client. Every call requests output constrained to a JSON schema, disables Qwen3's thinking "
                   "mode for speed, retries on failure and logs the exchange for fine-tuning"],
        ["resume_analyzer.py", "PDF (PyMuPDF, column-aware) and DOCX extraction; section, contact and skill detection; "
                               "deterministic ATS scoring; optional LLM review with an invented-number guard"],
        ["interview_engine.py", "Question generation, rubric grading with few-shot examples, empty-output detection, "
                                "final assessment, and rule-based fallbacks for every step"],
        ["speech.py", "Whisper speech-to-text, loaded in a background thread at start-up"],
        ["monitoring.py", "Per-session MediaPipe face mesh, pose and hands analysis with baseline calibration"],
        ["reports.py", "Interview, activity and ATS PDF reports (ReportLab + Matplotlib)"],
    ], [3.6 * cm, CONTENT_W - 3.6 * cm])]
    s += [P("4.4 Data model", "h2"), P(
        "Each interview or resume check is a <b>session</b>, held in memory and mirrored to "
        "<font name='Courier'>data/sessions/&lt;id&gt;.json</font> so restarts do not lose work. Answers and "
        "evaluations are stored <i>by question index</i>, so skipping or re-answering a question never misaligns the "
        "results (a bug in version 1)."),
        table([
            ["Field", "Description"],
            ["session_id, purpose", "UUID; 'interview' or 'ats'"],
            ["user_id, candidate_name", "Anonymous browser id; name from the profile or detected on the resume"],
            ["resume_text, resume_links, skills", "Extracted text, hyperlinks and detected skills"],
            ["questions[]", "{type: theory | coding, topic, question}"],
            ["answers[] / evaluations[] / status[]", "Per question: transcript or code, rubric evaluation, and "
                                                      "pending / queued / processing / done / skipped"],
            ["tab_events[], activity_summary", "Tab-switch log and the camera monitoring summary"],
            ["final_assessment, report paths", "Verdict, ratings and summary; locations of the generated PDFs"],
            ["ats_result", "Full ATS analysis for resume-check sessions"],
        ], [5.2 * cm, CONTENT_W - 5.2 * cm])]
    s += [P("4.5 Technology stack", "h2"), table([
        ["Layer", "Technology", "Why"],
        ["Frontend", "React 18, TypeScript 5, Vite 5", "Typed SPA with fast builds"],
        ["UI", "Tailwind CSS 3, shadcn/ui (Radix), Framer Motion", "Accessible components and animation"],
        ["Data & routing", "TanStack Query 5, React Router 6", "Caching and client-side routing"],
        ["Editor & charts", "Monaco Editor, Recharts", "VS Code-grade editor; dashboard charts"],
        ["Backend", "Python 3.11, Flask 3, Flask-CORS", "Lightweight REST API"],
        ["LLM", "Ollama + Qwen3-4B (Q4, ~2.5 GB)", "Local, free, fine-tunable, reliable JSON"],
        ["Speech", "OpenAI Whisper (small) + ffmpeg", "Accurate on-device transcription"],
        ["Vision", "MediaPipe 0.10 (Face Mesh, Pose, Hands), OpenCV", "Real-time landmarks on CPU"],
        ["Documents", "PyMuPDF, ReportLab, Matplotlib", "Parsing resumes; generating PDF reports"],
        ["Fine-tuning", "Unsloth, TRL (QLoRA), GGUF export", "Train on a free GPU, run in Ollama"],
        ["Hosting", "Render static site, Docker", "Free frontend hosting; containerised API"],
    ], [2.8 * cm, 6.4 * cm, CONTENT_W - 9.2 * cm])]
    s += [P("4.6 REST API", "h2"), table([
        ["Method", "Endpoint", "Purpose"],
        ["GET", "/api/healthz", "Status of the LLM, Whisper, MediaPipe and the grading queue"],
        ["POST", "/api/upload-resume", "Parse a resume; for interviews, generate the questions"],
        ["POST", "/api/submit-answer", "Queue a text, code or audio answer for grading"],
        ["GET", "/api/session/<id>", "Grading progress"],
        ["POST", "/api/monitor-frame", "Analyse one webcam frame; returns live face/gaze/posture status"],
        ["POST", "/api/monitor-event", "Record a tab switch"],
        ["POST", "/api/generate-report", "Finish the interview; poll until the reports are ready"],
        ["GET", "/api/report/<id>/<kind>", "Download the interview, activity or ATS PDF"],
        ["POST", "/api/ats-check", "Run the ATS analysis (optionally against a job description)"],
        ["POST", "/api/generate-ats-report", "Build the ATS PDF"],
        ["GET", "/api/user-stats/<user_id>", "History for the dashboard"],
    ], [1.5 * cm, 5.2 * cm, CONTENT_W - 6.7 * cm])]
    return s


def ch_implementation():
    s = chapter(5, "Implementation")
    s += [P("5.1 Resume analyser", "h2"), P(
        "Version 1 sent only the first 1,000 characters of a resume to a cloud LLM and asked it to invent scores, "
        "which produced different results on every run. The new analyser separates <b>measurement</b> from "
        "<b>advice</b>: scores are computed deterministically from the parsed resume, and the LLM is only used "
        "afterwards to write a summary, suggestions and rewrites.")]
    s += [P("Extraction", "h3")] + bullets([
        "PDFs are read block by block with PyMuPDF. Two-column layouts are detected from the horizontal distribution "
        "of text and read column by column, so sidebars do not interleave with the main content.",
        "DOCX files are read directly from the document XML, with no extra dependency.",
        "Icon-font glyphs, non-breaking spaces and zero-width characters are removed; hyperlinks (LinkedIn, GitHub) "
        "are collected from the PDF link annotations.",
        "Files with almost no selectable text are flagged as scanned images that ATS software cannot read.",
    ])
    s += [P("Parsing", "h3")] + bullets([
        "Section headings are matched against about 50 aliases (e.g. 'Work Experience', 'Positions of "
        "Responsibility').",
        "A taxonomy of about 150 skills in 8 categories is matched with symbol-aware patterns (so 'C++', 'C#' and "
        "'.NET' work).",
        "Bullets are reconstructed across line wraps, then checked for measurable results (numbers, %, currency) and "
        "strong opening verbs, looking past a 'Project name:' prefix.",
    ])
    s += [P("Scoring", "h3"), table([
        ["Section", "Weight", "What is measured"],
        ["Keywords", "30%", "With a job description: share of its key terms present. Without one: breadth of "
                            "recognised skills, capped at 85"],
        ["Impact", "30%", "Share of bullets with a measurable result and with an action verb; penalties for vague "
                          "phrases and missing dates"],
        ["Structure", "20%", "Standard headings, email, phone, LinkedIn, sensible length, first-person pronouns"],
        ["Skills", "20%", "Number and spread of skills, a dedicated section, and how many skills are backed by a "
                          "project or role description"],
    ], [2.4 * cm, 1.6 * cm, CONTENT_W - 4 * cm]), Spacer(1, 6),
        callout("Guarding against invented results",
                "The LLM is told to use placeholders such as [X%] instead of made-up metrics. As a second line of "
                "defence, any number in a rewritten bullet that does not appear in the original resume is replaced "
                "with [X] before the rewrite is shown.")]
    s += [P("5.2 Interview engine", "h2"), P(
        "Questions are requested as a JSON object with a fixed schema: an array of items with a type ('theory' or "
        "'coding'), a topic and the question. The prompt contains a condensed profile (level, skills, experience and "
        "project sections) rather than the whole resume, which keeps prompts short on CPU. If the model returns too "
        "few questions of either type, the set is topped up from a built-in bank keyed by the candidate's skills."),
        P("Grading rubrics", "h3"), table([
            ["Conceptual question", "Max", "Coding question", "Max"],
            ["Technical accuracy", "30", "Correctness", "40"],
            ["Depth", "25", "Efficiency", "20"],
            ["Clarity", "20", "Code quality", "15"],
            ["Examples", "15", "Edge cases", "15"],
            ["Relevance", "10", "Explanation", "10"],
        ], [5.2 * cm, 2 * cm, 5.2 * cm, CONTENT_W - 12.4 * cm]),
        P("The overall score is always the <b>sum</b> of the category scores, so the headline number can never "
          "disagree with its breakdown. Skipped or near-empty answers are scored 0 by rule without calling the model.")]
    s += [P("Verdict thresholds", "h3"), table([
        ["Average score", "Verdict", "Level"],
        [">= 80", "Strong Hire", "Advanced"],
        ["65 - 79", "Hire", "Intermediate (>= 60)"],
        ["45 - 64", "Borderline", "Developing (>= 40)"],
        ["< 45", "Not Yet Ready", "Beginner (< 40)"],
    ], [4 * cm, 4 * cm, CONTENT_W - 8 * cm])]
    s += [P("5.3 Background grading queue and sessions", "h2"), P(
        "Grading one answer takes about a minute on a CPU, so version 1's synchronous design left candidates staring "
        "at a spinner after every answer. In version 2, <font name='Courier'>/api/submit-answer</font> stores the "
        "answer, marks it 'queued' and returns immediately. A single worker thread transcribes and grades jobs in "
        "order. The results page polls <font name='Courier'>/api/generate-report</font>, which reports per-question "
        "status until grading is complete, then builds the final assessment and PDFs in another thread.")]
    s += [P("5.4 Speech recognition", "h2"), P(
        "The browser records answers with the MediaRecorder API (WebM/Opus). The backend decodes them with ffmpeg "
        "and transcribes them with Whisper 'small', loaded in a background thread at start-up so the server is "
        "available immediately. The model size is configurable ('base' is roughly twice as fast).")]
    s += [P("5.5 Activity monitoring", "h2"), P(
        "Version 1 opened the <i>server's</i> webcam, so monitoring only worked when the backend ran on the "
        "candidate's own computer, and it always recorded for a fixed three minutes. It also contained a geometry "
        "error that classified almost every frame as 'looking down'. Version 2 moves capture to the browser: the "
        "interview page sends a 480-pixel JPEG every 2.5 seconds for the whole interview."),
        table([
            ["Signal", "Method", "Rule"],
            ["Face in frame", "Face mesh (max 2 faces)", "No face = out of frame; 2 faces = another person"],
            ["Gaze", "Nose position relative to face width (yaw) and eye-to-chin height (pitch)",
             "Compared with the median of the first 5 frames; yaw deviation > 0.12 = away, pitch > 0.10 = down"],
            ["Posture", "Pose landmarks: shoulder tilt, head height above shoulders",
             "Tilt > 0.06 or head height < 80% of baseline = slouched"],
            ["Hands", "Wrist displacement between frames", "> 0.08 = movement"],
            ["Tab switches", "Browser visibilitychange events", "Warnings at 1 and 2; the 3rd ends the interview"],
        ], [2.6 * cm, 6 * cm, CONTENT_W - 8.6 * cm]),
        P("Calibrating against each candidate's own baseline means camera placement does not bias the results. The "
          "first occurrence of each issue, and every fifth after that, is saved as an evidence thumbnail for the "
          "report. No video is recorded.")]
    s += [P("5.6 Report generation", "h2"), P(
        "Reports are produced with ReportLab's layout engine, which handles tables, wrapping and page breaks, with "
        "Matplotlib charts embedded as images. The interview report contains the headline scores, summary, a "
        "per-question chart, strengths and focus areas, ratings, and a full question-by-question breakdown with the "
        "candidate's answer, rubric scores, feedback and a model answer. The activity report contains the metrics, "
        "observations, tips, a frame breakdown, the tab-switch log and the evidence frames.")]
    s += [P("5.7 Frontend", "h2"), table([
        ["Page", "Purpose"],
        ["Landing (/)", "Hero, statistics, the 'Why Choose Our Platform?' section, founder vlog, testimonials"],
        ["Dashboard", "Performance overview, score trend, interview history with PDF downloads, 'focus next' "
                      "areas, resume checks, local AI status and a configurable backend address"],
        ["Resume upload", "Step 1: upload with honest progress while questions are generated"],
        ["Camera & mic check", "Step 2: live preview, microphone level meter, option to continue without devices"],
        ["Interview", "Step 3: question panel, voice / text / code answers, live Face-Gaze-Posture indicators, "
                      "question navigator, tab-switch counter"],
        ["Results", "Step 4: grading progress, then the full report with downloads"],
        ["ATS Checker", "Upload plus optional job description; scores, fixes, rewrites, keywords, parsed data"],
    ], [3.6 * cm, CONTENT_W - 3.6 * cm]),
        P("Accounts were removed in version 2. Each browser receives an anonymous UUID that keys its history on the "
          "backend, so the dashboard still shows past interviews without any sign-in. The theme defaults to dark mode, "
          "and a render error on any page shows a recovery screen instead of a blank page.")]
    return s


def ch_model():
    s = chapter(6, "Model Selection and Fine-tuning")
    s += [P("6.1 Hardware constraints", "h2"), P(
        "Development and testing were done on a Windows 11 laptop with <b>7.4 GB of usable RAM</b> and integrated "
        "AMD Radeon graphics (no CUDA). All inference therefore runs on the CPU, and the model must share memory "
        "with Whisper and MediaPipe. This rules out models much larger than 4 billion parameters.")]
    s += [P("6.2 Benchmark", "h2"), P(
        "The three instruction-tuned models already installed in Ollama were compared on the same real task: grading "
        "a candidate's explanation of processes versus threads and returning JSON feedback. The answer mentioned "
        "synchronisation, which made it possible to check whether each model read the answer carefully."),
        table([
            ["Model", "Size (Q4)", "Cold run", "Speed", "Observation"],
            ["qwen3:4b (chosen)", "2.5 GB", "109.9 s", "5.5 tok/s", "Most detailed critique; valid JSON"],
            ["phi4-mini", "2.5 GB", "87.8 s", "6.3 tok/s", "Similar depth; claimed synchronisation was missing"],
            ["llama3.2:3b", "2.0 GB", "29.2 s", "7.9 tok/s", "Fastest; shallow, generic feedback"],
        ], [3.3 * cm, 1.9 * cm, 2 * cm, 2.1 * cm, CONTENT_W - 9.3 * cm]),
        Spacer(1, 6), fig(f"{FIG}/benchmark.png", caption="Figure 6.1: Generation speed and feedback detail on CPU"),
        P("Qwen3-4B was chosen for its grading quality, reliable structured output, Apache-2.0 licence and strong "
          "fine-tuning support. Speed matters less than it appears because grading runs in the background. The model "
          "is configurable, so llama3.2:3b can be used where speed matters more.")]
    s += [P("6.3 Prompt engineering: making a small model reliable", "h2"), P(
        "The first end-to-end test exposed a failure specific to small models. When the prompt described each JSON "
        "field in the form <font name='Courier'>detailed_feedback: 2-3 sentences</font>, Qwen3-4B returned a template: "
        "every rubric score was 0, and fields contained the instruction text itself ('2-3 sentences', 'max 3')."),
        table([
            ["Change", "Effect"],
            ["Few-shot example: a complete graded answer to a different question in the system prompt",
             "The model imitates real values instead of copying field descriptions"],
            ["'analysis' field placed first in the schema", "Brief reasoning before scoring improves the scores"],
            ["Length limits written as prose, not 'field: spec'", "No more instruction text echoed into output"],
            ["Empty-template detector with retry at a higher temperature", "Catches the rare remaining failures"],
            ["Estimated fallback grade if the model is unreachable", "The interview always completes"],
        ], [8.3 * cm, CONTENT_W - 8.3 * cm]), Spacer(1, 6),
        P("After the fix, the same model graded an off-topic answer (an explanation of overfitting given to a question "
          "about non-stationary time series) at <b>33/100</b> with the reason 'the candidate talks about overfitting "
          "rather than non-stationarity', and a strong on-topic answer at <b>83/100</b>. Previously both scored 0.")]
    s += [P("6.4 Measured latency (CPU only)", "h2"), table([
        ["Operation", "Typical time", "Where it runs"],
        ["Generate 5 questions", "60 - 95 s", "During upload, with staged progress in the UI"],
        ["Grade one answer (few-shot)", "55 - 75 s", "Background queue while the candidate continues"],
        ["Final assessment", "17 - 48 s", "After the last answer is graded"],
        ["ATS scoring (rule-based)", "< 1 s", "Instant; 'Quick check' uses only this"],
        ["ATS summary + rewrites (LLM)", "~ 2.5 min", "Optional"],
        ["Webcam frame analysis", "~ 0.1 - 0.2 s", "Per frame, every 2.5 s"],
    ], [5.2 * cm, 3 * cm, CONTENT_W - 8.2 * cm])]
    s += [P("6.5 Fine-tuning pipeline", "h2"), P(
        "Every successful model call is appended to <font name='Courier'>data/finetune/interactions.jsonl</font> as a "
        "system, user and assistant exchange. This turns normal use into a dataset that can be reviewed and used to "
        "specialise the model for grading.")]
    s += bullets([
        "<b>prepare_dataset.py</b> filters unusable records (empty evaluations, copied examples), removes duplicates "
        "and writes a review file in which each example can be corrected or marked keep = false.",
        "A second run writes train and validation splits in chat format.",
        "<b>train_qlora.py</b> fine-tunes unsloth/Qwen3-4B-Instruct-2507 with 4-bit QLoRA (rank 16, all attention "
        "and MLP projections), training only on the assistant responses. It runs on a free Colab or Kaggle T4 GPU "
        "and exports a Q4_K_M GGUF file.",
        "<b>Modelfile</b> loads the GGUF into Ollama as 'career-mentor'; setting LLM_MODEL=career-mentor switches the "
        "app to it with no code changes.",
    ])
    return s


def ch_trial():
    s = chapter(7, "Trial Run Summary")
    dur = (END - START).total_seconds() / 60
    answered = FA["questions_answered"]
    s += [P(
        f"This chapter documents a complete recorded session with the candidate's own resume, run on "
        f"{START.strftime('%d %B %Y')} on the laptop described in Section 6.1, using {SESSION['model']} for all "
        f"language tasks and Whisper 'small' for transcription. Nothing was sent to a cloud service."),
        stat_row([("Overall score", f"{FA['average_score']:.0f}/100", tone_hex(FA["average_score"])),
                  ("Verdict", FA["final_recommendation"], "#1E293B"),
                  ("Answered", f"{answered}/{FA['questions_total']}", "#1E293B"),
                  ("Session length", f"{dur:.0f} min", "#1E293B")]),
        Spacer(1, 10)]
    s += [P("7.1 Trial setup", "h2"), table([
        ["Item", "Value"],
        ["Candidate", "Shrish (own resume, AI & ML / full-stack profile)"],
        ["Date and time", f"{START.strftime('%d %b %Y, %H:%M')} - {END.strftime('%H:%M')} UTC ({dur:.1f} minutes)"],
        ["Question model", f"{SESSION['model']} via Ollama (questions generated by the LLM: "
                           f"{'yes' if SESSION.get('llm_questions') else 'no'})"],
        ["Skills detected on resume", ", ".join(SESSION["skills"][:22]) + (" ..." if len(SESSION["skills"]) > 22 else "")],
        ["Answer modes used", "Voice (Q1, Q2), code (Q4), skipped (Q3, Q5)"],
        ["Camera monitoring", f"{ACT['frames']} frames over {ACT['duration_min']} minutes; "
                              f"{ACT['tab_switches']} tab switches"],
    ], [4.2 * cm, CONTENT_W - 4.2 * cm])]
    s += [P("7.2 Generated questions", "h2"), P(
        "All five questions referred to the candidate's real work: the <i>Bullseye</i> stock analytics project "
        "(XGBoost/LSTM, Hugging Face) and the <i>Career Mentor</i> project itself (MediaPipe, OpenCV, YOLOv8)."),
        table([["#", "Type", "Topic", "Question"]] + [
            [str(i + 1), q["type"].title(), q["topic"], q["question"]] for i, q in enumerate(Q)
        ], [0.7 * cm, 1.7 * cm, 2.6 * cm, CONTENT_W - 5 * cm])]
    s += [P("7.3 Scores", "h2"), fig(f"{FIG}/trial_scores.png", width=CONTENT_W * 0.86,
                                     caption="Figure 7.1: Score per question (green >= 70, amber >= 45, red < 45)"),
          fig(f"{FIG}/trial_rubric.png", caption="Figure 7.2: Rubric breakdown for the three answered questions")]

    s += [P("7.4 Answer-level feedback", "h2")]
    for i, (q, a, e) in enumerate(zip(Q, AN, EV)):
        text = (a or {}).get("text") or ""
        head = Table([[Paragraph(f"<b>Q{i+1}  |  {escape(q['type'].upper())}  |  {escape(clean(q['topic']))}</b>",
                                 S["cellb"]),
                       Paragraph(f'<para alignment="right"><font name="Helvetica-Bold" size="13" '
                                 f'color="{tone_hex(e["overall_score"])}">{e["overall_score"]}/100</font></para>',
                                 S["cell"])]],
                     colWidths=[CONTENT_W * 0.75, CONTENT_W * 0.25],
                     style=[("LINEABOVE", (0, 0), (-1, 0), 1, NAVY), ("TOPPADDING", (0, 0), (-1, -1), 5),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)])
        block = [head, Pesc(q["question"], "small"), Spacer(1, 4)]
        if not text:
            block.append(P("<i>Skipped by the candidate. Scored 0 by rule, without calling the model.</i>", "small"))
            s.append(KeepTogether(block + [Spacer(1, 8)]))
            continue
        label = "Candidate's code" if q["type"] == "coding" else "Candidate's spoken answer (Whisper transcript)"
        block += [P(f"<b>{label}</b>", "small"),
                  Pesc(text[:900] + ("..." if len(text) > 900 else ""), "mono" if q["type"] == "coding" else "quote"),
                  Spacer(1, 4),
                  P("<b>Rubric:</b> " + ", ".join(f"{k.replace('_', ' ')} {v}/{MAXIMA[k]}"
                                                  for k, v in e["category_scores"].items()), "small"),
                  Spacer(1, 3), Pesc(e.get("detailed_feedback", ""), "body")]
        s.append(KeepTogether(block))
        rows = [["", ""]]
        if e.get("strengths"):
            rows.append(["What worked", "\n".join(f"- {x}" for x in e["strengths"])])
        if e.get("weaknesses"):
            rows.append(["What was missing", "\n".join(f"- {x}" for x in e["weaknesses"])])
        if e.get("improvement_suggestions"):
            rows.append(["To improve", "\n".join(f"- {x}" for x in e["improvement_suggestions"])])
        if e.get("model_answer"):
            rows.append(["A strong answer", e["model_answer"]])
        data = [[Paragraph(f"<b>{escape(k)}</b>", S["small"]), Pesc(v, "cell")] for k, v in rows[1:]]
        t = Table(data, colWidths=[3.2 * cm, CONTENT_W - 3.2 * cm])
        t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
        s += [t, Spacer(1, 12)]

    s += [P("7.5 Final assessment (generated by the LLM)", "h2"),
          stat_row([("Average", f"{FA['average_score']:.0f}", tone_hex(FA["average_score"])),
                    ("Level", FA["technical_level"], "#1E293B"),
                    ("Communication", f"{FA['communication_rating']}/10", "#1E293B"),
                    ("Problem solving", f"{FA['problem_solving_rating']}/10", "#1E293B")]),
          Spacer(1, 8), Pesc(FA["overall_assessment"])]
    two = Table([[[P("<b>Key strengths</b>", "cellb")] + bullets(FA["key_strengths"], "cell"),
                  [P("<b>Development areas</b>", "cellb")] + bullets(FA["development_areas"], "cell")]],
                colWidths=[CONTENT_W / 2] * 2)
    two.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
    s += [two, Spacer(1, 6), callout("Next steps recommended by the model", FA["next_steps"])]

    c = ACT["counts"]
    s += [P("7.6 Activity monitoring", "h2"),
          stat_row([("Eye contact", f"{ACT['eye_contact_pct']}%", tone_hex(ACT["eye_contact_pct"])),
                    ("Upright posture", f"{ACT['posture_pct']}%", tone_hex(ACT["posture_pct"])),
                    ("Face in frame", f"{ACT['face_visible_pct']}%", tone_hex(ACT["face_visible_pct"])),
                    ("Tab switches", str(ACT["tab_switches"]), "#16A34A" if not ACT["tab_switches"] else "#DC2626")]),
          Spacer(1, 8),
          fig(f"{FIG}/trial_activity.png", caption=f"Figure 7.3: Gaze and posture classification of {c['frames']} frames"),
          table([
              ["Measure", "Frames", "Share"],
              ["Looking at the screen", str(c["gaze_center"]), f"{100 * c['gaze_center'] / c['face_frames']:.0f}% of face frames"],
              ["Looking away (left/right)", str(c["gaze_side"]), f"{100 * c['gaze_side'] / c['face_frames']:.0f}%"],
              ["Looking down", str(c["gaze_down"]), f"{100 * c['gaze_down'] / c['face_frames']:.0f}%"],
              ["Face not in frame", str(c["no_face"]), f"{100 * c['no_face'] / c['frames']:.0f}% of all frames"],
              ["Another person in frame", str(c["multiple_faces"]), "0%"],
              ["Slouched or tilted posture", str(c["posture_bad"]), f"{100 * c['posture_bad'] / c['pose_frames']:.0f}% of pose frames"],
              ["Frequent hand movement", str(c["hand_motion"]), f"{100 * c['hand_motion'] / c['frames']:.1f}%"],
          ], [6 * cm, 2.4 * cm, CONTENT_W - 8.4 * cm]), Spacer(1, 6)]
    s += bullets(ACT["observations"] + ACT["tips"])

    ev = evidence_frames()
    if ev:
        s += [P("7.7 Images captured during the interview", "h2"), P(
            f"The monitor saved {len(ev)} evidence frames automatically when it detected an issue: the first "
            "occurrence of each type, then every fifth. These are the exact 320-pixel thumbnails used in the activity "
            "report; no video was recorded. Frame numbers convert to time at one frame every 2.5 seconds.")]
        cell_w = (CONTENT_W - 12) / 3
        rows, row = [], []
        for path, label in ev:
            with PILImage.open(path) as im:
                ratio = im.height / im.width
            row.append([Image(path, width=cell_w, height=cell_w * ratio), P(label, "caption")])
            if len(row) == 3:
                rows.append(row)
                row = []
        if row:
            rows.append(row + [""] * (3 - len(row)))
        grid = Table(rows, colWidths=[cell_w + 4] * 3)
        grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2),
                                  ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
        s += [grid, P("Figure 7.4: Evidence frames captured by the activity monitor during the trial", "caption")]

    d = ATS["details"]
    sec = ATS["sections"]
    s += [P("7.8 Resume check (ATS) trial", "h2"), P(
        "The same resume was checked against a machine-learning engineer job description. Scoring took under a "
        "second; the LLM then wrote the summary, fixes and rewrites."),
        stat_row([("Overall", str(ATS["overallScore"]), tone_hex(ATS["overallScore"])),
                  ("Keywords", str(sec["keywords"]["score"]), tone_hex(sec["keywords"]["score"])),
                  ("Impact", str(sec["experience"]["score"]), tone_hex(sec["experience"]["score"])),
                  ("Structure", str(sec["formatting"]["score"]), tone_hex(sec["formatting"]["score"])),
                  ("Skills", str(sec["skills"]["score"]), tone_hex(sec["skills"]["score"]))]),
        Spacer(1, 8), Pesc(ATS["summary"]),
        table([
            ["Parsed item", "Result"],
            ["Keywords found", f"{len(d['matched_keywords'])}: " + ", ".join(d["matched_keywords"])],
            ["Keywords missing", f"{len(d['missing_keywords'])}: " + ", ".join(d["missing_keywords"])],
            ["Sections found", ", ".join(d["sections_found"])],
            ["Contact", ", ".join(k for k, v in d["contact"].items() if v) + " detected"],
            ["Length", f"{d['metrics']['word_count']} words, {d['metrics']['pages']} page(s)"],
            ["Skills detected", f"{sum(len(v) for v in d['skills_by_category'].values())} across "
                                f"{len(d['skills_by_category'])} categories; "
                                f"{len(d['skills_backed_by_evidence'])} backed by a project"],
        ], [3.6 * cm, CONTENT_W - 3.6 * cm]), P("Priority fixes", "h3")]
    s += [Paragraph(f"<b>{i}.</b> {escape(clean(t))}", S["bullet"]) for i, t in enumerate(ATS["suggestions"][:6], 1)]
    if ATS.get("bullet_rewrites"):
        s += [P("Bullet rewrites (placeholders mark where real numbers go)", "h3")]
        rows = [["Before", "After"]] + [[r["original"], r["improved"]] for r in ATS["bullet_rewrites"]]
        s.append(table(rows, [CONTENT_W / 2] * 2))

    s += [P("7.9 Results as seen in the application", "h2"),
          fig(f"{SHOTS}/interview-results-overview.png", caption="Figure 7.5: Interview results page for the trial"),
          fig(f"{SHOTS}/interview-question-feedback.png", caption="Figure 7.6: Question-level feedback with rubric bars and a model answer"),
          fig(f"{SHOTS}/ats-result-overview.png", caption="Figure 7.7: ATS result for the trial resume"),
          fig(f"{SHOTS}/dashboard.png", caption="Figure 7.8: Dashboard after the trial, with focus areas taken from the report",
              max_h=14 * cm)]

    s += [P("7.10 Observations from the trial", "h2")] + bullets([
        "<b>Personalisation worked.</b> Every question named a project or technology from the resume, including the "
        "Career Mentor project itself.",
        "<b>Grading was specific and fair.</b> Q1 earned 82/100 with the note that it lacked time-series context; the "
        "coding answer earned 65/100 because it ignored empty and single-element lists.",
        "<b>Transcription of technical terms is the weakest link.</b> Whisper heard 'scale_pos_weight' as 'scale pose "
        "weight', 'class weights' as 'glass weights', 'F1 score' as 'F1 school' and 'CLAHE' as 'Clar'. The grader "
        "still understood the intent, but a domain vocabulary prompt or a larger Whisper model would help.",
        "<b>Skipping costs heavily.</b> Two skipped questions pulled an average of 72 across the answered questions "
        "down to 43, which the report explains clearly.",
        "<b>Camera behaviour was good.</b> 72% eye contact with mostly sideways (not downward) glances, 79% upright "
        "posture, the face visible 99% of the time and no tab switches.",
    ])
    return s


def ch_testing():
    s = chapter(8, "Testing and Validation")
    s += [P("8.1 End-to-end backend test", "h2"), P(
        "An automated script drives the Flask application through a full session with the real model: health check, "
        "resume upload and question generation, three text answers plus one code answer with one question left "
        "unanswered, report polling, PDF download, then an ATS check against a job description, the ATS PDF, the "
        "statistics endpoint, and a path-traversal probe."),
        table([
            ["Check", "Result"],
            ["Questions generated by the LLM, referencing resume projects", "Pass (5 questions, 3 theory + 2 coding)"],
            ["Answers queued instantly; background grading", "Pass (about 1 minute per answer on CPU)"],
            ["Unanswered question marked skipped and scored 0", "Pass"],
            ["Final assessment written from the answers, not a template", "Pass after the fix in Section 6.3"],
            ["Interview and ATS PDFs generated and downloadable", "Pass (HTTP 200)"],
            ["Statistics updated for the anonymous user", "Pass"],
            ["User id path traversal (../../etc)", "Rejected (HTTP 404)"],
            ["Monitoring with synthetic frames (no face)", "Pass; reports 'n/a' rather than 0% when there is no data"],
        ], [9 * cm, CONTENT_W - 9 * cm])]
    s += [P("8.2 Grading validity", "h2"), P(
        "The grader was tested with deliberately mismatched answers. Answers written for different questions were "
        "scored 0-35 with explanations that named the mismatch (for example, 'the code is for finding two numbers "
        "that sum to a target, not the maximum product'), while a correct, on-topic answer scored 83. This confirms "
        "the model reads the answer rather than rewarding length.")]

    cal = calibration()
    import figures  # noqa: E402
    figures.calibration_chart([(r[0], r[1]) for r in cal])
    s += [P("8.3 ATS calibration across real resumes", "h2"), P(
        f"The deterministic scorer was run on {len(cal)} distinct resumes uploaded to the platform over time "
        "(results recorded on 22 September 2026) "
        "(anonymised as R1-R" + str(len(cal)) + "). Early runs gave almost every resume 100 for keywords and skills, "
        "so the formulas were recalibrated: keyword coverage without a job description is capped at 85, and skills "
        "now reward evidence in project descriptions. The final spread (below) separates strong, average and weak "
        "resumes, and the same file always receives the same score."),
        fig(f"{FIG}/calibration.png", caption="Figure 8.1: Overall ATS score of each anonymised resume (no job description)"),
        table([["Resume", "Overall score", "Bullet points", "With a number", "Start with a verb"]] + [
            [r[0], str(r[1]), str(r[2]), str(r[3]), str(r[4])] for r in cal
        ], [2.2 * cm] + [(CONTENT_W - 2.2 * cm) / 4] * 4)]
    s += [P("8.4 Frontend checks", "h2")] + bullets([
        "TypeScript type-check and ESLint pass on all application code; production builds succeed from a clean "
        "checkout with <font name='Courier'>npm ci</font>, exactly as on Render.",
        "Automated browser navigation (Playwright driving Microsoft Edge) across header links, the logo, hero "
        "buttons, browser Back and footer links: 8 of 8 steps rendered with no page errors.",
        "Pages were reviewed in light and dark themes and at mobile width.",
    ])
    s += [callout("Case study: the blank-page bug",
                  "After deployment, clicking any link showed a blank page until refresh. Reproducing it in an "
                  "automated browser revealed 'n is not a function' inside React's effect cleanup. Instrumenting the "
                  "unminified bundle identified the ScrollToTop component: its effect returned the value of "
                  "window.scrollTo(), and current Chromium browsers return a Promise from it, which React then tried "
                  "to call as a cleanup function. Changing the effect to a block body fixed it.",
                  PURPLE_TINT, PURPLE)]
    s += [P("8.5 Defects found and fixed during the upgrade", "h2"), table([
        ["Area", "Defect in version 1", "Fix"],
        ["Reports", "NameError crashed report generation when Supabase was not configured", "Reports served locally"],
        ["Assessment", "Final assessment hard-coded ('Promising candidate...') for everyone", "Generated from answers"],
        ["Answers", "Answers appended, so a skip or retry misaligned all later questions", "Stored by question index"],
        ["Security", "User id used directly in a file path (path traversal)", "Validated id format"],
        ["Startup", "Backend blocked on input() asking for a Gemini key", "No keys needed"],
        ["Sessions", "Held only in memory; lost on reload or across 2 gunicorn workers", "Mirrored to disk"],
        ["Monitoring", "Used the server's webcam; fixed 180 s; gaze maths always 'down'", "Browser frames + baseline"],
        ["ATS page", "Ran interview question generation it never used", "Separate 'ats' purpose"],
        ["Code evaluator", "Stripped the word 'json' from model output, corrupting it", "Schema-constrained output"],
        ["Profile popup", "Read camelCase fields that the API returned in snake_case", "Removed with accounts"],
        ["Tab switching", "Listener re-attached on every render", "Attached once, uses refs"],
        ["Deployment", ".gitignore excluded package.json and requirements.txt", "Rewritten .gitignore"],
        ["Windows", "Emoji in log lines could crash requests on cp1252 consoles", "Safe stdout encoding"],
    ], [2.4 * cm, 8.4 * cm, CONTENT_W - 10.8 * cm])]
    return s


def ch_versions():
    s = chapter(9, "Version 1 vs Version 2")
    s += [table([
        ["Area", "Version 1", "Version 2"],
        ["AI model", "Google Gemini API (paid key, rate limits)", "Qwen3-4B on Ollama: local, free, fine-tunable"],
        ["Resume analysis", "First 1,000 characters to the LLM; scores varied per run",
         "Full PDF/DOCX parsing, deterministic scores, job-description matching, safe rewrites"],
        ["Grading", "Frequent JSON parse failures; hard-coded verdict",
         "JSON-schema output, rubric sums, few-shot examples, model answers"],
        ["Waiting", "30-90 s after every answer", "Background queue; no waiting between questions"],
        ["Answer modes", "Voice and code", "Voice, typed text and code"],
        ["Monitoring", "Server webcam, fixed 3 minutes", "Browser frames for the whole interview, calibrated"],
        ["Accounts", "Supabase login (broke when the project paused)", "No sign-up; anonymous local profile"],
        ["Reports", "Basic PDF", "Redesigned interview, activity and ATS reports with evidence frames"],
        ["Frontend", "Separate pages, limited feedback",
         "Dashboard, step-by-step flow, rich results, dark mode, error recovery"],
        ["Hosting", "Frontend and backend on Render", "Static frontend on Render; local or tunnelled backend"],
    ], [2.8 * cm, 6 * cm, CONTENT_W - 8.8 * cm]), Spacer(1, 10)]
    v1 = [p for p in [f"{SHOTS}/v1-results.png", f"{SHOTS}/v1-home.jpg"] if os.path.exists(p)]
    if v1:
        s += [fig(v1[0], width=CONTENT_W * 0.9, caption="Figure 9.1: Version 1 results page (charts only, generic feedback)")]
    s += [fig(f"{SHOTS}/interview-question-list.png", width=CONTENT_W * 0.9,
              caption="Figure 9.2: Version 2 results, with every question, its score and expandable feedback")]
    return s


def ch_limits():
    s = chapter(10, "Limitations and Future Scope")
    s += [P("10.1 Limitations", "h2")] + bullets([
        "<b>CPU latency.</b> On a laptop without a GPU, question generation takes about a minute and each grade about "
        "a minute. The background queue hides most of this, but the results page still waits for the last answers.",
        "<b>Hosting.</b> Free cloud tiers cannot run a 4B model, so the public site hosts only the frontend; the "
        "backend must run on the user's machine or behind a tunnel.",
        "<b>Transcription of jargon.</b> Whisper 'small' mis-hears some technical terms (Section 7.10).",
        "<b>Heuristic gaze.</b> Gaze is estimated from head pose, not eye tracking, so glancing with the eyes alone is "
        "not detected.",
        "<b>Single-user scale.</b> One grading worker and file-based sessions suit personal use, not many concurrent "
        "users.",
        "<b>Small-model judgement.</b> A 4B model occasionally misses nuance that a larger model would catch. "
        "Fine-tuning on reviewed data is the planned mitigation.",
    ])
    s += [P("10.2 Future scope", "h2")] + bullets([
        "Fine-tune a dedicated 'career-mentor' model on reviewed interview data (the pipeline is already in place).",
        "Adaptive follow-up questions based on the candidate's previous answer.",
        "HR and behavioural rounds graded with the STAR method.",
        "Role-specific tracks (frontend, backend, ML, data) and difficulty levels.",
        "A domain vocabulary prompt for Whisper, or a larger model when a GPU is available.",
        "Eye-landmark (iris) gaze estimation for finer eye-contact measurement.",
        "Progress reports across multiple interviews, and optional one-click cloud GPU hosting for the backend.",
    ])
    return s


def ch_conclusion():
    s = chapter(11, "Conclusion")
    s += [P(
        "Career Mentor v2 shows that a complete, credible mock interview experience can be delivered with open-source "
        "models on an ordinary laptop. The platform reads a resume, asks questions about the candidate's own projects, "
        "accepts spoken, typed and coded answers, grades them against transparent rubrics with model answers, monitors "
        "on-camera behaviour and produces two detailed reports. It does all of this without paid APIs, user accounts "
        "or sending personal data to third parties."),
        P("The most important engineering lessons were about reliability rather than raw capability. JSON-schema "
          "decoding, few-shot examples, rubric sums and output guards turned a small model that initially returned "
          "empty templates into a grader that tells an off-topic answer (33/100) from a strong one (83/100). "
          "Separating deterministic measurement from LLM-written advice made the resume checker consistent and "
          "trustworthy. Moving slow work into a background queue removed the waiting that made version 1 feel broken."),
        P("The recorded trial confirms the system works end to end: personalised questions, specific feedback, a "
          "coherent final assessment, 305 analysed camera frames with evidence images, and a resume check with "
          "actionable, truthful rewrites. With interaction logging and the QLoRA pipeline already built, the next step "
          "is to turn real usage into a model specialised for interview coaching."),
        Spacer(1, 12),
        callout("Project links", [
            P("<b>Live demo:</b> <link href='https://career-mentor-6ctn.onrender.com' color='#F46A3D'>"
              "https://career-mentor-6ctn.onrender.com</link>", "cell"),
            P("<b>Source code:</b> <link href='https://github.com/Shrishkd/CareerMentorV2' color='#F46A3D'>"
              "https://github.com/Shrishkd/CareerMentorV2</link>", "cell"),
        ])]
    return s


def references():
    s = chapter(0, "References", kicker="REFERENCES")
    refs = [
        "Qwen Team. <i>Qwen3 Technical Report.</i> arXiv:2505.09388, 2025.",
        "A. Radford, J. W. Kim, T. Xu, G. Brockman, C. McLeavey, I. Sutskever. <i>Robust Speech Recognition via "
        "Large-Scale Weak Supervision</i> (Whisper). arXiv:2212.04356, 2022.",
        "C. Lugaresi et al. <i>MediaPipe: A Framework for Building Perception Pipelines.</i> arXiv:1906.08172, 2019.",
        "E. J. Hu et al. <i>LoRA: Low-Rank Adaptation of Large Language Models.</i> arXiv:2106.09685, 2021.",
        "T. Dettmers, A. Pagnoni, A. Holtzman, L. Zettlemoyer. <i>QLoRA: Efficient Finetuning of Quantized LLMs.</i> "
        "arXiv:2305.14314, 2023.",
        "Ollama documentation, structured outputs. https://ollama.com",
        "Unsloth: fast LLM fine-tuning. https://github.com/unslothai/unsloth",
        "React documentation. https://react.dev",
        "Flask documentation. https://flask.palletsprojects.com",
        "PyMuPDF documentation. https://pymupdf.readthedocs.io",
        "ReportLab user guide. https://docs.reportlab.com",
        "MediaPipe solutions guide. https://ai.google.dev/edge/mediapipe",
    ]
    s += [Paragraph(f"[{i}]&nbsp;&nbsp;{clean(r)}", ParagraphStyle(f"ref{i}", parent=S["body"], leftIndent=22,
                                                                   firstLineIndent=-22, alignment=0))
          for i, r in enumerate(refs, 1)]
    return s


def appendix():
    s = chapter(0, "Appendix A: User Interface", kicker="APPENDIX")
    for path, cap in [
        (f"{SHOTS}/landing-hero.jpg", "A.1 Landing page hero"),
        (f"{SHOTS}/landing-why-choose.png", "A.2 'Why Choose Our Platform?' section"),
        (f"{SHOTS}/landing-founder-vlog.png", "A.3 Founder vlog section"),
        (f"{SHOTS}/interview-upload.png", "A.4 Step 1: resume upload"),
        (f"{SHOTS}/interview-device-check.png", "A.5 Step 2: camera and microphone check"),
        (f"{SHOTS}/interview-theory.png", "A.6 Step 3: conceptual question (typed answer mode)"),
        (f"{SHOTS}/interview-coding.png", "A.7 Step 3: coding question in the Monaco editor"),
        (f"{SHOTS}/ats-result-details.png", "A.8 ATS details: rewrites, parsed data, skills by category"),
    ]:
        if os.path.exists(path):
            s.append(fig(path, caption=cap, max_h=11.5 * cm))
    s += chapter(0, "Appendix B: Running the Project", kicker="APPENDIX")
    s += [P("Prerequisites: Python 3.11, Node.js 18+, Ollama, ffmpeg, and at least 8 GB of RAM.")]
    for title, lines in [
        ("1. Pull the model", ["ollama pull qwen3:4b"]),
        ("2. Backend", ["python -m venv .venv", ".venv\\Scripts\\activate      (macOS/Linux: source .venv/bin/activate)",
                        "cd Backend", "pip install -r requirements.txt", "copy .env.example .env",
                        "python backend_api.py        -> http://localhost:8000"]),
        ("3. Frontend", ["cd Frontend", "npm install", "npm run dev                   -> http://localhost:8080"]),
    ]:
        s += [P(title, "h3"), Pesc("\n".join(lines), "mono")]
    s += [P("Configuration", "h3"), table([
        ["Variable", "Default", "Meaning"],
        ["LLM_MODEL", "qwen3:4b", "Any Ollama model, e.g. a fine-tuned 'career-mentor'"],
        ["OLLAMA_HOST", "http://127.0.0.1:11434", "Where Ollama runs"],
        ["LLM_TIMEOUT", "300", "Seconds per model call"],
        ["WHISPER_MODEL", "small", "tiny / base / small / medium"],
        ["LLM_LOG_INTERACTIONS", "1", "Log exchanges for fine-tuning"],
        ["VITE_API_URL (frontend)", "(empty)", "Backend URL; also settable from the Dashboard"],
    ], [4.2 * cm, 4.2 * cm, CONTENT_W - 8.4 * cm])]
    return s


def build():
    doc = ReportDoc(OUT)
    story = [Spacer(1, 1)]
    story += front_matter()
    for part in (ch_introduction, ch_motivation, ch_existing, ch_design, ch_implementation, ch_model, ch_trial,
                 ch_testing, ch_versions, ch_limits, ch_conclusion, references, appendix):
        story += part()
    doc.multiBuild(story)
    print("wrote", OUT, os.path.getsize(OUT) // 1024, "KB")


if __name__ == "__main__":
    sys.path.insert(0, HERE)
    build()
