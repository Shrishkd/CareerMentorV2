"""
Local LLM client (Ollama).

All model calls in the app go through `chat_json`, which asks Ollama for output
constrained to a JSON schema, so responses parse reliably even on small models.

Every successful call is appended to data/finetune/interactions.jsonl in chat
format. Curate that file and use it with finetune/train_qlora.py to fine-tune
the model on your own interview data.
"""
import json
import os
import threading
import time
from datetime import datetime

import requests

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:4b")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "300"))
LLM_CONTEXT = int(os.getenv("LLM_CONTEXT", "4096"))
LLM_KEEP_ALIVE = os.getenv("LLM_KEEP_ALIVE", "30m")
LOG_INTERACTIONS = os.getenv("LLM_LOG_INTERACTIONS", "1") == "1"

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
FINETUNE_LOG = os.path.join(_PROJECT_ROOT, "data", "finetune", "interactions.jsonl")
_log_lock = threading.Lock()


class LLMError(RuntimeError):
    pass


def status():
    """Report whether Ollama is reachable and the configured model is pulled."""
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=3)
        r.raise_for_status()
        names = [m.get("name", "") for m in r.json().get("models", [])]
        wanted = LLM_MODEL if ":" in LLM_MODEL else f"{LLM_MODEL}:latest"
        return {"reachable": True, "model": LLM_MODEL, "model_available": wanted in names}
    except Exception as e:
        return {"reachable": False, "model": LLM_MODEL, "model_available": False, "error": str(e)}


def warm_up():
    """Load the model into memory in the background so the first request is fast."""
    def _run():
        try:
            requests.post(
                f"{OLLAMA_HOST}/api/generate",
                json={"model": LLM_MODEL, "prompt": "", "keep_alive": LLM_KEEP_ALIVE},
                timeout=LLM_TIMEOUT,
            )
            print(f"[llm] {LLM_MODEL} loaded")
        except Exception as e:
            print(f"[llm] warm-up skipped: {e}")

    threading.Thread(target=_run, daemon=True).start()


def _log(task, messages, content):
    if not LOG_INTERACTIONS:
        return
    record = {
        "ts": datetime.utcnow().isoformat(),
        "task": task,
        "model": LLM_MODEL,
        "messages": messages + [{"role": "assistant", "content": content}],
    }
    try:
        os.makedirs(os.path.dirname(FINETUNE_LOG), exist_ok=True)
        with _log_lock, open(FINETUNE_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[llm] could not write interaction log: {e}")


def chat_json(system, user, schema, task="general", temperature=0.3, max_tokens=900, retries=1):
    """
    Send one chat turn and return the parsed JSON object.
    Raises LLMError if the model is unreachable or never returns valid JSON.
    """
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    body = {
        "model": LLM_MODEL,
        "messages": messages,
        "stream": False,
        "format": schema,
        # Qwen3 is a hybrid reasoning model; thinking tokens are slow on CPU and
        # not needed for structured grading. Ignored by models without it.
        "think": False,
        "keep_alive": LLM_KEEP_ALIVE,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": LLM_CONTEXT,
        },
    }

    last_err = None
    for attempt in range(retries + 1):
        started = time.time()
        try:
            r = requests.post(f"{OLLAMA_HOST}/api/chat", json=body, timeout=LLM_TIMEOUT)
            if r.status_code == 400 and "think" in r.text:
                # Older Ollama builds reject the think flag for non-thinking models.
                body.pop("think", None)
                r = requests.post(f"{OLLAMA_HOST}/api/chat", json=body, timeout=LLM_TIMEOUT)
            r.raise_for_status()
            content = r.json().get("message", {}).get("content", "").strip()
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError("model returned JSON that is not an object")
            print(f"[llm] {task} ok in {time.time() - started:.1f}s")
            _log(task, messages, content)
            return parsed
        except requests.exceptions.ConnectionError as e:
            raise LLMError(
                f"Cannot reach Ollama at {OLLAMA_HOST}. Start it with `ollama serve`."
            ) from e
        except Exception as e:
            last_err = e
            print(f"[llm] {task} attempt {attempt + 1} failed: {e}")
    raise LLMError(f"{task} failed: {last_err}")
