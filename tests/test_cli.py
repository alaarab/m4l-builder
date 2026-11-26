"""The ``m4l`` command line, driven through ``main(argv)`` like a shell would."""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from m4l_builder import cli
from m4l_builder.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
GAIN_EXAMPLE = EXAMPLES / "01_gain_audio_effect.py"


@pytest.fixture(autouse=True)
def user_library(tmp_path, monkeypatch):
    """Point every User Library write at a temp folder."""
    root = tmp_path / "User Library"
    monkeypatch.setenv("M4L_USER_LIBRARY", str(root))
    return root


def _write(path: Path, source: str) -> Path:
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return path


# -- new ------------------------------------------------------------------- #

@pytest.mark.parametrize("kind, type_code, folder", [
    ("audio", b"aaaa", "Presets/Audio Effects/Max Audio Effect"),
    ("midi", b"mmmm", "Presets/MIDI Effects/Max MIDI Effect"),
    ("instrument", b"iiii", "Presets/Instruments/Max Instrument"),
])
def test_new_scaffold_builds_lint_clean_into_the_user_library(
        tmp_path, user_library, capsys, kind, type_code, folder):
    script = tmp_path / "scaffold" / "build.py"
    assert main(["new", "Fresh Device", "--type", kind, "--out", str(script)]) == 0
    assert script.is_file()

    assert main(["lint", str(script), "--strict"]) == 0
    assert not user_library.exists(), "lint must not write to the User Library"
    assert main(["build", str(script)]) == 0

    built = user_library / folder / "Fresh Device.amxd"
    assert built.read_bytes()[8:12] == type_code
    assert str(built) in capsys.readouterr().out


def test_new_defaults_to_a_slug_folder_and_refuses_to_overwrite(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["new", "My Gain!"]) == 0
    script = tmp_path / "my_gain" / "build.py"
    original = script.read_text()
    assert "NAME = 'My Gain!'" in original

    script.write_text("# my edits\n")
    assert main(["new", "My Gain!"]) == 1
    assert script.read_text() == "# my edits\n"
    assert "already exists" in capsys.readouterr().err

    assert main(["new", "My Gain!", "--force"]) == 0
    assert script.read_text() == original


# -- build ----------------------------------------------------------------- #

def test_build_out_directory_keeps_the_scripts_file_name(tmp_path):
    out = tmp_path / "dist"
    assert main(["build", str(GAIN_EXAMPLE), "--out", str(out)]) == 0
    assert (out / "My Gain.amxd").read_bytes()[:4] == b"ampf"


def test_build_out_file_needs_a_single_device(tmp_path, capsys):
    target = tmp_path / "renamed.amxd"
    assert main(["build", str(GAIN_EXAMPLE), "--out", str(target)]) == 0
    assert target.read_bytes()[:4] == b"ampf"

    two = _write(tmp_path / "two.py", """
        from m4l_builder import AudioEffect
        AudioEffect("A", 100, 100).build("a.amxd")
        AudioEffect("B", 100, 100).build("b.amxd")
    """)
    assert main(["build", str(two), "--out", str(tmp_path / "one.amxd")]) == 1
    assert "more than one device" in capsys.readouterr().err


def test_build_accepts_a_module_level_device_and_defaults_to_the_user_library(
        tmp_path, user_library):
    # The m4l_builder.guidelines convention: a top-level `device`, no build() call.
    script = _write(tmp_path / "plain.py", """
        from m4l_builder import COOL, MidiEffect
        device = MidiEffect("Plain", 120, 100, theme=COOL)
        device.add_panel("bg", [0, 0, 120, 100])
    """)
    assert main(["build", str(script)]) == 0
    assert (user_library / "Presets/MIDI Effects/Max MIDI Effect/Plain.amxd").is_file()


def test_build_reports_a_script_that_builds_nothing(tmp_path, capsys):
    empty = _write(tmp_path / "empty.py", "x = 1\n")
    assert main(["build", str(empty)]) == 1
    assert "built no device" in capsys.readouterr().err


def test_build_restores_argv_and_lets_scripts_import_siblings(tmp_path):
    _write(tmp_path / "helpers.py", """
        import sys
        SEEN_ARGV = list(sys.argv)
    """)
    script = _write(tmp_path / "uses_helper.py", """
        import helpers
        from m4l_builder import AudioEffect
        AudioEffect("Helper " + str(len(helpers.SEEN_ARGV)), 100, 100).build("x.amxd")
    """)
    argv = sys.argv[:]
    assert main(["build", str(script), "--out", str(tmp_path / "o")]) == 0
    assert sys.argv == argv
    assert (tmp_path / "o" / "x.amxd").is_file()


# -- lint ------------------------------------------------------------------ #

def test_lint_fails_on_a_wiring_error_without_writing(tmp_path, user_library, capsys):
    script = _write(tmp_path / "broken.py", """
        from m4l_builder import AudioEffect
        device = AudioEffect("Broken", 100, 100)
        device.add_newobj("g", "*~ 1.")
        device.add_line("g", 0, "nowhere", 0)
        device.build("broken.amxd")
    """)
    assert main(["lint", str(script)]) == 1
    out = capsys.readouterr().out
    assert "E unknown-destination" in out
    assert not (tmp_path / "broken.amxd").exists()
    assert not user_library.exists()


def test_lint_reports_genexpr_problems_that_skipped_build_time_lint(tmp_path, capsys):
    script = _write(tmp_path / "gen.py", """
        from m4l_builder import AudioEffect
        device = AudioEffect("Gen", 100, 100)
        device.embed_gendsp("dsp", "out1 = in1;", 2, 2, [0, 0, 60, 20], lint=False)
    """)
    assert main(["lint", str(script)]) == 1
    assert "out2 declared (numouts=2) but never assigned" in capsys.readouterr().out


def test_lint_strict_turns_warnings_into_failure(capsys):
    # The gain example is wider than its content: a layout warning, not an error.
    assert main(["lint", str(GAIN_EXAMPLE)]) == 0
    assert "w width-mismatch" in capsys.readouterr().out
    assert main(["lint", str(GAIN_EXAMPLE), "--strict"]) == 1


def test_lint_reads_a_built_amxd(tmp_path, capsys):
    main(["build", str(GAIN_EXAMPLE), "--out", str(tmp_path)])
    assert main(["lint", str(tmp_path / "My Gain.amxd")]) == 0
    assert "My Gain: 0 error(s)" in capsys.readouterr().out


# -- inspect --------------------------------------------------------------- #

def test_inspect_summarises_type_size_parameters_and_boxes(tmp_path, capsys):
    main(["build", str(GAIN_EXAMPLE), "--out", str(tmp_path)])
    amxd = tmp_path / "My Gain.amxd"
    capsys.readouterr()

    assert main(["inspect", str(amxd), "--json"]) == 0
    summary = json.loads(capsys.readouterr().out)
    # Facts from examples/01: a 150x110 audio effect, one Gain dial (-70..6 dB),
    # plugin~/plugout~ + panel + dial + five objects, nine patch lines.
    assert summary["type"] == "audio_effect"
    assert summary["size"] == [150, 110]
    assert summary["parameters"] == [
        {"name": "Gain", "type": "float", "min": -70.0, "max": 6.0, "initial": 0.0}]
    assert summary["boxes"] == 9
    assert summary["lines"] == 9
    assert summary["maxclasses"] == {"newobj": 7, "live.dial": 1, "panel": 1}
    assert summary["file_bytes"] == amxd.stat().st_size

    assert main(["inspect", str(amxd)]) == 0
    text = capsys.readouterr().out
    assert "My Gain  (audio_effect, 150 x 110 px)" in text
    assert "- Gain (float: -70.0 .. 6.0, initial 0.0)" in text


def test_inspect_rejects_a_file_that_is_not_a_device(tmp_path, capsys):
    bogus = tmp_path / "bogus.amxd"
    bogus.write_bytes(b"nope")
    assert main(["inspect", str(bogus)]) == 1
    assert "not a valid AMXD file" in capsys.readouterr().err


def test_python_dash_m_runs_the_cli(tmp_path):
    main(["build", str(GAIN_EXAMPLE), "--out", str(tmp_path)])
    result = subprocess.run(
        [sys.executable, "-m", "m4l_builder", "inspect", str(tmp_path / "My Gain.amxd")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "audio_effect" in result.stdout


# -- watch ----------------------------------------------------------------- #

def test_watch_rebuilds_on_save_reports_changes_and_survives_errors(
        tmp_path, user_library, monkeypatch, capsys):
    script = _write(tmp_path / "build.py", """
        from m4l_builder import WARM, AudioEffect
        device = AudioEffect("Watched", 120, 100, theme=WARM)
        device.add_panel("bg", [0, 0, 120, 100])
        device.build("Watched.amxd")
    """)
    with_dial = script.read_text().replace(
        'device.build(',
        'device.add_dial("drive", "Drive", [10, 6, 50, 90])\ndevice.build(')
    edits = [with_dial, "raise RuntimeError('half-typed edit')\n"]

    def save_next_edit(_interval):
        if not edits:
            raise KeyboardInterrupt
        script.write_text(edits.pop(0))
        stat = script.stat()  # bump mtime even on coarse-timestamp filesystems
        os.utime(script, (stat.st_atime, stat.st_mtime + 5))

    monkeypatch.setattr(cli.time, "sleep", save_next_edit)
    assert main(["watch", str(script)]) == 0

    out = capsys.readouterr().out
    built = user_library / "Presets/Audio Effects/Max Audio Effect/Watched.amxd"
    assert built.is_file()
    assert out.count(f"built Watched -> {built}") == 2
    assert "+ boxes: drive" in out
    assert "+ parameter: Drive" in out
    assert "build failed: RuntimeError: half-typed edit" in out
    assert out.rstrip().endswith("stopped")
