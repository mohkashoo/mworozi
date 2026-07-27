# 🫀 Project Humura — Neonatal Cry Acoustic Diagnostic Triage

A low-resource clinical triage platform for rural African midwives. Listens to an infant's cry, runs local acoustic AI to detect distress patterns, and generates a structured triage brief via Google Gemini.

---

## How It Works

```
🧑‍⚕️ MIDWIFE → 🎤 RECORD CRY (2s live mic / upload / simulate)
       ↓
🧠 TIER 1 — LOCAL AI (on laptop, no internet)
   • Extracts 36 acoustic features via librosa
   • Random Forest classifies: normal (0) or distress (1)
   • Risk score 0–100
       ↓
🤖 TIER 2 — GENERATIVE AI (Gemini, only if distress detected)
   • Reads: acoustic score + vitals + maternal history
   • Generates: assessment + stabilization steps + referral letter
   • Falls back to rule engine if API key missing / quota exceeded
       ↓
📋 RESULT → Alert banner + spectrogram + clinical brief + referral letter
```

---

## AI Models

| Model | Location | Purpose | Training Data |
|-------|----------|---------|---------------|
| **Random Forest Classifier** | `audio_processor.py` (scikit-learn) | Classifies cry into **normal** (class 0) or **distress** (class 1) | **1,267 samples**: 845 real baby cries + 422 synthetic distress cries. 200 trees, max depth 16. |
| **Google Gemini `gemini-flash-latest`** | `app.py` — Tier 2 | Generates structured triage brief + referral letter | Pre-trained foundation model. Prompted with acoustic score + vitals. |
| **Clinical Rule Engine** | `app.py` (built-in fallback) | 8 clinical rules evaluating vitals + acoustic score → CRITICAL / HIGH / MODERATE / STABLE | Rule-based (no training). Always runs when Gemini is unavailable. |

**Model locked to disk** (`cry_model.joblib`) — consistent predictions across restarts. No retraining wait.

---

## Audio / Signal Processing (librosa)

| Feature | What it measures | Normal Baby | Distress Baby |
|---------|-----------------|-------------|---------------|
| **F0 (Fundamental Frequency)** | Pitch of the cry | 350–650 Hz (stable) | 150–1000 Hz (volatile) |
| **MFCCs (13 coefficients)** | Voice-print / timbre | Low variance | High variance |
| **Spectral Centroid** | Brightness of the sound | 1500–3000 Hz | 800–5000 Hz |
| **Spectral Bandwidth** | Frequency spread | 1500–3000 Hz | 800–6000 Hz |
| **Spectral Rolloff** | Where 85% of energy is | 2000–4000 Hz | 1000–7000 Hz |
| **Zero-Crossing Rate** | Noisiness of signal | 0.02–0.08 | 0.05–0.25 |
| **RMS Energy** | Loudness over time | 0.01–0.10 | 0.01–0.20 |
| **STFT Spectrogram** | Time-frequency heatmap (Plotly) | — | — |
| **librosa.yin** | Pitch tracking algorithm | — | — |

**36 features** per cry sample (8 descriptors × 2 stats + 13 MFCCs × 2 stats)

---

## Training Data

The model is trained on **real infant cry recordings** from the public `mahmudulhasan01/baby_crying_sound` dataset on Hugging Face.

| Category | Label | Count | Class |
|----------|-------|-------|-------|
| Hungry | non-urgent | 382 | normal |
| Discomfort | non-urgent | 135 | normal |
| Tired | non-urgent | 132 | normal |
| Burping | non-urgent | 108 | normal |
| Laugh | non-urgent | 108 | normal |
| Silence | non-urgent | 108 | normal |
| Synthetic distress | high-risk | 422 | distress |

**Total**: 845 real + 422 synthetic = **1,267 training samples**

---

## Features

| Feature | Details |
|---------|---------|
| **🎤 3 audio input methods** | Live mic (`st.audio_input`), file upload, simulated profile |
| **📊 Live spectrogram** | Plotly heatmap + F0 contour overlay + healthy range (350–650 Hz) |
| **🟢🔴 Triage alerts** | CRITICAL (red) / HIGH (amber) / MODERATE (blue) / STABLE (green) |
| **🤖 Gemini clinical brief** | Assessment + stabilization steps + referral letter |
| **⚙️ Fallback rule engine** | 8 clinical rules, runs when Gemini is unavailable |
| **📋 Patient ledger** | SQLite database, visible on every page load |
| **🔬 Feature summary** | 6 key acoustic features with green/red indicators |
| **🖤 Dark SOC theme** | Bootstrap Icons, clinical styling (#090a0f / #10b981 / #ef4444) |

---

## Infrastructure & UI

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.12 | Runtime |
| **Streamlit** | 1.60.0 | Web application framework |
| **Plotly** | 6.9.0 | Interactive spectrogram + feature charts |
| **scikit-learn** | 1.9.0 | Random Forest classifier (200 trees) |
| **librosa** | 0.11.0 | Audio feature extraction |
| **joblib** | — | Model serialization (instant startup) |
| **NumPy / SciPy** | — | Array operations, signal processing |
| **SQLite** | — | Patient assessment ledger (`humura.db`) |
| **Pandas** | 3.0.3 | Data querying + ledger display |
| **google-genai** | 2.14.0 | Gemini API client |
| **Bootstrap Icons** | 1.11.3 | Dashboard UI icons |
| **python-dotenv** | 1.0.0 | Environment variable loading |
| **Hugging Face Datasets** | — | 1,068 real infant cry WAV files for training |

---

## Project Structure

```
├── app.py                 # Streamlit clinical interface
├── audio_processor.py     # NeonatalAudioEngine (feature extraction + ML)
├── train.py               # Training script (downloads HF dataset + trains model)
├── cry_model.joblib       # Pre-trained Random Forest model (loaded at startup)
├── cry_scaler.joblib      # Feature scaler
├── cry_features.json      # Feature key ordering
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── .streamlit/config.toml # Streamlit theme config
└── README.md
```

---

## Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Set Gemini API key for AI triage
export GEMINI_API_KEY="your-key-here"
export GEMINI_MODEL="gemini-flash-latest"

# 3. Launch
streamlit run app.py --server.enableCORS false
```

**First launch**: loads pre-trained model instantly (~5s). No retraining needed.

**Offline**: Tier 1 acoustic analysis works with no internet. Tier 2 Gemini triage needs internet (falls back to rules gracefully).

---

## Deployment

| Scenario | Setup |
|----------|-------|
| **Phase 1 — Pilot** | Deploy on Railway / Hugging Face Spaces ($10/mo). 5 clinics get tablets with Chrome shortcut. No install. |
| **Phase 2 — Offline** | Docker container with offline acoustic engine. Sync when connected. USB distribution for remote areas. |
| **Scaling** | Switch SQLite → PostgreSQL for multi-clinic. Add simple PIN auth. |

---

## Limitations

- Gemini free tier: ~60 req/min. Exceeded → falls back to rule engine.
- Model trained on clean recordings. Noisy environments reduce accuracy.
- Clinical decision support only — always consult a qualified health professional.

---

## Disclaimer

**Demonstration and research tool — not for clinical use.** No patient data is transmitted to external servers. Acoustic analysis runs entirely on-device.

Built with ❤️ for Rwanda

⭐ Star this repo if you find it useful!
