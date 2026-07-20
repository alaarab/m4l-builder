"""Matcher predicates for the legacy-device reverse tool.

Extracted from _reverse_legacy.py (god-file split); re-exported by it."""
from __future__ import annotations

import copy
import os
import pprint
import re
from pathlib import Path
from typing import Any

from ._reverse_constants import *  # noqa: F401,F403
from ._reverse_helpers import *  # noqa: F401,F403
from .constants import AMXD_TYPE, AUDIO_EFFECT, INSTRUMENT, MIDI_EFFECT
from .device import Device
from .live_api import (
    device_active_state,
    live_object_path,
    live_observer,
    live_parameter_probe,
    live_set_control,
    live_state_observer,
    live_thisdevice,
)
from .recipes import (
    dry_wet_stage,
    gain_controlled_stage,
    midi_note_gate,
    tempo_synced_delay,
    transport_sync_lfo_recipe,
)


def _match_param_smooth(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> dict | None:
    pack_id = f"{prefix}_pack"
    line_id = f"{prefix}_line"
    pack = boxes_by_id.get(pack_id)
    line = boxes_by_id.get(line_id)
    if not pack or not line:
        return None

    pack_text = str(pack.get("text", ""))
    smooth_ms = _text_float(pack_text, "pack f ")
    if smooth_ms is None or line.get("text") != "line~":
        return None

    required_line = _line_key(pack_id, 0, line_id, 0)
    if required_line not in line_keys:
        return None

    helper = None
    if _rect_matches(pack, [30, 120, 80, 20]) and _rect_matches(line, [30, 150, 40, 20]):
        helper_kwargs = {}
        if float(smooth_ms) != 20.0:
            helper_kwargs["smooth_ms"] = _normalize_number(float(smooth_ms))
        helper = {
            "name": "param_smooth",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="param_smooth",
        prefix=prefix,
        box_ids=[pack_id, line_id],
        line_keys=[required_line],
        params={"smooth_ms": _normalize_number(float(smooth_ms))},
        helper=helper,
    )


def _match_delay_line(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> dict | None:
    tapin_id = f"{prefix}_tapin"
    tapout_id = f"{prefix}_tapout"
    tapin = boxes_by_id.get(tapin_id)
    tapout = boxes_by_id.get(tapout_id)
    if not tapin or not tapout:
        return None

    max_delay_tapin = _text_int(str(tapin.get("text", "")), "tapin~ ")
    max_delay_tapout = _text_int(str(tapout.get("text", "")), "tapout~ ")
    if max_delay_tapin is None or max_delay_tapout is None or max_delay_tapin != max_delay_tapout:
        return None

    required_line = _line_key(tapin_id, 0, tapout_id, 0)
    if required_line not in line_keys:
        return None

    helper = None
    if _rect_matches(tapin, [30, 120, 100, 20]) and _rect_matches(tapout, [30, 150, 100, 20]):
        helper_kwargs = {}
        if max_delay_tapin != 5000:
            helper_kwargs["max_delay_ms"] = max_delay_tapin
        helper = {
            "name": "delay_line",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="delay_line",
        prefix=prefix,
        box_ids=[tapin_id, tapout_id],
        line_keys=[required_line],
        params={"max_delay_ms": max_delay_tapin},
        helper=helper,
    )


def _match_gain_stage(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> dict | None:
    left_id = f"{prefix}_l"
    right_id = f"{prefix}_r"
    left = boxes_by_id.get(left_id)
    right = boxes_by_id.get(right_id)
    if not left or not right:
        return None
    if left.get("text") != "*~ 1." or right.get("text") != "*~ 1.":
        return None

    helper_kwargs = {}
    if not _rect_matches(left, [30, 120, 40, 20]):
        helper_kwargs["patching_rect_l"] = copy.deepcopy(left.get("patching_rect"))
    if not _rect_matches(right, [150, 120, 40, 20]):
        helper_kwargs["patching_rect_r"] = copy.deepcopy(right.get("patching_rect"))

    return _pattern_match(
        kind="gain_stage",
        prefix=prefix,
        box_ids=[left_id, right_id],
        line_keys=[],
        helper={
            "name": "gain_stage",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        },
    )


def _match_dc_block(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> dict | None:
    left_id = f"{prefix}_l"
    right_id = f"{prefix}_r"
    left = boxes_by_id.get(left_id)
    right = boxes_by_id.get(right_id)
    if not left or not right:
        return None

    dc_text = "biquad~ 1. -1. 0. -0.9997 0."
    if left.get("text") != dc_text or right.get("text") != dc_text:
        return None

    helper = None
    if _rect_matches(left, [30, 120, 180, 20]) and _rect_matches(right, [220, 120, 180, 20]):
        helper = {
            "name": "dc_block",
            "positional": [prefix],
            "kwargs": {},
        }

    return _pattern_match(
        kind="dc_block",
        prefix=prefix,
        box_ids=[left_id, right_id],
        line_keys=[],
        helper=helper,
    )


def _match_saturation(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> dict | None:
    left_id = f"{prefix}_l"
    right_id = f"{prefix}_r"
    left = boxes_by_id.get(left_id)
    right = boxes_by_id.get(right_id)
    if not left or not right:
        return None

    mode_by_text = {
        "tanh~": "tanh",
        "overdrive~": "overdrive",
        "clip~ -1. 1.": "clip",
        "degrade~": "degrade",
    }
    mode = mode_by_text.get(str(left.get("text", "")))
    if mode is None or right.get("text") != left.get("text"):
        return None

    helper = None
    if _rect_matches(left, [30, 120, 80, 20]) and _rect_matches(right, [150, 120, 80, 20]):
        helper_kwargs = {}
        if mode != "tanh":
            helper_kwargs["mode"] = mode
        helper = {
            "name": "saturation",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="saturation",
        prefix=prefix,
        box_ids=[left_id, right_id],
        line_keys=[],
        params={"mode": mode},
        helper=helper,
    )


def _match_selector(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> dict | None:
    box = boxes_by_id.get(prefix)
    if not box:
        return None

    match = re.match(r"^selector~ (\d+) (\d+)$", str(box.get("text", "")))
    if not match:
        return None

    num_inputs = int(match.group(1))
    initial = int(match.group(2))
    helper = None
    if _rect_matches(box, [30, 120, 100, 20]):
        helper_kwargs = {}
        if num_inputs != 2:
            helper_kwargs["num_inputs"] = num_inputs
        if initial != 1:
            helper_kwargs["initial"] = initial
        helper = {
            "name": "selector",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="selector",
        prefix=prefix,
        box_ids=[prefix],
        line_keys=[],
        params={"num_inputs": num_inputs, "initial": initial},
        helper=helper,
    )


def _match_onepole_filter(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> dict | None:
    left_id = f"{prefix}_l"
    right_id = f"{prefix}_r"
    left = boxes_by_id.get(left_id)
    right = boxes_by_id.get(right_id)
    if not left or not right:
        return None

    freq_l = _text_float(str(left.get("text", "")), "onepole~ ")
    freq_r = _text_float(str(right.get("text", "")), "onepole~ ")
    if freq_l is None or freq_r is None or float(freq_l) != float(freq_r):
        return None

    helper = None
    if _rect_matches(left, [30, 120, 80, 20]) and _rect_matches(right, [150, 120, 80, 20]):
        helper_kwargs = {}
        if float(freq_l) != 1000.0:
            helper_kwargs["freq"] = _normalize_number(float(freq_l))
        helper = {
            "name": "onepole_filter",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="onepole_filter",
        prefix=prefix,
        box_ids=[left_id, right_id],
        line_keys=[],
        params={"freq": _normalize_number(float(freq_l))},
        helper=helper,
    )


def _match_svf_filter(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> dict | None:
    left_id = f"{prefix}_l"
    right_id = f"{prefix}_r"
    out_left_id = f"{prefix}_out_l"
    out_right_id = f"{prefix}_out_r"
    left = boxes_by_id.get(left_id)
    right = boxes_by_id.get(right_id)
    out_left = boxes_by_id.get(out_left_id)
    out_right = boxes_by_id.get(out_right_id)
    if not all((left, right, out_left, out_right)):
        return None

    if left.get("text") != "svf~" or right.get("text") != "svf~":
        return None
    if out_left.get("text") != "*~ 1." or out_right.get("text") != "*~ 1.":
        return None

    for outlet, kind in ((0, "lowpass_filter"), (1, "highpass_filter"), (2, "bandpass_filter")):
        required_lines = [
            _line_key(left_id, outlet, out_left_id, 0),
            _line_key(right_id, outlet, out_right_id, 0),
        ]
        if not all(line in line_keys for line in required_lines):
            continue

        helper = None
        if (
            _rect_matches(left, [30, 120, 40, 20])
            and _rect_matches(right, [150, 120, 40, 20])
            and _rect_matches(out_left, [30, 150, 40, 20])
            and _rect_matches(out_right, [150, 150, 40, 20])
        ):
            helper = {
                "name": kind,
                "positional": [prefix],
                "kwargs": {},
            }

        return _pattern_match(
            kind=kind,
            prefix=prefix,
            box_ids=[left_id, right_id, out_left_id, out_right_id],
            line_keys=required_lines,
            helper=helper,
        )

    return None


def _match_lfo(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> dict | None:
    osc_id = f"{prefix}_osc"
    depth_id = f"{prefix}_depth"
    osc = boxes_by_id.get(osc_id)
    depth = boxes_by_id.get(depth_id)
    if not osc or not depth or depth.get("text") != "*~ 1.":
        return None

    osc_text = str(osc.get("text", ""))
    required_boxes = [osc_id, depth_id]
    required_lines = []
    waveform = None
    helperizable = False

    if osc_text == "phasor~":
        waveform = "saw"
        required_lines = [_line_key(osc_id, 0, depth_id, 0)]
        helperizable = (
            _rect_matches(osc, [30, 120, 60, 20])
            and _rect_matches(depth, [30, 210, 40, 20])
        )
    elif osc_text in {"cycle~", "rect~", "tri~"}:
        scale_id = f"{prefix}_scale"
        offset_id = f"{prefix}_offset"
        scale = boxes_by_id.get(scale_id)
        offset = boxes_by_id.get(offset_id)
        if not scale or not offset:
            return None
        if scale.get("text") != "*~ 0.5" or offset.get("text") != "+~ 0.5":
            return None
        waveform = {
            "cycle~": "sine",
            "rect~": "square",
            "tri~": "triangle",
        }[osc_text]
        required_boxes = [osc_id, scale_id, offset_id, depth_id]
        required_lines = [
            _line_key(osc_id, 0, scale_id, 0),
            _line_key(scale_id, 0, offset_id, 0),
            _line_key(offset_id, 0, depth_id, 0),
        ]
        helperizable = (
            _rect_matches(depth, [30, 210, 40, 20])
            and _rect_matches(scale, [30, 150, 50, 20])
            and _rect_matches(offset, [30, 180, 50, 20])
            and (
                (osc_text == "cycle~" and _rect_matches(osc, [30, 120, 50, 20]))
                or (osc_text == "rect~" and _rect_matches(osc, [30, 120, 50, 20]))
                or (osc_text == "tri~" and _rect_matches(osc, [30, 120, 50, 20]))
            )
        )
    else:
        return None

    if not all(line in line_keys for line in required_lines):
        return None

    helper = None
    if helperizable:
        helper_kwargs = {}
        if waveform != "sine":
            helper_kwargs["waveform"] = waveform
        helper = {
            "name": "lfo",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="lfo",
        prefix=prefix,
        box_ids=required_boxes,
        line_keys=required_lines,
        params={"waveform": waveform},
        helper=helper,
    )


def _match_transport_lfo(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> dict | None:
    poll_id = f"{prefix}_poll"
    transport_id = f"{prefix}_transport"
    bpm_id = f"{prefix}_bpm"
    rate_id = f"{prefix}_rate"
    osc_id = f"{prefix}_osc"
    poll = boxes_by_id.get(poll_id)
    transport = boxes_by_id.get(transport_id)
    bpm = boxes_by_id.get(bpm_id)
    rate = boxes_by_id.get(rate_id)
    osc = boxes_by_id.get(osc_id)
    if not all((poll, transport, bpm, rate, osc)):
        return None

    if poll.get("text") != "metro 100 @active 1":
        return None
    if transport.get("text") != "transport" or bpm.get("text") != "f":
        return None

    division = _transport_lfo_division_from_text(str(rate.get("text", "")))
    if division is None:
        return None

    shape_map = {
        "cycle~": "sine",
        "phasor~": "saw",
        "rect~": "square",
    }
    shape = shape_map.get(osc.get("text"))
    if shape is None:
        return None

    required_lines = [
        _line_key(poll_id, 0, transport_id, 0),
        _line_key(transport_id, 4, bpm_id, 0),
        _line_key(bpm_id, 0, rate_id, 0),
        _line_key(rate_id, 0, osc_id, 0),
    ]
    if not _line_keys_present(line_keys, required_lines):
        return None

    helper = None
    if (
        _rect_matches(poll, [30, 30, 110, 20])
        and _rect_matches(transport, [30, 60, 70, 20])
        and _rect_matches(bpm, [30, 90, 30, 20])
        and _rect_matches(rate, [30, 120, 160, 20])
        and _rect_matches(osc, [30, 160, 60, 20])
    ):
        helper_kwargs = {}
        if division != "1/4":
            helper_kwargs["division"] = division
        if shape != "sine":
            helper_kwargs["shape"] = shape
        helper = {
            "name": "transport_lfo",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="transport_lfo",
        prefix=prefix,
        box_ids=[poll_id, transport_id, bpm_id, rate_id, osc_id],
        line_keys=required_lines,
        params={
            "division": division,
            "shape": shape,
        },
        helper=helper,
    )


def _match_ms_encode_decode(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> dict | None:
    specs = {
        f"{prefix}_enc_add": "+~",
        f"{prefix}_enc_sub": "-~",
        f"{prefix}_enc_mid": "*~ 0.5",
        f"{prefix}_enc_side": "*~ 0.5",
        f"{prefix}_dec_add": "+~",
        f"{prefix}_dec_sub": "-~",
    }
    boxes = {}
    for box_id, text in specs.items():
        box = boxes_by_id.get(box_id)
        if not box or box.get("text") != text:
            return None
        boxes[box_id] = box

    required_lines = [
        _line_key(f"{prefix}_enc_add", 0, f"{prefix}_enc_mid", 0),
        _line_key(f"{prefix}_enc_sub", 0, f"{prefix}_enc_side", 0),
    ]
    if not all(line in line_keys for line in required_lines):
        return None

    helper = None
    if (
        _rect_matches(boxes[f"{prefix}_enc_add"], [300, 60, 30, 20])
        and _rect_matches(boxes[f"{prefix}_enc_sub"], [340, 60, 30, 20])
        and _rect_matches(boxes[f"{prefix}_enc_mid"], [300, 90, 45, 20])
        and _rect_matches(boxes[f"{prefix}_enc_side"], [340, 90, 45, 20])
        and _rect_matches(boxes[f"{prefix}_dec_add"], [300, 160, 30, 20])
        and _rect_matches(boxes[f"{prefix}_dec_sub"], [340, 160, 30, 20])
    ):
        helper = {
            "name": "ms_encode_decode",
            "positional": [prefix],
            "kwargs": {},
        }

    return _pattern_match(
        kind="ms_encode_decode",
        prefix=prefix,
        box_ids=list(specs),
        line_keys=required_lines,
        helper=helper,
    )


def _match_feedback_delay(prefix: str, boxes_by_id: dict, line_keys: set[tuple]) -> dict | None:
    sum_id = f"{prefix}_sum"
    tapin_id = f"{prefix}_tapin"
    tapout_id = f"{prefix}_tapout"
    sat_id = f"{prefix}_sat"
    lp_id = f"{prefix}_lp"
    fb_id = f"{prefix}_fb"

    boxes = {
        sum_id: boxes_by_id.get(sum_id),
        tapin_id: boxes_by_id.get(tapin_id),
        tapout_id: boxes_by_id.get(tapout_id),
        sat_id: boxes_by_id.get(sat_id),
        lp_id: boxes_by_id.get(lp_id),
        fb_id: boxes_by_id.get(fb_id),
    }
    if not all(boxes.values()):
        return None

    max_delay_tapin = _text_int(str(boxes[tapin_id].get("text", "")), "tapin~ ")
    max_delay_tapout = _text_int(str(boxes[tapout_id].get("text", "")), "tapout~ ")
    lp_freq = _text_float(str(boxes[lp_id].get("text", "")), "onepole~ ")
    fb_amount = _text_float(str(boxes[fb_id].get("text", "")), "*~ ")
    if (
        boxes[sum_id].get("text") != "+~"
        or max_delay_tapin is None
        or max_delay_tapout is None
        or max_delay_tapin != max_delay_tapout
        or boxes[sat_id].get("text") != "tanh~"
        or lp_freq is None
        or fb_amount is None
    ):
        return None

    required_lines = [
        _line_key(sum_id, 0, tapin_id, 0),
        _line_key(tapin_id, 0, tapout_id, 0),
        _line_key(tapout_id, 0, sat_id, 0),
        _line_key(sat_id, 0, lp_id, 0),
        _line_key(lp_id, 0, fb_id, 0),
        _line_key(fb_id, 0, sum_id, 1),
    ]
    if not all(line in line_keys for line in required_lines):
        return None

    helper = None
    if (
        float(lp_freq) == 3000.0
        and float(fb_amount) == 0.5
        and _rect_matches(boxes[sum_id], [30, 120, 30, 20])
        and _rect_matches(boxes[tapin_id], [30, 150, 100, 20])
        and _rect_matches(boxes[tapout_id], [30, 180, 100, 20])
        and _rect_matches(boxes[sat_id], [30, 210, 45, 20])
        and _rect_matches(boxes[lp_id], [30, 240, 90, 20])
        and _rect_matches(boxes[fb_id], [30, 270, 50, 20])
    ):
        helper_kwargs = {}
        if max_delay_tapin != 5000:
            helper_kwargs["max_delay_ms"] = max_delay_tapin
        helper = {
            "name": "feedback_delay",
            "positional": [prefix],
            "kwargs": helper_kwargs,
        }

    return _pattern_match(
        kind="feedback_delay",
        prefix=prefix,
        box_ids=[sum_id, tapin_id, tapout_id, sat_id, lp_id, fb_id],
        line_keys=required_lines,
        params={
            "max_delay_ms": max_delay_tapin,
            "lp_freq": _normalize_number(float(lp_freq)),
            "feedback_amount": _normalize_number(float(fb_amount)),
        },
        helper=helper,
    )


def _match_gain_controlled_recipe(
    prefix: str,
    boxes_by_id: dict[str, dict],
    line_keys: set[tuple],
    pattern_index: dict[tuple[str, str], dict],
) -> dict | None:
    dial_id = f"{prefix}_dial"
    dbtoa_id = f"{prefix}_dbtoa"
    gain_id = f"{prefix}_gain"
    dial = boxes_by_id.get(dial_id)
    dbtoa = boxes_by_id.get(dbtoa_id)
    gain = boxes_by_id.get(gain_id)
    smooth = pattern_index.get(("param_smooth", f"{prefix}_smooth"))
    if not all((dial, dbtoa, gain, smooth)):
        return None

    if not _box_parameter_matches(
        dial,
        maxclass="live.dial",
        varname=f"{prefix}_gain",
        min_val=-70.0,
        max_val=6.0,
        initial=0.0,
        unitstyle=4,
        annotation_name=f"{prefix} Gain",
    ):
        return None
    if dbtoa.get("text") != "dbtoa" or gain.get("text") != "*~ 1.":
        return None

    extra_lines = [
        _line_key(dial_id, 0, dbtoa_id, 0),
        _line_key(dbtoa_id, 0, f"{prefix}_smooth_pack", 0),
        _line_key(f"{prefix}_smooth_line", 0, gain_id, 1),
    ]
    required_line_keys = list(smooth["line_keys"]) + extra_lines
    if not _line_keys_present(line_keys, required_line_keys):
        return None

    dial_rect = copy.deepcopy(dial.get("presentation_rect") or dial.get("patching_rect"))
    dbtoa_rect = copy.deepcopy(dbtoa.get("patching_rect"))
    x = y = None
    if dbtoa_rect and len(dbtoa_rect) == 4:
        x = _normalize_number(float(dbtoa_rect[0]))
        y = _normalize_number(float(dbtoa_rect[1]))

    recipe = None
    if dial_rect is not None and x is not None and y is not None:
        recipe_kwargs = {}
        if x != 30:
            recipe_kwargs["x"] = x
        if y != 30:
            recipe_kwargs["y"] = y
        if _recipeizable_subset_matches(
            recipe_name="gain_controlled_stage",
            prefix=prefix,
            positional=[dial_rect],
            kwargs=recipe_kwargs,
            boxes_by_id=boxes_by_id,
            line_keys=line_keys,
        ):
            recipe = {
                "name": "gain_controlled_stage",
                "positional": [prefix, dial_rect],
                "kwargs": recipe_kwargs,
            }

    return _recipe_match(
        kind="gain_controlled_stage",
        prefix=prefix,
        box_ids=[dial_id, dbtoa_id, gain_id, *smooth["box_ids"]],
        line_keys=required_line_keys,
        params={
            "dial_rect": dial_rect,
            "x": x,
            "y": y,
        },
        recipe=recipe,
    )


def _match_dry_wet_recipe(
    prefix: str,
    boxes_by_id: dict[str, dict],
    line_keys: set[tuple],
    pattern_index: dict[tuple[str, str], dict],
) -> dict | None:
    dial_id = f"{prefix}_dial"
    scale_id = f"{prefix}_scale"
    trig_id = f"{prefix}_trig"
    inv_id = f"{prefix}_inv"
    wet_gain_id = f"{prefix}_wet_gain"
    dry_gain_id = f"{prefix}_dry_gain"
    dial = boxes_by_id.get(dial_id)
    scale = boxes_by_id.get(scale_id)
    trig = boxes_by_id.get(trig_id)
    inv = boxes_by_id.get(inv_id)
    wet_gain = boxes_by_id.get(wet_gain_id)
    dry_gain = boxes_by_id.get(dry_gain_id)
    wet_smooth = pattern_index.get(("param_smooth", f"{prefix}_wet_smooth"))
    dry_smooth = pattern_index.get(("param_smooth", f"{prefix}_dry_smooth"))
    if not all((dial, scale, trig, inv, wet_gain, dry_gain, wet_smooth, dry_smooth)):
        return None

    if not _box_parameter_matches(
        dial,
        maxclass="live.dial",
        varname=f"{prefix}_mix",
        min_val=0.0,
        max_val=100.0,
        initial=50.0,
        unitstyle=5,
        annotation_name=f"{prefix} Dry/Wet",
    ):
        return None
    if (
        scale.get("text") != "*~ 0.01"
        or trig.get("text") != "t f f"
        or inv.get("text") != "!-~ 1."
        or wet_gain.get("text") != "*~ 0."
        or dry_gain.get("text") != "*~ 1."
    ):
        return None

    extra_lines = [
        _line_key(dial_id, 0, trig_id, 0),
        _line_key(trig_id, 0, f"{prefix}_wet_smooth_pack", 0),
        _line_key(f"{prefix}_wet_smooth_line", 0, wet_gain_id, 1),
        _line_key(trig_id, 1, inv_id, 0),
        _line_key(inv_id, 0, f"{prefix}_dry_smooth_pack", 0),
        _line_key(f"{prefix}_dry_smooth_line", 0, dry_gain_id, 1),
    ]
    required_line_keys = list(wet_smooth["line_keys"]) + list(dry_smooth["line_keys"]) + extra_lines
    if not _line_keys_present(line_keys, required_line_keys):
        return None

    dial_rect = copy.deepcopy(dial.get("presentation_rect") or dial.get("patching_rect"))
    scale_rect = copy.deepcopy(scale.get("patching_rect"))
    x = y = None
    if scale_rect and len(scale_rect) == 4:
        x = _normalize_number(float(scale_rect[0]))
        y = _normalize_number(float(scale_rect[1]))

    recipe = None
    if dial_rect is not None and x is not None and y is not None:
        recipe_kwargs = {}
        if x != 30:
            recipe_kwargs["x"] = x
        if y != 30:
            recipe_kwargs["y"] = y
        if _recipeizable_subset_matches(
            recipe_name="dry_wet_stage",
            prefix=prefix,
            positional=[dial_rect],
            kwargs=recipe_kwargs,
            boxes_by_id=boxes_by_id,
            line_keys=line_keys,
        ):
            recipe = {
                "name": "dry_wet_stage",
                "positional": [prefix, dial_rect],
                "kwargs": recipe_kwargs,
            }

    return _recipe_match(
        kind="dry_wet_stage",
        prefix=prefix,
        box_ids=[dial_id, scale_id, trig_id, inv_id, wet_gain_id, dry_gain_id, *wet_smooth["box_ids"], *dry_smooth["box_ids"]],
        line_keys=required_line_keys,
        params={
            "dial_rect": dial_rect,
            "x": x,
            "y": y,
        },
        recipe=recipe,
    )


def _match_tempo_synced_delay_recipe(
    prefix: str,
    boxes_by_id: dict[str, dict],
    line_keys: set[tuple],
    pattern_index: dict[tuple[str, str], dict],
) -> dict | None:
    time_dial_id = f"{prefix}_time_dial"
    fb_dial_id = f"{prefix}_fb_dial"
    transport_id = f"{prefix}_transport"
    loadbang_id = f"{prefix}_loadbang"
    fb_scale_id = f"{prefix}_fb_scale"
    fb_mul_id = f"{prefix}_fb_mul"
    sum_id = f"{prefix}_sum"
    time_dial = boxes_by_id.get(time_dial_id)
    fb_dial = boxes_by_id.get(fb_dial_id)
    transport = boxes_by_id.get(transport_id)
    loadbang = boxes_by_id.get(loadbang_id)
    fb_scale = boxes_by_id.get(fb_scale_id)
    fb_mul = boxes_by_id.get(fb_mul_id)
    total_sum = boxes_by_id.get(sum_id)
    delay = pattern_index.get(("delay_line", f"{prefix}_delay"))
    time_smooth = pattern_index.get(("param_smooth", f"{prefix}_time_smooth"))
    fb_smooth = pattern_index.get(("param_smooth", f"{prefix}_fb_smooth"))
    if not all((time_dial, fb_dial, transport, loadbang, fb_scale, fb_mul, total_sum, delay, time_smooth, fb_smooth)):
        return None

    if not _box_parameter_matches(
        time_dial,
        maxclass="live.dial",
        varname=f"{prefix}_time",
        min_val=1.0,
        max_val=5000.0,
        initial=375.0,
        unitstyle=2,
        annotation_name=f"{prefix} Delay Time",
    ):
        return None
    if not _box_parameter_matches(
        fb_dial,
        maxclass="live.dial",
        varname=f"{prefix}_feedback",
        min_val=0.0,
        max_val=95.0,
        initial=40.0,
        unitstyle=5,
        annotation_name=f"{prefix} Feedback",
    ):
        return None
    if (
        transport.get("text") != "transport"
        or loadbang.get("text") != "loadbang"
        or fb_scale.get("text") != "scale 0. 95. 0. 0.95"
        or fb_mul.get("text") != "*~ 0."
        or total_sum.get("text") != "+~"
    ):
        return None

    extra_lines = [
        _line_key(time_dial_id, 0, f"{prefix}_time_smooth_pack", 0),
        _line_key(f"{prefix}_time_smooth_line", 0, f"{prefix}_delay_tapout", 1),
        _line_key(fb_dial_id, 0, fb_scale_id, 0),
        _line_key(fb_scale_id, 0, f"{prefix}_fb_smooth_pack", 0),
        _line_key(f"{prefix}_fb_smooth_line", 0, fb_mul_id, 1),
        _line_key(f"{prefix}_delay_tapout", 0, fb_mul_id, 0),
        _line_key(fb_mul_id, 0, sum_id, 1),
        _line_key(sum_id, 0, f"{prefix}_delay_tapin", 0),
        _line_key(loadbang_id, 0, transport_id, 0),
    ]
    required_line_keys = list(delay["line_keys"]) + list(time_smooth["line_keys"]) + list(fb_smooth["line_keys"]) + extra_lines
    if not _line_keys_present(line_keys, required_line_keys):
        return None

    time_dial_rect = copy.deepcopy(time_dial.get("presentation_rect") or time_dial.get("patching_rect"))
    fb_dial_rect = copy.deepcopy(fb_dial.get("presentation_rect") or fb_dial.get("patching_rect"))
    fb_mul_rect = copy.deepcopy(fb_mul.get("patching_rect"))
    transport_rect = copy.deepcopy(transport.get("patching_rect"))
    x = y = None
    if fb_mul_rect and transport_rect and len(fb_mul_rect) == 4 and len(transport_rect) == 4:
        x = _normalize_number(float(fb_mul_rect[0]))
        y = _normalize_number(float(transport_rect[1]))

    recipe = None
    if time_dial_rect is not None and fb_dial_rect is not None and x is not None and y is not None:
        recipe_kwargs = {}
        if x != 30:
            recipe_kwargs["x"] = x
        if y != 30:
            recipe_kwargs["y"] = y
        if _recipeizable_subset_matches(
            recipe_name="tempo_synced_delay",
            prefix=prefix,
            positional=[time_dial_rect, fb_dial_rect],
            kwargs=recipe_kwargs,
            boxes_by_id=boxes_by_id,
            line_keys=line_keys,
        ):
            recipe = {
                "name": "tempo_synced_delay",
                "positional": [prefix, time_dial_rect, fb_dial_rect],
                "kwargs": recipe_kwargs,
            }

    return _recipe_match(
        kind="tempo_synced_delay",
        prefix=prefix,
        box_ids=[
            time_dial_id,
            fb_dial_id,
            transport_id,
            loadbang_id,
            fb_scale_id,
            fb_mul_id,
            sum_id,
            *delay["box_ids"],
            *time_smooth["box_ids"],
            *fb_smooth["box_ids"],
        ],
        line_keys=required_line_keys,
        params={
            "time_dial_rect": time_dial_rect,
            "feedback_dial_rect": fb_dial_rect,
            "x": x,
            "y": y,
        },
        recipe=recipe,
    )


def _match_midi_note_gate_recipe(
    prefix: str,
    boxes_by_id: dict[str, dict],
    line_keys: set[tuple],
    pattern_index: dict[tuple[str, str], dict],
) -> dict | None:
    del pattern_index

    notein_id = f"{prefix}_notein"
    stripnote_id = f"{prefix}_stripnote"
    kslider_id = f"{prefix}_kslider"
    notein = boxes_by_id.get(notein_id)
    stripnote = boxes_by_id.get(stripnote_id)
    kslider = boxes_by_id.get(kslider_id)
    if not all((notein, stripnote, kslider)):
        return None

    notein_text = str(notein.get("text", ""))
    if notein_text not in {"notein", "notein 0"}:
        if not notein_text.startswith("notein "):
            return None
    if stripnote.get("text") != "stripnote" or kslider.get("maxclass") != "kslider":
        return None

    required_line_keys = [
        _line_key(notein_id, 0, stripnote_id, 0),
        _line_key(notein_id, 1, stripnote_id, 1),
        _line_key(stripnote_id, 0, kslider_id, 0),
    ]
    if not _line_keys_present(line_keys, required_line_keys):
        return None

    stripnote_rect = copy.deepcopy(stripnote.get("patching_rect"))
    kslider_rect = copy.deepcopy(kslider.get("presentation_rect") or kslider.get("patching_rect"))
    x = y = None
    if stripnote_rect and len(stripnote_rect) == 4:
        x = _normalize_number(float(stripnote_rect[0]))
        y = _normalize_number(float(stripnote_rect[1]) - 30.0)

    notein_channel = 0
    if notein_text not in {"notein", "notein 0"}:
        match = re.fullmatch(r"notein\s+(\d+)", notein_text)
        if match is None:
            return None
        notein_channel = int(match.group(1))

    recipe = None
    if kslider_rect is not None and x is not None and y is not None and notein_channel == 0:
        recipe_kwargs = {}
        if x != 30:
            recipe_kwargs["x"] = x
        if y != 30:
            recipe_kwargs["y"] = y
        if _recipeizable_subset_matches(
            recipe_name="midi_note_gate",
            prefix=prefix,
            positional=[],
            kwargs=recipe_kwargs,
            boxes_by_id=boxes_by_id,
            line_keys=line_keys,
        ):
            recipe = {
                "name": "midi_note_gate",
                "positional": [prefix],
                "kwargs": recipe_kwargs,
            }

    return _recipe_match(
        kind="midi_note_gate",
        prefix=prefix,
        box_ids=[notein_id, stripnote_id, kslider_id],
        line_keys=required_line_keys,
        params={
            "channel": notein_channel,
            "x": x,
            "y": y,
            "kslider_rect": kslider_rect,
        },
        recipe=recipe,
    )


def _match_transport_sync_lfo_recipe(
    prefix: str,
    boxes_by_id: dict[str, dict],
    line_keys: set[tuple],
    pattern_index: dict[tuple[str, str], dict],
) -> dict | None:
    depth_dial_id = f"{prefix}_depth_dial"
    depth_mul_id = f"{prefix}_depth_mul"
    menu_id = f"{prefix}_div_menu"
    depth_dial = boxes_by_id.get(depth_dial_id)
    depth_mul = boxes_by_id.get(depth_mul_id)
    menu = boxes_by_id.get(menu_id)
    transport_lfo = pattern_index.get(("transport_lfo", f"{prefix}_lfo"))
    if not all((depth_dial, depth_mul, menu, transport_lfo)):
        return None

    if not _box_parameter_matches(
        depth_dial,
        maxclass="live.dial",
        varname=f"{prefix}_depth",
        min_val=0.0,
        max_val=100.0,
        initial=50.0,
        unitstyle=5,
        annotation_name=f"{prefix} Depth",
    ):
        return None
    if depth_mul.get("text") != "*~ 0.01" or menu.get("maxclass") != "umenu":
        return None
    if menu.get("items") != ["1/4", "1/8", "1/16", "1/32"]:
        return None

    extra_lines = [
        _line_key(depth_dial_id, 0, depth_mul_id, 0),
        _line_key(f"{prefix}_lfo_osc", 0, depth_mul_id, 1),
    ]
    required_line_keys = list(transport_lfo["line_keys"]) + extra_lines
    if not _line_keys_present(line_keys, required_line_keys):
        return None

    depth_rect = copy.deepcopy(depth_dial.get("presentation_rect") or depth_dial.get("patching_rect"))
    mul_rect = copy.deepcopy(depth_mul.get("patching_rect"))
    x = y = None
    if mul_rect and len(mul_rect) == 4:
        x = _normalize_number(float(mul_rect[0]))
        y = _normalize_number(float(mul_rect[1]) - 60.0)

    recipe = None
    lfo_params = transport_lfo.get("params", {})
    if (
        depth_rect is not None
        and x is not None
        and y is not None
        and lfo_params.get("division") == "1/4"
        and lfo_params.get("shape") == "sine"
    ):
        recipe_kwargs = {}
        if x != 30:
            recipe_kwargs["x"] = x
        if y != 30:
            recipe_kwargs["y"] = y
        if _recipeizable_subset_matches(
            recipe_name="transport_sync_lfo_recipe",
            prefix=prefix,
            positional=[],
            kwargs=recipe_kwargs,
            boxes_by_id=boxes_by_id,
            line_keys=line_keys,
        ):
            recipe = {
                "name": "transport_sync_lfo_recipe",
                "positional": [prefix],
                "kwargs": recipe_kwargs,
            }

    return _recipe_match(
        kind="transport_sync_lfo_recipe",
        prefix=prefix,
        box_ids=[depth_dial_id, depth_mul_id, menu_id, *transport_lfo["box_ids"]],
        line_keys=required_line_keys,
        params={
            "division": lfo_params.get("division"),
            "shape": lfo_params.get("shape"),
            "x": x,
            "y": y,
            "depth_rect": depth_rect,
        },
        recipe=recipe,
    )


PATTERN_MATCHERS = [
    ([""], _match_feedback_delay),
    (["_transport", "_bpm", "_rate", "_osc"], _match_transport_lfo),
    (["_osc", "_depth"], _match_lfo),
    (["_enc_add", "_enc_sub", "_enc_mid", "_enc_side", "_dec_add", "_dec_sub"], _match_ms_encode_decode),
    (["_l", "_r", "_out_l", "_out_r"], _match_svf_filter),
    (["_tapin", "_tapout"], _match_delay_line),
    (["_pack", "_line"], _match_param_smooth),
    (["_l", "_r"], _match_dc_block),
    (["_l", "_r"], _match_saturation),
    (["_l", "_r"], _match_onepole_filter),
    (["_l", "_r"], _match_gain_stage),
    ([""], _match_selector),
]

RECIPE_MATCHERS = [
    (["_depth_dial", "_depth_mul", "_div_menu"], _match_transport_sync_lfo_recipe),
    (["_notein", "_stripnote", "_kslider"], _match_midi_note_gate_recipe),
    (["_time_dial", "_fb_dial", "_transport"], _match_tempo_synced_delay_recipe),
    (["_dial", "_scale", "_trig", "_wet_gain", "_dry_gain"], _match_dry_wet_recipe),
    (["_dial", "_dbtoa", "_gain"], _match_gain_controlled_recipe),
]

__all__ = [
    "_match_param_smooth",
    "_match_delay_line",
    "_match_gain_stage",
    "_match_dc_block",
    "_match_saturation",
    "_match_selector",
    "_match_onepole_filter",
    "_match_svf_filter",
    "_match_lfo",
    "_match_transport_lfo",
    "_match_ms_encode_decode",
    "_match_feedback_delay",
    "_match_gain_controlled_recipe",
    "_match_dry_wet_recipe",
    "_match_tempo_synced_delay_recipe",
    "_match_midi_note_gate_recipe",
    "_match_transport_sync_lfo_recipe",
    "PATTERN_MATCHERS",
    "RECIPE_MATCHERS",
]

