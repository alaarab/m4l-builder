"""Seed-history "dice brain" for variation macros (Shard's DICE).

A plain ``js`` module (no UI) that owns the DICE policy and the roll
history, so both are Node-testable instead of living as pak-assembly
hazards in the patch:

* one DICE press = one ``roll <rand> <vary>`` message. The brain derives
  the new seed tuple from ``<rand>`` via an internal LCG and the VARY
  policy: ``vary`` == 0 or >= 70 -> FULL reseed (classic dice; wild also
  refreshes the mutation salt); 0 < ``vary`` < 70 -> SALT-ONLY roll (the
  seeds stay — "mutate THIS groove", depth owned by the engine's
  ``vary_amount``).
* every roll pushes onto an 8-deep UNDO ring: ``back`` / ``fwd`` walk it
  (recall only, no push); a fresh roll from a back position truncates the
  redo tail; ``fwd`` at the head is inert.
* the ring is deliberately SESSION-ONLY: the *kept* roll persists through
  the device's existing Stored-Only seed hosts — the brain is primed from
  them at load (``seeds``/``seedp``…) and individual GEN buttons keep it
  in sync via the silent field setters.

Inlets:
    0 -- messages: ``roll <rand> <vary>``, ``back``, ``fwd``,
         ``seeds <p> <c> <g> <m> <v>`` (prime current, silent; seeds the
         ring once), ``seedp/seedc/seedg/seedm/seedv <n>`` (silent field
         sync from individual GEN rolls)

Outlets:
    0 -- ``seeds <pseed> <cseed> <gseed> <mseed> <vsalt>`` (one ordered
         list per roll/walk — the device unpacks and silent-writes hosts)
    1 -- ``pos <index> <count>`` after every ring movement (history dots)
"""

SEED_HISTORY_OUTLETS = 2


def seed_history_js(*, depth: int = 8) -> str:
    """Return JavaScript source for the DICE / seed-history brain."""
    return (
        "inlets = 1;\n"
        "outlets = 2;\n"
        f"var DEPTH = {int(depth)};\n"
        "var ring = [];\n"
        "var pos = -1;\n"
        "var cur = [11, 37, 53, 79, 0];\n"    # pseed cseed gseed mseed vsalt
        "\n"
        "function lcg_next(s) {\n"
        "    return (s * 16807) % 2147483647;\n"
        "}\n"
        "\n"
        "function emit() {\n"
        "    outlet(1, 'pos', pos, ring.length);\n"
        "    outlet(0, 'seeds', cur[0], cur[1], cur[2], cur[3], cur[4]);\n"
        "}\n"
        "\n"
        "function push_cur() {\n"
        "    ring.length = pos + 1;\n"    # undo semantics: drop the redo tail
        "    ring.push(cur.slice());\n"
        "    if (ring.length > DEPTH) ring.shift();\n"
        "    pos = ring.length - 1;\n"
        "}\n"
        "\n"
        "function seeds(p, c, g, m, v) {\n"    # prime from hosts (silent)
        "    cur = [Math.round(p), Math.round(c), Math.round(g),\n"
        "           Math.round(m), Math.round(v)];\n"
        "    if (ring.length === 0) push_cur();\n"
        "    else ring[pos] = cur.slice();\n"
        "}\n"
        "\n"
        "function seedp(n) { cur[0] = Math.round(n); }\n"
        "function seedc(n) { cur[1] = Math.round(n); }\n"
        "function seedg(n) { cur[2] = Math.round(n); }\n"
        "function seedm(n) { cur[3] = Math.round(n); }\n"
        "function seedv(n) { cur[4] = Math.round(n); }\n"
        "\n"
        "function roll(rand, vary) {\n"
        "    var s = Math.max(1, Math.round(rand));\n"
        "    function draw() { s = lcg_next(s); return s % 32000; }\n"
        "    if (vary > 0.5 && vary < 70.0) {\n"
        "        cur = cur.slice();\n"    # mutate THIS groove: new salt only
        "        cur[4] = draw();\n"
        "    } else {\n"
        "        cur = [draw(), draw(), draw(), draw(), draw()];\n"
        "    }\n"
        "    push_cur();\n"
        "    emit();\n"
        "}\n"
        "\n"
        "function back() {\n"
        "    if (pos <= 0) return;\n"
        "    pos -= 1;\n"
        "    cur = ring[pos].slice();\n"
        "    emit();\n"
        "}\n"
        "\n"
        "function fwd() {\n"
        "    if (pos >= ring.length - 1) return;\n"    # inert at the head
        "    pos += 1;\n"
        "    cur = ring[pos].slice();\n"
        "    emit();\n"
        "}\n"
    )
