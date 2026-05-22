#!/usr/bin/env python
"""VSCode Claude Code Extension Improvement's Patch.

Post-build patcher for the Claude Code VS Code extension. Adds a persistent
right-side session pane, pin/star, status indicators (running / done / waiting),
a header toggle, and modal/layout fixes. See README.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

__version__ = "0.2.3"

DEFAULT_MARKETPLACE_ITEM = "anthropic.claude-code"
MARKETPLACE_QUERY_URL = "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery?api-version=7.2-preview.1"
LOG_PATH: Path | None = None


def log(message: str) -> None:
    line = f"[{dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    if LOG_PATH is not None:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def marketplace_item_from_target(target: str) -> str | None:
    if target.startswith(("http://", "https://")):
        item = urllib.parse.parse_qs(urllib.parse.urlparse(target).query).get("itemName", [""])[0].strip()
        return item or None
    if "." in target and not any(sep in target for sep in ("/", "\\")) and not target.lower().endswith(".vsix"):
        return target
    return None


def download_marketplace_vsix(item: str, dest_dir: Path, version: str | None = None) -> Path:
    body = {"filters": [{"criteria": [{"filterType": 7, "value": item}]}], "flags": 914}
    req = urllib.request.Request(
        MARKETPLACE_QUERY_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json;api-version=7.2-preview.1"},
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        data = json.load(response)
    extension = data["results"][0]["extensions"][0]
    selected = next((v for v in extension["versions"] if not version or v["version"] == version), None)
    if selected is None:
        raise RuntimeError(f"Version {version or 'latest'} not found for {item}")
    package = next(f for f in selected["files"] if f.get("assetType", "").endswith("VSIXPackage"))
    publisher = extension["publisher"]["publisherName"]
    name = extension["extensionName"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{publisher}.{name}-{selected['version']}.vsix"
    log(f"Downloading {publisher}.{name} {selected['version']} to {dest}")
    urllib.request.urlretrieve(package["source"], dest)
    log(f"Downloaded VSIX size: {dest.stat().st_size} bytes")
    return dest


CLAUDE_HELPER_JS = r"""function ccPatchTitle(e){return(e.summary?.value||`Untitled`).trim()}
function ccPatchIsStarred(e){return ccPatchTitle(e).startsWith(`⭐ `)}
function ccPatchIsPinned(e){let t=ccPatchTitle(e);return t.startsWith(`📌 `)||t.startsWith(`⭐ 📌 `)}
function ccPatchToggleStarTitle(e){let t=ccPatchTitle(e);if(t.startsWith(`⭐ 📌 `))return`📌 ${t.slice(4).trimStart()}`;if(t.startsWith(`⭐ `))return t.slice(2).trimStart();if(t.startsWith(`📌 `))return`⭐ ${t}`;return`⭐ ${t}`}
function ccPatchStarTitle(e){return ccPatchToggleStarTitle(e)}
function ccPatchPinTitle(e){let t=ccPatchTitle(e),n=t.startsWith(`⭐ `),r=n?t.slice(2).trimStart():t;return r.startsWith(`📌 `)?(n?`⭐ `:``)+r.slice(2).trimStart():(n?`⭐ 📌 `:`📌 `)+r}
function ccPatchSortSessions(e,t){return Number(ccPatchIsPinned(t))-Number(ccPatchIsPinned(e))||t.lastModifiedTime.value-e.lastModifiedTime.value}
function ccPatchSessionId(e){return e.sessionId?.value||e.internalId||ccPatchTitle(e)}
var ccPatchBusyBySession=new Map,ccPatchDoneSessions=new Set;
function ccPatchTrackSessionStatus(e,t){let n=ccPatchSessionId(e),r=!!e.busy?.value,a=ccPatchBusyBySession.get(n);a===void 0?ccPatchBusyBySession.set(n,r):(a&&!r&&(ccPatchDoneSessions.add(n),setTimeout(t,0)),ccPatchBusyBySession.set(n,r))}
function ccPatchClearDone(e){ccPatchDoneSessions.delete(ccPatchSessionId(e))}
function ccPatchIsWaiting(e){return!!e.pendingInput?.value&&!e.busy?.value}
function ccPatchSessionIndicator(e,t){if(e.busy?.value)return`running`;if(!t&&ccPatchIsWaiting(e))return`waiting`;if(ccPatchDoneSessions.has(ccPatchSessionId(e)))return`done`;return``}
function ccPatchCloseMenu(){document.querySelector(`.claudePatchContextMenu`)?.remove()}
function ccPatchShowMenu(e,t,n,r,a,i){ccPatchCloseMenu();let s=document.createElement(`div`);s.className=`claudePatchContextMenu`,s.style.left=`${Math.min(e,window.innerWidth-150)}px`,s.style.top=`${Math.min(t,window.innerHeight-72)}px`;let o=(c,l)=>{let d=document.createElement(`button`),u=!1,h=(p)=>{p.preventDefault(),p.stopPropagation();if(u)return;u=!0,ccPatchCloseMenu(),l()};return d.textContent=c,d.onmousedown=h,d.onclick=h,s.appendChild(d),d};o(a||`Pin`,n),o(i||`Star`,r),document.body.appendChild(s);setTimeout(()=>document.addEventListener(`mousedown`,ccPatchCloseMenu,{once:!0}),0)}
function ccPatchStartResize(e){e.preventDefault();let t=e.currentTarget.parentElement?.querySelector(`.claudePatchInlineSessions`);if(!t||document.body.classList.contains(`claudePatchSessionsHidden`))return;let n=e.clientX,r=t.getBoundingClientRect().width,a=(i)=>{let s=Math.max(180,Math.min(window.innerWidth*.75,r-(i.clientX-n)));document.documentElement.style.setProperty(`--claude-patch-sessions-width`,`${s}px`);try{localStorage.setItem(`claudePatchSessionsWidth`,String(s))}catch(o){}},o=()=>{document.removeEventListener(`pointermove`,a),document.removeEventListener(`pointerup`,o)};document.addEventListener(`pointermove`,a),document.addEventListener(`pointerup`,o)}
function ccPatchAreSessionsHidden(){try{return localStorage.getItem(`claudePatchSessionsHidden`)===`1`}catch(e){return!1}}
function ccPatchApplyVisibility(){let e=ccPatchAreSessionsHidden();document.body.classList.toggle(`claudePatchSessionsHidden`,e);try{let t=parseFloat(localStorage.getItem(`claudePatchSessionsWidth`)||``);if(t>=180&&t<=window.innerWidth*.75)document.documentElement.style.setProperty(`--claude-patch-sessions-width`,`${t}px`)}catch(n){}}
function ccPatchToggleSessions(){let e=!ccPatchAreSessionsHidden();try{localStorage.setItem(`claudePatchSessionsHidden`,e?`1`:`0`)}catch(t){}document.body.classList.toggle(`claudePatchSessionsHidden`,e)}
if(typeof document!==`undefined`){if(document.readyState===`loading`)document.addEventListener(`DOMContentLoaded`,ccPatchApplyVisibility);else ccPatchApplyVisibility()}
"""


def patch_webview_js(webview_js: Path) -> bool:
    text = read(webview_js)
    changed = False
    anchor = "var _R0=16,wR0=1000;"
    if anchor not in text:
        raise RuntimeError("Could not find Claude session-list helper anchor")
    if "!!e.pendingInput?.value&&!e.busy?.value" not in text:
        # Upgrade path: an older helper block may already be present. Strip it
        # back to the anchor, then re-inject the current helper block.
        helper_start = text.find("function ccPatchTitle(")
        if helper_start != -1:
            anchor_pos = text.find(anchor, helper_start)
            if anchor_pos == -1:
                raise RuntimeError("Found old Claude helper block but lost anchor")
            text = text[:helper_start] + text[anchor_pos:]
        text = text.replace(anchor, CLAUDE_HELPER_JS + anchor, 1)
        changed = True

    old_sort = '}):_1,t=S0.useRef(F);'
    new_sort = '}):_1;b=[...b].sort(ccPatchSortSessions);let t=S0.useRef(F);'
    if old_sort in text:
        text = text.replace(old_sort, new_sort, 1)
        changed = True

    old_status_hook = 'z6();let j=S0.useRef(null),D=S0.useRef(!0);'
    new_status_hook = 'z6();let j=S0.useRef(null),D=S0.useRef(!0),[L,I]=S0.useState(0);S0.useEffect(()=>{ccPatchTrackSessionStatus(Z,()=>I(M=>M+1))},[Z,Z.busy?.value]);'
    if old_status_hook in text:
        text = text.replace(old_status_hook, new_status_hook, 1)
        changed = True

    old_context = 'return S0.default.createElement("button",{ref:F,className:`${w2.sessionItem} ${J?w2.active:""} ${Y?w2.focused:""}`,onClick:X?void 0:G,onMouseMove:q},'
    new_context = 'return S0.default.createElement("button",{ref:F,className:`${w2.sessionItem} ${J?w2.active:""} ${Y?w2.focused:""}`,onClick:X?void 0:(M)=>{ccPatchClearDone(Z),I(W5=>W5+1),G(M)},onMouseMove:q,onContextMenu:(M)=>{if(z&&Z.sessionId.value)M.preventDefault(),M.stopPropagation(),ccPatchShowMenu(M.clientX,M.clientY,()=>U(Z,ccPatchPinTitle(Z)),()=>U(Z,ccPatchToggleStarTitle(Z)),ccPatchIsPinned(Z)?"Unpin":"Pin",ccPatchIsStarred(Z)?"Unstar":"Star")}},'
    if old_context in text:
        text = text.replace(old_context, new_context, 1)
        changed = True
    # Upgrade path: replace the v0.1.x / v0.2.0 context handler (hardcoded labels, one-way Star) with the v0.2.1 form.
    legacy_context_handler = 'onContextMenu:(M)=>{if(z&&Z.sessionId.value)M.preventDefault(),M.stopPropagation(),ccPatchShowMenu(M.clientX,M.clientY,()=>U(Z,ccPatchPinTitle(Z)),()=>U(Z,ccPatchStarTitle(Z)))}'
    new_context_handler = 'onContextMenu:(M)=>{if(z&&Z.sessionId.value)M.preventDefault(),M.stopPropagation(),ccPatchShowMenu(M.clientX,M.clientY,()=>U(Z,ccPatchPinTitle(Z)),()=>U(Z,ccPatchToggleStarTitle(Z)),ccPatchIsPinned(Z)?"Unpin":"Pin",ccPatchIsStarred(Z)?"Unstar":"Star")}'
    if legacy_context_handler in text:
        text = text.replace(legacy_context_handler, new_context_handler, 1)
        changed = True

    old_status_var = 'let _=J&&!Z.summary.value&&!Z.messages.value.length&&!Z.teleportedMessageCount.value;return'
    new_status_var = 'let R1=ccPatchSessionIndicator(Z,J),_=J&&!Z.summary.value&&!Z.messages.value.length&&!Z.teleportedMessageCount.value;return'
    if old_status_var in text:
        text = text.replace(old_status_var, new_status_var, 1)
        changed = True
    # Upgrade path: v0.2.0..v0.2.2 passed only Z; bring it to the active-aware 2-arg form.
    legacy_status_var = 'let R1=ccPatchSessionIndicator(Z),_=J&&!Z.summary.value&&!Z.messages.value.length&&!Z.teleportedMessageCount.value;return'
    if legacy_status_var in text:
        text = text.replace(legacy_status_var, new_status_var, 1)
        changed = True

    old_status_insert = 'S0.default.createElement("span",{className:w2.sessionName},Le1(Kk(Z),Q)),B&&Z.worktree.value&&Z.worktree.value.path!==W&&'
    new_status_insert = 'S0.default.createElement("span",{className:w2.sessionName},Le1(Kk(Z),Q)),R1&&S0.default.createElement("span",{className:`claudePatchStatus claudePatchStatus${R1.charAt(0).toUpperCase()}${R1.slice(1)}`,title:R1==="running"?"Running":R1==="waiting"?"Waiting for your reply":"Completed"}),B&&Z.worktree.value&&Z.worktree.value.path!==W&&'
    if old_status_insert in text:
        text = text.replace(old_status_insert, new_status_insert, 1)
        changed = True
    # Upgrade path: replace the legacy 2-state status span with the 3-state one.
    legacy_status_span = 'R1&&S0.default.createElement("span",{className:`claudePatchStatus ${R1==="running"?"claudePatchStatusRunning":"claudePatchStatusDone"}`,title:R1==="running"?"Running":"Completed"})'
    new_status_span = 'R1&&S0.default.createElement("span",{className:`claudePatchStatus claudePatchStatus${R1.charAt(0).toUpperCase()}${R1.slice(1)}`,title:R1==="running"?"Running":R1==="waiting"?"Waiting for your reply":"Completed"})'
    if legacy_status_span in text:
        text = text.replace(legacy_status_span, new_status_span, 1)
        changed = True

    old_inline = 'p0.default.createElement("div",{className:h6.body},p0.default.createElement("div",{className:h6.content},'
    new_inline = 'p0.default.createElement("div",{className:h6.body},p0.default.createElement("div",{className:"claudePatchInlineSessions"},p0.default.createElement(Rs,{localSessions:[...u].sort(ccPatchSortSessions),localSessionsLoaded:$.localSessionsLoaded.value,remoteSessions:[...o].sort(ccPatchSortSessions),remoteConnected:$.remoteConnected.value,remoteReconnecting:$.remoteReconnecting.value,remoteSessionsLoaded:$.remoteSessionsLoaded.value,onReconnectRemote:()=>{$.listRemoteSessions()},activeSession:$.activeSession.value||null,onSessionClick:x,onRenameSession:s,onDeleteSession:_1,onOpenInNewWindow:Z.host!=="jetbrains"?r:void 0,currentCwd:Z.defaultCwd.value,authMethod:Z.authStatus.value?.authMethod,onRefresh:()=>{$.listSessions(),$.listRemoteSessions()},onOpenURL:Z.openURL})),p0.default.createElement("div",{className:"claudePatchResizeHandle",onPointerDown:ccPatchStartResize}),p0.default.createElement("div",{className:`${h6.content} claudePatchMainContent`},'
    if old_inline in text:
        text = text.replace(old_inline, new_inline, 1)
        changed = True

    old_rewind = "let B=q?.filesChanged&&q.filesChanged.length>0,W=q?.canRewind&&!Q&&(B||J);"
    new_rewind = "let B=q?.filesChanged&&q.filesChanged.length>0,W=q?.canRewind&&!Q;"
    if old_rewind in text:
        text = text.replace(old_rewind, new_rewind, 1)
        changed = True

    old_history_btn = 'p0.default.createElement(QQ,{ref:X,ariaLabel:"Session history",iconSize:20,onClick:()=>q(!G)},p0.default.createElement(in1,null))'
    toggle_btn = 'p0.default.createElement(QQ,{ariaLabel:"Toggle session pane",iconSize:20,onClick:ccPatchToggleSessions},p0.default.createElement("span",{className:"claudePatchSidebarIcon","aria-hidden":"true"}))'
    new_history_btn = toggle_btn + "," + old_history_btn
    if old_history_btn in text and toggle_btn not in text:
        text = text.replace(old_history_btn, new_history_btn, 1)
        changed = True

    if changed:
        write(webview_js, text)
    return changed


CSS_SENTINEL_START = "/*claudePatch:start*/"
CSS_SENTINEL_END = "/*claudePatch:end*/"


def patch_webview_css(webview_css: Path) -> bool:
    text = read(webview_css)
    changed = False
    anchor = ".dropdown_Wc_2Bg{position:fixed;background:var(--app-menu-background);border:1px solid var(--app-menu-border);display:flex;z-index:1000;outline:none;box-sizing:border-box;border-radius:12px;flex-direction:column;width:min(400px,100vw - 32px);max-height:min(500px,50vh);padding:6px;box-shadow:0 4px 16px #0000001a}"
    patch_body = (
        ".claudePatchMainContent{position:relative;z-index:2;min-width:0;min-height:0;overflow:hidden}"
        ".overlay_f3sAzg,.overlay_W2z5EA,.overlay_yumWmQ,.overlay_5FHdxw,.overlay_ukWSlw{z-index:10000;background-color:#000000e6}"
        ".claudePatchInlineSessions{order:2;position:relative;z-index:0;flex:0 0 var(--claude-patch-sessions-width,min(44vw,360px));min-width:180px;max-width:75%;border-left:1px solid var(--app-primary-border-color);overflow:hidden;background:var(--app-primary-background)}"
        ".claudePatchInlineSessions>div{height:100%}"
        ".claudePatchResizeHandle{order:1;position:relative;z-index:0;flex:0 0 4px;cursor:col-resize;background:var(--app-primary-border-color);opacity:.5}"
        ".claudePatchResizeHandle:hover,.claudePatchResizeHandle:active{opacity:1;background:var(--vscode-sash-hoverBorder,var(--app-primary-border-color))}"
        "body.claudePatchSessionsHidden .claudePatchInlineSessions,body.claudePatchSessionsHidden .claudePatchResizeHandle{display:none!important}"
        ".claudePatchSidebarIcon{display:inline-block;width:14px;height:14px;border:1.5px solid currentColor;border-radius:2px;box-sizing:border-box;position:relative;opacity:.9}"
        ".claudePatchSidebarIcon::after{content:'';position:absolute;top:0;bottom:0;right:0;width:5px;background:currentColor;border-radius:0 .5px .5px 0}"
        "body.claudePatchSessionsHidden .claudePatchSidebarIcon{opacity:.55}"
        "body.claudePatchSessionsHidden .claudePatchSidebarIcon::after{background:transparent}"
        ".claudePatchStatus{flex:0 0 auto;width:8px;height:8px;border-radius:50%;margin-left:2px}"
        ".claudePatchStatusDone{background:var(--vscode-charts-blue,#3b82f6)}"
        ".claudePatchStatusWaiting{background:var(--vscode-charts-yellow,#f59e0b);box-shadow:0 0 0 0 var(--vscode-charts-yellow,#f59e0b);animation:claudePatchWaitingPulse 1.6s ease-in-out infinite}"
        ".claudePatchStatusRunning{box-sizing:border-box;width:10px;height:10px;background:transparent;border:2px solid var(--app-secondary-foreground);border-top-color:transparent;animation:claudePatchSpin .8s linear infinite}"
        "@keyframes claudePatchSpin{to{transform:rotate(360deg)}}"
        "@keyframes claudePatchWaitingPulse{0%,100%{opacity:1;box-shadow:0 0 0 0 color-mix(in srgb,var(--vscode-charts-yellow,#f59e0b)55%,transparent)}50%{opacity:.85;box-shadow:0 0 0 4px color-mix(in srgb,var(--vscode-charts-yellow,#f59e0b)0%,transparent)}}"
        ".claudePatchContextMenu{position:fixed;z-index:2000;background:var(--app-menu-background);border:1px solid var(--app-menu-border);border-radius:6px;padding:4px;box-shadow:0 4px 16px #00000040;display:flex;flex-direction:column;min-width:120px}"
        ".claudePatchContextMenu button{background:transparent;border:0;color:var(--app-primary-foreground);text-align:left;padding:6px 10px;border-radius:4px;cursor:pointer}"
        ".claudePatchContextMenu button:hover{background:var(--app-list-hover-background)}"
    )
    new_block = CSS_SENTINEL_START + patch_body + CSS_SENTINEL_END
    # Strip any prior patched block so reapplying always lands the current CSS.
    start = text.find(CSS_SENTINEL_START)
    end = text.find(CSS_SENTINEL_END)
    if start != -1 and end != -1 and end > start:
        text = text[:start] + text[end + len(CSS_SENTINEL_END):]
        changed = True
    # Also strip the v0.0.x / v0.1.x raw-appended blocks (no sentinels).
    for legacy in _LEGACY_CSS_BLOCKS:
        if legacy in text:
            text = text.replace(legacy, "", 1)
            changed = True
    if anchor not in text:
        raise RuntimeError("Could not find Claude CSS anchor")
    if new_block not in text:
        text = text.replace(anchor, anchor + new_block, 1)
        changed = True
    if changed:
        write(webview_css, text)
    return changed


_LEGACY_CSS_BLOCKS = (
    # v0.0.x — original spec, before toggle support
    ".claudePatchMainContent{position:relative;z-index:2;overflow:visible}.overlay_f3sAzg{z-index:10000;background-color:#000000e6}.claudePatchInlineSessions{order:2;position:relative;z-index:0;flex:0 0 var(--claude-patch-sessions-width,min(44vw,360px));min-width:180px;max-width:75%;border-left:1px solid var(--app-primary-border-color);overflow:hidden;background:var(--app-primary-background)}.claudePatchInlineSessions>div{height:100%}.claudePatchResizeHandle{order:1;position:relative;z-index:0;flex:0 0 4px;cursor:col-resize;background:var(--app-primary-border-color);opacity:.5}.claudePatchResizeHandle:hover,.claudePatchResizeHandle:active{opacity:1;background:var(--vscode-sash-hoverBorder,var(--app-primary-border-color))}.claudePatchStatus{flex:0 0 auto;width:8px;height:8px;border-radius:50%;margin-left:2px}.claudePatchStatusDone{background:var(--vscode-charts-blue,#3b82f6)}.claudePatchStatusRunning{box-sizing:border-box;width:10px;height:10px;background:transparent;border:2px solid var(--app-secondary-foreground);border-top-color:transparent;animation:claudePatchSpin .8s linear infinite}@keyframes claudePatchSpin{to{transform:rotate(360deg)}}.claudePatchContextMenu{position:fixed;z-index:2000;background:var(--app-menu-background);border:1px solid var(--app-menu-border);border-radius:6px;padding:4px;box-shadow:0 4px 16px #00000040;display:flex;flex-direction:column;min-width:120px}.claudePatchContextMenu button{background:transparent;border:0;color:var(--app-primary-foreground);text-align:left;padding:6px 10px;border-radius:4px;cursor:pointer}.claudePatchContextMenu button:hover{background:var(--app-list-hover-background)}",
    # v0.1.x — added toggle, min-width/min-height, extra overlay classes, but no waiting indicator
    ".claudePatchMainContent{position:relative;z-index:2;min-width:0;min-height:0;overflow:hidden}.overlay_f3sAzg,.overlay_W2z5EA,.overlay_yumWmQ,.overlay_5FHdxw,.overlay_ukWSlw{z-index:10000;background-color:#000000e6}.claudePatchInlineSessions{order:2;position:relative;z-index:0;flex:0 0 var(--claude-patch-sessions-width,min(44vw,360px));min-width:180px;max-width:75%;border-left:1px solid var(--app-primary-border-color);overflow:hidden;background:var(--app-primary-background)}.claudePatchInlineSessions>div{height:100%}.claudePatchResizeHandle{order:1;position:relative;z-index:0;flex:0 0 4px;cursor:col-resize;background:var(--app-primary-border-color);opacity:.5}.claudePatchResizeHandle:hover,.claudePatchResizeHandle:active{opacity:1;background:var(--vscode-sash-hoverBorder,var(--app-primary-border-color))}body.claudePatchSessionsHidden .claudePatchInlineSessions,body.claudePatchSessionsHidden .claudePatchResizeHandle{display:none!important}.claudePatchSidebarIcon{display:inline-block;width:14px;height:14px;border:1.5px solid currentColor;border-radius:2px;box-sizing:border-box;position:relative;opacity:.9}.claudePatchSidebarIcon::after{content:'';position:absolute;top:0;bottom:0;right:0;width:5px;background:currentColor;border-radius:0 .5px .5px 0}body.claudePatchSessionsHidden .claudePatchSidebarIcon{opacity:.55}body.claudePatchSessionsHidden .claudePatchSidebarIcon::after{background:transparent}.claudePatchStatus{flex:0 0 auto;width:8px;height:8px;border-radius:50%;margin-left:2px}.claudePatchStatusDone{background:var(--vscode-charts-blue,#3b82f6)}.claudePatchStatusRunning{box-sizing:border-box;width:10px;height:10px;background:transparent;border:2px solid var(--app-secondary-foreground);border-top-color:transparent;animation:claudePatchSpin .8s linear infinite}@keyframes claudePatchSpin{to{transform:rotate(360deg)}}.claudePatchContextMenu{position:fixed;z-index:2000;background:var(--app-menu-background);border:1px solid var(--app-menu-border);border-radius:6px;padding:4px;box-shadow:0 4px 16px #00000040;display:flex;flex-direction:column;min-width:120px}.claudePatchContextMenu button{background:transparent;border:0;color:var(--app-primary-foreground);text-align:left;padding:6px 10px;border-radius:4px;cursor:pointer}.claudePatchContextMenu button:hover{background:var(--app-list-hover-background)}",
)


def patch_extension_dir(extension_dir: Path) -> bool:
    changed = False
    webview_js = extension_dir / "webview" / "index.js"
    webview_css = extension_dir / "webview" / "index.css"
    if not webview_js.exists() or not webview_css.exists():
        raise RuntimeError("Could not find Claude webview index.js/index.css")
    log("Patching Claude webview JS")
    changed |= patch_webview_js(webview_js)
    log("Patching Claude webview CSS")
    changed |= patch_webview_css(webview_css)
    verify_extension_dir(extension_dir)
    return changed


def verify_extension_dir(extension_dir: Path) -> None:
    js = read(extension_dir / "webview" / "index.js")
    css = read(extension_dir / "webview" / "index.css")
    checks = {
        "star helper": "ccPatchStarTitle" in js,
        "pin helper": "ccPatchPinTitle" in js,
        "context menu": "ccPatchShowMenu" in js and ".claudePatchContextMenu" in css,
        "pin sort": "ccPatchSortSessions" in js,
        "inline sessions": "claudePatchInlineSessions" in js and ".claudePatchInlineSessions" in css,
        "main content overlay": "claudePatchMainContent" in js and ".claudePatchMainContent{position:relative;z-index:2;min-width:0;min-height:0;overflow:hidden}" in css,
        "modal backdrop": ".overlay_f3sAzg,.overlay_W2z5EA,.overlay_yumWmQ,.overlay_5FHdxw,.overlay_ukWSlw{z-index:10000;background-color:#000000e6}" in css,
        "sidebar toggle": "ccPatchToggleSessions" in js and 'ariaLabel:"Toggle session pane"' in js and ".claudePatchSidebarIcon" in css,
        "sessions hidden state": "body.claudePatchSessionsHidden .claudePatchInlineSessions,body.claudePatchSessionsHidden .claudePatchResizeHandle{display:none!important}" in css,
        "resize handle": "ccPatchStartResize" in js and ".claudePatchResizeHandle{order:1;position:relative;z-index:0;" in css,
        "status indicators": "ccPatchSessionIndicator" in js and ".claudePatchStatusRunning" in css and ".claudePatchStatusDone" in css,
        "waiting indicator": "ccPatchIsWaiting" in js and ".claudePatchStatusWaiting" in css and "@keyframes claudePatchWaitingPulse" in css,
        "star toggle + dynamic labels": "ccPatchIsStarred" in js and "ccPatchToggleStarTitle" in js and 'ccPatchIsPinned(Z)?"Unpin":"Pin"' in js and 'ccPatchIsStarred(Z)?"Unstar":"Star"' in js,
        "rewind without file changes": "W=q?.canRewind&&!Q;" in js,
        "edit actions preserved": 'title:"Rename session"' in js and 'title:"Delete session"' in js,
    }
    missing = [name for name, ok in checks.items() if not ok]
    if missing:
        raise RuntimeError("Verification failed: " + ", ".join(missing))
    node = shutil.which("node")
    if node:
        log("Running JS syntax check")
        subprocess.check_call([node, "--check", str(extension_dir / "webview" / "index.js")])
    log(f"Verification passed ({len(checks)} checks)")


def zip_dir(src: Path, dest: Path) -> None:
    if dest.exists():
        dest.unlink()
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in src.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(src).as_posix())


def main() -> int:
    global LOG_PATH
    parser = argparse.ArgumentParser(description="Patch Claude Code VSIX session list behavior.")
    parser.add_argument("target", nargs="?", default=DEFAULT_MARKETPLACE_ITEM)
    parser.add_argument("--out", default="")
    parser.add_argument("--version", default="")
    parser.add_argument("--download-dir", default=".")
    parser.add_argument("--log", default="claude-vsix-patch.log")
    parser.add_argument("-V", "--patcher-version", action="version", version=f"vscode-claude-code-extension-improvements-patch {__version__}")
    args = parser.parse_args()

    LOG_PATH = Path(args.log).expanduser().resolve()
    LOG_PATH.write_text("", encoding="utf-8")
    log(f"Starting Claude VSIX patcher v{__version__}")
    raw = args.target
    raw_path = Path(raw).expanduser()
    if raw_path.exists() or raw_path.suffix.lower() == ".vsix":
        target = raw_path.resolve()
        if not target.exists():
            raise RuntimeError(f"VSIX file not found: {target}")
        log(f"Using local target: {target}")
    else:
        item = marketplace_item_from_target(raw)
        if item is None:
            raise RuntimeError(f"Target does not exist and is not a Marketplace item or URL: {raw}")
        target = download_marketplace_vsix(item, Path(args.download_dir).expanduser().resolve(), args.version or None)

    out = Path(args.out).resolve() if args.out else target.with_name(target.stem + ".tasks-patched.vsix")
    log(f"Output VSIX: {out}")
    with tempfile.TemporaryDirectory(prefix="claude-vsix-patch-") as temp:
        root = Path(temp) / "vsix"
        log("Extracting VSIX")
        with zipfile.ZipFile(target) as zf:
            zf.extractall(root)
        changed = patch_extension_dir(root / "extension")
        log("Writing patched VSIX")
        zip_dir(root, out)
    log(f"Patched VSIX written: {out}")
    log(f"Overall status: {'updated files' if changed else 'already patched'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log(f"Patch run failed: {exc}")
        raise
