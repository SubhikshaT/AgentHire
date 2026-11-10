"""Split resume sections into chunks of at most ~300 words for embedding / retrieval."""
MAX_WORDS = 300
SKIP_SECTIONS = {"other"}  # hobbies, references, personal details: not useful evidence


def chunk_sections(sections: dict[str, str], max_words: int = MAX_WORDS) -> list[tuple[str, int, str]]:
    """Return (section, chunk_index, text) tuples."""
    chunks: list[tuple[str, int, str]] = []
    for section, body in sections.items():
        if section in SKIP_SECTIONS or not body.strip():
            continue
        idx = 0
        buf: list[str] = []
        count = 0
        for line in body.split("\n"):
            words = line.split()
            if not words:
                continue
            # a single very long line is split by words
            while len(words) > max_words:
                if buf:
                    chunks.append((section, idx, "\n".join(buf)))
                    idx += 1
                    buf, count = [], 0
                chunks.append((section, idx, " ".join(words[:max_words])))
                idx += 1
                words = words[max_words:]
            if count + len(words) > max_words and buf:
                chunks.append((section, idx, "\n".join(buf)))
                idx += 1
                buf, count = [], 0
            buf.append(" ".join(words))
            count += len(words)
        if buf:
            chunks.append((section, idx, "\n".join(buf)))
    return chunks
