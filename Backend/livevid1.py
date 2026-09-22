# livevid1.py (fixed and enhanced)
import os
import cv2
import time
import json
import math
import traceback
import threading
import shutil
from datetime import datetime
from pathlib import Path
from typing import Tuple
from PIL import Image

# ------------------- Dependencies & Setup -------------------
try:
    import mediapipe as mp
    MP_AVAILABLE = True
except Exception as e:
    MP_AVAILABLE = False
    print("⚠️ Mediapipe not available:", e)

# Gemini / Google Generative AI Setup (optional)
GENAI_AVAILABLE = False
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.0")

try:
    import google.generativeai as genai
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        GENAI_AVAILABLE = True
        print("✅ Gemini API configured successfully")
    else:
        print("⚠️ Gemini API key not found — fallback text mode enabled")
except Exception as e:
    print("⚠️ google.generativeai import failed:", e)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader

# ------------------- Directories -------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
REPORT_DIR = PROJECT_ROOT / "reports"
EVIDENCE_DIR = REPORT_DIR / "evidence"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# ------------------- Threshold Constants -------------------
SHOULDER_TILT_THR = 0.06
NECK_SLUMP_DEG_THR = 12
HAND_MOVE_THR = 0.03
GAZE_DOWN_THR = 0.02


# ------------------- Helper Functions -------------------
def new_log(session_id: str):
    return {
        "session_id": session_id,
        "started_at": datetime.utcnow().isoformat(),
        "ended_at": None,
        "eye_contact": {"center": 0, "left": 0, "right": 0, "down": 0, "examples": []},
        "posture": {"correct": 0, "incorrect": 0, "examples": []},
        "hand_movements": {"detected": 0, "examples": []},
        "objects_detected": {"gadgets": [], "examples": []},
        "frames_processed": 0,
        "duration_sec": 0.0
    }


def save_frame_example(frame, tag, frame_id, session_id):
    """Save a small evidence image for the report."""
    fname = f"{session_id}_{tag}_{frame_id}_{int(time.time())}.jpg"
    outp = EVIDENCE_DIR / fname
    try:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        Image.fromarray(rgb).save(outp)
        return str(outp)
    except Exception as e:
        print("⚠️ Failed to save frame example:", e)
        return None


# ------------------- Gemini / AI Summary -------------------
def build_gemini_prompt(log_dict):
    summary = {
        "frames_processed": log_dict.get("frames_processed"),
        "eye_contact": log_dict.get("eye_contact"),
        "posture": log_dict.get("posture"),
        "hand_movements": log_dict.get("hand_movements"),
    }
    prompt = (
        "You are an interview coach. Summarize the candidate’s performance "
        "in three sections: Executive Summary, Observations, and Actionable Tips.\n\n"
        + json.dumps(summary, indent=2)
    )
    return prompt


def get_gemini_report(log_dict):
    """Safely generate AI report or fallback to static text."""
    if not GENAI_AVAILABLE:
        return (
            "Executive summary: The candidate showed a mix of good and improvable behaviours.\n\n"
            "Observations: Eye contact was variable; posture sometimes slouched; hand movements detected.\n\n"
            "Actionable tips: Maintain eye contact, sit upright, and reduce excessive hand gestures."
        )

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        resp = model.generate_content(build_gemini_prompt(log_dict))
        return getattr(resp, "text", "") or "AI summary generated but text missing."
    except Exception as e:
        print("⚠️ Gemini generation failed, using fallback:", e)
        return (
            "Executive summary: The candidate showed a mix of good and improvable behaviours.\n\n"
            "Observations: Eye contact was variable; posture sometimes slouched; hand movements detected.\n\n"
            "Actionable tips: Maintain eye contact, sit upright, and reduce excessive hand gestures."
        )


# ------------------- PDF Report Builder -------------------
def make_pdf_report(pdf_path: str, log_dict: dict, coaching_text: str):
    """Generate a visual report PDF."""
    try:
        W, H = A4
        margin = 2 * cm
        c = canvas.Canvas(pdf_path, pagesize=A4)
        y = H - margin

        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, y, "AI Interview Monitoring Report")
        y -= 30

        c.setFont("Helvetica", 10)
        for line in coaching_text.split("\n"):
            if y < margin + 40:
                c.showPage()
                y = H - margin
            c.drawString(margin, y, line)
            y -= 14

        # Evidence thumbnails
        def add_section(title, paths):
            nonlocal y
            if not paths:
                return
            c.setFont("Helvetica-Bold", 12)
            if y < margin + 80:
                c.showPage()
                y = H - margin
            c.drawString(margin, y, title)
            y -= 16
            cols = 3
            gap = 0.5 * cm
            iw = (W - 2 * margin - (cols - 1) * gap) / cols
            ih = 4 * cm
            x = margin
            for i, p in enumerate(paths):
                try:
                    img = ImageReader(p)
                    w0, h0 = img.getSize()
                    scale = min(iw / w0, ih / h0)
                    fw, fh = w0 * scale, h0 * scale
                    if y - fh < margin:
                        c.showPage()
                        y = H - margin
                    c.drawImage(p, x, y - fh, fw, fh)
                except Exception:
                    pass
                x += iw + gap
                if (i + 1) % cols == 0:
                    x = margin
                    y -= ih + 20
            y -= 16

        add_section("Eye Contact Examples", log_dict["eye_contact"]["examples"])
        add_section("Posture Examples", log_dict["posture"]["examples"])
        add_section("Hand Movement Examples", log_dict["hand_movements"]["examples"])

        c.showPage()
        c.save()
        return True
    except Exception as e:
        print("❌ PDF generation failed:", e)
        traceback.print_exc()
        return False


# ------------------- Frame Processing -------------------
def process_frame(frame, mp_face_mesh, face_mesh, pose, hands, prev_state, frame_id, log, session_id):
    """Analyze one frame."""
    try:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Gaze
        if face_mesh:
            res = face_mesh.process(rgb)
            if res.multi_face_landmarks:
                lm = res.multi_face_landmarks[0]
                nose = lm.landmark[1]
                left_eye = lm.landmark[33]
                right_eye = lm.landmark[263]
                dy = ((left_eye.y + right_eye.y) / 2) - nose.y
                if dy < -GAZE_DOWN_THR:
                    log["eye_contact"]["down"] += 1
                    if frame_id % 10 == 0:
                        p = save_frame_example(frame, "gaze_down", frame_id, session_id)
                        if p:
                            log["eye_contact"]["examples"].append(p)
                else:
                    log["eye_contact"]["center"] += 1

        # Posture
        if pose:
            resp = pose.process(rgb)
            if resp.pose_landmarks:
                pl = resp.pose_landmarks.landmark
                ls, rs = pl[11], pl[12]
                le, re = pl[7], pl[8]
                tilt = abs(ls.y - rs.y)
                mid_ear = ((le.x + re.x) / 2, (le.y + re.y) / 2)
                mid_shoulder = ((ls.x + rs.x) / 2, (ls.y + rs.y) / 2)
                neck_vec = (mid_ear[0] - mid_shoulder[0], mid_ear[1] - mid_shoulder[1])
                neck_angle = math.degrees(math.atan2(neck_vec[1], neck_vec[0]) * -1)
                incorrect = tilt > SHOULDER_TILT_THR or abs(neck_angle) > NECK_SLUMP_DEG_THR
                if incorrect:
                    log["posture"]["incorrect"] += 1
                    if frame_id % 15 == 0:
                        p = save_frame_example(frame, "posture_incorrect", frame_id, session_id)
                        if p:
                            log["posture"]["examples"].append(p)
                else:
                    log["posture"]["correct"] += 1

        # Hand movement
        if hands:
            hr = hands.process(rgb)
            if hr.multi_hand_landmarks:
                cur = hr.multi_hand_landmarks[0].landmark[0]
                hx, hy = cur.x, cur.y
                prev = prev_state.get("hand_pos")
                if prev:
                    dist = math.hypot(hx - prev[0], hy - prev[1])
                    if dist > HAND_MOVE_THR:
                        log["hand_movements"]["detected"] += 1
                        if frame_id % 10 == 0:
                            p = save_frame_example(frame, "hand_move", frame_id, session_id)
                            if p:
                                log["hand_movements"]["examples"].append(p)
                prev_state["hand_pos"] = (hx, hy)

        log["frames_processed"] += 1
    except Exception as e:
        print("⚠️ Frame processing error:", e)
    return prev_state


# ------------------- Main Monitor -------------------
def run_monitor_for_session(session_id: str, duration_sec: int = 180) -> Tuple[dict, str, dict]:
    """Run camera monitoring for duration."""
    if not MP_AVAILABLE:
        raise RuntimeError("Mediapipe not installed or available")

    log = new_log(session_id)
    start_ts = time.time()
    frame_id = 0
    prev_state = {}

    mp_face_mesh = mp.solutions.face_mesh
    mp_pose = mp.solutions.pose
    mp_hands = mp.solutions.hands

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Webcam not accessible")

    try:
        with mp_face_mesh.FaceMesh(refine_landmarks=True, max_num_faces=1) as face_mesh, \
             mp_pose.Pose(model_complexity=1) as pose, \
             mp_hands.Hands(max_num_hands=2) as hands:

            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                frame_id += 1
                prev_state = process_frame(frame, mp_face_mesh, face_mesh, pose, hands, prev_state, frame_id, log, session_id)

                try:
                    cv2.imshow("AI Interview Monitor (press q to stop)", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                except Exception:
                    pass

                if time.time() - start_ts >= duration_sec:
                    break

        cap.release()
        cv2.destroyAllWindows()

        log["ended_at"] = datetime.utcnow().isoformat()
        log["duration_sec"] = int(time.time() - start_ts)

        coaching_text = get_gemini_report(log)

        pdf_name = f"Interview_Report_{session_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        report_path = str(REPORT_DIR / pdf_name)
        make_pdf_report(report_path, log, coaching_text)

        meta = {"storage": "local", "path": report_path, "url": None}
        return log, report_path, meta

    except Exception as e:
        traceback.print_exc()
        cap.release()
        raise


# ------------------- Async Wrapper for Backend -------------------
def start_monitoring_async(session_id: str, duration_sec: int = 180, reports_dir: str = None) -> str:
    """Launch background camera monitor thread and return provisional report path."""
    if reports_dir:
        os.makedirs(reports_dir, exist_ok=True)
        provisional = os.path.join(reports_dir, f"{session_id}_PENDING.pdf")
    else:
        provisional = str(REPORT_DIR / f"{session_id}_PENDING.pdf")

    def worker():
        try:
            log, real_path, meta = run_monitor_for_session(session_id, duration_sec)
            shutil.copy(real_path, provisional)
            print(f"✅ Monitoring finished: {real_path}")
        except Exception as e:
            print(f"❌ Monitoring worker error: {e}")

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return provisional


# ------------------- CLI Test -------------------
if __name__ == "__main__":
    sid = f"localtest_{int(time.time())}"
    log, report, meta = run_monitor_for_session(sid, duration_sec=60)
    print(f"✅ Report generated: {report}")
