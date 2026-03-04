"""Pre-wired DSP combo recipes for common M4L patterns.

Each recipe takes a device instance and parameters, then adds a complete
pre-wired section using device.add_dsp(), device.add_newobj(), device.add_dial(),
and device.add_line(). Returns a dict of important IDs for further wiring.
"""

from .dsp import notein as dsp_notein, delay_line, param_smooth


def gain_controlled_stage(device, id_prefix, dial_rect, x=30, y=30):
    """Add a gain-controlled stage: live.dial -> dbtoa -> *~ gain cell.

    The dial outputs dB values, dbtoa converts to linear amplitude,
    and *~ applies the gain to whatever signal is wired into its inlet 0.

    Args:
        device: Device instance to add objects to.
        id_prefix: Prefix for all object IDs in this stage.
        dial_rect: [x, y, w, h] for the dial in presentation mode.
        x: Patching x offset for DSP objects.
        y: Patching y offset for DSP objects.

    Returns:
        dict with keys "dial" and "gain" (the *~ object ID).
    """
    p = id_prefix

    dial_id = device.add_dial(
        f"{p}_dial", f"{p}_gain", dial_rect,
        min_val=-70.0, max_val=6.0, initial=0.0,
        unitstyle=4, annotation_name=f"{p} Gain",
    )

    dbtoa_id = device.add_newobj(
        f"{p}_dbtoa", "dbtoa", numinlets=1, numoutlets=1,
        outlettype=[""], patching_rect=[x, y, 50, 20],
    )

    smooth_boxes, smooth_lines = param_smooth(f"{p}_smooth")
    device.add_dsp(smooth_boxes, smooth_lines)

    gain_id = device.add_newobj(
        f"{p}_gain", "*~ 1.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 90, 40, 20],
    )

    # Wiring: dial -> dbtoa -> pack -> line~ -> *~ inlet 1
    device.add_line(dial_id, 0, dbtoa_id, 0)
    device.add_line(dbtoa_id, 0, f"{p}_smooth_pack", 0)
    device.add_line(f"{p}_smooth_line", 0, gain_id, 1)

    return {"dial": dial_id, "gain": gain_id}


def dry_wet_stage(device, id_prefix, dial_rect, x=30, y=30):
    """Add a dry/wet crossfade stage: live.dial (0-100) -> scaled mix.

    The dial outputs 0-100 percent, multiplied by 0.01 to get 0.0-1.0.
    A trigger fans the value to wet gain and an inverter for dry gain.
    Wire dry signal into {prefix}_dry_gain inlet 0,
    wet signal into {prefix}_wet_gain inlet 0,
    then sum {prefix}_dry_gain and {prefix}_wet_gain outputs.

    Args:
        device: Device instance to add objects to.
        id_prefix: Prefix for all object IDs in this stage.
        dial_rect: [x, y, w, h] for the dial in presentation mode.
        x: Patching x offset for DSP objects.
        y: Patching y offset for DSP objects.

    Returns:
        dict with keys "dial", "wet_gain", "dry_gain".
    """
    p = id_prefix

    dial_id = device.add_dial(
        f"{p}_dial", f"{p}_mix", dial_rect,
        min_val=0.0, max_val=100.0, initial=50.0,
        unitstyle=5, annotation_name=f"{p} Dry/Wet",
    )

    scale_id = device.add_newobj(
        f"{p}_scale", "*~ 0.01", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y, 55, 20],
    )

    trig_id = device.add_newobj(
        f"{p}_trig", "t f f", numinlets=1, numoutlets=2,
        outlettype=["", ""], patching_rect=[x, y + 30, 40, 20],
    )

    wet_smooth_boxes, wet_smooth_lines = param_smooth(f"{p}_wet_smooth")
    device.add_dsp(wet_smooth_boxes, wet_smooth_lines)

    dry_smooth_boxes, dry_smooth_lines = param_smooth(f"{p}_dry_smooth")
    device.add_dsp(dry_smooth_boxes, dry_smooth_lines)

    # !-~ 1. gives (1 - mix) for the dry side
    inv_id = device.add_newobj(
        f"{p}_inv", "!-~ 1.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x + 80, y + 30, 45, 20],
    )

    wet_gain_id = device.add_newobj(
        f"{p}_wet_gain", "*~ 0.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 90, 40, 20],
    )

    dry_gain_id = device.add_newobj(
        f"{p}_dry_gain", "*~ 1.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x + 80, y + 90, 40, 20],
    )

    # Wiring: dial -> trig; trig fans to wet smooth and dry inverter
    # t f f fires outlet 1 first (dry/inv), then outlet 0 (wet)
    device.add_line(dial_id, 0, trig_id, 0)
    device.add_line(trig_id, 0, f"{p}_wet_smooth_pack", 0)
    device.add_line(f"{p}_wet_smooth_line", 0, wet_gain_id, 1)
    device.add_line(trig_id, 1, inv_id, 0)
    device.add_line(inv_id, 0, f"{p}_dry_smooth_pack", 0)
    device.add_line(f"{p}_dry_smooth_line", 0, dry_gain_id, 1)

    return {"dial": dial_id, "wet_gain": wet_gain_id, "dry_gain": dry_gain_id}


def tempo_synced_delay(device, id_prefix, time_dial_rect, feedback_dial_rect,
                       x=30, y=30):
    """Add a tempo-synced delay: two dials + tapin~/tapout~ with transport.

    Delay time dial controls the base delay in ms. Feedback dial controls
    how much of the output feeds back into the input (0-95%).
    Transport object provides BPM for tempo sync calculations.

    Args:
        device: Device instance to add objects to.
        id_prefix: Prefix for all object IDs in this stage.
        time_dial_rect: [x, y, w, h] for the time dial in presentation mode.
        feedback_dial_rect: [x, y, w, h] for the feedback dial.
        x: Patching x offset for DSP objects.
        y: Patching y offset for DSP objects.

    Returns:
        dict with keys "time_dial", "feedback_dial", "tapin", "tapout".
    """
    p = id_prefix

    time_dial_id = device.add_dial(
        f"{p}_time_dial", f"{p}_time", time_dial_rect,
        min_val=1.0, max_val=5000.0, initial=375.0,
        unitstyle=2, annotation_name=f"{p} Delay Time",
    )

    fb_dial_id = device.add_dial(
        f"{p}_fb_dial", f"{p}_feedback", feedback_dial_rect,
        min_val=0.0, max_val=95.0, initial=40.0,
        unitstyle=5, annotation_name=f"{p} Feedback",
    )

    delay_boxes, delay_lines = delay_line(f"{p}_delay", max_delay_ms=5000)
    device.add_dsp(delay_boxes, delay_lines)
    tapin_id = f"{p}_delay_tapin"
    tapout_id = f"{p}_delay_tapout"

    transport_id = device.add_newobj(
        f"{p}_transport", "transport", numinlets=1, numoutlets=7,
        outlettype=["int", "", "float", "float", "float", "", "int"],
        patching_rect=[x + 200, y, 70, 20],
    )

    loadbang_id = device.add_newobj(
        f"{p}_loadbang", "loadbang", numinlets=1, numoutlets=1,
        outlettype=["bang"], patching_rect=[x + 200, y - 30, 55, 20],
    )

    time_smooth_boxes, time_smooth_lines = param_smooth(f"{p}_time_smooth")
    device.add_dsp(time_smooth_boxes, time_smooth_lines)

    fb_scale_id = device.add_newobj(
        f"{p}_fb_scale", "scale 0. 95. 0. 0.95", numinlets=6, numoutlets=1,
        outlettype=[""], patching_rect=[x + 100, y + 60, 120, 20],
    )

    fb_smooth_boxes, fb_smooth_lines = param_smooth(f"{p}_fb_smooth")
    device.add_dsp(fb_smooth_boxes, fb_smooth_lines)

    fb_mul_id = device.add_newobj(
        f"{p}_fb_mul", "*~ 0.", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 120, 40, 20],
    )

    sum_id = device.add_newobj(
        f"{p}_sum", "+~", numinlets=2, numoutlets=1,
        outlettype=["signal"], patching_rect=[x, y + 150, 30, 20],
    )

    # Wiring: time dial -> smooth -> tapout~ delay time
    device.add_line(time_dial_id, 0, f"{p}_time_smooth_pack", 0)
    device.add_line(f"{p}_time_smooth_line", 0, tapout_id, 1)

    # Wiring: feedback dial -> scale -> smooth -> fb_mul inlet 1
    device.add_line(fb_dial_id, 0, fb_scale_id, 0)
    device.add_line(fb_scale_id, 0, f"{p}_fb_smooth_pack", 0)
    device.add_line(f"{p}_fb_smooth_line", 0, fb_mul_id, 1)

    # Wiring: tapout -> fb_mul -> sum inlet 1 (feedback loop)
    device.add_line(tapout_id, 0, fb_mul_id, 0)
    device.add_line(fb_mul_id, 0, sum_id, 1)

    # Wiring: sum -> tapin (input goes to sum inlet 0 externally)
    device.add_line(sum_id, 0, tapin_id, 0)

    # Wiring: loadbang -> transport
    device.add_line(loadbang_id, 0, transport_id, 0)

    return {
        "time_dial": time_dial_id,
        "feedback_dial": fb_dial_id,
        "tapin": tapin_id,
        "tapout": tapout_id,
    }


def midi_note_gate(device, id_prefix, x=30, y=30):
    """Add a MIDI note input stage: notein -> unpack -> stripnote -> kslider.

    Receives MIDI notes and unpacks pitch and velocity. stripnote filters
    out note-off messages. kslider provides a visual keyboard display.

    Args:
        device: Device instance to add objects to.
        id_prefix: Prefix for all object IDs in this stage.
        x: Patching x offset for DSP objects.
        y: Patching y offset for DSP objects.

    Returns:
        dict with keys "notein", "pitch", "velocity".
    """
    p = id_prefix

    notein_boxes, notein_lines = dsp_notein(p)
    device.add_dsp(notein_boxes, notein_lines)
    notein_id = f"{p}_notein"

    # stripnote passes pitch/velocity only when velocity > 0
    stripnote_id = device.add_newobj(
        f"{p}_stripnote", "stripnote", numinlets=2, numoutlets=2,
        outlettype=["", ""], patching_rect=[x, y + 30, 60, 20],
    )

    kslider_id = device.add_kslider(
        f"{p}_kslider", [x, y + 60, 200, 40],
    )

    device.add_line(notein_id, 0, stripnote_id, 0)
    device.add_line(notein_id, 1, stripnote_id, 1)
    device.add_line(stripnote_id, 0, kslider_id, 0)

    return {
        "notein": notein_id,
        "pitch": stripnote_id,      # outlet 0
        "velocity": stripnote_id,   # outlet 1
    }
