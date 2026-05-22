# VSCode Claude Code Extension Improvement's Patch

> Current version: **v0.2.1**

A post-build patcher for the **Claude Code VS Code extension** that replaces the cramped session-history popover with a persistent, resizable session pane — plus a handful of related ergonomic fixes and status indicators.

This is a community patch, not an official Anthropic project. It edits the installed extension's bundled `webview/index.js` and `webview/index.css` in place (or a downloaded `.vsix`).

> **Sister project:** [vscodexfix](https://github.com/LunarWerxs/vscodexfix) — the same idea for the **OpenAI ChatGPT / Codex** VS Code extension (right-click rename / pin / star, expanded task list, workspace grouping, sticky composer).

## What it does

- **Persistent right-side session pane** with a draggable divider between chat and sessions.
- **Header toggle button** (next to "Session history") that hides/shows the session pane. State and the chosen width persist across reloads.
- **Pin / Star** actions on sessions via right-click context menu — both toggle on/off and the menu labels flip to `Unpin` / `Unstar` when the action is already applied. Pinned sessions sort to the top.
- **Three status indicators on session rows:**
  - **Running** — animated spinner while the session is actively working.
  - **Waiting for your reply** *(new in v0.2.0)* — pulsing amber dot when the session is idle and Claude's last message is waiting on you (e.g. it asked a question or finished a turn).
  - **Done** — solid blue dot when a session just finished. Cleared when you click the session.
- **Rewind without file changes** — the "Rewind code" dialog no longer disables its primary action when the dry-run reports zero file diffs, so context rewinds still work.
- **Modal layering hardened** — all five of the bundle's modal overlay classes are bumped above the split-pane UI so dialogs are not covered by the divider or the session list.
- **Flex layout hardened** — chat and session panes get `min-width: 0 / min-height: 0` and the chat pane gets its own stacking context, so long messages or wide code blocks no longer push the divider or clip the session pane.

Existing rename/edit and delete actions are preserved exactly as they are in the stock extension.

### Status indicator priority

When more than one condition is true, the indicator picks the most-actionable state:

1. `running` — session is busy
2. `waiting` — session is idle and the last message was from Claude
3. `done` — session just transitioned from busy to idle (cleared on click)
4. *(no indicator)*

> Note: `waiting` is inferred — Claude Code doesn't expose a real "awaiting input" signal in the bundle, so this lights up whenever the last message is from Claude. That covers "Claude asked a question / is waiting on you to type", but it can false-positive on sessions Claude simply finished without a question. Treat it as a hint, not ground truth.

## Requirements

- Python 3.9+
- Node.js (optional — used for a `node --check` syntax pass after patching; the patch still applies if Node is missing)
- The Claude Code extension installed in VS Code (`anthropic.claude-code`)

## Usage

There are two ways to run it.

### A. Patch a `.vsix` file you'll install yourself

```bash
# Download + patch the latest from the Marketplace, write a patched .vsix next to the source
python patch_claude_vsix_tasks.py

# Or pass an explicit Marketplace itemName / Marketplace URL / local .vsix path
python patch_claude_vsix_tasks.py anthropic.claude-code
python patch_claude_vsix_tasks.py "https://marketplace.visualstudio.com/items?itemName=anthropic.claude-code"
python patch_claude_vsix_tasks.py ./anthropic.claude-code-2.1.147.vsix

# Custom output path
python patch_claude_vsix_tasks.py --out ./claude-code.patched.vsix

# Print patcher version
python patch_claude_vsix_tasks.py --patcher-version
```

Then install the resulting `*.tasks-patched.vsix` via **Extensions → "..." menu → Install from VSIX...**.

### B. Patch the already-installed extension in place

The script's `patch_extension_dir` function operates on an extracted extension directory. The installed extension lives at:

- Windows: `%USERPROFILE%\.vscode\extensions\anthropic.claude-code-<version>`
- macOS / Linux: `~/.vscode/extensions/anthropic.claude-code-<version>`

Back the webview files up, then run the patcher against the extension directory:

```bash
python -c "import importlib.util, pathlib; \
spec = importlib.util.spec_from_file_location('p', 'patch_claude_vsix_tasks.py'); \
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); \
m.LOG_PATH = pathlib.Path('claude-vsix-patch.log'); m.LOG_PATH.write_text(''); \
print('CHANGED:', m.patch_extension_dir(pathlib.Path('<path to anthropic.claude-code-X.Y.Z>')))"
```

Reload the VS Code window (**Ctrl/Cmd+Shift+P → Developer: Reload Window**) to pick up the new bundle.

## Upgrading from an earlier patcher version

The patcher detects whichever prior version's helper block is present and replaces it cleanly. Just re-run the script against the same target — no need to uninstall or revert first. The CSS block is wrapped in `/*claudePatch:start*/` / `/*claudePatch:end*/` sentinels so reapplication is idempotent.

## Rollback

If anything looks broken:

- For path A: uninstall the patched VSIX and reinstall the stock extension from the Marketplace.
- For path B: restore the backup copies of `webview/index.js` and `webview/index.css` you made before patching, then reload the window. The script does **not** create backups for you in path B — make them first.

## Version compatibility

The patch script anchors on specific minified identifiers in the Claude Code bundle. Anthropic ships new bundles regularly and those identifiers can change without notice. If `patch_webview_js` raises `Could not find Claude session-list helper anchor`, the bundle has shifted and the anchor strings need updating.

Tested against:

- Claude Code extension `2.1.147`

If the patch fails on a newer version, please open an issue with the extension version and the failing anchor.

## Why a runtime patch instead of a fork

Claude Code's source is not public. The webview bundle is the only artifact available to modify. The patch is intentionally narrow — it injects a small helper block, swaps a handful of minified call sites, and adds a single CSS block. The goal is for Anthropic to eventually implement these ergonomics natively; until then this fills the gap.

See [CLAUDE_EXTENSION_FEEDBACK.md](CLAUDE_EXTENSION_FEEDBACK.md) for the full feature spec sent to the Anthropic team.

## Changelog

### v0.2.1

- **Star is now toggleable.** Right-clicking a starred session and selecting the menu item removes the star. Previously the action was one-way.
- **Pin/Star menu labels are dynamic.** The context menu now reads `Unpin` / `Unstar` when the session is already pinned/starred, so it's obvious what the next click will do.

### v0.2.0

- Added **waiting** status indicator (pulsing amber dot) for sessions where Claude's last message is awaiting your reply.
- Added header toggle button that hides/shows the session pane, with persisted state + width.
- Hardened split-pane flex layout (`min-width: 0` / `min-height: 0`) so long messages no longer push the divider.
- Bumped z-index on all five modal overlay classes so dialogs sit above the session pane and resize divider.
- Wrapped injected CSS in sentinel comments for clean idempotent re-application.
- Added `--patcher-version` CLI flag.
- Renamed project to *VSCode Claude Code Extension Improvement's Patch*.

### v0.1.0

- Initial public release: persistent right-side session pane, draggable divider, pin/star context menu, running spinner, done dot, rewind-without-file-changes fix.

## License

MIT.
