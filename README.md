# VeriBar / VeriShield

VeriBar is a Chrome Manifest V3 extension plus a local FastAPI service. It scans article-like text as pages load and scroll, adds a compact bar above each item, and shows the current page's average model score in a corner HUD and the toolbar popup. The bar expands to show the analysis method, model confidence, and scraped word count.

## Run locally

Use Python 3.10 or newer. From this repository:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r verishield-backend/requirements.txt
HF_HOME=.cache/huggingface uvicorn server:app --app-dir verishield-backend --host 127.0.0.1 --port 8001
```

The first text analysis downloads the approximately 500 MB [RoBERTa GPT-2 detector](https://huggingface.co/openai-community/roberta-base-openai-detector) from Hugging Face. Subsequent runs use the local `.cache/huggingface` cache, including without a network connection. Check `http://127.0.0.1:8001/health` for service status; `loaded: false` means the model has not loaded yet. Port 8001 is used because port 8000 is occupied on this machine.

In Chrome, open `chrome://extensions`, enable Developer mode, choose **Load unpacked**, and select the `verishield-extension` folder. Reload any already open page to inject VeriBar. The toolbar popup can turn scanning off or rescan the current tab.

For a controlled demo, run `python3 -m http.server 8765 --bind 127.0.0.1` from this repository and open `http://127.0.0.1:8765/demo/` in Chrome. The page contains sample articles, an image, and a button that adds another article while VeriBar is running.

## What the score means

The specified model was trained to distinguish GPT-2 generated text from WebText, primarily in English. A “GPT-2-like” percentage is the model's `Fake` class output for up to 512 tokens. It is an estimate, not verified authorship, a general AI detector, or a fact check. The model card warns against using it to make serious allegations about writing from newer models.

When the server is unreachable or the model is unavailable, the extension shows a clearly labelled **local pattern score** based on sentence-length variation and a few phrase markers. That number is not an AI probability. Text under 30 words is marked too short when the server responds. Audio, video, image manipulation, lip-sync drift, vocoder artifacts, and C2PA provenance are **not analyzed** in this MVP; media receives a status bar that says so.

The extension reads page text and sends up to 30,000 HTML characters per item to the API on `127.0.0.1`. The API binds only to localhost by default in the command above. No page content is sent to a hosted VeriBar service. The extension's `<all_urls>` content-script permission is necessary for automatic scanning across sites. Chrome internal pages and other protected pages cannot be scanned.

## Develop and test

The backend is in `verishield-backend/server.py`; the extension is in `verishield-extension`. To run the lightweight backend tests, install `pytest` and `httpx`, then run:

```bash
python -m pytest verishield-backend/test_server.py
```

These tests stub inference and do not download model weights. A real model smoke test requires installing the full requirements and running the server while online for the first download.
