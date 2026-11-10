"""
Chunk a story into natural sections (chapters/parts) under a max context size.

Features:
- Pre-strip forum/nav boilerplate safely (dual-signal gate + caps).
- Detect chapters (Chapter/Part/Book/Section headers; ALL-CAPS headers; ≥N blank lines).
- Drop leading/trailing metadata (conservative scorer + size gate).
- Merge only *tiny* chapters; keep meaningful ones intact.
- Enforce per-chunk max context by splitting large chunks on paragraph boundaries.
"""

import os
import re
import argparse
from textwrap import shorten

# =============================================================
# Configuration (tweak here or via CLI toggles)
# =============================================================

# Minimum size (in characters) for a valid chunk from initial split
MIN_CHAPTER_SIZE = 500

# Tokens that count as a "meaningful" chapter; below this may be merged
MIN_MEANINGFUL_TOKENS = 3000

# Treat ≥ this many blank lines as a chapter break
MIN_BLANK_BREAK = 3

# --- Metadata handling (front/back matter, license, “about author”, etc.) ---
DROP_LEADING_METADATA_DEFAULT = True
DROP_TRAILING_METADATA_DEFAULT = True
METADATA_MAX_TOKENS = 3000             # small enough to be considered metadata
METADATA_SCORE_THRESHOLD = 0.65         # 0..1; higher = stricter drop

# --- Forum/navigation boilerplate stripper ---
FORUM_STRIP_DEFAULT = True              # can be disabled with --no-forum-strip
FORUM_MAX_SCAN_LINES = 600
FORUM_MAX_DROP_LINES = 200
FORUM_MAX_DROP_CHARS = 5000

# =============================================================
# Helpers
# =============================================================

def estimate_tokens(text: str) -> int:
    """Heuristic: 1 token ≈ 4 characters."""
    return len(text) // 4

def normalize_text(s: str) -> str:
    """Normalize newlines and common whitespace artifacts."""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace("\u00A0", " ")  # non-breaking space -> space
    return s

# =============================================================
# Forum/Nav boilerplate detection & stripping
# =============================================================

URL_LIKE = re.compile(r"(https?://|www\.)", re.I)
ANGLE_LINK = re.compile(r"<https?://[^>]+>", re.I)
HORIZONTAL_RULE = re.compile(r"^\s*[-=_]{6,}\s*$")
MENU_KEYWORDS = {
    "watched", "whats-new", "what's new", "search", "media", "threads", "posts",
    "faq", "help", "rules", "mark read", "latest activity", "news feed",
    "download", "profile", "chat", "terms", "index.php", "featured", "categories",
    "resources", "albums", "users", "mark-viewed", "mark viewed"
}

def is_urlish_line(line: str) -> bool:
    l = line.strip()
    if not l:
        return False
    if URL_LIKE.search(l) or ANGLE_LINK.search(l):
        return True
    if HORIZONTAL_RULE.match(l):
        return True
    # bullet-ish or nav-ish
    if l[:1] in {"*", "•", ">", "·", "—", "-", "▶"} and len(l) < 200:
        return True
    # menu keywords + short-ish
    lk = l.lower()
    if any(k in lk for k in MENU_KEYWORDS) and (len(l) < 180 or "index.php" in lk):
        return True
    return False

SENTENCE_END = re.compile(r"[.!?][\"')\]]?\s*$")

def looks_like_content_line(line: str) -> bool:
    """
    'Prose' heuristic: longish, letters/spaces predominance,
    ends like a sentence or shows dialogue quotes.
    """
    l = line.strip()
    if len(l) < 40:
        return False
    letters = sum(c.isalpha() for c in l)
    if letters / max(len(l), 1) < 0.6:
        return False
    if SENTENCE_END.search(l) or ('“' in l or '”' in l or '"' in l or "'" in l):
        return True
    return False

def should_drop_forum_block(lines, start=0, max_scan=FORUM_MAX_SCAN_LINES):
    end = min(len(lines), start + max_scan)
    block = lines[start:end]

    urlish = sum(1 for ln in block if is_urlish_line(ln))
    scanned = len(block)

    # Signal 1: link/menu density
    link_density = urlish / max(scanned, 1)
    link_ok = (urlish >= 3) and (link_density >= 0.25)

    # Signal 2: low prose density
    sentence_lines = sum(1 for ln in block if SENTENCE_END.search(ln))
    letters_ratio = sum(c.isalpha() for ln in block for c in ln) / max(sum(len(ln) for ln in block), 1)
    prose_ok = (sentence_lines < 10) and (letters_ratio < 0.60)

    return link_ok and prose_ok

def strip_forum_boilerplate(text: str, debug: bool = False) -> tuple[str, int]:
    """
    Remove a leading block of forum/nav boilerplate (URL/menu-heavy),
    stopping before actual prose or an explicit chapter header.
    Returns (clean_text, dropped_line_count).
    """
    t = normalize_text(text)
    lines = t.splitlines()

    # Loosely mirror chapter header recognition
    chapter_header = re.compile(
        r"^\s*(?:CHAPTER|Chapter|PART|Part|BOOK|Book|SECTION|Section)\s+(?:[IVXLCDM]+|\d+|[A-Za-z][A-Za-z-]+)\b",
        re.M
    )

    drop_until = 0
    urlish_count = 0
    content_streak = 0
    N = min(len(lines), FORUM_MAX_SCAN_LINES)

    for i in range(N):
        line = lines[i]

        if chapter_header.match(line):
            break

        if is_urlish_line(line):
            urlish_count += 1
            content_streak = 0
            drop_until = i + 1
            continue

        if not line.strip():
            content_streak = 0
            drop_until = i + 1
            continue

        if looks_like_content_line(line):
            content_streak += 1
            if content_streak >= 2:
                break
        else:
            content_streak = 0
            drop_until = i + 1

    # Apply dual-signal gate + caps + continuity peek
    if drop_until > 0 and urlish_count >= 3 and should_drop_forum_block(lines):
        if (drop_until > FORUM_MAX_DROP_LINES or
            sum(len(ln) for ln in lines[:drop_until]) > FORUM_MAX_DROP_CHARS):
            return t, 0  # too risky

        preview = "\n".join(lines[drop_until:drop_until+10])
        if not (re.search(r"[.!?][\"')\]]?\s", preview) or
                re.search(r"^\s*(?:CHAPTER|PART|BOOK|SECTION)\b", preview, re.M)):
            return t, 0  # no obvious prose/chapter ahead

        kept = "\n".join(lines[drop_until:])
        if debug:
            print(f"[DEBUG] strip_forum_boilerplate: dropped {drop_until} line(s) of forum/nav header.")
        return kept.lstrip("\n"), drop_until

    return t, 0

# =============================================================
# Metadata scoring and trimming (front/back matter)
# =============================================================

META_KEYWORDS = {
    "copyright", "all rights reserved", "license", "smashwords", "gutenberg",
    "creative commons", "isbn", "edition", "publisher", "imprint",
    "acknowledg", "dedication", "preface", "foreword", "table of contents",
    "about the author", "also by", "author’s note", "disclaimer",
    "http://", "https://", "www.", "@", "email", "chapter index", "toc"
}
META_PATTERNS = [
    re.compile(r"\b\d{4}\b"),
    re.compile(r"https?://\S+"),
    re.compile(r"\bISBN[- ]?\d", re.I),
    re.compile(r"©"),
]

def metadata_score(text: str) -> float:
    """Return 0..1 how much this looks like metadata."""
    t = text.lower()
    hits = sum(1 for kw in META_KEYWORDS if kw in t)
    hits += sum(1 for rx in META_PATTERNS if rx.search(text))

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    short_lines = sum(1 for ln in lines if len(ln) <= 60)
    sentence_like = len(re.findall(r"[.!?][\"')\]]?\s", text))

    n = max(len(lines), 1)
    short_ratio = short_lines / n
    few_sentences = 1.0 if sentence_like <= 3 else 0.0

    quote_ratio = text.count('"') / max(len(text), 1)
    low_dialogue = 1.0 if quote_ratio < 0.002 else 0.0

    score = (
        min(hits, 6) / 6 * 0.55 +
        short_ratio * 0.20 +
        few_sentences * 0.15 +
        low_dialogue * 0.10
    )
    return max(0.0, min(1.0, score))

def strip_leading_metadata(chapters, debug=False):
    if not chapters:
        return chapters, 0, 0
    dropped_cnt = dropped_tok = 0
    kept = chapters[:]
    while kept:
        head = kept[0]
        tok = estimate_tokens(head)
        if tok <= METADATA_MAX_TOKENS and metadata_score(head) >= METADATA_SCORE_THRESHOLD:
            kept.pop(0)
            dropped_cnt += 1
            dropped_tok += tok
            if debug:
                print(f"[DEBUG] Dropped leading metadata (~{tok} tokens, score {metadata_score(head):.2f})")
        else:
            break
    if not kept:
        return chapters, 0, 0
    return kept, dropped_cnt, dropped_tok

def strip_trailing_metadata(chapters, debug=False):
    if not chapters:
        return chapters, 0, 0
    dropped_cnt = dropped_tok = 0
    kept = chapters[:]
    while kept:
        tail = kept[-1]
        tok = estimate_tokens(tail)
        if tok <= METADATA_MAX_TOKENS and metadata_score(tail) >= METADATA_SCORE_THRESHOLD:
            kept.pop()
            dropped_cnt += 1
            dropped_tok += tok
            if debug:
                print(f"[DEBUG] Dropped trailing metadata (~{tok} tokens, score {metadata_score(tail):.2f})")
        else:
            break
    if not kept:
        return chapters, 0, 0
    return kept, dropped_cnt, dropped_tok

# =============================================================
# Chapter detection and chunking
# =============================================================

def split_into_chapters(text: str, debug: bool = False):
    """
    Split text into natural 'chapter'-like divisions.
    Rules:
      - "Chapter/Part/Book/Section" + number/roman/word (indented allowed).
      - Markdown-ish headers (## Chapter ...).
      - Broad ALL-CAPS header consuming a preceding blank line.
      - A run of ≥ MIN_BLANK_BREAK blank lines.
    """
    text = normalize_text(text)

    chapter_header = (
        r"^\s*(?:CHAPTER|Chapter|PART|Part|BOOK|Book|SECTION|Section)\s+"
        r"(?:[IVXLCDM]+|\d+|[A-Za-z][A-Za-z-]+)\b[^\n]*\n"
    )
    markdown_header = r"^\s{0,3}#{2,6}\s+.*\n"
    all_caps_header = r"(?:\n[ \t]*\n)[ \t]*[A-Z0-9 ,.'’\-:;!?]{6,}[ \t]*\n"
    blank_block = rf"\n{{{MIN_BLANK_BREAK},}}"

    combined = "|".join([chapter_header, markdown_header, all_caps_header, blank_block])
    splitter = re.compile(combined, flags=re.MULTILINE)

    if debug:
        print("\n[DEBUG] Detected boundary previews:")
        for m in splitter.finditer(text):
            boundary = text[m.start():m.end()].strip().split("\n", 1)[0]
            print(f"  • at {m.start():>8}-{m.end():<8} : {boundary[:120]}")

    splits = splitter.split(text)
    chunks = [s.strip() for s in splits if len(s.strip()) > MIN_CHAPTER_SIZE]
    return chunks

def merge_small_chapters(chapters, min_meaningful_tokens=MIN_MEANINGFUL_TOKENS, max_tokens=32000):
    """
    Merge only *tiny* chapters (< min_meaningful_tokens) with adjacent ones.
    Meaningful chapters remain standalone (preserves narrative units).
    """
    merged = []
    current, count = [], 0

    for ch in chapters:
        tokens = estimate_tokens(ch)

        # Keep meaningful chapters intact
        if tokens >= min_meaningful_tokens:
            if current:
                merged.append("\n\n".join(current))
                current, count = [], 0
            merged.append(ch)
            continue

        # Accumulate short chapters into a single chunk (up to max_tokens)
        if count + tokens > max_tokens:
            if current:
                merged.append("\n\n".join(current))
            current, count = [ch], tokens
        else:
            current.append(ch)
            count += tokens

    if current:
        merged.append("\n\n".join(current))
    return merged

def enforce_context_limit(chunks, max_tokens):
    """
    Ensure no individual chunk exceeds max_tokens.
    If a chunk is too long, split by paragraph boundaries (blank line).
    """
    safe = []
    for chunk in chunks:
        tokens = estimate_tokens(chunk)
        if tokens <= max_tokens:
            safe.append(chunk)
            continue

        # Too big -> split by paragraphs
        paragraphs = chunk.split("\n\n")
        current, count = [], 0
        for para in paragraphs:
            t = estimate_tokens(para)
            if count + t > max_tokens:
                if current:
                    safe.append("\n\n".join(current))
                current, count = [para], t
            else:
                current.append(para)
                count += t
        if current:
            safe.append("\n\n".join(current))
    return safe

# =============================================================
# CLI
# =============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Chunk a story into natural sections (chapters/parts) under a max context size.",
        epilog="Example: python chunker.py mynovel.txt -c 32000 -o -d"
    )
    parser.add_argument("filename", type=str, help="Input text file")
    parser.add_argument("-c", "--context", type=int, default=32000,
                        help="Max context length (in tokens)")
    parser.add_argument("-o", "--output", action="store_true",
                        help="Write each chunk as chunk_001.txt etc. to a folder.")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Print where chapter boundaries / drops were detected.")
    parser.add_argument("--no-forum-strip", action="store_true",
                        help="Disable forum/navigation boilerplate stripping.")
    parser.add_argument("--keep-meta", action="store_true",
                        help="Keep leading/trailing metadata (disable metadata drop).")
    args = parser.parse_args()

    if not os.path.isfile(args.filename):
        print(f"❌ File not found: {args.filename}")
        return

    with open(args.filename, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    print(f"\n📖 Processing: {args.filename}")
    print(f"   Max context: {args.context} tokens")
    print(f"   Minimum chapter size: {MIN_CHAPTER_SIZE} characters")
    print(f"   Minimum meaningful chapter: {MIN_MEANINGFUL_TOKENS} tokens")
    print(f"   Blank-line chapter break threshold: ≥{MIN_BLANK_BREAK} blank lines")
    print(f"   Forum/nav strip: {FORUM_STRIP_DEFAULT and not args.no_forum_strip}")
    print(f"   Drop metadata (lead/tail): {DROP_LEADING_METADATA_DEFAULT and not args.keep_meta}/"
          f"{DROP_TRAILING_METADATA_DEFAULT and not args.keep_meta}\n")

    # Step 0 — forum/nav boilerplate pre-strip
    if FORUM_STRIP_DEFAULT and not args.no_forum_strip:
        text, dropped_forum_lines = strip_forum_boilerplate(text, debug=args.debug)
        if dropped_forum_lines:
            print(f"   • Dropped {dropped_forum_lines} forum/nav header line(s)")

    # Step 1 — detect chapters
    chapters = split_into_chapters(text, debug=args.debug)
    if not chapters or len(chapters) == 1:
        print("⚠️  No natural chapters detected — using full text as one chunk.")
        chapters = [normalize_text(text).strip()]

    # Step 1.5 — drop metadata (front/back)
    lead_cnt = lead_tok = tail_cnt = tail_tok = 0
    if DROP_LEADING_METADATA_DEFAULT and not args.keep_meta:
        chapters, lead_cnt, lead_tok = strip_leading_metadata(chapters, debug=args.debug)
    if DROP_TRAILING_METADATA_DEFAULT and not args.keep_meta:
        chapters, tail_cnt, tail_tok = strip_trailing_metadata(chapters, debug=args.debug)

    print(f"Found {len(chapters)} natural chapters/sections."
          f"{' (metadata dropped)' if (lead_cnt or tail_cnt) else ''}")
    if lead_cnt:
        print(f"   • Dropped {lead_cnt} leading metadata section(s) (~{lead_tok} tokens)")
    if tail_cnt:
        print(f"   • Dropped {tail_cnt} trailing metadata section(s) (~{tail_tok} tokens)")

    # Step 2 — merge tiny ones only (preserve meaningful chapters)
    merged = merge_small_chapters(
        chapters,
        min_meaningful_tokens=MIN_MEANINGFUL_TOKENS,
        max_tokens=args.context
    )
    print(f"After merging small ones: {len(merged)} chunks")

    # Step 3 — enforce max context
    final_chunks = enforce_context_limit(merged, args.context)
    print(f"After enforcing context limit: {len(final_chunks)} final chunks\n")

    # Step 4 — output or preview
    if args.output:
        base = os.path.splitext(os.path.basename(args.filename))[0]
        outdir = f"{base}_chunks"
        os.makedirs(outdir, exist_ok=True)
        for i, chunk in enumerate(final_chunks, start=1):
            outname = os.path.join(outdir, f"chunk_{i:03}.txt")
            with open(outname, "w", encoding="utf-8") as f:
                f.write(chunk)
            preview = shorten(chunk.replace("\n", " "), width=100, placeholder="...")
            print(f"  ✂️  Wrote {outname} ({estimate_tokens(chunk)} tokens): {preview}")
        print(f"\n✅ {len(final_chunks)} chunks written to folder '{outdir}'")
    else:
        for i, chunk in enumerate(final_chunks, start=1):
            preview = shorten(chunk.replace("\n", " "), width=100, placeholder="...")
            print(f"Chunk {i}: {estimate_tokens(chunk)} tokens | {preview}")

    # Step 5 — summary
    natural_count = len(chapters)
    merged_count = natural_count - len(merged)
    final_count = len(final_chunks)
    total_tokens = sum(estimate_tokens(c) for c in final_chunks)

    print("\n📊 Summary:")
    print(f"   • {natural_count} natural chapters detected")
    print(f"   • {merged_count} small chapters merged into neighbors")
    print(f"   • {final_count} final chunks after enforcing context limit")
    print(f"   • Total estimated tokens: {total_tokens}\n")


# Public API to use from other modules
def chunk_file(
    filename: str,
    context_tokens: int = 32000,
    *,
    forum_strip: bool = True,
    drop_leading_meta: bool = True,
    drop_trailing_meta: bool = True,
    debug: bool = False,
):
    """Return (final_chunks, stats_dict) for a file, with no printing or file writes."""
    with open(filename, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    # Step 0 — optional forum/nav strip
    if forum_strip:
        text, _ = strip_forum_boilerplate(text, debug=debug)

    # Step 1 — chapter detection
    chapters = split_into_chapters(text, debug=debug)
    if not chapters or len(chapters) == 1:
        chapters = [normalize_text(text).strip()]

    # Step 1.5 — optional metadata drop
    lead_cnt = lead_tok = tail_cnt = tail_tok = 0
    if drop_leading_meta:
        chapters, lead_cnt, lead_tok = strip_leading_metadata(chapters, debug=debug)
    if drop_trailing_meta:
        chapters, tail_cnt, tail_tok = strip_trailing_metadata(chapters, debug=debug)

    natural_count = len(chapters)

    # Step 2 — merge tiny ones
    merged = merge_small_chapters(
        chapters,
        min_meaningful_tokens=MIN_MEANINGFUL_TOKENS,
        max_tokens=context_tokens
    )

    # Step 3 — enforce max context
    final_chunks = enforce_context_limit(merged, context_tokens)

    stats = {
        "natural_chapters": natural_count,
        "merged_chunks": len(merged),
        "final_chunks": len(final_chunks),
        "total_tokens": sum(estimate_tokens(c) for c in final_chunks),
        "dropped_leading_meta_count": lead_cnt,
        "dropped_leading_meta_tokens": lead_tok,
        "dropped_trailing_meta_count": tail_cnt,
        "dropped_trailing_meta_tokens": tail_tok,
    }
    return final_chunks, stats


if __name__ == "__main__":
    main()