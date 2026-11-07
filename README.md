# wechat-chat-analysis-Yonder-lin

A portable Codex skill for analyzing a WeChat conversation through one of two local inputs:

- **macOS:** a Dukou / WeChat export ZIP. The helper filters messages through an inclusive date, inventories available attachments and links, and preserves media that can be attributed to selected messages.
- **Windows:** a ChatTrace JSON export plus the same account's local media files and decrypted database. The helper filters by date, validates file attachments by MD5, decodes available images, and copies available videos and voice.

The skill and scripts do not upload chat contents. Link manifests contain metadata only until an agent actually opens a URL. The Windows ChatTrace and macOS Dukou routes are different; this project does not run ChatTrace on macOS.

## Install in Codex

Clone or download this repository, then copy the complete `wechat-chat-analysis-yonder-lin` folder into `~/.codex/skills/` (or `$CODEX_HOME/skills/`). Restart Codex and invoke `$wechat-chat-analysis-yonder-lin`.

```bash
git clone https://github.com/Yonder-lin/wechat-chat-analysis-Yonder-lin.git
mkdir -p ~/.codex/skills
cp -R wechat-chat-analysis-Yonder-lin/wechat-chat-analysis-yonder-lin ~/.codex/skills/
```

Read [SKILL.md](wechat-chat-analysis-yonder-lin/SKILL.md) for the platform-specific workflow and commands. On macOS, the helper requires Python 3.9+ and a Dukou ZIP. On Windows, use the same Python environment as ChatTrace.

## Verification and limits

The helpers were tested on a small local ChatTrace sample and on synthetic Dukou Markdown and native TXT ZIPs. A real macOS WeChat/Dukou export has **not** been tested. Dukou's quick forward depends on macOS/WeChat versions and the account's available UI controls. Ordinary file attachments and historical coverage depend on what WeChat actually puts in the ZIP. Inspect the generated `status.json` and manifests before treating an export as complete.

Only process an account and conversation you are authorized to access. Keep generated plaintext chat data, keys, and media out of Git repositories.

