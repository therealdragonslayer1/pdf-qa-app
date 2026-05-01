"""
AI-Based PDF Question Answering Web App with Voice Output
=========================================================
Backend: Flask + pdfplumber + IBM Watson TTS
"""

import os
import re
import uuid
import string
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import pdfplumber

# ─── IBM Watson Text-to-Speech ───────────────────────────────────────────────
# Replace these two values with your real IBM Watson credentials
IBM_API_KEY     = "KQGmrsTgRBa98vWMfJJY5qU7HZ3kNJLIJMTz4mIHI2MY"        # ← paste your API key
IBM_SERVICE_URL = "https://api.au-syd.text-to-speech.watson.cloud.ibm.com/instances/be3bd205-595f-4025-a5a0-fd1ce9a0526a"    # ← paste your service URL
#  e.g. "https://api.us-south.text-to-speech.watson.cloud.ibm.com/instances/xxxx"
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config["UPLOAD_FOLDER"]    = os.path.join(os.path.dirname(__file__), "uploads")
app.config["AUDIO_FOLDER"]     = os.path.join(os.path.dirname(__file__), "static", "audio")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024   # 16 MB limit
ALLOWED_EXTENSIONS = {"pdf"}

# Ensure required directories exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["AUDIO_FOLDER"],  exist_ok=True)

# In-memory store: maps session key → extracted text chunks
pdf_store: dict[str, list[str]] = {}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_chunks(pdf_path: str, chunk_size: int = 400) -> list[str]:
    """
    Extract all text from a PDF and split into overlapping chunks.
    Falls back to fixed-size word chunks when paragraph breaks are sparse.
    """
    raw_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                raw_pages.append(text.strip())

    full_text = "\n\n".join(raw_pages)

    # Clean up extra whitespace / control chars
    full_text = re.sub(r"[ \t]+", " ", full_text)
    full_text = re.sub(r"\n{3,}", "\n\n", full_text)

    # Split on blank lines first (paragraph-based)
    paragraphs = [p.strip() for p in re.split(r"\n\n+", full_text) if p.strip()]

    # If paragraphs are too long, break them into word-based chunks
    chunks: list[str] = []
    for para in paragraphs:
        words = para.split()
        if len(words) <= chunk_size:
            chunks.append(para)
        else:
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i : i + chunk_size])
                chunks.append(chunk)

    return chunks if chunks else ["No readable text found in this PDF."]


def find_best_answer(question: str, chunks: list[str]) -> str:
    """
    Simple keyword-matching: score each chunk by how many question
    words appear in it, then return the highest-scoring chunk.
    """
    # Tokenise + normalise question
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "used", "to", "of", "in", "on", "at", "by", "for", "with", "about",
        "against", "between", "into", "through", "during", "before", "after",
        "above", "below", "from", "up", "down", "out", "off", "over", "under",
        "again", "further", "then", "once", "and", "but", "or", "nor", "so",
        "yet", "both", "either", "neither", "not", "only", "own", "same",
        "than", "too", "very", "what", "which", "who", "whom", "this", "that",
        "these", "those", "i", "me", "my", "myself", "we", "our", "you",
        "your", "he", "she", "it", "they", "their", "them", "its",
    }
    translator = str.maketrans("", "", string.punctuation)
    q_words = [
        w for w in question.lower().translate(translator).split()
        if w not in stop_words and len(w) > 1
    ]

    if not q_words:
        return "Please ask a more specific question."

    best_score = 0
    best_chunk = ""

    for chunk in chunks:
        chunk_lower = chunk.lower()
        score = sum(1 for w in q_words if w in chunk_lower)
        # Bonus: exact phrase match
        if question.lower() in chunk_lower:
            score += len(q_words)
        if score > best_score:
            best_score = score
            best_chunk = chunk

    if best_score == 0:
        return "Answer not found in the document. Try rephrasing your question."

    # Trim very long chunks for readability
    if len(best_chunk) > 800:
        best_chunk = best_chunk[:800].rsplit(" ", 1)[0] + "…"

    return best_chunk


def text_to_speech(text: str) -> str | None:
    """
    Convert text to speech via IBM Watson TTS.
    Returns the relative URL path to the audio file, or None on failure.
    """
    if IBM_API_KEY == "YOUR_IBM_API_KEY_HERE":
        return None   # credentials not configured → skip gracefully

    try:
        from ibm_watson import TextToSpeechV1
        from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

        authenticator = IAMAuthenticator(IBM_API_KEY)
        tts = TextToSpeechV1(authenticator=authenticator)
        tts.set_service_url(IBM_SERVICE_URL)

        filename  = f"answer_{uuid.uuid4().hex[:8]}.mp3"
        filepath  = os.path.join(app.config["AUDIO_FOLDER"], filename)

        # Synthesise and save
        audio_data = tts.synthesize(
            text[:3000],               # Watson limit guard
            voice="en-US_AllisonV3Voice",
            accept="audio/mp3",
        ).get_result().content

        with open(filepath, "wb") as f:
            f.write(audio_data)

        return f"/static/audio/{filename}"

    except Exception as e:
        app.logger.warning("IBM Watson TTS failed: %s", e)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_pdf():
    """
    Accept a PDF upload, extract text, and return a session key.
    The key is used by /ask to look up the right chunks.
    """
    if "pdf" not in request.files:
        return jsonify({"error": "No file part in request."}), 400

    file = request.files["pdf"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Only PDF files are accepted."}), 400

    filename  = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    try:
        chunks = extract_text_chunks(save_path)
    except Exception as e:
        return jsonify({"error": f"Could not read PDF: {e}"}), 500

    # Store under a unique key so multiple tabs can work independently
    session_key = uuid.uuid4().hex
    pdf_store[session_key] = chunks

    # Clean up the uploaded file immediately (we have the text)
    os.remove(save_path)

    word_count = sum(len(c.split()) for c in chunks)
    return jsonify({
        "success":     True,
        "session_key": session_key,
        "chunks":      len(chunks),
        "words":       word_count,
        "filename":    filename,
    })


@app.route("/ask", methods=["POST"])
def ask_question():
    """
    Receive a question + session_key, find the best answer, synthesise audio.
    """
    data = request.get_json(silent=True) or {}
    question    = (data.get("question") or "").strip()
    session_key = (data.get("session_key") or "").strip()

    if not question:
        return jsonify({"error": "Please enter a question."}), 400
    if not session_key or session_key not in pdf_store:
        return jsonify({"error": "PDF session expired or not found. Please re-upload."}), 400

    chunks = pdf_store[session_key]
    answer = find_best_answer(question, chunks)

    # Attempt TTS (fails gracefully if IBM not configured)
    audio_url = text_to_speech(answer)

    return jsonify({
        "answer":    answer,
        "audio_url": audio_url,   # None when TTS unavailable
    })


@app.route("/static/audio/<path:filename>")
def serve_audio(filename):
    return send_from_directory(app.config["AUDIO_FOLDER"], filename)


# ──────────────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)