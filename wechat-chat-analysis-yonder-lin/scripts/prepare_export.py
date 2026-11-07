"""Create a date-bounded ChatTrace 0.5.1 export with local attachment manifests."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit


def digest(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_name(title: str) -> str:
    name = title.replace("\\", "/").split("/")[-1]
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .")
    return name[:150] or "unnamed"


def put_file(source: Path, target: Path, expected_md5: str | None = None) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if expected_md5 and digest(target) == expected_md5:
            return
        if not expected_md5 and target.stat().st_size == source.stat().st_size and digest(target) == digest(source):
            return
        raise FileExistsError(f"destination differs: {target}")
    shutil.copy2(source, target)


def direct_links(messages: list[dict]) -> list[dict]:
    entries = []
    seen = set()
    for msg in messages:
        meta = msg.get("meta") or {}
        urls = []
        if msg.get("kind") in ("link", "weapp", "video channel") and meta.get("url"):
            urls.append(meta["url"])
        if msg.get("kind") == "text":
            urls += [u for u in msg.get("links") or [] if u in (msg.get("text") or "")]
        for url in urls:
            key = (msg["create_time"], msg["local_id"], url)
            if key in seen:
                continue
            seen.add(key)
            try:
                host = urlsplit(url).hostname or ""
            except ValueError:
                host = ""
            entries.append({"time": msg["time"], "kind": msg["kind"],
                            "title": meta.get("title") or "", "url": url,
                            "host": host, "check_status": "not_checked"})
    return entries


def file_index(account_dir: Path) -> dict[str, list[Path]]:
    root = account_dir / "msg" / "file"
    result = collections.defaultdict(list)
    if root.is_dir():
        for path in root.rglob("*"):
            if path.is_file():
                result[path.name.casefold()].append(path)
    return result


def recover_files(messages: list[dict], account_dir: Path, output: Path) -> list[dict]:
    index = file_index(account_dir)
    hashes = {}
    manifest = []
    for msg in messages:
        if msg.get("kind") != "file":
            continue
        meta = msg.get("meta") or {}
        title = str(meta.get("title") or "")
        expected = str(meta.get("md5") or "").lower()
        record = {"time": msg["time"], "local_id": msg["local_id"],
                  "title": title, "status": "missing", "saved_path": None}
        if not re.fullmatch(r"[0-9a-f]{32}", expected):
            record["status"] = "no_md5"
            manifest.append(record)
            continue
        candidates = index.get(title.casefold(), [])
        if candidates:
            candidates = sorted(candidates, key=lambda p: (msg["time"][:7] not in p.parts, str(p)))
            match = None
            for candidate in candidates:
                try:
                    if candidate not in hashes:
                        hashes[candidate] = digest(candidate)
                    if hashes[candidate] == expected:
                        match = candidate
                        break
                except OSError:
                    continue
            if match is None:
                record["status"] = "hash_mismatch"
            else:
                target = output / "files" / msg["time"][:7] / f"{msg['local_id']}__{safe_name(title)}"
                try:
                    put_file(match, target, expected)
                    record["status"] = "exported"
                    record["saved_path"] = str(target)
                    record["bytes"] = target.stat().st_size
                except OSError as exc:
                    record["status"] = "copy_error"
                    record["error"] = type(exc).__name__
        manifest.append(record)
    return manifest


def recover_media(messages: list[dict], account_dir: Path, decrypted_dir: Path,
                  username: str, output: Path) -> list[dict]:
    from chattrace.service.database import DatabaseService
    from chattrace.service.media import MediaService

    account_id = account_dir.name
    db = DatabaseService(account_id, decrypted_dir)
    svc = MediaService(account_id, account_dir, decrypted_dir, output / "media_cache")
    allowed = {(int(m["create_time"]), int(m["local_id"])): m for m in messages
               if m.get("kind") in ("image", "video", "voice")}
    if not allowed:
        return []
    found = set()
    manifest = []
    for raw in db.iter_chat_all(username):
        key = (raw.create_time, raw.local_id)
        if key not in allowed:
            continue
        found.add(key)
        msg = allowed[key]
        record = {"time": msg["time"], "local_id": raw.local_id,
                  "kind": msg["kind"], "status": "missing", "saved_path": None}
        try:
            item = svc.item_for_message(db, username, raw)
            record["status"] = item.status
            record["detail"] = item.detail
            if item.status == "ok":
                folder = output / "media" / msg["kind"] / msg["time"][:7]
                folder.mkdir(parents=True, exist_ok=True)
                stem = f"{raw.create_time}_{raw.local_id}"
                if msg["kind"] == "image":
                    decoded = svc.decode_image(item)
                    if decoded is None:
                        record["status"] = "decode_failed"
                    else:
                        ext, blob = decoded
                        target = folder / f"{stem}.{ext}"
                        if target.exists() and target.read_bytes() != blob:
                            raise FileExistsError(f"destination differs: {target}")
                        if not target.exists():
                            target.write_bytes(blob)
                        record["status"] = "exported"
                        record["saved_path"] = str(target)
                elif msg["kind"] == "video" and item.disk_path:
                    target = folder / f"{stem}{item.disk_path.suffix or '.bin'}"
                    put_file(item.disk_path, target)
                    record["status"] = "thumbnail_only" if item.is_thumbnail else "exported"
                    record["saved_path"] = str(target)
                elif msg["kind"] == "voice":
                    blob = svc.voice_wav(username, raw.local_id, raw.create_time)
                    if blob:
                        target = folder / f"{stem}.wav"
                        if target.exists() and target.read_bytes() != blob:
                            raise FileExistsError(f"destination differs: {target}")
                        if not target.exists():
                            target.write_bytes(blob)
                        record["status"] = "exported"
                        record["saved_path"] = str(target)
                    else:
                        record["status"] = "decode_failed"
                if record["saved_path"]:
                    record["bytes"] = Path(record["saved_path"]).stat().st_size
        except Exception as exc:
            record["status"] = "error"
            record["error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
        manifest.append(record)
    for key, msg in allowed.items():
        if key not in found:
            manifest.append({"time": msg["time"], "local_id": msg["local_id"],
                             "kind": msg["kind"], "status": "db_row_missing", "saved_path": None})
    return sorted(manifest, key=lambda x: (x["time"], x["local_id"]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=Path, required=True, help="ChatTrace JSON export")
    parser.add_argument("--account-dir", type=Path, required=True, help="xwechat_files/<account>")
    parser.add_argument("--decrypted-dir", type=Path, required=True, help="ChatTrace account/decrypted")
    parser.add_argument("--through", required=True, help="Inclusive YYYY-MM-DD cutoff")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    cutoff = datetime.strptime(args.through, "%Y-%m-%d").date()
    source = json.loads(args.json.read_text(encoding="utf-8"))
    username = source.get("meta", {}).get("username")
    if not username or not isinstance(source.get("messages"), list):
        parser.error("expected ChatTrace JSON with meta.username and messages")
    if not (args.account_dir / "msg").is_dir() or not args.decrypted_dir.is_dir():
        parser.error("account or decrypted directory is missing")
    selected = [m for m in source["messages"] if datetime.strptime(m["time"][:10], "%Y-%m-%d").date() <= cutoff]
    output = args.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    meta = {**source["meta"], "through": args.through, "source_total": len(source["messages"]),
            "total": len(selected), "prepared_at": datetime.now().isoformat(timespec="seconds")}
    write_json(output / "chat.json", {"meta": meta, "messages": selected})
    files = recover_files(selected, args.account_dir, output)
    write_json(output / "file_manifest.json", files)
    media = recover_media(selected, args.account_dir, args.decrypted_dir, username, output)
    write_json(output / "media_manifest.json", media)
    links = direct_links(selected)
    write_json(output / "link_manifest.json", links)
    stats = {"messages": len(selected), "files": dict(collections.Counter(x["status"] for x in files)),
             "media": {k: dict(collections.Counter(x["status"] for x in media if x["kind"] == k))
                       for k in ("image", "video", "voice")}, "links": len(links)}
    write_json(output / "status.json", stats)
    print(json.dumps({"output": str(output), **stats}, ensure_ascii=False))


if __name__ == "__main__":
    main()

