import os
import sys
import tempfile
import wave
import numpy as np
import sounddevice as sd
import threading
import time

# Import libraries
import fitz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pyttsx3
from datetime import datetime
from dotenv import load_dotenv
import re
from fpdf import FPDF
import json
import speech_recognition as sr


GENAI_AVAILABLE = False
try:
    import google.generativeai as genai
    
    load_dotenv(override=True) 
    
    api_key =os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        GENAI_AVAILABLE = True
        print("✅ Gemini API configured")
    else:
        print("❌ No Gemini API key found in env. Set GOOGLE_API_KEY to enable Gemini.")
except Exception:
    GENAI_AVAILABLE = False
    print("❌ google.generativeai library not available (pip install google-generativeai).")

DEFAULT_MODEL_NAME = "gemini-2.5-flash"

# Try importing whisper
try:
    import whisper
    print("✅ Whisper imported successfully")
    print("🔄 Loading Whisper model...")
    whisper_model = whisper.load_model("small")
    print("✅ Whisper model loaded successfully!")
    WHISPER_AVAILABLE = True
except Exception as e:
    print(f"❌ Whisper setup failed: {e}")
    whisper_model = None
    WHISPER_AVAILABLE = False

# ========== Enhanced Gemini Setup ==========
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ GEMINI_API_KEY not found in environment variables")
    api_key = input("Please enter your Gemini API key: ").strip()


# ========== Global variables for smart recording ==========
is_recording = False
silence_duration = 0
max_silence_before_stop = 3.0
min_answer_duration = 5.0
audio_buffer = []

# ========== PDF Handling ==========
def select_pdf_file():
    """Select a PDF file path.
    On server (Render), tkinter is not available, so fallback to input().
    """
    try:
        # In headless environments, just ask for manual input
        pdf_path = input("📂 Enter the path to your resume PDF: ").strip()
        return pdf_path
    except Exception as e:
        print(f"⚠️ Error selecting file: {e}")
        return ""


def extract_text_from_pdf(pdf_path):
    try:
        with fitz.open(pdf_path) as doc:
            text = "\n".join([page.get_text("text") for page in doc])
        return text.strip()
    except Exception as e:
        print(f"❌ Error extracting text from PDF: {e}")
        return ""

# ========== Enhanced Gemini LLM Calls ==========
def call_llm(prompt, temperature=0.7, max_tokens=2048, model_name=DEFAULT_MODEL_NAME):
    """Call Gemini LLM safely with modern API"""
    if not GENAI_AVAILABLE:
        return "⚠️ Gemini not available — running fallback mode."

    try:
        print("🔄 Calling Gemini API...")
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
        )
        response = model.generate_content(prompt)
        
        if not response or not response.candidates:
            return "No response from Gemini."

        # Safely extract text from first candidate
        parts = []
        for c in response.candidates:
            for p in c.content.parts:
                if p.text:
                    parts.append(p.text)
        result = "\n".join(parts).strip()

        # Remove ```json or ``` fences if present
        if result.startswith("```"):
            result = result.split("```")[1].replace("json", "").strip()

        print("✅ Gemini API call successful")
        return result or "No response text."
    except Exception as e:
        print(f"❌ Error calling Gemini API: {e}")
        return f"Error calling Gemini: {e}"


def generate_questions_from_resume(resume_text):
    prompt = f"""
As an expert technical interviewer, analyze the following resume and generate exactly 5 highly relevant, industry-standard interview questions. Make them specific to the candidate's background:

RESUME:
{resume_text}

REQUIREMENTS:
- Generate exactly 5 questions
- 3 theoretical/conceptual questions related to their field
- 2 coding/problem-solving questions in Python or C/C++ in DSA
- Questions should be easy but fair
- Focus on their mentioned skills and experience level
- Do not include any introduction text or explanatory headers
- Start directly with Question 1

FORMAT:
1. [First theoretical question]
2. [Second theoretical question]  
3. [Third theoretical question]
4. [First coding question]
5. [Second coding question]

Return ONLY the numbered questions, nothing else:
"""
    
    print("🔄 Generating questions from resume...")
    response = call_llm(prompt, temperature=0.8)
    print(f"✅ Questions generated successfully")
    return response

def parse_questions_properly(questions_text):
    """Parse questions and remove any introductory text"""
    lines = questions_text.split('\n')
    questions = []
    
    for line in lines:
        line = line.strip()
        # Look for lines that start with numbers (1., 2., etc.) or **
        if re.match(r'^\d+\.', line) or line.startswith('**'):
            # Clean up the question
            question = re.sub(r'^\d+\.\s*', '', line)  # Remove number prefix
            question = re.sub(r'^\*\*[^*]*\*\*:?\s*', '', question)  # Remove **Theoretical:** etc.
            question = question.strip()
            
            # Only add substantial qustions (not headers or intro text)
            if len(question) > 20 and not any(skip_word in question.lower() for skip_word in 
                                            ['here are', 'questions for', 'tailored to', 'interview questions']):
                questions.append(question)
    
    return questions[:5]  # Return only first 5 questions

def enhanced_evaluate_answer(question, answer, resume_context=""):
    """Enhanced evaluation using Gemini with detailed analysis and explanations"""
    
    prompt = f"""
As an expert technical interviewer, evaluate this candidate's answer comprehensively and provide detailed explanations.

QUESTION: {question}

CANDIDATE'S ANSWER: {answer}

CANDIDATE BACKGROUND: {resume_context[:500]}...

EVALUATION CRITERIA:
1. Technical Accuracy (0-25 points)
2. Completeness & Depth (0-25 points) 
3. Communication Clarity (0-20 points)
4. Problem-Solving Approach (0-20 points)
5. Relevance to Role (0-10 points)

ANALYSIS REQUIREMENTS:
- Provide specific technical feedback with detailed explanations
- Explain WHY the answer is good or bad with concrete examples
- Identify specific strengths and weaknesses with reasoning
- Give actionable improvement suggestions
- Consider the candidate's experience level
- Provide detailed explanation of the scoring rationale

RESPONSE FORMAT (STRICT JSON):
{{
    "overall_score": 75,
    "category_scores": {{
        "technical_accuracy": 18,
        "completeness": 20, 
        "communication": 15,
        "problem_solving": 16,
        "relevance": 6
    }},
    "strengths": ["Shows good understanding of core concepts", "Provided specific examples"],
    "weaknesses": ["Could explain more details", "Missing some advanced concepts"],
    "detailed_feedback": "The candidate demonstrates solid foundational knowledge but could benefit from deeper technical explanations.",
    "detailed_explanation": "This answer is scored 75/100 because: Technical accuracy is strong (18/25) as the candidate correctly identified key concepts and provided accurate information about the topic. However, completeness could be improved (20/25) as some important aspects were not fully addressed. Communication was clear (15/20) with good structure, though some technical terms could be better explained. The problem-solving approach (16/20) showed logical thinking but lacked some depth in analysis. Overall, this demonstrates good competency with room for improvement in technical depth and comprehensive coverage of the topic.",
    "improvement_suggestions": ["Practice explaining complex concepts simply", "Include more real-world examples", "Expand on technical details"],
    "interviewer_notes": "Good potential, needs some development in communication",
    "follow_up_questions": ["Can you explain the implementation details?", "How would you optimize this solution?"]
}}
"""
    
    print(f"🔄 Evaluating answer using Gemini...")
    response = call_llm(prompt, temperature=0.3, max_tokens=3000)
    
    try:
        # Clean the response to ensure valid JSON
        response_clean = response.strip()
        if response_clean.startswith("```"):
            response_clean = response_clean[7:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        response_clean = response_clean.strip()
        
        print(f"🔍 Attempting to parse JSON response...")
        evaluation = json.loads(response_clean)
        print(f"✅ Successfully parsed evaluation")
        print(f"📊 Score: {evaluation.get('overall_score', 'N/A')}/100")
        
        # Validate and ensure all required fields exist
        required_keys = ["overall_score", "category_scores", "strengths", "weaknesses", "detailed_feedback", "detailed_explanation"]
        for key in required_keys:
            if key not in evaluation:
                if key == "detailed_explanation":
                    evaluation[key] = f"This answer received a score of {evaluation.get('overall_score', 50)}/100. The evaluation is based on technical accuracy, completeness, communication clarity, problem-solving approach, and relevance to the role."
                elif key == "overall_score":
                    evaluation[key] = 60
                elif key == "category_scores":
                    evaluation[key] = {"technical_accuracy": 12, "completeness": 12, "communication": 12, "problem_solving": 12, "relevance": 6}
        
        
        return evaluation
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")
        print(f"🔍 Raw response: {response[:300]}...")
        
        # Extract score using regex as fallback
        score_match = re.search(r'"overall_score":\s*(\d+)', response)
        score = int(score_match.group(1)) if score_match else 60
        
        print(f"📊 Extracted score using regex: {score}")
        
        # Return fallback evaluation structure with explanation
        return {
            "overall_score": score,
            "category_scores": {
                "technical_accuracy": int(score * 0.25),
                "completeness": int(score * 0.25),
                "communication": int(score * 0.20),
                "problem_solving": int(score * 0.20),
                "relevance": int(score * 0.10)
            },
            "strengths": ["Provided a response to the question"],
            "weaknesses": ["Could provide more comprehensive answers"],
            "detailed_feedback": f"The candidate provided an answer with an estimated quality score of {score}/100. The response shows effort but could be improved with more detail and technical depth.",
            "detailed_explanation": f"This answer received {score}/100 points. The evaluation is based on several factors: technical accuracy, completeness of the response, clarity of communication, problem-solving approach, and relevance to the role. While the candidate attempted to answer the question, there are opportunities for improvement in providing more comprehensive and detailed responses with better technical depth and clearer explanations.",
            "improvement_suggestions": [
                "Provide more detailed explanations",
                "Include specific examples",
                "Structure answers more clearly"
            ],
            "interviewer_notes": "Evaluation generated using fallback method due to response parsing issues",
            "follow_up_questions": ["Can you elaborate on that?", "What specific experience do you have with this?"]
        }
        
def evaluate_code_answer(question, code_text, resume_context=""):
    """Specialized evaluation for coding interview answers using Gemini with detailed explanations."""

    prompt = f"""
As a senior software engineering interviewer, evaluate the candidate's coding solution.

QUESTION: {question}

CANDIDATE'S CODE:
{code_text}

CANDIDATE BACKGROUND: {resume_context[:500]}...

EVALUATION CRITERIA:
1. Correctness (0-40 points)
2. Efficiency (0-20 points)
3. Code Quality (0-15 points)
4. Edge Cases (0-15 points)
5. Communication (0-10 points)

RESPONSE FORMAT (STRICT JSON ONLY, no markdown, no commentary):
{{
  "overall_score": 80,
  "category_scores": {{
    "correctness": 30,
    "efficiency": 15,
    "code_quality": 12,
    "edge_cases": 10,
    "communication": 8
  }},
  "strengths": ["Implements correct algorithm", "Readable structure"],
  "weaknesses": ["No edge case handling", "Could optimize further"],
  "detailed_feedback": "The code solves the problem but misses edge cases.",
  "detailed_explanation": "Overall score 80/100: correctness strong, misses edge cases.",
  "improvement_suggestions": ["Add edge case handling", "Optimize loops"],
  "interviewer_notes": "Candidate shows strong fundamentals.",
  "follow_up_questions": ["What is the time complexity?", "How would you handle invalid inputs?"]
}}
"""

    print("🔄 Evaluating CODE answer using Gemini...")
    response = call_llm(prompt, temperature=0.3, max_tokens=3000)

    try:
        response_clean = response.strip()

        # ✅ Strip Markdown fences if present
        if response_clean.startswith("```"):
            parts = response_clean.split("```")
            for p in parts:
                if "{" in p and "}" in p:
                    response_clean = p
                    break

        # ✅ Remove possible "json" hints
        response_clean = response_clean.replace("json", "").strip()

        # ✅ Try to parse
        evaluation = json.loads(response_clean)

        print(f"✅ Parsed code evaluation. Score: {evaluation.get('overall_score', 'N/A')}/100")

        # Ensure required fields exist
        required_keys = [
            "overall_score", "category_scores", "strengths",
            "weaknesses", "detailed_feedback", "detailed_explanation",
            "improvement_suggestions", "interviewer_notes", "follow_up_questions"
        ]
        for key in required_keys:
            if key not in evaluation:
                evaluation[key] = [] if isinstance(evaluation.get(key), list) else "N/A"

        return evaluation

    except Exception as e:
        print("⚠️ evaluate_code_answer error:", e)
        return {
            "overall_score": 50,
            "category_scores": {},
            "strengths": [],
            "weaknesses": ["Error parsing AI evaluation"],
            "detailed_feedback": "Evaluation fallback used.",
            "detailed_explanation": str(e),
            "improvement_suggestions": [],
            "interviewer_notes": "",
            "follow_up_questions": []
        }


def analyze_resume_for_ats(resume_text, job_description=""):
    """
    Use Gemini to analyze resume for ATS compatibility and return structured JSON
    matching the frontend `ATSResult` interface.
    """
    # Truncate inputs to avoid JSON parsing issues
    resume_snippet = resume_text[:1000] if resume_text else ""
    job_snippet = job_description[:500] if job_description else ""
    
    # Simple prompt with example JSON structure to guide response
    prompt = f"""Analyze this resume for ATS compatibility. Return ONLY a JSON object with this exact structure, no extra text:
{{"overallScore": 85, "sections": {{"keywords": {{"score": 85, "feedback": ["keyword1", "keyword2"]}}, "formatting": {{"score": 82, "feedback": ["tip1", "tip2"]}}, "experience": {{"score": 80, "feedback": ["tip1", "tip2"]}}, "skills": {{"score": 88, "feedback": ["tip1", "tip2"]}}}}, "suggestions": ["suggestion1", "suggestion2"]}}

Resume: {resume_snippet}

Job role: {job_snippet}

Provide scores 0-100 and brief 2-3 word feedback items."""

    print("🔄 Analyzing resume for ATS compatibility using Gemini...")
    response = call_llm(prompt, temperature=0.1, max_tokens=800)

    resp = response.strip()
    
    # Find JSON object
    if "{" in resp and "}" in resp:
        start_idx = resp.find("{")
        end_idx = resp.rfind("}")
        if start_idx >= 0 and end_idx > start_idx:
            resp = resp[start_idx:end_idx+1]

    try:
        parsed = json.loads(resp)
        if "overallScore" not in parsed:
            parsed["overallScore"] = int(parsed.get("overall_score", 50))
        return parsed
    except Exception as e:
        print(f"⚠️ Failed parsing ATS JSON from Gemini: {e}. Using heuristic fallback.")
        # Fallback: heuristic analysis
        keywords_score = 80 if len(re.findall(r"\b(engineer|developer|python|javascript|react|node)\b", resume_text.lower())) > 0 else 50
        formatting_score = 85 if len(resume_text.splitlines()) > 20 else 65
        experience_score = 80 if "experience" in resume_text.lower() else 60
        skills_score = 75 if "skills" in resume_text.lower() else 55
        overall = int((keywords_score * 0.35 + formatting_score * 0.2 + experience_score * 0.25 + skills_score * 0.2))

        return {
            "overallScore": overall,
            "sections": {
                "keywords": {"score": keywords_score, "feedback": ["Check keyword alignment", "Add relevant terms"]},
                "formatting": {"score": formatting_score, "feedback": ["Use headers", "Keep simple"]},
                "experience": {"score": experience_score, "feedback": ["Quantify achievements", "Add roles"]},
                "skills": {"score": skills_score, "feedback": ["Use comma-separated", "Be specific"]},
            },
            "suggestions": ["Add relevant keywords", "Simplify formatting for ATS"]
        }

# ========== Keep all your existing audio functions (smart_audio_recording, etc.) ==========
def detect_speech_activity(audio_chunk, threshold=0.01):
    if len(audio_chunk) == 0:
        return False
    rms = np.sqrt(np.mean(audio_chunk ** 2))
    return rms > threshold

def smart_audio_recording(max_duration=120, silence_threshold=3.0, min_duration=5.0):
    global is_recording, audio_buffer
    
    samplerate = 16000
    chunk_duration = 0.1
    chunk_size = int(samplerate * chunk_duration)
    
    audio_buffer = []
    silence_counter = 0.0
    total_duration = 0.0
    
    is_recording = True
    print("🎙️ Recording started... Speak your answer!")
    print(f"📍 Will auto-stop after {silence_threshold}s of silence (minimum {min_duration}s)")
    
    try:
        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            audio_buffer.append(indata.copy())
        
        with sd.InputStream(samplerate=samplerate, channels=1, 
                           callback=audio_callback, blocksize=chunk_size):
            
            while is_recording and total_duration < max_duration:
                time.sleep(chunk_duration)
                total_duration += chunk_duration
                
                if len(audio_buffer) > 0:
                    latest_chunk = audio_buffer[-1].flatten()
                    has_speech = detect_speech_activity(latest_chunk, threshold=0.015)
                    
                    if has_speech:
                        silence_counter = 0.0
                        print("🗣️", end="", flush=True)
                    else:
                        silence_counter += chunk_duration
                        if silence_counter > 0.5:
                            print(".", end="", flush=True)
                    
                    if (total_duration >= min_duration and 
                        silence_counter >= silence_threshold):
                        print(f"\n⏹️ Auto-stopped after {silence_threshold}s of silence")
                        break
                
                if int(total_duration) % 5 == 0 and total_duration > 0:
                    remaining = max_duration - total_duration
                    print(f"\n⏱️ {int(total_duration)}s recorded, {int(remaining)}s remaining")
    
    except Exception as e:
        print(f"\n❌ Recording error: {e}")
        return None
    
    finally:
        is_recording = False
    
    print(f"\n✅ Recording completed ({total_duration:.1f}s total)")
    
    if audio_buffer:
        combined_audio = np.concatenate(audio_buffer, axis=0).flatten()
        return combined_audio
    
    return None

def create_temp_wav_file(audio_data, samplerate=16000):
    try:
        temp_fd, temp_path = tempfile.mkstemp(suffix='.wav', prefix='interview_audio_')
        os.close(temp_fd)
        
        if audio_data.dtype != np.int16:
            if audio_data.dtype == np.float32:
                audio_data = np.clip(audio_data, -1.0, 1.0)
                audio_data = (audio_data * 32767).astype(np.int16)
            else:
                audio_data = audio_data.astype(np.int16)
        
        with wave.open(temp_path, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(samplerate)
            wav_file.writeframes(audio_data.tobytes())
        
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            print(f"✅ Created temp audio file: {temp_path} ({os.path.getsize(temp_path)} bytes)")
            return temp_path
        else:
            print(f"❌ Failed to create valid temp file: {temp_path}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating temp WAV file: {e}")
        return None

def transcribe_with_whisper(audio_file_path):
    if not WHISPER_AVAILABLE or not whisper_model:
        print("⚠️ Whisper not available, using Google Speech Recognition")
        return transcribe_with_google_fallback(audio_file_path)
    
    try:
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
        
        file_size = os.path.getsize(audio_file_path)
        if file_size == 0:
            raise ValueError(f"Audio file is empty: {audio_file_path}")
        
        print(f"🔄 Transcribing with Whisper... (File: {file_size} bytes)")
        
        result = whisper_model.transcribe(
            audio_file_path,
            language="en",
            task="transcribe"
        )
        
        transcription = result["text"].strip()
        print(f"📝 Whisper Transcription: '{transcription}'")
        return transcription
        
    except Exception as e:
        print(f"❌ Whisper transcription error: {e}")
        return transcribe_with_google_fallback(audio_file_path)
    
    finally:
        try:
            if os.path.exists(audio_file_path):
                os.remove(audio_file_path)
        except:
            pass

def transcribe_with_google_fallback(audio_file_path):
    recognizer = sr.Recognizer()
    try:
        print("🔄 Using Google Speech Recognition...")
        with sr.AudioFile(audio_file_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
        
        text = recognizer.recognize_google(audio_data)
        print(f"📝 Google Transcription: '{text}'")
        return text
        
    except Exception as e:
        print(f"❌ Fallback transcription error: {e}")
        return ""
    finally:
        try:
            if os.path.exists(audio_file_path):
                os.remove(audio_file_path)
        except:
            pass

def listen_to_answer():
    print("\n" + "="*50)
    print("🎙️ READY TO RECORD YOUR ANSWER")
    print("="*50)
    
    try:
        audio_data = smart_audio_recording(
            max_duration=120,
            silence_threshold=3.0,
            min_duration=5.0
        )
        
        if audio_data is None or len(audio_data) == 0:
            print("❌ No audio data recorded")
            return ""
        
        max_amplitude = np.max(np.abs(audio_data))
        if max_amplitude < 0.005:
            print("⚠️ Audio seems very quiet - please speak louder next time")
        
        temp_audio_path = create_temp_wav_file(audio_data, samplerate=16000)
        if not temp_audio_path:
            print("❌ Failed to create temporary audio file")
            return ""
        
        return transcribe_with_whisper(temp_audio_path)
        
    except Exception as e:
        print(f"❌ Error in listen_to_answer: {e}")
        return ""

def speak_text(text, voice_id=None):
    engine = pyttsx3.init()
    if voice_id:
        engine.setProperty('voice', voice_id)
    engine.setProperty('rate', 150)
    engine.say(text)
    engine.runAndWait()

# ========== Enhanced Report Generation with Detailed Explanations ==========
def create_comprehensive_report(questions, answers, evaluations, final_assessment, resume_text):
    import matplotlib
    try:
        # Use non-interactive backend for server environments
        matplotlib.use('Agg')
    except Exception as e:
        print("⚠️ Could not switch matplotlib backend to Agg:", e)

    print("🔄 Creating comprehensive report with detailed explanations (robust mode)...")

    def clean_text_for_pdf(text):
        """Clean text to remove problematic Unicode characters for PDF generation"""
        replacements = {
            '•': '- ', '✓': '+ ', '✗': '- ', '→': '-> ', '←': '<- ', '↑': '^ ',
            '↓': 'v ', '★': '* ', '☆': '* ', '…': '...', '–': '-', '—': '-',
            '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'", '\u201c': '"',
            '\u201d': '"', '\u2026': '...', '\u2022': '- '
        }
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                text = ""
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text.encode('ascii', 'ignore').decode('ascii')

    # --- Normalise evaluations to a safe structure (defensive) ---
    norm_evals = []
    for ev in (evaluations or []):
        ev_obj = {}
        try:
            if isinstance(ev, str):
                try:
                    ev_obj = json.loads(ev)
                except Exception:
                    ev_obj = {"detailed_feedback": ev}
            elif isinstance(ev, dict):
                ev_obj = ev
            else:
                ev_obj = {"detailed_feedback": str(ev)}
        except Exception:
            ev_obj = {"detailed_feedback": "Invalid evaluation format"}

        safe = {
            "overall_score": int(ev_obj.get("overall_score", 0) or 0),
            "category_scores": ev_obj.get("category_scores", {}) if isinstance(ev_obj.get("category_scores", {}), dict) else {},
            "strengths": ev_obj.get("strengths", []) if isinstance(ev_obj.get("strengths", []), list) else [str(ev_obj.get("strengths", ""))],
            "weaknesses": ev_obj.get("weaknesses", []) if isinstance(ev_obj.get("weaknesses", []), list) else [str(ev_obj.get("weaknesses", ""))],
            "detailed_feedback": ev_obj.get("detailed_feedback", ev_obj.get("detailed_explanation", "No feedback provided.")),
            "detailed_explanation": ev_obj.get("detailed_explanation", ev_obj.get("detailed_feedback", "No detailed explanation available.")),
            "improvement_suggestions": ev_obj.get("improvement_suggestions", []) if isinstance(ev_obj.get("improvement_suggestions", []), list) else [str(ev_obj.get("improvement_suggestions", ""))],
            "interviewer_notes": ev_obj.get("interviewer_notes", ""),
            "follow_up_questions": ev_obj.get("follow_up_questions", [])
        }
        norm_evals.append(safe)

    # Safe score list
    scores = [e.get("overall_score", 0) for e in norm_evals] if norm_evals else []
    avg_score = (sum(scores) / len(scores)) if scores else 0.0

    # Short question labels
    questions_short = [f"Q{i+1}" for i in range(len(questions))]

    # Create performance visualization (Agg backend prevents GUI errors)
    try:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        ax1.plot(questions_short if questions_short else ['Q1'], scores if scores else [0],
                 marker='o', linestyle='-', linewidth=3, markersize=8)
        ax1.set_title('Interview Performance Analysis')
        ax1.set_xlabel('Questions')
        ax1.set_ylabel('Score (%)')
        ax1.set_ylim(0, 100)
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=70, linestyle='--', alpha=0.5, label='Good Performance')
        ax1.axhline(y=50, linestyle='--', alpha=0.5, label='Average Performance')
        ax1.legend()

        for i, score in enumerate(scores):
            ax1.annotate(f'{score}%', (questions_short[i], score), textcoords="offset points", xytext=(0,10), ha='center')

        if norm_evals and isinstance(norm_evals[0].get("category_scores", None), dict) and len(norm_evals[0]["category_scores"]) > 0:
            categories = list(norm_evals[0]["category_scores"].keys())
            category_scores = [norm_evals[0]["category_scores"].get(c, 0) for c in categories]
            ax2.bar(categories, category_scores)
            ax2.set_title('Performance Breakdown (Sample Question)')
            ax2.tick_params(axis='x', rotation=45)
        else:
            ax2.text(0.1, 0.5, "No detailed category scores available", transform=ax2.transAxes)

        plt.tight_layout()
        graph_path = "comprehensive_interview_analysis.png"
        plt.savefig(graph_path, dpi=200, bbox_inches='tight')
        plt.close()
    except Exception as e:
        print("⚠️ Failed to create performance graph:", e)
        graph_path = None

    # Create PDF report (FPDF)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Cover
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=18)
    pdf.cell(0, 12, "COMPREHENSIVE INTERVIEW ASSESSMENT", ln=True, align='C')
    pdf.set_font("Arial", size=11)
    pdf.ln(6)
    pdf.cell(0, 7, f"Date: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}", ln=True)
    pdf.cell(0, 7, f"Average Score: {avg_score:.1f}%", ln=True)
    pdf.ln(6)
    pdf.multi_cell(0, 6, clean_text_for_pdf(final_assessment.get('overall_assessment', 'No overall assessment provided.')))

    # Performance Overview with graph
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(0, 8, "PERFORMANCE OVERVIEW", ln=True)
    pdf.ln(6)
    if graph_path and os.path.exists(graph_path):
        try:
            pdf.image(graph_path, x=10, y=pdf.get_y(), w=190)
            pdf.ln(100)
        except Exception as e:
            print("⚠️ Could not attach graph to PDF:", e)
            pdf.multi_cell(0, 6, "Graph generation was not available.")
    else:
        pdf.multi_cell(0, 6, "No performance graph available.")

    # Key findings
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 8, "KEY STRENGTHS:", ln=True)
    pdf.set_font("Arial", size=10)
    for s in final_assessment.get('key_strengths', []):
        pdf.cell(0, 6, f"- {clean_text_for_pdf(s)}", ln=True)

    pdf.ln(4)
    pdf.set_font("Arial", style='B', size=12)
    pdf.cell(0, 8, "DEVELOPMENT AREAS:", ln=True)
    pdf.set_font("Arial", size=10)
    for a in final_assessment.get('development_areas', []):
        pdf.cell(0, 6, f"- {clean_text_for_pdf(a)}", ln=True)

    # Detailed question-by-question analysis
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(0, 8, "DETAILED QUESTION ANALYSIS", ln=True)
    pdf.ln(6)
    for i, (q, a, ev) in enumerate(zip(questions, answers, norm_evals)):
        if pdf.get_y() > 240:
            pdf.add_page()
        pdf.set_font("Arial", style='B', size=11)
        pdf.multi_cell(0, 6, f"Question {i+1}: {clean_text_for_pdf(q)}")
        pdf.ln(2)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 6, f"Overall Score: {ev.get('overall_score', 0)}/100", ln=True)
        # category scores
        if ev.get("category_scores"):
            for cat, sc in ev.get("category_scores", {}).items():
                pdf.cell(0, 5, f"  - {clean_text_for_pdf(cat.replace('_',' ').title())}: {sc}", ln=True)
        pdf.ln(2)
        pdf.set_font("Arial", style='B', size=10)
        pdf.cell(0, 5, "Candidate's Answer:", ln=True)
        pdf.set_font("Arial", style='I', size=9)
        ans_text = a if isinstance(a, str) else str(a)
        pdf.multi_cell(0, 5, clean_text_for_pdf((ans_text[:400] + '...') if len(ans_text) > 400 else ans_text))
        pdf.ln(2)
        pdf.set_font("Arial", size=9)
        explanation = ev.get('detailed_explanation') or ev.get('detailed_feedback') or "No detailed explanation available."
        pdf.multi_cell(0, 5, clean_text_for_pdf(explanation))
        pdf.ln(2)
        pdf.set_font("Arial", style='B', size=9)
        pdf.cell(0, 5, "Improvement Suggestions:", ln=True)
        pdf.set_font("Arial", size=9)
        for s in ev.get('improvement_suggestions', [])[:5]:
            pdf.multi_cell(0, 5, f" - {clean_text_for_pdf(s)}")
        pdf.ln(4)

    # Final recommendations
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(0, 8, "FINAL RECOMMENDATIONS", ln=True)
    pdf.ln(6)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(0, 6, clean_text_for_pdf(final_assessment.get('overall_assessment', '')))

    # Save file
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    reports_dir = os.path.join(project_root, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    report_path = os.path.join(
        reports_dir,
        f"comprehensive_interview_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    try:
        pdf.output(report_path)
        print(f"✅ Report generated: {report_path}")
    except Exception as e:
        print("❌ Error writing PDF:", e)
        return None
    finally:
        if graph_path and os.path.exists(graph_path):
            try:
                os.remove(graph_path)
            except:
                pass

    return report_path

# --- END of replacement block ---


def create_ats_report(ats_result, resume_text):
    """Generate a PDF report specifically for ATS analysis (not interview)"""
    print("🔄 Creating ATS analysis report...")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    def clean_text_for_pdf(text):
        """Clean text to remove problematic Unicode characters for PDF generation"""
        if not isinstance(text, str):
            try:
                text = str(text)
            except Exception:
                return "N/A"
        
        # Common replacements for special characters
        replacements = {
            '•': '-', '✓': '+', '✗': '-', '→': '->', '←': '<-', '↑': '^',
            '↓': 'v', '★': '*', '☆': '*', '…': '...', '–': '-', '—': '-',
            '\u2013': '-', '\u2014': '-', '\u2018': "'", '\u2019': "'", 
            '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u2022': '-',
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Encode to latin-1, replacing unknown characters with spaces
        try:
            text = text.encode('latin-1', 'replace').decode('latin-1')
        except Exception:
            text = text.encode('ascii', 'replace').decode('ascii')
        
        return text.strip() if text else "N/A"

    # Cover page
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=20)
    pdf.cell(0, 12, "ATS RESUME ANALYSIS REPORT", ln=True, align='C')
    pdf.set_font("Arial", size=11)
    pdf.ln(6)
    pdf.cell(0, 7, f"Date: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}", ln=True, align='C')
    pdf.ln(10)

    # Overall Score Section
    overall_score = ats_result.get("overallScore", 0)
    pdf.set_font("Arial", style='B', size=24)
    pdf.cell(0, 20, f"{overall_score}%", ln=True, align='C')
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(0, 8, "ATS COMPATIBILITY SCORE", ln=True, align='C')
    pdf.set_font("Arial", size=11)
    
    if overall_score >= 90:
        assessment = "Excellent - Your resume is highly optimized for ATS systems"
    elif overall_score >= 70:
        assessment = "Good - Your resume is well-optimized for most ATS systems"
    elif overall_score >= 50:
        assessment = "Fair - Your resume could be improved for better ATS compatibility"
    else:
        assessment = "Poor - Your resume needs significant improvements for ATS compatibility"
    
    try:
        pdf.multi_cell(0, 6, clean_text_for_pdf(assessment))
    except Exception as e:
        print(f"Warning: Could not write assessment: {e}")
        pdf.multi_cell(0, 6, "Assessment: Please review in dashboard")
    pdf.ln(6)

    # Detailed Breakdown
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(0, 10, "DETAILED BREAKDOWN", ln=True)
    pdf.ln(4)

    sections = ats_result.get("sections", {})
    section_order = ["keywords", "formatting", "experience", "skills"]
    
    for section_name in section_order:
        if section_name in sections:
            section_data = sections[section_name]
            score = section_data.get("score", 0)
            feedback = section_data.get("feedback", [])
            
            try:
                # Section title with score
                pdf.set_font("Arial", style='B', size=12)
                title = section_name.replace("_", " ").title()
                pdf.cell(0, 8, f"{title}: {score}%", ln=True)
                
                # Feedback items (simplified, no special chars)
                pdf.set_font("Arial", size=10)
                for item in feedback[:3]:
                    clean_item = clean_text_for_pdf(str(item))
                    pdf.multi_cell(0, 5, f"- {clean_item}")
                pdf.ln(2)
            except Exception as e:
                print(f"Warning: Could not write section {section_name}: {e}")
                pdf.ln(3)

    # Improvement Suggestions
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(0, 10, "IMPROVEMENT SUGGESTIONS", ln=True)
    pdf.ln(4)

    suggestions = ats_result.get("suggestions", [])
    pdf.set_font("Arial", size=10)
    
    for i, suggestion in enumerate(suggestions, 1):
        if pdf.get_y() > 240:
            pdf.add_page()
        try:
            clean_sugg = clean_text_for_pdf(str(suggestion))
            pdf.multi_cell(0, 6, f"{i}. {clean_sugg}")
            pdf.ln(2)
        except Exception as e:
            print(f"Warning: Could not write suggestion {i}: {e}")
            pdf.ln(3)

    # Key Recommendations
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=14)
    pdf.cell(0, 10, "KEY RECOMMENDATIONS", ln=True)
    pdf.ln(4)

    pdf.set_font("Arial", size=10)
    recommendations = [
        "Use standard fonts and formatting to ensure ATS readability",
        "Include relevant keywords from job descriptions in your resume",
        "Use clear section headers and bullet points",
        "Keep numerical values as words rather than symbols",
        "Avoid tables, graphics, and special formatting",
        "Use standard section names: Summary, Experience, Education, Skills",
        "Include your full name at the top",
        "Use a simple, consistent formatting style throughout"
    ]
    
    for rec in recommendations:
        if pdf.get_y() > 240:
            pdf.add_page()
        try:
            pdf.multi_cell(0, 6, f"- {rec}")
            pdf.ln(1)
        except Exception as e:
            print(f"Warning: Could not write recommendation: {e}")
            pdf.ln(2)

    # Save file
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    reports_dir = os.path.join(project_root, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    report_path = os.path.join(
        reports_dir,
        f"ats_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    try:
        pdf.output(report_path)
        print(f"✅ ATS Report generated: {report_path}")
    except UnicodeEncodeError as e:
        print(f"⚠️ Encoding error in PDF generation: {e}. Retrying with ASCII-only content...")
        # Try again with a simpler version
        try:
            pdf2 = FPDF()
            pdf2.set_auto_page_break(auto=True, margin=15)
            pdf2.add_page()
            pdf2.set_font("Arial", style='B', size=20)
            pdf2.cell(0, 12, "ATS ANALYSIS REPORT", ln=True, align='C')
            pdf2.set_font("Arial", size=11)
            pdf2.ln(2)
            
            overall_score = ats_result.get("overallScore", 0)
            pdf2.set_font("Arial", size=16)
            pdf2.cell(0, 10, f"Overall Score: {overall_score}%", ln=True)
            pdf2.ln(5)
            
            pdf2.set_font("Arial", size=10)
            pdf2.multi_cell(0, 5, "See detailed analysis in the dashboard for complete feedback.")
            
            pdf2.output(report_path)
            print(f"✅ ATS Report generated (simplified): {report_path}")
        except Exception as e2:
            print(f"❌ Error writing simplified ATS report PDF: {e2}")
            return None
    except Exception as e:
        print(f"❌ Error writing ATS report PDF: {e}")
        return None

    return report_path


def generate_final_interview_assessment(all_evaluations, resume_text):
    """Keep your existing final assessment function"""
    scores = [eval_data["overall_score"] for eval_data in all_evaluations]
    avg_score = sum(scores) / len(scores) if scores else 0
    
    # Prepare evaluation summary
    eval_summary = ""
    for i, evaluation in enumerate(all_evaluations, 1):
        eval_summary += f"Q{i} Score: {evaluation['overall_score']}/100\n"
        eval_summary += f"Strengths: {', '.join(evaluation['strengths'][:2])}\n"
        eval_summary += f"Weaknesses: {', '.join(evaluation['weaknesses'][:2])}\n\n"
    
    prompt = f"""
As a senior technical interviewer, provide a comprehensive final assessment for this candidate.

CANDIDATE BACKGROUND:
{resume_text[:800]}...

INTERVIEW PERFORMANCE SUMMARY:
Average Score: {avg_score:.1f}/100
{eval_summary}

INDIVIDUAL QUESTION SCORES:
{', '.join([str(score) for score in scores])}

ASSESSMENT REQUIREMENTS:
1. Overall hiring recommendation (Strong Hire/Hire/Maybe/No Hire)
2. Key strengths demonstrated
3. Major areas for improvement  
4. Technical competency level
5. Communication effectiveness
6. Cultural fit indicators
7. Specific role recommendations
8. Salary band suggestion
9. Onboarding focus areas

RESPONSE FORMAT (STRICT JSON):
{{
    "final_recommendation": "Hire",
    "confidence_level": 7,
    "overall_assessment": "The candidate demonstrates solid technical fundamentals with good problem-solving abilities.",
    "key_strengths": ["Technical knowledge", "Communication skills"],
    "development_areas": ["Advanced concepts", "System design"],
    "technical_level": "Mid",
    "communication_rating": 7,
    "problem_solving_rating": 7,
    "role_fit": "Good fit for mid-level developer position with mentoring support",
    "salary_recommendation": "Market rate for mid-level position",
    "onboarding_focus": ["Advanced technical training", "Mentorship program"],
    "next_steps": "Proceed to technical deep-dive interview"
}}
"""
    
    print("🔄 Generating final assessment...")
    response = call_llm(prompt, temperature=0.2)
    
    try:
        response_clean = response.strip()
        if response_clean.startswith("```"):
            response_clean = response_clean[7:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        response_clean = response_clean.strip()
        
        final_assessment = json.loads(response_clean)
        print("✅ Final assessment generated successfully")
        return final_assessment
        
    except json.JSONDecodeError as e:
        print(f"❌ Final assessment JSON parsing failed: {e}")
        
        return {
            "final_recommendation": "Maybe" if avg_score >= 50 else "No Hire",
            "confidence_level": 6,
            "overall_assessment": f"Candidate scored an average of {avg_score:.1f}/100 across all questions.",
            "key_strengths": ["Participated in all questions", "Showed engagement"],
            "development_areas": ["Technical depth", "Communication clarity"],
            "technical_level": "Junior" if avg_score < 60 else "Mid",
            "communication_rating": min(10, max(1, int(avg_score / 10))),
            "problem_solving_rating": min(10, max(1, int(avg_score / 10))),
            "role_fit": "Requires additional assessment and potential training",
            "salary_recommendation": "Entry-level to mid-level range",
            "onboarding_focus": ["Technical skill development", "Communication training"],
            "next_steps": "Additional technical assessment recommended"
        }

def get_time_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 17:
        return "Good afternoon"
    else:
        return "Good evening"

# ========== Main Flow with Fixed Question Parsing ==========
if __name__ == "__main__":
    print("🚀 AI INTERVIEW SYSTEM - ENHANCED WITH DETAILED EXPLANATIONS")
    print("=" * 70)
    
    if WHISPER_AVAILABLE and whisper_model:
        print("📌 Speech Recognition: Whisper AI (Offline, High Accuracy)")
    else:
        print("📌 Speech Recognition: Google STT (Online Fallback)")
    
    print(f"🤖 AI Evaluation: Gemini {'New API' if GENAI_AVAILABLE else 'Legacy API'}")
    print("✨ Features: Smart auto-stop, Real Gemini evaluation, Detailed explanations")
    
    # Test Gemini API first
    print("\n🔧 Testing Gemini API...")
    test_response = call_llm("Say 'Hello, Gemini API is working!' in exactly those words.")
    if "Hello, Gemini API is working!" in test_response:
        print("✅ Gemini API test successful!")
    else:
        print(f"⚠️ Gemini API test response: {test_response}")
        response = input("Gemini API may not be working properly. Continue anyway? (y/n): ")
        if response.lower() != 'y':
            exit()
    
    # PDF processing
    pdf_path = select_pdf_file()
    if not pdf_path:
        print("❌ No PDF selected. Exiting.")
        exit()

    resume_text = extract_text_from_pdf(pdf_path)
    if not resume_text:
        print("❌ Could not extract resume text. Exiting.")
        exit()

    print("🔄 Generating personalized interview questions using Gemini...")
    questions_text = generate_questions_from_resume(resume_text)
    
    # ✅ FIXED: Properly parse questions and remove intro text
    main_questions = parse_questions_properly(questions_text)

    print(f"\n📝 Generated {len(main_questions)} questions:")
    for i, q in enumerate(main_questions, 1):
        print(f"{i}. {q[:100]}{'...' if len(q) > 100 else ''}")

    if len(main_questions) < 5:
        print("⚠️ Less than 5 questions generated. Consider checking your resume content.")

    # Start interview
    greeting = get_time_greeting()
    
    print("\n🎤 STARTING INTERVIEW SESSION")
    print("=" * 40)
    
    speak_text(f"{greeting}. Welcome to your comprehensive AI interview assessment powered by Gemini. "
               f"I'll ask you {len(main_questions)} questions. Answer naturally - "
               f"the system will automatically detect when you're finished speaking.")

    # Introduction
    speak_text("Let's begin with your introduction. Please tell me about yourself, your background, and your experience.")
    intro_answer = listen_to_answer()

    # Collect all responses
    all_questions = ["Please introduce yourself and tell me about your background"] + main_questions
    all_answers = [intro_answer]
    all_evaluations = []

    # Evaluate introduction
    print("\n🔄 Evaluating your introduction...")
    if len(intro_answer.split()) > 5:
        intro_eval = enhanced_evaluate_answer(
            "Please introduce yourself and tell me about your background", 
            intro_answer, 
            resume_text
        )
        all_evaluations.append(intro_eval)
        speak_text(f"Thank you for your introduction. You scored {intro_eval['overall_score']} out of 100.")
        print(f"📊 Introduction score: {intro_eval['overall_score']}/100")
    else:
        speak_text("Thank you. Your introduction was brief - consider providing more detail in future interviews.")
        all_evaluations.append({
            "overall_score": 25,
            "category_scores": {"technical_accuracy": 5, "completeness": 5, "communication": 5, "problem_solving": 5, "relevance": 5},
            "strengths": ["Provided basic response"],
            "weaknesses": ["Very brief introduction", "Lacks detail about experience"],
            "detailed_feedback": "Introduction was too brief to properly assess candidate background and experience.",
            "detailed_explanation": "This introduction received 25/100 points because it was too brief to evaluate technical competency, communication skills, or relevant experience. A good introduction should include background information, key skills, relevant experience, and career objectives. The brevity suggests the candidate may be nervous or unprepared for the interview process.",
            "improvement_suggestions": ["Provide more detail about background", "Highlight key experiences", "Be more specific about skills"],
            "interviewer_notes": "Candidate may be nervous or unprepared",
            "follow_up_questions": ["Can you tell me more about your experience?", "What are your key skills?"]
        })

    # Main interview questions
    for idx, question in enumerate(main_questions, start=1):
        print(f"\n{'='*60}")
        print(f"QUESTION {idx} OF {len(main_questions)}")
        print('='*60)
        
        speak_text(f"Question {idx}: {question}")
        
        print(f"\n🔥 Question: {question}")
        print("\nYour answer will be automatically recorded. Speak naturally and the system will detect when you're finished.")
        
        answer = listen_to_answer()
        all_answers.append(answer)

        if len(answer.split()) > 5:
            print(f"\n🔄 Evaluating your answer using Gemini AI...")
            evaluation = enhanced_evaluate_answer(question, answer, resume_text)
            all_evaluations.append(evaluation)
            
            score = evaluation['overall_score']
            speak_text(f"Thank you for your detailed answer. You scored {score} out of 100 for this question.")
            print(f"📊 Question {idx} score: {score}/100")
            
            # Provide brief feedback
            if len(evaluation['strengths']) > 0:
                print(f"✅ Key strength: {evaluation['strengths'][0]}")
            if len(evaluation['improvement_suggestions']) > 0:
                print(f"💡 Improvement tip: {evaluation['improvement_suggestions'][0]}")
                
        else:
            speak_text("Thank you for your response. Consider providing more detailed answers.")
            all_evaluations.append({
                "overall_score": 20,
                "category_scores": {"technical_accuracy": 4, "completeness": 4, "communication": 4, "problem_solving": 4, "relevance": 4},
                "strengths": ["Attempted to answer"],
                "weaknesses": ["Response too brief", "Lacks technical detail"],
                "detailed_feedback": "Answer was too brief to properly evaluate technical knowledge and communication skills.",
                "detailed_explanation": "This answer received 20/100 points due to its brevity. Brief answers make it difficult to assess technical competency, problem-solving abilities, and communication skills. In a technical interview, detailed responses that demonstrate understanding of concepts, provide examples, and show logical thinking are essential for proper evaluation.",
                "improvement_suggestions": ["Provide more detailed responses", "Include specific examples", "Elaborate on technical concepts"],
                "interviewer_notes": "May need encouragement to provide more comprehensive answers",
                "follow_up_questions": ["Can you elaborate on that?", "What specific experience do you have with this?"]
            })

    # Generate comprehensive assessment
    speak_text("Thank you for completing the interview. I'm now generating your comprehensive assessment report with detailed explanations using Gemini AI.")
    
    print("\n🔄 Generating final assessment using Gemini AI...")
    final_assessment = generate_final_interview_assessment(all_evaluations, resume_text)
    
    print("📊 Creating comprehensive interview report with detailed explanations...")
    report_path = create_comprehensive_report(all_questions, all_answers, all_evaluations, final_assessment, resume_text)
    
    # Final summary
    avg_score = sum(eval_data["overall_score"] for eval_data in all_evaluations) / len(all_evaluations)
    
    print("\n" + "="*60)
    print("🎯 INTERVIEW COMPLETED - COMPREHENSIVE SUMMARY")
    print("="*60)
    print(f"📊 Overall Performance: {avg_score:.1f}/100")
    print(f"🎯 Final Recommendation: {final_assessment['final_recommendation']}")
    print(f"📈 Technical Level: {final_assessment['technical_level']}")
    print(f"💬 Communication Rating: {final_assessment['communication_rating']}/10")
    print(f"🧠 Problem Solving: {final_assessment['problem_solving_rating']}/10")
    print(f"📄 Detailed Report: {report_path}")
    print("="*60)
    
    speak_text(f"Your interview assessment is complete. Your overall performance score is {avg_score:.0f} out of 100. "
               f"The recommendation is {final_assessment['final_recommendation']}. "
               f"A comprehensive report with detailed explanations has been generated for your review.")
    
    print(f"\n✅ Interview session completed successfully!")
    print(f"📁 Open '{report_path}' for your detailed assessment report with explanations.")
