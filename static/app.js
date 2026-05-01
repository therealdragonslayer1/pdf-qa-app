/**
 * PDF Oracle — Frontend JS
 * Handles: drag-drop, file selection, upload, Q&A, audio playback
 */

// ── State ──────────────────────────────────────────────────────────────────
let sessionKey    = null;   // returned by /upload
let selectedFile  = null;   // File object

// ── Element refs ──────────────────────────────────────────────────────────
const dropZone      = document.getElementById("dropZone");
const pdfInput      = document.getElementById("pdfInput");
const fileInfo      = document.getElementById("fileInfo");
const fileName      = document.getElementById("fileName");
const btnRemove     = document.getElementById("btnRemove");
const btnUpload     = document.getElementById("btnUpload");
const uploadMeta    = document.getElementById("uploadMeta");

const questionInput = document.getElementById("questionInput");
const charCounter   = document.getElementById("charCounter");
const btnAsk        = document.getElementById("btnAsk");

const emptyState    = document.getElementById("emptyState");
const answerCard    = document.getElementById("answerCard");
const questionEcho  = document.getElementById("questionEcho");
const answerText    = document.getElementById("answerText");
const audioSection  = document.getElementById("audioSection");
const audioPlayer   = document.getElementById("audioPlayer");
const ttsUnavailable= document.getElementById("ttsUnavailable");
const errorCard     = document.getElementById("errorCard");
const errorMessage  = document.getElementById("errorMessage");
const btnCopy       = document.getElementById("btnCopy");

// ── Drag & Drop ────────────────────────────────────────────────────────────

dropZone.addEventListener("click", () => pdfInput.click());

dropZone.addEventListener("dragover", e => {
  e.preventDefault();
  dropZone.classList.add("drag-over");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) setFile(file);
});

pdfInput.addEventListener("change", () => {
  if (pdfInput.files[0]) setFile(pdfInput.files[0]);
});

function setFile(file) {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    showError("Only PDF files are supported.");
    return;
  }
  selectedFile = file;
  fileName.textContent = file.name;
  fileInfo.classList.remove("hidden");
  dropZone.classList.add("hidden");
  btnUpload.disabled = false;
  hideError();
  resetOutput();

  // Reset session when a new file is picked
  sessionKey = null;
  disableAsk();
  uploadMeta.classList.add("hidden");
}

btnRemove.addEventListener("click", () => {
  selectedFile = null;
  pdfInput.value = "";
  fileInfo.classList.add("hidden");
  dropZone.classList.remove("hidden");
  btnUpload.disabled = true;
  uploadMeta.classList.add("hidden");
  disableAsk();
  resetOutput();
});

// ── Upload ─────────────────────────────────────────────────────────────────

btnUpload.addEventListener("click", uploadPDF);

async function uploadPDF() {
  if (!selectedFile) return;

  setLoading(btnUpload, true);
  hideError();

  const formData = new FormData();
  formData.append("pdf", selectedFile);

  try {
    const res  = await fetch("/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok || data.error) {
      showError(data.error || "Upload failed.");
      return;
    }

    sessionKey = data.session_key;
    uploadMeta.textContent =
      `✓  ${data.filename}  ·  ${data.chunks} chunks  ·  ${data.words.toLocaleString()} words`;
    uploadMeta.classList.remove("hidden");
    enableAsk();

  } catch (err) {
    showError("Network error — is Flask running?");
  } finally {
    setLoading(btnUpload, false);
  }
}

// ── Question input ─────────────────────────────────────────────────────────

const MAX_Q = 300;

questionInput.addEventListener("input", () => {
  const len = questionInput.value.length;
  charCounter.textContent = `${len} / ${MAX_Q}`;
  if (len > MAX_Q) questionInput.value = questionInput.value.slice(0, MAX_Q);
  btnAsk.disabled = len === 0 || !sessionKey;
});

questionInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey && !btnAsk.disabled) {
    e.preventDefault();
    askQuestion();
  }
});

btnAsk.addEventListener("click", askQuestion);

// ── Ask ────────────────────────────────────────────────────────────────────

async function askQuestion() {
  const question = questionInput.value.trim();
  if (!question || !sessionKey) return;

  setLoading(btnAsk, true);
  hideError();
  resetOutput();

  try {
    const res  = await fetch("/ask", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ question, session_key: sessionKey }),
    });
    const data = await res.json();

    if (!res.ok || data.error) {
      showError(data.error || "Something went wrong.");
      return;
    }

    // Show answer
    questionEcho.textContent = question;
    answerText.textContent   = data.answer;
    emptyState.classList.add("hidden");
    answerCard.classList.remove("hidden");
    errorCard.classList.add("hidden");

    // Audio
    if (data.audio_url) {
      audioPlayer.src = data.audio_url;
      audioSection.classList.remove("hidden");
      ttsUnavailable.classList.add("hidden");
      audioPlayer.play().catch(() => {});  // autoplay (may be blocked by browser)
    } else {
      audioSection.classList.add("hidden");
      ttsUnavailable.classList.remove("hidden");
    }

  } catch (err) {
    showError("Network error — is Flask running?");
  } finally {
    setLoading(btnAsk, false);
  }
}

// ── Copy button ────────────────────────────────────────────────────────────

btnCopy.addEventListener("click", () => {
  const text = answerText.textContent;
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    btnCopy.classList.add("copied");
    btnCopy.querySelector("span").textContent = "Copied!";
    setTimeout(() => {
      btnCopy.classList.remove("copied");
      btnCopy.querySelector("span").textContent = "Copy";
    }, 2000);
  });
});

// ── Helpers ────────────────────────────────────────────────────────────────

function setLoading(btn, on) {
  const text   = btn.querySelector(".btn-text");
  const loader = btn.querySelector(".btn-loader");
  btn.disabled = on;
  text.classList.toggle("hidden", on);
  loader.classList.toggle("hidden", !on);
}

function enableAsk() {
  questionInput.disabled = false;
  questionInput.focus();
}
function disableAsk() {
  questionInput.disabled = true;
  btnAsk.disabled = true;
}

function showError(msg) {
  errorMessage.textContent = msg;
  errorCard.classList.remove("hidden");
  emptyState.classList.add("hidden");
  answerCard.classList.add("hidden");
}
function hideError() { errorCard.classList.add("hidden"); }

function resetOutput() {
  answerCard.classList.add("hidden");
  emptyState.classList.remove("hidden");
  audioSection.classList.add("hidden");
  ttsUnavailable.classList.add("hidden");
  audioPlayer.src = "";
}
