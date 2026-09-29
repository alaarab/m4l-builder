"""The root package's TYPE_CHECKING imports mirror its lazy exports."""

import ast
import importlib
import importlib.util
from pathlib import Path

import m4l_builder
from m4l_builder._exports import ROOT_ALL, ROOT_NAMESPACE_MODULES

ROOT = Path(__file__).resolve().parents[1]


def _load_generator():
    path = ROOT / "tools" / "gen_root_type_imports.py"
    spec = importlib.util.spec_from_file_location("gen_root_type_imports", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _type_checking_block():
    tree = ast.parse(Path(m4l_builder.__file__).read_text())
    for node in tree.body:
        if isinstance(node, ast.If) and getattr(node.test, "id", None) == "TYPE_CHECKING":
            return node.body
    raise AssertionError("no TYPE_CHECKING block in m4l_builder/__init__.py")


def _static_bindings():
    """{public name: (module, attribute)} bound by the TYPE_CHECKING block."""
    imported = {}
    bindings = {}
    for node in _type_checking_block():
        if isinstance(node, ast.ImportFrom):
            package = importlib.import_module(
                "m4l_builder" + ("." + node.module if node.module else ""))
            for alias in node.names:
                imported[alias.asname or alias.name] = (package.__name__, alias.name)
        elif isinstance(node, ast.Assign):
            (target,) = node.targets
            imported[target.id] = imported[node.value.id]
    for name, source in imported.items():
        if not name.startswith("_"):
            bindings[name] = source
    return bindings


def test_generated_block_is_current():
    generator = _load_generator()
    assert generator.current() == generator.render(), (
        "run: uv run python tools/gen_root_type_imports.py")


def test_static_imports_cover_exactly_the_lazy_exports():
    assert set(_static_bindings()) == set(ROOT_ALL) | set(ROOT_NAMESPACE_MODULES)


def test_static_imports_resolve_to_the_runtime_objects():
    for name, (module_name, attribute) in _static_bindings().items():
        module = importlib.import_module(module_name)
        try:
            value = getattr(module, attribute)
        except AttributeError:
            value = importlib.import_module(f"{module_name}.{attribute}")
        if name in ROOT_NAMESPACE_MODULES:
            # Compare with the lazy table, not getattr: importing a same-named
            # submodule (m4l_builder/reverse.py) shadows the lazy `reverse`.
            expected = importlib.import_module(ROOT_NAMESPACE_MODULES[name])
        else:
            expected = getattr(m4l_builder, name)
        assert value is expected, name
