import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Code2, Keyboard, Mic } from "lucide-react";
import { cn } from "@/lib/utils";

// "Why Choose Our Platform?" on the landing page. Each tile shows a small
// preview of the real feature instead of a generic icon-and-caption card.

function Tile({
  className,
  delay = 0,
  children,
}: {
  className?: string;
  delay?: number;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-60px" }}
      transition={{ duration: 0.5, delay }}
      className={cn(
        "group relative overflow-hidden rounded-2xl border border-border bg-card p-7 transition-all duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-primary",
        className,
      )}
    >
      {children}
    </motion.div>
  );
}

function Label({ n, children }: { n: string; children: React.ReactNode }) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <span className="font-mono text-xs font-semibold text-primary">{n}</span>
      <span className="h-px w-8 bg-gradient-primary" />
      <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{children}</span>
    </div>
  );
}

function Bar({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono">{value}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <motion.div
          initial={{ width: 0 }}
          whileInView={{ width: `${value}%` }}
          viewport={{ once: true }}
          transition={{ duration: 1, delay: 0.3 }}
          className="h-full rounded-full bg-gradient-primary"
        />
      </div>
    </div>
  );
}

export default function WhyChoose() {
  const navigate = useNavigate();

  return (
    <section className="relative overflow-hidden py-24">
      {/* soft colour wash behind the grid */}
      <div className="pointer-events-none absolute -left-40 top-20 h-96 w-96 rounded-full bg-primary/10 blur-3xl" />
      <div className="pointer-events-none absolute -right-40 bottom-10 h-96 w-96 rounded-full bg-accent/10 blur-3xl" />

      <div className="container relative mx-auto px-6">
        <div className="mb-14 grid items-end gap-6 lg:grid-cols-2">
          <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.6 }}>
            <p className="mb-3 text-sm font-semibold text-primary">Why Choose Our Platform?</p>
            <h2 className="text-4xl font-bold leading-tight md:text-5xl">
              A practice room that actually{" "}
              <span className="bg-gradient-primary bg-clip-text text-transparent">knows your resume.</span>
            </h2>
          </motion.div>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-lg text-muted-foreground lg:pb-2"
          >
            Every question comes from your own projects, every answer gets a real grade, and everything runs on
            open-source AI on your machine. No accounts, no API keys, no data leaving your computer.
          </motion.p>
        </div>

        <div className="grid gap-5 md:grid-cols-6">
          {/* 01: resume-based questions (hero tile) */}
          <Tile className="md:col-span-4 md:row-span-2">
            <Label n="01">Built from your resume</Label>
            <h3 className="text-2xl font-bold">Questions about the projects you actually built</h3>
            <p className="mt-2 max-w-lg text-muted-foreground">
              Upload a PDF or Word resume. The interviewer reads your projects and skills, then asks three conceptual
              questions and two coding problems written for you.
            </p>

            <div className="mt-7 grid gap-4 sm:grid-cols-[0.9fr_1.1fr]">
              <div className="rounded-xl border border-border bg-background/60 p-4">
                <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Found on resume</p>
                <div className="flex flex-wrap gap-1.5">
                  {["python", "react", "flask", "mongodb", "opencv", "docker", "sql"].map((s, i) => (
                    <motion.span
                      key={s}
                      initial={{ opacity: 0, scale: 0.8 }}
                      whileInView={{ opacity: 1, scale: 1 }}
                      viewport={{ once: true }}
                      transition={{ delay: 0.2 + i * 0.06 }}
                      className="rounded-md bg-primary/10 px-2 py-1 font-mono text-xs text-primary"
                    >
                      {s}
                    </motion.span>
                  ))}
                </div>
              </div>
              <div className="relative rounded-xl border border-primary/30 bg-background/60 p-4">
                <span className="absolute -top-2.5 left-4 rounded-full bg-gradient-primary px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-primary-foreground">
                  Question 2 · Theory
                </span>
                <p className="mt-1 text-sm leading-relaxed">
                  "In your face-tracking project you used OpenCV. How would you keep detection accurate when the room
                  lighting changes mid-interview?"
                </p>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-3">
              {[
                { icon: Mic, title: "Speak", sub: "Transcribed by Whisper" },
                { icon: Keyboard, title: "Type", sub: "When a mic isn't handy" },
                { icon: Code2, title: "Code", sub: "Built-in code editor" },
              ].map((m) => (
                <div key={m.title} className="rounded-xl border border-border bg-background/60 p-3">
                  <m.icon className="h-4 w-4 text-primary" />
                  <p className="mt-2 text-sm font-semibold">{m.title}</p>
                  <p className="text-xs text-muted-foreground">{m.sub}</p>
                </div>
              ))}
            </div>

            <button
              onClick={() => navigate("/resume-upload")}
              className="mt-7 inline-flex items-center gap-2 text-sm font-semibold text-primary"
            >
              Start a mock interview
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
            </button>
          </Tile>

          {/* 02: private open-source AI */}
          <Tile className="md:col-span-2" delay={0.1}>
            <Label n="02">Private by design</Label>
            <h3 className="text-xl font-bold">Open-source AI on your machine</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Grading runs on Qwen3 through Ollama. Your resume never goes to a third-party service, and the model can
              be fine-tuned on your own data.
            </p>
            <div className="mt-5 rounded-lg bg-slate-950 p-3 font-mono text-xs text-slate-300">
              <span className="text-emerald-400">$</span> ollama run qwen3:4b
              <br />
              <span className="text-slate-500">model loaded · running locally</span>
            </div>
          </Tile>

          {/* 03: activity monitoring */}
          <Tile className="md:col-span-2" delay={0.15}>
            <Label n="03">Real-time monitoring</Label>
            <h3 className="text-xl font-bold">Your webcam, like a proctor</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Eye contact, posture and tab switches are tracked live and summarised in an activity report.
            </p>
            <div className="mt-5 space-y-3">
              <Bar label="Eye contact" value={86} />
              <Bar label="Upright posture" value={74} />
            </div>
          </Tile>

          {/* 04: ATS checker */}
          <Tile className="md:col-span-3" delay={0.1}>
            <Label n="04">Resume check</Label>
            <h3 className="text-xl font-bold">See what screening software sees</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Paste a job description to find missing keywords, get a consistent ATS score and rewrites for weak
              bullet points.
            </p>
            <div className="mt-5 flex flex-wrap items-center gap-1.5">
              {["python", "pytorch", "rest"].map((k) => (
                <span key={k} className="rounded-md border border-success/30 bg-success/10 px-2 py-0.5 font-mono text-xs text-success">
                  ✓ {k}
                </span>
              ))}
              {["aws", "kubernetes"].map((k) => (
                <span key={k} className="rounded-md border border-destructive/30 bg-destructive/10 px-2 py-0.5 font-mono text-xs text-destructive">
                  ✗ {k}
                </span>
              ))}
            </div>
          </Tile>

          {/* 05: reports */}
          <Tile className="md:col-span-3" delay={0.15}>
            <Label n="05">Instant results</Label>
            <h3 className="text-xl font-bold">No waiting between questions</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Answers are graded in the background while you continue. Speak, type or code, and every question gets a
              score, feedback and a model answer.
            </p>
            <div className="mt-5 flex items-center gap-3">
              {[82, 64, 91, 58, 77].map((s, i) => (
                <div key={i} className="flex flex-1 flex-col items-center gap-1">
                  <div className="flex h-14 w-full items-end overflow-hidden rounded-md bg-muted">
                    <motion.div
                      initial={{ height: 0 }}
                      whileInView={{ height: `${s}%` }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.8, delay: 0.2 + i * 0.08 }}
                      className="w-full bg-gradient-primary"
                    />
                  </div>
                  <span className="font-mono text-[10px] text-muted-foreground">Q{i + 1}</span>
                </div>
              ))}
            </div>
          </Tile>

          {/* 06: no sign-up (full-width strip) */}
          <Tile className="md:col-span-6 !p-0" delay={0.1}>
            <div className="flex flex-col items-start justify-between gap-4 bg-gradient-primary p-7 text-primary-foreground md:flex-row md:items-center">
              <div>
                <p className="mb-1 font-mono text-xs font-semibold opacity-80">06 · NO SIGN-UP</p>
                <h3 className="text-xl font-bold">Open the site and start practising. No account needed.</h3>
                <p className="mt-1 text-sm opacity-90">Your interview history and ATS scores stay on your device.</p>
              </div>
              <button
                onClick={() => navigate("/resume-upload")}
                className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-white px-5 py-2.5 text-sm font-semibold text-primary transition-transform hover:scale-105"
              >
                Try it now <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </Tile>
        </div>
      </div>
    </section>
  );
}
