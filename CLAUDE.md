# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`meetingsummary` is a local-first, privacy-respecting meeting assistant. It records system + microphone audio, transcribes with a local ASR model (FunASR/SenseVoice), chunks the transcript, and uses a local LLM (Ollama by default) to produce meeting notes. The GUI is PyQt6.

The product is a Chinese-language app — all user-facing strings and prompt templates are in Chinese.

## Common Commands

All commands assume `poetry` is installed.

| Action | Command |
|---|---|
| Install dependencies | `poetry install` |
| Run the app (dev) | `poetry run python meeting_summarizer/main_window.py` |
| Lint (flake8) | `poetry run flake8 meeting_summarizer` |
| Format (black) | `poetry run black meeting_summarizer` |
| Sort imports | `poetry run isort meeting_summarizer` |
| Type-check | `poetry run mypy meeting_summarizer` |
| Run tests | `poetry run pytest` |
| Run a single test | `poetry run pytest tests/test_<file>.py::test_<name>` |
| Build Windows installer | `cicd/build_installer.cmd` (runs PyInstaller against `meeting_summarizer/main_window.spec`) |
| Double-click launch (macOS) | `open MeetingSummarizer.app` (or just double-click the bundle in Finder) |

There is no test suite yet — `tests/` is configured in `pyproject.toml` but empty. When adding tests, follow the `test_*.py` naming convention and put them under `meeting_summarizer/tests/` (or top-level `tests/`).

## Architecture

The app is organized as a single-page-of-pages PyQt6 application driven by a `QStackedWidget` with slide animations (see `main_window.py:32` `SlideStackedWidget`). Each stage of the meeting pipeline is a separate widget that is shown as the user progresses.

### Pipeline

```
Record (audio_recorder)  →  Transcribe (speech_to_text)  →  Chunk + Summarize (text_processor + utils)
       │                            │                                    │
       ▼                            ▼                                    ▼
  audio/*.opus|mp3|wav      transcript/transcript_*.txt           summary/summary_vNNN.md
                            transcript/proofread.md
```

Each user meeting becomes a `MeetingRecordProject` (in `utils/MeetingRecordProject.py`) — a directory tree of `audio/`, `transcript/`, `summary/`, and a `project_info.json` manifest. The project root lives at `~/.meeting_summary/projects/<project_name>/`.

### Module map

- **`meeting_summarizer/main_window.py`** — App entry point (`python main_window.py`). Owns the `MeetingRecordProject` and switches between widgets.
- **`meeting_summarizer/recording_window.py`** — Recording UI. Spawns a `RecordingThread` (QThread) that calls `audio_recorder.recorder.record_audio`. Live waveform uses `pyqtgraph`.
- **`meeting_summarizer/processing_window.py`** — Post-record pipeline: transcription + chunking + summarization kickoff.
- **`meeting_summarizer/transcript_window.py`** — Transcript viewer/editor and proofread trigger.
- **`meeting_summarizer/summary_window.py`** — Generated summary viewer with export.
- **`meeting_summarizer/history_window.py`** — Modal dialog listing past projects (loaded from `~/.meeting_summary/projects/`).
- **`meeting_summarizer/settings_window.py`** — Edits the persisted config (audio, transcription, summary, output, project, llm sections).
- **`audio_recorder/recorder.py`** — `record_audio()` captures system audio via `soundcard` (loopback) and optional mic, writes time-segmented files (default 5 min each), then merges them. Honors `audio.format` / `audio.bitrate` from settings; auto-falls-back to WAV if `ffmpeg` is missing.
- **`speech_to_text/transcriber.py`** — `SenseVoiceTranscriber` (FunASR `iic/SenseVoiceSmall`) with VAD. `transcribe_audio()` is the public entry. Auto-detects language.
- **`text_processor/summarizer.py`** — `MeetingSummarizer`: chunk → per-chunk LLM summary → merge. Loads prompt from `text_processor/prompt/summary.txt`.
- **`text_processor/meeting_analyzer.py`** — Classifies meeting type (discussion vs. lecture) and proofreads transcripts using domain keywords.
- **`utils/MeetingRecordProject.py`** — Project CRUD; central place for filename conventions (`audio_<timestamp>.wav`, `transcript_<timestamp>.txt`, `summary_v<N>.md`).
- **`utils/chunker.py`** — `TranscriptChunker`: token-aware chunking via `tiktoken` (`cl100k_base`, `max_tokens=4000`). Detects timestamped vs. plain text and uses NLTK `sent_tokenize` for sentence splitting (NLTK data is bundled/auto-downloaded).
- **`utils/llm_factory.py`** — Plain-`requests` providers: `OllamaProvider`, `VLLMProvider`, `OpenAIProvider`, `DeepseekProvider`. Used by `summarizer.py`.
- **`utils/llamaindex_llm_factory.py`** — LlamaIndex-based providers (Ollama, OpenAI, OpenLLM). Used by the notes generators.
- **`utils/notes_processor_factory.py`** + `utils/processor_types.py` — Strategy selector for `proofreading | lecture | meeting` processors.
- **`utils/llm_proofreader.py`**, **`utils/meeting_notes_generator.py`**, **`utils/lecture_notes_generator.py`** — The three concrete `ProcessorType` implementations.
- **`utils/prompts/*.txt`** and **`utils/prompts/*.md`** — Prompt templates (also mirrors of some in `text_processor/prompt/`).
- **`utils/flexible_logger.py`** — Shared logger; use this rather than `print` for anything that should appear in `meeting_summarizer.log`.
- **`config/settings.py`** — `Settings` singleton. Persists to `~/.meeting_summary/meeting_summary_config.json`. Sections: `audio`, `transcription`, `summary`, `output`, `project`, `llm`. **Note:** `summarizer.py:15` reads `settings._settings["llm"]` directly (private attr) rather than via the public `get()` — preserve this pattern or refactor both sides.

### Recording specifics (`audio_recorder/recorder.py`)

- `record_audio()` uses **function attributes** (`record_audio.stop_flag`, `.pause_flag`, `.use_microphone`, `.current_audio_data`) as the cross-thread control channel. The `RecordingThread` in `recording_window.py` flips these from the UI.
- Segments are saved as `recording_partNNN.<format>`, then merged into `recording_merged.<format>`. If ffmpeg is missing, output silently falls back to WAV.
- The waveform panel reads `record_audio.current_audio_data` on a `QTimer`.

### LLM prompt templates

`utils/prompts/` and `text_processor/prompt/` contain the canonical templates (`summary.txt`, `meetingtype.txt`, `class.txt`, `discussion.txt`, `meeting_notes.md`, `lecture_notes.md`, `domain_keyword.txt`). When changing prompts, update both directories if the same prompt exists in both — `summarizer.py` reads from `text_processor/prompt/`, but the factory and analyzers under `utils/prompts/`.

## Environment Requirements

- Python 3.10–3.13 (per `pyproject.toml`; `target-version = py311` for black)
- **ffmpeg** on `PATH` for non-WAV recording (Opus/MP3). `install_ffmpeg.ps1` is a Windows helper; on macOS/Linux install via the system package manager. If absent, the recorder falls back to WAV automatically.
- **Ollama** running locally (default `http://localhost:11434`) with a pulled model — `qwen2.5` is the default in `config/settings.py`.
- **NLTK** data: `chunker.py` will auto-download `punkt`/`punkt_tab` to `~/AppData/Roaming/nltk_data` on first run (the Windows path is hardcoded; on macOS this resolves under `~`).
- **FunASR SenseVoice model** (`iic/SenseVoiceSmall`): downloaded from ModelScope on first transcribe; ensure network access or pre-stage the model.

## Build / Packaging

- `meeting_summarizer/main_window.spec` is the PyInstaller spec. Run `pyinstaller --clean main_window.spec` (the spec uses Windows backslashes in `datas=` — adjust to forward slashes on macOS/Linux).
- CI script: `cicd/build_installer.cmd` (Windows-only batch).
- i18n: translation workflow is `cicd/translation/gettext.sh`; `.po` files live in `meeting_summarizer/locales/{en,zh-cn}/LC_MESSAGES/`.

## Conventions

- **Logging:** use `from utils.flexible_logger import Logger; logger = Logger(name=__name__, ...)`. Do not sprinkle `print()` in production code paths — the existing recorder/transcriber are exceptions because they predate the logger and are noisy on purpose during long runs.
- **File path handling:** all internal module imports use the implicit `meeting_summarizer/` package root (no `sys.path` hacks). Run scripts from the repo root so the `meeting_summarizer` package is importable.
- **Resource paths:** use the `get_resource_path()` helper defined in each window module — it handles both dev and PyInstaller-bundled layouts.
- **Settings mutations:** go through `Settings.set(section, key, value)` so they persist. Direct mutation of `_settings` (as `summarizer.py` does for the `llm` block) is a known shortcut — avoid adding new call sites in that style.
- **Timestamps in transcripts:** chunker regex supports `[HH:MM:SS]`, `HH:MM:SS`, and `(MM:SS)` — keep all three working when touching the regex.
- **Language:** user-facing strings are Chinese; keep comments and docstrings bilingual (Chinese explanation, English function/var names is the existing pattern).
