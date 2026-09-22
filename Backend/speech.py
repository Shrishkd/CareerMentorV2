"""Speech-to-text with a locally running Whisper model (requires ffmpeg on PATH)."""
import os
import threading

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")

_model = None
_load_error = None
_loaded = threading.Event()


def _load():
    global _model, _load_error
    try:
        import whisper
        _model = whisper.load_model(WHISPER_MODEL)
        print(f"[speech] whisper '{WHISPER_MODEL}' loaded")
    except Exception as e:
        _load_error = str(e)
        print(f"[speech] whisper unavailable: {e}")
    finally:
        _loaded.set()


def preload():
    threading.Thread(target=_load, daemon=True).start()


def status():
    return {"model": WHISPER_MODEL, "ready": _model is not None, "error": _load_error}


def transcribe(path):
    """Return the transcript text, or raise RuntimeError with a readable reason."""
    if not _loaded.is_set():
        _loaded.wait(timeout=300)
    if _model is None:
        raise RuntimeError(f"Speech recognition is unavailable: {_load_error or 'model not loaded'}")
    if not os.path.exists(path) or os.path.getsize(path) < 1000:
        raise RuntimeError("The recording was empty. Check that the correct microphone is selected.")
    result = _model.transcribe(path, language="en", task="transcribe", fp16=False)
    return (result.get("text") or "").strip()
