import argparse
import base64
import html
import mimetypes
import re
from pathlib import Path

from markdownify import markdownify
import mammoth


DEFAULT_INPUT_DIR = Path("OneNote_Export")
DEFAULT_OUTPUT_DIR = Path("Markdown")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
DATE_KEYWORDS = (
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
)


# -----------------------------
# SQL识别
# -----------------------------
def detect_sql_blocks(text):
    sql_keywords = [
        "select",
        "update",
        "insert",
        "delete",
        "create",
        "alter",
        "drop",
        "from",
        "where",
        "join",
    ]

    lines = text.splitlines()
    result = []
    in_sql = False

    for line in lines:
        lower = line.lower().strip()

        if any(lower.startswith(k) for k in sql_keywords):
            if not in_sql:
                result.append("```sql")
                in_sql = True
            result.append(line)
        else:
            if in_sql:
                result.append("```")
                in_sql = False
            result.append(line)

    if in_sql:
        result.append("```")

    return "\n".join(result)


def is_date_line(line):
    text = line.strip()
    if not text:
        return False
    if text.lower().endswith("am") or text.lower().endswith("pm"):
        return True
    return text.startswith(DATE_KEYWORDS) or re.match(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),", text, re.I)


def is_bullet_line(line):
    text = line.strip()
    return text.startswith(("* ", "- ", "+ "))


def is_title_like(line):
    text = line.strip()
    if not text or len(text) > 120:
        return False
    if text.startswith(("#", "*", "-", "+", "!", "[", "(", "`", "<")):
        return False
    if text.startswith(("http://", "https://", "file://", "data:")):
        return False
    if "|" in text or "<" in text or ">" in text:
        return False
    if re.match(r"^\d+[\.)]", text):
        return False
    return bool(re.search(r"[A-Za-zÄÖÜäöüß]", text))


def normalize_markdown_headings(md):
    lines = md.splitlines()
    result = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        next_line = ""
        for j in range(i + 1, len(lines)):
            candidate = lines[j].strip()
            if candidate:
                next_line = candidate
                break

        if is_title_like(line) and is_date_line(next_line):
            result.append(f"# {line}")
            i += 1
            continue

        if is_title_like(line) and (next_line.startswith(("* ", "- ", "+ ")) or next_line.startswith("#")):
            result.append(f"## {line}")
            i += 1
            continue

        result.append(lines[i])
        i += 1

    return "\n".join(result)


def extract_embedded_data_images(md, output_dir=None):
    if output_dir is None:
        return md

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    counter = 1

    def replace(match):
        nonlocal counter
        alt_text = match.group(1)
        data_url = match.group(2)

        match_data = re.match(r"data:(image/[A-Za-z0-9.+-]+);base64,(.*)", data_url, re.I)
        if not match_data:
            return match.group(0)

        mime_type, encoded = match_data.groups()
        ext = mimetypes.guess_extension(mime_type) or ".png"
        filename = f"image{counter}{ext}"
        counter += 1

        target = output_dir / filename
        target.write_bytes(base64.b64decode(encoded))

        return f"![{alt_text}]({filename})"

    return re.sub(r"(?<!\])!\[([^\]]*)\]\((data:image/[^)]+)\)", replace, md)


# -----------------------------
# markdown清洗
# -----------------------------
def strip_broken_data_urls(md):
    patterns = [
        r"(?m)^\s*\]\(data:image/[A-Za-z0-9.+-]+;base64,[A-Za-z0-9+/=\r\n]+\)\s*$",
        r"(?<!\!)\]\(data:image/[A-Za-z0-9.+-]+;base64,[A-Za-z0-9+/=\r\n]+\)",
    ]
    cleaned = md
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned)
    return cleaned


def clean_markdown(md, source_file=None, output_dir=None):
    md = html.unescape(md)
    md = re.sub(r"(?is)<!--.*?-->", "", md)
    md = re.sub(r"(?is)<(style|script|xml|object|embed)\b.*?>.*?</\1>", "", md)
    md = re.sub(r"(?im)^\s*\[[^\]]+\]:\s*.*$", "", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = normalize_markdown_headings(md)
    md = extract_embedded_data_images(md, output_dir)
    md = strip_broken_data_urls(md)
    md = detect_sql_blocks(md)
    return md.strip()


# -----------------------------
# DOCX -> MD
# -----------------------------
def docx_to_md(docx_file, output_dir=None):
    with open(docx_file, "rb") as f:
        result = mammoth.convert_to_html(f)
        html_content = result.value

    md = markdownify(html_content, heading_style="ATX")
    return clean_markdown(md, docx_file, output_dir)


# -----------------------------
# -----------------------------
# 目录转换
# -----------------------------
def convert_file(file_path, input_dir, output_dir):
    suffix = file_path.suffix.lower()
    if suffix != ".docx":
        return None

    rel = file_path.relative_to(input_dir)
    document_dir = output_dir / rel.parent / rel.stem
    document_dir.mkdir(parents=True, exist_ok=True)
    md = docx_to_md(file_path, document_dir)
    target = document_dir / f"{rel.stem}.md"
    target.write_text(md, encoding="utf-8")
    return target


def convert_directory(input_dir=DEFAULT_INPUT_DIR, output_dir=DEFAULT_OUTPUT_DIR):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    converted = []
    for file in sorted(input_dir.rglob("*")):
        if not file.is_file():
            continue

        try:
            target = convert_file(file, input_dir, output_dir)
            if target is not None:
                converted.append(target)
                print(f"OK: {file}")
        except Exception as exc:
            print(f"ERROR: {file}")
            print(exc)

    return converted


# -----------------------------
# CLI
# -----------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description="Convert one DOCX file to Markdown.")
    parser.add_argument("input_file", type=Path, help="DOCX file to convert.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory where Markdown files will be written.")
    args = parser.parse_args(argv)

    if args.input_file.suffix.lower() != ".docx":
        parser.error("input_file must be a .docx file")
    if not args.input_file.is_file():
        parser.error(f"input file does not exist: {args.input_file}")

    target = convert_file(args.input_file, args.input_file.parent, args.output_dir)
    print(f"OK: {args.input_file} -> {target}")


if __name__ == "__main__":
    main()