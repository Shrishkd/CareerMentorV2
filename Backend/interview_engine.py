"""
Question generation, answer grading and the final assessment.

Every function has a deterministic fallback so an interview can always finish,
even if the local model is not running.
"""
import json
import random
import re

import llm

QUESTION_COUNT = 5
CODING_COUNT = 2

INTERVIEWER_SYSTEM = (
    "You are a senior technical interviewer at a product company interviewing a university student or "
    "early-career engineer. You are fair, specific and never vague."
)

# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["theory", "coding"]},
                    "topic": {"type": "string"},
                    "question": {"type": "string"},
                },
                "required": ["type", "topic", "question"],
            },
        }
    },
    "required": ["questions"],
}

# Used when the model is unavailable. Keyed by skill, falls back to "general".
THEORY_BANK = {
    "python": ["Explain the difference between a list, a tuple and a set in Python, and when you would choose each.",
               "What are Python decorators? Describe a situation where you used or would use one."],
    "javascript": ["Explain how the JavaScript event loop handles asynchronous code such as promises and setTimeout."],
    "react": ["How does React decide when to re-render a component, and how would you prevent unnecessary re-renders?"],
    "node.js": ["Why is Node.js well suited to I/O-heavy applications, and where does its single-threaded model struggle?"],
    "machine learning": ["Explain overfitting, how you detect it, and three techniques you would use to reduce it."],
    "deep learning": ["What problem do batch normalization and dropout each solve when training neural networks?"],
    "sql": ["Explain the difference between INNER JOIN, LEFT JOIN and a subquery, with an example of when to use each."],
    "mongodb": ["When would you choose MongoDB over a relational database, and what trade-offs does that bring?"],
    "java": ["Explain the difference between an abstract class and an interface in Java."],
    "c++": ["Explain the difference between a pointer and a reference in C++, and when each is appropriate."],
    "docker": ["What problem does Docker solve, and how is a container different from a virtual machine?"],
    "general": ["Explain the difference between a process and a thread.",
                "What happens, step by step, when you type a URL into a browser and press Enter?",
                "Explain time and space complexity using an example from one of your projects.",
                "What is the difference between REST and GraphQL APIs?",
                "Explain what normalization is in databases and why it matters."],
}

CODING_BANK = [
    "Write a function that returns the indices of the two numbers in an array that add up to a given target.",
    "Write a function that checks whether a string of brackets such as '({[]})' is balanced.",
    "Write a function that returns the first non-repeating character in a string.",
    "Write a function that reverses a singly linked list and explain its time complexity.",
    "Write a function that merges two sorted arrays into one sorted array without using built-in sort.",
    "Write a function that finds the length of the longest substring without repeating characters.",
]


def _fallback_questions(profile):
    skills = profile.get("skills_flat", []) if profile else []
    theory = []
    for s in skills:
        for q in THEORY_BANK.get(s, []):
            if q not in theory:
                theory.append({"type": "theory", "topic": s, "question": q})
    general = [{"type": "theory", "topic": "fundamentals", "question": q} for q in THEORY_BANK["general"]]
    random.shuffle(general)
    theory = (theory + general)[: QUESTION_COUNT - CODING_COUNT]
    coding = [{"type": "coding", "topic": "dsa", "question": q} for q in random.sample(CODING_BANK, CODING_COUNT)]
    return theory + coding


def _profile_summary(profile, resume_text):
    if not profile:
        return resume_text[:2500]
    s = profile.get("sections", {})
    parts = [
        f"Level: {profile.get('level', 'unknown')}",
        f"Skills: {', '.join(profile.get('skills_flat', [])[:30]) or 'not listed'}",
    ]
    for key in ("summary", "experience", "projects"):
        if s.get(key):
            parts.append(f"{key.upper()}:\n{s[key][:1100]}")
    summary = "\n\n".join(parts)
    return summary if len(summary) > 200 else resume_text[:2500]


def generate_questions(resume_text, profile=None):
    """Return a list of {'type', 'topic', 'question'} dicts: 3 theory + 2 coding."""
    user = (
        f"CANDIDATE RESUME (condensed):\n{_profile_summary(profile, resume_text)}\n\n"
        f"Write exactly {QUESTION_COUNT} interview questions for this candidate:\n"
        f"- {QUESTION_COUNT - CODING_COUNT} 'theory' questions that probe concepts behind the specific projects, "
        "tools and skills on the resume. Reference the project or technology by name.\n"
        f"- {CODING_COUNT} 'coding' questions: easy-to-medium data structures and algorithms problems solvable in "
        "Python, C++ or Java in under 20 lines. State the input and expected output clearly.\n"
        "Each question must be one or two sentences, answerable verbally in two minutes. No preamble."
    )
    try:
        result = llm.chat_json(INTERVIEWER_SYSTEM, user, QUESTION_SCHEMA, task="generate_questions",
                               temperature=0.7, max_tokens=700)
        items = [q for q in result.get("questions", [])
                 if isinstance(q, dict) and len(str(q.get("question", "")).strip()) > 15]
        theory = [q for q in items if q.get("type") != "coding"][: QUESTION_COUNT - CODING_COUNT]
        coding = [q for q in items if q.get("type") == "coding"][:CODING_COUNT]
        fallback = _fallback_questions(profile)
        # Top up if the model returned too few of either kind.
        while len(theory) < QUESTION_COUNT - CODING_COUNT:
            theory.append(fallback[len(theory)])
        while len(coding) < CODING_COUNT:
            coding.append(fallback[QUESTION_COUNT - CODING_COUNT + len(coding)])
        questions = theory + coding
        for q in questions:
            q["question"] = re.sub(r"^\s*(?:q?\d+[.):]\s*)", "", str(q["question"]).strip(), flags=re.IGNORECASE)
            q["topic"] = str(q.get("topic") or "general")[:40]
        return questions, True
    except Exception as e:
        print(f"[engine] question generation fell back to the bank: {e}")
        return _fallback_questions(profile), False


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

THEORY_RUBRIC = {"technical_accuracy": 30, "depth": 25, "clarity": 20, "examples": 15, "relevance": 10}
CODING_RUBRIC = {"correctness": 40, "efficiency": 20, "code_quality": 15, "edge_cases": 15, "explanation": 10}


THEORY_EXAMPLE = {
    "question": "What is a hash map and what is its lookup time?",
    "answer": "It stores key value pairs using a hash function so lookup is O(1) on average, but collisions can "
              "make it O(n) in the worst case.",
    "grade": {
        "analysis": "Correct definition and complexity, and mentions the worst case. Does not say how collisions "
                    "are resolved and gives no example.",
        "category_scores": {"technical_accuracy": 27, "depth": 15, "clarity": 18, "examples": 4, "relevance": 9},
        "strengths": ["Correct average O(1) lookup", "Mentions worst-case O(n) caused by collisions"],
        "weaknesses": ["Does not explain chaining or open addressing", "No real-world example"],
        "detailed_feedback": "Accurate and concise. To score higher, explain how collisions are handled and give a "
                             "concrete use such as caching or counting frequencies.",
        "improvement_suggestions": ["Name the two collision strategies and their trade-offs",
                                    "Add one example from your own project"],
        "model_answer": "A hash map stores key-value pairs in buckets chosen by a hash function, giving O(1) average "
                        "lookup. Collisions are handled by chaining or open addressing; with a poor hash or high load "
                        "factor lookups degrade toward O(n), so the table resizes past a load factor of about 0.75. "
                        "I used one to count word frequencies in my sentiment project.",
    },
}

CODING_EXAMPLE = {
    "question": "Write a function that returns the maximum element of a list.",
    "answer": "def find_max(nums):\n    best = nums[0]\n    for n in nums:\n        if n > best:\n            best = n\n"
              "    return best",
    "grade": {
        "analysis": "Correct single-pass O(n) solution with clear naming. Crashes on an empty list and has no "
                    "explanation of complexity.",
        "category_scores": {"correctness": 34, "efficiency": 20, "code_quality": 12, "edge_cases": 5, "explanation": 3},
        "strengths": ["Correct linear scan", "Optimal O(n) time and O(1) space"],
        "weaknesses": ["IndexError on an empty list", "No comment on complexity"],
        "detailed_feedback": "The core logic is right and efficient. Guard against an empty input and state the time "
                             "and space complexity when you submit.",
        "improvement_suggestions": ["Handle the empty list explicitly", "State the complexity in one line"],
        "model_answer": "Check for an empty list first (return None or raise ValueError), then keep a running "
                        "maximum in one pass: O(n) time, O(1) space. Mention that max(nums) does the same in Python.",
    },
}


def _eval_schema(rubric):
    return {
        "type": "object",
        "properties": {
            "analysis": {"type": "string"},
            "category_scores": {
                "type": "object",
                "properties": {k: {"type": "integer"} for k in rubric},
                "required": list(rubric),
            },
            "strengths": {"type": "array", "items": {"type": "string"}},
            "weaknesses": {"type": "array", "items": {"type": "string"}},
            "detailed_feedback": {"type": "string"},
            "improvement_suggestions": {"type": "array", "items": {"type": "string"}},
            "model_answer": {"type": "string"},
        },
        "required": ["analysis", "category_scores", "strengths", "weaknesses", "detailed_feedback",
                     "improvement_suggestions", "model_answer"],
    }


def _grader_system(kind):
    ex = CODING_EXAMPLE if kind == "coding" else THEORY_EXAMPLE
    return (
        "You are a senior technical interviewer grading a candidate's answer. Read the answer carefully and grade "
        "only what was actually said: never claim something is missing when it is present, and give low relevance "
        "and accuracy to answers that do not address the question.\n\n"
        f"Reply with a JSON object. Example for a different question ({json.dumps(ex['question'])}, "
        f"answer: {json.dumps(ex['answer'])}):\n"
        + json.dumps(ex["grade"])
    )


# Small models sometimes return an empty template instead of a grade.
_PLACEHOLDERS = {"", "2-3 sentences", "strength_1", "weakness_1", "suggestion_1", "under 90 words", "..."}


def _looks_empty(r):
    scores = r.get("category_scores") or {}
    feedback = str(r.get("detailed_feedback", "")).strip().lower()
    return (not any(isinstance(v, (int, float)) and v > 0 for v in scores.values())
            and (feedback in _PLACEHOLDERS or len(feedback) < 15))


def empty_evaluation(kind, reason):
    rubric = CODING_RUBRIC if kind == "coding" else THEORY_RUBRIC
    return {
        "overall_score": 0,
        "category_scores": {k: 0 for k in rubric},
        "strengths": [],
        "weaknesses": [reason],
        "detailed_feedback": reason,
        "detailed_explanation": f"Scored 0/100: {reason}",
        "improvement_suggestions": ["Attempt every question. A partial answer that shows your reasoning scores "
                                    "far better than no answer."],
        "model_answer": "",
        "follow_up_questions": [],
        "graded_by": "rules",
    }


def _fallback_evaluation(kind, answer):
    """Heuristic grade used only when the LLM is unavailable."""
    rubric = CODING_RUBRIC if kind == "coding" else THEORY_RUBRIC
    words = len(answer.split())
    ratio = min(1.0, words / (60 if kind == "coding" else 120))
    base = 0.35 + 0.35 * ratio
    cats = {k: int(round(v * base)) for k, v in rubric.items()}
    score = sum(cats.values())
    return {
        "overall_score": score,
        "category_scores": cats,
        "strengths": ["Attempted the question"] if words > 10 else [],
        "weaknesses": ["Detailed AI grading was unavailable; this is an estimate based on answer length."],
        "detailed_feedback": "The local model was not reachable, so this answer received an estimated score. "
                             "Start Ollama and retake the interview for full feedback.",
        "detailed_explanation": f"Estimated {score}/100 from answer length ({words} words).",
        "improvement_suggestions": ["Structure answers as: definition, how it works, an example, trade-offs."],
        "model_answer": "",
        "follow_up_questions": [],
        "graded_by": "estimate",
    }


def _clean_list(value, limit=4):
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()][:limit]


def evaluate_answer(question, answer, kind="theory", resume_context=""):
    """Grade one answer. Overall score is the sum of rubric categories, so it is always consistent."""
    answer = (answer or "").strip()
    if not answer or answer.upper() == "SKIPPED":
        return empty_evaluation(kind, "The question was skipped.")
    if len(answer.split()) < 4 and kind != "coding":
        return empty_evaluation(kind, "The answer was too short to assess (fewer than four words).")

    rubric = CODING_RUBRIC if kind == "coding" else THEORY_RUBRIC
    maxima = ", ".join(f"{k} {v}" for k, v in rubric.items())
    what = "CODE" if kind == "coding" else "SPOKEN ANSWER (speech-to-text transcript; ignore filler words)"
    user = (
        f"QUESTION:\n{question}\n\n"
        f"CANDIDATE'S {what}:\n{answer[:3500]}\n\n"
        + (f"CANDIDATE BACKGROUND: {resume_context[:400]}\n\n" if resume_context else "")
        + f"Rubric maximums: {maxima}. "
        + ("Judge correctness on normal and edge-case inputs, and the time complexity. " if kind == "coding" else "")
        + "Keep the analysis to two sentences, strengths and weaknesses to at most three each, the feedback to two "
          "or three sentences, and the model answer under 90 words."
    )
    r = None
    for attempt, temp in enumerate((0.2, 0.5)):
        try:
            r = llm.chat_json(_grader_system(kind), user, _eval_schema(rubric), task=f"evaluate_{kind}",
                              temperature=temp, max_tokens=800)
        except Exception as e:
            print(f"[engine] grading fell back to estimate: {e}")
            return _fallback_evaluation(kind, answer)
        if not _looks_empty(r):
            break
        print(f"[engine] grader returned an empty template (attempt {attempt + 1})")
    if r is None or _looks_empty(r):
        return _fallback_evaluation(kind, answer)

    raw = r.get("category_scores") if isinstance(r.get("category_scores"), dict) else {}
    cats = {}
    for k, cap in rubric.items():
        try:
            cats[k] = max(0, min(cap, int(raw.get(k, 0))))
        except (TypeError, ValueError):
            cats[k] = 0
    score = sum(cats.values())
    feedback = str(r.get("detailed_feedback", "")).strip()
    breakdown = ", ".join(f"{k.replace('_', ' ')} {cats[k]}/{rubric[k]}" for k in rubric)
    return {
        "overall_score": score,
        "category_scores": cats,
        "strengths": _clean_list(r.get("strengths"), 3),
        "weaknesses": _clean_list(r.get("weaknesses"), 3),
        "detailed_feedback": feedback,
        "detailed_explanation": f"Scored {score}/100 ({breakdown}). {feedback}",
        "improvement_suggestions": _clean_list(r.get("improvement_suggestions"), 3),
        "model_answer": str(r.get("model_answer", "")).strip(),
        "follow_up_questions": _clean_list(r.get("follow_up_questions"), 2),
        "graded_by": llm.LLM_MODEL,
    }


# ---------------------------------------------------------------------------
# Final assessment
# ---------------------------------------------------------------------------

ASSESSMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_assessment": {"type": "string"},
        "key_strengths": {"type": "array", "items": {"type": "string"}},
        "development_areas": {"type": "array", "items": {"type": "string"}},
        "communication_rating": {"type": "integer"},
        "problem_solving_rating": {"type": "integer"},
        "next_steps": {"type": "string"},
    },
    "required": ["overall_assessment", "key_strengths", "development_areas", "communication_rating",
                 "problem_solving_rating", "next_steps"],
}


ASSESSMENT_EXAMPLE = {
    "overall_assessment": "Solid on Python fundamentals and explained the REST API project clearly, but struggled "
                          "with the database indexing question and skipped one coding problem. Submitted code was "
                          "correct but ignored edge cases.",
    "key_strengths": ["Clear explanation of REST design in the Flask project", "Correct two-pointer solution"],
    "development_areas": ["Database indexing and query plans", "Handling empty and invalid inputs in code"],
    "communication_rating": 7,
    "problem_solving_rating": 6,
    "next_steps": "Revise B-tree indexes and practise three array problems a day, stating edge cases before coding.",
}


def recommendation_for(score):
    if score >= 80:
        return "Strong Hire"
    if score >= 65:
        return "Hire"
    if score >= 45:
        return "Borderline"
    return "Not Yet Ready"


def level_for(score):
    if score >= 80:
        return "Advanced"
    if score >= 60:
        return "Intermediate"
    if score >= 40:
        return "Developing"
    return "Beginner"


def final_assessment(questions, answers, evaluations, activity=None):
    scores = [e.get("overall_score", 0) for e in evaluations]
    avg = sum(scores) / len(scores) if scores else 0
    answered = sum(1 for a in answers if a and a.strip() and a.strip().upper() != "SKIPPED")

    base = {
        "average_score": round(avg, 1),
        "final_recommendation": recommendation_for(avg),
        "technical_level": level_for(avg),
        "questions_answered": answered,
        "questions_total": len(questions),
    }

    lines = []
    for i, (q, e) in enumerate(zip(questions, evaluations), 1):
        text = q["question"] if isinstance(q, dict) else str(q)
        lines.append(f"Q{i} ({e.get('overall_score', 0)}/100): {text[:120]}\n"
                     f"  strengths: {'; '.join(e.get('strengths', [])[:2]) or '-'}\n"
                     f"  weaknesses: {'; '.join(e.get('weaknesses', [])[:2]) or '-'}")
    activity_note = ""
    if activity:
        def pct(v):
            return "n/a" if v is None else f"{v}%"
        activity_note = (f"\nCamera monitoring: eye contact {pct(activity.get('eye_contact_pct'))}, "
                         f"upright posture {pct(activity.get('posture_pct'))}, "
                         f"tab switches {activity.get('tab_switches', 0)}.")
    user = (
        f"Interview results (average {avg:.1f}/100, {answered}/{len(questions)} answered):\n"
        + "\n".join(lines) + activity_note +
        "\n\nWrite the final assessment of this candidate as JSON. Base every statement on the results above. "
        "Ratings are integers from 1 to 10. Example of the expected style, for a different candidate:\n"
        + json.dumps(ASSESSMENT_EXAMPLE)
    )
    try:
        r = llm.chat_json(INTERVIEWER_SYSTEM, user, ASSESSMENT_SCHEMA, task="final_assessment",
                          temperature=0.3, max_tokens=500)
        summary = str(r.get("overall_assessment", "")).strip()
        if len(summary) < 40 or summary == ASSESSMENT_EXAMPLE["overall_assessment"]:
            raise ValueError("assessment was empty or copied the example")
        base.update({
            "overall_assessment": str(r.get("overall_assessment", "")).strip(),
            "key_strengths": _clean_list(r.get("key_strengths"), 3),
            "development_areas": _clean_list(r.get("development_areas"), 3),
            "communication_rating": max(1, min(10, int(r.get("communication_rating", 5) or 5))),
            "problem_solving_rating": max(1, min(10, int(r.get("problem_solving_rating", 5) or 5))),
            "next_steps": str(r.get("next_steps", "")).strip(),
        })
        return base
    except Exception as e:
        print(f"[engine] final assessment fell back to rules: {e}")

    strengths = [s for e in evaluations for s in e.get("strengths", [])][:3]
    weaknesses = [w for e in evaluations for w in e.get("weaknesses", [])][:3]
    best = max(range(len(scores)), key=lambda i: scores[i]) + 1 if scores else None
    worst = min(range(len(scores)), key=lambda i: scores[i]) + 1 if scores else None
    base.update({
        "overall_assessment": (f"Average score {avg:.1f}/100 with {answered} of {len(questions)} questions answered. "
                               + (f"Strongest answer was Q{best}; weakest was Q{worst}." if best else "")),
        "key_strengths": strengths or ["Completed the interview"],
        "development_areas": weaknesses or ["Answer every question with a structured explanation"],
        "communication_rating": max(1, min(10, round(avg / 10))),
        "problem_solving_rating": max(1, min(10, round(avg / 10))),
        "next_steps": "Review the model answers in this report and retake the interview in a few days.",
    })
    return base
