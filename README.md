# Sadhana

**Sadhana** is a real-time Indian classical swara pitch-coaching prototype. The primary estimator is **FFT-based DSP**; it does not use YIN and does not modify or pitch-shift the microphone audio.

## Architecture

- **Frontend:** React + Vite; captures microphone audio and renders one live scene that combines the estimated F0, cents deviation, the live FFT spectrum, and the time-domain frame.
- **Backend:** Python + FastAPI WebSocket; analyzes audio frames and streams pitch estimates plus compact spectrum data to the browser.
- **Primary pitch method:** Hann-windowed real FFT, harmonic summation, parabolic peak interpolation, and short median smoothing across frames.
- **Pitch feedback:** Compares the measured pitch class with a target swara relative to the user's Sa reference, then reports flat / in tune / sharp.

## Requirements

- Python 3.10+
- Node.js 18+
- Microphone permission (localhost is allowed by browsers; deployed sites need HTTPS and a secure WebSocket)

## Run the backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Run the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL printed in the terminal (usually `http://localhost:5173`). The backend host is configured through the `VITE_BACKEND_HOST` variable in `frontend/.env` (default `127.0.0.1:8000`); change it there to point the frontend at a different backend without editing source.

## Deploy on Render

Deploy as two services: a Python **Web Service** for the DSP backend and a **Static Site** for the Vite build. Create the backend first so you know its hostname.

### 1. Backend — New > Web Service

| Field | Value |
| --- | --- |
| Name | `sadhana-api` |
| Root Directory | `backend` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |
| Instance Type | Free (or Starter) |

Environment variables:

- `ALLOWED_ORIGINS` — comma-separated browser origins allowed to call the API, e.g. `https://sadhana.onrender.com`. Defaults to the two localhost dev origins.
- `PYTHON_VERSION` — e.g. `3.12.8`, to pin the interpreter.

The service must bind `0.0.0.0` on `$PORT` (Render's default is 10000). Do not keep Render's default `gunicorn` start command — gunicorn is not a dependency of this project.

### 2. Frontend — New > Static Site

| Field | Value |
| --- | --- |
| Name | `sadhana` |
| Root Directory | `frontend` |
| Build Command | `npm ci && npm run build` |
| Publish Directory | `dist` |

Environment variable:

- `VITE_BACKEND_HOST` — the backend hostname **without** a scheme or trailing slash, e.g. `sadhana-api.onrender.com`. The page protocol decides `ws://` versus `wss://`.

`VITE_BACKEND_HOST` is read at **build time** and baked into the bundle, so changing it requires a new deploy of the static site.

### Free-tier notes

- A free web service spins down after 15 minutes without inbound traffic and takes about a minute to wake up. The frontend reconnects automatically with exponential backoff and shows a **Reconnecting** state, so a session recovers on its own.
- Microphone capture needs a secure context; `https://*.onrender.com` qualifies.

## How to use

1. Start the backend and frontend.
2. Set the reference Sa frequency in Hz.
3. Choose the swara you intend to sing and set the tolerance.
4. Click **Start microphone** and allow browser access.
5. Sustain a note. Watch the FFT peaks, estimated F0, cents deviation, and coaching feedback.
6. Stop the microphone when finished.

## DSP pipeline

1. Capture mono floating-point audio from the browser.
2. Maintain a rolling frame of about 256 ms at the browser's native sample rate.
3. Remove the frame's DC component and apply a Hann window to reduce spectral leakage.
4. Compute the one-sided spectrum with `numpy.fft.rfft`; zero-pad to provide a denser sampled spectrum for peak interpolation.
5. Score F0 candidates using energy near their harmonic multiples. This helps when the fundamental is weaker than its upper harmonics.
6. Refine the selected salience peak with three-point parabolic interpolation.
7. Apply a five-frame median to the cents error to reduce momentary jitter.
8. Compare against the selected swara and return coaching feedback.

### Important interpretation notes

- Zero-padding makes the displayed spectrum smoother and can aid interpolation, but it does **not** increase the true frequency resolution of the original frame.
- The displayed confidence value is a heuristic, not a calibrated probability.
- When the strongest evidence points to an octave harmonic, the app compares the pitch class at the nearest octave to the target. The displayed F0 remains the measured frequency; the comparison frequency is shown separately when it differs.
- Swara positions currently use equal-tempered semitone ratios relative to Sa as a starting profile. Indian classical intonation can vary by raga, style, and performer; future versions should support custom ratios and raga-specific targets.
- This is a prototype, not a validated clinical or performance-grade tuner. Test with real singers and labelled recordings before relying on its accuracy. Background noise, polyphonic audio, gamakas, vibrato, and weak fundamentals can still confuse a simple harmonic-summation estimator.
- Browser `ScriptProcessorNode` is used for compatibility in this starter; a production version should move capture into `AudioWorklet`.

## Run synthetic DSP checks

```bash
cd backend
python -m unittest test_dsp.py
```

The tests cover a harmonic-rich tone, a missing fundamental / octave-equivalence case, and silence rejection. They are smoke tests, not a full accuracy benchmark.
