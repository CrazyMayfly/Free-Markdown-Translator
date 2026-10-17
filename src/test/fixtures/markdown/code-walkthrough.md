# Getting Started with mdtx

This short guide walks through installing mdtx, configuring a provider, and
translating your first document. See the [FAQ](https://example.com/faq) if
anything fails.

## Installation

Install from source with `pip`:

```bash
pip install -e ".[ui,mcp]"
mdtx --init-config
```

## First translation

Run the CLI against any Markdown file:

```bash
mdtx translate README.md --to zh-CN
```

The pipeline stages are:

- Parse the document into an AST
  - Protect code spans, links, and HTML tags
- Segment translatable text into bundles
- Translate, review, and validate

## Verify the result

The output keeps every fenced block intact:

```json
{"model": "gpt-5-mini", "temperature": 0.2}
```

If validation reports errors, re-run with `--mode strict`.
