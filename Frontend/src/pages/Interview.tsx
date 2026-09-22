import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Editor from "@monaco-editor/react";
import { Check, Keyboard, Mic, Play, Square, Volume2, VolumeX } from "lucide-react";
import Header from "@/components/Header";
import { Spinner } from "@/components/bits";
import { Button } from "@/components/ui/button";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "@/hooks/use-toast";
import { useTheme } from "@/components/ThemeContext";
import { api, type InterviewSession } from "@/lib/api";
import { clearInterview, loadInterview } from "@/lib/profile";
import { cn } from "@/lib/utils";

type StoredSession = InterviewSession & { devices?: { camera: boolean; mic: boolean } };
type Live = { face?: string; gaze?: string; posture?: string };

const FRAME_INTERVAL_MS = 2500;
const MAX_TAB_SWITCHES = 3;
const JUDGE0_KEY = import.meta.env.VITE_RAPIDAPI_KEY as string | undefined;

const LANGS = {
  python: { label: "Python", judge0: 71, starter: "def solve():\n    # Write your solution here\n    pass\n" },
  cpp: { label: "C++", judge0: 54, starter: "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    // Write your solution here\n    return 0;\n}\n" },
  java: { label: "Java", judge0: 62, starter: "public class Main {\n    public static void main(String[] args) {\n        // Write your solution here\n    }\n}\n" },
  javascript: { label: "JavaScript", judge0: 63, starter: "function solve() {\n  // Write your solution here\n}\n" },
} as const;
type Lang = keyof typeof LANGS;

function fmt(sec: number) {
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
}

export default function Interview() {
  const navigate = useNavigate();
  const { isDark } = useTheme();
  const [session] = useState<StoredSession | null>(() => loadInterview<StoredSession>());
  const questions = session?.questions ?? [];

  const [index, setIndex] = useState(0);
  const [submitted, setSubmitted] = useState<boolean[]>(() => questions.map(() => false));
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"voice" | "text">(session?.devices?.mic ? "voice" : "text");
  const [typed, setTyped] = useState("");
  const [code, setCode] = useState<Record<number, string>>({});
  const [lang, setLang] = useState<Lang>("python");
  const [runOutput, setRunOutput] = useState<string | null>(null);
  const [recording, setRecording] = useState(false);
  const [recordSec, setRecordSec] = useState(0);
  const [questionSec, setQuestionSec] = useState(0);
  const [speak, setSpeak] = useState(true);
  const [live, setLive] = useState<Live>({});
  const [tabSwitches, setTabSwitches] = useState(0);
  const [confirmFinish, setConfirmFinish] = useState(false);
  const [confirmExit, setConfirmExit] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const camStream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const finishing = useRef(false);

  const q = questions[index];
  const isCoding = q?.type === "coding";

  useEffect(() => {
    if (!session) navigate("/resume-upload", { replace: true });
  }, [session, navigate]);

  // ---- Camera preview + frame upload for activity monitoring --------------
  useEffect(() => {
    if (!session?.devices?.camera) return;
    let timer: ReturnType<typeof setInterval> | undefined;
    let stopped = false;
    navigator.mediaDevices
      .getUserMedia({ video: { width: 640, height: 480 } })
      .then((stream) => {
        if (stopped) return stream.getTracks().forEach((t) => t.stop());
        camStream.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
        timer = setInterval(() => {
          const v = videoRef.current;
          const c = canvasRef.current;
          if (!v || !c || v.readyState < 2 || document.hidden) return;
          c.width = 480;
          c.height = Math.round((480 * v.videoHeight) / v.videoWidth) || 360;
          c.getContext("2d")?.drawImage(v, 0, 0, c.width, c.height);
          c.toBlob(
            async (blob) => {
              if (!blob || finishing.current) return;
              const form = new FormData();
              form.append("session_id", session.session_id);
              form.append("frame", blob, "frame.jpg");
              try {
                setLive(await api.form<Live>("/api/monitor-frame", form));
              } catch (e) {
                // Monitoring is optional; stop trying if the server can't analyse frames.
                if ((e as { status?: number }).status === 503) clearInterval(timer);
              }
            },
            "image/jpeg",
            0.7,
          );
        }, FRAME_INTERVAL_MS);
      })
      .catch(() => toast({ title: "Camera unavailable", description: "Continuing without activity monitoring." }));
    return () => {
      stopped = true;
      clearInterval(timer);
      camStream.current?.getTracks().forEach((t) => t.stop());
    };
  }, [session]);

  // ---- Timers ---------------------------------------------------------------
  useEffect(() => {
    setQuestionSec(0);
    const t = setInterval(() => setQuestionSec((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [index]);

  useEffect(() => {
    if (!recording) return;
    setRecordSec(0);
    const t = setInterval(() => setRecordSec((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [recording]);

  // ---- Read the question aloud --------------------------------------------
  useEffect(() => {
    if (!q || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    if (speak) {
      const u = new SpeechSynthesisUtterance(q.question);
      u.lang = "en-US";
      u.rate = 1;
      window.speechSynthesis.speak(u);
    }
    setTyped("");
    setRunOutput(null);
    return () => window.speechSynthesis.cancel();
  }, [q, speak]);

  // ---- Finish ---------------------------------------------------------------
  const finish = useCallback(() => {
    if (!session || finishing.current) return;
    finishing.current = true;
    if (recorder.current?.state === "recording") recorder.current.stop();
    camStream.current?.getTracks().forEach((t) => t.stop());
    window.speechSynthesis?.cancel();
    clearInterview();
    localStorage.setItem("cm_last_session", session.session_id); // lets /results survive a refresh
    navigate("/results", { state: { sessionId: session.session_id }, replace: true });
  }, [session, navigate]);

  const finishRef = useRef(finish);
  finishRef.current = finish;

  // ---- Tab switch detection (listener attached once) -----------------------
  useEffect(() => {
    if (!session) return;
    const onVisibility = () => {
      if (!document.hidden || finishing.current) return;
      api.post("/api/monitor-event", { session_id: session.session_id, type: "tab_hidden" }).catch(() => {});
      setTabSwitches((n) => {
        const next = n + 1;
        if (next >= MAX_TAB_SWITCHES) {
          toast({ title: "Interview ended", description: "You left the tab three times.", variant: "destructive" });
          setTimeout(() => finishRef.current(), 0);
        } else {
          toast({
            title: `Tab switch ${next} of ${MAX_TAB_SWITCHES - 1} allowed`,
            description: next === MAX_TAB_SWITCHES - 1 ? "One more switch will end the interview." : "Stay on this tab during the interview.",
            variant: "destructive",
          });
        }
        return next;
      });
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [session]);

  // Warn before closing the tab mid-interview.
  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!finishing.current) e.preventDefault();
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, []);

  // ---- Submitting -----------------------------------------------------------
  const advance = () => {
    setSubmitted((s) => s.map((v, i) => (i === index ? true : v)));
    const nextOpen = questions.findIndex((_, i) => i > index && !submitted[i]);
    if (nextOpen !== -1) setIndex(nextOpen);
    else if (index < questions.length - 1) setIndex(index + 1);
    else setConfirmFinish(true);
  };

  const submitJSON = async (answer: string, type: "text" | "code") => {
    if (!session) return;
    setBusy(true);
    try {
      await api.post("/api/submit-answer", { session_id: session.session_id, question_index: index, answer, type });
      toast({ title: "Answer saved", description: "It's being graded in the background." });
      advance();
    } catch (e) {
      toast({ title: "Couldn't save your answer", description: (e as Error).message, variant: "destructive" });
    } finally {
      setBusy(false);
    }
  };

  const startRecording = async () => {
    window.speechSynthesis?.cancel();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus"].find((m) => MediaRecorder.isTypeSupported(m));
      const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      const chunks: Blob[] = [];
      const questionIndex = index;
      rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      rec.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        if (finishing.current || !session) return;
        const blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
        if (blob.size < 2000) {
          toast({ title: "Nothing was recorded", description: "Check your microphone and try again.", variant: "destructive" });
          return;
        }
        setBusy(true);
        try {
          const form = new FormData();
          form.append("session_id", session.session_id);
          form.append("question_index", String(questionIndex));
          form.append("audio", blob, `answer.${blob.type.includes("ogg") ? "ogg" : "webm"}`);
          await api.form("/api/submit-answer", form);
          toast({ title: "Answer saved", description: "It's being transcribed and graded in the background." });
          advance();
        } catch (e) {
          toast({ title: "Upload failed", description: (e as Error).message, variant: "destructive" });
        } finally {
          setBusy(false);
        }
      };
      rec.start(1000);
      recorder.current = rec;
      setRecording(true);
    } catch {
      toast({ title: "Microphone blocked", description: "Switching to typed answers.", variant: "destructive" });
      setMode("text");
    }
  };

  const stopRecording = () => recorder.current?.state === "recording" && recorder.current.stop();

  const runCode = async () => {
    if (!JUDGE0_KEY) return;
    setRunOutput("Running…");
    try {
      const res = await fetch("https://judge0-ce.p.rapidapi.com/submissions?base64_encoded=false&wait=true", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com",
          "X-RapidAPI-Key": JUDGE0_KEY,
        },
        body: JSON.stringify({ source_code: code[index] ?? "", language_id: LANGS[lang].judge0 }),
      });
      const out = await res.json();
      if (!res.ok) throw new Error(out.message || `HTTP ${res.status}`);
      setRunOutput(out.compile_output || out.stderr || out.stdout || "(no output)");
    } catch (e) {
      setRunOutput(`Could not run code: ${(e as Error).message}`);
    }
  };

  if (!session || !q) return null;

  const answeredCount = submitted.filter(Boolean).length;
  const currentCode = code[index] ?? LANGS[lang].starter;
  const codeChanged = currentCode.trim() !== LANGS[lang].starter.trim() && currentCode.trim().length > 0;

  return (
    <div className="min-h-screen">
      <Header focus onExit={() => setConfirmExit(true)} />
      <canvas ref={canvasRef} className="hidden" />

      <main className="container grid gap-8 py-8 lg:grid-cols-[1fr_300px]">
        {/* Question + answer */}
        <section className="min-w-0">
          <div className="flex items-center justify-between">
            <p className="eyebrow">
              Question {index + 1} of {questions.length} · {isCoding ? "Coding" : "Conceptual"}
            </p>
            <span className="num text-xs text-muted-foreground">{fmt(questionSec)}</span>
          </div>

          <h1 className="mt-4 text-2xl font-medium leading-snug sm:text-[28px]">{q.question}</h1>
          <div className="mt-3 flex items-center gap-3 text-sm text-muted-foreground">
            <span className="capitalize">{q.topic}</span>
            <span>·</span>
            <button onClick={() => setSpeak((s) => !s)} className="inline-flex items-center gap-1.5 hover:text-foreground">
              {speak ? <Volume2 className="h-3.5 w-3.5" /> : <VolumeX className="h-3.5 w-3.5" />}
              {speak ? "Reading aloud" : "Muted"}
            </button>
            {submitted[index] && (
              <>
                <span>·</span>
                <span className="inline-flex items-center gap-1 text-success">
                  <Check className="h-3.5 w-3.5" /> Submitted, re-answering replaces it
                </span>
              </>
            )}
          </div>

          <div className="mt-8">
            {isCoding ? (
              <div className="overflow-hidden rounded-md border bg-card">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2">
                  <select
                    value={lang}
                    onChange={(e) => setLang(e.target.value as Lang)}
                    className="h-8 rounded border bg-background px-2 text-sm"
                    aria-label="Language"
                  >
                    {Object.entries(LANGS).map(([k, v]) => (
                      <option key={k} value={k}>{v.label}</option>
                    ))}
                  </select>
                  <div className="flex items-center gap-2">
                    {JUDGE0_KEY && (
                      <Button variant="outline" size="sm" onClick={runCode} disabled={!codeChanged}>
                        <Play className="h-3.5 w-3.5" /> Run
                      </Button>
                    )}
                    <Button size="sm" onClick={() => submitJSON(`// ${LANGS[lang].label}\n${currentCode}`, "code")} disabled={!codeChanged || busy}>
                      {busy ? <Spinner /> : null} Submit solution
                    </Button>
                  </div>
                </div>
                <Editor
                  height="380px"
                  language={lang}
                  value={currentCode}
                  onChange={(v) => setCode((c) => ({ ...c, [index]: v ?? "" }))}
                  theme={isDark ? "vs-dark" : "light"}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    fontFamily: "'Geist Mono', ui-monospace, monospace",
                    scrollBeyondLastLine: false,
                    padding: { top: 12 },
                    tabSize: 4,
                  }}
                />
                {runOutput !== null && (
                  <pre className="num max-h-48 overflow-auto border-t bg-muted/50 px-4 py-3 text-xs whitespace-pre-wrap">{runOutput}</pre>
                )}
                <p className="border-t px-3 py-2 text-xs text-muted-foreground">
                  Add a comment explaining your approach and its time complexity. It counts toward the score.
                </p>
              </div>
            ) : mode === "voice" ? (
              <div className="rounded-md border bg-card p-8 text-center">
                {!recording ? (
                  <>
                    <button
                      onClick={startRecording}
                      disabled={busy}
                      className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-foreground text-background transition-transform hover:scale-105 disabled:opacity-50"
                      aria-label="Start recording"
                    >
                      {busy ? <Spinner /> : <Mic className="h-6 w-6" />}
                    </button>
                    <p className="mt-4 text-sm font-medium">{busy ? "Uploading…" : "Record your answer"}</p>
                    <p className="mt-1 text-sm text-muted-foreground">Think for a moment, then speak as you would to an interviewer.</p>
                  </>
                ) : (
                  <>
                    <button
                      onClick={stopRecording}
                      className="relative mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-destructive text-destructive-foreground"
                      aria-label="Stop recording"
                    >
                      <span className="absolute inset-0 animate-ping rounded-full bg-destructive/30" />
                      <Square className="relative h-5 w-5 fill-current" />
                    </button>
                    <p className="num mt-4 text-2xl">{fmt(recordSec)}</p>
                    <p className="mt-1 text-sm text-muted-foreground">Recording. Click stop when you're done.</p>
                  </>
                )}
                <button
                  onClick={() => setMode("text")}
                  disabled={recording}
                  className="mt-6 inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground disabled:opacity-40"
                >
                  <Keyboard className="h-3.5 w-3.5" /> Type instead
                </button>
              </div>
            ) : (
              <div className="rounded-md border bg-card">
                <textarea
                  value={typed}
                  onChange={(e) => setTyped(e.target.value)}
                  rows={9}
                  placeholder="Write your answer as you would say it: what it is, how it works, an example, and the trade-offs."
                  className="w-full resize-y rounded-t-md bg-transparent px-4 py-3 text-[15px] leading-relaxed outline-none"
                />
                <div className="flex items-center justify-between border-t px-3 py-2">
                  <div className="flex items-center gap-3">
                    <span className="num text-xs text-muted-foreground">{typed.trim() ? typed.trim().split(/\s+/).length : 0} words</span>
                    {session.devices?.mic && (
                      <button onClick={() => setMode("voice")} className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground">
                        <Mic className="h-3.5 w-3.5" /> Answer by voice
                      </button>
                    )}
                  </div>
                  <Button size="sm" onClick={() => submitJSON(typed, "text")} disabled={typed.trim().split(/\s+/).length < 3 || busy}>
                    {busy ? <Spinner /> : null} Submit answer
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className="mt-6 flex items-center justify-between">
            <button
              onClick={() => (index < questions.length - 1 ? setIndex(index + 1) : setConfirmFinish(true))}
              disabled={recording || busy}
              className="text-sm text-muted-foreground hover:text-foreground disabled:opacity-40"
            >
              Skip this question
            </button>
            <Button variant="outline" onClick={() => setConfirmFinish(true)} disabled={recording || busy}>
              Finish interview
            </Button>
          </div>
        </section>

        {/* Sidebar */}
        <aside className="space-y-4">
          <div className="overflow-hidden rounded-md border bg-card">
            <div className="relative aspect-[4/3] bg-muted">
              {session.devices?.camera ? (
                <video ref={videoRef} autoPlay playsInline muted className="h-full w-full scale-x-[-1] object-cover" />
              ) : (
                <div className="flex h-full items-center justify-center px-6 text-center text-xs text-muted-foreground">
                  Camera off. The activity report will only include tab switches.
                </div>
              )}
              {recording && (
                <span className="absolute left-2 top-2 inline-flex items-center gap-1.5 rounded bg-black/60 px-2 py-0.5 text-[11px] text-white">
                  <span className="h-1.5 w-1.5 rounded-full bg-red-500" /> REC
                </span>
              )}
            </div>
            {session.devices?.camera && (
              <dl className="grid grid-cols-3 divide-x border-t text-center">
                <LiveCell label="Face" value={live.face === "missing" ? "Not seen" : live.face === "multiple" ? "2+ people" : live.gaze ? "OK" : "…"} bad={!!live.face} />
                <LiveCell label="Gaze" value={live.gaze === "calibrating" ? "Calibrating" : live.gaze === "away" ? "Away" : live.gaze === "down" ? "Down" : live.gaze ? "On screen" : "…"} bad={live.gaze === "away" || live.gaze === "down"} />
                <LiveCell label="Posture" value={live.posture === "slouched" ? "Slouched" : live.posture === "tilted" ? "Tilted" : live.posture === "upright" ? "Upright" : live.posture === "calibrating" ? "Calibrating" : "…"} bad={live.posture === "slouched" || live.posture === "tilted"} />
              </dl>
            )}
          </div>

          <div className="rounded-md border bg-card p-4">
            <div className="flex items-baseline justify-between">
              <p className="text-sm font-medium">Questions</p>
              <p className="num text-xs text-muted-foreground">{answeredCount}/{questions.length} answered</p>
            </div>
            <ol className="mt-3 space-y-1">
              {questions.map((item, i) => (
                <li key={i}>
                  <button
                    onClick={() => !recording && setIndex(i)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded px-2 py-1.5 text-left text-sm transition-colors",
                      i === index ? "bg-muted" : "hover:bg-muted/60",
                    )}
                  >
                    <span
                      className={cn(
                        "num flex h-5 w-5 shrink-0 items-center justify-center rounded-full border text-[10px]",
                        submitted[i] && "border-success bg-success text-success-foreground",
                      )}
                    >
                      {submitted[i] ? <Check className="h-3 w-3" /> : i + 1}
                    </span>
                    <span className="truncate capitalize text-muted-foreground">
                      {item.type === "coding" ? "Coding" : item.topic}
                    </span>
                  </button>
                </li>
              ))}
            </ol>
          </div>

          <p className={cn("px-1 text-xs", tabSwitches ? "text-destructive" : "text-muted-foreground")}>
            Tab switches: <span className="num">{tabSwitches}</span> of {MAX_TAB_SWITCHES - 1} allowed
          </p>
        </aside>
      </main>

      <AlertDialog open={confirmFinish} onOpenChange={setConfirmFinish}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Finish the interview?</AlertDialogTitle>
            <AlertDialogDescription>
              {answeredCount < questions.length
                ? `You've answered ${answeredCount} of ${questions.length} questions. Unanswered questions score zero.`
                : "All questions are answered. Your report will be ready once grading finishes."}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep going</AlertDialogCancel>
            <AlertDialogAction onClick={finish}>See my report</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={confirmExit} onOpenChange={setConfirmExit}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Leave this interview?</AlertDialogTitle>
            <AlertDialogDescription>Your progress won't be saved and no report will be generated.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Stay</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                finishing.current = true;
                camStream.current?.getTracks().forEach((t) => t.stop());
                clearInterview();
                navigate("/dashboard");
              }}
            >
              Leave
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function LiveCell({ label, value, bad }: { label: string; value: string; bad?: boolean }) {
  return (
    <div className="px-2 py-2.5">
      <dt className="eyebrow text-[10px]">{label}</dt>
      <dd className={cn("mt-0.5 text-xs", bad ? "text-warning" : "text-foreground")}>{value}</dd>
    </div>
  );
}

