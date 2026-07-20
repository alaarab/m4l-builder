"""ParameterSpec build-time validation guards (turn silent runtime defects into
build errors). Added after the 100-agent scan flagged the missing checks.
"""
import pytest

from m4l_builder.parameters import ParameterSpec


def test_initial_above_maximum_raises():
    with pytest.raises(ValueError, match="above maximum"):
        ParameterSpec(name="Gain", minimum=-12.0, maximum=12.0, initial=20.0)


def test_initial_below_minimum_raises():
    with pytest.raises(ValueError, match="below minimum"):
        ParameterSpec(name="Gain", minimum=0.0, maximum=100.0, initial=-5.0)


def test_initial_list_form_is_checked():
    with pytest.raises(ValueError, match="above maximum"):
        ParameterSpec(name="Gain", minimum=0.0, maximum=6.0, initial=[100.0])


def test_initial_in_range_ok():
    ParameterSpec(name="Gain", minimum=-12.0, maximum=12.0, initial=3.0)


def test_allow_wide_range_bypasses_initial_check():
    ParameterSpec(name="Gain", minimum=0.0, maximum=6.0, initial=[100.0], allow_wide_range=True)


def test_exponent_must_be_positive():
    with pytest.raises(ValueError, match="exponent must be > 0"):
        ParameterSpec(name="Freq", exponent=0.0)
    with pytest.raises(ValueError, match="exponent must be > 0"):
        ParameterSpec(name="Freq", exponent=-1.0)
    ParameterSpec(name="Freq", exponent=3.0)  # positive is fine


def test_menu_duplicate_options_raise():
    with pytest.raises(ValueError, match="duplicate options"):
        ParameterSpec(name="Mode", parameter_type=2, enum=["A", "B", "A"])


def test_two_option_same_label_toggle_is_allowed():
    # the legitimate toggle pattern: one button label kept across both states
    ParameterSpec(name="Freeze", parameter_type=2, enum=["ON", "ON"])


def test_enumerated_initial_index_out_of_range_raises():
    with pytest.raises(ValueError, match="out of range"):
        ParameterSpec(name="Mode", parameter_type=2, enum=["A", "B", "C"], initial=[5])


def test_enumerated_initial_index_in_range_ok():
    ParameterSpec(name="Mode", parameter_type=2, enum=["A", "B", "C"], initial=[2])
