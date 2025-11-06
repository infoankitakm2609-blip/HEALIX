import os
import json
from datetime import datetime
from string import Template
import streamlit as st
from dotenv import load_dotenv
import logging # <-- ADD THIS
# add near imports
import traceback
from pathlib import Path
from datetime import datetime

STT_LOG = "stt_debug.log"

def _log_stt(message: str):
    try:
        with open(STT_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
    except Exception:
        pass  # never break UI because of logging

def stt_diagnostics():
    """Return a dict of STT readiness and write details to stt_debug.log."""
    env_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or ""
    has_env = bool(env_path)
    path_exists = Path(env_path).exists() if env_path else False
    can_import = HAS_SPEECH
    client_ok = False
    client_err = ""

    if can_import and has_env and path_exists:
        try:
            _ = speech.SpeechClient()  # dry-run
            client_ok = True
        except Exception as e:
            client_err = f"{type(e).__name__}: {e}"

    diag = {
        "has_env": has_env,
        "env_path": env_path,
        "path_exists": path_exists,
        "has_pkg": can_import,
        "client_ok": client_ok,
        "client_err": client_err,
    }
    _log_stt(f"Diagnostics: {diag}")
    return diag

load_dotenv()

try:
    from audio_recorder_streamlit import audio_recorder
    HAS_RECORDER = True
except Exception:
    HAS_RECORDER = False

# --- Google Cloud Speech-to-Text
try:
    from google.cloud import speech_v1 as speech
    HAS_SPEECH = True
except Exception:
    HAS_SPEECH = False

# --- Google GenAI (new client)
from google import genai

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler("app_errors.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AarogyaAIApp') # <-- Get a logger instance

# --------------- CONFIG ---------------
st.set_page_config(page_title="AarogyaAIApp", page_icon="🩺", layout="wide")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

SUPPORTED_LANGS = ["hi-IN", "en-US"]

# --------------- PROMPT (plain-language) ---------------
AAROGYA_PROMPT = Template("""
Make a clear medical summary that any common person can easily understand.
Do NOT return JSON. Use simple sentences and bullet points.

Chief Complaint:
- Main problem in one short line.

History of Present Illness:
- Describe symptoms in 2–4 short lines.

Possible Conditions:
- Condition 1 (likely)
- Condition 2 (if any)

Red Flags:
- (Write "None" if no serious warning signs)

Suggested Tests:
- Write useful tests OR "No immediate tests needed"

Urgency Level:
- Low / Routine / Prompt / Urgent

Advice:
- Home care steps and when to see a doctor.

Follow-up Questions:
- Add 1–3 useful clarification questions.

Patient Details:
$patient_demo

Patient Said:
<RAW_TEXT_START>
$raw_text
<RAW_TEXT_END>
""")

# --------------- FUNCTIONS ---------------
def transcribe_audio_google(audio_bytes: bytes, language_code: str, alt_langs=None) -> str:
    """Transcribe recorded/uploaded audio with Google STT."""
    client_stt = speech.SpeechClient()
    if alt_langs is None:
        alt_langs = ["en-US"] if language_code == "hi-IN" else ["hi-IN"]

    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        language_code=language_code,
        alternative_language_codes=alt_langs,
        enable_automatic_punctuation=True,
        model="latest_long",
        audio_channel_count=1,
        enable_word_time_offsets=False,
        encoding=speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
    )
    resp = client_stt.recognize(config=config, audio=audio)
    return " ".join([r.alternatives[0].transcript.strip() for r in resp.results]).strip()

def summarize_text(raw_text: str, patient: dict) -> str:
    prompt = AAROGYA_PROMPT.substitute(
        patient_demo=json.dumps(patient, ensure_ascii=False),
        raw_text=raw_text.strip()
    )
    res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return res.text

# Keep a place for the transcribed/typed text
if "typed_text" not in st.session_state:
    st.session_state.typed_text = ""

# --------------- UI ---------------
st.title("🩺 AarogyaAIApp – Symptom Summarizer")

with st.sidebar:
    st.subheader("Patient Details")
    pname = st.text_input("Patient Name (optional)")
    age = st.number_input("Age", 0, 120, 25)
    gender = st.selectbox("Gender", ["Unspecified", "Male", "Female", "Other"], index=0)
    lang = st.selectbox("Speech Language", SUPPORTED_LANGS, index=0)
    consent = st.checkbox("I confirm patient consent ✅")

    st.divider()
    st.caption("Status")
    st.write(f"Gemini API key: {'✅' if GEMINI_API_KEY else '❌'}")
    st.write(f"Speech-to-Text: {'✅' if HAS_SPEECH else '❌'}")
    st.write(f"Mic widget: {'✅' if HAS_RECORDER else '❌'}")
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        st.caption("Set GOOGLE_APPLICATION_CREDENTIALS to your service-account.json for STT")

st.subheader("🎤 Input Symptoms")

# -------- Mic recording (auto-transcribe on stop) --------
recorded_bytes = None
if HAS_RECORDER:
    st.caption("Click the mic to start/stop recording. Speak naturally in Hindi or English.")
    recorded_bytes = audio_recorder(
        text="Click to record / stop",
        icon_name="microphone",
        sample_rate=16000
    )

# When user stops recording, audio_recorder returns bytes. Auto-transcribe:
# if recorded_bytes and consent:
#     if HAS_SPEECH and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
#         with st.spinner("Transcribing..."):
#             try:
#                 st.session_state.typed_text = transcribe_audio_google(recorded_bytes, language_code=lang)
#                 st.success("✅ Transcription complete")
#             except Exception as e:
#                 st.error(f"STT error: {e}")
#     else:
#         st.error("Google STT not configured (GOOGLE_APPLICATION_CREDENTIALS missing).")

if recorded_bytes and consent:
    diag = stt_diagnostics()

    if not diag["has_pkg"]:
        st.error("google-cloud-speech not installed. Run: pip install google-cloud-speech")
        _log_stt("Error: google-cloud-speech not installed.")
    elif not diag["has_env"]:
        st.error("Missing GOOGLE_APPLICATION_CREDENTIALS environment variable.")
        st.caption("Set it to your service-account.json path (downloaded from Google Cloud Console).")
        _log_stt("Error: GOOGLE_APPLICATION_CREDENTIALS not set.")
    elif not diag["path_exists"]:
        st.error(f"Service account file not found at: {diag['env_path']}")
        st.caption("Check the path or move the JSON file there.")
        _log_stt(f"Error: JSON path not found -> {diag['env_path']}")
    elif not diag["client_ok"]:
        st.error("Could not initialize Google STT client.")
        if diag["client_err"]:
            st.code(diag["client_err"], language="text")
        _log_stt(f"Error: SpeechClient init failed -> {diag['client_err']}")
    else:
        with st.spinner("Transcribing..."):
            try:
                # Tip: keep recordings short (< 60s) for sync API
                st.session_state.typed_text = transcribe_audio_google(recorded_bytes, language_code=lang)
                st.success("✅ Transcription complete")
                _log_stt("Success: transcription complete.")
            except Exception as e:
                st.error(f"STT error: {type(e).__name__}: {e}")
                tb = traceback.format_exc()
                st.code(tb[-1500:], language="text")  # show tail of traceback
                _log_stt(f"Exception during transcribe: {e}\n{tb}")

# -------- Upload audio (optional) --------
uploaded = st.file_uploader("Or upload audio (wav/mp3/m4a)", type=["wav", "mp3", "m4a"])

if uploaded and consent:
    if HAS_SPEECH and os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        with st.spinner("Transcribing uploaded audio..."):
            try:
                st.session_state.typed_text = transcribe_audio_google(uploaded.read(), language_code=lang)
                st.success("✅ Transcription complete")
            except Exception as e:
                st.error(f"STT error: {e}")
    else:
        st.error("Google STT not configured (GOOGLE_APPLICATION_CREDENTIALS missing).")

# -------- Manual typing (always available) --------
st.session_state.typed_text = st.text_area(
    "Or type symptoms (Hindi/English)", value=st.session_state.typed_text, height=150
)

# -------- Generate Summary --------
if st.button("✨ Generate Summary", use_container_width=True):
    if not consent:
        st.error("Consent required.")
    elif not st.session_state.typed_text.strip():
        st.error("Please speak or type symptoms first.")
    elif not client:
        st.error("GEMINI_API_KEY missing. Set it before running.")
    else:
        patient = {
            "name": pname,
            "age": age,
            "gender": gender,
            "language": lang,
            "datetime": datetime.now().isoformat(timespec="seconds")
        }
        with st.spinner("Analyzing..."):
            try:
                summary = summarize_text(st.session_state.typed_text, patient)
                st.success("✅ Summary Ready")
                st.write(summary)
                st.download_button("Download Summary", summary, file_name="summary.txt")
            except Exception as e:
                st.error(f"Summarization error: {e}")
