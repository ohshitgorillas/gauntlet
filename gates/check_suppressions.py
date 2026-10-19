"""Suppression gate: fail on any comment that silences a checker, and on any reference to `typing.no_type_check`."""

import ast
import errno
import io
import re
import stat
import sys
import tokenize
import tomllib
import warnings
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

MARKERS: dict[str, re.Pattern[str]] = {
    "noqa": re.compile(r"noqa", re.IGNORECASE),
    "type: ignore": re.compile(r"type\s*:\s*ignore", re.IGNORECASE),
    "pyright: ignore": re.compile(r"pyright\s*:\s*ignore", re.IGNORECASE),
    "pragma: no cover": re.compile(r"pragma\s*:\s*no\s*cover", re.IGNORECASE),
    "pragma: no mutate": re.compile(r"pragma\s*:\s*no\s*mutate", re.IGNORECASE),
    "# mypy:": re.compile(r"mypy\s*:", re.IGNORECASE),
    "# pyright:": re.compile(r"pyright\s*:", re.IGNORECASE),
    "# fmt: off": re.compile(r"fmt\s*:\s*off", re.IGNORECASE),
    "# fmt: skip": re.compile(r"fmt\s*:\s*skip", re.IGNORECASE),
}

TYPING_MODULES = frozenset({"typing", "typing_extensions"})

NO_TYPE_CHECK = frozenset({"no_type_check", "no_type_check_decorator"})

CONFIG = Path(__file__).resolve().parent.parent / "pyproject.toml"

PYTHON_SUFFIXES = (".py", ".pyi")

PYTHON_SHEBANG = re.compile(rb"^#!.*python")

NAMES_NOTHING = frozenset({errno.ENOENT, errno.ENOTDIR})

BLOCKED = 2


@dataclass(frozen=True, order=True)
class Suppression:
    """One finding: where it is, what kind it is, and what it names; findings order by path, then line.

    A comment finding names every marker its comment carries; a reference finding names the
    `no_type_check` function the line refers to.
    """

    path: Path
    line: int
    kind: str
    marker: str


def is_python_source(path: Path) -> bool:
    """Return whether `path` is a Python file: a name ending in `.py` or `.pyi`, or an extensionless file whose first line is a python shebang.

    A path named as a Python file, or an extensionless one, that cannot be told to be a file,
    as under a directory it may not search, or an extensionless file whose first line cannot be
    read, may be a Python file, and nothing short of reading it tells, so it is taken as one:
    the gate hands it to its checker, which reports that it could not read it, and the gate
    exits 2 on a file it could not finish instead of skipping it or dying before any check runs.
    Only a path that names nothing, because it or one of its directories does not exist, is
    told not to be a file by its failure. The path is stat'ed here, not asked `Path.is_file()`,
    which reports False on any error and so cannot tell the two apart.
    """
    named = path.name.endswith(PYTHON_SUFFIXES)
    if not named and path.suffix:
        return False
    try:
        if not stat.S_ISREG(path.stat().st_mode):
            return False
        if named:
            return True
        with path.open("rb") as source:
            first_line = source.readline()
    except OSError as error:
        return error.errno not in NAMES_NOTHING
    return PYTHON_SHEBANG.match(first_line) is not None


@dataclass(frozen=True)
class Unfinished:
    """A Python file the gate could not read, tokenize or parse, with what it reported for that file."""

    path: Path
    report: str


def comment_suppressions(path: Path, source: str) -> list[Suppression]:
    """Return one finding per comment token of `source` that carries a marker, naming every marker it carries."""
    comments = [token for token in tokenize.generate_tokens(io.StringIO(source).readline) if token.type == tokenize.COMMENT]
    carried = [(comment.start[0], [marker for marker, pattern in MARKERS.items() if pattern.search(comment.string)]) for comment in comments]
    return [Suppression(path=path, line=line, kind="suppression comment", marker=", ".join(markers)) for line, markers in carried if markers]


@dataclass(frozen=True)
class Referent:
    """What a name is bound to: the typing module it names, the `no_type_check` function it names, or neither when both are None."""

    module: str | None = None
    function: str | None = None


OTHER = Referent()

type ScopeKind = Literal["module", "function", "class", "comprehension"]

type Task = Callable[[], None]


@dataclass(eq=False)
class Scope:
    """One Python scope: what each name bound in it so far refers to, and the scope each of its `global` and `nonlocal` names lives in."""

    kind: ScopeKind
    parent: "Scope | None" = None
    names: dict[str, Referent] = field(default_factory=dict[str, Referent])
    declared: "dict[str, Scope]" = field(default_factory=dict[str, "Scope"])

    def bind(self, name: str, referent: Referent) -> None:
        """Bind `name` to `referent` in the scope the name lives in."""
        self.declared.get(name, self).names[name] = referent

    def lookup(self, name: str) -> Referent:
        """Return what `name` refers to here: its binding in this scope, else in the nearest enclosing scope that binds it, else neither."""
        if name in self.declared:
            return self.declared[name].lookup(name)
        scope: Scope | None = self
        while scope is not None:
            if name in scope.names:
                return scope.names[name]
            scope = scope.enclosing()
        return OTHER

    def enclosing(self) -> "Scope | None":
        """Return the nearest enclosing scope whose names code in this scope sees; a class body's names are seen only by that body."""
        scope = self.parent
        while scope is not None and scope.kind == "class":
            scope = scope.parent
        return scope

    def module(self) -> "Scope":
        """Return the module scope, where a `global` name lives."""
        scope = self
        while scope.parent is not None:
            scope = scope.parent
        return scope

    def binder(self, name: str) -> "Scope | None":
        """Return the nearest enclosing function scope that binds `name`, where a `nonlocal` name lives, or None when none does."""
        scope = self.enclosing()
        while scope is not None and (scope.kind != "function" or name not in scope.names):
            scope = scope.enclosing()
        return scope

    def assignment_scope(self) -> "Scope":
        """Return the scope an assignment expression here binds in: the nearest one that is not a comprehension."""
        scope = self
        while scope.kind == "comprehension" and scope.parent is not None:
            scope = scope.parent
        return scope

    def referent(self, node: ast.expr) -> Referent:
        """Return what the expression `node` refers to here: a name's binding, a typing module's `no_type_check` function named as its attribute, or neither."""
        match node:
            case ast.Name(id=name):
                return self.lookup(name)
            case ast.Attribute(value=ast.Name(id=name), attr=attribute) if attribute in NO_TYPE_CHECK:
                module = self.lookup(name).module
                return OTHER if module is None else Referent(function=f"{module}.{attribute}")
            case _:
                return OTHER


class Resolver:
    """Find each reference to a `no_type_check` function in one module, resolving every name by Python's scopes.

    Each scope is read in source order, so a name refers to what its latest binding before the
    read made it: an import, a def or class, an assignment, a parameter, a loop or comprehension
    target, or any other binding. A function or lambda body is read after the scope it is
    defined in, as it runs when called. Nodes are scheduled on a stack instead of visited by
    recursion, so a tree as deep as the parser can build is read whole.
    """

    def __init__(self, path: Path) -> None:
        """Start with no finding for the file at `path`."""
        self.path = path
        self.findings: list[Suppression] = []
        self.stack: list[Task] = []
        self.deferred: deque[Task] = deque()

    def run(self, tree: ast.Module) -> list[Suppression]:
        """Read `tree` in the module scope and every body defined in it, and return the references found."""
        self.later(Scope("module"), *tree.body)
        while self.stack or self.deferred:
            task = self.stack.pop() if self.stack else self.deferred.popleft()
            task()
        return self.findings

    def then(self, *tasks: Task) -> None:
        """Schedule `tasks` to run next, in order."""
        self.stack.extend(reversed(tasks))

    def visiting(self, scope: Scope, node: ast.AST) -> Task:
        """Return a task that reads `node` in `scope`."""
        return lambda: self.visit(node, scope)

    def later(self, scope: Scope, *nodes: ast.AST | None) -> None:
        """Schedule each of `nodes` that is present to be read next in `scope`, in order."""
        self.then(*(self.visiting(scope, node) for node in nodes if node is not None))

    def naming(self, scope: Scope, name: str | None) -> list[Task]:
        """Return a task that binds `name` in `scope` to neither a typing module nor a `no_type_check` function, or none when there is no name."""
        if name is None:
            return []
        return [lambda: scope.bind(name, OTHER)]

    def binding(self, scope: Scope, name: str, value: ast.expr, home: Scope) -> Task:
        """Return a task that binds `name` in `home` to what `value` refers to in `scope`."""
        return lambda: home.bind(name, scope.referent(value))

    def assigning(self, scope: Scope, target: ast.expr, value: ast.expr) -> Task:
        """Return a task that binds a plain-name `target` to what `value` refers to, or reads any other target, whose names bind to neither."""
        if isinstance(target, ast.Name):
            return self.binding(scope, target.id, value, scope)
        return self.visiting(scope, target)

    def refer(self, node: ast.Name | ast.Attribute, referent: Referent) -> None:
        """Record a finding on the line of `node` when `referent` is a `no_type_check` function."""
        if referent.function is not None:
            self.findings.append(Suppression(path=self.path, line=node.lineno, kind="reference to", marker=referent.function))

    def visit(self, node: ast.AST, scope: Scope) -> None:
        """Read `node` in `scope`: record a reference, apply a binding, or schedule the nodes under it in the order and scope Python evaluates them."""
        match node:
            case ast.Name(id=name, ctx=ast.Load()):
                self.refer(node, scope.lookup(name))
            case ast.Name(id=name):
                scope.bind(name, OTHER)
            case ast.Attribute(value=value):
                self.refer(node, scope.referent(node))
                self.later(scope, value)
            case ast.Import(names=aliases):
                for alias in aliases:
                    bound = alias.asname or alias.name.partition(".")[0]
                    module = alias.name if alias.asname else bound
                    scope.bind(bound, Referent(module=module) if module in TYPING_MODULES else OTHER)
            case ast.ImportFrom():
                self.import_from(node, scope)
            case ast.Assign(targets=targets, value=value):
                self.then(self.visiting(scope, value), *(self.assigning(scope, target, value) for target in targets))
            case ast.AnnAssign(target=target, annotation=annotation, value=ast.expr() as value):
                self.then(self.visiting(scope, annotation), self.visiting(scope, value), self.assigning(scope, target, value))
            case ast.AnnAssign(target=ast.Name(), annotation=annotation):
                self.later(scope, annotation)
            case ast.NamedExpr(target=ast.Name(id=name), value=value):
                self.then(self.visiting(scope, value), self.binding(scope, name, value, scope.assignment_scope()))
            case ast.For(target=target, iter=iterable, body=body, orelse=orelse) | ast.AsyncFor(target=target, iter=iterable, body=body, orelse=orelse):
                self.later(scope, iterable, target, *body, *orelse)
            case ast.ListComp(elt=element, generators=generators) | ast.SetComp(elt=element, generators=generators) | ast.GeneratorExp(elt=element, generators=generators):
                self.comprehend(scope, generators, element)
            case ast.DictComp(key=key, value=value, generators=generators):
                self.comprehend(scope, generators, key, value)
            case ast.FunctionDef(name=name) | ast.AsyncFunctionDef(name=name):
                self.then(*(self.visiting(scope, part) for part in (*node.decorator_list, node.args, *([] if node.returns is None else [node.returns]), *node.type_params)), *self.naming(scope, name))
                self.deferred.append(lambda: self.function_body(node, scope))
            case ast.Lambda(args=arguments):
                self.later(scope, arguments)
                self.deferred.append(lambda: self.function_body(node, scope))
            case ast.ClassDef(name=name, body=body):
                inner = Scope("class", scope)
                head = (*node.decorator_list, *node.bases, *node.keywords, *node.type_params)
                self.then(*(self.visiting(scope, part) for part in head), *(self.visiting(inner, statement) for statement in body), *self.naming(scope, name))
            case ast.Global(names=names):
                scope.declared.update(dict.fromkeys(names, scope.module()))
            case ast.Nonlocal(names=names):
                scope.declared.update({name: binder for name in names if (binder := scope.binder(name)) is not None})
            case ast.ExceptHandler(type=kind, name=name, body=body):
                self.then(*(self.visiting(scope, part) for part in ([] if kind is None else [kind])), *self.naming(scope, name), *(self.visiting(scope, statement) for statement in body))
            case ast.MatchAs(pattern=pattern, name=name):
                self.then(*(self.visiting(scope, part) for part in ([] if pattern is None else [pattern])), *self.naming(scope, name))
            case ast.MatchStar(name=name):
                self.then(*self.naming(scope, name))
            case ast.MatchMapping(keys=keys, patterns=patterns, rest=rest):
                self.then(*(self.visiting(scope, part) for part in (*keys, *patterns)), *self.naming(scope, rest))
            case _:
                self.later(scope, *ast.iter_child_nodes(node))

    def import_from(self, node: ast.ImportFrom, scope: Scope) -> None:
        """Bind each name `node` imports: a `no_type_check` function from a typing module, its import line a finding, and anything else to neither.

        A star import from a typing module binds both functions; one from any other module
        binds names it does not list, so it leaves every binding as it was.
        """
        typing = node.module if node.level == 0 and node.module in TYPING_MODULES else None
        for alias in node.names:
            if alias.name == "*":
                if typing is not None:
                    for name in NO_TYPE_CHECK:
                        scope.bind(name, Referent(function=f"{typing}.{name}"))
                continue
            function = f"{typing}.{alias.name}" if typing is not None and alias.name in NO_TYPE_CHECK else None
            if function is not None:
                self.findings.append(Suppression(path=self.path, line=alias.lineno, kind="reference to", marker=function))
            scope.bind(alias.asname or alias.name, Referent(function=function))

    def comprehend(self, scope: Scope, generators: list[ast.comprehension], *results: ast.expr) -> None:
        """Read a comprehension in a scope of its own: its first iterable in `scope`, then each target, condition, later iterable and result inside."""
        inner = Scope("comprehension", scope)
        nodes = [part for generator in generators for part in (generator.iter, generator.target, *generator.ifs)]
        self.then(self.visiting(scope, nodes[0]), *(self.visiting(inner, part) for part in (*nodes[1:], *results)))

    def function_body(self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, scope: Scope) -> None:
        """Read the body of a function or lambda defined in `scope`, in a scope of its own where each parameter binds to neither."""
        inner = Scope("function", scope)
        arguments = node.args
        optional = [parameter for parameter in (arguments.vararg, arguments.kwarg) if parameter is not None]
        for parameter in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs, *optional):
            inner.bind(parameter.arg, OTHER)
        if isinstance(node, ast.Lambda):
            self.later(inner, node.body)
        else:
            self.later(inner, *node.body)


def no_type_check_references(path: Path, tree: ast.Module) -> list[Suppression]:
    """Return one finding per reference in `tree` to `no_type_check` or `no_type_check_decorator` of `typing` or `typing_extensions`.

    A reference is a name importing the function, a read of a name whose binding at that point
    in its scope is the function, by an import, a star import or an assignment from another
    reference, and an attribute naming it of a name bound at that point to a typing module, by
    an import or by an assignment from another such name. A name a parameter, def, class,
    other import, assignment or loop target has bound since refers to the function no more.
    """
    return Resolver(path).run(tree)


def pinned_grammar() -> tuple[int, int] | None:
    """Return the Python version the tree is pinned to, as `(major, minor)`: pyright's `pythonVersion` in `pyproject.toml`, or None when that is not set, since pyright then takes the version of the interpreter the gate hands it, the one `ast` parses with by default.

    The pin is read from `pyproject.toml` on every call, never kept in a gate, so a gate that
    parses with it parses with the grammar the type checkers take from the same file.
    """
    with CONFIG.open("rb") as config:
        settings: object = tomllib.load(config)
    match settings:
        case {"tool": {"pyright": {"pythonVersion": str() as version}}}:
            major, minor, *_ = version.split(".")
            return int(major), int(minor)
        case _:
            return None


def parse_pinned(path: Path, source: str) -> ast.Module:
    """Parse `source` with the grammar of the pinned Python, `pinned_grammar`, raising `SyntaxError` on what that grammar cannot parse.

    A source nested deeper than the parser can go cannot be parsed either: the parser raises
    `MemoryError` when its stack overflows, and `RecursionError` when building the tree of a
    parse runs past the recursion limit.

    A `SyntaxWarning` the parse raises, such as an invalid escape sequence, says nothing about
    the grammar, so it is kept out of the warning filters of whoever runs the gate and cannot
    turn a file that parses into one the gate did not finish.
    """
    with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
        return ast.parse(source, filename=str(path), feature_version=pinned_grammar())


def find_suppressions(path: Path) -> list[Suppression]:
    """Return every suppression comment and every `no_type_check` reference in the Python file at `path`, in line order.

    Raise `OSError` when the file, or the `pyproject.toml` that holds the pin, cannot be read, `SyntaxError`, `UnicodeDecodeError` or
    `tokenize.TokenError` when it cannot be decoded or tokenized, `SyntaxError` when the
    grammar of the pinned Python cannot parse it, and `MemoryError` or `RecursionError` when
    its parse runs deeper than the parser can go.
    """
    with tokenize.open(path) as reader:
        source = reader.read()
    comments = comment_suppressions(path, source)
    references = no_type_check_references(path, parse_pinned(path, source))
    return sorted(comments + references)


def scan(path: Path) -> list[Suppression] | Unfinished:
    """Return every finding in the Python file at `path`, or what the gate reported when it could not read, tokenize or parse that file."""
    try:
        return find_suppressions(path)
    except (OSError, SyntaxError, UnicodeDecodeError, tokenize.TokenError, MemoryError, RecursionError) as error:
        return Unfinished(path=path, report=f"{type(error).__name__}: {error}")


def main(paths: list[Path]) -> int:
    """List every suppression comment and `no_type_check` reference found in the Python files among `paths`.

    When every file was parsed, print a count line and exit 1 on any finding and 0 on none.
    A file the gate cannot read, tokenize or parse is one it did not finish: print each
    finding of the other files all the same, then what the gate reported for each such
    file, then a count line saying on how many files it could not finish and with how many
    findings, and exit 2. When no path is a Python file, nothing was checked: print a line
    saying so and exit 1.
    """
    sources = [path for path in paths if is_python_source(path)]
    if not sources:
        sys.stdout.write(f"check_suppressions: no Python file among {len(paths)} path(s); nothing was checked\n")
        return 1
    scans = [scan(path) for path in sources]
    found = [suppression for scanned in scans if not isinstance(scanned, Unfinished) for suppression in scanned]
    unfinished = [scanned for scanned in scans if isinstance(scanned, Unfinished)]
    for suppression in found:
        sys.stdout.write(f"{suppression.path}:{suppression.line}: {suppression.kind} `{suppression.marker}`\n")
    for file in unfinished:
        sys.stdout.write(f"{file.path}: {file.report}\n")
    if unfinished:
        sys.stdout.write(f"check_suppressions: the gate could not finish on {len(unfinished)} of {len(sources)} Python file(s), with {len(found)} finding(s)\n")
        return BLOCKED
    sys.stdout.write(f"check_suppressions: {len(found)} finding(s) in {len(sources)} Python file(s)\n")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
