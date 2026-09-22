"""
Activity monitoring from webcam frames sent by the browser.

The interview page posts a JPEG frame every couple of seconds. Each frame is
analysed with MediaPipe for face presence, gaze direction, posture and hand
movement. Head pose is compared against a per-candidate baseline taken from the
first few frames, so camera placement does not skew the results.
"""
import os
import statistics
import threading
import time

import cv2
import numpy as np

try:
    import mediapipe as mp
    MP_AVAILABLE = True
except Exception as e:  # pragma: no cover
    MP_AVAILABLE = False
    print(f"[monitor] mediapipe unavailable: {e}")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, "reports", "evidence")
os.makedirs(EVIDENCE_DIR, exist_ok=True)

BASELINE_FRAMES = 5
YAW_TOLERANCE = 0.12       # nose offset across the face width
PITCH_TOLERANCE = 0.10     # nose offset between eye line and chin
SHOULDER_TILT_MAX = 0.06
SLOUCH_RATIO = 0.80        # head-to-shoulder height vs. baseline
HAND_MOVE_MIN = 0.08
MAX_EVIDENCE_PER_KIND = 3

EVIDENCE_LABELS = {
    "no_face": "Face not visible",
    "multiple_faces": "Another person in frame",
    "gaze_side": "Looking away from screen",
    "gaze_down": "Looking down",
    "posture_bad": "Slouched or tilted posture",
}


class MonitorSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.lock = threading.Lock()
        self.started = time.time()
        self.last_frame = None
        self.counts = {k: 0 for k in ("frames", "face_frames", "pose_frames", "gaze_center", "gaze_side",
                                      "gaze_down", "no_face", "multiple_faces", "posture_ok", "posture_bad",
                                      "hand_motion")}
        self.baseline = {"yaw": [], "pitch": [], "head": []}
        self.prev_hand = None
        self.evidence = []  # (label, path)
        self._evidence_count = {}
        self.tab_events = []
        self._face = self._pose = self._hands = None

    def _models(self):
        if self._face is None:
            self._face = mp.solutions.face_mesh.FaceMesh(max_num_faces=2, refine_landmarks=False,
                                                         min_detection_confidence=0.5)
            self._pose = mp.solutions.pose.Pose(model_complexity=1,  # bundled with the wheel, no download
                                                 min_detection_confidence=0.5)
            self._hands = mp.solutions.hands.Hands(max_num_hands=2, model_complexity=0,
                                                   min_detection_confidence=0.5)
        return self._face, self._pose, self._hands

    def close(self):
        for m in (self._face, self._pose, self._hands):
            try:
                if m:
                    m.close()
            except Exception:
                pass
        self._face = self._pose = self._hands = None

    def _save_evidence(self, kind, frame):
        n = self._evidence_count.get(kind, 0)
        # Keep the first occurrence, then only every 5th, capped per kind.
        if n >= MAX_EVIDENCE_PER_KIND * 5 or n % 5:
            self._evidence_count[kind] = n + 1
            return
        self._evidence_count[kind] = n + 1
        path = os.path.join(EVIDENCE_DIR, f"{self.session_id}_{kind}_{self.counts['frames']}.jpg")
        small = cv2.resize(frame, (320, int(320 * frame.shape[0] / frame.shape[1])))
        cv2.imwrite(path, small, [cv2.IMWRITE_JPEG_QUALITY, 80])
        elapsed = int(time.time() - self.started)
        self.evidence.append((f"{EVIDENCE_LABELS.get(kind, kind)} ({elapsed // 60}:{elapsed % 60:02d})", path))

    def process(self, jpeg_bytes):
        frame = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("could not decode frame")
        with self.lock:
            self.last_frame = time.time()
            self.counts["frames"] += 1
            face_mesh, pose, hands = self._models()
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            status = {}

            faces = face_mesh.process(rgb).multi_face_landmarks or []
            if not faces:
                self.counts["no_face"] += 1
                self._save_evidence("no_face", frame)
                status["face"] = "missing"
            else:
                self.counts["face_frames"] += 1
                if len(faces) > 1:
                    self.counts["multiple_faces"] += 1
                    self._save_evidence("multiple_faces", frame)
                    status["face"] = "multiple"
                status["gaze"] = self._gaze(faces[0].landmark, frame)

            pr = pose.process(rgb)
            if pr.pose_landmarks:
                status["posture"] = self._posture(pr.pose_landmarks.landmark, frame)

            hr = hands.process(rgb)
            if hr.multi_hand_landmarks:
                wrist = hr.multi_hand_landmarks[0].landmark[0]
                if self.prev_hand and np.hypot(wrist.x - self.prev_hand[0], wrist.y - self.prev_hand[1]) > HAND_MOVE_MIN:
                    self.counts["hand_motion"] += 1
                self.prev_hand = (wrist.x, wrist.y)
            else:
                self.prev_hand = None
            return status

    def _gaze(self, lm, frame):
        left, right, nose, chin = lm[234], lm[454], lm[1], lm[152]
        eye_y = (lm[33].y + lm[263].y) / 2
        width = (right.x - left.x) or 1e-6
        height = (chin.y - eye_y) or 1e-6
        yaw = (nose.x - left.x) / width
        pitch = (nose.y - eye_y) / height

        if len(self.baseline["yaw"]) < BASELINE_FRAMES:
            self.baseline["yaw"].append(yaw)
            self.baseline["pitch"].append(pitch)
            self.counts["gaze_center"] += 1
            return "calibrating"

        by = statistics.median(self.baseline["yaw"])
        bp = statistics.median(self.baseline["pitch"])
        if abs(yaw - by) > YAW_TOLERANCE:
            self.counts["gaze_side"] += 1
            self._save_evidence("gaze_side", frame)
            return "away"
        if pitch - bp > PITCH_TOLERANCE:
            self.counts["gaze_down"] += 1
            self._save_evidence("gaze_down", frame)
            return "down"
        self.counts["gaze_center"] += 1
        return "center"

    def _posture(self, pl, frame):
        ls, rs, nose = pl[11], pl[12], pl[0]
        if min(ls.visibility, rs.visibility) < 0.5:
            return "unknown"
        self.counts["pose_frames"] += 1
        shoulder_w = abs(ls.x - rs.x) or 1e-6
        head_height = (((ls.y + rs.y) / 2) - nose.y) / shoulder_w
        tilt = abs(ls.y - rs.y)

        if len(self.baseline["head"]) < BASELINE_FRAMES:
            self.baseline["head"].append(head_height)
            self.counts["posture_ok"] += 1
            return "calibrating"

        slouched = head_height < statistics.median(self.baseline["head"]) * SLOUCH_RATIO
        if slouched or tilt > SHOULDER_TILT_MAX:
            self.counts["posture_bad"] += 1
            self._save_evidence("posture_bad", frame)
            return "slouched" if slouched else "tilted"
        self.counts["posture_ok"] += 1
        return "upright"

    def summary(self):
        c = self.counts
        frames = c["frames"] or 1
        face = c["face_frames"] or 1
        pose_frames = c["pose_frames"] or 1
        # None means "no data" (face or shoulders never seen), which is different from 0%.
        eye = round(100 * c["gaze_center"] / face) if c["face_frames"] else None
        posture = round(100 * c["posture_ok"] / pose_frames) if c["pose_frames"] else None
        visible = round(100 * c["face_frames"] / frames) if c["frames"] else 0
        hand_pct = round(100 * c["hand_motion"] / frames) if c["frames"] else 0
        tabs = len(self.tab_events)

        obs, tips = [], []
        if not c["frames"]:
            obs.append("No camera frames were received, so behaviour could not be analysed.")
            tips.append("Allow camera access and keep the interview tab open so monitoring can run.")
        else:
            if c["face_frames"]:
                obs.append(f"You were looking at the screen in {eye}% of frames where your face was visible.")
            if c["face_frames"] and eye < 70:
                tips.append("Keep your eyes near the camera while answering; place notes out of reach so you are not "
                            "tempted to read.")
            if c["gaze_down"] > c["gaze_side"] and c["gaze_down"] > 2:
                obs.append("Most lapses were downward glances, which often reads as reading notes or a phone.")
            elif c["gaze_side"] > 2:
                obs.append("Most lapses were sideways glances away from the screen.")
            if visible < 90:
                obs.append(f"Your face was out of frame {100 - visible}% of the time.")
                tips.append("Sit centred with your head and shoulders in view, and make sure the room is well lit.")
            if c["multiple_faces"]:
                obs.append(f"Another face appeared in {c['multiple_faces']} frame(s).")
                tips.append("Take interviews alone in a quiet room; a second person on camera can void a real interview.")
            if posture is not None:
                obs.append(f"Posture was upright in {posture}% of frames where your shoulders were visible.")
                if posture < 75:
                    tips.append("Sit back in the chair with shoulders level; raise the laptop so the camera is at eye level.")
            if hand_pct > 25:
                obs.append("Hand movement was frequent. Some gesturing is natural, but constant movement distracts.")
                tips.append("Rest your hands on the desk between points and gesture deliberately to emphasise ideas.")
        if tabs:
            obs.append(f"You left the interview tab {tabs} time(s).")
            tips.append("Close other tabs and notifications before starting; switching tabs is flagged in real "
                        "proctored interviews.")
        if not tips:
            tips.append("Strong on-camera presence. Keep the same setup for real interviews.")

        return {
            "frames": c["frames"],
            "duration_min": round((time.time() - self.started) / 60, 1),
            "eye_contact_pct": eye,
            "posture_pct": posture,
            "face_visible_pct": visible,
            "tab_switches": tabs,
            "tab_events": list(self.tab_events),
            "counts": c,
            "observations": obs,
            "tips": tips,
        }


_sessions = {}
_sessions_lock = threading.Lock()


def get(session_id, create=True):
    with _sessions_lock:
        m = _sessions.get(session_id)
        if m is None and create:
            if not MP_AVAILABLE:
                raise RuntimeError("mediapipe is not installed")
            m = _sessions[session_id] = MonitorSession(session_id)
        return m


def finish(session_id, tab_events=None):
    """Stop monitoring and return (summary, evidence).

    Tab-switch events come from the session record so they are reported even
    when the camera was never enabled.
    """
    with _sessions_lock:
        m = _sessions.pop(session_id, None)
    if m is None:
        if not tab_events:
            return None, []
        m = MonitorSession(session_id)  # models load lazily, so this is cheap
    with m.lock:
        m.tab_events = list(tab_events or [])
        summary = m.summary()
        evidence = list(m.evidence)
        m.close()
    return summary, evidence
