import io
import os
import json
import warnings

import numpy as np
import librosa
import soundfile as sf
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import joblib

warnings.filterwarnings("ignore")

SAMPLE_RATE = 22050
N_MFCC = 13
N_FFT = 2048
HOP_LENGTH = 512
CRY_FMIN = librosa.note_to_hz("C2")
CRY_FMAX = librosa.note_to_hz("C7")

FEATURE_KEYS = [
    "bandwidth_mean", "bandwidth_std",
    "f0_mean", "f0_std",
    "mfcc_0_mean", "mfcc_0_std",
    "mfcc_1_mean", "mfcc_1_std",
    "mfcc_2_mean", "mfcc_2_std",
    "mfcc_3_mean", "mfcc_3_std",
    "mfcc_4_mean", "mfcc_4_std",
    "mfcc_5_mean", "mfcc_5_std",
    "mfcc_6_mean", "mfcc_6_std",
    "mfcc_7_mean", "mfcc_7_std",
    "mfcc_8_mean", "mfcc_8_std",
    "mfcc_9_mean", "mfcc_9_std",
    "mfcc_10_mean", "mfcc_10_std",
    "mfcc_11_mean", "mfcc_11_std",
    "mfcc_12_mean", "mfcc_12_std",
    "rms_mean", "rms_std",
    "rolloff_mean", "rolloff_std",
    "spectral_centroid_mean", "spectral_centroid_std",
    "zcr_mean", "zcr_std",
]


def _synthetic_audio(category: str, rng: np.random.Generator, sr: int) -> np.ndarray:
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    if category == "normal":
        f0_base = rng.uniform(350, 600)
        f0_mod = rng.uniform(30, 80)
        f0 = f0_base + f0_mod * np.sin(2 * np.pi * rng.uniform(2, 5) * t)
        sig = (
            0.8 * np.sin(2 * np.pi * f0 * t)
            + rng.uniform(0.15, 0.35) * np.sin(2 * np.pi * f0 * 2 * t)
            + rng.uniform(0.05, 0.15) * np.sin(2 * np.pi * f0 * 3 * t)
        )
        env = np.exp(-rng.uniform(1.5, 3.0) * t) + rng.uniform(0.1, 0.3)
        sig *= env
        sig += rng.normal(0, rng.uniform(0.002, 0.01), len(sig))
    else:
        f0_base = rng.uniform(600, 900)
        f0_mod = rng.uniform(100, 300)
        f0 = f0_base + f0_mod * np.sin(2 * np.pi * rng.uniform(6, 12) * t)
        brk = int(sr * duration * rng.uniform(0.25, 0.55))
        f0[brk:] = f0[brk:] * rng.uniform(1.3, 2.0)
        sig = (
            0.6 * np.sin(2 * np.pi * f0 * t)
            + rng.uniform(0.3, 0.5) * np.sin(2 * np.pi * f0 * rng.uniform(2.0, 3.0) * t)
            + rng.uniform(0.1, 0.3) * np.sin(2 * np.pi * f0 * rng.uniform(3.5, 5.0) * t)
        )
        env = np.exp(-rng.uniform(1.0, 2.0) * t) + rng.uniform(0.2, 0.4)
        env += rng.uniform(0.1, 0.3) * np.sin(2 * np.pi * rng.uniform(4, 8) * t)
        sig *= env
        sig += rng.normal(0, rng.uniform(0.01, 0.03), len(sig))

    peak = max(np.abs(sig))
    if peak > 0:
        sig /= peak * 1.05
    return sig


_MODEL_DIR = os.path.dirname(os.path.abspath(__file__))


class NeonatalAudioEngine:
    def __init__(self, random_state: int = 42):
        self.sample_rate = SAMPLE_RATE
        self.feature_keys = FEATURE_KEYS
        self._load_or_train(random_state)

    def _load_or_train(self, random_state: int):
        model_path = os.path.join(_MODEL_DIR, "cry_model.joblib")
        scaler_path = os.path.join(_MODEL_DIR, "cry_scaler.joblib")
        keys_path = os.path.join(_MODEL_DIR, "cry_features.json")
        if os.path.exists(model_path) and os.path.exists(scaler_path):
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            if os.path.exists(keys_path):
                with open(keys_path) as f:
                    self.feature_keys = json.load(f)
        else:
            self.scaler = StandardScaler()
            self.model = self._seed_training_data(random_state)

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------
    def _extract_features(self, audio: np.ndarray, sr: int) -> dict:
        f0 = librosa.yin(audio, fmin=CRY_FMIN, fmax=CRY_FMAX, sr=sr)
        cent = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=N_MFCC)
        bw = librosa.feature.spectral_bandwidth(y=audio, sr=sr)[0]
        rolloff = librosa.feature.spectral_rolloff(y=audio, sr=sr)[0]
        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        rms = librosa.feature.rms(y=audio)[0]

        feats = {
            "f0_mean": float(np.mean(f0)),
            "f0_std": float(np.std(f0)),
            "spectral_centroid_mean": float(np.mean(cent)),
            "spectral_centroid_std": float(np.std(cent)),
            "bandwidth_mean": float(np.mean(bw)),
            "bandwidth_std": float(np.std(bw)),
            "rolloff_mean": float(np.mean(rolloff)),
            "rolloff_std": float(np.std(rolloff)),
            "zcr_mean": float(np.mean(zcr)),
            "zcr_std": float(np.std(zcr)),
            "rms_mean": float(np.mean(rms)),
            "rms_std": float(np.std(rms)),
        }
        for i in range(N_MFCC):
            feats[f"mfcc_{i}_mean"] = float(np.mean(mfccs[i]))
            feats[f"mfcc_{i}_std"] = float(np.std(mfccs[i]))

        return feats

    # ------------------------------------------------------------------
    # Training data
    # ------------------------------------------------------------------
    def _seed_training_data(self, random_state: int):
        rng = np.random.default_rng(random_state)
        sr = self.sample_rate
        n_per_class = 150

        X, y = [], []
        for _ in range(n_per_class):
            feats = self._extract_features(_synthetic_audio("normal", rng, sr), sr)
            X.append([feats[k] for k in self.feature_keys])
            y.append(0)
        for _ in range(n_per_class):
            feats = self._extract_features(_synthetic_audio("distress", rng, sr), sr)
            X.append([feats[k] for k in self.feature_keys])
            y.append(1)

        X = np.array(X)
        y = np.array(y)
        X_scaled = self.scaler.fit_transform(X)

        model = RandomForestClassifier(
            n_estimators=100, max_depth=12, min_samples_split=4,
            class_weight="balanced", random_state=random_state,
        )
        model.fit(X_scaled, y)
        return model

    # ------------------------------------------------------------------
    # Public prediction API
    # ------------------------------------------------------------------
    def evaluate_cry(self, audio_buffer) -> dict:
        try:
            if isinstance(audio_buffer, bytes):
                audio, sr = librosa.load(
                    io.BytesIO(audio_buffer), sr=self.sample_rate, mono=True
                )
            else:
                audio, sr = librosa.load(
                    audio_buffer, sr=self.sample_rate, mono=True
                )

            if len(audio) < self.sample_rate * 0.1:
                return {
                    "classification": 0, "probability": 0.0, "risk_score": 0.0,
                    "anomaly_score": 0.0, "features": {}, "error": "Audio too short (< 100 ms)",
                }

            features = self._extract_features(audio, sr)
            vec = np.array([features[k] for k in self.feature_keys]).reshape(1, -1)
            vec_scaled = self.scaler.transform(vec)

            probs = self.model.predict_proba(vec_scaled)[0]
            classification = int(self.model.predict(vec_scaled)[0])
            probability = float(probs[1])

            f0_m = features.get("f0_mean", 500)
            f0_dev = min(abs(f0_m - 500) / 200.0, 1.0)
            sc_m = features.get("spectral_centroid_mean", 2000)
            sc_dev = min(abs(sc_m - 2000) / 1000.0, 1.0)
            anomaly = min(1.0, probability * 0.6 + (f0_dev + sc_dev) * 0.2)
            risk_score = round(anomaly * 95 + 5, 1)

            return {
                "classification": classification, "probability": round(probability, 4),
                "risk_score": risk_score, "anomaly_score": round(anomaly, 4),
                "features": features, "error": None,
            }

        except Exception as exc:
            return {
                "classification": 0, "probability": 0.0, "risk_score": 0.0,
                "anomaly_score": 0.0, "features": {}, "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Spectrogram data for Plotly + F0 track overlay
    # ------------------------------------------------------------------
    def compute_spectrogram(self, audio_buffer) -> dict:
        try:
            if isinstance(audio_buffer, bytes):
                audio, sr = librosa.load(
                    io.BytesIO(audio_buffer), sr=self.sample_rate, mono=True
                )
            else:
                audio, sr = librosa.load(
                    audio_buffer, sr=self.sample_rate, mono=True
                )

            D = librosa.stft(audio, n_fft=N_FFT, hop_length=HOP_LENGTH)
            D_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)
            freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)
            times = librosa.frames_to_time(
                range(D.shape[1]), sr=sr, hop_length=HOP_LENGTH
            )
            f0 = librosa.yin(audio, fmin=CRY_FMIN, fmax=CRY_FMAX, sr=sr)
            f0_times = librosa.frames_to_time(
                range(len(f0)), sr=sr, hop_length=512
            )

            return {
                "spectrogram": D_db, "frequencies": freqs, "times": times,
                "f0_track": f0, "f0_times": f0_times, "sr": sr, "error": None,
            }
        except Exception as exc:
            return {
                "spectrogram": None, "frequencies": None, "times": None,
                "f0_track": None, "f0_times": None, "sr": self.sample_rate,
                "error": str(exc),
            }

    # ------------------------------------------------------------------
    # Simulated cry generator for live demo
    # ------------------------------------------------------------------
    def generate_simulated_cry(self, category: str = "normal") -> bytes:
        sr = self.sample_rate
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        if category == "normal":
            f0 = 450 + 50 * np.sin(2 * np.pi * 3 * t)
            sig = (
                0.8 * np.sin(2 * np.pi * f0 * t)
                + 0.3 * np.sin(2 * np.pi * f0 * 2 * t)
                + 0.1 * np.sin(2 * np.pi * f0 * 3 * t)
            )
            sig *= np.exp(-2 * t) + 0.2
            sig += np.random.RandomState(0).randn(len(sig)) * 0.005
        else:
            f0_base = 700 + 200 * np.sin(2 * np.pi * 8 * t)
            brk = int(sr * duration * 0.4)
            f0_base[brk:] = f0_base[brk:] * 1.5
            sig = (
                0.6 * np.sin(2 * np.pi * f0_base * t)
                + 0.4 * np.sin(2 * np.pi * f0_base * 2.5 * t)
                + 0.2 * np.sin(2 * np.pi * f0_base * 4 * t)
                + 0.1 * np.sin(2 * np.pi * f0_base * 5.5 * t)
            )
            sig *= np.exp(-1.5 * t) + 0.3 + 0.2 * np.sin(2 * np.pi * 6 * t)
            sig += np.random.RandomState(1).randn(len(sig)) * 0.02

        sig /= max(np.abs(sig)) * 1.05
        buf = io.BytesIO()
        sf.write(buf, sig, sr, format="WAV")
        buf.seek(0)
        return buf.read()
