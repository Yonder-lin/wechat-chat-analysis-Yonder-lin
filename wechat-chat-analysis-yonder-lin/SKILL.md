---
name: wechat-chat-analysis-yonder-lin
description: Export and analyze an authorized WeChat conversation through Windows ChatTrace or macOS Murmur, with a Dukou ZIP fallback. Use for date-bounded chat summaries with available files, images, videos, links, and a missing-content manifest.
---

# WeChat chat analysis

Use this for one named conversation and the scope the user requests. On Windows, use ChatTrace and local database/media files. On macOS, prefer Murmur's local decrypted database and structured export; use a Dukou ZIP when Murmur cannot acquire keys or the user chooses the forwarding route. Do not use screen scraping or automate opening chats to collect message text. Keep private data local and use the user's chosen output directory. Do not copy keys, account IDs, or example data from another computer.

## Windows: ChatTrace

1. Confirm a local WeChat 4.x account directory (`xwechat_files/<account>`), ChatTrace availability, and the output directory. Keep source `xwechat_files` read-only. Follow the installed ChatTrace version's own instructions if its CLI differs from the commands below.
2. Keep the same `LOCALAPPDATA` override in every ChatTrace and helper process when the user chooses a non-default storage disk. ChatTrace stores keys, decrypted databases, and caches under `%LOCALAPPDATA%/ChatTrace`.
3. If a usable key has not been captured, guide the account owner through normal login, then tray exit, and run `chattrace keyagent run --store --account-dir <account-dir>`. Run `chattrace key test --account-dir <account-dir>`; do not print or copy the raw key. A failed key or unsupported client version is a stopping point for extraction, not a reason to guess a key.
4. Run `chattrace data decrypt --account-dir <account-dir>`. Report failed databases. A successful older decrypted snapshot may be queried, but label its freshness accurately.

5. Resolve the exact conversation ID with `chattrace chat contacts` or `chattrace chat list`. Names may duplicate or change; export by stable `--user` ID. A self-chat may appear in contacts but not the session list.
6. Export JSON with media metadata: `chattrace export --account-dir <account-dir> --user <username> --format json --media --out <temporary-json>`. ChatTrace 0.5.1 has no end-date flag, so the temporary JSON may contain later messages; remove it after successfully creating the scoped package.
7. Run `scripts/prepare_export.py --json <temporary-json> --account-dir <account-dir> --decrypted-dir <decrypted-dir> --through YYYY-MM-DD --out-dir <output-dir>`. This includes the cutoff day through 23:59:59 local time. The helper copies files only when their MD5 matches the message metadata, decodes available images, copies videos or surviving thumbnails, extracts available voice as WAV, and writes separate manifests.
8. Compare the message counts, status totals, and media directory to the output manifest. Keep missing and hash-mismatch entries visible. Do not describe all attachments as recovered when only metadata or a thumbnail survives.

## macOS: Murmur local database (preferred)

1. Check the installed Mac WeChat version and chip. [Murmur](https://github.com/sgaofen/murmur) v0.5.0 documents a WeChat 4.1.15 Apple Silicon key-capture test, provides an Apple Silicon DMG, and requires source installation on Intel Mac. Its automated Mac route supports the Tencent website edition of WeChat, not the App Store edition. Follow [its current Mac guide](https://github.com/sgaofen/murmur/blob/main/docs/ONBOARDING_MAC.md) rather than assuming future WeChat versions work. The skill does not bundle or silently install Murmur.
2. Have the account owner complete Murmur's local onboarding and confirm decrypted databases are present. For WeChat 4.1.9+, do not use old memory scanning. Murmur's private-copy route needs the original WeChat fully exited and a fresh login to the temporary copy; it does not require disabling SIP. Its Frida route has different requirements. Key capture interacts with a local WeChat process, but message retrieval afterward reads decrypted database files, not the chat window. Do not print, paste into chat, or commit keys. If the owner declines key capture or it fails, do not claim the database is readable.
3. Find the exact conversation in Murmur by stable ID. Use its read-only [MCP interface](https://github.com/sgaofen/murmur/blob/main/docs/MCP.md) for bounded queries when connected to Codex, or export that conversation as JSON with media strategy `best` in Murmur's UI. Its `get_messages` accepts `since`/`until` and pages through a conversation; verify all pages were read. MCP message tools do not deliver media bytes, so use a local export for media. For the source CLI, Murmur v0.5.0 exposes `python3 cli/exporters.py json --wxid <chat-id> --media best --dir <export-root>`; verify the installed version's CLI and active account before running it.
4. To create a package ending on a date, run `python3 scripts/prepare_murmur.py --json <murmur-chat.json> --through YYYY-MM-DD --out-dir <output-dir>` with Python 3.9+. This copies only media referenced by selected messages and writes `messages.json`, `attachments.json`, `links.json`, and `status.json`. The date is inclusive in Beijing time. Keep the original Murmur `导出报告.md` beside the source export and reconcile its missing-media counts with the scoped package.
5. Murmur's media exporter currently copies available **images and videos**; a missing original may leave a thumbnail. File and voice message bodies are not guaranteed to be exported. Check the message text, attachment manifest, source report, and local files before claiming a file or voice was recovered. A link in message text is only metadata until its webpage is opened. Report missing source history and refresh the decrypted data if newer messages are requested.

## macOS: Dukou ZIP fallback

1. Confirm macOS and the installed WeChat and Dukou versions. [Dukou](https://github.com/qzz0518/Dukou) documents macOS 14+ and WeChat 4.1.13+ for its WeChat export route. Have the account owner export the desired conversation with WeChat's merge-forward feature through Dukou and save its ZIP locally. For the best attachment-to-message mapping, use Dukou's Markdown output with images and videos enabled. Its quick forward mode is experimental and may be unavailable when WeChat does not expose chat controls; manual forwarding can still produce a native ZIP.
2. Run `python3 scripts/prepare_dukou.py --zip <dukou.zip> --through YYYY-MM-DD --out-dir <output-dir>` with Python 3.9 or newer. This uses only Python's standard library and does not need ChatTrace. It validates the ZIP CRC, filters dated messages, copies attachments referenced by selected Markdown messages, and writes message, attachment, link, and status manifests.
3. If the ZIP has only WeChat's native `聊天记录.txt`, the helper filters the text. It copies media files only when **all** parsed messages in that ZIP are within the requested cutoff, because the native TXT does not reliably map every attachment to a message. Otherwise it leaves those assets in the source ZIP and reports them as unattributed. If the ZIP lacks parseable dates, stop and inspect the export rather than guessing.
4. This fallback does not decrypt the WeChat database or guarantee that every historical message or ordinary file attachment is present. The result covers only what WeChat exported into the ZIP. Report that coverage when summarizing.

## Check links and summarize

All helpers leave link status as `not_checked`. For links the user wants checked, open selected URLs with an available browser or web tool. Record `opened`, `failed`, or `not_checked` separately from the title and URL in the report. Do not infer remote content from a card title. Download linked files only when the user requested them and the link is accessible; keep those files separate from local WeChat attachments.

Read representative documents and images relevant to the requested summary. Inspect or transcribe videos and voice only when tools and time permit; otherwise say which media were copied but not interpreted. Summarize the main themes, decisions, and key exchanges with dates and evidence. A self-chat or file-transfer conversation may have no two-way dialogue; describe its notes and archive timeline instead. State the cutoff, source freshness, recovered counts, and material gaps. Avoid reproducing passwords, access codes, identity numbers, or unrelated personal details.

## Installation boundary

This skill packages the workflow, not ChatTrace, Murmur, or Dukou themselves. On Windows, `scripts/prepare_export.py` imports ChatTrace's Python package; use the same Python environment as ChatTrace. On macOS, `scripts/prepare_murmur.py` uses only the standard library and consumes Murmur JSON; `scripts/prepare_dukou.py` consumes a Dukou ZIP. Never run the Windows key capture on macOS or pass one source format to another helper.

