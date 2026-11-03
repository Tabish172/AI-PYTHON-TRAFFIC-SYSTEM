# AI Traffic Intelligence System

A working local Streamlit application for YOLOv8 vehicle detection, ByteTrack tracking,
calibrated two-line speed estimates, best-effort Indian plate OCR, evidence collection,
SQLite storage, analytics and simulated challan PDF/CSV exports.

## Run on this machine

Python 3.12 and a virtual environment have been prepared locally. In PowerShell:

```powershell
cd C:\Users\aaqib\AI-PYTHON-TRAFFIC-SYSTEM
.\.tools\uv.exe pip install --python .venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Or activate the environment and use the requested standard command:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

On a new computer with Python 3.11/3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

`requirements-lock.txt` records the exact versions installed and tested on this Windows
machine. Use it in place of `requirements.txt` to reproduce this environment.

Open http://localhost:8501. Select **Upload Traffic Video** and **Start new scan**.
The supplied WhatsApp video is copied to `uploads/traffic_sample.mp4` and selected by
default. The original in Downloads is untouched. Upload MP4, MOV or AVI to scan other footage.
The surveillance page replays files; it does not connect to a camera.

## Model and processing

First scan downloads official `yolov8n.pt` through Ultralytics into `models/`. Alternatively,
place trusted Ultralytics YOLOv8 nano weights at `models/yolov8n.pt` before starting.
Internet is required for initial model downloads. The model persists for a scan, and each
session owns its tracker to prevent cross-user ID contamination. CPU is default;
CUDA requires a compatible GPU and PyTorch installation. Every decoded frame is processed
once, with short batches so Stop works between batches. Keep the scanning page open while
processing; navigation pauses processing until you return. Start new scan creates a new
run and intentionally counts the footage again. Dashboard metrics are scoped to one run.

Run the provided video from the terminal (detection only):

```powershell
.\.venv\Scripts\python.exe scan_video.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Calibration

Without calibration, boxes remain yellow, speed is unknown and no fines are generated.
For a fixed camera, choose the travel axis and position reference lines A and B using the
preview. Each line must represent a real road cross-section on the same travel path.
Measure their physical separation **along the road**, enter meters, then confirm the
measurement. The bottom center of a tracked box must cross both lines.

Crossing times are interpolated between frames; elapsed time uses frame index / source
FPS. Estimated speed is `distance_m / elapsed_seconds * 3.6`, not raw pixel movement.
The default threshold is 80 km/h. Estimates require correct geometry, visible ground
contact points and constant-frame-rate footage. Moving cameras, camera cuts, angled
cross-sections, sloping roads, lane-dependent distances and variable-frame-rate videos
can invalidate estimates. Transcode variable-frame-rate input to constant frame rate
before analysis. No distance can be reliably inferred from the supplied footage alone.
Long tracking gaps reset pending crossings. ID switches can still cause counting errors.

## OCR and demo fines

Enable OCR before starting a calibrated scan. EasyOCR downloads English models on first
use. Rectangular candidates are extracted from a violating vehicle crop, enhanced and
read. Recognized text must match a supported Indian registration pattern; otherwise the
application records **Number Plate Not Recognized**. Small or blurred plates may be
unreadable, and even matching text is an unverified candidate. OCR errors do not stop
vehicle detection. This is a heuristic plate localizer, not a trained plate detector.

Fines are **DEMO** amounts, configurable per scan. No government fines, owner lookup,
payment service or official notices are issued. Each `(run_id, track_id)` has at most
one challan. UTC dates describe processing time, not the original recording date.
Evidence and annotated MP4 files are stored locally. Challan Management supports search,
type/date/status filters, demo status updates, CSV exports and individual PDFs.

## Storage and troubleshooting

- `database/traffic.db`: scan settings, tracks and demo challans.
- `reports/`: annotated MP4 files (MPEG-4 codec; VLC recommended).
- `evidence/`: violation images. Keep these files with the database for PDF exports.
- Model download failure: check internet access or manually supply trusted weights.
- Invalid/corrupted video: re-encode to a supported constant-frame-rate MP4.
- No detections: lower confidence, raise resolution or use clearer traffic footage.
- No speeds: verify calibration and vehicles crossing both lines without a long gap.
- Slow processing: choose 640 resolution, disable OCR or configure CUDA.
- Missing OCR: reinstall requirements; detection can run with OCR disabled.
- Database error: ensure the project is writable and close external exclusive DB locks.
- Abrupt process termination can leave a run marked Running; start a new scan. Interrupted
  videos may lack a finalized MP4 container. Stop the scan before closing the app.

The app is designed for local use. Video files and evidence are excluded from Git.
Review Ultralytics and other dependency licenses before redistributing commercially.

API references: [Ultralytics tracking](https://docs.ultralytics.com/modes/track/)
and [Streamlit fragments](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment).

## Gemini AI Intelligence Center

The original `app.py` now includes six AI workspaces: Traffic Analyst, Traffic Assistant,
Violation Intelligence, Traffic Predictions, Report Generator and Recommendations.
Detection, tracking, OCR, speed calculation and demo challan decisions remain in Python.
Gemini has no database write tool, SQL execution tool or enforcement authority.

Install the updated dependencies and run the same application:

```powershell
.\.tools\uv.exe pip install --python .venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Configure your private `.env` using `.env.example` as the format (do not replace an
existing configuration). The application reads `GEMINI_API_KEY` and optional
`GEMINI_MODEL=gemini-flash-latest`. Existing process environment variables take priority;
the application does not overwrite them or modify `.env`. Keep your real key out of
source control. `.env` and its variants are ignored. There is no frontend key field.
The model alias follows Google's supported Flash model; a model ID can be set in `.env`.
Integration uses the official `google-genai` SDK, not the legacy generativeai package.

Use **Test Gemini connection** inside the AI center or run:

```powershell
.\.venv\Scripts\python.exe check_gemini.py
```

The live test checks connectivity, a database-backed chatbot request and a report/PDF.
It prints sanitized status messages only. API authorization, quota, model and network
failures are caught without printing the raw SDK exception. Requests have a 25-second
timeout, no automatic retry storm, a short inter-call limit and a one-minute cooldown
after failures. Successful identical requests are cached for five minutes, up to 64
entries. Database views have a 15-second cache and a manual refresh; chat reads a fresh
SQLite snapshot for every question. Calls occur only after explicit user actions.

### Grounding and data meaning

Python queries SQLite with parameterized filters and calculates all facts. To prevent
invented records, Gemini returns a validated structured selection of existing fact and
recommendation IDs. Python renders the selected verified statements as the explanation.
This intentionally constrains prose: Gemini organizes findings and priorities but cannot
invent a new plate, number, fine, speed or causal claim. Invalid references are rejected.
The assistant passes a bounded history of prior questions for conversational context.
Unsupported requests are flagged; the verified fact table is always available.

Only structured summaries and user questions go to Google. Video, evidence images, source
file paths and stored registration text are not included. Registration and evidence remain
available locally in Violation Intelligence. The latest 20 violations and latest 31 daily
breakdowns are available to the model; aggregates cover the entire selected period and
full filtered records remain available for CSV export.

Dates default to **Asia/Kolkata scan processing dates**, not filming dates. "Today",
"yesterday", "this week" and "this month" in chat override the date controls while retaining
the selected scan filter. Use Custom dates for other periods. Daily, weekly and monthly
reports use the selected ending date (or today) to choose the corresponding calendar
period. Reports export PDF, factual CSV and underlying tracks. All-history counts can
include repeated scans; counts are tracking records, not a verified census.

When Gemini is unavailable, clearly labeled local analysis and report exports remain
functional. Unknown speeds are never treated as zero or as speed-limit compliance.
The above-80 statistic is distinct from stored violations against each scan's own limit.

### Forecasts

The existing database has no reliable original recording dates or observation coverage.
In **AI Traffic Predictions**, add a verified original recording timestamp and fixed camera
identifier for each completed scan. Duration is read from the original file, and a source
SHA-256 prevents repeated scans of the same video from creating artificial history.
No original files or existing records are modified by this metadata entry.

Ridge regression uses weekday features and time trend to forecast observed tracks/minute
for three comparable recording windows. It requires at least 14 distinct recording days
from the same camera and recording hour, durations within 10% of the median, clips of at
least one minute, and a latest observation no older than seven days. The final three days
are held out; a model worse than the historical-mean baseline is withheld. Error bands are
heuristic, not calibrated confidence intervals. Historical overspeed percentages require
at least 20 calibrated tracks per observation. These are forecasts of sampled arrival
rates, **not physical density or measured congestion**. Congestion prediction remains
unsupported without occupancy/capacity data; the app says so rather than fabricating it.

## Delete old history

Open **History Management**, select completed/stopped/failed scans, check the deletion
box and choose **Delete selected history**. The scan, vehicles, challans and recording
metadata are moved transactionally to a local Trash archive and disappear from active
dashboards and AI queries. Choose **Restore selected history** to restore all records.
Running scans cannot be deleted. No data is removed merely by opening the page.
Source videos, evidence and exported reports remain on disk so restoration is possible;
this reversible deletion does not reclaim disk space or purge previously downloaded files.
The current session's AI snapshots/conversation are cleared after deletion.

## Background image

In **Settings**, upload a JPG, PNG or WebP and click **Apply background image**. The app
stores a local normalized JPEG at `assets/traffic_background.jpg` and applies a responsive
full-page image with a dark readability overlay. No image service or external URL is used.

## Integration verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover the original scanner, calibration, evidence/PDF exports, all AI workspaces,
SQLite aggregation and timezone boundaries, grounding rejection, safe API errors,
forecast eligibility, and reversible history deletion/restoration. Synthetic records
exist only in isolated test fixtures, never in the production database. Live Gemini
availability must be checked separately; a passing local test suite does not imply a
working API credential or available Google quota.

SDK reference: [official Google Gen AI Python SDK](https://googleapis.github.io/python-genai/).

### Files added or changed for this integration

Added:
- `modules/gemini_service.py`: private SDK client, structured grounding and error handling.
- `modules/traffic_intelligence.py`: SQLite snapshots, facts, date scopes and local answers.
- `modules/traffic_forecasting.py`: verified recording metadata and guarded ML forecasts.
- `modules/ai_center.py`: six AI workspaces within the existing Streamlit app.
- `database/history.py`, `modules/history_ui.py`: transactional Trash and restore workflow.
- `utils/ai_reports.py`: AI report PDF and CSV exports.
- `utils/app_theme.py`: local background-image loading and readability overlay.
- `check_gemini.py`: sanitized opt-in live API smoke test.
- `tests/test_intelligence.py`: grounding, database, forecasting and history tests.
- `.env.example`: credential configuration template; `.env` is local and Git-ignored.
- `.streamlit/config.toml`: navy/charcoal theme with blue/purple chart colors.

Modified: `app.py`, `requirements.txt`, `requirements-lock.txt`, `.gitignore`,
`tests/test_app.py`, and this `README.md`. Existing detection, tracking, calibration,
OCR and challan-generation modules were preserved.
