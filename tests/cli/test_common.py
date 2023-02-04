import pytest

from belay.cli.common import confirm_action


@pytest.mark.parametrize("input_str", ["yes", "YES", "y"])
def test_confirm_action_yes(input_str, mocker):
    mocker.patch("belay.cli.common.input", return_value=input_str)
    assert confirm_action() is True


@pytest.mark.parametrize("input_str", ["no", "NO", "n"])
def test_confirm_action_no(input_str, mocker):
    mocker.patch("belay.cli.common.input", return_value=input_str)
    assert confirm_action() is False


@pytest.mark.parametrize("input_str", ["foo", "ye"])
def test_confirm_action_invalid(input_str, mocker):
    mock_input = mocker.patch("belay.cli.common.input", side_effect=[input_str, "yes"])
    assert confirm_action() is True
    assert len(mock_input.call_args_list) == 2
