import csv
from pathlib import Path

from belay.cli.main import app
from tests.conftest import run_cli


def test_latency_verbose(mocker, mock_device, capsys):
    mock_device.patch("belay.cli.latency.Device")
    exit_code = run_cli(app, ["latency", "/dev/ttyUSB0", "--password", "password", "--count", "3", "--verbose"])
    assert exit_code == 0
    mock_device.cls_assert_common()
    captured = capsys.readouterr()
    # Check that we got output with the expected format
    assert "Measuring latency with 3 iterations" in captured.out
    assert "Statistics (3 samples)" in captured.out
    assert "Min:" in captured.out
    assert "Max:" in captured.out
    assert "Average:" in captured.out
    assert "Median:" in captured.out
    assert "Std Dev:" in captured.out
    # Should have 3 measurement lines
    assert captured.out.count(" ms\n") >= 8  # 3 measurements + 5 stats


def test_latency_non_verbose(mocker, mock_device, capsys):
    mock_device.patch("belay.cli.latency.Device")
    exit_code = run_cli(app, ["latency", "/dev/ttyUSB0", "--password", "password", "--count", "3"])
    assert exit_code == 0
    mock_device.cls_assert_common()
    captured = capsys.readouterr()
    # Should NOT show "Measuring latency" message in non-verbose mode
    assert "Measuring latency" not in captured.out
    # Should show statistics
    assert "Statistics (3 samples)" in captured.out
    assert "Min:" in captured.out
    assert "Max:" in captured.out
    assert "Average:" in captured.out
    assert "Median:" in captured.out
    assert "Std Dev:" in captured.out
    # Should only have 5 stats lines, no individual measurements
    assert captured.out.count(" ms\n") == 5  # Only 5 stats, no individual measurements


def test_latency_default_count(mocker, mock_device, capsys):
    mock_device.patch("belay.cli.latency.Device")
    exit_code = run_cli(app, ["latency", "/dev/ttyUSB0", "--password", "password"])
    assert exit_code == 0
    captured = capsys.readouterr()
    # Default count should be 10
    assert "Statistics (10 samples)" in captured.out
    # Should NOT show "Measuring latency" in non-verbose mode
    assert "Measuring latency" not in captured.out


def test_latency_export_csv(mocker, mock_device, capsys, tmp_path):
    mock_device.patch("belay.cli.latency.Device")
    output_file = tmp_path / "latency.csv"
    exit_code = run_cli(
        app, ["latency", "/dev/ttyUSB0", "--password", "password", "--count", "5", "--output", str(output_file)]
    )
    assert exit_code == 0
    mock_device.cls_assert_common()

    # Check that the file was created
    assert output_file.exists()

    # Read and verify CSV contents
    with output_file.open("r") as csvfile:
        reader = csv.reader(csvfile)
        rows = list(reader)

    # Should have header + 5 data rows
    assert len(rows) == 6
    assert rows[0] == ["latency_ms"]

    # Verify each row has correct format (just the latency value)
    for row in rows[1:]:
        assert len(row) == 1  # Only one column
        # Check that latency_ms is a valid float string
        assert float(row[0]) >= 0
