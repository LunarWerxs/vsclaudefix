# vsclaudefix

**Make the Claude Code sidebar pull its weight.**

The stock VS Code extension hides every old session behind a cramped popover. This puts them in a real pane on the right — resizable, pinnable, with status dots so you can see at a glance which sessions are running, waiting on you, or done.

Plus the layout and modal bugs that have been driving you up a wall.

> Current release: **v0.2.3** · sister project: [vscodexfix](https://github.com/LunarWerxs/vscodexfix) for the OpenAI Codex extension.

---

## Install

```bash
python patch_claude_vsix_tasks.py
```

That downloads the latest Claude Code VSIX from the Marketplace, patches it, and writes `*.tasks-patched.vsix` next to it. Install via **Extensions → "…" → Install from VSIX…** and reload the window.

Got the extension installed already and want to skip the round trip? Point the script at the extracted extension directory — see [Power-user usage](#power-user-usage).

**Requires:** Python 3.9+. Node.js is optional (used for a post-patch syntax check).

---

## What you get

#### Side-by-side sessions

A persistent session pane on the right of the chat, with a draggable divider. New header toggle hides it when you want the chat full-width — state and width persist across reloads.

#### Pin / Star — actually toggleable

Right-click any session. Pin floats it to the top of the list; Star prefixes it with ⭐. Both toggle on/off, and the menu labels flip to `Unpin` / `Unstar` so it's obvious what the next click does. Existing rename and delete still work exactly as they did.

#### Status dots

| Indicator | Meaning |
| --- | --- |
| Spinner | Session is actively working |
| 🟡 Pulsing amber | Claude is asking you something — a permission prompt or a question |
| 🔵 Blue dot | Just finished. Clears on click |

Priority is running → waiting → done, so the most actionable state wins. The waiting indicator reads the bundle's real `pendingInput` signal (true only when the backend reports `state === "waiting_input"`), gated on the session being idle and **not** the one you're currently viewing — no point pinging you about the chat you're already in.

#### Quality-of-life fixes

- **Rewind without file changes** — the *Rewind code* dialog no longer disables its primary button when only the conversation context changed.
- **Modals stay on top** — all five overlay classes in the bundle are now above the session pane and resize divider, so dialogs don't get clipped.
- **Layout doesn't break on long messages** — chat and session panes carry the flex `min-width: 0 / min-height: 0` they always needed, so a wide code block can't push the divider or clip the pane.

---

## Upgrading

Just re-run the script. It detects whichever prior version is in place and replaces it cleanly — CSS is wrapped in sentinel comments and the JS upgrade path strips old helper blocks before re-injecting.

## Rollback

Uninstall the patched VSIX and reinstall the stock extension from the Marketplace. If you patched in place (path B below), restore the backups you made first.

## Compatibility

Anchored on Claude Code **2.1.147**. Anthropic ships new bundles regularly and minified identifiers shift — if the patcher errors with *"Could not find Claude session-list helper anchor"*, the bundle has moved. Open an issue with the version.

---

## Power-user usage

```bash
# Specific marketplace item / URL / local VSIX
python patch_claude_vsix_tasks.py anthropic.claude-code
python patch_claude_vsix_tasks.py ./anthropic.claude-code-2.1.147.vsix

# Custom output path
python patch_claude_vsix_tasks.py --out ./claude-code.patched.vsix

# Patch the installed extension in place (Windows path shown)
python -c "import importlib.util, pathlib; \
spec = importlib.util.spec_from_file_location('p', 'patch_claude_vsix_tasks.py'); \
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); \
m.LOG_PATH = pathlib.Path('claude-vsix-patch.log'); m.LOG_PATH.write_text(''); \
m.patch_extension_dir(pathlib.Path(r'%USERPROFILE%\.vscode\extensions\anthropic.claude-code-2.1.147'))"

# Version
python patch_claude_vsix_tasks.py --patcher-version
```

The full feature spec sent to the Anthropic team lives in [CLAUDE_EXTENSION_FEEDBACK.md](CLAUDE_EXTENSION_FEEDBACK.md) if you want the long version.

---

## Changelog

**v0.2.3** — Waiting indicator now gated on `!busy` and on the session not being the active one. No more amber pulsing on the chat you're currently typing in.

**v0.2.2** — Waiting indicator now reads the real `pendingInput` signal instead of guessing from message history. Amber dot lights up when Claude actually needs your reply, not just because its message was last.

**v0.2.1** — Star is now a toggle. Pin/Star menu labels flip to `Unpin` / `Unstar` when applied.

**v0.2.0** — Waiting indicator. Header show/hide toggle (state + width persisted). Flex layout hardened. Modal z-index hardened. Idempotent re-application. `--patcher-version` flag.

**v0.1.0** — First release: persistent right-side session pane, draggable divider, pin/star context menu, running spinner, done dot, rewind-without-file-changes fix.

## License

MIT.
