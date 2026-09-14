# OneNote Conversion

This project converts exported DOCX files into Markdown documents.

## Features

- Converts .docx files using mammoth
- Creates one output folder per DOCX file
- Extracts embedded images beside the generated Markdown file
- Cleans generated Markdown output
- Detects SQL snippets and wraps them in fenced code blocks
- Preserves the source folder structure under the output directory

## Project structure

- `onenote2md.py` – main conversion logic and CLI entry point
- `main.py` – thin wrapper for running the converter
- `OneNote_Export/` – source export folder
- `Markdown/` – generated Markdown output

## Usage

From the project root, convert one DOCX file:

```bash
python onenote2md.py "OneNote_Export/PB_Client.docx" --output-dir "Markdown"
```

Or use the wrapper:

```bash
python main.py "OneNote_Export/PB_Client.docx" --output-dir "Markdown"
```

## Typical workflow

1. Export OneNote pages/files to `OneNote_Export/`
2. Run the converter
3. Find each document and its images in a same-named folder under `Markdown/`

For example, `PB_Client.docx` produces:

```text
Markdown/
└── PB_Client/
	├── PB_Client.md
	├── image1.png
	└── image2.png
```

## Notes

The script will skip unsupported file types and print conversion errors for any file that fails to process.
