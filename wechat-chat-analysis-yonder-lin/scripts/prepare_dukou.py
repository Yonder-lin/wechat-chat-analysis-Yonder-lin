"""Scope a Dukou Markdown ZIP by date and preserve referenced local attachments."""

from __future__ import annotations

import argparse
import collections
import json
import posixpath
import re
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

DATE_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$")
MESSAGE_RE = re.compile(r"^\*\*(.+?)\*\* (\d{2}:\d{2})\s*$")
MARKDOWN_LINK_RE = re.compile(r"!?\[([^\]]*)\]\(([^)]+)\)")
URL_RE = re.compile(r"https?://[^\s<>]+")
NATIVE_RECORD_RE = re.compile(r"(?m)^·([^\n]+)\n(\d{4})年(\d{1,2})月(\d{1,2})日 (\d{2}:\d{2})\n")
MEDIA_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".mp4", ".mov", ".m4v", ".mp3", ".m4a", ".wav", ".amr"}


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_archive_path(value: str) -> str | None:
    value = unquote(value).replace("\\", "/")
    if value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        return None
    normalized = posixpath.normpath(value)
    if normalized in (".", "..") or normalized.startswith("../"):
        return None
    return normalized


def parse_markdown(content: str) -> tuple[list[dict], list[str]]:
    records = []
    unknown = []
    day = None
    current = None
    for line in content.splitlines():
        date_match = DATE_RE.match(line)
        if date_match:
            if current:
                records.append(current)
                current = None
            day = date_match.group(1)
            continue
        message_match = MESSAGE_RE.match(line) if day else None
        if message_match:
            if current:
                records.append(current)
            current = {"time": f"{day} {message_match.group(2)}",
                       "sender": message_match.group(1), "lines": [], "attachments": [], "links": []}
            continue
        if current:
            current["lines"].append(line)
        elif day and line.strip() and not line.startswith("## "):
            unknown.append(line)
    if current:
        records.append(current)
    for record in records:
        body = "\n".join(record["lines"]).strip()
        for label, href in MARKDOWN_LINK_RE.findall(body):
            if urlsplit(href).scheme in ("http", "https"):
                record["links"].append({"title": label, "url": href, "check_status": "not_checked"})
            else:
                path = safe_archive_path(href)
                if path:
                    record["attachments"].append(path)
        for url in URL_RE.findall(body):
            url = url.rstrip(".,;)]}，。；）")
            if url not in [x["url"] for x in record["links"]]:
                record["links"].append({"title": "", "url": url, "check_status": "not_checked"})
        record["text"] = body
        del record["lines"]
    return records, unknown


def parse_native_txt(content: str) -> list[dict]:
    content = content.lstrip("\ufeff").replace("\r\n", "\n")
    matches = list(NATIVE_RECORD_RE.finditer(content))
    records = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start:end].strip()
        timestamp = f"{int(match.group(2)):04d}-{int(match.group(3)):02d}-{int(match.group(4)):02d} {match.group(5)}"
        datetime.strptime(timestamp, "%Y-%m-%d %H:%M")
        links = [{"title": "", "url": url.rstrip(".,;)]}，。；）"), "check_status": "not_checked"}
                 for url in URL_RE.findall(body)]
        records.append({"time": timestamp, "sender": match.group(1), "text": body,
                        "attachments": [], "links": links})
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True, help="Dukou ZIP, preferably with 聊天记录.md")
    parser.add_argument("--through", required=True, help="Inclusive YYYY-MM-DD cutoff")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    cutoff = datetime.strptime(args.through, "%Y-%m-%d").date()
    output = args.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.zip) as archive:
        names = set(archive.namelist())
        markdown = "聊天记录.md" if "聊天记录.md" in names else None
        bad = archive.testzip()
        if bad:
            parser.error(f"ZIP CRC check failed: {bad}")
        if markdown:
            content = archive.read(markdown).decode("utf-8-sig")
            records, unknown = parse_markdown(content)
            mode = "markdown"
        else:
            transcripts = sorted(n for n in names if n.endswith("/聊天记录.txt"))
            if not transcripts and "聊天记录.txt" in names:
                transcripts = ["聊天记录.txt"]
            if not transcripts:
                parser.error("no 聊天记录.md or 聊天记录.txt found")
            records = [r for n in transcripts for r in parse_native_txt(archive.read(n).decode("utf-8-sig"))]
            records.sort(key=lambda r: r["time"])
            unknown = []
            mode = "native_txt"
        if not records:
            parser.error("no dated messages parsed; preserve the ZIP and inspect its format")
        selected = [r for r in records if datetime.strptime(r["time"][:10], "%Y-%m-%d").date() <= cutoff]
        attachments = []
        copied = set()
        for record in selected:
            for path in record["attachments"]:
                item = {"time": record["time"], "path": path, "status": "missing"}
                if path in names:
                    target = output / path
                    if target.resolve().is_relative_to(output) and path not in copied:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(archive.read(path))
                        copied.add(path)
                    if path in copied:
                        item["status"] = "exported"
                        item["bytes"] = target.stat().st_size
                attachments.append(item)
        if mode == "native_txt":
            payloads = sorted(n for n in names if not n.endswith("/") and not n.endswith("聊天记录.txt")
                              and n not in ("index.html", "聊天记录.md"))
            if len(selected) == len(records):
                for path in payloads:
                    safe = safe_archive_path(path)
                    if safe != path:
                        attachments.append({"path": path, "status": "unsafe_path"})
                        continue
                    target = output / "attachments" / safe
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(path))
                    attachments.append({"path": path, "status": "exported_unattributed", "bytes": target.stat().st_size})
                unlinked = []
            else:
                unlinked = payloads
        else:
            unlinked = sorted(n for n in names if n.startswith("batches/") and not n.endswith("/")
                              and not n.endswith("聊天记录.txt") and n not in copied)
    write_json(output / "messages.json", {"source": "Dukou ZIP", "mode": mode, "through": args.through,
                                          "parsed_total": len(records), "selected_total": len(selected),
                                          "messages": selected})
    write_json(output / "attachment_manifest.json", attachments)
    write_json(output / "link_manifest.json", [{"time": r["time"], **link} for r in selected for link in r["links"]])
    status = {"messages": len(selected), "source_mode": mode,
              "attachments": dict(collections.Counter(x["status"] for x in attachments)),
              "links": sum(len(r["links"]) for r in selected), "unparsed_lines": len(unknown),
              "unlinked_archive_members": len(unlinked), "unlinked_member_names": unlinked}
    write_json(output / "status.json", status)
    lines = [f"# 微信聊天导出（截至 {args.through}）", ""]
    for record in selected:
        lines += [f"## {record['time']} {record['sender']}", "", record["text"], ""]
    (output / "selected.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"output": str(output), **{k: v for k, v in status.items() if k != "unlinked_member_names"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()

