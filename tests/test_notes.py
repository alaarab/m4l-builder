import json

import pytest

from m4l_builder import NoteEvent, notes_dict


def test_to_dict_required_fields_only():
    note = NoteEvent(pitch=60, start_time=0.0, duration=1.0)

    assert note.to_dict() == {"pitch": 60, "start_time": 0.0, "duration": 1.0}


def test_to_dict_includes_set_optionals():
    note = NoteEvent(
        pitch=64,
        start_time=0.5,
        duration=0.25,
        velocity=100.0,
        probability=0.75,
        velocity_deviation=-10.0,
        release_velocity=64.0,
        mute=1,
    )

    assert note.to_dict() == {
        "pitch": 64,
        "start_time": 0.5,
        "duration": 0.25,
        "velocity": 100.0,
        "probability": 0.75,
        "velocity_deviation": -10.0,
        "release_velocity": 64.0,
        "mute": 1,
    }


def test_to_dict_omits_unset_optionals_individually():
    note = NoteEvent(pitch=60, start_time=0.0, duration=1.0, velocity=90.0)

    result = note.to_dict()
    assert result["velocity"] == 90.0
    for key in ("probability", "velocity_deviation", "release_velocity", "mute"):
        assert key not in result


@pytest.mark.parametrize(
    "kwargs",
    [
        {"pitch": -1},
        {"pitch": 128},
        {"pitch": 60.0},
        {"pitch": True},
        {"start_time": -0.1},
        {"duration": 0.0},
        {"duration": -1.0},
        {"velocity": -1.0},
        {"velocity": 128.0},
        {"probability": -0.1},
        {"probability": 1.1},
        {"velocity_deviation": -128.0},
        {"velocity_deviation": 128.0},
        {"release_velocity": 200.0},
        {"mute": 2},
    ],
)
def test_note_event_validation(kwargs):
    fields = {"pitch": 60, "start_time": 0.0, "duration": 1.0}
    fields.update(kwargs)

    with pytest.raises(ValueError):
        NoteEvent(**fields)


def test_notes_dict_with_events_and_mappings():
    result = notes_dict(
        [
            NoteEvent(pitch=60, start_time=0.0, duration=1.0),
            {"pitch": 67, "start_time": 1.0, "duration": 0.5, "velocity": 80.0},
        ]
    )

    assert result == {
        "notes": [
            {"pitch": 60, "start_time": 0.0, "duration": 1.0},
            {"pitch": 67, "start_time": 1.0, "duration": 0.5, "velocity": 80.0},
        ]
    }


def test_notes_dict_empty():
    assert notes_dict([]) == {"notes": []}


def test_notes_dict_rejects_mapping_missing_required_keys():
    with pytest.raises(ValueError, match="start_time"):
        notes_dict([{"pitch": 60, "duration": 1.0}])


def test_notes_dict_rejects_non_note_values():
    with pytest.raises(TypeError):
        notes_dict([42])


def test_notes_dict_copies_mappings():
    source = {"pitch": 60, "start_time": 0.0, "duration": 1.0}

    result = notes_dict([source])
    result["notes"][0]["pitch"] = 72

    assert source["pitch"] == 60


def test_notes_dict_round_trips_through_json():
    payload = notes_dict(
        [NoteEvent(pitch=60, start_time=0.0, duration=1.0, probability=0.5)]
    )

    assert json.loads(json.dumps(payload)) == payload
