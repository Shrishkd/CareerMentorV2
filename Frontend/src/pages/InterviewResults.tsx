import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Download, RotateCcw } from "lucide-react";
import Header, { Footer } from "@/components/Header";
import { FlowSteps, Meter, Spinner, scoreLabel, scoreTone } from "@/components/bits";
import { Button } from "@/components/ui/button";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { api, download, type ReportResponse } from "@/lib/api";
import { useRefreshStats } from "@/hooks/useUserStats";
import { cn } from "@/lib/utils";

const POLL_MS = 4000;

const STATUS_TEXT: Record<string, string> = {
  pending: "Waiting",
  queued: "In queue",
  processing: "Grading now",
  done: "Graded",
  skipped: "Skipped",
};

export default function InterviewResults() {
  const location = useLocation();
  const sessionId =
    (location.state as { sessionId?: string } | null)?.sessionId ?? localStorage.getItem("cm_last_session");
  const [data, setData] = useState<ReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const refreshStats = useRefreshStats();
  const refreshed = useRef(false);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const res = await api.post<ReportResponse>("/api/generate-report", { session_id: sessionId });
        if (cancelled) return;
        setData(res);
        setError(null);
        if (!res.ready) timer = setTimeout(poll, POLL_MS);
      } catch (e) {
        if (cancelled) return;
        setError((e as Error).message);
        timer = setTimeout(poll, POLL_MS * 2);
      }
    };
    poll();
    const tick = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      clearInterval(tick);
    };
  }, [sessionId]);

  useEffect(() => {
    if (data?.ready && !refreshed.current) {
      refreshed.current = true;
      refreshStats();
    }
  }, [data, refreshStats]);

  if (!sessionId) {
    return (
      <div className="min-h-screen">
        <Header />
        <main className="container max-w-xl py-24 text-center">
          <h1 className="display text-4xl">No interview to show</h1>
          <p className="mt-3 text-muted-foreground">Finish an interview to see its report here, or open past reports from your dashboard.</p>
          <div className="mt-8 flex justify-center gap-3">
            <Button asChild><Link to="/resume-upload">Start an interview</Link></Button>
            <Button asChild variant="outline"><Link to="/dashboard">Dashboard</Link></Button>
          </div>
        </main>
      </div>
    );
  }

  if (!data?.ready) {
    return (
      <div className="min-h-screen">
        <Header />
        <main className="container max-w-2xl py-10">
          <FlowSteps current={3} />
          <div className="mt-10">
            <p className="eyebrow mb-3">Almost there</p>
            <h1 className="display text-4xl sm:text-5xl">
              {data?.stage === "assessment" ? "Writing your assessment" : "Grading your answers"}
            </h1>
            <p className="mt-3 text-muted-foreground">
              Each answer is transcribed and scored by the model running on this computer. This takes about a minute per
              answer. You can leave this page open, or come back later from the dashboard.
            </p>
          </div>

          <div className="mt-8 rounded-md border bg-card">
            <div className="flex items-center justify-between border-b px-5 py-3">
              <p className="text-sm font-medium">
                {data ? `${data.done} of ${data.total} graded` : "Connecting…"}
              </p>
              <span className="num text-xs text-muted-foreground">
                {Math.floor(elapsed / 60)}:{String(elapsed % 60).padStart(2, "0")}
              </span>
            </div>
            {data && <Meter value={(data.done / Math.max(1, data.total)) * 100} className="rounded-none" />}
            <ul className="divide-y">
              {(data?.status ?? []).map((s, i) => (
                <li key={i} className="flex items-center justify-between px-5 py-3 text-sm">
                  <span>Question {i + 1}</span>
                  <span className={cn("inline-flex items-center gap-2 text-xs", s === "done" ? "text-success" : "text-muted-foreground")}>
                    {s === "processing" && <Spinner className="h-3 w-3" />}
                    {STATUS_TEXT[s] ?? s}
                  </span>
                </li>
              ))}
              {data?.stage === "assessment" && (
                <li className="flex items-center justify-between px-5 py-3 text-sm">
                  <span>Final assessment & PDF</span>
                  <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
                    <Spinner className="h-3 w-3" /> Writing
                  </span>
                </li>
              )}
            </ul>
          </div>
          {error && <p className="mt-4 text-sm text-destructive">{error} Retrying…</p>}
        </main>
      </div>
    );
  }

  const fa = data.final_assessment!;
  const questions = data.questions ?? [];
  const evaluations = data.evaluations ?? [];
  const answers = data.answers ?? [];
  const activity = data.activity_summary;
  const score = Math.round(fa.average_score);

  return (
    <div className="min-h-screen">
      <Header />
      <main className="container py-10">
        <div className="flex flex-col justify-between gap-6 border-b pb-8 lg:flex-row lg:items-end">
          <div>
            <p className="eyebrow mb-3">Interview report</p>
            <h1 className="display text-4xl sm:text-5xl">{data.candidate_name ? `${data.candidate_name}'s results` : "Your results"}</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            {data.report_url && (
              <Button variant="outline" onClick={() => download(data.report_url!)}>
                <Download /> Interview report
              </Button>
            )}
            {data.activity_report_url && (
              <Button variant="outline" onClick={() => download(data.activity_report_url!)}>
                <Download /> Activity report
              </Button>
            )}
            <Button asChild>
              <Link to="/resume-upload"><RotateCcw /> Practise again</Link>
            </Button>
          </div>
        </div>

        {/* Headline */}
        <section className="mt-8 grid gap-px overflow-hidden rounded-md border bg-border md:grid-cols-[1.2fr_1fr_1fr_1fr]">
          <div className="bg-card p-6">
            <p className="eyebrow">Overall score</p>
            <p className={cn("display mt-2 text-7xl leading-none", scoreTone(score))}>
              {score}
              <span className="text-2xl text-muted-foreground">/100</span>
            </p>
            <p className="mt-2 text-sm text-muted-foreground">{scoreLabel(score)} · {fa.questions_answered} of {fa.questions_total} answered</p>
          </div>
          <Cell label="Verdict" value={fa.final_recommendation} />
          <Cell label="Communication" value={`${fa.communication_rating}/10`} />
          <Cell label="Problem solving" value={`${fa.problem_solving_rating}/10`} />
        </section>

        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_340px]">
          <div className="min-w-0 space-y-8">
            <section>
              <h2 className="display text-2xl">Summary</h2>
              <p className="mt-3 max-w-3xl leading-relaxed">{fa.overall_assessment}</p>
              <div className="mt-6 grid gap-6 sm:grid-cols-2">
                <ListBlock title="Strengths" items={fa.key_strengths} tone="good" />
                <ListBlock title="Work on" items={fa.development_areas} tone="bad" />
              </div>
              {fa.next_steps && (
                <div className="mt-6 rounded-md border-l-2 border-accent bg-accent-soft/60 px-4 py-3">
                  <p className="eyebrow text-accent">Next step</p>
                  <p className="mt-1 text-sm">{fa.next_steps}</p>
                </div>
              )}
            </section>

            <section>
              <h2 className="display text-2xl">Question by question</h2>
              <Accordion type="multiple" defaultValue={["q0"]} className="mt-4 rounded-md border bg-card">
                {questions.map((q, i) => {
                  const e = evaluations[i];
                  const s = e?.overall_score ?? 0;
                  return (
                    <AccordionItem key={i} value={`q${i}`} className="px-5 last:border-b-0">
                      <AccordionTrigger className="gap-4 py-4 text-left hover:no-underline">
                        <div className="flex min-w-0 flex-1 items-start gap-4">
                          <span className={cn("num w-9 shrink-0 pt-0.5 text-lg", scoreTone(s))}>{s}</span>
                          <div className="min-w-0">
                            <p className="eyebrow">Q{i + 1} · {q.type === "coding" ? "Coding" : q.topic}</p>
                            <p className="mt-1 font-normal leading-snug">{q.question}</p>
                          </div>
                        </div>
                      </AccordionTrigger>
                      <AccordionContent className="pb-6 pl-[52px]">
                        <p className="eyebrow">Your answer</p>
                        {answers[i] ? (
                          q.type === "coding" ? (
                            <pre className="num mt-2 max-h-72 overflow-auto rounded border bg-muted/40 p-3 text-xs">{answers[i]}</pre>
                          ) : (
                            <blockquote className="mt-2 border-l-2 pl-3 text-muted-foreground">{answers[i]}</blockquote>
                          )
                        ) : (
                          <p className="mt-2 text-sm text-muted-foreground">No answer.</p>
                        )}

                        {e && Object.keys(e.category_scores ?? {}).length > 0 && s > 0 && (
                          <dl className="mt-5 grid gap-x-8 gap-y-2.5 sm:grid-cols-2">
                            {Object.entries(e.category_scores).map(([k, v]) => {
                              const max = CATEGORY_MAX[k] ?? 20;
                              return (
                                <div key={k}>
                                  <div className="flex justify-between text-xs">
                                    <dt className="capitalize text-muted-foreground">{k.replace(/_/g, " ")}</dt>
                                    <dd className="num">{v}/{max}</dd>
                                  </div>
                                  <Meter value={(v / max) * 100} className="mt-1" />
                                </div>
                              );
                            })}
                          </dl>
                        )}

                        {e?.detailed_feedback && <p className="mt-5 text-sm leading-relaxed">{e.detailed_feedback}</p>}

                        <div className="mt-5 grid gap-5 sm:grid-cols-2">
                          <ListBlock title="What worked" items={e?.strengths ?? []} tone="good" small />
                          <ListBlock title="What was missing" items={e?.weaknesses ?? []} tone="bad" small />
                        </div>
                        {!!e?.improvement_suggestions?.length && (
                          <div className="mt-5">
                            <ListBlock title="To improve" items={e.improvement_suggestions} small />
                          </div>
                        )}
                        {e?.model_answer && (
                          <div className="mt-5 rounded-md border bg-background p-4">
                            <p className="eyebrow">A strong answer</p>
                            <p className="mt-2 text-sm leading-relaxed">{e.model_answer}</p>
                          </div>
                        )}
                      </AccordionContent>
                    </AccordionItem>
                  );
                })}
              </Accordion>
            </section>
          </div>

          <aside className="space-y-6">
            <section className="rounded-md border bg-card p-5">
              <h2 className="text-sm font-medium">Scores</h2>
              <ul className="mt-4 space-y-3">
                {evaluations.map((e, i) => (
                  <li key={i} className="grid grid-cols-[28px_1fr_28px] items-center gap-3 text-xs">
                    <span className="num text-muted-foreground">Q{i + 1}</span>
                    <Meter value={e?.overall_score ?? 0} />
                    <span className="num text-right">{e?.overall_score ?? 0}</span>
                  </li>
                ))}
              </ul>
            </section>

            <section className="rounded-md border bg-card p-5">
              <h2 className="text-sm font-medium">On camera</h2>
              {activity && activity.frames > 0 ? (
                <>
                  <dl className="mt-4 grid grid-cols-2 gap-4">
                    <Metric label="Eye contact" value={pct(activity.eye_contact_pct)} tone={activity.eye_contact_pct === null ? undefined : scoreTone(activity.eye_contact_pct)} />
                    <Metric label="Upright posture" value={pct(activity.posture_pct)} tone={activity.posture_pct === null ? undefined : scoreTone(activity.posture_pct)} />
                    <Metric label="Face in frame" value={`${activity.face_visible_pct}%`} tone={scoreTone(activity.face_visible_pct)} />
                    <Metric label="Tab switches" value={String(activity.tab_switches)} tone={activity.tab_switches ? "text-destructive" : "text-success"} />
                  </dl>
                  <ul className="mt-5 space-y-2 border-t pt-4 text-sm text-muted-foreground">
                    {activity.tips.map((t) => (
                      <li key={t}>· {t}</li>
                    ))}
                  </ul>
                </>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  {activity?.tab_switches
                    ? `Camera was off. You switched tabs ${activity.tab_switches} time(s).`
                    : "Camera was off for this interview, so there's no activity data."}
                </p>
              )}
            </section>
          </aside>
        </div>
      </main>
      <Footer />
    </div>
  );
}

const pct = (v: number | null) => (v === null ? "n/a" : `${v}%`);

const CATEGORY_MAX: Record<string, number> = {
  technical_accuracy: 30, depth: 25, clarity: 20, examples: 15, relevance: 10,
  correctness: 40, efficiency: 20, code_quality: 15, edge_cases: 15, explanation: 10,
};

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-card p-6">
      <p className="eyebrow">{label}</p>
      <p className="display mt-2 text-3xl leading-tight">{value}</p>
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className={cn("display mt-0.5 text-2xl", tone)}>{value}</dd>
    </div>
  );
}

function ListBlock({ title, items, tone, small }: { title: string; items: string[]; tone?: "good" | "bad"; small?: boolean }) {
  if (!items?.length) return null;
  return (
    <div>
      <p className={cn("eyebrow", tone === "good" && "text-success", tone === "bad" && "text-warning")}>{title}</p>
      <ul className={cn("mt-2 space-y-1.5", small ? "text-sm" : "text-[15px]")}>
        {items.map((it) => (
          <li key={it} className="flex gap-2 leading-snug">
            <span className="text-muted-foreground">–</span>
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
