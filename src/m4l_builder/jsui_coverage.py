"""MAX-VALIDATION L2 — jsui/v8ui message-handler coverage.

The failure this catches: a message is routed into a ``jsui``/``v8ui`` whose
script defines no handler for it. Max logs ``js: no function <name>`` to the
console and the message is silently dropped. Nothing else in the build gate
sees it — the box exists, the wire exists, the script exists, and every
structural check passes. It only shows up as a control that quietly does
nothing, which is the same symptom as the dead-control class this repo has
now shipped several times.

This is the PRESENT-but-incomplete case. The missing-sidecar case (a jsui
whose script is not registered at all) is already caught in
``amxd.build_device``.

Scope, deliberately narrow to keep false positives at zero:

* Only selectors that are *statically* determinable are checked — a
  ``prepend X``, a ``message`` box whose first token is a bare word, or a
  ``loadmess X``. Anything computed at runtime is skipped rather than guessed.
* ``---`` send/receive buses are NOT traced. The receive lives inside the
  subpatcher and the send side may be in another device instance entirely, so
  a static trace would produce confident nonsense.
* A script defining ``anything()`` is treated as covering everything, which is
  what Max does.
"""

from __future__ import annotations

import re

# Handlers Max dispatches to fixed names rather than to a same-named function.
# A script receiving these needs the mapped name, not a function called "int".
_BUILTIN_MESSAGE_HANDLERS = {
    "bang": ("bang",),
    "int": ("msg_int", "anything"),
    "float": ("msg_float", "anything"),
    "list": ("list", "anything"),
}

# Messages the jsui/v8ui OBJECT consumes itself — they never reach the script,
# so a missing function is not a defect.
_OBJECT_LEVEL_MESSAGES = frozenset({
    "size", "bringtofront", "sendtoback", "hide", "show", "script",
    "jsargs", "compile", "autowatch", "loadbang", "closebang", "paint",
    "notifydeleted", "onresize", "local", "front", "back", "read", "write",
})

_FUNC_RE = re.compile(r"^\s*function\s+([A-Za-z_$][\w$]*)\s*\(", re.M)
_ASSIGN_FN_RE = re.compile(
    r"^\s*(?:var\s+)?([A-Za-z_$][\w$]*)\s*=\s*function\s*\(", re.M)
_BARE_WORD_RE = re.compile(r"^[A-Za-z_][\w.]*$")


def _declared_handlers(js: str) -> set:
    """Every function name the script defines, by either declaration form."""
    return set(_FUNC_RE.findall(js)) | set(_ASSIGN_FN_RE.findall(js))


def _selector_from_box(payload: dict):
    """The message selector this box emits, or None if not statically known."""
    maxclass = payload.get("maxclass")
    text = (payload.get("text") or "").strip()
    if not text:
        return None

    if maxclass == "message":
        first = text.split()[0]
        # "$1", "42", "set $1" -> set; a leading number or $-arg is a value,
        # not a selector, and lands on msg_int/msg_float/list.
        return first if _BARE_WORD_RE.match(first) else None

    if maxclass == "newobj":
        head = text.split()
        if head[0] == "prepend" and len(head) > 1:
            return head[1] if _BARE_WORD_RE.match(head[1]) else None
        if head[0] == "loadmess" and len(head) > 1:
            return head[1] if _BARE_WORD_RE.match(head[1]) else None
    return None


def jsui_coverage_issues(boxes: list, lines: list, support_files: dict = None):
    """Return ``(box_id, selector)`` pairs routed into a jsui with no handler.

    ``support_files`` maps filename -> {"content": str}; the jsui's script is
    looked up by its ``filename`` attribute.
    """
    support_files = support_files or {}
    by_id = {}
    for entry in boxes:
        payload = entry.get("box", entry)
        if payload.get("id") is not None:
            by_id[payload["id"]] = payload

    # jsui/v8ui targets, with their script text resolved
    targets = {}
    for box_id, payload in by_id.items():
        if payload.get("maxclass") not in ("jsui", "v8ui"):
            continue
        fname = payload.get("filename")
        record = support_files.get(fname) if fname else None
        js = (record or {}).get("content") if isinstance(record, dict) else None
        if not js:
            # No script resolvable here — that is the missing-sidecar case,
            # already gated in build_device. Not this check's job.
            continue
        targets[box_id] = _declared_handlers(js)

    if not targets:
        return []

    findings = []
    for line in lines:
        patch = line.get("patchline", line)
        src, dest = patch.get("source"), patch.get("destination")
        if not src or not dest:
            continue
        dest_id = dest[0]
        if dest_id not in targets:
            continue
        src_payload = by_id.get(src[0])
        if src_payload is None:
            continue
        selector = _selector_from_box(src_payload)
        if selector is None or selector in _OBJECT_LEVEL_MESSAGES:
            continue

        declared = targets[dest_id]
        if "anything" in declared:
            continue
        accepted = _BUILTIN_MESSAGE_HANDLERS.get(selector, (selector,))
        if any(name in declared for name in accepted):
            continue
        findings.append((dest_id, selector, src[0]))
    return findings
