from typing import List, Literal, Optional


def generate_markdown_table(
    headers: Optional[List[str]],
    rows: List[List[str]],
    aligns: Optional[List[Literal["l", "c", "r"]]] = None,
) -> str:
    """
    Generate a Markdown table.

    Args:
        headers: List of column headers, or None to use first row as headers.
        rows: List of rows, each a list of strings.
        aligns: List of alignments ('l', 'c', 'r') for each column.
                Defaults to all center ('c').

    Returns:
        str: Markdown formatted table.
    """
    if not rows:
        return ""

    # If no headers, take the first row as header and remove it from rows
    if not headers:
        headers, rows = rows[0], rows[1:]

    headers = list(map(str, headers))
    rows = [list(map(str, row)) for row in rows]

    num_cols = len(headers)
    if aligns is None:
        aligns = ["c"] * num_cols
    elif len(aligns) != num_cols:
        raise ValueError("Length of aligns must match number of headers.")

    align_map = {
        "l": ":---",
        "c": ":---:",
        "r": "---:",
    }

    header_line = "| " + " | ".join(headers) + " |"
    align_line = "| " + " | ".join(align_map[a] for a in aligns) + " |"
    row_lines = ["| " + " | ".join(map(str, row)) + " |" for row in rows]

    return "\n".join([header_line, align_line, *row_lines])
