---
name: wechat-chat-analysis-yonder-lin
description: Export and analyze an authorized WeChat conversation using cross-platform Murmur first, with Windows ChatTrace or macOS Dukou when needed. Use for date-bounded summaries with available files, images, videos, links, and a missing-content manifest.
---

# WeChat chat analysis

Use this for one named conversation and the scope the user requests. Prefer a tool that works on both Windows and macOS when it meets the requested coverage. Murmur is the first candidate on both systems: it reads locally decrypted backend data and exports structured messages. On Windows, use ChatTrace when Murmur cannot run or the task needs its stronger file/voice recovery; on macOS, use a Dukou ZIP when Murmur cannot acquire keys or the user chooses forwarding. Do not use screen scraping or automate opening chats to collect message text. Keep private data local and use the user's chosen output directory. Do not copy keys, account IDs, or example data from another computer.

## Cross-platform first: Murmur

1. Check [Murmur's current releases and platform guide](https://github.com/sgaofen/murmur). It provides Windows and Apple Silicon Mac installers; Intel Mac currently needs source installation. Confirm the installed WeChat version, account, and available local history. Do not claim compatibility for an untested version based only on the project name.
   On macOS, if Codex receives `Operation not permitted` while probing WeChat's app container, stop direct probing. Installing this skill or passing its synthetic tests does not grant database access, install Murmur, or extract keys. Use Murmur as a separate local application; do not try to bypass macOS permissions or repeat failed direct reads.
2. Have the account owner complete Murmur's local key capture and decryption. On Windows, follow its Windows onboarding; on macOS, follow [the Mac guide](https://github.com/sgaofen/murmur/blob/main/docs/ONBOARDING_MAC.md), which documents a WeChat 4.1.15 Apple Silicon key-capture test. The Mac private-copy route requires the original WeChat fully exited and a fresh login to the temporary copy, but does not require disabling SIP. Key capture involves the local WeChat process; subsequent message retrieval reads decrypted database files, not the chat window. Do not print or commit keys. If key capture fails, do not claim the database is readable.
   For the macOS app build, add `/Applications/Murmur.app` under System Settings → Privacy & Security → Full Disk Access, enable it, then fully quit and reopen Murmur. This permission belongs to Murmur, not to the skill. The documented automatic Mac route supports Tencent's website edition of WeChat; check the edition before key capture.
3. Resolve the exact conversation by stable ID. Use Murmur's read-only [MCP interface](https://github.com/sgaofen/murmur/blob/main/docs/MCP.md) for date-bounded, paginated text queries when connected to Codex. For a media package, export that conversation as JSON with media strategy `best` in Murmur's UI. Its source CLI currently exposes `python3 cli/exporters.py json --wxid <chat-id> --media best --dir <export-root>`; verify the installed version's CLI and active account before using it.
   Before analysis, verify that Murmur reports a successfully decrypted account and that its conversation list includes the requested chat. If not, explain the missing setup step rather than asking Codex to read the encrypted WeChat container itself.
4. Run `python3 scripts/prepare_murmur.py --json <murmur-chat.json> --through YYYY-MM-DD --out-dir <output-dir>` with Python 3.9+. It copies media referenced by selected messages and writes `messages.json`, `attachments.json`, `links.json`, and `status.json`. The cutoff includes the whole date in Beijing time. Reconcile the scoped package with Murmur's source `导出报告.md`.
5. Murmur's current media exporter copies available images and videos. File and voice bodies are not guaranteed; record them as missing unless independently verified. A link is only metadata until its webpage is opened. Refresh decrypted data if newer messages are requested.

## Windows: ChatTrace fallback or fuller file/voice recovery

1. Confirm a local WeChat 4.x account directory (`xwechat_files/<account>`), ChatTrace availability, and the output directory. Keep source `xwechat_files` read-only. Follow the installed ChatTrace version's own instructions if its CLI differs from the commands below.
2. Keep the same `LOCALAPPDATA` override in every ChatTrace and helper process when the user chooses a non-default storage disk. ChatTrace stores keys, decrypted databases, and caches under `%LOCALAPPDATA%/ChatTrace`.
3. If a usable key has not been captured, guide the account owner through normal login, then tray exit, and run `chattrace keyagent run --store --account-dir <account-dir>`. Run `chattrace key test --account-dir <account-dir>`; do not print or copy the raw key. A failed key or unsupported client version is a stopping point for extraction, not a reason to guess a key.
4. Run `chattrace data decrypt --account-dir <account-dir>`. Report failed databases. A successful older decrypted snapshot may be queried, but label its freshness accurately.

5. Resolve the exact conversation ID with `chattrace chat contacts` or `chattrace chat list`. Names may duplicate or change; export by stable `--user` ID. A self-chat may appear in contacts but not the session list.
6. Export JSON with media metadata: `chattrace export --account-dir <account-dir> --user <username> --format json --media --out <temporary-json>`. ChatTrace 0.5.1 has no end-date flag, so the temporary JSON may contain later messages; remove it after successfully creating the scoped package.
7. Run `scripts/prepare_export.py --json <temporary-json> --account-dir <account-dir> --decrypted-dir <decrypted-dir> --through YYYY-MM-DD --out-dir <output-dir>`. This includes the cutoff day through 23:59:59 local time. The helper copies files only when their MD5 matches the message metadata, decodes available images, copies videos or surviving thumbnails, extracts available voice as WAV, and writes separate manifests.
8. Compare the message counts, status totals, and media directory to the output manifest. Keep missing and hash-mismatch entries visible. Do not describe all attachments as recovered when only metadata or a thumbnail survives.

## macOS: Dukou ZIP fallback

1. Confirm macOS and the installed WeChat and Dukou versions. [Dukou](https://github.com/qzz0518/Dukou) documents macOS 14+ and WeChat 4.1.13+ for its WeChat export route. Have the account owner export the desired conversation with WeChat's merge-forward feature through Dukou and save its ZIP locally. For the best attachment-to-message mapping, use Dukou's Markdown output with images and videos enabled. Its quick forward mode is experimental and may be unavailable when WeChat does not expose chat controls; manual forwarding can still produce a native ZIP.
2. Run `python3 scripts/prepare_dukou.py --zip <dukou.zip> --through YYYY-MM-DD --out-dir <output-dir>` with Python 3.9 or newer. This uses only Python's standard library and does not need ChatTrace. It validates the ZIP CRC, filters dated messages, copies attachments referenced by selected Markdown messages, and writes message, attachment, link, and status manifests.
3. If the ZIP has only WeChat's native `聊天记录.txt`, the helper filters the text. It copies media files only when **all** parsed messages in that ZIP are within the requested cutoff, because the native TXT does not reliably map every attachment to a message. Otherwise it leaves those assets in the source ZIP and reports them as unattributed. If the ZIP lacks parseable dates, stop and inspect the export rather than guessing.
4. This fallback does not decrypt the WeChat database or guarantee that every historical message or ordinary file attachment is present. The result covers only what WeChat exported into the ZIP. Report that coverage when summarizing.

## Check links and summarize

All helpers leave link status as `not_checked`. For links the user wants checked, open selected URLs with an available browser or web tool. Record `opened`, `failed`, or `not_checked` separately from the title and URL in the report. Do not infer remote content from a card title. Download linked files only when the user requested them and the link is accessible; keep those files separate from local WeChat attachments.

Read representative documents and images relevant to the requested summary. Inspect or transcribe videos and voice only when tools and time permit; otherwise say which media were copied but not interpreted. Summarize the main themes, decisions, and key exchanges with dates and evidence. A self-chat or file-transfer conversation may have no two-way dialogue; describe its notes and archive timeline instead. State the cutoff, source freshness, recovered counts, and material gaps. Avoid reproducing passwords, access codes, identity numbers, or unrelated personal details.

## Installation boundary

This skill packages the workflow, not ChatTrace, Murmur, or Dukou themselves. On both Windows and macOS, `scripts/prepare_murmur.py` uses only the standard library and consumes Murmur JSON. On Windows, `scripts/prepare_export.py` imports ChatTrace's Python package; use the same Python environment as ChatTrace. On macOS, `scripts/prepare_dukou.py` consumes a Dukou ZIP. Never run the Windows ChatTrace key capture on macOS or pass one source format to another helper.

