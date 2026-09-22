# Career Mentor

Mock interviews built from your resume. Upload a resume, answer five questions about the projects and skills on it (three conceptual, two coding), and get a graded report with model answers plus an activity report from your webcam. A separate resume checker scores ATS readiness against a job description.

Everything AI runs locally on open-source models. There are no accounts and no paid APIs.

| Part | Technology |
| --- | --- |
| Frontend | React 18, TypeScript, Vite, Tailwind, shadcn/ui, Monaco editor, Recharts |
| Backend | Flask |
| Language model | Qwen3-4B via [Ollama](https://ollama.com) (any Ollama model works) |
| Speech-to-text | OpenAI Whisper (local) |
| Activity monitoring | MediaPipe face mesh, pose and hands on frames sent by the browser |
| Reports | ReportLab + Matplotlib |

## How it works

```
Browser                               Flask backend                       Ollama
───────                               ─────────────                       ──────
Upload resume  ─────────────────────► parse resume (PyMuPDF / DOCX)
                                      generate 5 questions  ─────────────► qwen3:4b
Answer by voice / text / code  ─────► queue ──► Whisper ──► grade  ──────► qwen3:4b
Webcam frame every 2.5 s  ──────────► MediaPipe: gaze, posture, faces
Tab switches  ──────────────────────► logged on the session
Finish  ────────────────────────────► final assessment ─────────────────► qwen3:4b
                                      interview PDF + activity PDF
```

Grading runs in a background queue, so the candidate moves straight to the next question while earlier answers are transcribed and scored.

## Running locally

**Prerequisites:** Python 3.11, Node 18+, [ffmpeg](https://ffmpeg.org) on PATH, and Ollama.

```bash
# 1. Model
ollama pull qwen3:4b

# 2. Backend
cd Backend
python -m venv ../.venv && ../.venv/Scripts/activate   # macOS/Linux: source ../.venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python backend_api.py                                   # http://localhost:8000

# 3. Frontend (new terminal)
cd Frontend
npm install
npm run dev                                             # http://localhost:8080
```

The dashboard's **Local AI status** panel shows whether Ollama, Whisper and MediaPipe are ready.

### Configuration (`Backend/.env`)

| Variable | Default | Notes |
| --- | --- | --- |
| `LLM_MODEL` | `qwen3:4b` | Any Ollama model name, e.g. `qwen3:4b-instruct-2507-q4_K_M` or your fine-tuned `career-mentor` |
| `OLLAMA_HOST` | `http://127.0.0.1:11434` | |
| `LLM_TIMEOUT` | `300` | Seconds per model call. CPU inference is slow. |
| `WHISPER_MODEL` | `small` | `base` is about twice as fast, `small` is more accurate |
| `LLM_LOG_INTERACTIONS` | `1` | Saves prompts and responses for fine-tuning |

`Frontend/.env` accepts `VITE_API_URL` (empty uses the Vite proxy) and an optional `VITE_RAPIDAPI_KEY` for the Judge0 "Run code" button.

## Choosing and fine-tuning the model

The default is **Qwen3-4B**. On an 8 GB RAM laptop without a GPU it is the best balance of quality and speed among small open models: it returns valid structured JSON reliably, follows grading rubrics well, fits in about 2.5 GB at 4-bit, and is Apache-2.0 licensed with first-class fine-tuning support. Expect about 60 seconds to grade one answer on a CPU. `llama3.2:3b` is faster but noticeably shallower as a grader.

To fine-tune on your own interviews:

1. Use the app. Every model call is logged to `data/finetune/interactions.jsonl`.
2. `python finetune/prepare_dataset.py` writes `review.jsonl`. Correct weak responses and mark bad ones `"keep": false`.
3. `python finetune/prepare_dataset.py --use-review` writes `train.jsonl` and `val.jsonl`.
4. Run `finetune/train_qlora.py` on a free Colab or Kaggle GPU (QLoRA with Unsloth, exports GGUF).
5. `ollama create career-mentor -f finetune/Modelfile`, then set `LLM_MODEL=career-mentor`.

## Project structure

```
Backend/
  backend_api.py       Flask routes, session store, grading queue, local stats
  llm.py               Ollama client with JSON-schema output + interaction logging
  interview_engine.py  question generation, rubric grading, final assessment
  resume_analyzer.py   PDF/DOCX parsing, section/skill detection, deterministic ATS scoring
  monitoring.py        webcam frame analysis (gaze, posture, faces, hands)
  speech.py            Whisper transcription
  reports.py           interview, activity and ATS PDFs
Frontend/src/
  pages/               Index, Dashboard, ResumeUpload, GrantPermissions, Interview, InterviewResults, ATSChecker
  lib/api.ts           typed API client
  lib/profile.ts       anonymous local profile (replaces login)
finetune/              dataset builder, QLoRA training script, Ollama Modelfile
```

## Deployment

`Backend/Dockerfile` builds the API. It expects an Ollama server reachable at `OLLAMA_HOST`. Free hosting tiers such as Render's cannot run a 4B model, so host the backend on a machine with at least 8 GB RAM, or point `OLLAMA_HOST` at a GPU box. The frontend is a static build (`npm run build`, publish `Frontend/dist`) with `VITE_API_URL` set to the backend URL.

## Author

**Shrish Das** · [shrish-portfolio.netlify.app](https://shrish-portfolio.netlify.app)

MIT License.
