"""Validated helpers for common Max wiring idioms that devices used to hand-wire
and get subtly wrong. Prefer these over rolling your own — each encodes a trap
that shipped as a real bug:

* Max ``expr`` has NO ternary (``?:``) operator; a ``?`` is a silent parse error
  that kills the whole expression (this left Shard's chance/cond dead). Build
  conditionals branchlessly with :func:`expr_cond`.
* A float ``%`` in ``expr`` can silently fail to output; :func:`expr_safe_mod`
  keeps it integer and guards divide-by-zero.
* ``change`` dedupes NUMBERS — feeding it a bang is a no-op AND Max drops the
  patchline at load. :func:`dedupe_value` wires it correctly.
* A message-driven inlet is COLD (silence) until its first value;
  :func:`init_prime` gives it a fail-open default via ``loadmess``.
* :func:`debounce` is the t-b-f + delay settle used to coalesce a dragged control.
"""
from __future__ import annotations

from .stages import stage_result


def expr_cond(*cases) -> str:
    """Branchless conditional ``expr`` body (Max ``expr`` has no ``?:``).

    Each case is ``(condition, value)``; conditions must be MUTUALLY EXCLUSIVE
    (exactly one true at a time). Returns ``(c1)*(v1) + (c2)*(v2) + ...`` — wrap
    it yourself: ``add_newobj(oid, f"expr {expr_cond(...)}")``. Raises if any
    operand contains ``?`` (that is the very ternary trap this exists to avoid).
    """
    parts = []
    for cond, val in cases:
        if "?" in str(cond) or "?" in str(val):
            raise ValueError(
                "expr_cond operands must be branchless — Max expr has no ternary; "
                "a '?' is a silent parse error. Express the branch as (cond)*(val).")
        parts.append(f"({cond})*({val})")
    return " + ".join(parts)


def expr_safe_mod(a, b) -> str:
    """Integer-safe modulo sub-expression: ``(a) % ((b)+((b)==0))``.

    Guards divide-by-zero (a zero divisor becomes 1) and stays integer so the
    ``expr`` reliably fires — a float ``%`` in Max ``expr`` can silently not
    output, leaving a downstream inlet cold.
    """
    return f"({a}) % (({b})+(({b})==0))"


def debounce(device, id_prefix, source, target, *, ms=160, source_outlet=0,
             target_inlet=0, x=0, y=0):
    """Coalesce a rapidly-changing value: forward it to ``target`` only after it
    has been quiet for ``ms``. The classic ``t b f`` + ``delay`` + ``float``
    settle: outlet 1 (float) stores the latest cold, outlet 0 (bang) restarts the
    timer, and on settle the delay bangs the stored value out. Returns ids
    ``{trig, hold, delay}``.
    """
    p = id_prefix
    device.add_newobj(f"{p}_t", "t b f", numinlets=1, numoutlets=2,
                      outlettype=["bang", "float"], patching_rect=[x, y, 56, 20])
    device.add_newobj(f"{p}_f", "float", numinlets=2, numoutlets=1,
                      outlettype=["float"], patching_rect=[x, y + 25, 50, 20])
    device.add_newobj(f"{p}_d", f"delay {ms}", numinlets=2, numoutlets=1,
                      outlettype=["bang"], patching_rect=[x + 62, y, 60, 20])
    device.add_line(source, source_outlet, f"{p}_t", 0)
    device.add_line(f"{p}_t", 1, f"{p}_f", 1)   # store the latest value (cold)
    device.add_line(f"{p}_t", 0, f"{p}_d", 0)   # restart the settle timer
    device.add_line(f"{p}_d", 0, f"{p}_f", 0)   # settle -> emit stored value
    device.add_line(f"{p}_f", 0, target, target_inlet)
    return stage_result({"trig": f"{p}_t", "hold": f"{p}_f", "delay": f"{p}_d"},
                        name="debounce")


def dedupe_value(device, id_prefix, source, target, *, source_outlet=0,
                 target_inlet=0, x=0, y=0):
    """Fire ``target`` only when a NUMBER on ``source`` actually changes, via a
    ``change`` object. ``change`` ignores bangs, so feed it a number — not a
    trigger's bang outlet (that shipped as a dead patchline in Shard). Returns
    ids ``{change}``.
    """
    p = id_prefix
    device.add_newobj(f"{p}_chg", "change", numinlets=1, numoutlets=3,
                      outlettype=["", "int", "int"], patching_rect=[x, y, 60, 20])
    device.add_line(source, source_outlet, f"{p}_chg", 0)
    device.add_line(f"{p}_chg", 0, target, target_inlet)
    return stage_result({"change": f"{p}_chg"}, name="dedupe_value")


def control_smooth(device, prefix, dial_id, scale_text, x, *, y=360, ramp_ms=20):
    """Smooth a control dial into a signal: ``dial -> [scale expr] -> pack f
    <ramp_ms> -> line~``. Optional ``scale_text`` is a ``expr``/``scale`` object
    text inserted between the dial and the pack (pass None to skip). Returns the
    ``line~`` id (feed it into your DSP). Was hand-wired identically across
    several audio-effect devices.
    """
    pk, ln = f"{prefix}_pk", f"{prefix}_ln"
    if scale_text is not None:
        sc = f"{prefix}_scale"
        device.add_newobj(sc, scale_text, numinlets=6, numoutlets=1,
                          outlettype=[""], patching_rect=[x, y, 130, 20])
        device.add_line(dial_id, 0, sc, 0)
        src = sc
    else:
        src = dial_id
    device.add_newobj(pk, f"pack f {ramp_ms}", numinlets=2, numoutlets=1,
                      outlettype=[""], patching_rect=[x, y + 25, 70, 20])
    device.add_newobj(ln, "line~", numinlets=2, numoutlets=2,
                      outlettype=["signal", "bang"], patching_rect=[x, y + 50, 40, 20])
    device.add_line(src, 0, pk, 0)
    device.add_line(pk, 0, ln, 0)
    return ln


def init_prime(device, id_prefix, target, value, *, target_inlet=0, x=0, y=0):
    """Give a message-driven inlet a fail-open default: ``loadmess <value>`` into
    the inlet, so it is not cold (silence-producing) before its first real value.
    Returns ids ``{loadmess}``.
    """
    p = id_prefix
    device.add_newobj(f"{p}_prime", f"loadmess {value}", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[x, y, 90, 20])
    device.add_line(f"{p}_prime", 0, target, target_inlet)
    return stage_result({"loadmess": f"{p}_prime"}, name="init_prime")


def corr_readout(device, id_prefix, source, target, *, source_outlet=0,
                 target_inlet=0, x=0, y=0):
    """Sample a signal into a live ``"CORR x.xx"`` text readout: ``snapshot~ 50
    -> sprintf CORR %.2f -> prepend set -> target``. ``target`` is the
    PRE-EXISTING readout box (a comment/textedit already showing placeholder
    text like ``"CORR 1.00"``) — this only wires the sampling chain into it.
    Was hand-wired identically for stereo-correlation meters across several
    devices. Returns ids ``{snap, fmt, set}``.
    """
    p = id_prefix
    device.add_newobj(f"{p}_snap", "snapshot~ 50", numinlets=2, numoutlets=1,
                      outlettype=["float"], patching_rect=[x, y, 80, 20])
    device.add_newobj(f"{p}_fmt", "sprintf CORR %.2f", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[x, y + 30, 130, 20])
    device.add_newobj(f"{p}_set", "prepend set", numinlets=1, numoutlets=1,
                      outlettype=[""], patching_rect=[x, y + 60, 90, 20])
    device.add_line(source, source_outlet, f"{p}_snap", 0)
    device.add_line(f"{p}_snap", 0, f"{p}_fmt", 0)
    device.add_line(f"{p}_fmt", 0, f"{p}_set", 0)
    device.add_line(f"{p}_set", 0, target, target_inlet)
    return stage_result({"snap": f"{p}_snap", "fmt": f"{p}_fmt", "set": f"{p}_set"},
                        name="corr_readout")


def assign_parameter_banks(device, banks):
    """Assign every parameter to a NAMED Push/controller bank, 8 slots each, in
    the given order — without this, Live auto-banks in creation order (8 per
    UNNAMED bank), scattering related controls across banks. ``banks`` is an
    ordered list of ``(bank_name, param_names)`` pairs; each bank's slot index
    is a parameter's position within its ``param_names``. Was hand-wired as an
    identical nested loop across several devices.
    """
    for bank_index, (bank_name, param_names) in enumerate(banks):
        for slot_index, param_name in enumerate(param_names):
            device.assign_parameter_bank(param_name, bank_index, slot_index,
                                         bank_name=bank_name)
