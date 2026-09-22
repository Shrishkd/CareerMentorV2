import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDropzone } from "react-dropzone";
import { FileText, Upload, X } from "lucide-react";
import Header from "@/components/Header";
import { FlowSteps, Spinner } from "@/components/bits";
import { Button } from "@/components/ui/button";
import { api, type InterviewSession } from "@/lib/api";
import { saveInterview } from "@/lib/profile";
import { useProfile } from "@/hooks/useProfile";
import { cn } from "@/lib/utils";

const STAGES = [
  "Reading your resume",
  "Finding your projects and skills",
  "Writing questions about your work",
  "Preparing two coding problems",
];

export default function ResumeUpload() {
  const navigate = useNavigate();
  const { profile } = useProfile();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stage, setStage] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  // Question generation on a CPU takes a minute or two; show honest progress.
  useEffect(() => {
    if (!uploading) return;
    setStage(0);
    setElapsed(0);
    const t = setInterval(() => {
      setElapsed((e) => {
        const next = e + 1;
        setStage(next < 3 ? 0 : next < 8 ? 1 : next < 45 ? 2 : 3);
        return next;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [uploading]);

  const onDrop = useCallback((accepted: File[], rejected: unknown[]) => {
    setError(null);
    if (rejected.length) {
      setError("Upload a PDF or Word (.docx) file under 10 MB.");
      return;
    }
    if (accepted[0]) setFile(accepted[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
    disabled: uploading,
  });

  const start = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const form = new FormData();
      form.append("resume", file);
      form.append("purpose", "interview");
      form.append("user_id", profile.id);
      if (profile.name) form.append("name", profile.name);
      const data = await api.form<InterviewSession>("/api/upload-resume", form);
      saveInterview({ ...data, started_at: null });
      navigate("/grant-permissions");
    } catch (e) {
      setError((e as Error).message);
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <Header />
      <main className="container max-w-3xl py-10">
        <FlowSteps current={0} />

        <div className="mt-10">
          <p className="eyebrow mb-3">Step 1</p>
          <h1 className="display text-4xl sm:text-5xl">Upload your resume</h1>
          <p className="mt-3 max-w-xl text-muted-foreground">
            The questions are written from what's on it, so use the version you'd send to a recruiter.
          </p>
        </div>

        {!uploading ? (
          <div className="mt-8">
            <div
              {...getRootProps()}
              className={cn(
                "flex cursor-pointer flex-col items-center justify-center rounded-md border border-dashed bg-card px-6 py-14 text-center transition-colors",
                isDragActive ? "border-foreground bg-muted" : "hover:border-foreground/40",
              )}
            >
              <input {...getInputProps()} />
              <Upload className="h-6 w-6 text-muted-foreground" />
              <p className="mt-4 font-medium">{isDragActive ? "Drop it here" : "Drag your resume here"}</p>
              <p className="mt-1 text-sm text-muted-foreground">
                or <span className="link-underline text-foreground">browse files</span> · PDF or DOCX, up to 10 MB
              </p>
            </div>

            {file && (
              <div className="mt-4 flex items-center justify-between rounded-md border bg-card px-4 py-3">
                <div className="flex min-w-0 items-center gap-3">
                  <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{file.name}</p>
                    <p className="num text-xs text-muted-foreground">{(file.size / 1024).toFixed(0)} KB</p>
                  </div>
                </div>
                <button
                  onClick={() => setFile(null)}
                  className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                  aria-label="Remove file"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            )}

            {error && (
              <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                {error}
              </p>
            )}

            <div className="mt-8 flex items-center justify-between border-t pt-6">
              <p className="max-w-sm text-xs text-muted-foreground">
                Your resume is processed by the local server only. It is never sent to an external AI service.
              </p>
              <Button onClick={start} disabled={!file} size="lg">
                Generate questions
              </Button>
            </div>
          </div>
        ) : (
          <div className="mt-8 rounded-md border bg-card p-8">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">{file?.name}</p>
              <span className="num text-xs text-muted-foreground">
                {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, "0")}
              </span>
            </div>
            <ol className="mt-6 space-y-3">
              {STAGES.map((s, i) => (
                <li key={s} className="flex items-center gap-3 text-sm">
                  {i < stage ? (
                    <span className="h-4 w-4 rounded-full bg-success" />
                  ) : i === stage ? (
                    <Spinner className="text-foreground" />
                  ) : (
                    <span className="h-4 w-4 rounded-full border" />
                  )}
                  <span className={i <= stage ? "text-foreground" : "text-muted-foreground"}>{s}</span>
                </li>
              ))}
            </ol>
            <p className="mt-6 border-t pt-4 text-xs text-muted-foreground">
              The model runs on this computer, so this usually takes one to two minutes. Keep this tab open.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
