#!/usr/bin/env python3
"""Build a date-bounded analysis package from one Murmur JSON chat export."""

import argparse
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path


CST = timezone(timedelta(hours=8))
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
MEDIA_TYPES = {3: "image", 43: "video", 34: "voice", 62: "video"}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def within(source_root, relative):
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    candidate = (source_root / rel).resolve()
    try:
        candidate.relative_to(source_root.resolve())
    except ValueError:
        return None
    return candidate


def is_file_message(type_id):
    return type_id > 0xFFFFFFFF and (type_id & 0xFFFFFFFF) == 49 and (type_id >> 32) == 6


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", required=True, type=Path, help="Murmur chat JSON exported with media=best")
    parser.add_argument("--through", required=True, help="Inclusive cutoff in YYYY-MM-DD, Beijing time")
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    cutoff = datetime.strptime(args.through, "%Y-%m-%d").replace(tzinfo=CST) + timedelta(days=1)
    cutoff_ts = cutoff.timestamp()
    source = args.json.resolve()
    data = json.loads(source.read_text(encoding="utf-8-sig"))
    if data.get("format_version") != 1 or not isinstance(data.get("messages"), list):
        parser.error("Expected a Murmur format_version=1 JSON chat export")
    if args.out_dir.resolve() == source.parent or source.parent in args.out_dir.resolve().parents:
        parser.error("Output directory must be outside the Murmur source export directory")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    messages = []
    attachments = []
    links = []
    invalid_dates = 0
    for message in data["messages"]:
        try:
            ts = int(message["ts"])
        except (KeyError, ValueError, TypeError):
            invalid_dates += 1
            continue
        if ts >= cutoff_ts:
            continue
        msg = dict(message)
        msg_id = len(messages)
        media = msg.get("media")
        type_id = int(msg.get("type_id") or 0)
        kind = MEDIA_TYPES.get(type_id)
        if kind or is_file_message(type_id):
            entry = {"message_index": msg_id, "time": msg.get("time"),
                     "type": "file" if is_file_message(type_id) else kind,
                     "source_media": media, "status": "not_in_murmur_export"}
            if media:
                found = within(source.parent, media)
                if found and found.is_file():
                    media_rel = Path(media)
                    dest = args.out_dir / (media_rel if media_rel.parts[0] == "media" else Path("media") / media_rel)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(found, dest)
                    msg["media"] = dest.relative_to(args.out_dir).as_posix()
                    entry["status"] = "copied"
                    entry["path"] = msg["media"]
                else:
                    msg.pop("media", None)
                    entry["status"] = "missing_or_unsafe_path"
            attachments.append(entry)
        elif media:
            msg.pop("media", None)
        for url in URL_RE.findall(str(msg.get("text") or "")):
            links.append({"message_index": msg_id, "time": msg.get("time"),
                          "url": url.rstrip(".,;:)]}"), "status": "not_checked"})
        messages.append(msg)

    write_json(args.out_dir / "messages.json", {"source": "Murmur", "wxid": data.get("wxid"),
               "name": data.get("name"), "through": args.through, "messages": messages})
    write_json(args.out_dir / "attachments.json", attachments)
    write_json(args.out_dir / "links.json", links)
    write_json(args.out_dir / "status.json", {"source": "Murmur", "through": args.through,
               "source_messages": len(data["messages"]), "selected_messages": len(messages),
               "invalid_dates": invalid_dates, "attachment_entries": len(attachments),
               "copied_media": sum(x["status"] == "copied" for x in attachments),
               "missing_media": sum(x["status"] != "copied" for x in attachments),
               "links_found": len(links)})


if __name__ == "__main__":
    main()

