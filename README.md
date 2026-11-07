# wechat-chat-analysis-Yonder-lin

A portable Codex skill for analyzing a WeChat conversation through local data:

- **macOS (preferred):** a local [Murmur](https://github.com/sgaofen/murmur) decrypted database and structured conversation export. Murmur reads backend data, not chat-window screenshots. The helper filters its JSON export through an inclusive date and keeps only media attributed to selected messages.
- **macOS (fallback):** a Dukou / WeChat export ZIP when Murmur key capture is unavailable or the user chooses that route.
- **Windows:** a ChatTrace JSON export plus the same account's local media files and decrypted database. The helper filters by date, validates file attachments by MD5, decodes available images, and copies available videos and voice.

The skill and scripts do not upload chat contents. Link manifests contain metadata only until an agent actually opens a URL. The Windows ChatTrace and Mac Murmur/Dukou routes use different source formats; this project does not run ChatTrace on macOS.

## Install in Codex

Clone or download this repository, then copy the complete `wechat-chat-analysis-yonder-lin` folder into `~/.codex/skills/` (or `$CODEX_HOME/skills/`). Restart Codex and invoke `$wechat-chat-analysis-yonder-lin`.

```bash
git clone https://github.com/Yonder-lin/wechat-chat-analysis-Yonder-lin.git
mkdir -p ~/.codex/skills
cp -R wechat-chat-analysis-Yonder-lin/wechat-chat-analysis-yonder-lin ~/.codex/skills/
```

Read [SKILL.md](wechat-chat-analysis-yonder-lin/SKILL.md) for the platform-specific workflow and commands. On macOS, install Murmur separately, finish its local database decryption, and export the target chat as JSON with media strategy `best`. Then run:

```bash
python3 wechat-chat-analysis-yonder-lin/scripts/prepare_murmur.py \
  --json /path/to/murmur-chat.json --through 2026-09-01 \
  --out-dir /path/to/analysis-package
```

The package contains date-filtered messages, copied available media, link and attachment manifests, and a status report. The alternative Dukou ZIP helper also requires Python 3.9+. On Windows, use the same Python environment as ChatTrace.

## Verification and limits

The Windows helper was tested on a small local ChatTrace sample, and the Dukou helper on synthetic Markdown and native TXT ZIPs. Murmur's author [reports a real WeChat 4.1.15 Apple Silicon key-capture test](https://github.com/sgaofen/murmur/blob/main/docs/ONBOARDING_MAC.md), but this skill's Murmur route has **not** been tested end to end on a Mac. Murmur's [media exporter](https://github.com/sgaofen/murmur/blob/main/cli/export_media.py) currently handles locally available images and videos; ordinary file and voice bodies are not guaranteed. Mac key capture requires a local WeChat process and may require a fresh login, but message analysis reads decrypted backend databases. Dukou's quick forward depends on macOS/WeChat versions and available UI controls. Inspect `status.json`, the source export report, and manifests before treating an export as complete.

Only process an account and conversation you are authorized to access. Keep generated plaintext chat data, keys, and media out of Git repositories.

