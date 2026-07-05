"""Signal and message routing."""

from ..objects import newobj, patchline
from ._common import _nxn_signal_sum, _signal_sum_chain


def selector(id_prefix: str, num_inputs: int, initial: int = 1) -> tuple:
    """Create a selector~ for switching between signal inputs.

    selector~ N initial has N+1 inlets (int selector + N signal inputs).
    selector~ N without an initial arg defaults to input 0 (silence), so always pass initial.
    """
    if initial < 0 or initial > num_inputs:
        raise ValueError(f"selector~ initial {initial} out of range [0, {num_inputs}]")
    boxes = [
        newobj(id_prefix, f"selector~ {num_inputs} {initial}",
               numinlets=num_inputs + 1, numoutlets=1,
               outlettype=["signal"], patching_rect=[30, 120, 100, 20]),
    ]
    return (boxes, [])


def mc_expand(id_prefix: str, channels: int = 8) -> tuple:
    """Expand stereo to N-channel using mc.pack~.

    Wire stereo signals into {prefix}_pack inlet 0 and 1.
    Output MC signal from {prefix}_pack outlet 0.
    """
    if channels < 1:
        raise ValueError(f"mc_expand channels must be >= 1, got {channels}")
    p = id_prefix
    boxes = [
        newobj(f"{p}_pack", f"mc.pack~ {channels}", numinlets=channels,
               numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 120, 80, 20]),
    ]
    return (boxes, [])


def mc_collapse(id_prefix: str, channels: int = 8) -> tuple:
    """Collapse N-channel MC signal to stereo using mc.unpack~ and summing.

    Wire MC signal into {prefix}_unpack inlet 0.
    Output stereo L/R from {prefix}_sum_l / {prefix}_sum_r outlet 0.
    """
    if channels < 1:
        raise ValueError(f"mc_collapse channels must be >= 1, got {channels}")
    p = id_prefix
    boxes = [
        newobj(f"{p}_unpack", f"mc.unpack~ {channels}", numinlets=1,
               numoutlets=channels, outlettype=["signal"] * channels,
               patching_rect=[30, 120, 100, 20]),
    ]
    lines = []

    # Sum even-indexed channels to L, odd to R
    l_channels = list(range(0, channels, 2))
    r_channels = list(range(1, channels, 2))

    for side, ch_list in (("l", l_channels), ("r", r_channels)):
        if len(ch_list) == 1:
            boxes.append(newobj(f"{p}_sum_{side}", "*~ 1.", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[30, 200, 40, 20]))
            lines.append(patchline(f"{p}_unpack", ch_list[0], f"{p}_sum_{side}", 0))
        else:
            # Build a +~ summing chain
            for j, ch in enumerate(ch_list):
                if j == 0:
                    boxes.append(newobj(f"{p}_add_{side}_0", "+~", numinlets=2,
                                        numoutlets=1, outlettype=["signal"],
                                        patching_rect=[30, 200, 30, 20]))
                    lines.append(patchline(f"{p}_unpack", ch_list[0], f"{p}_add_{side}_0", 0))
                    lines.append(patchline(f"{p}_unpack", ch_list[1], f"{p}_add_{side}_0", 1))
                elif j >= 2:
                    adder_id = f"{p}_add_{side}_{j - 1}"
                    boxes.append(newobj(adder_id, "+~", numinlets=2, numoutlets=1,
                                        outlettype=["signal"],
                                        patching_rect=[30, 200 + j * 30, 30, 20]))
                    lines.append(patchline(f"{p}_add_{side}_{j - 2}", 0, adder_id, 0))
                    lines.append(patchline(f"{p}_unpack", ch, adder_id, 1))

            last_adder = f"{p}_add_{side}_{max(len(ch_list) - 2, 0)}"
            boxes.append(newobj(f"{p}_sum_{side}", "*~ 1.", numinlets=2, numoutlets=1,
                                outlettype=["signal"],
                                patching_rect=[30, 300, 40, 20]))
            lines.append(patchline(last_adder, 0, f"{p}_sum_{side}", 0))

    return (boxes, lines)


def xfade_matrix(id_prefix: str, sources: int = 4) -> tuple:
    """N-input crossfade matrix.

    Control (float 0.0 to N-1) sets crossfade position across sources.
    Each source weight = max(0, 1 - abs(control - i)) computed with expr~.
    All weighted sources summed with +~ chain.

    Wire signals into {prefix}_mul_{i} inlet 0 for each source i.
    Wire control float into {prefix}_ctrl inlet 0.
    Output from {prefix}_sum outlet 0.
    """
    if sources < 1:
        raise ValueError(f"xfade_matrix sources must be >= 1, got {sources}")
    p = id_prefix
    boxes = []
    lines = []

    # Control signal input: convert float to signal via sig~... but we must
    # avoid sig~ (cold-start silence). Use pack + line~ for smooth control.
    boxes.append(newobj(f"{p}_ctrl", "pack f 10", numinlets=2, numoutlets=1,
                        outlettype=[""],
                        patching_rect=[30, 60, 80, 20]))
    boxes.append(newobj(f"{p}_ctrl_line", "line~", numinlets=2, numoutlets=1,
                        outlettype=["signal"],
                        patching_rect=[30, 90, 50, 20]))
    lines.append(patchline(f"{p}_ctrl", 0, f"{p}_ctrl_line", 0))

    for i in range(sources):
        # weight = max(0, 1 - abs(ctrl - i))
        boxes.append(newobj(f"{p}_wt_{i}",
                            f"expr~ (1. - fabs($v1 - {float(i)})) > 0. ? "
                            f"(1. - fabs($v1 - {float(i)})) : 0.",
                            numinlets=1, numoutlets=1, outlettype=["signal"],
                            patching_rect=[30 + i * 130, 130, 220, 20]))
        lines.append(patchline(f"{p}_ctrl_line", 0, f"{p}_wt_{i}", 0))

        # multiply source by weight
        boxes.append(newobj(f"{p}_mul_{i}", "*~", numinlets=2, numoutlets=1,
                            outlettype=["signal"],
                            patching_rect=[30 + i * 130, 170, 30, 20]))
        lines.append(patchline(f"{p}_wt_{i}", 0, f"{p}_mul_{i}", 1))

    # Sum all weighted sources
    source_ids = [f"{p}_mul_{i}" for i in range(sources)]
    sum_boxes, sum_lines = _signal_sum_chain(p, source_ids)
    boxes.extend(sum_boxes)
    lines.extend(sum_lines)

    return (boxes, lines)


def matrix_mixer(id_prefix: str, inputs: int = 4, outputs: int = 4) -> tuple:
    """NxN gain routing matrix.

    Creates inputs*outputs *~ gain cells and +~ summing chains per output.
    Wire each input signal into {prefix}_in_{i}_gain_{j} inlet 0.
    Output from {prefix}_out_{j} outlet 0.
    """
    if inputs < 1:
        raise ValueError(f"matrix_mixer inputs must be >= 1, got {inputs}")
    if outputs < 1:
        raise ValueError(f"matrix_mixer outputs must be >= 1, got {outputs}")
    p = id_prefix
    boxes, lines = _nxn_signal_sum(
        p, inputs, outputs,
        cell_fmt=lambda i, j: f"{p}_in_{i}_gain_{j}",
        adder_prefix=f"{p}_add",
        out_fmt=lambda j: f"{p}_out_{j}",
    )
    return (boxes, lines)


def send_signal(id_prefix: str, name: str) -> tuple:
    """Create a send~ object for signal-domain routing without patch cords.

    The signal fed into {prefix}_send inlet 0 is available to any
    matching receive~ with the same name.
    """
    boxes = [
        newobj(f"{id_prefix}_send", f"send~ {name}",
               numinlets=1, numoutlets=0,
               patching_rect=[30, 30, 100, 20]),
    ]
    return (boxes, [])


def receive_signal(id_prefix: str, name: str) -> tuple:
    """Create a receive~ object for signal-domain routing without patch cords.

    Output the named signal from {prefix}_receive outlet 0.
    """
    boxes = [
        newobj(f"{id_prefix}_receive", f"receive~ {name}",
               numinlets=0, numoutlets=1, outlettype=["signal"],
               patching_rect=[30, 30, 100, 20]),
    ]
    return (boxes, [])


def send_msg(id_prefix: str, name: str) -> tuple:
    """Create a send object for message-domain routing without patch cords.

    Messages sent to {prefix}_send inlet 0 are available to any
    matching receive with the same name.
    """
    boxes = [
        newobj(f"{id_prefix}_send", f"send {name}",
               numinlets=1, numoutlets=0,
               patching_rect=[30, 30, 80, 20]),
    ]
    return (boxes, [])


def receive_msg(id_prefix: str, name: str) -> tuple:
    """Create a receive object for message-domain routing without patch cords.

    Output the named message from {prefix}_receive outlet 0.
    """
    boxes = [
        newobj(f"{id_prefix}_receive", f"receive {name}",
               numinlets=0, numoutlets=1, outlettype=[""],
               patching_rect=[30, 30, 80, 20]),
    ]
    return (boxes, [])


def mc_gain_stage(id_prefix: str, channels: int = 2) -> tuple:
    """Multichannel gain control using mc.gain~.

    Wire MC signal into {prefix}_mcgain inlet 0.
    Gain level into {prefix}_mcgain inlet 1.
    Output MC signal from {prefix}_mcgain outlet 0.
    """
    if channels < 1:
        raise ValueError(f"mc_gain_stage channels must be >= 1, got {channels}")
    p = id_prefix
    boxes = [
        newobj(f"{p}_mcgain", f"mc.gain~ {channels}", numinlets=2,
               numoutlets=1, outlettype=["multichannelsignal"],
               patching_rect=[30, 120, 100, 20]),
    ]
    return (boxes, [])


def mc_mixer(id_prefix: str, inputs: int = 2, channels: int = 2) -> tuple:
    """Sum multiple MC streams using mc.mix~.

    Wire MC signals into {prefix}_mcmix inlets 0..inputs-1.
    Output summed MC signal from {prefix}_mcmix outlet 0.
    """
    if channels < 1:
        raise ValueError(f"mc_mixer channels must be >= 1, got {channels}")
    p = id_prefix
    boxes = [
        newobj(f"{p}_mcmix", f"mc.mix~ {inputs} {channels}", numinlets=inputs,
               numoutlets=1, outlettype=["multichannelsignal"],
               patching_rect=[30, 120, 100, 20]),
    ]
    return (boxes, [])


def mc_selector(id_prefix: str, channels: int = 2, count: int = 2) -> tuple:
    """Switch between MC signal paths using mc.selector~.

    Wire selection index into {prefix}_mcsel inlet 0.
    Wire MC signals into {prefix}_mcsel inlets 1..count.
    Output selected MC signal from {prefix}_mcsel outlet 0.
    """
    if channels < 1:
        raise ValueError(f"mc_selector channels must be >= 1, got {channels}")
    p = id_prefix
    boxes = [
        newobj(f"{p}_mcsel", f"mc.selector~ {count} {channels}",
               numinlets=count + 1, numoutlets=1,
               outlettype=["multichannelsignal"],
               patching_rect=[30, 120, 120, 20]),
    ]
    return (boxes, [])


def oversampled_wrapper(id_prefix: str, inner_boxes: list, inner_lines: list,
                        *, up: int = 2, extra_msg_inlets: int = 1) -> tuple:
    """Wrap an MSP chain in a ``poly~ … 1 up N`` subpatcher (T23b/Q49 —
    2x-oversample stock-MSP nonlinearities without gen~).

    ``inner_boxes``/``inner_lines`` form the chain; wire it FROM the
    provided ``{p}_in1`` (``in~ 1``, the upsampled signal) and INTO
    ``{p}_out1`` (``out~ 1``). Control messages enter the poly~'s inlet 2
    (an ``in 2`` box, id ``{p}_msgin``) — route them inside the chain.
    poly~ inlet numbering is shared between ``in~`` and ``in`` (doc-
    verified), so the host box has ``1 + extra_msg_inlets`` inlets.

    Returns ``([poly_box], [], (sidecar_name, sidecar_json))`` — one host
    box (id ``{p}_poly``) plus the voice patcher to
    ``device.register_asset(name, content, asset_type="TEXT",
    category="js")``. poly~ cannot embed its patcher inline (Live-verified
    silent), so the voice ships as a ``.maxpat`` next to the device and
    freeze packs it. The anti-alias filtering is poly~'s own.
    """
    p = id_prefix
    boxes = [
        {"box": {"id": f"{p}_in1", "maxclass": "newobj", "text": "in~ 1",
                 "numinlets": 0, "numoutlets": 1, "outlettype": ["signal"],
                 "patching_rect": [30, 30, 45, 20]}},
        {"box": {"id": f"{p}_out1", "maxclass": "newobj", "text": "out~ 1",
                 "numinlets": 1, "numoutlets": 0,
                 "patching_rect": [30, 400, 50, 20]}},
    ]
    for k in range(extra_msg_inlets):
        boxes.append({"box": {
            "id": f"{p}_msgin" if k == 0 else f"{p}_msgin{k + 1}",
            "maxclass": "newobj", "text": f"in {k + 2}",
            "numinlets": 0, "numoutlets": 1, "outlettype": [""],
            "patching_rect": [200 + k * 80, 30, 40, 20]}})
    boxes.extend(inner_boxes)
    sub = {
        "patcher": {
            "fileversion": 1,
            "appversion": {"major": 8, "minor": 6, "revision": 2},
            "rect": [0, 0, 640, 480],
            "bglocked": 0,
            "openinpresentation": 0,
            "boxes": boxes,
            "lines": list(inner_lines),
        }
    }
    host = {
        "box": {
            "id": f"{p}_poly", "maxclass": "newobj",
            "text": f"poly~ {p}_osfx.maxpat 1 up {int(up)}",
            "numinlets": 1 + extra_msg_inlets, "numoutlets": 1,
            "outlettype": ["signal"],
            "patching_rect": [30, 30, 200, 20],
        }
    }
    # poly~ CANNOT embed its patcher inline (Live-verified: an embedded
    # "patcher" dict is ignored and the object loads dead/silent) — the
    # voice must be a real .maxpat sidecar next to the device; return it
    # for the caller to register_asset.
    import json as _json
    sidecar = (f"{p}_osfx.maxpat", _json.dumps(sub, indent="\t"))
    return ([host], [], sidecar)
