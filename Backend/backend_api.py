import json
import os
import queue
import re
import sys
import threading
import uuid
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Windows consoles default to cp1252; never let a log line crash a request.
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(errors="replace")
    except Exception:
        pass

from flask import Flask, jsonify, request, send_file  # noqa: E402
from flask_cors import CORS  # noqa: E402
from werkzeug.utils import secure_filename  # noqa: E402

import interview_engine  # noqa: E402
import llm  # noqa: E402
import monitoring  # noqa: E402
import reports  # noqa: E402
import resume_analyzer  # noqa: E402
import speech  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, os.pardir))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
SESSION_DIR = os.path.join(DATA_DIR, "sessions")
STATS_DIR = DATA_DIR
for d in (UPLOAD_DIR, SESSION_DIR):
    os.makedirs(d, exist_ok=True)

ALLOWED_RESUME = {".pdf", ".docx"}
USER_ID_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024
# allow_private_network lets a hosted frontend (e.g. on Render) call a backend on your own PC.
CORS(app, resources={r"/api/*": {"origins": os.getenv("FRONTEND_ORIGIN", "*")}}, allow_private_network=True)


# ---------------------------------------------------------------------------
# Session store: in memory, mirrored to disk so restarts and multiple workers
# don't lose interviews.
# ---------------------------------------------------------------------------

class SessionStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._cache = {}

    def _path(self, sid):
        return os.path.join(SESSION_DIR, f"{sid}.json")

    def create(self, data):
        with self._lock:
            self._cache[data["session_id"]] = data
            self._write(data)
        return data

    def get(self, sid):
        if not sid or not re.fullmatch(r"[0-9a-f-]{36}", str(sid)):
            return None
        with self._lock:
            if sid not in self._cache and os.path.exists(self._path(sid)):
                with open(self._path(sid), encoding="utf-8") as f:
                    self._cache[sid] = json.load(f)
            return self._cache.get(sid)

    def update(self, sid, fn):
        with self._lock:
            s = self.get(sid)
            if s is None:
                return None
            fn(s)
            self._write(s)
            return s

    def _write(self, s):
        tmp = self._path(s["session_id"]) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False)
        os.replace(tmp, self._path(s["session_id"]))


store = SessionStore()


def _error(message, code=400):
    return jsonify({"error": message}), code


def _session_or_404(sid):
    s = store.get(sid)
    if s is None:
        raise LookupError("Interview session not found. It may have expired; please upload your resume again.")
    return s


@app.errorhandler(LookupError)
def _lookup_error(e):
    return _error(str(e), 404)


@app.errorhandler(413)
def _too_large(_):
    return _error("File is too large (max 15 MB).", 413)


# ---------------------------------------------------------------------------
# Background grading queue. One worker keeps the CPU free for the model.
# ---------------------------------------------------------------------------

jobs = queue.Queue()


def _grade_worker():
    while True:
        sid, idx = jobs.get()
        try:
            _grade(sid, idx)
        except Exception as e:
            print(f"[queue] job {sid}:{idx} crashed: {e}")
        finally:
            jobs.task_done()


def _grade(sid, idx):
    s = store.get(sid)
    if s is None:
        return
    item = s["answers"][idx]
    if item is None:
        return
    store.update(sid, lambda s: s["status"].__setitem__(idx, "processing"))

    q = s["questions"][idx]
    text = item.get("text", "")
    if item.get("audio_path"):
        try:
            text = speech.transcribe(item["audio_path"])
        except Exception as e:
            print(f"[queue] transcription failed: {e}")
            text = ""
            item["error"] = str(e)
        finally:
            try:
                os.remove(item["audio_path"])
            except OSError:
                pass

    evaluation = interview_engine.evaluate_answer(q["question"], text, q.get("type", "theory"),
                                                  s.get("resume_text", "")[:600])
    if item.get("error") and not text:
        evaluation["weaknesses"] = [item["error"]]
        evaluation["detailed_feedback"] = item["error"]

    def apply(s):
        s["answers"][idx] = {"text": text, "type": item.get("type"), "error": item.get("error")}
        s["evaluations"][idx] = evaluation
        s["status"][idx] = "done"
    store.update(sid, apply)


threading.Thread(target=_grade_worker, daemon=True).start()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.route("/api/healthz", methods=["GET"])
def health():
    return jsonify({"ok": True, "llm": llm.status(), "speech": speech.status(),
                    "monitoring": monitoring.MP_AVAILABLE, "queue": jobs.qsize()})


# ---------------------------------------------------------------------------
# Resume upload -> session (+ questions for interviews)
# ---------------------------------------------------------------------------

@app.route("/api/upload-resume", methods=["POST"])
def upload_resume():
    f = request.files.get("resume")
    if not f or not f.filename:
        return _error("No file uploaded.")
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ALLOWED_RESUME:
        return _error("Please upload a PDF or DOCX file.")

    purpose = request.form.get("purpose", "interview")
    user_id = request.form.get("user_id") or None
    candidate_name = (request.form.get("name") or "").strip()[:80] or None

    sid = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR, f"{sid}_{secure_filename(f.filename) or 'resume' + ext}")
    f.save(path)

    extracted = resume_analyzer.extract_resume(path)
    if purpose == "interview" and not extracted["extractable"]:
        return _error("We couldn't read any text from this file. It may be a scanned image. "
                      "Export your resume as a text-based PDF and try again.", 422)

    profile = resume_analyzer.parse_resume(extracted["text"], extracted["links"], extracted["pages"])
    session = {
        "session_id": sid,
        "created_at": datetime.utcnow().isoformat(),
        "purpose": purpose,
        "user_id": user_id if user_id and USER_ID_RE.match(user_id) else None,
        "candidate_name": candidate_name or profile.get("name"),
        "resume_path": path,
        "resume_text": extracted["text"],
        "resume_links": extracted["links"],
        "resume_pages": extracted["pages"],
        "resume_extractable": extracted["extractable"],
        "skills": profile["skills_flat"],
        "questions": [],
        "answers": [],
        "evaluations": [],
        "status": [],
        "tab_events": [],
        "model": llm.LLM_MODEL,
    }

    if purpose == "interview":
        questions, generated = interview_engine.generate_questions(extracted["text"], profile)
        n = len(questions)
        session.update({"questions": questions, "answers": [None] * n, "evaluations": [None] * n,
                        "status": ["pending"] * n, "llm_questions": generated})

    store.create(session)
    return jsonify({
        "session_id": sid,
        "questions": session["questions"],
        "question_count": len(session["questions"]),
        "candidate_name": session["candidate_name"],
        "skills": profile["skills_flat"][:20],
        "llm_generated": session.get("llm_questions", False),
    })


# ---------------------------------------------------------------------------
# Answers
# ---------------------------------------------------------------------------

@app.route("/api/submit-answer", methods=["POST"])
def submit_answer():
    """JSON {session_id, question_index, answer, type} or multipart with an `audio` file."""
    if request.is_json:
        data = request.get_json(silent=True) or {}
        audio = None
    else:
        data = request.form
        audio = request.files.get("audio")

    s = _session_or_404(data.get("session_id"))
    try:
        idx = int(data.get("question_index"))
    except (TypeError, ValueError):
        return _error("question_index is required.")
    if not 0 <= idx < len(s["questions"]):
        return _error("Invalid question_index.")
    if s.get("finished"):
        return _error("This interview has already been submitted.", 409)

    if audio is not None:
        ext = os.path.splitext(audio.filename or "")[1].lower() or ".webm"
        audio_path = os.path.join(UPLOAD_DIR, f"{s['session_id']}_q{idx}_{uuid.uuid4().hex[:8]}{ext}")
        audio.save(audio_path)
        item = {"audio_path": audio_path, "type": "voice"}
    else:
        item = {"text": str(data.get("answer") or ""), "type": data.get("type", "text")}

    def apply(s):
        s["answers"][idx] = item
        s["evaluations"][idx] = None
        s["status"][idx] = "queued"
    store.update(s["session_id"], apply)
    jobs.put((s["session_id"], idx))
    return jsonify({"status": "queued", "question_index": idx, "queue_position": jobs.qsize()})


def _progress(s):
    total = len(s["questions"])
    done = sum(1 for st in s["status"] if st in ("done", "skipped"))
    return {"done": done, "total": total, "status": s["status"]}


@app.route("/api/session/<sid>", methods=["GET"])
def session_status(sid):
    s = _session_or_404(sid)
    return jsonify({"session_id": sid, "questions": s["questions"], "finished": bool(s.get("finished")),
                    "report_ready": bool(s.get("report_path")), **_progress(s)})


# ---------------------------------------------------------------------------
# Activity monitoring
# ---------------------------------------------------------------------------

@app.route("/api/monitor-frame", methods=["POST"])
def monitor_frame():
    s = _session_or_404(request.form.get("session_id"))
    frame = request.files.get("frame")
    if frame is None:
        return _error("No frame provided.")
    if s.get("finished"):
        return jsonify({"ignored": True})
    try:
        status = monitoring.get(s["session_id"]).process(frame.read())
        return jsonify(status)
    except RuntimeError as e:
        return _error(str(e), 503)
    except ValueError as e:
        return _error(str(e))


@app.route("/api/monitor-event", methods=["POST"])
def monitor_event():
    data = request.get_json(silent=True) or {}
    s = _session_or_404(data.get("session_id"))
    if data.get("type") == "tab_hidden" and not s.get("finished"):
        stamp = datetime.now().strftime("%H:%M:%S")
        store.update(s["session_id"], lambda s: s["tab_events"].append(f"Left the interview tab at {stamp}"))
    return jsonify({"tab_switches": len(store.get(s["session_id"])["tab_events"])})


# ---------------------------------------------------------------------------
# Finishing and reports
# ---------------------------------------------------------------------------

_building = set()
_building_lock = threading.Lock()


def _finish(sid):
    """Mark unanswered questions as skipped and close monitoring. Idempotent."""
    s = store.get(sid)
    if s.get("finished"):
        return
    summary, evidence = monitoring.finish(sid, s.get("tab_events"))
    activity_path = None
    if summary:
        try:
            activity_path = reports.activity_report(s, summary, evidence)
        except Exception as e:
            print(f"[report] activity report failed: {e}")

    def apply(s):
        for i, a in enumerate(s["answers"]):
            if a is None:
                s["answers"][i] = {"text": "", "type": "skipped"}
                s["evaluations"][i] = interview_engine.empty_evaluation(
                    s["questions"][i].get("type", "theory"), "The question was skipped.")
                s["status"][i] = "skipped"
        s["finished"] = True
        s["finished_at"] = datetime.utcnow().isoformat()
        s["activity_summary"] = summary
        s["activity_report_path"] = activity_path
    store.update(sid, apply)


def _build_report(sid):
    try:
        s = store.get(sid)
        answers = [(a or {}).get("text", "") for a in s["answers"]]
        fa = interview_engine.final_assessment(s["questions"], answers, s["evaluations"], s.get("activity_summary"))
        store.update(sid, lambda s: s.__setitem__("final_assessment", fa))
        s = store.get(sid)
        path = reports.interview_report({**s, "answers": answers})
        store.update(sid, lambda s: s.__setitem__("report_path", path))
        _record_interview(store.get(sid))
    except Exception as e:
        print(f"[report] interview report failed: {e}")
        store.update(sid, lambda s: s.__setitem__("report_error", str(e)))
    finally:
        with _building_lock:
            _building.discard(sid)


@app.route("/api/generate-report", methods=["POST"])
def generate_report():
    """Finish the interview and poll for the report. Returns ready=false until grading is complete."""
    data = request.get_json(silent=True) or {}
    s = _session_or_404(data.get("session_id"))
    sid = s["session_id"]
    _finish(sid)
    s = store.get(sid)
    progress = _progress(s)

    if s.get("report_path") and os.path.exists(s["report_path"]):
        return jsonify({
            "ready": True,
            **progress,
            "questions": s["questions"],
            "answers": [(a or {}).get("text", "") for a in s["answers"]],
            "evaluations": s["evaluations"],
            "final_assessment": s.get("final_assessment"),
            "activity_summary": s.get("activity_summary"),
            "candidate_name": s.get("candidate_name"),
            "report_url": f"/api/report/{sid}/interview",
            "activity_report_url": f"/api/report/{sid}/activity" if s.get("activity_report_path") else None,
        })
    if s.get("report_error"):
        message = s["report_error"]
        store.update(sid, lambda s: s.pop("report_error", None))  # allow a retry on the next poll
        return _error(f"Report generation failed: {message}", 500)

    if progress["done"] < progress["total"]:
        return jsonify({"ready": False, "stage": "grading", **progress})

    with _building_lock:
        if sid not in _building:
            _building.add(sid)
            threading.Thread(target=_build_report, args=(sid,), daemon=True).start()
    return jsonify({"ready": False, "stage": "assessment", **progress})


@app.route("/api/report/<sid>/<kind>", methods=["GET"])
def download_report(sid, kind):
    s = _session_or_404(sid)
    key = {"interview": "report_path", "activity": "activity_report_path", "ats": "ats_report_path"}.get(kind)
    if key is None:
        return _error("Unknown report type.", 404)
    path = s.get(key)
    if not path or not os.path.exists(path):
        return _error("Report not found.", 404)
    return send_file(path, as_attachment=True, download_name=f"career-mentor-{kind}-report.pdf")


# Backwards-compatible download routes.
@app.route("/api/download-report/<sid>", methods=["GET"])
def download_report_legacy(sid):
    return download_report(sid, "interview")


@app.route("/api/download-ats-report/<sid>", methods=["GET"])
def download_ats_legacy(sid):
    return download_report(sid, "ats")


# ---------------------------------------------------------------------------
# ATS
# ---------------------------------------------------------------------------

@app.route("/api/ats-check", methods=["POST"])
def ats_check():
    data = request.get_json(silent=True) or {}
    s = _session_or_404(data.get("session_id"))
    result = resume_analyzer.analyze_resume(
        s.get("resume_text", ""), data.get("job_description", ""), s.get("resume_links"),
        s.get("resume_pages", 1), s.get("resume_extractable", True), use_llm=data.get("use_llm", True),
    )
    store.update(s["session_id"], lambda s: s.__setitem__("ats_result", result))
    _record_ats(store.get(s["session_id"]))
    return jsonify({"ats_result": result})


@app.route("/api/generate-ats-report", methods=["POST"])
def generate_ats_report():
    data = request.get_json(silent=True) or {}
    s = _session_or_404(data.get("session_id"))
    if not s.get("ats_result"):
        return _error("Run the resume analysis first.")
    path = reports.ats_report(s["ats_result"], s["session_id"])
    store.update(s["session_id"], lambda s: s.__setitem__("ats_report_path", path))
    return jsonify({"report_url": f"/api/report/{s['session_id']}/ats"})


# ---------------------------------------------------------------------------
# Local profile stats (no accounts: the browser keeps an anonymous id)
# ---------------------------------------------------------------------------

_stats_lock = threading.Lock()


def _stats_path(user_id):
    return os.path.join(STATS_DIR, f"user_{user_id}_stats.json")


def _load_stats(user_id):
    path = _stats_path(user_id)
    stats = {"user_id": user_id, "interviews": [], "ats_checks": []}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            stats.update(json.load(f))
    if "recent_interviews" in stats and not stats["interviews"]:  # migrate the old format
        stats["interviews"] = [{"session_id": r.get("session_id"), "date": r.get("date"), "score": r.get("score", 0),
                                "questions": r.get("questions", 0)} for r in stats["recent_interviews"]]
    return stats


def _save_stats(stats):
    with open(_stats_path(stats["user_id"]), "w", encoding="utf-8") as f:
        json.dump({"user_id": stats["user_id"], "interviews": stats["interviews"],
                   "ats_checks": stats["ats_checks"]}, f, indent=2)


def _category_averages(evaluations):
    totals = {}
    for e in evaluations:
        for k, v in (e or {}).get("category_scores", {}).items():
            totals.setdefault(k, []).append(v)
    return {k: round(sum(v) / len(v), 1) for k, v in totals.items()}


def _record_interview(s):
    uid = s.get("user_id")
    if not uid:
        return
    fa = s.get("final_assessment") or {}
    entry = {
        "session_id": s["session_id"],
        "date": s.get("finished_at") or datetime.utcnow().isoformat(),
        "score": round(fa.get("average_score", 0)),
        "questions": len(s["questions"]),
        "answered": fa.get("questions_answered", 0),
        "recommendation": fa.get("final_recommendation"),
        "focus_areas": fa.get("development_areas", [])[:3],
        "question_scores": [(e or {}).get("overall_score", 0) for e in s["evaluations"]],
        "topics": [q.get("topic") for q in s["questions"]],
        "eye_contact": (s.get("activity_summary") or {}).get("eye_contact_pct"),
        "tab_switches": len(s.get("tab_events", [])),
        "has_activity_report": bool(s.get("activity_report_path")),
    }
    with _stats_lock:
        stats = _load_stats(uid)
        stats["interviews"] = [i for i in stats["interviews"] if i.get("session_id") != s["session_id"]]
        stats["interviews"].insert(0, entry)
        stats["interviews"] = stats["interviews"][:50]
        _save_stats(stats)


def _record_ats(s):
    uid = s.get("user_id")
    if not uid or not s.get("ats_result"):
        return
    r = s["ats_result"]
    entry = {"session_id": s["session_id"], "date": datetime.utcnow().isoformat(), "score": r["overallScore"],
             "sections": {k: v["score"] for k, v in r["sections"].items()},
             "job_description_used": r["details"]["job_description_used"],
             "file": os.path.basename(s.get("resume_path", "")).split("_", 1)[-1]}
    with _stats_lock:
        stats = _load_stats(uid)
        stats["ats_checks"] = [a for a in stats["ats_checks"] if a.get("session_id") != s["session_id"]]
        stats["ats_checks"].insert(0, entry)
        stats["ats_checks"] = stats["ats_checks"][:50]
        _save_stats(stats)


@app.route("/api/user-stats/<user_id>", methods=["GET"])
def get_user_stats(user_id):
    if not USER_ID_RE.match(user_id):
        return _error("Invalid user id.")
    with _stats_lock:
        stats = _load_stats(user_id)
    interviews = stats["interviews"]
    scores = [i.get("score", 0) for i in interviews]
    return jsonify({
        "user_id": user_id,
        "interviews": interviews,
        "ats_checks": stats["ats_checks"],
        "interviews_completed": len(interviews),
        "average_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "best_score": max(scores) if scores else 0,
        "ats_score": stats["ats_checks"][0]["score"] if stats["ats_checks"] else 0,
    })


if __name__ == "__main__":
    llm.warm_up()
    speech.preload()
    port = int(os.getenv("PORT", "8000"))
    # The reloader would import everything twice and load Whisper twice.
    app.run(host="0.0.0.0", port=port, debug=os.getenv("FLASK_DEBUG") == "1", use_reloader=False, threaded=True)
else:
    # Running under gunicorn.
    llm.warm_up()
    speech.preload()
