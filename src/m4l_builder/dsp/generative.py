"""Generative sequencing."""

from ..objects import newobj, patchline


def probability_gate(id_prefix: str, probability: float = 0.5) -> tuple:
    """Probabilistic gate: pass an incoming bang only some fraction of the time.

    A staple generative building block. Each bang into {prefix}_gate inlet 0
    draws a fresh random value; when it falls under the threshold a bang fires
    from {prefix}_sel outlet 0. Drive it from a clock (e.g. metro). Send an int
    0-1000 into {prefix}_thresh inlet 1 to change the density live (probability
    x 1000).
    """
    if not 0.0 <= probability <= 1.0:
        raise ValueError(f"probability must be in [0.0, 1.0], got {probability}")

    p = id_prefix
    threshold = int(round(probability * 1000))
    boxes = [
        newobj(f"{p}_gate", "random 1000", numinlets=2, numoutlets=1,
               outlettype=["int"], patching_rect=[30, 120, 90, 20]),
        newobj(f"{p}_thresh", f"< {threshold}", numinlets=2, numoutlets=1,
               outlettype=["int"], patching_rect=[30, 150, 70, 20]),
        newobj(f"{p}_sel", "sel 1", numinlets=2, numoutlets=2,
               outlettype=["bang", ""], patching_rect=[30, 180, 50, 20]),
    ]
    lines = [
        patchline(f"{p}_gate", 0, f"{p}_thresh", 0),
        patchline(f"{p}_thresh", 0, f"{p}_sel", 0),
    ]
    return (boxes, lines)


def random_note(id_prefix: str, low: int = 48, high: int = 72) -> tuple:
    """Generate a random MIDI note number in [low, high] on each incoming bang.

    A generative pitch source. Wire a trigger (bang) into {prefix}_rand inlet 0;
    the chosen pitch appears at {prefix}_offset outlet 0. Pair with
    pitch_quantize() to constrain the output to a musical scale.
    """
    if not 0 <= low <= high <= 127:
        raise ValueError(f"require 0 <= low <= high <= 127, got low={low}, high={high}")

    p = id_prefix
    span = high - low + 1
    boxes = [
        newobj(f"{p}_rand", f"random {span}", numinlets=2, numoutlets=1,
               outlettype=["int"], patching_rect=[30, 120, 80, 20]),
        newobj(f"{p}_offset", f"+ {low}", numinlets=2, numoutlets=1,
               outlettype=["int"], patching_rect=[30, 150, 60, 20]),
    ]
    lines = [
        patchline(f"{p}_rand", 0, f"{p}_offset", 0),
    ]
    return (boxes, lines)


def euclidean_rhythm(id_prefix: str, steps: int = 16, pulses: int = 4) -> tuple:
    """Generate a Euclidean rhythm: `pulses` hits spread evenly over `steps`.

    A `metro` clock drives a `counter` through 0..steps-1; the hit positions are
    computed at build time and matched by a `sel`, whose outlets are merged to a
    single bang at {prefix}_hit outlet 0. Start/stop by sending 1/0 to
    {prefix}_metro inlet 0, set the step time (ms) on {prefix}_metro inlet 1, and
    take the rhythm bang from {prefix}_hit. Self-contained -- no baked data.
    """
    if not 1 <= pulses <= steps <= 128:
        raise ValueError(
            f"require 1 <= pulses <= steps <= 128, got steps={steps}, pulses={pulses}"
        )

    hits = sorted({(i * steps) // pulses for i in range(pulses)})
    p = id_prefix
    boxes = [
        newobj(f"{p}_metro", "metro 125", numinlets=2, numoutlets=1,
               outlettype=["bang"], patching_rect=[30, 30, 70, 20]),
        newobj(f"{p}_counter", f"counter 0 {steps - 1}", numinlets=5, numoutlets=4,
               outlettype=["int", "", "", ""], patching_rect=[30, 60, 90, 20]),
        newobj(f"{p}_sel", "sel " + " ".join(str(h) for h in hits),
               numinlets=2, numoutlets=len(hits) + 1,
               outlettype=[""] * (len(hits) + 1), patching_rect=[30, 90, 130, 20]),
        newobj(f"{p}_hit", "t b", numinlets=1, numoutlets=1,
               outlettype=["bang"], patching_rect=[30, 120, 40, 20]),
    ]
    lines = [
        patchline(f"{p}_metro", 0, f"{p}_counter", 0),
        patchline(f"{p}_counter", 0, f"{p}_sel", 0),
    ]
    # Every match outlet of `sel` feeds the single bang trigger.
    lines += [patchline(f"{p}_sel", k, f"{p}_hit", 0) for k in range(len(hits))]
    return (boxes, lines)
