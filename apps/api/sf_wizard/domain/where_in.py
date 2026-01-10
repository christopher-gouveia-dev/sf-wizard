from typing import List

def chunk_values(values: List[str], max_chars: int = 10_000) -> List[List[str]]:
    """Chunk a list of values into batches that roughly respect a max character budget.

    v0.1.0: included for upcoming WHERE IN builder (v0.1.1).
    """
    chunks: List[List[str]] = []
    current: List[str] = []
    current_len = 0

    for v in values:
        token = f"'{v}'"
        token_len = len(token) + (2 if current else 0)  # comma+space if not first
        if current and (current_len + token_len) > max_chars:
            chunks.append(current)
            current = []
            current_len = 0
        current.append(v)
        current_len += token_len

    if current:
        chunks.append(current)
    return chunks
