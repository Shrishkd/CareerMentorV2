"""
Resume parsing and ATS analysis.

Scores are computed deterministically from the parsed resume so the same file
always gets the same score. The LLM is only used afterwards to write a short
summary, targeted suggestions and bullet rewrites.
"""
import json
import re
import zipfile
from collections import Counter
from xml.etree import ElementTree

import fitz  # PyMuPDF

import llm

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _order_blocks(blocks, page_width):
    """Return text blocks in reading order, handling two-column layouts."""
    text_blocks = [b for b in blocks if b[6] == 0 and b[4].strip()]
    if not text_blocks:
        return []

    mid = page_width / 2
    left = [b for b in text_blocks if b[2] <= mid + page_width * 0.05]
    right = [b for b in text_blocks if b[0] >= mid - page_width * 0.05]
    full = [b for b in text_blocks if b not in left and b not in right]

    left_chars = sum(len(b[4]) for b in left)
    right_chars = sum(len(b[4]) for b in right)
    total = sum(len(b[4]) for b in text_blocks)
    two_column = total and left_chars > total * 0.2 and right_chars > total * 0.2

    if not two_column:
        return sorted(text_blocks, key=lambda b: (round(b[1], 0), b[0]))

    # Full-width blocks above the columns (usually name/contact) come first.
    columns_top = min(b[1] for b in left + right)
    header = sorted([b for b in full if b[1] <= columns_top], key=lambda b: b[1])
    footer = sorted([b for b in full if b[1] > columns_top], key=lambda b: b[1])
    return header + sorted(left, key=lambda b: b[1]) + sorted(right, key=lambda b: b[1]) + footer


def _extract_pdf(path):
    parts, links, pages = [], [], 0
    with fitz.open(path) as doc:
        pages = doc.page_count
        for page in doc:
            blocks = page.get_text("blocks")
            for b in _order_blocks(blocks, page.rect.width):
                parts.append(b[4].strip())
            for link in page.get_links():
                uri = link.get("uri")
                if uri:
                    links.append(uri)
    return "\n".join(parts), links, pages


def _extract_docx(path):
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as z:
        root = ElementTree.fromstring(z.read("word/document.xml"))
    paragraphs = []
    for p in root.iter(f"{{{ns['w']}}}p"):
        text = "".join(t.text or "" for t in p.iter(f"{{{ns['w']}}}t"))
        if text.strip():
            paragraphs.append(text.strip())
    text = "\n".join(paragraphs)
    # Rough page estimate: ~500 words per page.
    pages = max(1, round(len(text.split()) / 500))
    return text, [], pages


def extract_resume(path):
    """Return {'text', 'links', 'pages', 'extractable'} for a PDF or DOCX file."""
    lower = path.lower()
    try:
        if lower.endswith(".docx"):
            text, links, pages = _extract_docx(path)
        else:
            text, links, pages = _extract_pdf(path)
    except Exception as e:
        print(f"[resume] extraction failed for {path}: {e}")
        return {"text": "", "links": [], "pages": 0, "extractable": False}

    text = _clean_text(text)
    return {"text": text, "links": links, "pages": pages, "extractable": len(text) >= 150}


def _clean_text(text):
    # Icon fonts (Font Awesome etc.) show up as private-use glyphs.
    text = re.sub(r"[\ue000-\uf8ff]", " ", text)
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

SECTION_ALIASES = {
    "summary": ["summary", "professional summary", "profile", "objective", "career objective", "about me", "about"],
    "experience": ["experience", "work experience", "professional experience", "employment", "employment history",
                   "internship", "internships", "work history", "industry experience"],
    "education": ["education", "academic background", "academics", "educational qualification", "qualifications"],
    "skills": ["skills", "technical skills", "core skills", "key skills", "skill set", "technologies",
               "tech stack", "core competencies", "competencies", "tools and technologies"],
    "projects": ["projects", "personal projects", "academic projects", "key projects", "project work", "project experience"],
    "certifications": ["certifications", "certificates", "licenses", "courses", "certifications and courses"],
    "achievements": ["achievements", "awards", "honors", "honours", "accomplishments", "awards and achievements"],
    "activities": ["extracurricular activities", "activities", "positions of responsibility", "leadership",
                   "volunteering", "volunteer experience", "extra curricular"],
    "publications": ["publications", "research", "papers"],
}

ESSENTIAL_SECTIONS = ["education", "skills"]

SKILL_TAXONOMY = {
    "Languages": ["python", "java", "javascript", "typescript", "c", "c++", "c#", "go", "golang", "rust", "kotlin",
                  "swift", "php", "ruby", "scala", "r", "matlab", "dart", "sql", "bash", "shell"],
    "Frontend": ["react", "react.js", "next.js", "angular", "vue", "vue.js", "svelte", "html", "css", "tailwind",
                 "tailwindcss", "bootstrap", "redux", "sass", "jquery", "vite", "webpack"],
    "Backend": ["node.js", "nodejs", "express", "express.js", "django", "flask", "fastapi", "spring", "spring boot",
                ".net", "asp.net", "laravel", "rails", "graphql", "rest", "rest api", "microservices", "grpc"],
    "Data & ML": ["machine learning", "deep learning", "nlp", "computer vision", "tensorflow", "pytorch", "keras",
                  "scikit-learn", "sklearn", "pandas", "numpy", "matplotlib", "seaborn", "opencv", "hugging face",
                  "transformers", "llm", "langchain", "rag", "xgboost", "data analysis", "data visualization",
                  "power bi", "tableau", "excel", "statistics", "spark", "hadoop", "mediapipe", "yolo"],
    "Databases": ["mysql", "postgresql", "postgres", "mongodb", "redis", "sqlite", "oracle", "firebase", "supabase",
                  "dynamodb", "cassandra", "elasticsearch"],
    "Cloud & DevOps": ["aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "jenkins", "ci/cd",
                       "github actions", "terraform", "linux", "nginx", "vercel", "netlify", "render", "heroku"],
    "Tools": ["git", "github", "gitlab", "jira", "postman", "figma", "vs code", "jupyter", "agile", "scrum"],
    "Core CS": ["data structures", "algorithms", "dsa", "oop", "object oriented programming", "dbms",
                "operating systems", "computer networks", "system design", "design patterns"],
}

# Aliases that should count as the same skill in reports.
SKILL_CANONICAL = {
    "react.js": "react", "nodejs": "node.js", "express.js": "express", "vue.js": "vue", "golang": "go",
    "sklearn": "scikit-learn", "postgres": "postgresql", "tailwindcss": "tailwind", "dsa": "data structures",
    "object oriented programming": "oop", "rest api": "rest",
}

ACTION_VERBS = {
    "achieved", "analyzed", "analysed", "architected", "automated", "built", "collaborated", "configured",
    "conducted", "created", "debugged", "delivered", "deployed", "designed", "developed", "directed", "drove",
    "engineered", "enhanced", "established", "evaluated", "executed", "expanded", "improved", "implemented",
    "increased", "integrated", "introduced", "launched", "led", "maintained", "managed", "mentored", "migrated",
    "modernized", "optimized", "optimised", "organized", "owned", "pioneered", "planned", "produced",
    "programmed", "published", "reduced", "refactored", "researched", "resolved", "restructured", "scaled",
    "shipped", "simplified", "solved", "spearheaded", "streamlined", "tested", "trained", "transformed",
    "upgraded", "won", "wrote", "coordinated", "contributed", "fine-tuned", "prototyped", "orchestrated",
}

WEAK_PHRASES = ["responsible for", "worked on", "helped with", "helped in", "involved in", "duties included",
                "various", "etc", "hard working", "hardworking", "team player", "quick learner", "go-getter"]

STOPWORDS = set("""
a an the and or but if then else for to of in on at by with from as is are was were be been being this that
these those it its we you your our their they he she i me my mine will would shall should can could may might
must do does did done have has had not no yes than too very so such into over under about above below also
etc using use used work working job role candidate candidates team teams company experience years year
ability strong good excellent knowledge skills skill required requirements preferred plus including include
responsibilities responsible looking join who what where when how why which all any each other more most
new within across per via based well able must-have nice-to-have etc.
""".split())

BULLET_RE = re.compile(r"^\s*(?:[\u2022\u2023\u25aa\u25cf\u25e6\u2043\u2219\-\*\u27a2\u25ba\u2713\u2714>]|\d+[.)])\s+")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{3,5}\)?[\s-]?)\d{3,5}[\s-]?\d{3,5}")
DATE_RE = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s*'?\d{2,4}\b|\b(?:19|20)\d{2}\b",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|x|k|\+|lpa|cr|users|ms|s\b)|[$\u20b9\u20ac\u00a3]\s*\d|\b\d{2,}\b", re.IGNORECASE)


def _skill_pattern(skill):
    escaped = re.escape(skill)
    # Word boundaries don't work around symbols like c++ / c# / .net
    return re.compile(rf"(?<![\w+#.]){escaped}(?![\w+#])", re.IGNORECASE)


_SKILL_PATTERNS = {s: _skill_pattern(s) for cat in SKILL_TAXONOMY.values() for s in cat}


def find_skills(text):
    """Return {category: [skill, ...]} for every taxonomy skill present in text."""
    found = {}
    seen = set()
    for category, skills in SKILL_TAXONOMY.items():
        for skill in skills:
            canonical = SKILL_CANONICAL.get(skill, skill)
            if canonical in seen:
                continue
            # Single letters like "c" / "r" are too ambiguous outside a skills list.
            if len(skill) == 1 and not re.search(rf"(?:^|[\s,|/:]){re.escape(skill)}(?:$|[\s,|/])", text, re.IGNORECASE | re.MULTILINE):
                continue
            if _SKILL_PATTERNS[skill].search(text):
                seen.add(canonical)
                found.setdefault(category, []).append(canonical)
    return found


def _normalize_header(line):
    return re.sub(r"[^a-z& ]", "", line.lower()).replace("&", "and").strip()


def split_sections(text):
    """Split resume text into {section_name: body}. Text before the first header goes to 'header'."""
    lookup = {alias: name for name, aliases in SECTION_ALIASES.items() for alias in aliases}
    sections = {"header": []}
    current = "header"
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        norm = _normalize_header(line)
        if len(norm.split()) <= 4 and norm in lookup:
            current = lookup[norm]
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {k: "\n".join(v) for k, v in sections.items() if v or k != "header"}


def extract_contact(text, links):
    joined = text + "\n" + "\n".join(links)
    email = EMAIL_RE.search(joined)
    phone = None
    for m in PHONE_RE.finditer(text):
        digits = re.sub(r"\D", "", m.group())
        if 10 <= len(digits) <= 13:
            phone = m.group().strip()
            break
    linkedin = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-%]+", joined, re.IGNORECASE)
    github = re.search(r"(?:https?://)?(?:www\.)?github\.com/[\w\-]+", joined, re.IGNORECASE)
    return {
        "email": email.group() if email else None,
        "phone": phone,
        "linkedin": linkedin.group() if linkedin else None,
        "github": github.group() if github else None,
    }


NOT_NAME_WORDS = {"resume", "curriculum", "vitae", "cv", "student", "engineer", "developer", "profile",
                  "summary", "analyst", "designer", "intern", "scientist", "manager", "consultant"}


def guess_name(text):
    for line in text.splitlines()[:4]:
        line = line.strip()
        words = line.split()
        if not 1 <= len(words) <= 4:
            continue
        if any(w.lower().strip(".,") in NOT_NAME_WORDS for w in words) or line.endswith(":"):
            continue
        norm = _normalize_header(line)
        if any(norm in aliases for aliases in SECTION_ALIASES.values()):
            continue
        if all(w[:1].isalpha() and w[:1].isupper() for w in words) \
                and not EMAIL_RE.search(line) and not any(ch.isdigit() for ch in line):
            return line.title() if line.isupper() else line
    return None


def _bullet_lines(section_text):
    lines = []
    prev_is_bullet = False
    for line in section_text.splitlines():
        stripped = BULLET_RE.sub("", line).strip()
        if not stripped:
            prev_is_bullet = False
            continue
        # A wrapped continuation of the previous bullet (PDFs break long bullets across lines).
        if lines and prev_is_bullet and not BULLET_RE.match(line) and (
                stripped[:1].islower() or not lines[-1].rstrip().endswith((".", "!", "?")))                 and stripped.count("|") < 2 and not DATE_RE.fullmatch(stripped):
            lines[-1] = f"{lines[-1]} {stripped}"
            continue
        # Project/role title rows like "App | Live Demo | GitHub | 2025" are not bullets.
        if stripped.count("|") >= 2:
            prev_is_bullet = False
            continue
        if BULLET_RE.match(line) or (len(stripped.split()) >= 6 and stripped[:1].isupper()):
            lines.append(stripped)
            prev_is_bullet = True
        else:
            prev_is_bullet = False
    return lines


def _leading_verb(bullet):
    """First word of a bullet, looking past a short 'Project name:' prefix."""
    head, sep, tail = bullet.partition(":")
    if sep and len(head.split()) <= 6 and tail.strip():
        bullet = tail.strip()
    words = bullet.split()
    return re.sub(r"[^a-z\-]", "", words[0].lower()) if words else ""


def _is_action_verb(word):
    return word in ACTION_VERBS or (len(word) > 4 and word.endswith("ed"))


def jd_keywords(job_description, limit=25):
    """Pick the terms a recruiter's ATS would search for in this job description."""
    jd = job_description.lower()
    keywords = []
    for skills in find_skills(job_description).values():
        keywords.extend(skills)

    tokens = [t for t in re.findall(r"[a-z][a-z+#.\-]{2,}", jd) if t not in STOPWORDS and not t.endswith(".")]
    counts = Counter(tokens)
    for word, n in counts.most_common(60):
        if n >= 2 and word not in keywords:
            keywords.append(word)
        if len(keywords) >= limit:
            break
    return keywords[:limit]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def _clamp(v):
    return int(max(0, min(100, round(v))))


def parse_resume(text, links=None, pages=1):
    """Structured view of a resume, shared by the ATS checker and question generator."""
    links = links or []
    sections = split_sections(text)
    skills = find_skills(text)
    contact = extract_contact(text, links)

    body_sections = [sections.get(k, "") for k in ("experience", "projects", "activities", "achievements")]
    if not any(body_sections):
        body_sections = [text]
    bullets = [b for s in body_sections for b in _bullet_lines(s)]

    action_bullets = sum(1 for b in bullets if _is_action_verb(_leading_verb(b)))
    quantified = sum(1 for b in bullets if NUMBER_RE.search(b))
    lower = text.lower()
    weak = sorted({p for p in WEAK_PHRASES if re.search(rf"\b{re.escape(p)}\b", lower)})
    pronouns = len(re.findall(r"\b(?:i|me|my)\b", text, re.IGNORECASE))

    level = "fresher"
    if "experience" in sections and len(DATE_RE.findall(sections["experience"])) >= 4:
        level = "experienced"
    elif "experience" in sections:
        level = "intern-level"

    return {
        "name": guess_name(text),
        "contact": contact,
        "sections": sections,
        "sections_found": [k for k in SECTION_ALIASES if k in sections],
        "skills": skills,
        "skills_flat": [s for group in skills.values() for s in group],
        "bullets": bullets,
        "level": level,
        "metrics": {
            "word_count": len(text.split()),
            "pages": pages,
            "bullets": len(bullets),
            "quantified_bullets": quantified,
            "action_verb_bullets": action_bullets,
            "weak_phrases": weak,
            "pronouns": pronouns,
            "dates_found": len(DATE_RE.findall(text)),
        },
    }


def _score_formatting(p, extractable):
    m, c = p["metrics"], p["contact"]
    score, fb = 100, []
    if not extractable:
        return 5, ["No selectable text found. This looks like a scanned or image-based PDF, which most ATS software "
                   "cannot read. Export the resume from Word/Google Docs as a text-based PDF."]

    missing = [s for s in ESSENTIAL_SECTIONS if s not in p["sections"]]
    if "experience" not in p["sections"] and "projects" not in p["sections"]:
        missing.append("experience or projects")
    if missing:
        score -= 15 * len(missing)
        fb.append(f"Missing standard section heading(s): {', '.join(missing)}. ATS parsers look for these exact names.")

    if not c["email"]:
        score -= 15
        fb.append("No email address detected.")
    if not c["phone"]:
        score -= 10
        fb.append("No phone number detected.")
    if not c["linkedin"]:
        score -= 5
        fb.append("Add a LinkedIn profile URL in the header.")

    wc, pages = m["word_count"], m["pages"]
    if wc < 250:
        score -= 20
        fb.append(f"Only {wc} words. The resume is too thin to rank well; aim for 400-800 words.")
    elif wc > 1100 or pages > 2:
        score -= 10
        fb.append(f"{wc} words across {pages} page(s). Trim to 1 page (student) or 2 pages (experienced).")

    if m["pronouns"] > 3:
        score -= 5
        fb.append(f"Found {m['pronouns']} first-person pronouns (I/me/my). Resumes read better without them.")

    if not fb:
        fb.append("Clean structure: standard headings, contact details and a sensible length.")
    return _clamp(score), fb


def _score_experience(p):
    m = p["metrics"]
    n = m["bullets"]
    fb = []
    if n == 0:
        return 30, ["No bullet points found under Experience/Projects. Describe each role or project in 2-4 bullets."]

    quant_ratio = m["quantified_bullets"] / n
    verb_ratio = m["action_verb_bullets"] / n
    score = 35 + quant_ratio * 35 + verb_ratio * 30 - 4 * len(m["weak_phrases"])

    fb.append(f"{m['quantified_bullets']} of {n} bullet points include a measurable result.")
    if quant_ratio < 0.4:
        fb.append("Quantify impact: users served, % improvement, time saved, accuracy reached, dataset size.")
    fb.append(f"{m['action_verb_bullets']} of {n} bullet points start with a strong action verb.")
    if verb_ratio < 0.6:
        fb.append("Start bullets with verbs such as Built, Designed, Reduced or Deployed instead of descriptions.")
    if m["weak_phrases"]:
        fb.append(f"Replace vague phrases: {', '.join(m['weak_phrases'])}.")
    if "experience" in p["sections"] and m["dates_found"] < 2:
        score -= 10
        fb.append("Add start and end dates (Mon YYYY - Mon YYYY) to every role.")
    return _clamp(score), fb


def _score_skills(p):
    skills, n = p["skills"], len(p["skills_flat"])
    fb = []
    score = min(40, n * 2.5) + min(20, len(skills) * 4)
    if "skills" in p["sections"]:
        score += 15
    else:
        fb.append("Add a dedicated Skills section so parsers can map your skills reliably.")

    # Skills that appear in experience/projects are backed by evidence.
    evidence_text = (p["sections"].get("experience", "") + "\n" + p["sections"].get("projects", "")).lower()
    backed = [s for s in p["skills_flat"] if _SKILL_PATTERNS.get(s, _skill_pattern(s)).search(evidence_text)]
    if n:
        fb.append(f"Detected {n} recognised skills across {len(skills)} categories.")
        if evidence_text.strip():
            fb.append(f"{len(backed)} of them are backed by a project or role description.")
            if len(backed) < n / 2:
                fb.append("Mention your key skills inside project/experience bullets, not only in the skills list.")
    else:
        fb.append("No widely recognised technical skills detected. Name specific languages, frameworks and tools.")
    if n:
        score += 25 * (len(backed) / n if evidence_text.strip() else 0.4)
    if n > 35:
        score -= 10
        fb.append("The skills list is very long. Keep the 15-25 skills you can defend in an interview.")
    return _clamp(score), fb, backed


def _score_keywords(p, text, job_description):
    if job_description.strip():
        keywords = jd_keywords(job_description)
        lower = text.lower()
        matched = [k for k in keywords if _skill_pattern(k).search(lower)]
        missing = [k for k in keywords if k not in matched]
        rate = len(matched) / len(keywords) if keywords else 0
        fb = [f"Matches {len(matched)} of {len(keywords)} key terms from the job description."]
        if missing:
            fb.append(f"Missing terms: {', '.join(missing[:10])}. Add the ones you genuinely have.")
        return _clamp(20 + rate * 80), fb, matched, missing

    n = len(p["skills_flat"])
    fb = ["No job description provided, so the score reflects general keyword coverage.",
          "Paste a job description to see exactly which terms you are missing."]
    # Without a target role we can't confirm relevance, so cap at 85.
    return _clamp(25 + min(60, n * 2.5)), fb, p["skills_flat"], []


def _llm_review(text, parsed, sections, job_description):
    schema = {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "suggestions": {"type": "array", "items": {"type": "string"}},
            "bullet_rewrites": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"original": {"type": "string"}, "improved": {"type": "string"}},
                    "required": ["original", "improved"],
                },
            },
        },
        "required": ["summary", "suggestions", "bullet_rewrites"],
    }
    weakest = [b for b in parsed["bullets"] if not NUMBER_RE.search(b)][:4] or parsed["bullets"][:4]
    facts = {
        "scores": {k: v["score"] for k, v in sections.items()},
        "skills": parsed["skills_flat"][:30],
        "sections_found": parsed["sections_found"],
        "metrics": parsed["metrics"],
    }
    example = {
        "summary": "Reads as a capable student developer with two relevant full-stack projects, but most bullets "
                   "describe tasks rather than results, and cloud skills are listed without evidence.",
        "suggestions": [
            "Add the number of users or requests your Flask API handled to the Task Manager project.",
            "Move 'Docker' from the skills list into the deployment bullet where you actually used it.",
        ],
        "bullet_rewrites": [{
            "original": "Worked on the frontend of an e-commerce site using React.",
            "improved": "Built the React checkout flow for an e-commerce site, cutting page load time by [X%].",
        }],
    }
    user = (
        f"RESUME TEXT:\n{text[:3000]}\n\n"
        f"AUTOMATED CHECKS:\n{facts}\n\n"
        + (f"TARGET JOB DESCRIPTION:\n{job_description[:1000]}\n\n" if job_description.strip() else "")
        + "BULLETS TO REWRITE:\n" + "\n".join(f"- {b}" for b in weakest) + "\n\n"
        "Write a two-sentence summary of how this resume reads to a recruiter, five one-sentence suggestions that "
        "refer to actual content in the resume, and a stronger rewrite of each listed bullet.\n"
        "Strict rule: never invent numbers, tools, platforms or results that are not in the resume. Where a metric "
        "would help, use a placeholder such as [X%], [N users] or [X ms].\n\n"
        f"Example of the expected style (for a different resume):\n{json.dumps(example)}"
    )
    system = ("You are a senior technical recruiter who reviews resumes for ATS readiness. "
              "Be specific and concrete, and stay truthful to the resume.")
    return llm.chat_json(system, user, schema, task="ats_review", temperature=0.3, max_tokens=700)


ACTIONABLE_START = {"add", "replace", "quantify", "start", "trim", "mention", "missing", "name", "keep",
                    "export", "remove", "describe"}


def _strip_invented_numbers(improved, resume_text):
    """Replace figures the model made up (not present in the resume) with an [X] placeholder."""
    def digits(s):
        return re.sub(r"(?<=\d),(?=\d)", "", s)

    known = set(re.findall(r"\d+(?:\.\d+)?", digits(resume_text)))

    def check(m):
        value = re.search(r"\d+(?:\.\d+)?", digits(m.group())).group()
        return m.group() if value in known else "[X]"

    parts = re.split(r"(\[[^\]]*\])", improved)  # leave existing placeholders untouched
    return "".join(p if p.startswith("[") else re.sub(r"(?<![\w.])\d[\d,]*(?:\.\d+)?", check, p) for p in parts)


def _is_actionable(item):
    """Feedback lines that tell the user to do something (vs. status lines like '12 of 14 bullets...')."""
    first = item.split()[0].lower().strip(":,.") if item.split() else ""
    return first in ACTIONABLE_START or item.startswith(("No email", "No phone", "No bullet", "No selectable",
                                                         "No widely"))


def analyze_resume(text, job_description="", links=None, pages=1, extractable=True, use_llm=True):
    """Full ATS analysis. Result keeps the original API shape and adds `details`."""
    job_description = job_description or ""
    p = parse_resume(text, links, pages)

    fmt_score, fmt_fb = _score_formatting(p, extractable)
    exp_score, exp_fb = _score_experience(p)
    skl_score, skl_fb, backed = _score_skills(p)
    kw_score, kw_fb, matched, missing = _score_keywords(p, text, job_description)

    if not extractable:
        exp_score = skl_score = kw_score = 0

    sections = {
        "keywords": {"score": kw_score, "feedback": kw_fb},
        "formatting": {"score": fmt_score, "feedback": fmt_fb},
        "experience": {"score": exp_score, "feedback": exp_fb},
        "skills": {"score": skl_score, "feedback": skl_fb},
    }
    overall = _clamp(kw_score * 0.30 + exp_score * 0.30 + fmt_score * 0.20 + skl_score * 0.20)

    # Deterministic suggestions ordered by weakest section first.
    suggestions = []
    for name, data in sorted(sections.items(), key=lambda kv: kv[1]["score"]):
        for item in data["feedback"]:
            if _is_actionable(item):
                suggestions.append(item)
    summary, rewrites, llm_used = None, [], False

    if use_llm and extractable:
        try:
            review = _llm_review(text, p, sections, job_description)
            summary = review.get("summary") or None
            ai_suggestions = [s for s in review.get("suggestions", []) if isinstance(s, str) and s.strip()]
            suggestions = ai_suggestions + [s for s in suggestions if s not in ai_suggestions]
            rewrites = [{"original": r["original"], "improved": _strip_invented_numbers(r["improved"], text)}
                        for r in review.get("bullet_rewrites", [])
                        if isinstance(r, dict) and r.get("original") and r.get("improved")][:4]
            llm_used = True
        except Exception as e:
            print(f"[resume] LLM review skipped: {e}")

    if summary is None:
        if overall >= 80:
            summary = "This resume is well structured for ATS software. Focus on tailoring keywords to each application."
        elif overall >= 60:
            summary = "The resume parses correctly but under-sells your impact. Quantified results and tailored keywords will lift it."
        else:
            summary = "Several structural issues will cost you in automated screening. Fix the formatting items first, then strengthen bullet points."

    return {
        "overallScore": overall,
        "sections": sections,
        "suggestions": suggestions[:8],
        "summary": summary,
        "bullet_rewrites": rewrites,
        "llm_used": llm_used,
        "details": {
            "name": p["name"],
            "contact": p["contact"],
            "sections_found": p["sections_found"],
            "sections_missing": [s for s in ["summary", "experience", "education", "skills", "projects"]
                                 if s not in p["sections"]],
            "skills_by_category": p["skills"],
            "skills_backed_by_evidence": backed,
            "matched_keywords": matched,
            "missing_keywords": missing,
            "metrics": p["metrics"],
            "job_description_used": bool(job_description.strip()),
        },
    }
