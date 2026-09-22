import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { clearUserStatsCache } from "@/hooks/useUserStats";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
  BarChart, Bar, Legend
} from "recharts";

interface Evaluation {
  overall_score: number;
  category_scores?: Record<string, number>;
  strengths?: string[];
  weaknesses?: string[];
  detailed_feedback?: string;
  detailed_explanation?: string;
}

interface FinalAssessment {
  final_recommendation: string;
  confidence_level: number;
  overall_assessment: string;
  key_strengths: string[];
  development_areas: string[];
  technical_level: string;
  communication_rating: number;
  problem_solving_rating: number;
  role_fit: string;
  next_steps: string;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const InterviewResults: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { user } = useAuth();

  // session passed via navigate(...)
  const { sessionId } = location.state || {};

  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [finalAssessment, setFinalAssessment] = useState<FinalAssessment | null>(null);
  const [reportPath, setReportPath] = useState<string | null>(null);
  const [reportUrl, setReportUrl] = useState<string | null>(null);
  const [storedSession, setStoredSession] = useState<string | null>(sessionId || null);

  useEffect(() => {
    // 1️⃣ First try using router state (preferred)
    if (sessionId) {
      loadFromLocalStorage(sessionId);
      return;
    }

    // 2️⃣ If sessionId not provided via route, fallback to localStorage
    const raw = localStorage.getItem("InterviewResults");
    if (!raw) {
      navigate("/");
      return;
    }

    try {
      const parsed = JSON.parse(raw);
      setStoredSession(parsed.session_id || null);
      setEvaluations(parsed.evaluations || []);
      setReportPath(parsed.report_path || null);
      setReportUrl(parsed.report_url || null);

      // final assessment is optional
      if (parsed.final_assessment) {
        setFinalAssessment(parsed.final_assessment);
      }
      
      // Save interview result to backend
      if (user?.id) {
        const overallScore = parsed.evaluations?.reduce((sum: number, ev: Evaluation) => sum + (ev.overall_score || 0), 0) / (parsed.evaluations?.length || 1) || 0;
        console.log("📊 Calculated score details:", {
          evaluations: parsed.evaluations,
          length: parsed.evaluations?.length || 0,
          sum: parsed.evaluations?.reduce((sum: number, ev: Evaluation) => sum + (ev.overall_score || 0), 0),
          calculatedScore: overallScore,
          roundedScore: Math.round(overallScore)
        });
        saveInterviewResult(user.id, parsed.session_id, Math.round(overallScore), parsed.evaluations?.length || 0);
      }
    } catch (err) {
      console.error("Error parsing InterviewResults:", err);
      navigate("/");
    }
  }, [sessionId, navigate, user?.id]);

  const saveInterviewResult = async (userId: string, sessionId: string, score: number, questionCount: number) => {
    try {
      console.log("📤 Saving interview result:", { userId, sessionId, score, questionCount });
      const response = await fetch("/api/save-interview-result", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          session_id: sessionId,
          overall_score: score,
          questions_count: questionCount,
        }),
      });
      
      const responseData = await response.json();
      console.log("📥 Server response:", responseData);
      
      if (response.ok) {
        console.log("✅ Interview result saved");
        // Clear the cache so dashboard fetches fresh data
        clearUserStatsCache();
        console.log("🔄 Cache cleared, listeners notified");
      } else {
        console.error("❌ Server error:", responseData);
      }
    } catch (err) {
      console.error("Failed to save interview result:", err);
    }
  };

  // Load data from localStorage when sessionId is available
  const loadFromLocalStorage = (id: string) => {
    const raw = localStorage.getItem("InterviewResults");
    if (!raw) {
      navigate("/");
      return;
    }

    try {
      const parsed = JSON.parse(raw);

      setStoredSession(id);
      setEvaluations(parsed.evaluations || []);
      setReportPath(parsed.report_path || null);
      setReportUrl(parsed.report_url || null);

      if (parsed.final_assessment) setFinalAssessment(parsed.final_assessment);

      // Save interview result to backend
      if (user?.id) {
        const overallScore = parsed.evaluations?.reduce((sum: number, ev: Evaluation) => sum + (ev.overall_score || 0), 0) / (parsed.evaluations?.length || 1) || 0;
        console.log("📊 Calculated score details (from sessionId route):", {
          evaluations: parsed.evaluations,
          length: parsed.evaluations?.length || 0,
          sum: parsed.evaluations?.reduce((sum: number, ev: Evaluation) => sum + (ev.overall_score || 0), 0),
          calculatedScore: overallScore,
          roundedScore: Math.round(overallScore)
        });
        saveInterviewResult(user.id, parsed.session_id, Math.round(overallScore), parsed.evaluations?.length || 0);
      }
    } catch (err) {
      console.error("Failed to load localStorage InterviewResults:", err);
      navigate("/");
    }
  };

  // Line chart data (overall score per question)
  const scoreData = evaluations.map((ev, idx) => ({
    name: `Q${idx + 1}`,
    score: ev.overall_score || 0,
  }));

  // Category breakdown for first question
  const categoryData =
    evaluations.length > 0 && evaluations[0].category_scores
      ? Object.entries(evaluations[0].category_scores).map(([cat, val]) => ({
          category: cat,
          score: val,
        }))
      : [];

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Interview Results</h1>

      {/* Final Assessment Section */}
      {finalAssessment && (
        <div className="mb-8 p-6 border rounded-lg shadow bg-white">
          <h2 className="text-2xl font-semibold mb-4">Final Assessment</h2>
          <p><strong>Recommendation:</strong> {finalAssessment.final_recommendation}</p>
          <p><strong>Confidence:</strong> {finalAssessment.confidence_level}/10</p>
          <p><strong>Technical Level:</strong> {finalAssessment.technical_level}</p>
          <p><strong>Communication:</strong> {finalAssessment.communication_rating}/10</p>
          <p><strong>Problem Solving:</strong> {finalAssessment.problem_solving_rating}/10</p>
          <p className="mt-2">{finalAssessment.overall_assessment}</p>
        </div>
      )}

      {/* Score Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-10">
        {/* Line Chart */}
        <div className="p-4 border rounded-lg shadow bg-white">
          <h3 className="text-lg font-semibold mb-2">Scores per Question</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={scoreData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Line type="monotone" dataKey="score" stroke="#2E86AB" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Bar Chart */}
        <div className="p-4 border rounded-lg shadow bg-white">
          <h3 className="text-lg font-semibold mb-2">Category Breakdown (Q1)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={categoryData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="category" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="score" fill="#A23B72" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Detailed Evaluations */}
      <h2 className="text-xl font-semibold mb-4">Detailed Question Evaluations</h2>
      <div className="space-y-6">
        {evaluations.map((ev, idx) => (
          <div key={idx} className="p-4 border rounded-lg shadow bg-white">
            <h3 className="font-bold">Question {idx + 1}</h3>
            <p><strong>Score:</strong> {ev.overall_score}/100</p>
            <p><strong>Strengths:</strong> {ev.strengths?.join(", ") || "N/A"}</p>
            <p><strong>Weaknesses:</strong> {ev.weaknesses?.join(", ") || "N/A"}</p>
            <p><strong>Feedback:</strong> {ev.detailed_feedback || "No feedback"}</p>
          </div>
        ))}
      </div>

      {/* Download PDF Button */}
      {(reportUrl || storedSession) && (
        <div className="mt-8">
          <a
            href={
              reportUrl
                ? reportUrl
                : `${API_BASE}/api/download-report/${storedSession}`
            }
            target="_blank"
            rel="noopener noreferrer"
            className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700"
          >
            📄 Download Full Report (PDF)
          </a>
        </div>
      )}

      {/* Back Home */}
      <button
        onClick={() => navigate("/dashboard")}
        className="mt-6 bg-gray-700 text-white px-4 py-2 rounded hover:bg-gray-800"
      >
        Go Home
      </button>
    </div>
  );
};

export default InterviewResults;
