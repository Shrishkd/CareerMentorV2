import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Check, Download, FileText, Upload, X } from "lucide-react";
import Header, { Footer } from "@/components/Header";
import { Meter, Spinner, Tag, scoreLabel, scoreTone } from "@/components/bits";
import { Button } from "@/components/ui/button";
import { toast } from "@/hooks/use-toast";
import { api, download, type ATSResult } from "@/lib/api";
import { useProfile } from "@/hooks/useProfile";
import { useRefreshStats } from "@/hooks/useUserStats";
import { cn } from "@/lib/utils";

const SECTION_LABELS: Record<keyof ATSResult["sections"], { title: string; hint: string }> = {
  keywords: { title: "Keywords", hint: "Terms screening software searches for" },
  experience: { title: "Impact", hint: "Action verbs and measurable results" },
  formatting: { title: "Structure", hint: "Headings, contact details, length" },
  skills: { title: "Skills", hint: "Coverage and evidence in projects" },
};

export default function ATSChecker() {
  const { profile } = useProfile();
  const refreshStats = useRefreshStats();
  const [file, setFile] = useState<File | null>(null);
  const [jd, setJd] = useState("");
  const [quick, setQuick] = useState(false);
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [result, setResult] = useState<ATSResult | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!loading) return;
    setElapsed(0);
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [loading]);

  const onDrop = useCallback((accepted: File[], rejected: unknown[]) => {
    if (rejected.length) {
      toast({ title: "Unsupported file", description: "Upload a PDF or DOCX under 10 MB.", variant: "destructive" });
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
    disabled: loading,
  });

  const analyze = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const form = new FormData();
      form.append("resume", file);
      form.append("purpose", "ats");
      form.append("user_id", profile.id);
      const up = await api.form<{ session_id: string }>("/api/upload-resume", form);
      setSessionId(up.session_id);
      const res = await api.post<{ ats_result: ATSResult }>("/api/ats-check", {
        session_id: up.session_id,
        job_description: jd,
        use_llm: !quick,
      });
      setResult(res.ats_result);
      refreshStats();
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      toast({ title: "Analysis failed", description: (e as Error).message, variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const downloadReport = async () => {
    if (!sessionId) return;
    setDownloading(true);
    try {
      const r = await api.post<{ report_url: string }>("/api/generate-ats-report", { session_id: sessionId });
      download(r.report_url);
    } catch (e) {
      toast({ title: "Couldn't create the PDF", description: (e as Error).message, variant: "destructive" });
    } finally {
      setDownloading(false);
    }
  };

  const reset = () => {
    setResult(null);
    setSessionId(null);
  };

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="container flex-1 py-10">
        {!result ? (
          <div className="grid gap-12 lg:grid-cols-[1.15fr_0.85fr]">
            <div>
              <p className="eyebrow mb-3">Resume check</p>
              <h1 className="display text-4xl sm:text-5xl">How does your resume read to screening software?</h1>
              <p className="mt-3 max-w-xl text-muted-foreground">
                Upload your resume and, ideally, the job description you're applying to. You'll get a score, the
                keywords you're missing, and rewrites for your weakest bullet points.
              </p>

              <div className="mt-8 space-y-5">
                <div
                  {...getRootProps()}
                  className={cn(
                    "flex cursor-pointer items-center gap-4 rounded-md border border-dashed bg-card px-5 py-6 transition-colors",
                    isDragActive ? "border-foreground bg-muted" : "hover:border-foreground/40",
                    loading && "pointer-events-none opacity-60",
                  )}
                >
                  <input {...getInputProps()} />
                  {file ? <FileText className="h-5 w-5 shrink-0" /> : <Upload className="h-5 w-5 shrink-0 text-muted-foreground" />}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{file ? file.name : "Drop your resume, or click to browse"}</p>
                    <p className="text-xs text-muted-foreground">{file ? `${(file.size / 1024).toFixed(0)} KB` : "PDF or DOCX, up to 10 MB"}</p>
                  </div>
                  {file && !loading && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setFile(null);
                      }}
                      className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                      aria-label="Remove file"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>

                <div>
                  <label htmlFor="jd" className="flex items-baseline justify-between text-sm font-medium">
                    Job description <span className="text-xs font-normal text-muted-foreground">optional, recommended</span>
                  </label>
                  <textarea
                    id="jd"
                    value={jd}
                    onChange={(e) => setJd(e.target.value)}
                    disabled={loading}
                    rows={7}
                    placeholder="Paste the full job posting here to check keyword match…"
                    className="mt-2 w-full resize-y rounded-md border bg-card px-3 py-2.5 text-sm leading-relaxed outline-none focus:ring-2 focus:ring-ring"
                  />
                </div>

                <div className="flex flex-wrap items-center justify-between gap-4 border-t pt-5">
                  <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground">
                    <input type="checkbox" checked={quick} onChange={(e) => setQuick(e.target.checked)} disabled={loading} className="accent-foreground" />
                    Quick check (skip AI-written suggestions)
                  </label>
                  <Button size="lg" onClick={analyze} disabled={!file || loading}>
                    {loading ? <><Spinner /> Analysing · <span className="num">{elapsed}s</span></> : "Analyse resume"}
                  </Button>
                </div>
                {loading && !quick && (
                  <p className="text-xs text-muted-foreground">
                    The local model is writing suggestions and rewrites, which takes one to three minutes. Tick
                    "Quick check" next time for an instant score.
                  </p>
                )}
              </div>
            </div>

            <aside className="rounded-md border bg-card p-6 lg:mt-16">
              <p className="eyebrow">What's checked</p>
              <ul className="mt-4 space-y-4">
                {[
                  ["Parsing", "Whether the text can be read at all, including two-column layouts and icon fonts."],
                  ["Keywords", "Skills and terms from the job description that appear, or don't, in your resume."],
                  ["Impact", "How many bullets start with an action verb and include a measurable result."],
                  ["Structure", "Standard section headings, contact details, LinkedIn and length."],
                  ["Skills", "Recognised skills, grouped by area, and whether your projects back them up."],
                ].map(([t, d]) => (
                  <li key={t} className="text-sm">
                    <p className="font-medium">{t}</p>
                    <p className="mt-0.5 text-muted-foreground">{d}</p>
                  </li>
                ))}
              </ul>
              <p className="mt-6 border-t pt-4 text-xs text-muted-foreground">
                Scoring is rule-based, so the same resume always gets the same score.
              </p>
            </aside>
          </div>
        ) : (
          <Results result={result} onReset={reset} onDownload={downloadReport} downloading={downloading} fileName={file?.name} />
        )}
      </main>
      <Footer />
    </div>
  );
}

function Results({
  result,
  onReset,
  onDownload,
  downloading,
  fileName,
}: {
  result: ATSResult;
  onReset: () => void;
  onDownload: () => void;
  downloading: boolean;
  fileName?: string;
}) {
  const d = result.details;
  const m = d.metrics;
  const contact: [string, boolean][] = [
    ["Email", !!d.contact.email],
    ["Phone", !!d.contact.phone],
    ["LinkedIn", !!d.contact.linkedin],
    ["GitHub", !!d.contact.github],
  ];

  return (
    <div>
      <div className="flex flex-col justify-between gap-6 border-b pb-8 lg:flex-row lg:items-end">
        <div className="flex items-end gap-6">
          <p className={cn("display text-8xl leading-[0.85]", scoreTone(result.overallScore))}>{result.overallScore}</p>
          <div className="pb-1">
            <p className="eyebrow">Resume score · {scoreLabel(result.overallScore)}</p>
            <h1 className="display mt-1 text-3xl">{d.name ?? fileName ?? "Your resume"}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {d.job_description_used ? "Checked against your job description" : "General check, no job description"}
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onReset}>Check another</Button>
          <Button onClick={onDownload} disabled={downloading}>
            {downloading ? <Spinner /> : <Download />} PDF report
          </Button>
        </div>
      </div>

      <p className="mt-8 max-w-3xl text-lg leading-relaxed">{result.summary}</p>

      <div className="mt-8 grid gap-px overflow-hidden rounded-md border bg-border sm:grid-cols-2 lg:grid-cols-4">
        {(Object.keys(SECTION_LABELS) as (keyof ATSResult["sections"])[]).map((k) => {
          const s = result.sections[k];
          return (
            <div key={k} className="bg-card p-5">
              <div className="flex items-baseline justify-between">
                <p className="text-sm font-medium">{SECTION_LABELS[k].title}</p>
                <p className={cn("num text-lg", scoreTone(s.score))}>{s.score}</p>
              </div>
              <Meter value={s.score} className="mt-2" />
              <p className="mt-2 text-xs text-muted-foreground">{SECTION_LABELS[k].hint}</p>
            </div>
          );
        })}
      </div>

      <div className="mt-10 grid gap-10 lg:grid-cols-[1fr_340px]">
        <div className="min-w-0 space-y-10">
          <section>
            <h2 className="display text-2xl">Fix these first</h2>
            <ol className="mt-4 divide-y rounded-md border bg-card">
              {result.suggestions.map((s, i) => (
                <li key={i} className="flex gap-4 px-5 py-3.5 text-sm leading-relaxed">
                  <span className="num pt-px text-xs text-accent">{String(i + 1).padStart(2, "0")}</span>
                  <span>{s}</span>
                </li>
              ))}
            </ol>
          </section>

          {result.bullet_rewrites.length > 0 && (
            <section>
              <h2 className="display text-2xl">Bullet rewrites</h2>
              <p className="mt-1 text-sm text-muted-foreground">Replace anything in [brackets] with your real numbers.</p>
              <div className="mt-4 space-y-3">
                {result.bullet_rewrites.map((r, i) => (
                  <div key={i} className="grid overflow-hidden rounded-md border bg-card md:grid-cols-2">
                    <div className="border-b p-4 md:border-b-0 md:border-r">
                      <p className="eyebrow">Before</p>
                      <p className="mt-2 text-sm text-muted-foreground">{r.original}</p>
                    </div>
                    <div className="p-4">
                      <p className="eyebrow text-accent">After</p>
                      <p className="mt-2 text-sm">{r.improved}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section>
            <h2 className="display text-2xl">Details by area</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {(Object.keys(SECTION_LABELS) as (keyof ATSResult["sections"])[]).map((k) => (
                <div key={k} className="rounded-md border bg-card p-5">
                  <p className="text-sm font-medium">{SECTION_LABELS[k].title}</p>
                  <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
                    {result.sections[k].feedback.map((f) => (
                      <li key={f} className="leading-snug">· {f}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </section>
        </div>

        <aside className="space-y-6">
          {d.job_description_used && (
            <section className="rounded-md border bg-card p-5">
              <h2 className="text-sm font-medium">Keyword match</h2>
              <p className="eyebrow mt-4">Found ({d.matched_keywords.length})</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {d.matched_keywords.length ? d.matched_keywords.map((k) => <Tag key={k} tone="good">{k}</Tag>) : <span className="text-sm text-muted-foreground">None</span>}
              </div>
              <p className="eyebrow mt-5">Missing ({d.missing_keywords.length})</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {d.missing_keywords.length ? d.missing_keywords.map((k) => <Tag key={k} tone="bad">{k}</Tag>) : <span className="text-sm text-muted-foreground">Nothing missing</span>}
              </div>
            </section>
          )}

          <section className="rounded-md border bg-card p-5">
            <h2 className="text-sm font-medium">What the parser saw</h2>
            <ul className="mt-4 grid grid-cols-2 gap-2 text-sm">
              {contact.map(([label, ok]) => (
                <li key={label} className="flex items-center gap-2">
                  {ok ? <Check className="h-3.5 w-3.5 text-success" /> : <X className="h-3.5 w-3.5 text-destructive" />}
                  <span className={ok ? "" : "text-muted-foreground"}>{label}</span>
                </li>
              ))}
            </ul>
            <dl className="mt-5 space-y-2 border-t pt-4 text-sm">
              <Row label="Words" value={`${m.word_count} · ${m.pages} page${m.pages === 1 ? "" : "s"}`} />
              <Row label="Bullet points" value={String(m.bullets)} />
              <Row label="With a number" value={`${m.quantified_bullets} of ${m.bullets}`} />
              <Row label="Start with a verb" value={`${m.action_verb_bullets} of ${m.bullets}`} />
            </dl>
            <div className="mt-5 border-t pt-4">
              <p className="eyebrow">Sections found</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {d.sections_found.map((s) => <Tag key={s}>{s}</Tag>)}
              </div>
              {d.sections_missing.length > 0 && (
                <>
                  <p className="eyebrow mt-4">Not found</p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {d.sections_missing.map((s) => <Tag key={s} tone="bad">{s}</Tag>)}
                  </div>
                </>
              )}
            </div>
          </section>

          {Object.keys(d.skills_by_category).length > 0 && (
            <section className="rounded-md border bg-card p-5">
              <h2 className="text-sm font-medium">Skills detected</h2>
              <div className="mt-4 space-y-4">
                {Object.entries(d.skills_by_category).map(([cat, skills]) => (
                  <div key={cat}>
                    <p className="eyebrow">{cat}</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {skills.map((s) => (
                        <Tag key={s} tone={d.skills_backed_by_evidence.includes(s) ? "good" : "neutral"}>{s}</Tag>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-4 text-xs text-muted-foreground">Green skills are backed by a project or role description.</p>
            </section>
          )}
        </aside>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="num text-right">{value}</dd>
    </div>
  );
}
