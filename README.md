# ai_convo_summarizer

Three Python utilities for turning long-form conversations (AI chat transcripts, meeting notes, project docs) into compact, portfolio-ready evidence summaries — built from a real-world use case: consolidating 11 AI-assisted software-building conversations into an FDE/APM portfolio dossier.

## What's inside

| File | Purpose |
|------|---------|
| `chunker.py` | Smart chunker that splits long text into context-sized pieces (chapter-aware, strips forum/nav boilerplate, drops metadata, enforces a max token limit). |
| `summarize.py` | Story/document summarizer — one-pass or chunked (smart via `chunker.py` or dumb length-based), with recursive multi-level compression and optional chunk-summary persistence. |
| `summarize2.py` | Same core as `summarize.py` but with **all token/char/int limits removed** — adaptive chunking that scales to any input size without hardcoded budgets. Use this when your conversations exceed the fixed limits in `summarize.py`. |

All three scripts read an OpenRouter-compatible API key from the `OPENROUTER_API_KEY` environment variable, embed the system prompt inside the code (plug-n-use provisioning — just set your key and run), and write outputs to a configurable output directory.

---

## How to use

### Prerequisites

```bash
pip install requests
```

Set your OpenRouter API key:

```bash
# PowerShell
$env:OPENROUTER_API_KEY="sk-or-..."

# Bash / Linux / macOS
export OPENROUTER_API_KEY="sk-or-..."
```

---

### 1. chunker.py — chunk long text into context-sized parts

Splits a story/document into natural sections (chapters/parts) under a max context size. Strips forum/nav boilerplate, drops leading/trailing metadata, merges only tiny chapters, enforces per-chunk max context.

```bash
# Preview chunks on stdout (default context: 32000 tokens)
python chunker.py mynovel.txt

# Write each chunk as chunk_001.txt ... chunk_NNN.txt into <filename>_chunks/
python chunker.py mynovel.txt -c 32000 -o

# Debug: show where chapter boundaries and drops were detected
python chunker.py mynovel.txt -c 16000 -o -d

# Disable forum/nav boilerplate stripping
python chunker.py mynovel.txt --no-forum-strip

# Keep leading/trailing metadata (don't drop front/back matter)
python chunker.py mynovel.txt --keep-meta
```

**CLI flags**

| Flag | Description | Default |
|------|-------------|---------|
| `filename` | Input text file (required) | — |
| `-c, --context` | Max context length in tokens | `32000` |
| `-o, --output` | Write chunks as files instead of stdout preview | off |
| `-d, --debug` | Print chapter-boundary / drop debug info | off |
| `--no-forum-strip` | Disable forum/nav boilerplate stripping | enabled |
| `--keep-meta` | Keep leading/trailing metadata | dropped |

**Input:** `mynovel.txt` (any plain text)<br>
**Output:** folder `<basename>_chunks/` containing `chunk_001.txt` … `chunk_NNN.txt`, or stdout preview

---

### 2. summarize.py — summarize a story/document

Summarizes a long document or conversation into a structured evidence record, with SMART (chapter-aware via `chunker.py`) or DUMB (length-based) chunking, recursive multi-pass compression, and optional per-chunk summary persistence.

```bash
# One-shot summary (default: level 5, most detailed, context 32000)
python summarize.py "ChatGPT-API Testing Tools Alternatives-20261006-1915.txt"

# Lower detail level, larger context window
python summarize.py -s 2 -c 100000 input.txt

# Dumb length-based chunking instead of smart chapter-aware
python summarize.py --dumb input.txt

# Keep intermediate chunk summaries to a file
python summarize.py -k input.txt

# Resummarize from an existing chunk-summaries file
python summarize.py -r chunk_summaries_input.txt

# Use OpenRouter backend
python summarize.py --base-url "https://openrouter.ai/api/v1" --model "openrouter/free" input.txt
```

**CLI flags**

| Flag | Description | Default |
|------|-------------|---------|
| `filename` | Input file to summarize (required) | — |
| `-s, --summary` | Detail level 1-5 (1=smallest, 5=most detailed) | `5` |
| `-k, --keep` | Write concatenated chunk summaries to `chunk_summaries_<file>.txt` | off |
| `-c, --context` | Max context window tokens | `32000` |
| `--base-url` | Backend API URL | `http://127.0.0.1:1234/v1` |
| `--model` | Model name | `local-model` |
| `--dumb` | Simple length-based chunking instead of smart | off |
| `--resummarize / -r` | Treat input as existing chunk summaries, skip chunking | off |

**Input:** any plain text `.txt` (conversation transcript, story, doc)<br>
**Output:** `summary_s<level>_<clean_name>.txt` in the output directory (default `D:\My Docs\Product Management\summarize\tasl_canteen` — change `OUTPUT_DIR` at the top of the script)

---

### 3. summarize2.py — same as summarize.py, no limits

Identical CLI and behavior to `summarize.py`, but **all 5 hard-coded token/char/int limits are eliminated**:

- No fixed `DEFAULT_CONTEXT_LIMIT`
- No `CHUNK_INPUT_TOKENS` / `CHUNK_OVERLAP_TOKENS` chunking budgets
- No `INTERMEDIATE_MAX_TOKENS` / `FINAL_MAX_TOKENS` synthesis caps
- No forced chunking thresholds (`context_limit * 0.8`, `* 0.35`, etc.)

Code adapts automatically to any input size — use this for very long conversations where `summarize.py`'s fixed caps would truncate or force unnecessary chunking.

```bash
# Adaptive: no context cap, tries one-pass if it fits
python summarize2.py --base-url "https://openrouter.ai/api/v1" --model "openrouter/free" "long-conversation.txt"

# Two-stage: extract per-source evidence, then consolidate
python summarize2.py --stage extract source_summary.txt
python summarize2.py --stage consolidate combined_evidence.txt
```

---

## Plug-n-use system prompt (embedded in code)

Each script contains an embedded `BASE_SYSTEM_PROMPT` / `FINAL_SYSTEM_PROMPT` string at the top — no external prompt files needed. The prompt instructs the model to extract **how the user thinks, decides, navigates ambiguity, and builds software** (FDE/APM signal), not to write marketing copy about the app. Just set `OPENROUTER_API_KEY` and run.

---

## Input / Output directories

- **Input:** pass the path to your `.txt` file as the first positional argument
- **Output:** controlled by the `OUTPUT_DIR` constant at the top of each script:
  - `summarize.py` → `D:\My Docs\Product Management\summarize\tasl_canteen`
  - `summarize2.py` → `D:\My Docs\Product Management\P2_SCAI\cc`
  - `chunker.py` → writes `chunk_*.txt` next to the input file (`<basename>_chunks/`)

Edit `OUTPUT_DIR` in whichever script you're running to point at your own working folder.

---

## Portfolio framing

This toolchain was built to consolidate scattered, long-form AI conversations into reusable evidence for FDE / APM / technical-product roles — extracting **problem → reasoning → decision → build → outcome → competency signal** per conversation, with traceability preserved via source IDs (S1–S11). Use it to turn your own chat logs into resume bullets, case studies, and interview evidence.

---

## License

MIT — see `LICENSE` in the parent repository.
