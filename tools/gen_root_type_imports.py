"""Regenerate the TYPE_CHECKING import block in ``m4l_builder/__init__.py``.

The root package resolves exports lazily (``__getattr__`` over the
``_exports`` tables), which type checkers cannot follow. The generated block
imports each root export from the module that *defines* it, so mypy and
pyright see real types for ``from m4l_builder import AudioEffect``.

    uv run python tools/gen_root_type_imports.py          # rewrite in place
    uv run python tools/gen_root_type_imports.py --check  # exit 1 on drift

``tests/test_root_type_imports.py`` fails when the block is stale.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import sys
from pathlib import Path

INIT_PATH = Path(__file__).resolve().parents[1] / "src" / "m4l_builder" / "__init__.py"
BEGIN = "    # BEGIN GENERATED ROOT TYPE IMPORTS (tools/gen_root_type_imports.py)\n    # isort: off\n"
END = "    # isort: on\n    # END GENERATED ROOT TYPE IMPORTS\n"


def _defined_names(module) -> set[str]:
    """Top-level names a module binds itself (def/class/assignment, not import)."""
    try:
        tree = ast.parse(inspect.getsource(module))
    except (OSError, TypeError):
        return set()
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name):
                        names.add(sub.id)
    return names


def _defining_module(name: str, value, group_module: str) -> str:
    """The m4l_builder module whose own top level binds ``name`` to ``value``."""
    candidates = []
    owner = getattr(value, "__module__", None)
    if isinstance(owner, str):
        candidates.append(owner)
    group = importlib.import_module(group_module)
    candidates.extend(m.__name__ for m in getattr(group, "_SOURCE_MODULES", ()))
    candidates.append(group_module)
    candidates.extend(sorted(n for n in sys.modules if n.startswith("m4l_builder.")))
    for module_name in candidates:
        if not module_name.startswith("m4l_builder"):
            continue
        module = sys.modules.get(module_name) or importlib.import_module(module_name)
        if name in _defined_names(module) and getattr(module, name, None) is value:
            return module_name
    raise LookupError(f"no m4l_builder module defines root export {name!r}")


def _relative(module_name: str) -> str:
    return "." + module_name.removeprefix("m4l_builder.")


def render() -> str:
    """The generated block, mirroring ``__getattr__`` resolution order."""
    import m4l_builder
    from m4l_builder._exports import ROOT_ALL, ROOT_EXPORT_GROUPS, ROOT_NAMESPACE_MODULES

    lines: list[str] = []
    renamed: list[str] = []
    for alias, module_name in sorted(ROOT_NAMESPACE_MODULES.items()):
        parent, _, leaf = module_name.rpartition(".")
        package = "." if parent == "m4l_builder" else _relative(parent)
        if leaf == alias:
            lines.append(f"    from {package} import {leaf} as {alias}\n")
        else:
            # A non-redundant alias is private to pyright; assign it instead.
            lines.append(f"    from {package} import {leaf} as _{alias}_module\n")
            renamed.append(f"    {alias} = _{alias}_module\n")

    by_module: dict[str, list[str]] = {}
    seen = set(ROOT_NAMESPACE_MODULES)
    for group_module, exports in ROOT_EXPORT_GROUPS:
        for name in exports:
            if name in seen:
                continue  # __getattr__ returns the first match
            seen.add(name)
            value = getattr(m4l_builder, name)
            by_module.setdefault(_defining_module(name, value, group_module), []).append(name)

    missing = set(ROOT_ALL) - seen
    if missing:
        raise LookupError(f"ROOT_ALL names outside ROOT_EXPORT_GROUPS: {sorted(missing)}")

    for module_name in sorted(by_module):
        lines.append(f"    from {_relative(module_name)} import (\n")
        lines.extend(f"        {name} as {name},\n" for name in sorted(by_module[module_name]))
        lines.append("    )\n")
    return BEGIN + "".join(lines) + "".join(renamed) + END


def current() -> str:
    text = INIT_PATH.read_text()
    start, end = text.index(BEGIN), text.index(END) + len(END)
    return text[start:end]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the block is stale")
    args = parser.parse_args(argv)
    expected = render()
    if args.check:
        return 0 if current() == expected else 1
    INIT_PATH.write_text(INIT_PATH.read_text().replace(current(), expected))
    return 0


if __name__ == "__main__":
    sys.exit(main())
