Status: approved by the owner.

## Why

M2 supplies the six fixed kinds, credential proxy, hardening and host worktrees; its completion check compares complete mount and tool tables without starting containers (`docs/roadmap.md:60`). Pure decisions precede thin seams (`docs/roadmap.md:12`); measured platform behavior is not measured again (`docs/roadmap.md:14`).

- **Product launch, proxy and worktree implementations: zero surveyed copies.** Their required destinations are `docs/design.md:303`; the existing executor is an injected protocol (`gauntlet/seams/resume.py:30`), and the CLI reports its absence (`gauntlet/seams/cli.py:67`). M2 supplies reusable adapters; the full check/land executor belongs to M3s (`docs/roadmap.md:48`).

- **Canonical product contracts: one each.** Kind is at `gauntlet/core/records.py:64`, Config at `gauntlet/core/records.py:418`, role associations at `gauntlet/core/roles.py:15`, answer schemas at `gauntlet/core/codec.py:484`, and typed errors at `gauntlet/core/errors.py:5`. Launch records consume these definitions.

- **Process precedent: one gate runner.** Command/Completed/Runner are at `gates/core/checker.py:35`, `gates/core/checker.py:49` and `gates/core/checker.py:63`; process execution is at `gates/core/checker.py:81`. The product needs its separate process seam with this shape and a product fake (`docs/superpowers/specs/gates-core-design.md:468`). Product code imports no gate infrastructure.

- **Git precedent: one gate command builder.** `gates/core/project.py:170` invokes git in a gate root. `tests/support/project.py:45` uses it for gate fixtures. Neither supplies explicit product worktree identity. Product git has one new builder; gate git stays in its domain.

- **Cleanup has two existing domains.** Job publication deletes only its owned temporary (`gauntlet/seams/job.py:141`); gate Scratch owns its run directory (`gates/core/runner.py:40`). Extend the job store for durable workspace checkpoints and launch resources; do not borrow gate Scratch or write state from the launcher.

- **Test infrastructure has existing homes.** Gate process replies live at `tests/support/fake.py:17`, deterministic gate concurrency at `tests/support/scripted.py:49`, product executor replies at `tests/support/recovery.py:29`, and real-child coordination at `tests/support/lifeline.py:53`. Product process replies need a separate typed home, not per-test runners.

- **COPY finding: three CacheLeavingRunner definitions.** Anchors: `tests/test_check_mypy_core.py:44`, `tests/test_check_mypy_stderr.py:40`, `tests/test_check_mypy_stopped.py:47`. Gate cache-test helpers are outside M2's product-adapter scope.

- **Configuration and clock precedents have separate domains.** Config defaults live at `gauntlet/core/records.py:418`; validation is at `gauntlet/core/config.py:116` and `gauntlet/core/config.py:201`; YAML enters at `gauntlet/seams/config.py:90`. Extend these for readiness, proxy limits and additional API routes. Gate Clock is at `gates/core/clock.py:10`; VirtualClock is at `tests/support/clock.py:28`. Product readiness uses a separate structural protocol and the existing virtual clock, without importing gate code.

- **Configuration transport and fixtures each have one home.** Config enters the codec catalog at `gauntlet/core/codec.py:100`; ConfigChanges is at `tests/support/answers.py:106`. Extend the canonical record, validator and fixture view together. New mount validation, credential-descriptor and readiness adapters replace no product implementations; product seam destinations are specified at `docs/design.md:301`.

## Modules

All interfaces below are document stubs. Frozen dataclasses hold the listed fields; function bodies raise NotImplementedError. Imports use the canonical Kind, Config, RoleSpec, RoleAnswer, TraceRow, GitIntent, RecoveryPoint and Json. ProxyLimits and ProxyRoute persist with Config; other new records are runtime transport, not persisted workflow records. Builders stop with the missing shared contract when an owner decision or home cannot supply it.

### `gauntlet/core/launch.py` — pure kind policies, mount plans and container hardening

Replaces no product implementation. Consumes Kind and Config (`gauntlet/core/records.py:64`, `gauntlet/core/records.py:418`); replaces prospective per-kind conditionals in consumers with one complete table.

```python
@dataclass(frozen=True)
class Mount:
    source: str
    target: str
    mode: Literal["ro,z", "rw,z", "O"]


@dataclass(frozen=True)
class LaunchPaths:
    job_tree: str
    main_tree: str
    spec: str
    tests: str
    helpers: tuple[tuple[str, str], ...]
    policy: str
    interface: str
    lint_configs: tuple[tuple[str, str], ...]
    git_file: str
    socket_folder: str
    uid: int
    gid: int


@dataclass(frozen=True)
class KindPolicy:
    kind: Kind
    tools: tuple[str, ...]
    harness_tools: tuple[str, ...]


@dataclass(frozen=True)
class LaunchPlan:
    kind: Kind
    mounts: tuple[Mount, ...]
    tools: tuple[str, ...]
    harness_tools: tuple[str, ...]
    flags: tuple[str, ...]
    environment: tuple[tuple[str, str], ...]
    cwd: str


KINDS: tuple[KindPolicy, ...]


def hardening(*, network: bool, level: str, uid: int, gid: int) -> tuple[str, ...]: ...
def launch_plan(
    kind: Kind, paths: LaunchPaths, config: Config, *, level: str
) -> LaunchPlan: ...
```

The tools below are the SDK built-in list; shell is SDK Bash. MCP names occupy harness_tools, never the built-in list. StructuredOutput is supplied only by output_format, not inserted into these lists (`docs/design.md:119`, `docs/design.md:212`).

| Kind | Built-in tools | Harness tools | Job mounts |
|---|---|---|---|
| judge | empty | empty | None; prompt only. |
| reader | Read, Grep, Glob | empty | job tree ro at /work. |
| coordinator | Read, Grep, Glob | open_job, job_status, job_record | main tree ro at /work. |
| scratch | Bash, Read, Write, Edit, Grep, Glob | empty | job tree :O at /work; original .git ro over it. |
| tester | Bash, Read, Write, Edit, Grep, Glob | run_tests | tests rw at /work/tests; only spec, helpers, policy, interface and lint/type configs ro at their staged destinations. |

| Kind | Built-in tools | Harness tools | Job mounts |
|---|---|---|---|
| implementer | Bash, Read, Write, Edit, Grep, Glob | empty | job tree rw at /work; tests, .git and each protected path ro over it. |

This table implements `docs/design.md:110`, `docs/design.md:164`, `docs/design.md:194` and `docs/design.md:208`. Coordinator's /work contains the main checkout named by §3 (`docs/design.md:114`). Tester has no whole-tree bind; parent directories contain no source. Mount ordering places specific protections after the tree mount. Helpers overlapping tests remain read-only.

Every role also binds the socket folder at /run/gauntlet with :z, including judges (`docs/design.md:133`). No role binds credentials, host home, host CLI, job records or git metadata directories. Scratch's .git overlay stays read-only. Role tools never include Agent or the gauntlet CLI (`docs/design.md:121`).

hardening is the only flag builder: --rm, --userns=keep-id with an explicit nonzero uid/gid, --cap-drop=all, --security-opt no-new-privileges, a tmpfs /home/agent, HOME=/home/agent, and the per-launch SELinux level. It emits --network none unless kind is implementer and Config.implementer_network is true (`docs/design.md:140`, `docs/design.md:171`). Sidecars call the same builder with network enabled. No label=disable, privileged launch or mount widening exists.

### `gauntlet/seams/mounts.py` — validate sources and stage the minimal tester filesystem

Consumes the fixed table and explicit roots; replaces no product mount validator. Config paths remain opaque in the pure validator (`gauntlet/core/config.py:47`); filesystem checks live here.

```python
def prepare_paths(
    kind: Kind, paths: LaunchPaths, config: Config, resources: LaunchResources
) -> LaunchPaths: ...
```

Before any podman action, reject traversal, sources outside their assigned checkout or harness artifact root, symlinked source components within that root, missing sources and absent protected paths. Recursively reject links that would expose an unmounted source through a helper directory. Validate destinations as contained /work paths and reject collisions that widen access. Do not canonicalize symlinks or create missing-file placeholders.

For testers, populate only resources.staging with explicit spec, policy, interface, helper and lint/type-config artifacts; create empty destination parents, never copy a source parent. Bind tests writable and every staged artifact read-only at its explicit destination; helpers within tests get their own read-only overlay. A helper outside tests appears only at its named /work-relative destination. launch_plan receives the validated LaunchPaths and owns every mount decision. JobStore allocates and removes staging; this module only validates and populates it.

### `gauntlet/core/records.py` — canonical startup, proxy limits and route-extension records

Extends Config (`gauntlet/core/records.py:418`), retaining all existing fields and defaults. The readiness default is ten seconds; proxy limits and route defaults are canonical here.

```python
DEFAULT_READINESS_TIMEOUT_SECONDS: int = 10


@dataclass(frozen=True)
class ProxyRoute:
    method: str
    path: str
    query_parameters: tuple[str, ...] = ()


DEFAULT_PROXY_ROUTES: tuple[ProxyRoute, ...] = (
    ProxyRoute("POST", "/v1/messages", ("beta",)),
    ProxyRoute("POST", "/v1/messages/count_tokens", ("beta",)),
)


@dataclass(frozen=True)
class ProxyLimits:
    header_bytes: int = 65536
    body_bytes: int = 33554432
    connections: int = 8


@dataclass(frozen=True)
class Config:
    image: str
    tests: tuple[TestCommand, ...]
    gates: str
    test_policy: str
    interface: tuple[InterfaceCommand, ...]
    test_helpers: tuple[str, ...] = ()
    protected: tuple[str, ...] = ()
    test_lint: str | None = None
    implementer_network: bool = False
    caps: Caps = Caps()
    roles: tuple[RoleSetting, ...] = ()
    readiness_timeout_seconds: int = DEFAULT_READINESS_TIMEOUT_SECONDS
    proxy_limits: ProxyLimits = ProxyLimits()
    proxy_extra_routes: tuple[ProxyRoute, ...] = ()
```

gauntlet.yaml accepts readiness_timeout_seconds, shared by proxy and relay startup, and an optional proxy_limits mapping. Missing mapping members retain 64 KiB headers, 32 MiB streamed request bodies and eight concurrent requests per sidecar. Users can adjust each limit independently. These defaults are policy values, not measured SDK requirements. ProxyLimits is the one persisted record for these settings.

gauntlet.yaml also accepts proxy_extra_routes, an optional list of objects with required method and path and optional query_parameters. Omission adds no routes. Users extend the proxy for additional API tools without a harness release; entries add exact method/path permissions or query names to an existing route. Defaults remain available. ProxyRoute is the only route descriptor; it grants no SDK or MCP tools and changes no kind permissions.

readiness_timeout_seconds defaults to ten seconds and bounds each container/relay startup only after image preparation succeeds. Downloads and image builds precede this deadline. No per-kind timeout or model-response deadline exists.

### `gauntlet/core/config.py` — validate startup, proxy-limit and route overrides

Extends `gauntlet/core/config.py:116` and `gauntlet/core/config.py:201`; replaces no second validator.

```python
def config_from_json(value: Json) -> Config: ...
def config_problems(config: Config) -> tuple[str, ...]: ...
def proxy_limits_from_json(value: Json) -> ProxyLimits: ...
def proxy_routes_from_json(value: Json) -> tuple[ProxyRoute, ...]: ...
```

readiness_timeout_seconds and every proxy limit are positive integers, excluding bool. Missing values use the canonical defaults. Reject zero, negative, noninteger and boolean values at $.readiness_timeout_seconds or $.proxy_limits.<field>; reject unknown mapping members and a nonobject mapping. config_problems reports the same constraints for direct records. proxy_limits_from_json owns partial-map defaults and validation for config and sidecar transport. YAML access remains in seams/config.py (`gauntlet/seams/config.py:90`).

proxy_routes_from_json owns route-object parsing and validation for config and sidecar arguments. Require uppercase HTTP-token methods and exact origin-form paths without query, fragment, wildcard, credentials, traversal or ambiguous encoding. Query names are nonempty literal names without URI delimiters or controls. Reject unknown fields, invalid types and duplicate method/path entries within the extension list at $.proxy_extra_routes[index].<field>. config_problems applies the same constraints to direct records; it never defines another route grammar.

### `gauntlet/core/codec.py` — carry startup and proxy settings through the canonical catalog

Extends the Config catalog entry (`gauntlet/core/codec.py:100`); replaces no serializer.

```python
def encode_state(state: State) -> str: ...
def decode_state(text: str) -> State: ...
```

Catalog ProxyLimits and ProxyRoute once and round-trip readiness_timeout_seconds, proxy_limits and proxy_extra_routes with State.config through the existing dataclass codec. Existing schema/version and missing-field rules remain; these settings add no separate config wire format.

### `gauntlet/core/errors.py` — typed failures across process, mount, image and proxy boundaries

Extends the existing family (`gauntlet/core/errors.py:5`); replaces no gate errors. Existing ConfigError, StorageError, RecordError, RecoveryError and CapabilityError retain their contracts.

```python
class ProcessError(GauntletError):
    operation: str
    status: int | None
    reason: str

    def __init__(self, operation: str, status: int | None, reason: str) -> None: ...


class LaunchError(GauntletError):
    component: str
    reason: str

    def __init__(self, component: str, reason: str) -> None: ...
```

Errors carry safe operation identifiers and bounded reasons, not credentials, request bodies, inherited environments or arbitrary process output. CLI rendering and exit status remain at `gauntlet/seams/cli.py:31` and `gauntlet/seams/cli.py:36`; process status is evidence, not a CLI status decision.

### `gauntlet/seams/process.py` — product process execution and owned child cleanup

Replaces no gate runner; supplies the separate product shape required at `docs/superpowers/specs/gates-core-design.md:468`.

```python
@dataclass(frozen=True)
class Command:
    argv: tuple[str, ...]
    cwd: Path
    env: Mapping[str, str] | None = None
    timeout: float | None = None
    throttled: bool = False
    outputs: Mapping[str, Path] = field(default_factory=dict)
    capture: bool = True
    pass_fds: tuple[int, ...] = ()


@dataclass(frozen=True)
class Completed:
    status: int
    stdout: str
    stderr: str
    timed_out: bool
    outputs: Mapping[str, str | None]

    def output(self) -> str: ...


type Runner = Callable[[Command], Completed]


class Child(Protocol):
    def wait(self) -> Completed: ...
    def close(self) -> None: ...


type Starter = Callable[[Command], Child]


def run(command: Command, *, clock: Clock = SYSTEM) -> Completed: ...
def start(command: Command, *, clock: Clock = SYSTEM) -> Child: ...
def exec_command(argv: tuple[str, ...], env: Mapping[str, str]) -> NoReturn: ...
```

Commands carry argv as separate values. Nothing splits or interprets shell text. run/start own child sessions, termination and reaping on exceptions and interrupts; close is idempotent. Pass-through mode preserves stdio for SDK transport. Failed starts and failed cleanup raise ProcessError. Signal statuses follow the gate precedent's shell-status convention (`gates/core/checker.py:347`). Container lifetime cleanup additionally uses saved resource identities, since killing a podman client alone does not prove container removal.

### `gauntlet/seams/readiness.py` — product clock boundary and bounded socket readiness

Replaces prospective proxy/relay wait loops. Gate Clock remains in its domain (`gates/core/clock.py:10`); tests reuse the structurally compatible VirtualClock (`tests/support/clock.py:28`).

```python
type Ready = Callable[[float | None], bool]


class Clock(Protocol):
    def wait(self, ready: Ready, seconds: float | None) -> bool: ...


class SystemClock:
    def wait(self, ready: Ready, seconds: float | None) -> bool: ...


SYSTEM: Clock


class Readiness(Protocol):
    def unix(
        self, path: Path, *, seconds: int, start: Callable[[float], None]
    ) -> None: ...
    def tcp(
        self, host: str, port: int, *, seconds: int, start: Callable[[float], None]
    ) -> None: ...


class SocketReadiness:
    def __init__(self, *, clock: Clock = SYSTEM) -> None: ...
    def unix(
        self, path: Path, *, seconds: int, start: Callable[[float], None]
    ) -> None: ...
    def tcp(
        self, host: str, port: int, *, seconds: int, start: Callable[[float], None]
    ) -> None: ...
```

Real clock reads and deadline calculations for product startup and process waits live here. run/start take this Clock as a keyword collaborator, defaulting to SYSTEM. SocketReadiness starts its deadline immediately before invoking start with the remaining seconds, then probes within the same deadline. The callback bounds its process command with that remaining budget; it performs no image acquisition. Thus container creation and socket readiness share one startup budget.

SocketReadiness uses nonblocking connection events, retries only through clock-owned bounded waits, and closes probes on every path. A successful connection ends readiness; expiry or an unrecoverable socket failure raises LaunchError with a safe component/reason. Tests inject readiness events and VirtualClock; they never sleep or define a second fake clock.

### `gauntlet/seams/git.py` — explicit host git identity and job worktrees

Replaces prospective caller-specific git commands. It does not replace gate git (`gates/core/project.py:170`).

```python
@dataclass(frozen=True)
class Checkout:
    git_dir: Path
    work_tree: Path


def command(checkout: Checkout, arguments: tuple[str, ...]) -> Command: ...
def create_job(
    repository: Checkout, job: Path, identity: str, base: str, *, process: Runner
) -> Checkout: ...
def remove_job(
    repository: Checkout, checkout: Checkout, *, process: Runner
) -> None: ...
def observe_intent(
    checkout: Checkout, intent: GitIntent, *, effect: str, process: Runner
) -> Literal["applied", "unapplied"]: ...
```

Every command starts git --git-dir=<absolute identity> --work-tree=<absolute identity>, runs on the host and drops inherited GIT_* variables. Repository identity comes from the caller, never cwd discovery or container .git resolution (`docs/design.md:157`). Trusted git options disable hooks and external diff/filter execution; no repository-controlled command is used as recovery evidence.

create_job creates branch gauntlet/<identity> at job/tree and returns its actual worktree git directory. Identifiers are single safe components; pre-existing paths or branches with contradictory ownership fail. Removal verifies ownership before worktree removal and never deletes the owner's main checkout.

observe_intent checks the exact repository, reference, before/after commits and prepared effect metadata. The reference at after, or containing it, proves applied; an unreferenced object does not. Contradictions raise RecoveryError (`docs/design.md:277`). Prepared effect metadata is verified against the saved intent and executor-owned preparation identity; the caller supplies that identity, never a repository-written claim. It inspects evidence only; preparing commits and landing remain M3s (`docs/roadmap.md:48`).

### `gauntlet/seams/job.py` — durable workspace checkpoints and owned launch artifacts

Extends JobStore's single-writer and atomic-publication home (`gauntlet/seams/job.py:22`, `gauntlet/seams/job.py:141`); replaces no second checkpoint writer.

```python
@dataclass(frozen=True)
class LaunchResources:
    identity: str
    role_container: str
    proxy_container: str
    secret: str
    level: str
    folder: Path
    wrapper: Path
    staging: Path
    labels: tuple[tuple[str, str], ...]


class JobStore:
    def resources(self, effect: str, dispatch: int) -> LaunchResources: ...
    def checkpoint(self, effect: str, dispatch: int, tree: Path) -> str: ...
    def restore(self, token: str, tree: Path) -> None: ...
    def release_resources(self, resources: LaunchResources) -> None: ...
```

These are additions to the existing class, not a replacement declaration. Resources are deterministic per job/effect/dispatch and are available before any podman action. The folder contains only the proxy socket. Wrapper, staging, ownership metadata and checkpoints have separate owned paths outside every role bind; roles cannot modify host launch or recovery authority. Real secret values never enter these artifacts. JobStore owns filesystem allocation, atomic checkpoint publication, restoration and filesystem cleanup; launch owns removal of named podman resources through Runner.

Resource metadata is durably published before creation and includes job, effect and dispatch ownership labels, exact podman names, SELinux level and owned paths. Labels attach to both containers and the secret; inspection must match saved ownership before removal. Reopening resources for the same dispatch verifies the durable metadata instead of adopting an unrelated name. No PID proves ownership.

Checkpoint manifests bind the token to job, effect, dispatch and exact worktree identity. Snapshot entries contain relative paths, entry types, modes and contents/link targets; reject special files, absolute entry paths and parent-traversing entry paths, and never follow saved symlink targets. Publish snapshot contents and manifest atomically only after flushing them and their directory. Restore verifies the complete snapshot before modifying the tree, removes post-checkpoint entries, preserves .git and replays only the assigned workspace. Another interrupted restore repeats safely from the immutable snapshot. Cost in disk space and restoration time is unmeasured.

Checkpoints preserve files, executable modes and symlink identities, including untracked work, without following a link outside the assigned tree. Restore changes only the assigned worktree and preserves its git registration; git operations delegate to git.py. Incomplete snapshots never become recovery tokens. Recovery removes any surviving owned role/sidecar/secret before restoring; an absent resource is idempotent success only when podman's structured observation proves absence. Foreign ownership or contradictory checkpoint evidence raises RecoveryError. No trace-derived state or second workflow loop is introduced (`gauntlet/seams/resume.py:51`).

### `gauntlet/seams/images.py` — current dependencies and confirmed image availability

Replaces no image builder. Implements the separate image provenance required at `docs/design.md:131` and `docs/design.md:169`.

```python
@dataclass(frozen=True)
class Images:
    role: str
    proxy: str


def build_images(
    root: Path,
    config: Config,
    wheel: Path,
    *,
    refresh_cli: bool = False,
    process: Runner,
) -> Images: ...


class ImagePreparation(Protocol):
    def prepare(self) -> Images: ...


class ImageBuilder:
    def __init__(
        self,
        root: Path,
        config: Config,
        wheel: Path,
        *,
        refresh_cli: bool = False,
        process: Runner,
    ) -> None: ...
    def prepare(self) -> Images: ...
```

The role image extends Config.image with the current available Claude Code and socat releases and gauntlet-launch. The proxy image uses the current official Python slim base and the installed harness wheel. SDK and HTTP libraries come from the installed harness environment. Installation and explicit refresh resolve current versions; ordinary use accepts the versions already installed. No M2 release pin manifest, historical version check or exact CLI, SDK, relay or proxy-base version constraint exists. The dependency lock records an installation resolution rather than a runtime version requirement.

Neither the repository's image nor repository files enter the proxy build context. Record resolved versions and immutable image identities as provenance; every launch uses the confirmed identities. refresh_cli=True refreshes the CLI installation layer; reuse of already installed versions is valid. An active launch keeps its selected images. No host CLI bind or in-container auto-update changes that launch.

ImageBuilder.prepare delegates assembly to build_images and owns local availability inspection. Before returning, inspect both required images through Runner. Structured absence triggers download of a pullable source or rebuilding a locally assembled image from its trusted inputs; inspect the result again and return only confirmed immutable identities. Generic inspection failure, failed acquisition or contradictory provenance raises LaunchError. Downloads and builds have their own process failures and cancellation cleanup, outside readiness_timeout_seconds; missing images never consume the startup budget or become a socket-timeout report.

Measured versions are evidence scope, not required dependencies (`docs/measured.md:5`). Product summaries describe exact CLI and proxy-base pins at `docs/design.md:129`, `docs/design.md:131`, `docs/design.md:169` and `docs/config.md:31`; M2's installation contract uses current or installed versions and retains immutable identity only for each prepared launch.

### `gauntlet/seams/launch.py` — assemble and execute every SDK role launch

Replaces no launcher. Uses the pure plan, images, process seam, job resources, existing role registry and codec.

```python
@dataclass(frozen=True)
class LaunchResult:
    answer: RoleAnswer
    trace: TraceRow


@dataclass(frozen=True)
class HarnessTool:
    name: str
    description: str
    input_schema: Json
    call: Callable[[Json], Awaitable[Json]]


class Sdk(Protocol):
    async def query(
        self,
        *,
        wrapper: Path,
        plan: LaunchPlan,
        prompt: str,
        role: RoleSpec,
        model: str,
        effort: str,
    ) -> LaunchResult: ...


async def launch(
    role: RoleSpec,
    prompt: str,
    paths: LaunchPaths,
    config: Config,
    images: ImagePreparation,
    resources: LaunchResources,
    *,
    model: str,
    effort: str,
    sdk: Sdk,
    process: Runner,
    store: JobStore,
    credential: CredentialSource,
    ready: Readiness,
) -> LaunchResult: ...
def remove_resources(resources: LaunchResources, *, process: Runner) -> None: ...
def recover_workspace(
    resources: LaunchResources,
    token: str,
    tree: Path,
    *,
    process: Runner,
    store: JobStore,
) -> None: ...
def sdk_adapter(tools: tuple[HarnessTool, ...]) -> Sdk: ...
```

The SDK adapter passes tools exactly, registers only the listed in-process MCP tools and sets setting_sources=[], strict_mcp_config=True and permission_mode="dontAsk". It obtains output_format from answer_schema(role), and validates returned structured answers through the canonical codec (`gauntlet/core/codec.py:416`, `gauntlet/core/codec.py:484`). Missing MCP implementations raise CapabilityError before dispatch; they never become empty success handlers. MCP capability implementations remain at their roadmap milestones (`docs/roadmap.md:87`, `docs/roadmap.md:157`).

The SDK's cli_path is the trusted executable at resources.wrapper, outside every container bind. It forwards SDK argv unchanged to podman run -i <plan flags/mounts/environment> <role image> gauntlet-launch. It contains no API key and binds no host CLI. Python entrypoint execution delegates to process.exec_command. The role's authentication environment contains only ANTHROPIC_API_KEY=gauntlet-placeholder and ANTHROPIC_BASE_URL=http://127.0.0.1:18080; its readiness setting is nonsecret. Host credentials/settings are not inherited.

Before SDK dispatch, launch creates an owned podman secret from CredentialSource's read descriptor: pass_fds preserves it for podman secret create with /dev/fd/<fd> as its input file; no credential enters argv or a disk file. It starts the proxy container on the rootless default network, and waits for its socket readiness through an injected adapter. Both containers use resources.level. Startup, SDK failure, cancellation and normal completion remove role, proxy and secret by saved identity, then release the owned folder. remove_resources inspects each exact saved identity, verifies every ownership label and removes role, proxy and secret in that order. An explicit structured absence result is success; generic nonzero status or unreadable inspection is a failure. It verifies removal before releasing filesystem artifacts. recover_workspace removes surviving resources, restores the saved snapshot and releases owned artifacts in that order; a repeated call is safe. The existing Executor.recover boundary consumes it (`gauntlet/seams/resume.py:40`), with the RecoveryPoint workspace token unchanged. Cleanup failure remains visible and recoverable; no raw response is printed. Trace cost/tokens remain unknown when unavailable (`gauntlet/core/records.py:492`).

CredentialSource comes from seams/credentials.py, ImagePreparation from seams/images.py and Readiness from seams/readiness.py. launch validates prepare_paths before any podman action, then calls images.prepare before creating secrets or starting readiness. Only after both images are confirmed does it invoke ready.unix with the sidecar-start callback and Config.readiness_timeout_seconds. Timed podman runs prohibit implicit pulls, so an image disappearing after confirmation fails explicitly. Image preparation has no local substitute in the launcher or wrapper.

The trusted entrypoint receives the same readiness timeout through GAUNTLET_READINESS_TIMEOUT_SECONDS and starts its relay within ready.tcp's callback. Proxy limits and extra routes travel as nonsecret sidecar arguments from Config.proxy_limits and Config.proxy_extra_routes; route objects use one JSON argument, never shell text. Sidecar main validates them through proxy_limits_from_json and proxy_routes_from_json and constructs the fixed-authority policy through proxy_policy. No role reads repository configuration or chooses a proxy policy. The launcher returns evidence to the existing executor protocol; it never writes State, charges rounds or interprets stage transitions (`gauntlet/seams/resume.py:30`).

### `gauntlet/seams/credentials.py` — descriptor-only credential delivery to podman

Replaces no product supplier. The proxy secret boundary is at `docs/design.md:169`; caller credential acquisition remains outside the role launcher.

```python
class CredentialSource(Protocol):
    def open(self) -> ContextManager[int]: ...


class DescriptorCredentialSource:
    def __init__(self, descriptor: int) -> None: ...
    def open(self) -> ContextManager[int]: ...
```

The host caller supplies a readable descriptor positioned at the key bytes. open duplicates that descriptor for its context and closes the duplicate on all exits; the caller retains its original. Invalid or unreadable descriptors raise LaunchError before podman creation. The launcher passes only the descriptor number through pass_fds and /dev/fd; it never materializes key bytes, guesses a host settings file or logs the descriptor contents. The secret mounts only in the sidecar at /run/secrets/gauntlet-api-key.

### `gauntlet/seams/entrypoint.py` — in-image relay readiness and CLI exec

Replaces no entrypoint. Implements gauntlet-launch (`docs/design.md:131`).

```python
def main(
    arguments: tuple[str, ...],
    *,
    start_process: Starter,
    ready: Readiness,
    seconds: int,
    environment: Mapping[str, str],
    execute: Callable[[tuple[str, ...], Mapping[str, str]], NoReturn],
) -> NoReturn: ...
```

It starts socat TCP-LISTEN:18080,bind=127.0.0.1,fork UNIX-CONNECT:/run/gauntlet/proxy.sock through ready.tcp's start callback, waits for the relay to accept, and execs /usr/local/bin/claude with arguments unchanged. Readiness uses seams/readiness.py with the supplied seconds value, including relay process startup. Images are already present; the entrypoint performs no downloads. Startup failure or expiry closes the relay and raises LaunchError. Tests use supplied readiness events, not sleeps. The role container lifetime owns the relay after CLI exec.

### `gauntlet/core/proxy.py` — fixed upstream and request policy

Replaces no product policy. Implements the credential-forwarding boundary at `docs/design.md:166` and `docs/design.md:169`.

```python
UPSTREAM_ORIGIN = "https://api.anthropic.com"


@dataclass(frozen=True)
class ProxyPolicy:
    routes: tuple[ProxyRoute, ...]
    limits: ProxyLimits


RELEASE_POLICY: ProxyPolicy


def proxy_policy(
    limits: ProxyLimits, extra_routes: tuple[ProxyRoute, ...] = ()
) -> ProxyPolicy: ...
def upstream_target(method: str, target: str, policy: ProxyPolicy) -> str: ...
```

UPSTREAM_ORIGIN is fixed and has no repository override. Accept only origin-form API requests whose exact method/path matches the supplied ProxyPolicy; preserve only that route's allowed query parameters. Reject absolute authorities, credentials, fragments, traversal and ambiguous encodings with LaunchError. Return only a target under the fixed HTTPS origin.

RELEASE_POLICY uses DEFAULT_PROXY_ROUTES and canonical ProxyLimits. proxy_policy combines these routes with validated Config.proxy_extra_routes and uses Config.proxy_limits. A new method/path adds a route; an existing pair unions query names, preserving declaration order without duplicates. There are no wildcard routes, arbitrary origins or redirects. Users explicitly name the API endpoints their tools require; missing permissions fail closed.

The route-extension mechanism changes only request permissions at the fixed upstream. Kind tool tables, MCP registration and mounts retain their own contracts. Adapters never define route tables, merge rules, defaults or limit records.

### `gauntlet/seams/proxy.py` — sidecar-only credential replacement and streaming forwarding

Replaces no proxy. It alone reads the mounted podman secret (`docs/design.md:169`).

```python
class Upstream(Protocol):
    def forward(
        self,
        method: str,
        target: str,
        headers: tuple[tuple[str, str], ...],
        body: BinaryIO,
    ) -> ContextManager[tuple[int, tuple[tuple[str, str], ...], BinaryIO]]: ...


class HttpsUpstream:
    def __init__(self, *, policy: ProxyPolicy = RELEASE_POLICY) -> None: ...
    def forward(
        self,
        method: str,
        target: str,
        headers: tuple[tuple[str, str], ...],
        body: BinaryIO,
    ) -> ContextManager[tuple[int, tuple[tuple[str, str], ...], BinaryIO]]: ...


def serve(
    socket: Path,
    *,
    credential: Path,
    upstream: Upstream,
    policy: ProxyPolicy = RELEASE_POLICY,
) -> None: ...
def main(arguments: tuple[str, ...]) -> int: ...
```

The server binds only its Unix socket. It removes incoming x-api-key and Authorization headers case-insensitively, then adds the real x-api-key. It strips hop-by-hop headers and forwards status, safe headers and streaming body without buffering an entire model response. SDK stdio MCP traffic never passes through this HTTP proxy (`docs/design.md:138`). Upstream failures close the request explicitly; credentials and bodies are never logged. HttpsUpstream delegates target validation to core/proxy.py, verifies TLS for api.anthropic.com, constructs Host from that authority and never follows redirects. A redirect becomes an explicit upstream failure.

Enforce policy.limits on header bytes, streamed request bytes and concurrent requests; reject excess without forwarding more data. Reject conflicting content-length/transfer framing, strip client Host and hop-by-hop fields, and derive outbound framing in the HTTP transport. Responses remain streaming and close upstream work on client disconnect. main reads only /run/secrets/gauntlet-api-key as its credential. It receives numeric limits and JSON route extensions from trusted sidecar arguments, uses proxy_limits_from_json, proxy_routes_from_json and proxy_policy, and passes the same policy to serve and HttpsUpstream. Missing arguments use canonical defaults and no extensions; authority has no argument override. Invalid route JSON fails before listening.

### `tests/support/answers.py` — retain the exact Config fixture view

Extends ConfigChanges at `tests/support/answers.py:106` and the existing config builder; replaces no fixture.

```python
class ConfigChanges(TypedDict, total=False):
    image: str
    tests: tuple[TestCommand, ...]
    gates: str
    test_policy: str
    interface: tuple[InterfaceCommand, ...]
    test_helpers: tuple[str, ...]
    protected: tuple[str, ...]
    test_lint: str | None
    implementer_network: bool
    caps: Caps
    roles: tuple[RoleSetting, ...]
    readiness_timeout_seconds: int
    proxy_limits: ProxyLimits
    proxy_extra_routes: tuple[ProxyRoute, ...]


def config(**changes: Unpack[ConfigChanges]) -> Config: ...
```

Keep every existing fixture field and literal seed. Omission uses the canonical Config default; an explicit override passes unchanged to Config. No local startup-config factory is introduced.

### `tests/support/process.py` — literal product process and SDK collaborator replies

Replaces prospective local launch/git/image fakes, not the differently typed gate FakeRunner (`tests/support/fake.py:17`).

```python
class RepliesExhaustedError(Exception):
    collaborator: str
    count: int

    def __init__(self, collaborator: str, count: int) -> None: ...


class FakeRunner:
    commands: list[Command]

    def __init__(self, replies: Sequence[Completed | ProcessError]) -> None: ...
    def __call__(self, command: Command) -> Completed: ...


class FakeSdk:
    calls: list[tuple[Path, LaunchPlan, str, RoleSpec, str, str]]

    def __init__(self, replies: Sequence[LaunchResult | LaunchError]) -> None: ...
    async def query(
        self,
        *,
        wrapper: Path,
        plan: LaunchPlan,
        prompt: str,
        role: RoleSpec,
        model: str,
        effort: str,
    ) -> LaunchResult: ...


def completed(
    status: int = 0,
    stdout: str = "",
    stderr: str = "",
    *,
    timed_out: bool = False,
    outputs: Mapping[str, str | None] = MappingProxyType({}),
) -> Completed: ...
```

Replies are seeded literals, returned unchanged in call order; exhaustion raises RepliesExhaustedError with collaborator identity and attempted-call count; each fake retains its typed call history. Helper tests pin this behavior before consumer tests. Existing answers.config, recovery.Replies and lifeline coordination remain their own homes (`tests/support/recovery.py:29`, `tests/support/lifeline.py:53`). No fake computes expected mounts, commands, schemas or answers by calling product builders.

## Homes

| Shared concern | One home | Forbids elsewhere |
|---|---|---|
| Kind identity and persisted records | core/records.py | Another Kind, Config, TraceRow, GitIntent or RecoveryPoint. |
| Fixed role/kind/schema association | core/roles.py | A launcher reassigning roles or inventing schema tags. |
| Config defaults and validation | core/records.py:Config, ProxyLimits, ProxyRoute and DEFAULT_PROXY_ROUTES with core/config.py; YAML through seams/config.py | Another YAML reader, readiness/proxy default, route descriptor, override validator, limit record or network policy. |
| Kind tables and mount decisions | core/launch.py | Per-role permissions, optional widening, caller-built mount/tool lists. |
| Mount source validation and tester staging | seams/mounts.py | Per-kind path resolvers, symlink canonicalization, missing-file placeholders or parent-source copies. |
| Container hardening and network flags | core/launch.py:hardening | Role, proxy, future runner or entrypoint restating flags. |

| Shared concern | One home | Forbids elsewhere |
|---|---|---|
| SDK setup and wrapper assembly | seams/launch.py | Direct SDK launches elsewhere or host CLI binds. |
| Answer encoding/schema export | core/codec.py | SDK-specific product record reconstruction or another catalog. |
| Product errors | core/errors.py | Gate errors crossing product boundaries or per-adapter exception families. |
| Product terminal output/status | seams/cli.py | Printing product diagnostics or selecting CLI exit codes in adapters. |
| Product process execution/reaping | seams/process.py | subprocess/exec/session cleanup in git, images, launch or entrypoint. |

| Shared concern | One home | Forbids elsewhere |
|---|---|---|
| Host git and checkout identity | seams/git.py | git argv construction, cwd inference or container git elsewhere in product. |
| Durable state/checkpoints, resource ownership metadata and filesystem cleanup | seams/job.py | Launcher state writes, PID ownership, trace-derived recovery or broad temp deletion. |
| Podman lifecycle and resource-before-restore ordering | seams/launch.py:remove_resources, recover_workspace | Per-kind cleanup, unverified-name removal or workspace restore before container removal. |
| Current/installed dependencies, image preparation and provenance | seams/images.py | Release version manifests, historical dependency requirements, caller-specific image acquisition, repository-provided proxy code, host CLI binds or mutable active-launch images. |
| In-image relay and CLI exec | seams/entrypoint.py | Per-kind relays or SDK consumers starting their own relay. |
| Product startup/process clocks and readiness | seams/readiness.py | Downloads/builds inside startup deadlines, local clock reads, separate creation/probe budgets, ad hoc deadline loops or new fake clocks; tests use tests/support/clock.py. |

| Shared concern | One home | Forbids elsewhere |
|---|---|---|
| Credential-descriptor delivery | seams/credentials.py | Key material in argv, disk files, host-setting discovery or per-launch credential suppliers. |
| Upstream authority, routes and request policy | core/proxy.py using core/records.py:ProxyLimits, ProxyRoute and DEFAULT_PROXY_ROUTES | Configurable authorities, redirect following or per-adapter route tables, merge rules and defaults; validated limits and additive routes enter only through proxy_policy. |
| Real API key and HTTP forwarding | seams/proxy.py | Keys in role containers, SDK options, logs, wrappers or checkpoints. |
| Product process/SDK literal test replies | tests/support/process.py | Local FakeRunner/FakeSdk copies in consumer tests. |
| Product fixtures and crash coordination | existing tests/support/answers.py, recovery.py, lifeline.py | New State/Config factories or child coordination protocols. |
| Workflow/recovery dispatch | seams/resume.py with core/decide.py | Another workflow loop or M2 adapter choosing stages/rounds. |
| Gate infrastructure | existing gates/core/ and tests/support/fake.py | Product imports or M2 ports of gate-only helpers. |

## Order

Each row binds one implementation unit to an agent, at most five written paths and its behavioral contract.

| Step | Agent | Paths written | Required check / dependency |
|---|---|---|---|
| 1 stub | core-builder | gauntlet/core/errors.py | New typed constructors raise only. |
| 2 red | test-writer | tests/test_core_errors.py | New errors preserve safe data and hierarchy; require behavioral failure against stubs. |
| 3 build | core-builder | gauntlet/core/errors.py | Typed-error constructor and hierarchy tests must pass. |
| 3a stub | seam-builder | gauntlet/seams/readiness.py | Complete Clock and SocketReadiness interfaces before process consumers; the Readiness protocol waits for its first consumer at step 22. |
| 3b red | test-writer | tests/test_seams_readiness.py | Start callback and socket events share one deadline; expiry and cleanup fail against stubs using VirtualClock. |
| 3c build | seam-builder | gauntlet/seams/readiness.py | Shared startup-budget, socket-event, expiry and probe-cleanup tests must pass. |
| 3d declaration | core-builder | gauntlet/core/records.py | Add ProxyLimits, ProxyRoute, DEFAULT_PROXY_ROUTES, the ten-second readiness default and all three Config fields. |
| 3e red | test-writer | tests/test_core_config.py, tests/test_core_codec.py, tests/test_seams_config.py | Literal ten-second/default-route/limit values, additive routes, partial overrides, invalid values and all three persisted settings fail before validator/catalog changes. |

| Step | Agent | Paths written | Required check / dependency |
|---|---|---|---|
| 3f build | core-builder | gauntlet/core/config.py, gauntlet/core/codec.py | All three config settings and both proxy records pass catalog/validation tests through canonical defaults, proxy_limits_from_json and proxy_routes_from_json. |
| 3g port | test-writer | tests/support/answers.py, tests/test_support_answers.py | Extend ConfigChanges for all three settings and pin literal fixture defaults/overrides before consumer tests. |
| 4 stub | seam-builder | gauntlet/seams/process.py | Complete process interfaces with readiness.Clock injection. |
| 5 red | test-writer | tests/support/process.py, tests/test_support_process.py | Raise-only FakeRunner/completed contracts and literal ordering, recording and exhaustion tests; require behavioral failure against stubs. FakeSdk waits for step 29. |

| Step | Agent | Paths written | Required check / dependency |
|---|---|---|---|
| 7 port | test-writer | tests/support/process.py | Require literal helpers to satisfy step 5's tests; no SDK imports yet. |
| 8 red | test-writer | tests/test_seams_process.py | Require tests of argv, env, cwd, streams, failure and cleanup to fail against stubs; use harmless real children and lifeline coordination. |
| 9 build | seam-builder | gauntlet/seams/process.py | Process execution and cleanup tests must pass using harmless children. |
| 10 stub | core-builder | gauntlet/core/launch.py | Complete kind/plan contracts. |

| Step | Agent | Paths written | Required check / dependency |
|---|---|---|---|
| 11 red | test-writer | tests/test_core_launch.py | Require tests of six independent literal kind tables and all hardening/network branches to fail against stubs. |
| 12 build | core-builder | gauntlet/core/launch.py | Literal kind-table and hardening tests must pass; one policy per Kind. |
| 13 stub | seam-builder | gauntlet/seams/git.py | Host git/worktree/observation interfaces. |
| 14 red | test-writer | tests/test_seams_git.py | Require explicit-identity, job-lifecycle and intent-observation tests to fail against stubs; use literal commands and real temporary git repos. |
| 15 build | seam-builder | gauntlet/seams/git.py | Explicit-identity, worktree-lifecycle and git-intent tests must pass. |

| Step | Agent | Paths written | Required check / dependency |
|---|---|---|---|
| 16 stub | seam-builder | gauntlet/seams/job.py | Resource/checkpoint additions only. |
| 17 red | test-writer | tests/test_seams_workspace.py | Require snapshot, repeatable restoration, durable labels, staging isolation and publication-failure tests to fail against stubs. |
| 18 build | seam-builder | gauntlet/seams/job.py | Workspace snapshot, restore, ownership and isolation tests must pass alongside existing job tests. |
| 18a stub | seam-builder | gauntlet/seams/mounts.py | Complete source-validation/staging interface. |
| 18b red | test-writer | tests/test_seams_mounts.py | Escapes, symlinks, missing protections, parent exclusion, explicit config staging and helper overlays fail against stubs. |
| 18c build | seam-builder | gauntlet/seams/mounts.py | Source-validation and minimal-tree tests must pass using JobStore-owned staging. |
| 19 stub | seam-builder | gauntlet/seams/images.py | Complete ImagePreparation/ImageBuilder and build/refresh interfaces without a pin manifest. |
| 20 red | test-writer | tests/test_seams_images.py | Current-version assembly, installed reuse, proxy isolation, missing-image acquisition and confirmed identities fail against stubs using FakeRunner. |

| Step | Agent | Paths written | Required check / dependency |
|---|---|---|---|
| 21 build | seam-builder | gauntlet/seams/images.py | Current/installed-version, image-isolation, acquisition-failure and confirmed-identity tests must pass. |
| 22 stub | seam-builder | gauntlet/seams/entrypoint.py, gauntlet/seams/readiness.py | Relay and readiness interfaces, adding the Readiness protocol with its first consumer. |
| 23 red | test-writer | tests/test_seams_entrypoint.py | Relay-start callback, shared timeout, readiness-before-exec and failed-start cleanup fail against stubs. |
| 24 build | seam-builder | gauntlet/seams/entrypoint.py | Relay-start ordering, shared startup budget and cleanup tests must pass. |
| 24a stub | core-builder | gauntlet/core/proxy.py | Fixed-origin request-policy interfaces, canonical route descriptors and extension inputs. |
| 24b red | test-writer | tests/test_core_proxy.py | Literal default/extended routes, query unions, malicious targets, rejected authorities and limit overrides fail against stubs. |
| 24c build | core-builder | gauntlet/core/proxy.py | Default/extended-route, query-union, fixed-authority and adjustable-limit policy tests must pass. |
| 25 stub | seam-builder | gauntlet/seams/proxy.py | Complete secret/HTTPS-forwarding interfaces using the fixed policy. |

| Step | Agent | Paths written | Required check / dependency |
|---|---|---|---|
| 26 red | test-writer | tests/test_seams_proxy.py | Tests cover HTTPS routing to the fixed upstream, route-extension transport, redirects, default/overridden limits, invalid arguments, framing, streaming and secret isolation; require behavioral failure against stubs using local sockets and an injected upstream, without API calls. |
| 27 build | seam-builder | gauntlet/seams/proxy.py | HTTPS, framing, streaming, config limit/route transport and secret-isolation tests must pass. |
| 28 dependency | gatesmith | pyproject.toml, uv.lock | Resolve current SDK/HTTP releases into the installation lock; runtime accepts installed versions without exact release requirements. Land with importing adapters. |
| 28a stub | seam-builder | gauntlet/seams/credentials.py | Complete readable-descriptor source interfaces. |
| 28b red | test-writer | tests/test_seams_credentials.py | Duplicate/close ownership, invalid descriptors and no key in command text fail against stubs. |
| 28c build | seam-builder | gauntlet/seams/credentials.py | Descriptor ownership, validation and credential-isolation tests must pass. |
| 29 stub | seam-builder | gauntlet/seams/launch.py | Complete SDK/lifecycle/recovery contracts, importing shared mount, credential and readiness homes. |
| 29a red | test-writer | tests/support/process.py, tests/test_support_process.py | Raise-only FakeSdk contract and literal reply/call/exhaustion tests after launcher stubs; require behavioral failure against stubs. |

| Step | Agent | Paths written | Required check / dependency |
|---|---|---|---|
| 29c port | test-writer | tests/support/process.py | Require FakeSdk to satisfy step 29a's tests. |
| 30 red | test-writer | tests/test_m2_contract.py | Public assembly has six independently seeded mount/tool expectations and schema addition, with no container started; require behavioral failure against stubs. |
| 31 red | test-writer | tests/test_seams_launch.py | Mount validation, image preparation before deadline/secret creation, pull-disabled runs, SDK options, proxy limits/routes, labels and cleanup fail against stubs. Image-preparation events may exceed the startup budget without expiring it. |
| 31a red | test-writer | tests/test_seams_launch_recovery.py | Durable identities, contradictory ownership, structured absence and removal-before-restore/repeated-recovery tests fail against stubs. |
| 32 build | seam-builder | gauntlet/seams/launch.py | Six-kind assembly, launch and recovery tests must pass through shared planner, lifecycle and recovery helpers. |

Steps 10–12 and 13–15 are independent after the common process/error/helper base. Images, relay and proxy remain separate pieces behind the stated homes; their builders never fill a missing home locally. Their tests exercise new code, not platform restrictions already recorded at `docs/measured.md:9`. The six-kind contract uses independently written expected tables, not KINDS as its oracle. It checks exact mounts, modes, tools, MCP capabilities, hardening and SDK settings together.


