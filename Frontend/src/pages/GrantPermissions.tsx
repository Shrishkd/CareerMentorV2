import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Camera, CameraOff, Mic, MicOff } from "lucide-react";
import Header from "@/components/Header";
import { FlowSteps } from "@/components/bits";
import { Button } from "@/components/ui/button";
import { loadInterview, saveInterview } from "@/lib/profile";
import type { InterviewSession } from "@/lib/api";
import { cn } from "@/lib/utils";

type DeviceState = "idle" | "ok" | "denied";

export default function GrantPermissions() {
  const navigate = useNavigate();
  const session = loadInterview<InterviewSession & { devices?: { camera: boolean; mic: boolean } }>();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [camera, setCamera] = useState<DeviceState>("idle");
  const [mic, setMic] = useState<DeviceState>("idle");
  const [level, setLevel] = useState(0);
  const [requesting, setRequesting] = useState(false);

  useEffect(() => {
    if (!session) navigate("/resume-upload", { replace: true });
    return () => streamRef.current?.getTracks().forEach((t) => t.stop());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Microphone level meter so the candidate can confirm the right input is selected.
  useEffect(() => {
    if (mic !== "ok" || !streamRef.current) return;
    const ctx = new AudioContext();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 512;
    ctx.createMediaStreamSource(streamRef.current).connect(analyser);
    const data = new Uint8Array(analyser.fftSize);
    let raf = 0;
    const tick = () => {
      analyser.getByteTimeDomainData(data);
      let sum = 0;
      for (const v of data) sum += ((v - 128) / 128) ** 2;
      setLevel(Math.min(1, Math.sqrt(sum / data.length) * 4));
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => {
      cancelAnimationFrame(raf);
      ctx.close();
    };
  }, [mic]);

  const request = async () => {
    setRequesting(true);
    const tracks: MediaStreamTrack[] = [];
    try {
      const v = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      tracks.push(...v.getVideoTracks());
      setCamera("ok");
    } catch {
      setCamera("denied");
    }
    try {
      const a = await navigator.mediaDevices.getUserMedia({ audio: true });
      tracks.push(...a.getAudioTracks());
      setMic("ok");
    } catch {
      setMic("denied");
    }
    streamRef.current = new MediaStream(tracks);
    if (videoRef.current) videoRef.current.srcObject = streamRef.current;
    setRequesting(false);
  };

  const begin = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    if (session) saveInterview({ ...session, devices: { camera: camera === "ok", mic: mic === "ok" } });
    navigate("/interview");
  };

  if (!session) return null;
  const checked = camera !== "idle" || mic !== "idle";

  return (
    <div className="min-h-screen">
      <Header />
      <main className="container max-w-4xl py-10">
        <FlowSteps current={1} />

        <div className="mt-10 grid gap-10 md:grid-cols-[1fr_1fr]">
          <div>
            <p className="eyebrow mb-3">Step 2</p>
            <h1 className="display text-4xl sm:text-5xl">Check your camera and microphone</h1>
            <p className="mt-3 text-muted-foreground">
              Your microphone records spoken answers. Your camera is used to report on eye contact, posture and focus.
              Video is analysed frame by frame on the server and never recorded.
            </p>

            <ul className="mt-8 divide-y rounded-md border bg-card">
              <DeviceRow
                icon={camera === "denied" ? CameraOff : Camera}
                label="Camera"
                state={camera}
                okText="Working"
                deniedText="Blocked. Allow it from the address bar to get an activity report."
              />
              <DeviceRow
                icon={mic === "denied" ? MicOff : Mic}
                label="Microphone"
                state={mic}
                okText="Working, try speaking"
                deniedText="Blocked. You can still type your answers."
              >
                {mic === "ok" && (
                  <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-muted">
                    <div className="h-full bg-success transition-[width] duration-75" style={{ width: `${level * 100}%` }} />
                  </div>
                )}
              </DeviceRow>
            </ul>

            <div className="mt-6 rounded-md border bg-card p-4 text-sm">
              <p className="font-medium">Before you begin</p>
              <ul className="mt-2 space-y-1.5 text-muted-foreground">
                <li>· Five questions. There is no time limit, but aim for about two minutes per answer.</li>
                <li>· Stay on this tab. Switching tabs is logged, and the third switch ends the interview.</li>
                <li>· Sit facing a light source with your head and shoulders in frame.</li>
              </ul>
            </div>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              {!checked ? (
                <Button size="lg" onClick={request} disabled={requesting}>
                  {requesting ? "Waiting for permission…" : "Allow camera & microphone"}
                </Button>
              ) : (
                <Button size="lg" onClick={begin}>
                  Begin interview
                </Button>
              )}
              {!checked && (
                <button onClick={begin} className="text-sm text-muted-foreground hover:text-foreground">
                  Skip. I'll type my answers
                </button>
              )}
              <Link to="/resume-upload" className="ml-auto text-sm text-muted-foreground hover:text-foreground">
                Use a different resume
              </Link>
            </div>
          </div>

          <div className="relative aspect-[4/3] overflow-hidden rounded-md border bg-muted md:mt-14">
            <video ref={videoRef} autoPlay playsInline muted className="h-full w-full scale-x-[-1] object-cover" />
            {camera !== "ok" && (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center text-muted-foreground">
                <Camera className="h-6 w-6" />
                <p className="mt-3 text-sm">{camera === "denied" ? "Camera unavailable" : "Preview appears here"}</p>
              </div>
            )}
            {camera === "ok" && (
              <div className="pointer-events-none absolute inset-x-[22%] inset-y-[12%] rounded-[45%] border border-dashed border-white/60" aria-hidden />
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function DeviceRow({
  icon: Icon,
  label,
  state,
  okText,
  deniedText,
  children,
}: {
  icon: React.ElementType;
  label: string;
  state: DeviceState;
  okText: string;
  deniedText: string;
  children?: React.ReactNode;
}) {
  return (
    <li className="flex gap-3 px-4 py-3.5">
      <Icon className={cn("mt-0.5 h-4 w-4", state === "denied" ? "text-destructive" : "text-muted-foreground")} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium">{label}</p>
          <span
            className={cn(
              "text-xs",
              state === "ok" && "text-success",
              state === "denied" && "text-destructive",
              state === "idle" && "text-muted-foreground",
            )}
          >
            {state === "ok" ? "Ready" : state === "denied" ? "Blocked" : "Not checked"}
          </span>
        </div>
        {state !== "idle" && (
          <p className="mt-0.5 text-xs text-muted-foreground">{state === "ok" ? okText : deniedText}</p>
        )}
        {children}
      </div>
    </li>
  );
}
