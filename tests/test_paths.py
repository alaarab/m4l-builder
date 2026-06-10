from pathlib import Path

import pytest

from m4l_builder.constants import DEVICE_TYPE_CODES
from m4l_builder.paths import _DEVICE_TYPE_SUBDIRS, device_output_path


@pytest.mark.parametrize(
    ("device_type", "subdir"),
    [
        ("audio_effect", "Presets/Audio Effects/Max Audio Effect"),
        ("instrument", "Presets/Instruments/Max Instrument"),
        ("midi_effect", "Presets/MIDI Effects/Max MIDI Effect"),
        ("note_transformation", "MIDI Tools/Max Transformations"),
        ("note_generator", "MIDI Tools/Max Generators"),
    ],
)
def test_device_output_path_per_device_type(tmp_path, monkeypatch, device_type, subdir):
    monkeypatch.setenv("M4L_USER_LIBRARY", str(tmp_path / "User Library"))

    output = device_output_path("Probe", device_type)

    expected = tmp_path / "User Library" / Path(subdir) / "Probe.amxd"
    assert Path(output) == expected
    assert expected.parent.is_dir()


def test_midi_tool_paths_live_outside_presets(tmp_path, monkeypatch):
    monkeypatch.setenv("M4L_USER_LIBRARY", str(tmp_path / "User Library"))

    for device_type in ("note_transformation", "note_generator"):
        output = device_output_path("Tool", device_type)
        assert "Presets" not in Path(output).parts
        assert "MIDI Tools" in Path(output).parts


def test_device_output_path_rejects_unknown_device_type(tmp_path, monkeypatch):
    monkeypatch.setenv("M4L_USER_LIBRARY", str(tmp_path / "User Library"))

    with pytest.raises(ValueError, match="note_generator"):
        device_output_path("Bogus", "drum_rack")


def test_subfolder_under_midi_tool_type(tmp_path, monkeypatch):
    monkeypatch.setenv("M4L_USER_LIBRARY", str(tmp_path / "User Library"))

    output = device_output_path("Gen", "note_generator", subfolder="_Debug")

    expected = (
        tmp_path
        / "User Library"
        / "MIDI Tools"
        / "Max Generators"
        / "_Debug"
        / "Gen.amxd"
    )
    assert Path(output) == expected


def test_device_type_subdirs_cover_all_device_type_codes():
    assert set(_DEVICE_TYPE_SUBDIRS) == set(DEVICE_TYPE_CODES)


def test_device_output_path_supports_relative_subfolder(tmp_path, monkeypatch):
    monkeypatch.setenv("M4L_USER_LIBRARY", str(tmp_path / "User Library"))

    output = device_output_path("Linear Phase EQ Probe", subfolder="_Debug")

    expected = (
        tmp_path
        / "User Library"
        / "Presets"
        / "Audio Effects"
        / "Max Audio Effect"
        / "_Debug"
        / "Linear Phase EQ Probe.amxd"
    )
    assert Path(output) == expected
    assert expected.parent.is_dir()


@pytest.mark.parametrize("subfolder", ["/tmp/escape", "../escape", "_Debug/../../escape"])
def test_device_output_path_rejects_unsafe_subfolders(tmp_path, monkeypatch, subfolder):
    monkeypatch.setenv("M4L_USER_LIBRARY", str(tmp_path / "User Library"))

    with pytest.raises(ValueError):
        device_output_path("Unsafe", subfolder=subfolder)
