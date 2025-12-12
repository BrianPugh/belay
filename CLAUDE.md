# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Code Style Preferences

- **Minimum Python version is 3.9**. Use native generic types (`list[str]`, `dict[str, int]`) instead of importing from `typing`. However, `Optional[X]` still requires `from typing import Optional` since `X | None` syntax requires Python 3.10+.

- **Data class libraries: Use `attrs` or `pydantic`, never `dataclasses`.**
  - **pydantic (`BaseModel`)**: Use for configuration parsing, external input validation, and serialization (e.g., parsing `pyproject.toml`, user-provided config). Leverage validators, `model_dump()`, and `Field()` for these use cases.
  - **attrs (`@define`)**: Use for internal data structures that don't need validation. Use `field()` for advanced options like `factory`, `converter`, or `init=False`. Prefer `field(factory=...)` over `Factory(...)`.
  - **Do not use `@dataclass`** from the standard library. Convert any existing `@dataclass` to `@define` from attrs.

  ```python
  # Good - attrs for internal data structures
  from attrs import define, field


  @define
  class Implementation:
      name: str
      version: tuple[int, int, int] = (0, 0, 0)
      arch: Optional[str] = field(default=None, converter=_arch_converter)
      files: list[str] = field(factory=list)
      id: int = field(factory=lambda: next(_counter), init=False)


  # Good - pydantic for config/external input
  from pydantic import BaseModel, field_validator


  class BelayConfig(BaseModel):
      name: Optional[str] = None
      dependencies: dict[str, DependencyList] = {}

      @field_validator("dependencies", mode="before")
      @classmethod
      def preprocess(cls, v):
          return _preprocess(v)


  # Bad - don't use dataclasses
  from dataclasses import dataclass


  @dataclass  # Don't do this
  class MyData:
      value: str
  ```

---

# Belay Architecture Overview

This document describes the high-level architecture of the Belay codebase, which provides a Python framework for controlling MicroPython and CircuitPython devices over various communication channels (serial, telnet, WebREPL, etc.).

## Table of Contents

1. [Common Development Commands](#common-development-commands)
2. [Core Architecture](#core-architecture)
3. [Main Components](#main-components)
4. [Device Decorators & Executors](#device-decorators--executors)
5. [Communication Layer](#communication-layer)
6. [Code Synchronization](#code-synchronization)
7. [Package Manager](#package-manager)
8. [CLI Structure](#cli-structure)
9. [Key Abstractions](#key-abstractions)
10. [Testing](#testing)

---

## Common Development Commands

This project uses Poetry for dependency management.

### Setup

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell
# Or use prefix for each command:
poetry run <command>
```

### Running Tests

```bash
# Run unit tests only (fast)
poetry run python -m pytest tests

# Run with coverage
poetry run python -m pytest --cov=belay --cov-report=term --cov-report=xml tests

# Run unit + integration tests (requires emulated device)
poetry run python -m pytest --network tests tests/integration

# Run a single test file
poetry run python -m pytest tests/test_device.py

# Run a single test
poetry run python -m pytest tests/test_device.py::test_function_name

# Run with verbose output
poetry run python -m pytest tests -v
```

**Note:** Integration tests use rp2040js emulator and are skipped on Windows by default. Tests use the `--max-runs=3` (flaky) and `--timeout=240` flags automatically.

### Linting and Formatting

```bash
# Run pre-commit hooks manually
poetry run pre-commit run --all-files

# Install pre-commit hooks
poetry run pre-commit install

# Format code with black
poetry run black belay

# Lint with ruff
poetry run ruff check belay

# Auto-fix ruff issues
poetry run ruff check --fix belay
```

### Building Documentation

```bash
# Build HTML docs
poetry run sphinx-build -b html docs/source/ docs/build/html
```

### Integration Tests (Docker)

```bash
# Build Docker image for integration testing
make integration-build

# Run integration tests
make integration-test

# Interactive bash in Docker container
make integration-bash
```

---

## Core Architecture

### Design Philosophy

Belay is a remote code execution framework that bridges the Python host (e.g., a laptop) with a MicroPython/CircuitPython device over a serial or network connection. The key architectural principle is that users define functions and methods on the host, which are then executed on the device.

**Main entry point:** `/Users/brianpugh/projects/belay/belay/__init__.py`
- Exports: `Device`, `DeviceMeta`, `ProxyObject`, and various exceptions

### Execution Flow

```
Host Code → Belay Device Object → Executor → Pyboard → Serial/Network → Device REPL → Return Value
```

The flow involves:
1. User defines functions decorated with `@device.task`, `@device.setup`, etc.
2. Belay extracts the source code and sends it to the device
3. Pyboard communicates via serial/network protocols
4. Code executes on-device in MicroPython/CircuitPython REPL
5. Results are returned and parsed on the host

---

## Main Components

### 1. Device Class

**File:** `/Users/brianpugh/projects/belay/belay/device.py` (927 lines)

The central class for interacting with a remote MicroPython device.

**Key responsibilities:**
- Manages connection to the device via Pyboard
- Provides decorator-based interfaces (`@task`, `@setup`, `@teardown`, `@thread`)
- Executes arbitrary Python code on-device via `device(code)`
- Handles file synchronization (`sync()`, `sync_dependencies()`)
- Manages device state (implementation details, emitters, etc.)

**Key methods:**
- `__init__()` - Connects to device, detects implementation (MicroPython/CircuitPython), initializes executors
- `__call__(cmd, minify=True, record=True, trusted=False)` - Execute code on-device
- `setup()`, `teardown()`, `task()`, `thread()` - Decorator factories for defining on-device functions
- `sync()` - Synchronize local files/folders to device filesystem
- `sync_dependencies()` - Sync bundled dependencies to device
- `proxy(name)` - Create a ProxyObject for remote object interaction
- `close()` - Clean up connection and run teardown functions
- `reconnect()` - Reconnect and replay command history
- `soft_reset()` - Reset device while preserving state

**Lifecycle hooks (for subclassing):**
- `__pre_autoinit__()` - Called before `@Device.setup(autoinit=True)` methods; ideal for syncing dependencies
- `__post_init__()` - Called after `@Device.setup(autoinit=True)` methods; ideal for setting host attributes based on device state

**Device State Detection:**

Device detects implementation at initialization:
- name: "micropython" or "circuitpython"
- version: (major, minor, patch)
- platform: Board identifier ("rp2", "esp32", etc.)
- arch: CPU architecture ("armv7em", "xtensa", "rv32imc", etc.)
- emitters: Available code emitters ("native", "viper")

#### Device.setup()

Executes code in global context on-device when called (or at init if `autoinit=True`).

```python
@Device.setup(autoinit=True)
def my_setup():
    from machine import Pin

    led = Pin(25, Pin.OUT)
```

Features:
- Function body executed in global context
- Arguments set as global variables
- Returns `None`
- `autoinit=True` runs automatically during `__init__`
- `implementation="circuitpython"` allows board-specific versions

#### Device.task()

Sends function source code to device at decoration time. Calling executes it on-device.

```python
@device.task
def blink(times):
    for i in range(times):
        led.value(1)
        sleep(0.5)
        led.value(0)
        sleep(0.5)
```

Features:
- Source code sent during decoration (not execution)
- Supports generators for streaming data
- `trusted=True` allows eval'd return values (security risk)
- `minify=True` reduces transmission size
- Efficient for frequently-called functions

#### Device.teardown()

Executes code in global context when `device.close()` is called.

```python
@device.teardown
def cleanup():
    led.value(0)  # Turn off LED on exit
```

Features:
- No arguments allowed
- Automatic cleanup on exit
- Useful for resource cleanup, logging

#### Device.thread()

Spawns an on-device thread using `_thread.start_new_thread()`.

```python
@device.thread
def background_task():
    while True:
        # Do something in background
        sleep(1)
```

**Limitations:**
- CircuitPython doesn't support threading
- Only MicroPython supported

### 2. DeviceMeta Metaclass

**File:** `/Users/brianpugh/projects/belay/belay/device_meta.py` (118 lines)

Custom metaclass enabling method overloading by implementation and executor type.

**Key features:**
- `OverloadDict` - Allows multiple definitions of same method name
- `ExecuterMethod` - Descriptor that selects correct implementation at runtime
- Method resolution order (MRO) manipulation to place Device last

**Usage pattern:**
```python
class MyDevice(Device):
    @Device.setup
    def init_micropython():
        # MicroPython-specific setup
        pass

    @Device.setup(implementation="circuitpython")
    def init_circuitpython():
        # CircuitPython-specific setup
        pass
```

The metaclass ensures the correct method is chosen based on `device.implementation.name`.

### 3. Executor Classes

**File:** `/Users/brianpugh/projects/belay/belay/executers.py` (226 lines)

Four executor types manage different execution patterns:

**SetupExecuter:** Executes function body in global context.
- Arguments become global variables
- No return value
- `autoinit=True` runs during Device initialization

**TaskExecuter:** Sends function source to device at decoration time.
- Minimal overhead on invocation (just function call)
- Supports generators via helper functions
- Returns parsed results from device

**TeardownExecuter:** Executes at device close/exit.
- No arguments allowed
- Resource cleanup use case

**ThreadExecuter:** Spawns background threads using `_thread.start_new_thread()`.
- MicroPython only (CircuitPython raises `FeatureUnavailableError`)
- Fire-and-forget execution

All executors:
- Use `Registry` pattern for discovery
- Store source code with `getsource()` for inspection
- Apply minification to reduce transmission size
- Track execution via `__belay__` metadata

### 4. Device Support

**File:** `/Users/brianpugh/projects/belay/belay/device_support.py` (91 lines)

Contains implementation detection and method metadata:

```python
@define
class Implementation:
    name: str  # "micropython" or "circuitpython"
    version: Tuple[int, int, int]  # semantic version
    platform: str  # "rp2", "esp32", etc.
    arch: Optional[str]  # x64, armv7em, xtensa, rv32imc, etc.
    emitters: Tuple[str, ...]  # ("native", "viper") or ()
```

`MethodMetadata` - Stores decorator info for later binding:
- `executer` - Which executor class to use
- `kwargs` - Decorator kwargs (minify, register, etc.)
- `autoinit` - Run automatically during init
- `implementation` - Board implementation filter
- `id` - Global monotonic ID for execution ordering

---

## Device Decorators & Executors

### Decorator System Overview

Belay uses a sophisticated decorator system combining:
1. **Source code extraction** - `getsource()` from `inspect.py`
2. **Code minification** - `minify_code()` to reduce size
3. **Execution tracking** - Recording commands for reconnection
4. **Metadata attachment** - `__belay__` attribute on functions

### Source Code Extraction

**File:** `/Users/brianpugh/projects/belay/belay/inspect.py` (132 lines)

The `getsource()` function:
- Strips decorators from function definition
- Removes leading indentation
- Optionally strips function signature
- Returns: (code_string, line_number, file_path)

### Code Minification

**File:** `/Users/brianpugh/projects/belay/belay/_minify.py`

Reduces Python code size for transmission:
- Removes comments
- Strips unnecessary whitespace
- Preserves syntax validity
- Applied to all code by default (`minify=True`)

### Execution Recording

Device maintains `_cmd_history` for reconnection:
- Limited to 1000 commands (`MAX_CMD_HISTORY_LEN`)
- Replayed automatically on `reconnect()`
- Allows recovery from device disconnections
- Can be disabled with `record=False`

### Parser - parse_belay_response()

Responses from device are tagged with `_BELAY` prefix:
- `_BELAYR{id}|{value}` - Return result with optional proxy object ID
  - Empty ID (`_BELAYR|{value}`): Normal expression result
  - ID present (`_BELAYR{id}|`): Proxy object stored as `__belay_obj_{id}`
- `_BELAYS` - StopIteration (for generators)

Results are parsed with:
- Default: `ast.literal_eval()` (safe)
- With `trusted=True`: `eval()` (accepts any repr'd Python object)

---

## Communication Layer

### Pyboard

**File:** `/Users/brianpugh/projects/belay/belay/pyboard.py` (686 lines)

Low-level abstraction for device communication.

**Responsibilities:**
- Manage serial/network connection
- Handle raw REPL protocol
- Buffer management for reliable reads
- Data consumer callbacks for streaming

**Supported connection types:**

1. **Serial (USB):** `/dev/ttyUSB0`, `COM3`, etc. - Standard serial with configurable baudrate
2. **Network (Telnet):** `192.168.1.1:23` - IP address with optional port and authentication
3. **WebREPL:** `ws://192.168.1.1:8266` - WebSocket protocol
4. **Process (Emulation):** `exec:/path/to/micropython` - Spawn local process

**Device Detection (UsbSpecifier):**
- Auto-detection of connected devices
- Filtering by serial number, VID/PID, etc.
- Environment variable: `BELAY_DEVICE` (JSON format)

### Raw REPL Protocol

Pyboard implements MicroPython's raw REPL mode:

**Sequence:**
1. Enter raw REPL: Send Ctrl-A (0x01)
2. Send code with paste mode or raw exec
3. Read until `OK` marker
4. Exit raw REPL: Send Ctrl-B (0x02)

**Paste Mode (large code):**
- Used automatically for code > threshold
- Handles chunking and backpressure

**Data Consumer Pattern:**
```python
def data_consumer(data):
    # Called immediately as data arrives
    process(data)


board.exec(cmd, data_consumer=data_consumer)
```

---

## Code Synchronization

### File Sync Architecture

**Files:** `/Users/brianpugh/projects/belay/belay/device.py` (sync method) + `device_sync_support.py`

The `sync()` method intelligently synchronizes files:

**Algorithm:**
1. **Discovery** - Enumerate local files/directories
2. **Ignore patterns** - Filter with .gitignore-style patterns
3. **Hash comparison** - Compute FNV1a32 hashes on both sides
4. **Delta transfer** - Only send changed files
5. **Cleanup** - Delete remote files not in local directory

**Hash Functions:**

Multiple implementations (in order of preference):
1. **Pre-compiled native module** - `fnv1a32.mpy` (fastest)
   - Architecture-specific: `mpy1.22-armv7em.mpy`, etc.

2. **Viper emitter** - Native JIT compilation

3. **Native emitter** - Python native code

4. **Pure Python** - Basic implementation (slowest)

**On-device Snippets**

**File:** `/Users/brianpugh/projects/belay/belay/snippets/`

Pre-written MicroPython code snippets:

- `sync_begin.py` - Setup functions for sync
- `hf.py`, `hf_native.py`, `hf_viper.py`, `hf_nativemodule.py` - Hash implementations
- `ilistdir_micropython.py`, `ilistdir_circuitpython.py` - Directory iteration
- `convenience_imports_*.py` - Standard imports on startup
- `emitter_check.py` - Detect available emitters

**Sync Parameters:**

```python
device.sync(
    folder,  # Local path
    dst="/",  # Remote destination
    keep=None,  # Files to preserve
    ignore=None,  # Patterns to skip
    minify=True,  # Minify .py files
    mpy_cross_binary=None,  # Path to mpy-cross for compilation
    progress_update=None,  # Callback for progress
)
```

**Device Sync Support**

**File:** `/Users/brianpugh/projects/belay/belay/device_sync_support.py`

- `discover_files_dirs()` - Enumerate files/directories with ignore patterns
- `preprocess_keep()` - Normalize keep list
- `preprocess_ignore()` - Normalize ignore patterns
- `preprocess_src_file()` - Minify or compile .py files
- `preprocess_src_file_hash()` - Compute file hash
- `generate_dst_dirs()` - Calculate remote directory structure

---

## Key Abstractions

### ProxyObject

**File:** `/Users/brianpugh/projects/belay/belay/proxy_object.py` (101 lines)

Enables interacting with remote Python objects as if they were local.

**Usage:**
```python
@device.setup
def setup():
    class MyClass:
        def __init__(self, value):
            self.value = value

        def get_value(self):
            return self.value

    obj = MyClass(42)


setup()

# Create proxy for remote object
obj = device.proxy("obj")
value = obj.value  # Get attribute
result = obj.get_value()  # Call method
obj.value = 100  # Set attribute
```

**Implementation:**
- `__getattribute__()` - Access attributes/methods
- `__setattr__()` - Set attributes
- `__getitem__()` - Indexing support
- `__len__()` - Length support
- `__call__()` - Function/method invocation

All operations go through `device()` call with string expressions.

---

## Package Manager

### Configuration

**File:** `/Users/brianpugh/projects/belay/belay/packagemanager/`

The package manager handles dependency groups defined in `pyproject.toml`.

**Config Schema:**

```toml
[tool.belay]
name = "myapp"
dependencies_path = ".belay/dependencies"

[tool.belay.dependencies]
requests = "https://github.com/user/requests/archive/main.zip"

[tool.belay.group.dev]
optional = true

[tool.belay.group.dev.dependencies]
pytest = "https://github.com/pytest-dev/pytest/archive/main.zip"
```

**Models**

**File:** `/Users/brianpugh/projects/belay/belay/packagemanager/models.py` (155 lines)

- `DependencySourceConfig` - Individual dependency specification
- `GroupConfig` - Group of dependencies with metadata
- `BelayConfig` - Project-level configuration
- Pydantic validation for all fields

**Group Management**

**File:** `/Users/brianpugh/projects/belay/belay/packagemanager/group.py` (179 lines)

```python
class Group:
    def __init__(self, name: str, **kwargs): ...
    def download(packages=None, console=None): ...
    def clean(self): ...  # Remove unspecified dependencies
    def copy_to(self, dst): ...  # Stage for sync
```

Features:
- Download dependencies from various sources
- Verify downloaded files (AST parsing for .py files)
- Support for "develop" mode (local editable dependencies)
- `rename_to_init` flag for single-file packages

**Downloaders**

**File:** `/Users/brianpugh/projects/belay/belay/packagemanager/downloaders/`

- GitHub releases/archives
- Direct file URLs
- Local filesystem

---

## CLI Structure

### Main Entry

**File:** `/Users/brianpugh/projects/belay/belay/cli/main.py` (105 lines)

Built with Cyclopts.

**Commands:**
1. **sync** - Synchronize files to device
2. **exec** - Execute single statement
3. **run** - Execute Python file
4. **terminal** - Interactive REPL
5. **info** - Device information
6. **latency** - Measure round-trip latency
7. **select** - Interactive device selection
8. **install** - Install dependencies
9. **new** - Create new project
10. **update** - Update dependencies
11. **clean** - Clean dependency cache
12. **cache** - Manage local cache

**CLI Implementation Pattern**

Each command:
1. Creates a `Device` instance
2. Calls appropriate method
3. Handles exceptions
4. Returns exit code

**CLI Command Guidelines**

When writing CLI commands:
- **Use Cyclopts (not Typer):** This project uses Cyclopts for CLI argument parsing
- **Parameter help via docstrings:** Cyclopts parses NumPy-style docstrings to generate parameter help text. Use standard function signatures with type hints, and document parameters in the docstring rather than using `Annotated[type, Parameter(help="...")]`
- **Example:**
  ```python
  def my_command(
      port: PortStr,
      *,
      password: PasswordStr = "",
      count: int = 10,
      verbose: bool = False,
  ):
      """Command description.

      Longer description if needed.

      Parameters
      ----------
      count : int
          Number of iterations to perform.
      verbose : bool
          Show detailed output.
      """
  ```
- **Common types:** Use `PortStr` and `PasswordStr` from `belay.cli.common` for port and password parameters (these are Annotated types with help text already defined)

---

## Important Files Quick Reference

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Device Core | device.py | 927 | Main Device class |
| Metaclass | device_meta.py | 118 | Method overloading |
| Executors | executers.py | 226 | Execution engine |
| Support | device_support.py | 91 | Implementation detection |
| Communication | pyboard.py | 686 | Low-level protocol |
| Sync | device_sync_support.py | 114 | File sync logic |
| Proxies | proxy_object.py | 101 | Remote object proxying |
| Inspection | inspect.py | 132 | Source code extraction |
| Hash | hash.py | 39 | FNV1a32 implementation |
| Helpers | helpers.py | 39 | Utility functions |
| Minify | _minify.py | 138 | Code minification |
| Package Manager | packagemanager/group.py | 179 | Dependency groups |
| Package Config | packagemanager/models.py | 155 | Pydantic schemas |
| Project Config | project.py | 89 | pyproject.toml loading |
| CLI Main | cli/main.py | 105 | Typer app setup |

---

## Key Design Patterns

### 1. Registry Pattern (Executors)

Each executor class inherits from `Registry`:
```python
class Executer(Registry, suffix="Executer"):
    pass


class TaskExecuter(Executer):
    pass


# Discovery:
Executer.items()  # Returns all executers
```

### 2. Descriptor Pattern (Method Selection)

`ExecuterMethod` descriptor selects implementation based on device type.

### 3. Context Manager Pattern

Device can be used as context manager for automatic cleanup.

### 4. Data Consumer Pattern

Async streaming of device output without waiting for newline.

### 5. Minify-and-Send Pattern

All code paths through minification before transmission.

---

## Connection Type Selectors

Device detection and connection:

```python
# USB Serial
Device("/dev/ttyUSB0")

# Telnet
Device("192.168.1.1:23")

# WebREPL
Device("ws://192.168.1.1:8266")

# Process (emulation)
Device("exec:/path/to/micropython")

# Auto-detect
Device(UsbSpecifier(vid=0x2341))
Device(UsbSpecifier(serial_number="AB123CDE"))
```

---

## Summary

Belay is architected around a **decorator-based code execution model** where:

1. **Device** - Central interface managing connection and execution
2. **Decorators** (@task, @setup, @teardown, @thread) - Define remote functions
3. **Executors** - Implement decoration logic
4. **Pyboard** - Low-level communication protocol
5. **Sync** - Intelligent delta file transfer
6. **ProxyObject** - Remote object interaction
7. **PackageManager** - Dependency management
8. **CLI** - User-facing commands

The system is designed for rapid iteration on embedded systems development, enabling Python developers to write and test code in a familiar environment while controlling actual hardware or emulated devices.

---

## Testing

### Test Structure

```
tests/
├── conftest.py                    # Shared fixtures
├── test_device.py                 # Device class tests
├── test_device_sync.py            # File sync tests
├── test_hash.py                   # Hash function tests
├── test_inspect.py                # Source code inspection tests
├── test_minify.py                 # Code minification tests
├── test_project.py                # Project config tests
├── test_proxy_object.py           # ProxyObject tests
├── test_usb_specifier.py          # USB device detection tests
├── cli/                           # CLI command tests
├── packagemanager/                # Package manager tests
└── integration/                   # Integration tests with emulated devices
```

### Test Configuration

**pytest.ini options (pyproject.toml):**
- `--import-mode=importlib` - Use importlib for module loading
- `--max-runs=3` - Retry flaky tests up to 3 times
- `--timeout=240` - 4-minute timeout per test
- `--force-flaky --no-success-flaky-report` - Report only persistent failures

**Coverage configuration:**
- Excludes: `tests/`, `belay/pyboard.py`, `belay/snippets/`, `belay/webrepl.py`
- Branch coverage enabled
- Specific patterns excluded (see pyproject.toml lines 73-98)

### Writing Tests

When writing tests for Belay:

1. **Use flat test functions, not test classes.** Write `test_function_name()` functions instead of `class TestSomething` with methods. Group related tests using comments.
   ```python
   # Good
   def test_add_dependency_simple(): ...


   def test_add_dependency_with_options(): ...


   # Bad - don't use test classes
   class TestAddDependency:
       def test_simple(self): ...
   ```

2. **Unit tests** should not require actual hardware. Use mocks or the emulated device from `conftest.py`.

3. **Integration tests** go in `tests/integration/` and use rp2040js emulator with actual MicroPython/CircuitPython firmware.

4. Tests marked with `@pytest.mark.network` require network access.

5. The `--max-runs=3` flag means tests may run multiple times if they're flaky. Design tests to be idempotent.

### Code Quality Tools

**Ruff** (linter):
- Target: Python 3.8+
- Line length: 120 characters
- Configuration: pyproject.toml lines 107-199
- Pydocstyle convention: numpy
- Excludes: `belay/snippets/`, `examples/`

**Black** (formatter):
- Line length: 120 characters
- Target versions: py38, py39, py310

**Pre-commit hooks:**
- Ruff linting
- Black formatting
- Various file checks (YAML, JSON, TOML validation)
- Codespell for typos
- Creosote for unused dependencies
