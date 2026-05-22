# vsclaudefix

**Make the Claude Code sidebar pull its weight.**

The stock VS Code extension hides every old session behind a cramped popover. This puts them in a real pane on the right — resizable, pinnable, with status dots so you can see at a glance which sessions are running, waiting on you, or done.

Plus the layout and modal bugs that have been driving you up a wall.

> Current release: **v0.4.0** · sister project: [vscodexfix](https://github.com/LunarWerxs/vscodexfix) for the OpenAI Codex extension.

---

## Install

```bash
python patch_claude_vsix_tasks.py
```

That's it. The script downloads the latest Claude Code from the Marketplace, patches it, and installs the patched version via `code --install-extension`. Reload the VS Code window when it's done.

Pass `--vsix-only` if you'd rather inspect the patched `.vsix` before installing it yourself.

**Requires:** Python 3.9+, the `code` CLI on PATH (ships with VS Code). Node.js optional (used for a post-patch syntax check).

---

## What you get

#### Side-by-side sessions

A persistent session pane on the right of the chat, with a draggable divider. New header toggle hides it when you want the chat full-width — state and width persist across reloads.

#### Pin / Star — actually toggleable

Right-click any session. Pin floats it to the top of the list; Star prefixes it with ⭐. Both toggle on/off, and the menu labels flip to `Unpin` / `Unstar` so it's obvious what the next click does. Existing rename and delete still work exactly as they did.

#### Filter sessions

New filter button to the left of the sidebar-collapse toggle. Multi-select flyout with two groups:

- **Type**: 📌 Pinned, ⭐ Starred, Running, Waiting
- **Age**: Last 1 hour, 24 hours, 7 days, 30 days

Empty selection = show everything. Within a group, choices OR. Across groups, they AND (so "Pinned ∩ Last 24h" works). Selections persist in `localStorage` and the inline list re-renders live as you toggle. A small blue dot on the button signals when any filter is active; "Clear all" wipes it.

#### Status dots

| Indicator       | Meaning                                                            |
| --------------- | ------------------------------------------------------------------ |
| 🟡 Pulsing amber | Claude is asking you something — a permission prompt, AskUserQuestion, anything that's actually blocking on you |
| Spinner         | Session is actively working                                        |
| 🔵 Blue dot      | Just finished. Clears on click                                     |

Priority is **waiting → running → done**, so the most-actionable state wins. The waiting indicator reads `session.permissionRequests` — true exactly when a popup is open in that session, gone the moment you answer or dismiss it. Suppressed on the session you're currently viewing (no point flagging the chat you're already in).

#### Quality-of-life fixes

- **Rewind without file changes** — the *Rewind code* dialog no longer disables its primary button when only the conversation context changed.
- **Modals stay on top** — all five overlay classes in the bundle are now above the session pane and resize divider, so dialogs don't get clipped.
- **Layout doesn't break on long messages** — chat and session panes carry the flex `min-width: 0 / min-height: 0` they always needed, so a wide code block can't push the divider or clip the pane.

---

## Upgrading

Re-run the script. The marketplace download always pulls the latest extension, and `--install-extension --force` replaces whatever's currently loaded. Old helper blocks are stripped before the new one is injected.

## Rollback

Uninstall the patched VSIX from the VS Code Extensions panel and reinstall the stock extension from the Marketplace.

## Compatibility

Tested against Claude Code **2.1.148**. Anthropic ships new bundles regularly and minified identifiers shift — if the patcher errors with *"Could not find Claude session-list helper anchor"*, the bundle has moved. Open an issue with the extension version and the failing anchor.

---

## Power-user usage

```bash
# Skip auto-install, just write the patched .vsix
python patch_claude_vsix_tasks.py --vsix-only

# Patch a specific local .vsix instead of downloading
python patch_claude_vsix_tasks.py ./anthropic.claude-code-2.1.148.vsix

# Custom output path
python patch_claude_vsix_tasks.py --out ./claude-code.patched.vsix

# Print version
python patch_claude_vsix_tasks.py --patcher-version
```

The full feature spec sent to the Anthropic team lives in [CLAUDE_EXTENSION_FEEDBACK.md](CLAUDE_EXTENSION_FEEDBACK.md) if you want the long version.

---

## Changelog

**v0.4.0** — Filter button in the header. Multi-select flyout: Type (Pinned / Starred / Running / Waiting) × Age (1h / 24h / 7d / 30d). Filters apply to both the inline session pane and the search popup. Active state persists in `localStorage`; the inline list subscribes to filter changes via a header-component effect so toggles re-render immediately. Helper-block freshness sentinel bumped (`ccPatchFilterSort`) so older patched installs auto-upgrade on re-run.

**v0.3.1** — Waiting indicator now reads `session.permissionRequests` (the array backing the popup itself) instead of `pendingInput`, which could latch true after a click and never clear. Priority reordered to `waiting → running → done` so the amber dot wins when a popup is open (otherwise the spinner stole the slot while Claude was paused mid-tool-use). Removed `ccPatchDebugState` dev helper that was leaking into release builds.

**v0.3.0** — Default flow is now download-latest-from-Marketplace → patch → auto-install via `code --install-extension --force`. No more "I patched the wrong installed version" footgun (VS Code can have multiple versions of an extension side-by-side and only loads the highest). Pass `--vsix-only` to opt out of auto-install.

**v0.2.0–v0.2.3** — Iteration on the waiting indicator: started with a brittle "last message was from assistant" heuristic, moved to `pendingInput`, finally settled on `permissionRequests` in v0.3.1 above. Toggleable Star, dynamic Unpin/Unstar labels, hardened modal/flex layout, header show/hide toggle.

**v0.1.0** — First release: persistent right-side session pane, draggable divider, pin/star context menu, running spinner, done dot, rewind-without-file-changes fix.

## License

MIT.
