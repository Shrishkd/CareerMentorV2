"""Figures for the Career Mentor project report (architecture, workflow, charts)."""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "fig")
os.makedirs(OUT, exist_ok=True)

ORANGE = "#F46A3D"
PURPLE = "#A855F7"
NAVY = "#1E293B"
SLATE = "#475569"
LIGHT = "#F1F5F9"
GREEN = "#16A34A"
AMBER = "#D97706"
RED = "#DC2626"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})


def box(ax, x, y, w, h, title, sub="", color=NAVY, fill=LIGHT):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                linewidth=1.4, edgecolor=color, facecolor=fill))
    ax.text(x + w / 2, y + h / 2 + (0.13 if sub else 0), title, ha="center", va="center",
            fontsize=9.5, fontweight="bold", color=NAVY)
    if sub:
        ax.text(x + w / 2, y + h / 2 - 0.17, sub, ha="center", va="center", fontsize=7.6, color=SLATE)


def arrow(ax, x1, y1, x2, y2, label="", color=SLATE):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.2, shrinkA=2, shrinkB=2))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.1, label, ha="center", fontsize=7, color=SLATE,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none"))


def architecture():
    fig, ax = plt.subplots(figsize=(10, 6.2), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6.2)
    ax.axis("off")

    # zones
    for x, w, title, col in [(0.1, 2.6, "Browser (React + Vite)", ORANGE), (3.0, 4.6, "Flask backend (Python)", PURPLE),
                             (7.9, 2.0, "Local AI", GREEN)]:
        ax.add_patch(FancyBboxPatch((x, 0.15), w, 5.8, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    linewidth=1.2, edgecolor=col, facecolor="white", linestyle=(0, (4, 3))))
        ax.text(x + w / 2, 5.72, title, ha="center", fontsize=10.5, fontweight="bold", color=col)

    box(ax, 0.3, 4.3, 2.2, 0.9, "Pages & UI", "Landing, Dashboard, Interview,\nResults, ATS Checker", ORANGE)
    box(ax, 0.3, 2.9, 2.2, 0.9, "MediaRecorder", "spoken answers (webm)", ORANGE)
    box(ax, 0.3, 1.5, 2.2, 0.9, "Webcam sampler", "1 JPEG frame / 2.5 s", ORANGE)
    box(ax, 0.3, 0.35, 2.2, 0.75, "Local profile", "anonymous id (no login)", ORANGE)

    box(ax, 3.2, 4.4, 2.1, 0.85, "backend_api.py", "REST API + session store", PURPLE)
    box(ax, 5.4, 4.4, 2.0, 0.85, "resume_analyzer.py", "parse + ATS scoring", PURPLE)
    box(ax, 3.2, 3.1, 2.1, 0.85, "Grading queue", "background worker", PURPLE)
    box(ax, 5.4, 3.1, 2.0, 0.85, "interview_engine.py", "questions, rubric, verdict", PURPLE)
    box(ax, 5.4, 1.8, 2.0, 0.85, "speech.py", "Whisper (small)", PURPLE)
    box(ax, 3.2, 1.8, 2.1, 0.85, "monitoring.py", "MediaPipe face/pose/hands", PURPLE)
    box(ax, 3.2, 0.45, 2.1, 0.85, "reports.py", "ReportLab PDFs", PURPLE)
    box(ax, 5.4, 0.45, 2.0, 0.85, "data/ + reports/", "JSON sessions, stats, PDFs", PURPLE)

    box(ax, 8.1, 3.6, 1.6, 1.3, "Ollama", "qwen3:4b\n(JSON-schema output)", GREEN)
    box(ax, 8.1, 1.7, 1.6, 1.2, "Fine-tune logs", "interactions.jsonl\n-> QLoRA", GREEN)

    arrow(ax, 2.5, 4.75, 3.2, 4.8, "HTTP /api")
    arrow(ax, 2.5, 3.35, 3.2, 3.5, "audio")
    arrow(ax, 2.5, 1.95, 3.2, 2.15, "frames")
    arrow(ax, 5.3, 4.8, 5.4, 4.8)
    arrow(ax, 4.25, 4.4, 4.25, 3.95)
    arrow(ax, 5.0, 3.1, 5.9, 2.65, "audio")
    arrow(ax, 4.25, 1.8, 4.25, 1.3, "summary")
    arrow(ax, 6.4, 3.1, 6.4, 2.65)
    arrow(ax, 5.3, 3.5, 5.4, 3.5)
    arrow(ax, 7.4, 3.6, 8.1, 4.1, "prompts")
    arrow(ax, 7.4, 4.8, 8.1, 4.5)
    arrow(ax, 8.9, 3.6, 8.9, 2.9, "log")
    fig.tight_layout()
    fig.savefig(f"{OUT}/architecture.png")
    plt.close(fig)


def workflow():
    fig, ax = plt.subplots(figsize=(10, 2.7), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 2.7)
    ax.axis("off")
    steps = [("1. Upload resume", "PDF/DOCX parsed,\nskills detected"), ("2. Questions", "3 conceptual +\n2 coding (LLM)"),
             ("3. Device check", "camera & mic\npreview"), ("4. Interview", "voice / text / code\n+ live monitoring"),
             ("5. Grading", "Whisper + rubric\n(background)"), ("6. Reports", "assessment +\nactivity PDF")]
    w, gap = 1.45, 0.2
    for i, (t, s) in enumerate(steps):
        x = 0.15 + i * (w + gap)
        col = ORANGE if i % 2 == 0 else PURPLE
        box(ax, x, 0.7, w, 1.3, t, s, col)
        if i < len(steps) - 1:
            arrow(ax, x + w, 1.35, x + w + gap, 1.35)
    ax.text(5, 0.3, "Grading runs in parallel with the interview, so the candidate never waits between questions.",
            ha="center", fontsize=8.5, color=SLATE, style="italic")
    fig.tight_layout()
    fig.savefig(f"{OUT}/workflow.png")
    plt.close(fig)


def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#CBD5E1")
    ax.spines["bottom"].set_color("#CBD5E1")
    ax.tick_params(colors=SLATE)
    ax.grid(axis="y", color="#E2E8F0", linewidth=0.7)
    ax.set_axisbelow(True)


def tone(v):
    return GREEN if v >= 70 else AMBER if v >= 45 else RED


def trial_charts(session):
    evals = session["evaluations"]
    scores = [e["overall_score"] for e in evals]
    labels = [f"Q{i+1}\n{q['type']}" for i, q in enumerate(session["questions"])]
    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=200)
    bars = ax.bar(labels, scores, color=[tone(s) for s in scores], width=0.55)
    for b, s in zip(bars, scores):
        ax.text(b.get_x() + b.get_width() / 2, s + 2, str(s), ha="center", fontsize=9, fontweight="bold")
    ax.axhline(70, ls="--", lw=0.8, color=SLATE)
    ax.text(4.45, 72, "good (70)", fontsize=7.5, color=SLATE, ha="right")
    ax.set_ylim(0, 105)
    ax.set_ylabel("Score / 100")
    _style(ax)
    fig.tight_layout()
    fig.savefig(f"{OUT}/trial_scores.png")
    plt.close(fig)

    # rubric breakdown for the answered questions (as % of category max)
    maxima = {"technical_accuracy": 30, "depth": 25, "clarity": 20, "examples": 15, "relevance": 10,
              "correctness": 40, "efficiency": 20, "code_quality": 15, "edge_cases": 15, "explanation": 10}
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.1), dpi=200)
    for ax, idx in zip(axes, [0, 1, 3]):
        cats = evals[idx]["category_scores"]
        names = [k.replace("_", " ") for k in cats]
        pct = [100 * v / maxima[k] for k, v in cats.items()]
        ax.barh(names, pct, color=[tone(p) for p in pct])
        for y, (p, (k, v)) in enumerate(zip(pct, cats.items())):
            ax.text(p + 2, y, f"{v}/{maxima[k]}", va="center", fontsize=7.5)
        ax.set_xlim(0, 118)
        ax.invert_yaxis()
        ax.set_title(f"Q{idx+1} ({evals[idx]['overall_score']}/100)", fontsize=9.5, color=NAVY)
        ax.tick_params(labelsize=7.5)
        _style(ax)
        ax.grid(axis="x", color="#E2E8F0")
    fig.tight_layout()
    fig.savefig(f"{OUT}/trial_rubric.png")
    plt.close(fig)

    c = session["activity_summary"]["counts"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 3.2), dpi=200)
    parts = [("On screen", c["gaze_center"], GREEN), ("Looking away", c["gaze_side"], AMBER),
             ("Looking down", c["gaze_down"], PURPLE), ("No face", c["no_face"], RED)]
    a1.pie([p[1] for p in parts], colors=[p[2] for p in parts], startangle=90,
           wedgeprops=dict(width=0.42, edgecolor="white"))
    a1.legend([f"{p[0]}: {p[1]}" for p in parts], loc="center left", bbox_to_anchor=(0.95, 0.5), fontsize=8,
              frameon=False)
    a1.set_title("Gaze across 305 frames", fontsize=9.5, color=NAVY)
    parts = [("Upright", c["posture_ok"], GREEN), ("Slouched / tilted", c["posture_bad"], AMBER)]
    a2.pie([p[1] for p in parts], colors=[p[2] for p in parts], startangle=90,
           wedgeprops=dict(width=0.42, edgecolor="white"))
    a2.legend([f"{p[0]}: {p[1]}" for p in parts], loc="center left", bbox_to_anchor=(0.95, 0.5), fontsize=8,
              frameon=False)
    a2.set_title("Posture across 305 frames", fontsize=9.5, color=NAVY)
    fig.tight_layout()
    fig.savefig(f"{OUT}/trial_activity.png")
    plt.close(fig)


def ats_chart(ats):
    s = ats["sections"]
    names = ["Keywords", "Impact", "Structure", "Skills", "Overall"]
    vals = [s["keywords"]["score"], s["experience"]["score"], s["formatting"]["score"], s["skills"]["score"],
            ats["overallScore"]]
    fig, ax = plt.subplots(figsize=(8, 2.8), dpi=200)
    bars = ax.bar(names, vals, color=[tone(v) for v in vals[:-1]] + [NAVY], width=0.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, str(v), ha="center", fontsize=9, fontweight="bold")
    ax.set_ylim(0, 110)
    _style(ax)
    fig.tight_layout()
    fig.savefig(f"{OUT}/ats_scores.png")
    plt.close(fig)


def benchmark_chart():
    models = ["qwen3:4b", "phi4-mini", "llama3.2:3b"]
    tps = [5.5, 6.3, 7.9]
    tokens = [210, 170, 116]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 2.9), dpi=200)
    a1.bar(models, tps, color=[ORANGE, PURPLE, SLATE], width=0.5)
    for i, v in enumerate(tps):
        a1.text(i, v + 0.15, f"{v}", ha="center", fontsize=9)
    a1.set_title("Generation speed on CPU (tokens/s)", fontsize=9.5, color=NAVY)
    a1.set_ylim(0, 9.5)
    _style(a1)
    a2.bar(models, tokens, color=[ORANGE, PURPLE, SLATE], width=0.5)
    for i, v in enumerate(tokens):
        a2.text(i, v + 4, f"{v}", ha="center", fontsize=9)
    a2.set_title("Feedback length for the same answer (tokens)", fontsize=9.5, color=NAVY)
    a2.set_ylim(0, 250)
    _style(a2)
    fig.tight_layout()
    fig.savefig(f"{OUT}/benchmark.png")
    plt.close(fig)


def calibration_chart(rows):
    fig, ax = plt.subplots(figsize=(10, 3.2), dpi=200)
    labels = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    ax.bar(labels, vals, color=[tone(v) for v in vals], width=0.6)
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, str(v), ha="center", fontsize=8)
    ax.set_ylim(0, 100)
    ax.set_ylabel("ATS score")
    _style(ax)
    fig.tight_layout()
    fig.savefig(f"{OUT}/calibration.png")
    plt.close(fig)


if __name__ == "__main__":
    import sys
    root = sys.argv[1]
    sess = json.load(open(f"{root}/data/sessions/c56dbf04-c8da-42f2-abbf-7b0de1de2b6e.json", encoding="utf-8"))
    ats = json.load(open(f"{root}/data/sessions/193ebf83-dabd-432c-90f7-eb3a816229e3.json", encoding="utf-8"))["ats_result"]
    architecture()
    workflow()
    trial_charts(sess)
    ats_chart(ats)
    benchmark_chart()
    print("figures ok")
