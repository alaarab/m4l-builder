"""Which of the library's gen snippets the offline simulator can run.

Calls every public function in ``gen_snippets``, ``gen_character`` and
``gen_stateful``, turns what it returns into a standalone kernel, and runs 256
samples of noise through :class:`m4l_builder.gen_sim.GenKernel`. Prints a
markdown table: ``renders``, ``renders (approximate: ...)`` or the
``UnsupportedKernel`` reason.

To make a snippet standalone, names it reads but does not assign (its inputs,
parameters and the state its caller owns) are declared ``History name(0.25)``,
function definitions get a call site fed from ``in1``, and a few snippets get
the arguments, declarations or call they need from ``CALLS`` below. A name
that is CALLED but not defined is a gen operator the simulator does not model,
and is reported as such.

    uv run python tools/gen_sim_coverage.py
"""

from __future__ import annotations

import inspect
import random
import re

from m4l_builder import gen_character, gen_snippets, gen_stateful
from m4l_builder.gen_sim import GenKernel, UnsupportedKernel

# name -> args / kwargs for the call, gen code to put before it (function
# definitions it depends on), and declarations or statements to put after it.
CALLS: dict[str, dict] = {
    "flush": {"args": ("in1",), "wrap": "out1 = {};"},
    "rbj_shelf": {"args": ("1000.", "6.", "low", "b0", "b1", "b2", "a1", "a2")},
    "biquad_cascade": {"args": ("in1", "out1", "1000.", "low", 4)},
    "lr_crossover": {"args": ("in1", "lo", "hi", "1000.", 4)},
    "multiband_split": {"args": ("in1", ["b1", "b2", "b3"], ["200.", "2000."])},
    "frac_read_cubic": {"args": ("dl", "2.5", "out1"), "after": "Delay dl(64);"},
    "frac_read_allpass": {"args": ("dl", "2.5", "out1"), "after": "Delay dl(64);"},
    "allpass_diffusion_chain": {"args": ("in1", "out1", 2)},
    "ring_delay": {"args": ("rd", 64), "after": "out1 = y;"},
    "viz_poke_block": {"args": ("v = in1;",), "after": "out1 = in1;"},
    "lfo_osc_fn": {"before": gen_stateful.qpow_fn()},
    "allpass_fn": {"after": "Delay d1(64); Delay d2(64);\n"
                            "out1 = allpass(in1, 0.5, 10, d1, d2);"},
    "diffuse_fn": {"after": "Delay dl(64);\nout1 = diffuse(in1, 10, dl, 0.5);"},
    "lfo_voice_fn": {"after": "Data ph(4); Data sh(4); Data dr(4, 2);\n"
                              "out1 = lfo_voice(ph, sh, dr, 0, 2., in1);"},
    "freeze_capture_block": {"after": "Delay delaySigR(64); Delay delaySigL(64);"},
}
INT_ARGS = {"voices": 2, "order": 4, "num_stages": 2, "channels": 1}
NOT_KERNELS = {"butterworth_q_table": "returns a Q table, not gen code",
               "compose_gen_code": "assembles other snippets"}
_FN_DEF = re.compile(r"^([A-Za-z_]\w*)\s*\(([^()]*)\)\s*\{", re.M)
_CONTROL = {"if", "else", "for", "while"}


def _public_functions(module):
    for name, fn in inspect.getmembers(module, inspect.isfunction):
        if not name.startswith("_") and fn.__module__ == module.__name__:
            yield name, fn


def _source(name: str, fn) -> tuple[str, str]:
    """(code, extra) for one snippet: its gen source and what follows it."""
    spec = CALLS.get(name, {})
    if "args" in spec:
        args, kwargs = list(spec["args"]), {}
    else:
        args, kwargs = [], {}
        for param in inspect.signature(fn).parameters.values():
            if param.default is not inspect.Parameter.empty or param.kind in (
                    param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
            value = INT_ARGS.get(param.name, param.name)
            if param.kind == param.KEYWORD_ONLY:
                kwargs[param.name] = value
            else:
                args.append(value)
    code = fn(*args, **kwargs)
    code = spec.get("wrap", "{}").format(code)
    return spec.get("before", "") + "\n" + code, spec.get("after", "")


def _call_site(code: str, extra: str) -> str:
    defs = [(n, p) for n, p in _FN_DEF.findall(code) if n not in _CONTROL]
    if not defs or re.search(r"(?<![\w.])out1\s*=", code + extra):
        return ""
    name, params = defs[-1]
    arity = len([p for p in params.split(",") if p.strip()])
    return f"out1 = {name}({', '.join(['in1'] * arity)});"


def classify(code: str, extra: str = "") -> str:
    call = _call_site(code, extra)
    declared: list[str] = []
    rng = random.Random(0)
    noise = [rng.uniform(-1.0, 1.0) for _ in range(256)]
    for _ in range(64):
        source = "\n".join([code, extra, *declared, call])
        try:
            kernel = GenKernel(source)
            kernel.run({f"in{i}": noise for i in range(1, 5)}, num_samples=len(noise))
        except UnsupportedKernel as exc:
            missing = re.search(r"unknown name '(\w+)'", str(exc))
            if missing and not missing.group(1).startswith("_gfn"):
                name = missing.group(1)
                if re.search(rf"(?<![\w.]){name}\s*\(", source):
                    return f"refused: gen operator `{name}()` is not modelled"
                declared.append(f"History {name}(0.25);")
                continue
            reason = re.sub(r"^sample \d+: ", "", str(exc)).split("\n")[0]
            return f"refused: {reason}"
        if kernel.approximations:
            kinds = ", ".join("noise()" if "noise" in note else 'interp="cubic"'
                              for note in kernel.approximations)
            return f"renders (approximate: {kinds})"
        return "renders"
    return "refused: too many free names to make it standalone"


def main() -> None:
    print("| snippet | gen_sim |")
    print("|---|---|")
    for module in (gen_snippets, gen_character, gen_stateful):
        short = module.__name__.rsplit(".", 1)[1]
        for name, fn in _public_functions(module):
            if name in NOT_KERNELS:
                print(f"| `{short}.{name}` | n/a: {NOT_KERNELS[name]} |")
                continue
            code, extra = _source(name, fn)
            print(f"| `{short}.{name}` | {classify(code, extra)} |")


if __name__ == "__main__":
    main()
