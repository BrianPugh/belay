import csv
import statistics
import time
from pathlib import Path
from typing import Annotated, Optional

from cyclopts import Parameter

from belay import Device
from belay.cli.common import PasswordStr, PortStr


def latency(
    port: PortStr,
    *,
    password: PasswordStr = "",
    count: Annotated[int, Parameter(alias="-c")] = 10,
    verbose: Annotated[bool, Parameter(alias="-v")] = False,
    output: Annotated[Optional[Path], Parameter(alias="-o")] = None,
    with_timing: Annotated[bool, Parameter(alias="-t", negative=("--no-with-timing", "--without-timing"))] = True,
):
    """Measure round-trip latency between host and device.

    Performs multiple round-trip measurements and reports statistics.

    Parameters
    ----------
    count : int
        Number of round-trip measurements to perform.
    verbose : bool
        Show individual measurements in addition to statistics.
    output : Path, optional
        Export individual latency measurements to a CSV file.
    with_timing: bool
        With the additional per-call time synchronization logic.
    """
    device = Device(port, password=password, auto_sync_time=with_timing)

    latencies = []
    if verbose:
        print(f"Measuring latency with {count} iterations...")

    for i in range(count):
        start = time.perf_counter()
        device("0")  # Short, no-op statement
        end = time.perf_counter()
        latency_ms = (end - start) * 1000
        latencies.append(latency_ms)
        if verbose:
            print(f"  {i + 1:2d}: {latency_ms:6.2f} ms")

    # Calculate statistics
    min_latency = min(latencies)
    max_latency = max(latencies)
    avg_latency = statistics.mean(latencies)
    median_latency = statistics.median(latencies)
    stdev_latency = statistics.stdev(latencies) if len(latencies) > 1 else 0.0

    if verbose:
        print()
    print(f"Statistics ({count} samples):")
    print(f"  Min:     {min_latency:6.2f} ms")
    print(f"  Max:     {max_latency:6.2f} ms")
    print(f"  Average: {avg_latency:6.2f} ms")
    print(f"  Median:  {median_latency:6.2f} ms")
    print(f"  Std Dev: {stdev_latency:6.2f} ms")

    # Export to CSV if requested
    if output is not None:
        with output.open("w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["latency_ms"])
            for latency_ms in latencies:
                writer.writerow([f"{latency_ms:.2f}"])

    device.close()
