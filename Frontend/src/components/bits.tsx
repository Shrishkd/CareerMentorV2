// Small presentational pieces shared across pages.
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export function scoreTone(score: number) {
  if (score >= 70) return "text-success";
  if (score >= 45) return "text-warning";
  return "text-destructive";
}

export function scoreBar(score: number) {
  if (score >= 70) return "bg-success";
  if (score >= 45) return "bg-warning";
  return "bg-destructive";
}

export function scoreLabel(score: number) {
  if (score >= 85) return "Excellent";
  if (score >= 70) return "Strong";
  if (score >= 55) return "Fair";
  if (score >= 40) return "Needs work";
  return "Weak";
}

/** Thin horizontal meter used for scores. */
export function Meter({ value, className = "" }: { value: number; className?: string }) {
  const v = Math.max(0, Math.min(100, value));
  return (
    <div className={cn("h-1.5 w-full overflow-hidden rounded-full bg-muted", className)}>
      <div className={cn("h-full rounded-full transition-[width] duration-700", scoreBar(v))} style={{ width: `${v}%` }} />
    </div>
  );
}

export function PageHeading({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 border-b pb-8 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-2xl">
        {eyebrow && <p className="eyebrow mb-3">{eyebrow}</p>}
        <h1 className="display text-4xl leading-[1.05] sm:text-5xl">{title}</h1>
        {children && <div className="mt-3 text-muted-foreground">{children}</div>}
      </div>
      {action}
    </div>
  );
}

const FLOW = ["Upload resume", "Camera & mic check", "Interview", "Report"];

/** Step indicator for the interview flow. `current` is 0-based. */
export function FlowSteps({ current }: { current: number }) {
  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-2 text-sm" aria-label="Progress">
      {FLOW.map((label, i) => {
        const done = i < current;
        const active = i === current;
        return (
          <li key={label} className="flex items-center gap-2">
            <span
              className={cn(
                "num flex h-6 w-6 items-center justify-center rounded-full border text-[11px]",
                done && "border-foreground bg-foreground text-background",
                active && "border-foreground text-foreground",
                !done && !active && "text-muted-foreground",
              )}
            >
              {done ? <Check className="h-3 w-3" /> : i + 1}
            </span>
            <span className={cn(active ? "text-foreground" : "text-muted-foreground", "hidden sm:inline")}>{label}</span>
            {i < FLOW.length - 1 && <span className="mx-1 h-px w-6 bg-border sm:w-10" />}
          </li>
        );
      })}
    </ol>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={cn("inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-r-transparent", className)}
      aria-hidden
    />
  );
}

export function Tag({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "good" | "bad" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 text-xs",
        tone === "neutral" && "bg-card text-foreground",
        tone === "good" && "border-success/30 bg-accent-soft text-success",
        tone === "bad" && "border-destructive/30 bg-destructive/5 text-destructive",
      )}
    >
      {children}
    </span>
  );
}

export function formatDate(iso: string) {
  const d = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`);
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
