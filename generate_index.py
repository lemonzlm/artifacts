#!/usr/bin/env python3
"""Scan the repo for HTML artifacts and inject them into index.html.

Idempotent: rewrites the block between <!-- ARTIFACTS:START --> and
<!-- ARTIFACTS:END --> markers. Run before committing, or let the
GitHub Action handle it on push.
"""
from __future__ import annotations

import datetime as dt
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SKIP_NAMES = {"index.html"}
SKIP_PREFIXES = (".", "_")
START = "<!-- ARTIFACTS:START -->"
END = "<!-- ARTIFACTS:END -->"


def humanize(stem: str) -> str:
    words = re.split(r"[_\-\s]+", stem)
    out = []
    for w in words:
        if not w:
            continue
        if w.isupper() or (w.isalnum() and any(c.isdigit() for c in w)):
            out.append(w.upper())
        else:
            out.append(w[:1].upper() + w[1:])
    return " ".join(out)


def collect() -> list[dict]:
    items: list[dict] = []
    for p in sorted(ROOT.iterdir(), key=lambda x: x.name.lower()):
        if p.name in SKIP_NAMES or p.name.startswith(SKIP_PREFIXES):
            continue
        if p.is_file() and p.suffix.lower() == ".html":
            items.append({"href": p.name, "label": humanize(p.stem), "kind": "html"})
        elif p.is_dir():
            entry = p / "index.html"
            if entry.exists():
                items.append({"href": f"{p.name}/", "label": humanize(p.name), "kind": "dir"})
    return items


def render(items: list[dict]) -> str:
    if not items:
        return '      <div class="empty">no artifacts yet — drop an .html file beside this index</div>'
    lines = []
    for it in items:
        href = html.escape(it["href"], quote=True)
        label = html.escape(it["label"])
        file = html.escape(it["href"])
        kind = html.escape(it["kind"])
        search = html.escape(f"{it['label']} {it['href']}", quote=True)
        lines.append(
            f'      <a class="card" href="{href}" data-search="{search}">\n'
            f'        <div class="row">\n'
            f'          <span class="name">{label}</span>\n'
            f'          <span class="arrow">→</span>\n'
            f'        </div>\n'
            f'        <div class="file">{file}</div>\n'
            f'        <div class="tags"><span class="tag">{kind}</span></div>\n'
            f'      </a>'
        )
    return "\n".join(lines)


def inject(html_text: str, block: str, stamp: str) -> str:
    pattern = re.compile(
        re.escape(START) + r".*?" + re.escape(END),
        re.DOTALL,
    )
    new_block = f"{START}\n{block}\n      {END}"
    out = pattern.sub(new_block, html_text)
    out = re.sub(r'<html([^>]*)>', lambda m: f'<html{strip_built(m.group(1))} data-built="{stamp}">', out, count=1)
    return out


def strip_built(attrs: str) -> str:
    return re.sub(r'\s*data-built="[^"]*"', "", attrs)


def main() -> None:
    items = collect()
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    text = INDEX.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit("index.html is missing ARTIFACTS markers")
    new_text = inject(text, render(items), stamp)
    if new_text != text:
        INDEX.write_text(new_text, encoding="utf-8")
    print(f"indexed {len(items)} artifact(s) @ {stamp}")


if __name__ == "__main__":
    main()
