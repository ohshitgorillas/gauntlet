# Capture helper design

Status: approved, with its five decisions ruled.

## Constraints

- **Size and a full queue.** A write to a captured fd blocks as it would on a pipe whose reader is alive. It never fails, and is never cut, for its size or for a full queue.
- **A call that raises.** Every line written before the call raised reaches the caller.
- **A holder left running.** A child or other holder that keeps fd 1 or fd 2 open after the call ends is noticed and reported, within a bound, never waited on without end.
- **Typed errors.** The helper's own errors are typed exceptions carrying data, as the gates spec's "No copy" bullet asks (`docs/superpowers/specs/2026-10-17-quality-gates-design.md:93`).

**The constraints conflict on ordering.** No kernel object gives one queue, ordered across two fds and tagged by the fd that wrote, that also blocks like a pipe:

- A pipe or file per fd keeps each fd's own order, but not the order between the two fds.
- One pipe or file for both fds keeps that order, but cannot tell which fd wrote.
- A datagram socket does both, but fails a write under load instead of blocking.

The pipe and file statements are POSIX semantics. Decision 1 is the ruling this forces.

## Modules

One module, `tests/support/capture.py`. Its job is to run a call in this interpreter with fds 1 and 2 and `sys.stdout` and `sys.stderr` captured, take every write as a pipe with a reader would take it, and give back what was written.

```python
HOLD_BOUND: float  # seconds captured waits, once the call has ended, for every other holder of fd 1 or 2 to close it (decision 3)

class Output:  # lines written to fd 1, to fd 2, and to both in the order of decision 1; each line keeps its line end
    def __init__(self, out: list[str], err: list[str], merged: list[str]) -> None: ...
    @property
    def out(self) -> list[str]: ...     # a copy, as each view is
    @property
    def err(self) -> list[str]: ...
    @property
    def merged(self) -> list[str]: ...

class Captured[T](Output):  # a call that returned: its result and its Output
    def __init__(self, result: T, output: Output) -> None: ...
    @property
    def result(self) -> T: ...

class CaptureError(Exception):  # fd 1 or 2 was still held past the bound once the call had ended
    bound: float                # the seconds waited
    output: Output              # every line read before the bound
    def __init__(self, bound: float, output: Output) -> None: ...

class CaptureSetupError(Exception):  # capture could not set up, so the call never ran
    errno: int | None                # the errno of the failure; None where the step raised no OSError
    step: Literal["pipe", "dup", "reader"]  # making a pipe, a dup, or starting the reader thread
    def __init__(self, errno: int | None, step: Literal["pipe", "dup", "reader"]) -> None: ...

class CaptureUnrecordedError(Exception):  # output_of was asked for an exception captured never recorded
    exc: BaseException                    # that exception
    def __init__(self, exc: BaseException) -> None: ...

def captured[T](call: Callable[[], T], *, timeout: float = HOLD_BOUND) -> Captured[T]: ...
# A call that raised: its exception propagates as itself, and output_of reads its Output (decision 2).

def output_of(exc: BaseException) -> Output: ...  # the Output read while the call that raised exc ran; raises CaptureUnrecordedError for an exc captured never recorded
```

How `captured` behaves:

- **Writes.** For the length of the call, fd 1 and fd 2 each point at a pipe of their own. `sys.stdout` and `sys.stderr` are text streams over their fd, so `fileno()` still answers. A reader thread drains both pipes while the call runs. A write blocks only as it would on a pipe whose reader is alive, is never cut, and never fails for size. What was read is held in memory, with no limit but memory.
- **Order.** `.out` and `.err` each hold every line of their fd in the order written. `.merged` holds every line of both, each placed by the arrival of its first byte, as `_lines` places it. How exact that order is, decision 1 rules.
- **Setup failure.** A failure while capture sets up, in making a pipe, a dup or the reader thread (`EMFILE`, for one), gets the same cleanup as every exit path, and then `captured` raises `CaptureSetupError`, carrying the errno and the step that failed. No bare `OSError` leaves the helper.
- **A call that raises.** The call's exception leaves `captured` unchanged, as itself, once cleanup is done. Before it leaves, capture records the `Output` read against it in the exception's own instance `__dict__` under one private key that nothing else reads, so a test reads `output_of(exc).out`, `.err` and `.merged` as data, not as note text (decision 2).
- **A holder left behind.** Once the call has ended, capture closes its own write ends. The reader then drains until both pipes reach end of file, for at most `timeout` seconds. Past that bound, capture closes its read ends, joins the reader, and raises `CaptureError` with what it read. When the call raised too, `CaptureError` is raised from the call's exception, so both are shown. Capture never signals the holder, because it does not know the holder's PID. The bound stays under pytest-timeout's 30 seconds (`pyproject.toml:55`), so a test fails on the capture's error and not on the timeout.
- **Cleanup, on every exit path, an interrupt included.** The `sys` streams are restored, and fds 1 and 2 are restored from saved duplicates. Every fd that capture opened is closed, because a `ResourceWarning` is an error under `pyproject.toml:53`. The reader is joined before `captured` returns or raises. No temp directory is made.

`_lines` is the one place captured bytes become lines. It splits each fd's text at every `str.splitlines` boundary, each line keeping its line end, as `one_line` and `output_lines` in `2026-10-20-gates-core-design.md` do.

## Homes

| Concern | Home | Forbids elsewhere |
|---|---|---|
| Capturing what code writes to fds 1 and 2 or the `sys` streams, in any test | `captured` | `capsys`, `capfd`, `redirect_stdout`/`redirect_stderr` used to read output, `os.dup2` onto fd 1 or 2, and a child interpreter started to capture the output of own code, save the stream substitution decision 5 allows |
| Captured bytes as lines, and the three views | `Output`, built by `_lines` | a consumer joining `.out` and `.err`, or splitting captured text again |
| The helper's errors | `CaptureError`, typed, carrying `bound` and `output`; `CaptureSetupError`, typed, carrying `errno` and `step`; `CaptureUnrecordedError`, typed, carrying `exc` | a bare `OSError`, `RuntimeError` or `KeyError` from the helper, and an empty `Output` for an unrecorded exception |
| Waiting for the holders of the captured fds | `captured`, bounded by `timeout`, default `HOLD_BOUND` | a consumer's own wait or poll for a captured child's output |
| Restoring fds, streams and the reader | `captured`'s own cleanup | a consumer restoring fd 1, fd 2 or the `sys` streams |
| The output of a call that raised | `output_of`, over the exception's own instance `__dict__`, under one private key that nothing else reads (decision 2) | a consumer catching the call's exception to recover its output any other way, and output carried as note text |

## Decisions

1. **Order across fds: a pipe per fd.**
   - **Rule:** `.out` and `.err` are exact. `.merged` is exact for each write made through the capturing process's `sys.stdout` or `sys.stderr`, relative to every write that finished before it. Raw writes to the two fds with no stream write between them, from `os.write` or a child, are in the order they arrived, which may not be the order they were written.
   - **Cost:** raw and child interleaving across the two fds is not held exactly. Gate output keeps its exact order, because gates write through `sys.stdout` (`gates/core/report.py:97`). The cost of the stream-side bookkeeping is unmeasured.
   - **Not taken:** datagrams for exact order everywhere, where a raw or child write fails under load; and one pipe for both fds, where `.out` and `.err` lose every raw write.
2. **The output of a call that raises: a typed accessor.**
   - **Rule:** the call's exception propagates unchanged. Its `Output`, with `.out`, `.err` and `.merged`, is read through `output_of(exc: BaseException) -> Output` in `capture.py`, backed by the exception's own instance `__dict__` under one private key that nothing else reads; `output_of` reads it back with an `isinstance` check and raises `CaptureUnrecordedError` when it is absent. It stays the one typed accessor, not a note.
   - **Cost:** a test reads those lines as data, with no note text to parse. pytest's failure report does not show them.
   - **Not taken:** an attribute set on the exception through `setattr`, which hides from mypy and pyright, since it is set by string on an arbitrary `BaseException`; a note (`BaseException.add_note`) holding the `.merged` lines, which a test wanting data would have to parse; and `captured` never re-raising, with `Captured.raised: BaseException | None`, which passes a caller that never checks `.raised` on a call that failed; and a `weakref.WeakKeyDictionary`, since built-in exception instances such as `ValueError`, `AssertionError` and `KeyboardInterrupt` cannot be weakly referenced, so their output would be lost.
3. **The bound: a `timeout` keyword.**
   - **Rule:** `captured` takes `timeout`, defaulting to `HOLD_BOUND`, which is 5 seconds, under pytest-timeout's 30 (`pyproject.toml:55`). The helper's own test of the loud failure passes 0.5 seconds, the least the test-shape gate allows a `timeout` keyword (`2026-10-17-quality-gates-design.md:119`).
   - **Cost:** the 5 seconds is unmeasured, as is how long a legitimate holder takes to close its copy of the fd.
   - **Not taken:** a fixed bound with no keyword, where that test waits the full bound on every run.
4. **Both fds in written order: `.merged`.**
   - **Rule:** a consumer that reads both fds in the order written reads `.merged`.
   - **Cost:** none found.
   - **Not taken:** `.out`, where a line a gate printed to stderr goes unseen.
5. **Stream substitution in `tests/test_core_report.py:450`, `:500` and `:508`: a carve-out.**
   - **Rule:** those tests put a stream of their own in `sys.stdout` or `sys.stderr`, which the capture home allows only where the stream object is what the test is about. `write` looks up `sys.stdout` when it is called (`gates/core/report.py:97`), and a capture of fd 1 cannot tell that from a write to `sys.__stdout__`.
   - **Cost:** one stated carve-out from the capture home.
   - **Not taken:** a fourth `Output` view of the writes made through capture's own streams, kept for one consumer. The flush tests at `:500` and `:508` keep their buffered stream either way.

