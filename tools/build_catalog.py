"""Generate docs/catalog.md - a browsable index of the public building blocks.

Run:  uv run python tools/build_catalog.py
"""

import importlib
import inspect
import pkgutil
from pathlib import Path

import m4l_builder.theme as theme_mod
from m4l_builder.builder import dsp, recipes, ui
from m4l_builder.theme import Theme

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "catalog.md"


def _summary(obj) -> str:
    doc = (inspect.getdoc(obj) or "").strip()
    first = doc.splitlines()[0] if doc else ""
    return first.replace("|", r"\|")


def _public(module):
    pairs = []
    for name in getattr(module, "__all__", []):
        if name.startswith("_"):
            continue
        obj = getattr(module, name, None)
        if inspect.isfunction(obj) or inspect.isclass(obj):
            pairs.append((name, obj))
    return sorted(pairs)


def _table(pairs) -> str:
    rows = ["| Name | Summary |", "|------|---------|"]
    rows += [f"| `{name}` | {_summary(obj)} |" for name, obj in pairs]
    return "\n".join(rows)


def build() -> str:
    parts = [
        "# Catalog\n",
        "A browsable index of the public building blocks. Regenerate with "
        "`uv run python tools/build_catalog.py`.\n",
    ]
    for title, module in [("DSP blocks", dsp), ("UI widgets", ui), ("Recipes", recipes)]:
        pairs = _public(module)
        parts.append(f"## {title} ({len(pairs)})\n\n{_table(pairs)}\n")

    themes = sorted(n for n, v in vars(theme_mod).items() if isinstance(v, Theme))
    parts.append(f"## Themes ({len(themes)})\n\n" + ", ".join(f"`{t}`" for t in themes) + "\n")

    import m4l_builder.engines as eng
    rows = ["| Module | Generators |", "|--------|------------|"]
    count = 0
    for name in sorted(m.name for m in pkgutil.iter_modules(eng.__path__)):
        if name.startswith("_"):
            continue
        module = importlib.import_module(f"m4l_builder.engines.{name}")
        fns = sorted(
            n for n, v in vars(module).items()
            if inspect.isfunction(v) and not n.startswith("_")
            and getattr(v, "__module__", "") == module.__name__
        )
        if fns:
            count += 1
            rows.append(f"| `{name}` | {', '.join('`' + f + '`' for f in fns)} |")
    parts.append(
        f"## Engines ({count})\n\nJavaScript (jsui) visualization generators.\n\n"
        + "\n".join(rows) + "\n"
    )
    return "\n".join(parts)


if __name__ == "__main__":
    OUT.write_text(build())
    print("wrote", OUT)
