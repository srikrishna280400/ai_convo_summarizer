# code to run -  & "D:\My Docs\Product Management\P4_PKG\Working Code\max sophisticated\backend\.venv\Scripts\python.exe" summarize.py --base-url "https://openrouter.ai/api/v1" --model "openrouter/free" "ChatGPT-API Testing Tools Alternatives-20261006-1915.txt"  

import argparse
import os
import requests
from datetime import datetime
from chunker import chunk_file  # smart chunker (default)

OUTPUT_DIR = r"D:\My Docs\Product Management\summarize\tasl_canteen"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# -------------------------
# Configurable parameters
# -------------------------

BASE_SYSTEM_PROMPT = ("""# Software Product Building & FDE/APM Evidence Extractor

You are an evidence-extraction assistant analyzing long-form conversations. Do not produce a conventional conversation summary. Extract how the USER thinks, makes decisions, navigates ambiguity, learns unfamiliar technologies, and builds software products.

**Purpose:** Build a factual, reusable evidence base for Junior Forward Deployed Engineer (FDE), Associate Product Manager (APM), Technical Product, Product Engineering, Applied AI, and 0→1 product-building roles.

**Scope:** Focus exclusively on software development, full-stack applications, SaaS, AI/agents, automation, technical exploration, product decisions, integrations, debugging, and system design. Exclude mechanical-engineering experience for now.

## Core Instructions

- Prioritize the USER's prompts, decisions, questions, corrections, constraints, pivots, experiments and independent reasoning.
- Treat assistant suggestions as context, not evidence of the user's capabilities unless the user demonstrably evaluates, adapts or acts on them.
- Focus on what the user noticed, questioned, decided, investigated, rejected, changed, built and learned.
- Preserve meaningful technical details, dependencies, trade-offs, failures and outcomes.
- Do not invent reasoning, ownership, capabilities, results or business impact.
- Distinguish questions from demonstrated understanding, generated code from validated implementation, and intended benefits from actual outcomes.
- Avoid buzzwords, repetitive observations and generic skill claims. If evidence is insufficient, say so.
- Prioritize meaningful problem-solving episodes over routine implementation details.

## Six-Part Extraction Framework

### 1. Problem
What was the user trying to build, solve, understand or improve? What was ambiguous, difficult, constrained or initially unknown?

### 2. Approach
How did the user reason through the problem, investigate alternatives, decompose complexity, identify bottlenecks, test hypotheses or navigate uncertainty?

### 3. Decisions
What significant product or technical decisions did the user make, and why? Capture relevant architecture, workflows, data flows, integrations, tool choices, prioritization and trade-offs.

### 4. Build / Iteration
What did the user actually implement, test, debug, integrate, automate or change? Capture significant failures, root causes, experiments and how the solution evolved.

### 5. Outcome
What was actually achieved? What became functional, improved or possible? Include practical usefulness and measurable impact only when supported by evidence.

### 6. FDE / APM Signal
Identify the strongest demonstrated competencies from the taxonomy below. Explain each using concrete evidence and assign an evidence strength: Strong, Moderate or Weak. Note important limitations.

## Competency Taxonomy

Use these seven groups to classify evidence. Select only those relevant to each episode; do not force every category into every conversation.

1. **Problem Solving:** Root-cause analysis, problem decomposition, hypothesis testing, debugging, bottleneck identification, constraint analysis and first-principles reasoning.

2. **Systems Thinking:** System architecture, end-to-end workflows, data flows, dependencies, integration boundaries, state transitions, failure propagation, edge cases and second-order effects.

3. **Product Judgment:** Problem framing, user needs, requirements clarification, feature prioritization, MVP and scope decisions, workflow improvement, usability, simplification and build-versus-buy reasoning.

4. **Technical Judgment:** Architecture and tool selection, trade-off evaluation, technical feasibility, APIs, data modeling, integration decisions, modularity, maintainability and resource optimization.

5. **0→1 Execution:** Rapid prototyping, experimentation, iterative development, cross-stack implementation, automation, integration, testing, deployment and ownership.

6. **Learning & Resourcefulness:** Learning by building, mental-model formation, self-directed learning, cross-domain knowledge transfer, technical tinkering, creative workarounds and AI-assisted development.

7. **Outcomes & Communication:** Functional results, workflow value, success criteria, validation, reliability, technical documentation, decision rationale, stakeholder communication and reusability.

## Output Format

Start with a compact classification:

| Project / Problem | Approach | Key Decisions | Build / Iteration | Outcome | FDE/APM Signal |
|---|---|---|---|---|---|

Then provide only the most important supporting evidence under these six headings:

- **Problem**
- **Approach**
- **Decisions**
- **Build / Iteration**
- **Outcome**
- **FDE / APM Signal**

Use concise bullets and short tables. Do not repeat information already captured in the classification table. If the conversation contains multiple meaningful episodes, separate them rather than conflating unrelated problems.

For the strongest episodes, preserve this evidence chain:

**Problem or ambiguity → User's reasoning and actions → Decision → Implementation and iteration → Actual outcome → Demonstrated competency.**

For each significant competency, state its evidence strength and the specific behavior supporting it. Briefly identify what the conversation does not establish when that limitation matters.

End with a **Portfolio Evidence** section containing only the strongest reusable facts:

- **Potential case-study evidence:** The problem, decision, technical challenge or iteration worth documenting.
- **Resume evidence:** The defensible action, technical/product context and actual result.
- **Unproven claims:** Important capabilities or impacts that cannot be established from this conversation.

Do not write polished marketing copy, a full career narrative or a generic list of skills. Preserve the concrete evidence for later synthesis across conversations.

The goal is to create a compact, factual evidence record that can later be aggregated across many conversations into a coherent portfolio and professional narrative.

**Guiding principle:** Extract how the user thinks and works, not merely what they built. Evidence over adjectives; decisions over technology lists; root causes over symptoms; system interactions over isolated features; demonstrated outcomes over claimed impact.""")


# -------------------------
# Generic LLM Client
# -------------------------

class LLMClient:
    def __init__(
        self,
        base_url="http://127.0.0.1:1234/v1",
        model="local-model"
    ):
        self.url = f"{base_url.rstrip('/')}/chat/completions"
        self.model = model

        # OpenRouter API key
        self.api_key = os.environ.get("OPENROUTER_API_KEY")

        print("DEBUG:")
        print("  API key loaded:", bool(self.api_key))
        print(
            "  API key length:",
            len(self.api_key) if self.api_key else 0
        )
        print(
            "  API key prefix:",
            self.api_key[:12] if self.api_key else "NONE"
        )
        print("  Endpoint:", self.url)
        print("  Model:", self.model)

    def chat(
        self,
        prompt,
        max_tokens=1000,
        temperature=0.0,
        system_prompt=None,
        timeout=3000
    ):
        messages = []
        
        if system_prompt:
            messages.append({
            "role": "system",
            "content": system_prompt
        })
            
        messages.append({
        "role": "user",
        "content": prompt
    })
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            }
        
        try:
            response = requests.post(
            self.url,
            json=payload,
            headers=headers,
            timeout=timeout
        )
            
        except requests.exceptions.RequestException as e:
            print(f"\n❌ Network error: {e}\n")
            return ""
            
        if response.status_code != 200:
            print(f"\n❌ HTTP {response.status_code}")
            print(f"URL: {self.url}")
            print(
            "OpenRouter response:",
            response.text[:2000]
        )
            print()
            return ""
        
        try:
            data = response.json()
            
            message = data["choices"][0]["message"]
            content = message.get("content")
            
            if content is None:
                print("\n⚠️ Model returned no text content.")
                print("Message:", message)
                return ""
            
            return content.strip()
        
        except (ValueError, KeyError, TypeError) as e:
            print(f"\n❌ Invalid API response: {e}")
            print(
                "Raw response:",
                response.text[:2000]
                )
            print()
            return ""


# -------------------------
# Argument parsing
# -------------------------

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Summarize a document or conversation with varying detail levels",
        epilog="Example: python summarize.py -s 2 -c 100000 data.txt"
    )

    parser.add_argument(
        "filename",
        type=str,
        help="Input file to process (required)"
    )

    parser.add_argument(
        "-s",
        "--summary",
        type=int,
        default=5,
        metavar="LEVEL",
        help="Summary detail level (1-5, 1 = smallest, 5 = most detailed. Default: 5)"
    )

    parser.add_argument(
        "-k",
        "--keep",
        action="store_true",
        help="Write concatenated chunk summaries to chunk_summaries_<filename>.txt"
    )

    parser.add_argument(
        "-c",
        "--context",
        type=int,
        default=32000,
        metavar="TOKENS",
        help="Maximum context window size of the model in tokens (default: 32000)"
    )

    parser.add_argument(
        "--base-url",
        type=str,
        default="http://127.0.0.1:1234/v1",
        help="Base URL for the backend"
    )

    parser.add_argument(
        "--model",
        type=str,
        default="local-model",
        help="Model name"
    )

    parser.add_argument(
        "--dumb",
        action="store_true",
        help="Use simple length-based chunking instead of smart chapter chunking"
    )

    parser.add_argument(
        "--resummarize",
        "-r",
        action="store_true",
        help="Treat input as an existing chunk summaries file and skip chunking"
    )

    args = parser.parse_args()

    if not os.path.isfile(args.filename):
        parser.error(
            f"File not found: '{args.filename}'"
        )

    if args.summary < 1 or args.summary > 5:
        parser.error(
            "Summary level must be between 1 and 5"
        )

    return (
        args.summary,
        args.filename,
        args.keep,
        args.context,
        args.base_url,
        args.model,
        args.dumb,
        args.resummarize
    )


# -------------------------
# Chunk text helper
# -------------------------

def chunk_text(
    text,
    chunk_size_tokens=35000,
    overlap_tokens=500
):
    chars_per_token = 4

    chunk_size = chunk_size_tokens * chars_per_token
    overlap = overlap_tokens * chars_per_token

    chunks = []
    start = 0

    while start < len(text):
        end = min(
            start + chunk_size,
            len(text)
        )

        chunks.append(
            text[start:end]
        )

        start += chunk_size - overlap

    return chunks


# -------------------------
# Scaling function
# -------------------------

def target_master_length(story_tokens):

    if story_tokens <= 100000:
        return "Target length: 3 pages (~1500 words)."

    elif story_tokens <= 500000:
        return "Target length: 5–7 pages (~2500–3500 words)."

    elif story_tokens <= 1000000:
        return "Target length: 8–10 pages (~4000–6000 words)."

    else:
        return "Target length: 12–15 pages (~6000–9000 words)."


# -------------------------
# Recursive summarization
# -------------------------

def recursive_summarize(
    texts,
    client,
    detail_instruction,
    context_limit,
    level=0
):

    combined = "\n\n".join(texts)

    token_estimate = len(combined) // 4

    # Small enough to combine directly
    if token_estimate < context_limit * 0.8:

        prompt = (
            "Combine the following summaries into one coherent summary. "
            f"{detail_instruction}\n\n"
            f"{combined}"
        )

        print(
            f"\n🔄 Final summarization at recursion level "
            f"{level}, tokens ≈ {token_estimate}"
        )

        return client.chat(
            prompt,
            max_tokens=int(context_limit * 0.9),
            temperature=0.2,
            system_prompt=BASE_SYSTEM_PROMPT
        )

    # Still too large → recursively group summaries
    group_size = max(
        5,
        context_limit // 2000
    )

    groups = [
        texts[i:i + group_size]
        for i in range(
            0,
            len(texts),
            group_size
        )
    ]

    print(
        f"\nText too large (≈{token_estimate} tokens). "
        f"Breaking into {len(groups)} groups "
        f"at recursion level {level}..."
    )

    higher_level_summaries = []

    for i, group in enumerate(
        groups,
        start=1
    ):

        print(
            f"  • Summarizing group "
            f"{i}/{len(groups)} "
            f"at level {level}..."
        )

        combined_group = "\n\n".join(group)

        prompt = (
            "Combine the following summaries into one "
            "coherent summary:\n\n"
            f"{combined_group}"
        )

        group_summary = client.chat(
            prompt,
            max_tokens=int(context_limit * 0.8),
            temperature=0.1,
            system_prompt=BASE_SYSTEM_PROMPT
        )

        if group_summary:
            higher_level_summaries.append(
                group_summary
            )

    if not higher_level_summaries:
        return ""

    return recursive_summarize(
        higher_level_summaries,
        client,
        detail_instruction,
        context_limit,
        level + 1
    )


# -------------------------
# Main summarization
# -------------------------

def summarize_story(
    filename: str,
    context_limit: int,
    keep_flag: bool,
    client: LLMClient,
    use_dumb: bool
):

    with open(
        filename,
        "r",
        encoding="utf-8",
        errors="replace"
    ) as f:
        story_text = f.read()

    token_estimate = len(story_text) // 4

    master_instruction = (
        "Write a detailed summary of the following conversation/document. "
        f"{target_master_length(token_estimate)}\n"
        "Do not be too concise. "
        "Describe the flow of ideas, important decisions, "
        "technical details, reasoning, dependencies, "
        "and unresolved questions in chronological order. "
        "Ensure the summary is long enough to cover the "
        "source faithfully."
    )

    # -------------------------
    # Case 1: One-pass
    # -------------------------

    if token_estimate < context_limit * 0.8:

        print(
            f"  Strategy: One-pass injection "
            f"(≈{token_estimate} tokens). "
            "Skipping chunking."
        )

        prompt = (
            f"{master_instruction}\n\n"
            f"{story_text}"
        )

        return (
            client.chat(
                prompt,
                max_tokens=int(context_limit * 0.9),
                temperature=0.2,
                system_prompt=BASE_SYSTEM_PROMPT
            ),
            story_text
        )

    # -------------------------
    # Case 2: Chunking
    # -------------------------

    if use_dumb:

        CHUNK_SIZE = int(
            0.75 * context_limit
        )

        chunks = chunk_text(
            story_text,
            chunk_size_tokens=CHUNK_SIZE,
            overlap_tokens=500
        )

        print(
            f"  Strategy: DUMB "
            f"(length-based) chunking "
            f"(story ≈{token_estimate} tokens)."
        )

        print(
            f"   Using chunk size: "
            f"{CHUNK_SIZE} tokens → "
            f"{len(chunks)} chunks."
        )

    else:

        print(
            f"  Strategy: SMART "
            f"(chapter-aware) chunking via "
            f"chunker.py "
            f"(story ≈{token_estimate} tokens)."
        )

        chunks, stats = chunk_file(
            filename,
            context_tokens=context_limit,
            forum_strip=True,
            drop_leading_meta=True,
            drop_trailing_meta=True,
            debug=False,
        )

        print(
            f"   • Natural chapters: "
            f"{stats.get('natural_chapters')}"
        )

        print(
            f"   • Final chunks: "
            f"{stats.get('final_chunks')}"
        )

        print(
            f"   • Total tokens: "
            f"{stats.get('total_tokens')}"
        )

        # Fallback
        if not chunks:

            CHUNK_SIZE = int(
                0.75 * context_limit
            )

            chunks = chunk_text(
                story_text,
                chunk_size_tokens=CHUNK_SIZE,
                overlap_tokens=500
            )

            print(
                "   ! Smart chunker returned no chunks; "
                "falling back to DUMB length-based chunking."
            )

            print(
                f"   Using chunk size: "
                f"{CHUNK_SIZE} tokens → "
                f"{len(chunks)} chunks."
            )

    # -------------------------
    # Optional chunk-summary file
    # -------------------------

    chunks_filename = None

    if keep_flag:

        base_name = os.path.splitext(
            os.path.basename(filename)
        )[0]

        chunks_filename = os.path.join(OUTPUT_DIR, f"chunk_summaries_{base_name}.txt")

        print(
            f"Writing chunk summaries to "
            f"{chunks_filename}.\n"
        )

        with open(
            chunks_filename,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                f"Chunk summaries for {filename}\n\n"
            )

    # -------------------------
    # Process chunks
    # -------------------------

    chunk_summaries = []

    print(
        "Processing chunks:",
        end=" ",
        flush=True
    )

    for i, chunk in enumerate(
        chunks,
        start=1
    ):

        prompt = (
            "Write a detailed summary of the following text, "
            "focusing on key ideas, events, decisions, "
            "technical details, relationships between concepts, "
            "and important milestones. "
            "Preserve chronology and context.\n\n"
            f"Text:\n{chunk}"
        )

        summary = client.chat(
            prompt,
            max_tokens=int(
                context_limit * 0.25
            ),
            temperature=0,
            system_prompt=BASE_SYSTEM_PROMPT
        )

        if not summary:

            print(
                f"\n❌ Chunk {i} failed. "
                "Stopping rather than producing an incomplete summary."
            )

            return "", ""

        entry = (
            f"--- Chunk {i} ---\n"
            f"{summary}\n\n"
        )

        chunk_summaries.append(entry)

        if keep_flag and chunks_filename:

            with open(
                chunks_filename,
                "a",
                encoding="utf-8"
            ) as f:

                f.write(entry)

        print(
            f"{i}",
            end=" ",
            flush=True
        )

    print(
        "\nAll chunks processed, "
        "creating final master summary..."
    )

    final_summary = recursive_summarize(
        chunk_summaries,
        client,
        master_instruction,
        context_limit
    )

    combined_text = "\n\n".join(
        chunk_summaries
    )

    return final_summary, combined_text


# -------------------------
# Re-summarize saved chunks
# -------------------------

def resummarize_from_chunks(
    chunk_summary_file,
    context_limit,
    client: LLMClient,
    summary_level
):

    print(
        f"Reading existing chunk summaries from: "
        f"{chunk_summary_file}\n"
    )

    with open(
        chunk_summary_file,
        "r",
        encoding="utf-8",
        errors="replace"
    ) as f:

        content = f.read()

    sections = []
    current = []

    for line in content.splitlines():

        if line.strip().startswith("--- Chunk "):

            if current:

                sections.append(
                    "\n".join(current).strip()
                )

                current = []

        else:

            current.append(line)

    if current:

        sections.append(
            "\n".join(current).strip()
        )

    print(
        f"🧩 Found {len(sections)} "
        "existing chunk summaries.\n"
    )

    if not sections:

        print(
            "❌ No valid chunks found in file — "
            "aborting re-summarization."
        )

        return "", ""

    total_text = "\n\n".join(
        sections
    )

    token_estimate = len(total_text) // 4

    master_instruction = (
        "Write a detailed summary of the following "
        "conversation/document, combining the prior "
        "chunk summaries into one coherent whole. "
        f"{target_master_length(token_estimate)}\n"
        "Ensure smooth narrative flow, chronological "
        "structure, important decisions, technical "
        "details, reasoning, and unresolved questions."
    )

    print(
        f"Re-summarizing into a master summary "
        f"(≈{token_estimate} tokens)...\n"
    )

    master_summary = recursive_summarize(
        sections,
        client,
        master_instruction,
        context_limit
    )

    return master_summary, total_text


# -------------------------
# Main
# -------------------------

if __name__ == "__main__":

    (
        summary_level,
        filename,
        keep_flag,
        context_limit,
        base_url,
        model,
        use_dumb,
        resummarize_flag
    ) = parse_arguments()

    base_name = os.path.splitext(
        os.path.basename(filename)
    )[0]

    client = LLMClient(
        base_url=base_url,
        model=model
    )

    print("\nConfiguration validated:")

    print(
        f"   • Summary level: "
        f"{summary_level}"
    )

    print(
        f"   • Context limit: "
        f"{context_limit} tokens"
    )

    print(
        f"   • Input file: "
        f"'{filename}'"
    )

    print(
        f"   • Backend URL: "
        f"{base_url}"
    )

    print(
        f"   • Model: "
        f"{model}"
    )

    print(
        f"   • Chunking mode: "
        f"{'DUMB (length-based)' if use_dumb else 'SMART (chapter-aware)'}"
    )

    if resummarize_flag:

        print(
            f"   • Resummarizing from: "
            f"{filename}"
        )

    print()

    start_time = datetime.now()

    print(
        f"Summarization started at "
        f"{start_time.strftime('%Y-%m-%d %H:%M')}\n"
    )

    # -------------------------
    # Perform summarization
    # -------------------------

    if resummarize_flag:

        master_summary, combined_text = (
            resummarize_from_chunks(
                filename,
                context_limit,
                client,
                summary_level
            )
        )

    else:

        master_summary, combined_text = (
            summarize_story(
                filename,
                context_limit,
                keep_flag,
                client,
                use_dumb
            )
        )

    # -------------------------
    # Validate output
    # -------------------------

    if not master_summary or not master_summary.strip():

        print(
            "❌ ERROR - No summary was generated. "
            "Skipping file output."
        )

    else:

        clean_name = os.path.basename(
            base_name
        )

        clean_name = (
            clean_name
            .lower()
            .replace("chunk_summaries_", "")
            .replace(" ", "_")
        )

        summary_filename = os.path.join(OUTPUT_DIR, f"summary_s{summary_level}_{clean_name}.txt")

        output_summary = master_summary

        # -------------------------
        # Optional compression
        # -------------------------

        if summary_level < 5:

            level_instructions = {

                1: "Summarize the following into 3–4 paragraphs.",

                2: "Summarize the following into 7–8 paragraphs.",

                3: "Summarize the following into about 1,500 words.",

                4: "Summarize the following into about 2,500 words.",
            }

            compress_instruction = (
                level_instructions[
                    summary_level
                ]
            )

            compress_prompt = (
                "Summarize the following long summary "
                "into a shorter version.\n"
                f"{compress_instruction}\n\n"
                f"{master_summary}"
            )

            print(
                f"🪶 Compressing master summary "
                f"to level {summary_level}...\n"
            )

            short_summary = client.chat(
                compress_prompt,
                max_tokens=int(
                    context_limit * 0.5
                ),
                temperature=0.2,
                system_prompt=BASE_SYSTEM_PROMPT
            )

            if short_summary.strip():

                output_summary = short_summary

            else:

                print(
                    "⚠️ Compression step failed — "
                    "writing full version instead."
                )

        # -------------------------
        # Write final output
        # -------------------------

        with open(
            summary_filename,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(output_summary)

        final_word_count = len(
            output_summary.split()
        )

        print(
            f"\n✅ Final summary written to "
            f"{summary_filename}"
        )

        print(
            f"   • Length: "
            f"{final_word_count} words\n"
        )

    end_time = datetime.now()

    print(
        f"Finished summarizing at "
        f"{end_time.strftime('%Y-%m-%d  %H:%M')}\n"
    )

    print("\a")
    print("\a")
    print("\a")