from onenote2md import clean_markdown, convert_directory, detect_sql_blocks, main


def test_detect_sql_blocks_wraps_sql_lines():
    text = "select * from users\nwhere id = 1\nhello"

    result = detect_sql_blocks(text)

    assert "```sql" in result
    assert "```" in result
    assert "select * from users" in result


def test_clean_markdown_normalizes_headings_and_removes_noise():
    md = """<!-- HTML noise -->
Breakout
Montag, 29. Januar 2024
Generell
* first item
"""

    result = clean_markdown(md)

    assert "# Breakout" in result
    assert "## Generell" in result
    assert "HTML noise" not in result


def test_clean_markdown_extracts_embedded_data_images(tmp_path):
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"0123456789"
    encoded = __import__("base64").b64encode(png_bytes).decode("ascii")
    md = f"![Example](data:image/png;base64,{encoded})"

    result = clean_markdown(md, output_dir=tmp_path)

    assert "image1.png" in result
    assert "![]((" not in result
    assert (tmp_path / "image1.png").exists()


def test_clean_markdown_does_not_rewrite_sql_like_data_links():
    snippet = "Return 1 ](data:image/png;base64,AAAA)"

    result = clean_markdown(snippet, output_dir=__import__("pathlib").Path("."))

    assert "data:image/png;base64" not in result
    assert "assets/embedded_" not in result


def test_clean_markdown_removes_broken_data_url_after_sql_block():
    snippet = "```sql\nINSERT INTO t VALUES (1);\n```\nReturn 1 ](data:image/png;base64,AAAA)"

    result = clean_markdown(snippet, output_dir=__import__("pathlib").Path("."))

    assert "data:image/png;base64" not in result
    assert "INSERT INTO t VALUES (1);" in result


def test_convert_directory_converts_docx_to_named_folder(tmp_path, monkeypatch):
    input_dir = tmp_path / "OneNote_Export"
    output_dir = tmp_path / "Markdown"
    input_dir.mkdir()

    file = input_dir / "note.docx"
    file.write_bytes(b"placeholder")
    monkeypatch.setattr("onenote2md.docx_to_md", lambda path, output_dir: "# Example\n\n![Image](image1.png)")

    converted = convert_directory(input_dir, output_dir)

    assert len(converted) == 1
    target = output_dir / "note" / "note.md"
    assert converted[0] == target
    assert target.exists()
    assert "Example" in target.read_text(encoding="utf-8")


def test_convert_directory_skips_non_docx(tmp_path):
    input_dir = tmp_path / "OneNote_Export"
    output_dir = tmp_path / "Markdown"
    input_dir.mkdir()
    (input_dir / "note.mht").write_text("ignored", encoding="utf-8")

    assert convert_directory(input_dir, output_dir) == []


def test_main_converts_one_docx_file(tmp_path, monkeypatch, capsys):
    input_file = tmp_path / "note.docx"
    output_dir = tmp_path / "Markdown"
    input_file.write_bytes(b"placeholder")
    monkeypatch.setattr("onenote2md.docx_to_md", lambda path, output_dir: "# Example")

    main([str(input_file), "--output-dir", str(output_dir)])

    target = output_dir / "note" / "note.md"
    assert target.exists()
    assert target.read_text(encoding="utf-8") == "# Example"
    assert str(target) in capsys.readouterr().out
