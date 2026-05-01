# PDF Oracle — AI-Based PDF Q&A with Voice Output

A fully local Flask web app: upload a PDF → ask questions → see the answer → hear it spoken aloud via IBM Watson TTS.

---

## Project Structure

```
pdf_qa_app/
├── app.py                  ← Flask backend (all routes + logic)
├── requirements.txt        ← Python dependencies
├── templates/
│   └── index.html          ← Single-page UI
├── static/
│   ├── style.css           ← Dark editorial stylesheet
│   ├── app.js              ← Frontend JS (drag-drop, fetch, audio)
│   └── audio/              ← Generated MP3 files (auto-created)
└── uploads/                ← Temp PDF storage (cleared after extraction)
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. (Optional) Configure IBM Watson TTS

Open `app.py` and replace the two placeholder values near the top:

```python
IBM_API_KEY     = "YOUR_IBM_API_KEY_HERE"
IBM_SERVICE_URL = "YOUR_IBM_SERVICE_URL_HERE"
```

**Where to get credentials:**
1. Log in to [IBM Cloud](https://cloud.ibm.com)
2. Go to **Catalog → AI / Machine Learning → Text to Speech**
3. Create a free Lite instance
4. Click **Manage → Credentials** — copy the API key and URL

> If you skip this step, the app still works — answers are shown as text and a notice is displayed instead of the audio player.

### 3. Run the server

```bash
python app.py
```

### 4. Open in browser

```
http://127.0.0.1:5000
```

---

## How It Works

| Step | What happens |
|------|-------------|
| Upload | PDF is saved temporarily, `pdfplumber` extracts all text, splits into ~400-word chunks, then the file is deleted |
| Ask | Your question is tokenised; stop-words are removed; each chunk is scored by keyword overlap; the highest-scoring chunk is returned |
| Voice | The answer text is sent to IBM Watson TTS; the MP3 is saved in `static/audio/` and streamed back to the `<audio>` element |

---

## Requirements

```
flask==3.0.0
pdfplumber==0.10.3
ibm-watson==8.1.0
ibm-cloud-sdk-core==3.20.3
werkzeug==3.0.1
```

Python 3.9+ recommended.
