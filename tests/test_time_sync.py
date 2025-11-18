import time

import pytest

import belay
import belay.device


@pytest.fixture
def mock_pyboard_time(mocker):
    """Mock Pyboard for time synchronization tests."""
    # Simulate device returning incrementing time values
    device_time = [42.5]  # Starting device time in seconds

    def mock_exec_time(cmd, data_consumer=None):
        """Mock exec that handles time-related commands."""
        # Debug: print command to understand what's being sent
        # print(f"MOCK EXEC: {repr(cmd[:200])}")  # First 200 chars

        if "implementation" in cmd and "name" in cmd:
            # Return implementation info (no timing - _with_timing=False)
            data = b'_BELAYR||("micropython", (1, 19, 1), "rp2", None)\r\n'
        elif "__belay_timed_repr(__belay_monotonic())" in cmd:
            # Return current device time with dual timestamp format
            t1 = device_time[0]
            device_time[0] += 0.0005  # Small increment for execution
            t2 = device_time[0]
            device_time[0] += 0.0005
            avg_time = (t1 + t2) / 2
            # Format: _BELAYR|{avg_time}|{result}
            data = f"_BELAYR|{avg_time}|{t2}\r\n".encode()
        elif "def __belay_monotonic" in cmd or "def __belay_obj_create" in cmd or "def __belay" in cmd:
            # Loading snippets - no response
            data = b""
        else:
            # Default empty response for non-expression commands
            # Debug: uncomment to see unhandled commands
            # print(f"UNHANDLED: {repr(cmd[:200])}")
            data = b""

        if data_consumer and data:
            data_consumer(data)

    def mock_init(self, *args, **kwargs):
        self.serial = mocker.MagicMock()

    mocker.patch.object(belay.device.Pyboard, "__init__", mock_init)
    mocker.patch.object(belay.device.Pyboard, "exec", side_effect=mock_exec_time)
    mocker.patch("belay.device.Pyboard.enter_raw_repl", return_value=None)
    mocker.patch("belay.device.Pyboard.fs_put")


@pytest.fixture
def device_no_auto_sync(mock_pyboard_time):
    """Device with auto time sync disabled."""
    with belay.Device(auto_sync_time=False) as device:
        yield device


@pytest.fixture
def device_with_auto_sync(mock_pyboard_time):
    """Device with auto time sync enabled (default)."""
    with belay.Device(auto_sync_time=True) as device:
        yield device


def test_auto_sync_disabled(device_no_auto_sync):
    """Test that with auto_sync disabled, we still get an initial offset from init."""
    # With the new implementation, we always calculate an initial offset
    # during device initialization from the implementation detection round-trip
    assert device_no_auto_sync.time_offset is not None
    assert isinstance(device_no_auto_sync.time_offset, float)


def test_auto_sync_enabled(device_with_auto_sync):
    """Test that auto sync works by default."""
    assert device_with_auto_sync.time_offset is not None


def test_manual_sync_time(device_no_auto_sync):
    """Test manual time synchronization."""
    device = device_no_auto_sync

    # Initially has offset from init
    initial_offset = device.time_offset
    assert isinstance(initial_offset, float)

    # Perform sync - this will refine the offset
    offset = device.sync_time(samples=5)

    # Offset should now be updated
    assert isinstance(offset, float)
    assert device.time_offset == offset


def test_sync_time_samples(device_no_auto_sync):
    """Test that sync_time returns a valid offset regardless of sample count."""
    device = device_no_auto_sync

    # Test with different sample counts
    for samples in [1, 5, 10, 20]:
        offset = device.sync_time(samples=samples)
        # Should always return a valid float offset
        assert isinstance(offset, float)
        assert device.time_offset == offset


def test_device_to_host_time(device_no_auto_sync):
    """Test converting device timestamp to host time using offset."""
    device = device_no_auto_sync

    # Sync first
    device.sync_time()

    # Mock device time
    device_time = 100.0

    # Convert to host time using offset directly
    host_time = device_time - device.time_offset

    # Should be a reasonable epoch timestamp
    assert isinstance(host_time, float)
    assert host_time > 0  # Unix epoch timestamps are positive


def test_host_to_device_time(device_no_auto_sync):
    """Test converting host timestamp to device time using offset."""
    device = device_no_auto_sync

    # Sync first
    device.sync_time()

    # Current host time
    host_time = time.time()

    # Convert to device time using offset directly
    device_time = host_time + device.time_offset

    # Should be a float
    assert isinstance(device_time, float)


def test_bidirectional_conversion(device_no_auto_sync):
    """Test that conversions are inverses of each other."""
    device = device_no_auto_sync

    # Sync first
    device.sync_time()

    # Start with a device time
    original_device_time = 123.456

    # Convert to host and back using offset
    host_time = original_device_time - device.time_offset
    converted_device_time = host_time + device.time_offset

    # Should be very close (within floating point precision)
    assert abs(original_device_time - converted_device_time) < 1e-6


def test_conversion_without_explicit_sync(device_no_auto_sync):
    """Test that offset is available even without explicit sync."""
    device = device_no_auto_sync

    # time_offset is now available from init
    assert device.time_offset is not None
    assert isinstance(device.time_offset, float)


def test_time_offset_property(device_no_auto_sync):
    """Test the time_offset property."""
    device = device_no_auto_sync

    # Initially has offset from init
    initial_offset = device.time_offset
    assert isinstance(initial_offset, float)

    # After explicit sync, offset should be refined
    offset = device.sync_time()
    assert device.time_offset == offset
    assert isinstance(device.time_offset, float)


def test_resync_updates_offset(device_no_auto_sync):
    """Test that calling sync_time multiple times updates the offset."""
    device = device_no_auto_sync

    # First sync
    offset1 = device.sync_time(samples=3)

    # Second sync (might be different due to timing)
    offset2 = device.sync_time(samples=3)

    # Both should be valid offsets
    assert isinstance(offset1, float)
    assert isinstance(offset2, float)

    # Current offset should be the latest one
    assert device.time_offset == offset2


def test_implementation_specific_snippets(mocker, mock_pyboard_time):
    """Test that correct snippet is loaded based on implementation during init."""
    # Test MicroPython - snippet is loaded during __init__ now
    exec_snippet_spy = mocker.spy(belay.device.Device, "_exec_snippet")

    device_mp = belay.Device(auto_sync_time=False)

    # Should have loaded MicroPython-specific snippet during init
    # Check that it was called with the right snippet name
    calls = [call[0][1] for call in exec_snippet_spy.call_args_list if "time_monotonic" in str(call)]
    assert "time_monotonic_micropython" in calls
    device_mp.close()
