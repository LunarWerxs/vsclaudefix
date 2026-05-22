# vsclaudefix

A post-build patcher for the **Claude Code VS Code extension** that replaces the cramped session-history popover with a persistent, resizable session pane — plus a handful of related ergonomic fixes.

This is a community patch, not an official Anthropic project. It edits the installed extension's bundled `webview/index.js` and `webview/index.css` in place (or a downloaded `.vsix`).

## What it does

- **Persistent right-side session pane** with a draggable divider between chat and sessions.
- **Header toggle button** (next to "Session history") that hides/shows the session pane. State and the chosen width persist across reloads.
- **Pin / Star** actions on sessions via right-click context menu. Pinned sessions sort to the top.
- **Running spinner** on busy sessions, **blue "done" dot** on sessions that just finished. Clicking a finished session clears the dot.
- **Rewind without file changes** — the "Rewind code" dialog no longer disables its primary action when the dry-run reports zero file diffs, so context rewinds still work.
- **Modal layering hardened** — all five of the bundle's modal overlay classes are bumped above the split-pane UI so dialogs are not covered by the divider or the session list.
- **Flex layout hardened** — chat and session panes get `min-width: 0 / min-height: 0` and the chat pane gets its own stacking context, so long messages or wide code blocks no longer push the divider or clip the session pane.

Existing rename/edit and delete actions are preserved exactly as they are in the stock extension.

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

## Rollback

If anything looks broken:

- For path A: uninstall the patched VSIX and reinstall the stock extension from the Marketplace.
- For path B: restore the backup copies of `webview/index.js` and `webview/index.css` you made before patching, then reload the window. The script does **not** create backups for you in path B — make them first.

## Version compatibility

The patch script anchors on specific minified identifiers in the Claude Code bundle. Anthropic ships new bundles regularly and those identifiers can change without notice. If `patch_webview_js` raises `Could not find Claude session-list helper anchor`, the bundle has shifted and the anchor strings need updating.

Tested against:

- `anthropic.claude-code-2.1.147`

If the patch fails on a newer version, please open an issue with the extension version and the failing anchor.

## Why a runtime patch instead of a fork

Claude Code's source is not public. The webview bundle is the only artifact available to modify. The patch is intentionally narrow — it injects a small helper block, swaps a handful of minified call sites, and adds a single CSS block. The goal is for Anthropic to eventually implement these ergonomics natively; until then this fills the gap.

See [CLAUDE_EXTENSION_FEEDBACK.md](CLAUDE_EXTENSION_FEEDBACK.md) for the full feature spec sent to the Anthropic team.

## License

MIT.
