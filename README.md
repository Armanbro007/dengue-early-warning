# DengueWatch: Ward-level Dengue Early Warning

[![tests](https://github.com/Armanbro007/dengue-early-warning/actions/workflows/tests.yml/badge.svg)](https://github.com/Armanbro007/dengue-early-warning/actions/workflows/tests.yml)
[![readme quick start](https://github.com/Armanbro007/dengue-early-warning/actions/workflows/quickstart.yml/badge.svg)](https://github.com/Armanbro007/dengue-early-warning/actions/workflows/quickstart.yml)

**Rain today shows up as dengue cases in about three weeks.** DengueWatch uses that lag to forecast dengue cases for every ward in Dhaka North, Dhaka South, Chattogram, Gazipur and Narayanganj **2, 3 and 4 weeks ahead**. It ranks wards as Low / Medium / High / Critical, explains *why* each ward is at risk, and drafts an action briefing. City health officers can then send larvicide teams and hospital supplies to the right wards *before* admissions spike.

Built for the **EDU AI Engineering Hackathon 2026, Phase 1: "AI for Urban Dengue Outbreak"** by team **Vibe Engineers**.

**Live demo: [denguewatchedu.streamlit.app](https://denguewatchedu.streamlit.app/)** (free hosting: if the app is asleep, press the wake-up button and give it about a minute).

![DengueWatch overview page](docs/screenshots/overview.png)

**Two languages.** A switch at the top right shows the whole dashboard in **English or Bangla (বাংলা)**, including the officer briefing, chart labels, dates and numbers. The Bangla is written the way a city corporation health office would say it, not translated word for word. Your city, week and look-ahead settings stay the same when you switch.

![DengueWatch overview page in Bangla](docs/screenshots/overview_bangla.png)

## Quick start (about 2 minutes)

Requires **Python 3.10 or newer** (checked on 3.11 to 3.15) and git. No API keys needed. These exact steps run on fresh Windows, macOS and Linux machines on every push (see the *readme quick start* badge above).

```bash
git clone https://github.com/Armanbro007/dengue-early-warning.git
cd dengue-early-warning
```

Then run these three commands from inside that folder. They use the environment's Python directly, so there is nothing to activate (this also avoids PowerShell's "running scripts is disabled" error).

| | Windows (PowerShell or Command Prompt) | macOS / Linux |
|---|---|---|
| 1. Create the environment | `py -m venv .venv` | `python3 -m venv .venv` |
| 2. Install | `.venv\Scripts\python -m pip install -r requirements.txt` | `.venv/bin/python -m pip install -r requirements.txt` |
| 3. Start | `.venv\Scripts\python -m streamlit run app.py` | `.venv/bin/python -m streamlit run app.py` |

**Open http://localhost:8501 in your browser** once the terminal says "You can now view your Streamlit app". The dataset (`data/`) and trained models (`models/`) are included, so nothing else is downloaded. Install takes 1 to 2 minutes on a normal connection; the app itself is ready in a few seconds. If your scikit-learn version differs from ours, the app retrains its models on first start (about 10 seconds).

**If something goes wrong**

- *"'py' is not recognized"* on Windows: Python is not installed. Install it from python.org (3.12 is a safe choice), open a new terminal and run step 1 again. If you ticked "Add python.exe to PATH" when installing, `python -m venv .venv` works too.
- *"Python was not found; run without arguments to install from the Microsoft Store"*: you typed `python` instead of `py`. Use `py -m venv .venv` as in step 1.
- *"ensurepip is not available"* on Ubuntu or Debian: run `sudo apt install python3-venv`, then step 1 again.
- *"Port 8501 is not available"*: an older copy of the app is still running. Close that terminal (or press Ctrl+C in it) and start again. To use another port instead: add `--server.port 8502` to the run command.
- *You see an old version of the dashboard*: same cause as above, or an old download. Stop every running copy, run `git pull` in the folder, and start again.
- Always run the commands from inside the `dengue-early-warning` folder, so the app finds its settings, fonts and models.

Optional (use the same `.venv\Scripts\python` or `.venv/bin/python` in place of `python`):

```bash
cp .env.example .env        # (Windows: copy .env.example .env) then add GEMINI_API_KEY for AI-worded briefings
python scripts/train.py     # rebuild features, evaluation (metrics.json) and models (~35 s)
python -m pytest            # 36 tests: lag correctness, no leakage, explanations, retries/fallbacks, every page loads in English and Bangla
python scripts/ingest.py new_weeks.csv   # add new weekly data and retrain (--reset to undo)
```

Set `ALLOW_NETWORK=0` in `.env` to run fully offline.

## What the dashboard does

| Page | What an officer gets |
|---|---|
| **Overview** | The answer first: how many wards will reach high risk and when, a four-step picture of the rain-to-cases delay, each city at a glance, and the wards to act on first. |
| **Ward priorities** | All wards ranked by expected cases with a likely range and risk level. Wards **getting worse** (low or medium today, high or critical soon) are flagged. Includes an action briefing that follows the language switch, and a CSV export. |
| **Why this ward?** | Plain bars showing how recent rain, humidity, temperature and drainage, crowding and sanitation push the forecast above or below normal for the season; a "rain now, cases later" chart; a rain what-if slider; the ward's forecast-vs-real track record. |
| **Season calendar** | Every ward × every week of a season, coloured by forecast risk (or real risk, or forecast error). |
| **Live forecast** | The same model fed with this week's real and forecast weather from Open-Meteo: one API call for all cities, cached, with offline fallbacks. |
| **How accurate is it?** | Plain-language results on unseen years first, then the year-by-year backtest, lag evidence, baselines and confusion matrix for reviewers. |
| **Add weekly data** | Upload the latest ward reports (CSV). The file is checked, merged and the models retrain in about 15 s. Reset any time. |

The dashboard opens on **2 June 2025**, a week the model never saw during training. 56 of the 60 wards were still Low that week. The system flagged 46 wards as High for 23 June, and 52 of the 60 wards actually reached High or Critical.

## How it works (short version)

1. **Weather lag pipeline** (`src/dengue/features.py`): rainfall lags of 0-6 weeks, humidity lags of 0-4 weeks, temperature lags and rolling rain totals, computed **per `ward_id`**, plus ward vulnerability and season.
2. **Prediction engine** (`src/dengue/model.py`, `engine.py`): gradient-boosted trees with a Poisson loss, one per horizon, with monotonic constraints (more rain never lowers risk). Saved with joblib. The 80% ranges are calibrated on years the model did not train on.
3. **Tiers and explanations** (`tiers.py`, `explain.py`): Low < 2, Medium 2-5, High 5-10, Critical ≥ 10 cases per ward per week. Exact Shapley contributions of each driver group.
4. **Validation** (`evaluate.py`): trained 2016-2022, tuned 2023, tested on 2024-2025 (never shuffled).

| Test 2024-2025, 3 weeks ahead | DengueWatch | Naive "same as this week" |
|---|---|---|
| MAE in monsoon season (Jun-Oct), cases/ward/week | **2.19** | 4.14 |
| MAE, all weeks | **1.02** | 1.87 |
| High/Critical ward-weeks caught (recall) | **85%** | 61% |

Details, diagrams and the efficiency and failure-handling design are in **[ARCHITECTURE.md](ARCHITECTURE.md)**.

## Project structure

```
app.py                  Streamlit entry (navigation + shared controls)
ui_common.py            cached engine, chart styling, sidebar
views/                  one file per dashboard page
ui_text.py              every English and Bangla string on the dashboard
static/fonts/           bundled fonts, so the design works offline
src/dengue/
  config.py             all settings: horizons, tiers, split dates, network limits
  data.py               load + validate the dataset (local CSV, sheet fallback)
  features.py           per-ward lag features, targets, seasonal reference
  model.py              train / save / load / predict, conformal ranges
  evaluate.py           chronological metrics, baselines, backtest
  engine.py             prediction engine used by the UI (and a future API)
  explain.py            Shapley driver breakdown, rain what-if
  tiers.py              risk tiers + escalation flags
  briefing.py           officer briefing (English/Bangla): template or optional cached LLM
  i18n.py               Bangla names, digits and dates shared by the briefing and the pages
  ingest.py             add new weekly data, retrain, reset
  weather_api.py        Open-Meteo client with cache and fallbacks
  http.py               retries, backoff, Retry-After, circuit breaker
scripts/train.py        rebuild models + models/metrics.json
scripts/ingest.py       add new weekly data from the command line
tests/                  pytest suite (also run by GitHub Actions on Linux and Windows)
data/                   official hackathon dataset (60 wards × 522 weeks)
models/                 trained model bundle + evaluation metrics
```

## AI tools and external services disclosure

| Tool / service | Type | What it was used for |
|---|---|---|
| **Claude (Anthropic), via Claude Code** | AI coding assistant | Analysing the brief and dataset, planning the architecture, and writing most of the code, tests and documentation under the team's direction. The team reviewed, ran and can explain all code. |
| **Google Gemini API** (`generativelanguage.googleapis.com`, default model `gemini-2.5-flash`) | LLM API, **optional, off by default** | Rewording the officer briefing in plain language from model numbers only. Used only if `GEMINI_API_KEY` is set (the "Reword with AI" switch appears only then); otherwise a template is used. |
| **Open-Meteo Forecast API** (`api.open-meteo.com`) | Weather API, free, no key | Live weather for the Live forecast page. |
| **Google Sheets CSV export** | Dataset source | Official hackathon dataset; downloaded only if `data/bangladesh_dengue.csv` is missing. |

No other AI services or external APIs are used. Open-source libraries: pandas, NumPy, scikit-learn, joblib, PyArrow, Streamlit, Plotly, Requests, python-dotenv, pytest (see `requirements.txt`). Fonts: Geist, Geist Mono and Noto Sans Bengali (SIL Open Font License, bundled in `static/fonts`). No significant third-party code snippets were copied.

## Limitations and honest notes

- The dataset is the organisers' ward-week dataset (2016-2025). It has density but no population counts, so we forecast case **counts**, not incidence per 100k.
- Live mode uses city-level weather for all wards in a city. Ward differences come from ward attributes.
- November is dry season, so live risk is Low right now. The historical replay shows how the system behaves during the monsoon.
- Forecast ranges are 80% ranges: about 1 in 5 weeks will fall outside them.
