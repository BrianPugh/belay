import time

import pytest

import belay
import belay.device


@pytest.fixture
def mock_pyboard_time(mocker):
    """Mock Pyboard for time synchronization tests."""
    # Simulate device returning incrementing time values (in milliseconds)
    device_time_ms = [42500]  # Starting device time in milliseconds

    def mock_exec_time(cmd, data_consumer=None):
        """Mock exec that handles time-related commands."""
        # Debug: print command to understand what's being sent
        # print(f"MOCK EXEC: {repr(cmd[:200])}")  # First 200 chars

        # Add small delay to simulate realistic execution time
        # This prevents RTT from being exactly zero on systems with
        # low time resolution (e.g., Windows where time.time() has ~15ms resolution)
        time.sleep(0.02)

        if "implementation" in cmd and "name" in cmd:
            # Return implementation info (no timing - _with_timing=False)
            data = b'_BELAYR||("micropython", (1, 19, 1), "rp2", None)\r\n'
        elif "__belay_ticks_add" in cmd or ("ticks_add" in cmd and "-1" in cmd):
            # Query for TICKS_MAX - matches both function calls and result
            data = b"_BELAYR||1073741823\r\n"  # MicroPython typical value (2^30 - 1)
        elif "__belay_timed_repr(__belay_monotonic())" in cmd:
            # Return current device time with dual timestamp format (in milliseconds)
            t1 = device_time_ms[0]
            device_time_ms[0] += 1  # Small increment for execution (1ms)
            t2 = device_time_ms[0]
            device_time_ms[0] += 1
            avg_time = (t1 + t2) // 2  # Integer average
            # Format: _BELAYR|{avg_time}|{result}
            data = f"_BELAYR|{avg_time}|{t2}\r\n".encode()
        elif "__belay_monotonic()" in cmd:
            # Direct call to __belay_monotonic() without timed wrapper (with_timing=False)
            t = device_time_ms[0]
            device_time_ms[0] += 1
            # Format: _BELAYR||{result} (no timestamp in response)
            data = f"_BELAYR||{t}\r\n".encode()
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
    """Test that with auto_sync disabled, time_offset is None until sync_time() is called."""
    # When auto_sync_time=False, no automatic synchronization occurs
    # _time_offset should be None until sync_time() is explicitly called
    assert device_no_auto_sync._time_sync.time_offset is None

    # After calling sync_time(), offset should be available
    device_no_auto_sync.sync_time()
    assert device_no_auto_sync.time_offset is not None
    assert isinstance(device_no_auto_sync.time_offset, float)


def test_auto_sync_enabled(device_with_auto_sync):
    """Test that auto sync works by default."""
    assert device_with_auto_sync.time_offset is not None


def test_manual_sync_time(device_no_auto_sync):
    """Test manual time synchronization."""
    device = device_no_auto_sync

    # Perform sync
    offset = device.sync_time(samples=5)

    # Offset should now be set
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


def test_conversion_without_sync_raises_error(device_no_auto_sync):
    """Test that accessing time_offset without sync raises an error."""
    device = device_no_auto_sync

    # time_offset should be None and raise ValueError when accessed
    # before sync_time() is called
    with pytest.raises(ValueError, match="Time synchronization has not been performed"):
        _ = device.time_offset


def test_time_offset_property(device_no_auto_sync):
    """Test the time_offset property."""
    device = device_no_auto_sync

    # Initially no offset when auto_sync_time=False
    assert device._time_sync.time_offset is None

    # After explicit sync, offset should be set
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


def test_tick_wrap_detection(device_no_auto_sync):
    """Test that wrap-around is detected using time-based prediction."""
    device = device_no_auto_sync

    # Set small TICKS_MAX for testing (TICKS_PERIOD = 101 ms)
    device._time_sync.ticks_max = 100

    # Simulate time progression with host time
    base_time = 1000.0  # Start at arbitrary host time

    # First reading establishes reference (95ms device time at t=1000.0)
    unwrapped1 = device._time_sync.unwrap_tick(95, base_time)
    assert unwrapped1 == 95

    # 2ms later: device at 97ms, host at t=1000.002
    unwrapped2 = device._time_sync.unwrap_tick(97, base_time + 0.002)
    assert unwrapped2 == 97

    # 11ms later: device wraps to 5ms (95+11=106, 106 mod 101 = 5)
    # Host at t=1000.011, expects device ~106ms
    unwrapped3 = device._time_sync.unwrap_tick(5, base_time + 0.011)
    assert unwrapped3 == 106  # 1 * 101 + 5 (implies wrap_count=1)

    # 5ms later: device at 10ms (wrapped), host at t=1000.016, expects ~111ms
    unwrapped4 = device._time_sync.unwrap_tick(10, base_time + 0.016)
    assert unwrapped4 == 111  # 1 * 101 + 10

    # 95ms later: device at 95ms (still in wrap 1)
    # From reference: 95 + 101 = 196ms expected
    unwrapped5 = device._time_sync.unwrap_tick(95, base_time + 0.101)
    assert unwrapped5 == 196  # 1 * 101 + 95

    # 8ms later: device wraps again to 2ms (196+8=204, 204 mod 101 = 2)
    # Host at t=1000.109, expects ~204ms
    unwrapped6 = device._time_sync.unwrap_tick(2, base_time + 0.109)
    assert unwrapped6 == 204  # 2 * 101 + 2 (implies wrap_count=2)


def test_device_reset_detection_via_time_prediction(device_no_auto_sync):
    """Test that device reset is detected via time-based prediction."""
    import pytest

    from belay.device_support import DeviceResetDetected

    device = device_no_auto_sync

    # Use full 32-bit range for realistic test
    device._time_sync.ticks_max = 0xFFFFFFFF

    # Establish reference at host time t=1000.0, device at 50000ms
    base_time = 1000.0
    unwrapped1 = device._time_sync.unwrap_tick(50000, base_time)
    assert unwrapped1 == 50000

    # 1 second later: device at 51000ms, host at t=1001.0
    # This should work normally
    unwrapped2 = device._time_sync.unwrap_tick(51000, base_time + 1.0)
    assert unwrapped2 == 51000

    # Now simulate device reset: 10 seconds pass on host (t=1011.0)
    # but device restarted and shows only 100ms
    # Expected device time would be ~60000ms, but actual is 100ms
    # No wrap count can make 100ms match 60000ms within drift tolerance
    # This should raise DeviceResetDetected exception
    with pytest.raises(DeviceResetDetected, match="Device reset detected"):
        device._time_sync.unwrap_tick(100, base_time + 11.0)

    # Verify state unchanged (exception prevents state modification)
    assert device._time_sync._reference_device_tick_unwrapped == 50000
    assert device._time_sync._reference_host_time == base_time

    # Now test that update_offset handles the reset properly
    device._time_sync.update_offset(100, base_time + 11.0)

    # After reset handling, reference should be re-established at device=100ms
    assert device._time_sync._reference_device_tick_unwrapped == 100
    assert device._time_sync._reference_host_time == base_time + 11.0

    # Verify normal progression continues after reset
    # 1 second later: device at 1100ms, host at t=1012.0
    unwrapped3 = device._time_sync.unwrap_tick(1100, base_time + 12.0)
    assert unwrapped3 == 1100


def test_reconnect_resets_wrap_tracking(device_no_auto_sync, mocker):
    """Test that reconnect() resets wrap tracking state."""
    device = device_no_auto_sync

    # Simulate some wrap tracking state
    device._time_sync._reference_host_time = 1000.0
    device._time_sync._reference_device_tick_unwrapped = 50000

    # Mock the actual reconnection to avoid needing real hardware
    mocker.patch.object(device, "_connect_to_board")

    # Reconnect should reset wrap tracking including reference points
    device.reconnect()

    assert device._time_sync._reference_host_time is None
    assert device._time_sync._reference_device_tick_unwrapped is None


def test_tick_arithmetic_no_wrap(device_no_auto_sync):
    """Test that normal tick progression (no wrap) works correctly."""
    device = device_no_auto_sync

    device._time_sync.ticks_max = 0xFFFFFFFF

    # Monotonically increasing ticks with corresponding host times
    base_time = 1000.0
    for tick in [100, 200, 300, 500, 1000, 5000]:
        # Simulate roughly 1:1 time progression (tick is in ms, add appropriate seconds)
        host_time = base_time + (tick / 1000.0)
        unwrapped = device._time_sync.unwrap_tick(tick, host_time)
        assert unwrapped == tick
