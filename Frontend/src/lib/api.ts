// Where the Flask backend lives. Order of precedence:
//   1. a URL saved in this browser from the dashboard (lets a hosted frontend point at any backend,
//      e.g. your own PC or a tunnel, without rebuilding),
//   2. VITE_API_URL baked in at build time,
//   3. empty = same origin; in development Vite proxies /api to the Flask server.
const BACKEND_KEY = "cm_backend_url";
const BUILD_API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export function getBackendUrl(): string {
  try {
    const saved = localStorage.getItem(BACKEND_KEY);
    if (saved) return saved;
  } catch {
    // storage unavailable
  }
  return BUILD_API_BASE;
}

export function setBackendUrl(url: string) {
  const clean = url.trim().replace(/\/+$/, "");
  try {
    if (clean) localStorage.setItem(BACKEND_KEY, clean);
    else localStorage.removeItem(BACKEND_KEY);
  } catch {
    // storage unavailable
  }
}

export const apiUrl = (path: string) => `${getBackendUrl()}${path}`;

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function handle<T>(res: Response): Promise<T> {
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    // Non-JSON error pages (e.g. a proxy error) fall through to the generic message.
  }
  if (!res.ok) {
    const message =
      (data as { error?: string } | null)?.error ||
      (res.status === 502 || res.status === 504
        ? "The server is not responding. Is the backend running on port 8000?"
        : `Request failed (${res.status})`);
    throw new ApiError(message, res.status);
  }
  return data as T;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(apiUrl(path), init);
  } catch {
    throw new ApiError(
      `Can't reach the backend${getBackendUrl() ? ` at ${getBackendUrl()}` : ""}. Make sure it is running, or set its address on the Dashboard.`,
      0,
    );
  }
  return handle<T>(res);
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  form: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
};

/** Trigger a browser download for a backend file URL such as /api/report/<id>/interview. */
export function download(path: string) {
  const a = document.createElement("a");
  a.href = apiUrl(path);
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// ---- Shared API types -----------------------------------------------------

export type QuestionType = "theory" | "coding";

export interface Question {
  type: QuestionType;
  topic: string;
  question: string;
}

export interface Evaluation {
  overall_score: number;
  category_scores: Record<string, number>;
  strengths: string[];
  weaknesses: string[];
  detailed_feedback: string;
  improvement_suggestions: string[];
  model_answer?: string;
  follow_up_questions?: string[];
  graded_by?: string;
}

export interface FinalAssessment {
  average_score: number;
  final_recommendation: string;
  technical_level: string;
  questions_answered: number;
  questions_total: number;
  overall_assessment: string;
  key_strengths: string[];
  development_areas: string[];
  communication_rating: number;
  problem_solving_rating: number;
  next_steps: string;
}

export interface ActivitySummary {
  frames: number;
  duration_min: number;
  eye_contact_pct: number | null; // null = face/shoulders never detected
  posture_pct: number | null;
  face_visible_pct: number;
  tab_switches: number;
  observations: string[];
  tips: string[];
}

export interface InterviewSession {
  session_id: string;
  questions: Question[];
  candidate_name: string | null;
  skills: string[];
  llm_generated: boolean;
}

export interface ReportResponse {
  ready: boolean;
  stage?: "grading" | "assessment";
  done: number;
  total: number;
  status: string[];
  questions?: Question[];
  answers?: string[];
  evaluations?: Evaluation[];
  final_assessment?: FinalAssessment;
  activity_summary?: ActivitySummary | null;
  candidate_name?: string | null;
  report_url?: string;
  activity_report_url?: string | null;
}

export interface ATSSection {
  score: number;
  feedback: string[];
}

export interface ATSResult {
  overallScore: number;
  sections: { keywords: ATSSection; formatting: ATSSection; experience: ATSSection; skills: ATSSection };
  suggestions: string[];
  summary: string;
  bullet_rewrites: { original: string; improved: string }[];
  llm_used: boolean;
  details: {
    name: string | null;
    contact: { email: string | null; phone: string | null; linkedin: string | null; github: string | null };
    sections_found: string[];
    sections_missing: string[];
    skills_by_category: Record<string, string[]>;
    skills_backed_by_evidence: string[];
    matched_keywords: string[];
    missing_keywords: string[];
    job_description_used: boolean;
    metrics: {
      word_count: number;
      pages: number;
      bullets: number;
      quantified_bullets: number;
      action_verb_bullets: number;
      weak_phrases: string[];
      pronouns: number;
    };
  };
}

export interface InterviewRecord {
  session_id: string;
  date: string;
  score: number;
  questions: number;
  answered?: number;
  recommendation?: string;
  focus_areas?: string[];
  question_scores?: number[];
  topics?: string[];
  eye_contact?: number | null;
  tab_switches?: number;
  has_activity_report?: boolean;
}

export interface ATSRecord {
  session_id: string;
  date: string;
  score: number;
  sections: Record<string, number>;
  job_description_used: boolean;
  file: string;
}

export interface UserStats {
  interviews: InterviewRecord[];
  ats_checks: ATSRecord[];
  interviews_completed: number;
  average_score: number;
  best_score: number;
  ats_score: number;
}
