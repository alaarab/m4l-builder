from pathlib import Path

import pytest

from m4l_builder.paths import device_output_path


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
