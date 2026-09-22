import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowRight, Download, FileText, Mic, Pencil } from "lucide-react";
import Header, { Footer } from "@/components/Header";
import { Meter, Spinner, formatDate, scoreTone } from "@/components/bits";
import { useUserStats } from "@/hooks/useUserStats";
import { useProfile } from "@/hooks/useProfile";
import { api, download, getBackendUrl, setBackendUrl, type InterviewRecord } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Health {
  llm: { reachable: boolean; model: string; model_available: boolean };
  speech: { ready: boolean; model: string; error: string | null };
  monitoring: boolean;
}

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function NameEditor() {
  const { profile, setName } = useProfile();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(profile.name);

  if (editing) {
    return (
      <form
        className="inline-flex items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setName(value);
          setEditing(false);
        }}
      >
        <input
          autoFocus
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Your name"
          className="h-9 w-44 rounded-md border bg-card px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
        />
        <button className="h-9 rounded-md bg-primary px-3 text-sm text-primary-foreground">Save</button>
      </form>
    );
  }
  return (
    <button
      onClick={() => setEditing(true)}
      className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
    >
      <Pencil className="h-3.5 w-3.5" />
      {profile.name ? "Edit name" : "Add your name for reports"}
    </button>
  );
}

function Stat({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: string }) {
  return (
    <div className="bg-card px-5 py-5">
      <p className="eyebrow">{label}</p>
      <p className={cn("display mt-2 text-4xl leading-none", tone)}>{value}</p>
      {sub && <p className="mt-2 text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

function Trend({ interviews }: { interviews: InterviewRecord[] }) {
  const data = [...interviews]
    .reverse()
    .map((i, idx) => ({ n: idx + 1, score: i.score, date: formatDate(i.date) }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={data} margin={{ top: 10, right: 8, left: -24, bottom: 0 }}>
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity={0.18} />
            <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="hsl(var(--border))" strokeDasharray="2 4" />
        <XAxis dataKey="n" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} tickFormatter={(n) => `#${n}`} />
        <YAxis domain={[0, 100]} ticks={[0, 50, 100]} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
        <Tooltip
          cursor={{ stroke: "hsl(var(--border))" }}
          contentStyle={{
            background: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: 6,
            fontSize: 12,
          }}
          labelFormatter={(_, p) => (p?.[0]?.payload?.date as string) ?? ""}
          formatter={(v: number) => [`${v}/100`, "Score"]}
        />
        <Area type="monotone" dataKey="score" stroke="hsl(var(--accent))" strokeWidth={2} fill="url(#trendFill)" dot={{ r: 3, fill: "hsl(var(--accent))", strokeWidth: 0 }} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function BackendAddress() {
  const client = useQueryClient();
  const [value, setValue] = useState(getBackendUrl());
  const [saved, setSaved] = useState(false);
  return (
    <form
      className="mt-4 border-t pt-4"
      onSubmit={(e) => {
        e.preventDefault();
        setBackendUrl(value);
        setValue(getBackendUrl());
        setSaved(true);
        client.invalidateQueries();
      }}
    >
      <label htmlFor="backend-url" className="text-xs font-medium">Backend address</label>
      <div className="mt-1.5 flex gap-2">
        <input
          id="backend-url"
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            setSaved(false);
          }}
          placeholder="http://127.0.0.1:8000"
          className="h-8 min-w-0 flex-1 rounded-md border bg-background px-2 text-xs outline-none focus:ring-2 focus:ring-ring"
        />
        <button className="h-8 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground">Save</button>
      </div>
      <p className="mt-1.5 text-[11px] text-muted-foreground">
        {saved ? "Saved for this browser." : "Where the Career Mentor backend is running, e.g. your PC or a tunnel URL."}
      </p>
    </form>
  );
}

function SystemStatus() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: () => api.get<Health>("/api/healthz"),
    refetchInterval: 15_000,
  });
  const rows: [string, boolean, string][] = data
    ? [
        [
          "Language model",
          data.llm.reachable && data.llm.model_available,
          data.llm.reachable ? (data.llm.model_available ? data.llm.model : `${data.llm.model} not pulled`) : "Ollama offline",
        ],
        ["Speech to text", data.speech.ready, data.speech.ready ? `whisper-${data.speech.model}` : data.speech.error ? "unavailable" : "loading…"],
        ["Camera analysis", data.monitoring, data.monitoring ? "mediapipe" : "unavailable"],
      ]
    : [];
  return (
    <section className="rounded-md border bg-card p-5">
      <h2 className="text-sm font-medium">Local AI status</h2>
      {isLoading && <p className="mt-3 text-sm text-muted-foreground">Checking…</p>}
      {isError && <p className="mt-3 text-sm text-destructive">Backend not reachable{getBackendUrl() ? ` at ${getBackendUrl()}` : ""}.</p>}
      <ul className="mt-3 space-y-2">
        {rows.map(([label, ok, detail]) => (
          <li key={label} className="flex items-center justify-between gap-3 text-sm">
            <span className="flex items-center gap-2">
              <span className={cn("h-1.5 w-1.5 rounded-full", ok ? "bg-success" : "bg-warning")} />
              {label}
            </span>
            <span className="num truncate text-xs text-muted-foreground">{detail}</span>
          </li>
        ))}
      </ul>
      {data && !data.llm.reachable && (
        <p className="mt-3 border-t pt-3 text-xs text-muted-foreground">
          Run <code className="num rounded bg-muted px-1">ollama serve</code> and reload. Grading falls back to estimates without it.
        </p>
      )}
      <BackendAddress />
    </section>
  );
}

export default function Dashboard() {
  const { profile } = useProfile();
  const { data, isLoading, isError, error } = useUserStats();
  const interviews = data?.interviews ?? [];
  const ats = data?.ats_checks ?? [];
  const latest = interviews[0];
  const previous = interviews[1];
  const delta = latest && previous ? latest.score - previous.score : null;

  const focus = Array.from(new Set(interviews.slice(0, 3).flatMap((i) => i.focus_areas ?? []))).slice(0, 5);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="container flex-1 py-10">
        <div className="flex flex-col justify-between gap-4 border-b pb-8 sm:flex-row sm:items-end">
          <div>
            <p className="eyebrow mb-3">
              {new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}
            </p>
            <h1 className="display text-4xl sm:text-5xl">
              {greeting()}
              {profile.name ? `, ${profile.name.split(" ")[0]}` : ""}.
            </h1>
            <div className="mt-3">
              <NameEditor />
            </div>
          </div>
        </div>

        {/* Actions */}
        <h2 className="mt-8 mb-4 text-2xl font-bold">Quick Actions</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {[
            { to: "/resume-upload", icon: Mic, title: "Start AI Interview", sub: "Five questions from your resume · about 20 minutes" },
            { to: "/ats-checker", icon: FileText, title: "ATS Score Checker", sub: "Score, missing keywords and bullet rewrites" },
          ].map((a) => (
            <Link
              key={a.to}
              to={a.to}
              className="group rounded-lg border bg-card p-6 shadow-sm transition-all duration-300 hover:scale-[1.02] hover:shadow-primary"
            >
              <div className="flex items-center space-x-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-gradient-primary">
                  <a.icon className="h-6 w-6 text-primary-foreground" />
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold">{a.title}</h3>
                  <p className="text-muted-foreground">{a.sub}</p>
                </div>
                <ArrowRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-primary" />
              </div>
            </Link>
          ))}
        </div>

        {/* Stats */}
        <h2 className="mt-8 mb-4 text-2xl font-bold">Performance Overview</h2>
        <div className="grid grid-cols-2 gap-px overflow-hidden rounded-lg border bg-border shadow-sm lg:grid-cols-4">
          <Stat label="Interviews" value={isLoading ? "–" : String(data?.interviews_completed ?? 0)} sub={latest ? `Last on ${formatDate(latest.date)}` : "None yet"} />
          <Stat
            label="Latest score"
            value={latest ? String(latest.score) : "–"}
            tone={latest ? scoreTone(latest.score) : undefined}
            sub={delta === null ? (latest ? "First attempt" : "Complete an interview") : `${delta >= 0 ? "+" : ""}${delta} vs previous`}
          />
          <Stat label="Average" value={interviews.length ? String(Math.round(data!.average_score)) : "–"} sub={interviews.length ? `Best ${data!.best_score}` : "—"} />
          <Stat
            label="Resume score"
            value={ats.length ? String(ats[0].score) : "–"}
            tone={ats.length ? scoreTone(ats[0].score) : undefined}
            sub={ats.length ? (ats[0].job_description_used ? "Against a job description" : "General check") : "Not checked yet"}
          />
        </div>

        {isError && (
          <p className="mt-6 rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
            {(error as Error).message}
          </p>
        )}

        <div className="mt-8 grid gap-8 lg:grid-cols-[1fr_320px]">
          <div className="min-w-0 space-y-8">
            <section className="rounded-md border bg-card">
              <div className="flex items-baseline justify-between border-b px-5 py-4">
                <h2 className="text-sm font-medium">Score trend</h2>
                <span className="text-xs text-muted-foreground">Overall score per interview</span>
              </div>
              <div className="px-3 py-4">
                {interviews.length >= 2 ? (
                  <Trend interviews={interviews.slice(0, 12)} />
                ) : (
                  <div className="flex h-[220px] flex-col items-center justify-center text-center">
                    <p className="display text-2xl">Your progress will show here.</p>
                    <p className="mt-2 max-w-xs text-sm text-muted-foreground">
                      Complete two interviews to see how your score moves between attempts.
                    </p>
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-md border bg-card">
              <div className="border-b px-5 py-4">
                <h2 className="text-sm font-medium">Interview history</h2>
              </div>
              {isLoading ? (
                <div className="flex items-center gap-2 px-5 py-8 text-sm text-muted-foreground">
                  <Spinner /> Loading…
                </div>
              ) : interviews.length === 0 ? (
                <div className="px-5 py-10 text-center">
                  <p className="text-sm text-muted-foreground">No interviews yet.</p>
                  <Link to="/resume-upload" className="mt-3 inline-flex items-center gap-1 text-sm font-medium link-underline">
                    Start your first one <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[560px] text-sm">
                    <thead>
                      <tr className="border-b text-left">
                        <th className="eyebrow px-5 py-2.5 font-normal">Date</th>
                        <th className="eyebrow px-3 py-2.5 font-normal">Score</th>
                        <th className="eyebrow px-3 py-2.5 font-normal">Answered</th>
                        <th className="eyebrow px-3 py-2.5 font-normal">Verdict</th>
                        <th className="eyebrow px-5 py-2.5 text-right font-normal">Reports</th>
                      </tr>
                    </thead>
                    <tbody>
                      {interviews.slice(0, 10).map((i) => (
                        <tr key={i.session_id} className="border-b last:border-0">
                          <td className="whitespace-nowrap px-5 py-3">{formatDate(i.date)}</td>
                          <td className="px-3 py-3">
                            <div className="flex items-center gap-3">
                              <span className={cn("num w-7", scoreTone(i.score))}>{i.score}</span>
                              <Meter value={i.score} className="w-20" />
                            </div>
                          </td>
                          <td className="num px-3 py-3 text-muted-foreground">
                            {i.answered ?? "–"}/{i.questions}
                          </td>
                          <td className="px-3 py-3 text-muted-foreground">{i.recommendation ?? "–"}</td>
                          <td className="px-5 py-3">
                            <div className="flex justify-end gap-1">
                              <button
                                onClick={() => download(`/api/report/${i.session_id}/interview`)}
                                className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                                title="Download interview report"
                              >
                                <Download className="h-3 w-3" /> Answers
                              </button>
                              {i.has_activity_report && (
                                <button
                                  onClick={() => download(`/api/report/${i.session_id}/activity`)}
                                  className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                                  title="Download activity report"
                                >
                                  <Download className="h-3 w-3" /> Activity
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>

          <aside className="space-y-6">
            <section className="rounded-md border bg-card p-5">
              <h2 className="text-sm font-medium">Focus next</h2>
              {focus.length ? (
                <ol className="mt-3 space-y-3">
                  {focus.map((f, idx) => (
                    <li key={f} className="flex gap-3 text-sm leading-snug">
                      <span className="num pt-px text-xs text-accent">{String(idx + 1).padStart(2, "0")}</span>
                      <span>{f}</span>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">
                  After your first interview, the areas to work on from your reports collect here.
                </p>
              )}
            </section>

            <section className="rounded-md border bg-card p-5">
              <div className="flex items-baseline justify-between">
                <h2 className="text-sm font-medium">Resume checks</h2>
                <Link to="/ats-checker" className="text-xs text-muted-foreground hover:text-foreground">New check</Link>
              </div>
              {ats.length ? (
                <ul className="mt-3 divide-y">
                  {ats.slice(0, 5).map((a) => (
                    <li key={a.session_id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                      <div className="min-w-0">
                        <p className="truncate">{a.file || "Resume"}</p>
                        <p className="text-xs text-muted-foreground">{formatDate(a.date)}</p>
                      </div>
                      <span className={cn("num", scoreTone(a.score))}>{a.score}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-muted-foreground">No checks yet.</p>
              )}
            </section>

            <SystemStatus />
          </aside>
        </div>
      </main>
      <Footer />
    </div>
  );
}
