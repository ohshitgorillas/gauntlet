# Copyright 2026 oh shit, gorillas!
"""Shell gate: fail on a shell-parsing facility in product code, found by the AST."""

import ast
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from gates.core.report import Finding, Line, Outcome, Unfinished
from gates.core.runner import Gate, Run, run_gate
from gates.core.runner import main as run_main
from gates.core.source import Parsed, parse, pinned_version

PRODUCT = "gauntlet"

PARSING_MODULES = frozenset(
    {"shlex", "bashlex", "bashparser", "bashparserlib", "shellparse"}
)

DYNAMIC_IMPORTS = frozenset({"importlib.import_module", "builtins.__import__"})

SUBPROCESS_CALLS = frozenset(
    f"subprocess.{name}"
    for name in ("run", "Popen", "call", "check_call", "check_output")
)


@dataclass(frozen=True)
class Use:
    """One prohibited use: the line it starts on and what it is."""

    line: int
    construct: str


class Scope:
    """The names one Python scope binds, each with the targets it is bound to; None is a binding that is no import."""

    def __init__(self, parent: "Scope | None", *, is_class: bool = False) -> None:
        """Take the enclosing scope, and whether this one is a class body."""
        self.parent = parent
        self.is_class = is_class
        self.comprehension = False
        self.bindings: dict[str, set[str | None]] = {}
        self.globals: set[str] = set()
        self.nonlocals: set[str] = set()

    def bind(self, name: str, target: str | None = None) -> None:
        """Record a binding of the name: to the dotted name an import gives it, or to None."""
        self.bindings.setdefault(name, set()).add(target)

    def declared_scope(self, name: str) -> "Scope | None":
        """Return the scope a declaration names, once all lexical bindings are collected."""
        current = self
        if name in self.globals:
            while current.parent is not None:
                current = current.parent
            return current
        if name in self.nonlocals:
            enclosing = self.parent
            while enclosing is not None and enclosing.parent is not None:
                if not enclosing.is_class and name not in enclosing.globals:
                    if name in enclosing.nonlocals:
                        return enclosing.declared_scope(name)
                    if name in enclosing.bindings:
                        return enclosing
                enclosing = enclosing.parent
            return None
        return self

    def lookup(self, name: str) -> str | None:
        """Return the dotted name that every binding of the name resolves to, or None when it is not known.

        A class body's names are seen from that body only. A name no scope binds is a builtin.
        """
        current: Scope | None = self
        while current is not None:
            if current is self or not current.is_class:
                declared = current.declared_scope(name)
                if declared is None:
                    return None
                if declared is not current:
                    return declared.lookup(name)
                if name in current.bindings:
                    targets = current.bindings[name]
                    return next(iter(targets)) if len(targets) == 1 else None
            current = current.parent
        return f"builtins.{name}"

    def resolve(self, expression: ast.expr) -> str | None:
        """Return the dotted name an expression of names and attributes stands for, or None when it is not known."""
        match expression:
            case ast.Name(id=name):
                return self.lookup(name)
            case ast.Attribute(value=value, attr=attr):
                base = self.resolve(value)
                return None if base is None else f"{base}.{attr}"
            case _:
                return None

    def binding_scope(self) -> "Scope":
        """Return the nearest scope that is no comprehension, where an assignment expression binds."""
        scope = self
        while scope.comprehension and scope.parent is not None:
            scope = scope.parent
        return scope


def is_parsing_module(module: str) -> bool:
    """Tell whether the dotted module name is one of the parsing modules or a submodule of one."""
    return module.split(".", 1)[0] in PARSING_MODULES


def parameters(arguments: ast.arguments) -> list[ast.arg]:
    """Return every parameter the arguments bind."""
    found = [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]
    if arguments.vararg is not None:
        found.append(arguments.vararg)
    if arguments.kwarg is not None:
        found.append(arguments.kwarg)
    return found


class Collector:
    """Walks a tree once: it binds the names of each scope, and keeps the imports and the calls with their scope."""

    def __init__(self) -> None:
        """Start with an empty module scope."""
        self.module = Scope(None)
        self.scopes = [self.module]
        self.uses: list[Use] = []
        self.calls: list[tuple[ast.Call, Scope]] = []

    def walk_all(self, nodes: Iterable[ast.AST | None], scope: Scope) -> None:
        """Walk each node that is not None in the scope."""
        for node in nodes:
            if node is not None:
                self.walk(node, scope)

    def walk(self, node: ast.AST, scope: Scope) -> None:
        """Walk the node in the scope, binding what it binds and keeping what it imports and calls."""
        match node:
            case ast.Import(names=names):
                for alias in names:
                    if alias.asname is None:
                        top = alias.name.split(".", 1)[0]
                        scope.bind(top, top)
                    else:
                        scope.bind(alias.asname, alias.name)
                    if is_parsing_module(alias.name):
                        self.uses.append(Use(node.lineno, f"import of {alias.name}"))
            case ast.ImportFrom(module=module, names=names, level=0):
                for alias in names:
                    if module is not None and alias.name != "*":
                        scope.bind(alias.asname or alias.name, f"{module}.{alias.name}")
                if module is not None and is_parsing_module(module):
                    self.uses.append(Use(node.lineno, f"import from {module}"))
            case ast.ImportFrom(names=names):
                for alias in names:
                    scope.bind(alias.asname or alias.name)
            case ast.FunctionDef() | ast.AsyncFunctionDef():
                scope.bind(node.name)
                outer = [*node.decorator_list, *node.args.defaults]
                self.walk_all(outer, scope)
                self.walk_all(node.args.kw_defaults, scope)
                annotations = self.type_parameters(node.type_params, scope)
                self.walk_all([node.returns], annotations)
                self.walk_all(
                    (arg.annotation for arg in parameters(node.args)), annotations
                )
                self.function(node.args, node.body, annotations)
            case ast.Lambda():
                self.walk_all([*node.args.defaults, *node.args.kw_defaults], scope)
                self.function(node.args, [node.body], scope)
            case ast.ClassDef():
                scope.bind(node.name)
                self.walk_all(node.decorator_list, scope)
                annotations = self.type_parameters(node.type_params, scope)
                self.walk_all(node.bases, annotations)
                self.walk_all(node.keywords, annotations)
                inner = Scope(annotations, is_class=True)
                self.scopes.append(inner)
                self.walk_all(node.body, inner)
            case ast.ListComp() | ast.SetComp() | ast.GeneratorExp() | ast.DictComp():
                self.comprehension(node, scope)
            case ast.NamedExpr(target=target, value=value):
                scope.binding_scope().bind(target.id)
                self.walk(value, scope)
            case ast.Name(id=name, ctx=ast.Store() | ast.Del()):
                scope.bind(name)
            case ast.ExceptHandler(name=name) if name is not None:
                scope.bind(name)
                self.walk_all(ast.iter_child_nodes(node), scope)
            case ast.MatchAs(name=name) | ast.MatchStar(name=name) if name is not None:
                scope.bind(name)
                self.walk_all(ast.iter_child_nodes(node), scope)
            case ast.MatchMapping(rest=rest) if rest is not None:
                scope.bind(rest)
                self.walk_all(ast.iter_child_nodes(node), scope)
            case ast.Global(names=names):
                scope.globals.update(names)
            case ast.Nonlocal(names=names):
                scope.nonlocals.update(names)
            case ast.Call():
                self.calls.append((node, scope))
                self.walk_all(ast.iter_child_nodes(node), scope)
            case _:
                self.walk_all(ast.iter_child_nodes(node), scope)

    def type_parameters(
        self, parameters: Sequence[ast.type_param], scope: Scope
    ) -> Scope:
        """Walk generic bounds in the annotation scope that binds the type parameters."""
        if not parameters:
            return scope
        inner = Scope(scope)
        self.scopes.append(inner)
        for parameter in parameters:
            match parameter:
                case (
                    ast.TypeVar(name=name)
                    | ast.ParamSpec(name=name)
                    | ast.TypeVarTuple(name=name)
                ):
                    inner.bind(name)
                case _:
                    pass
        self.walk_all(parameters, inner)
        return inner

    def function(
        self, arguments: ast.arguments, body: Sequence[ast.AST], scope: Scope
    ) -> None:
        """Walk a function's body in a scope of its own that binds its parameters."""
        inner = Scope(scope)
        self.scopes.append(inner)
        for parameter in parameters(arguments):
            inner.bind(parameter.arg)
        self.walk_all(body, inner)

    def comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp,
        scope: Scope,
    ) -> None:
        """Walk a comprehension: its first iterable in the enclosing scope, the rest in a scope of its own."""
        inner = Scope(scope)
        self.scopes.append(inner)
        inner.comprehension = True
        for index, generator in enumerate(node.generators):
            if index == 0:
                self.walk(generator.iter, scope)
            else:
                self.walk(generator.iter, inner)
            self.walk(generator.target, inner)
            self.walk_all(generator.ifs, inner)
        if isinstance(node, ast.DictComp):
            self.walk_all([node.key, node.value], inner)
        else:
            self.walk(node.elt, inner)


def call_uses(call: ast.Call, scope: Scope) -> list[Use]:
    """Return the prohibited uses a call is: a literal parsing-module name to a dynamic import, or shell=True to subprocess."""
    target = scope.resolve(call.func)
    if target in DYNAMIC_IMPORTS:
        names = [*call.args[:1], *(k.value for k in call.keywords if k.arg == "name")]
        return [
            Use(call.lineno, f"dynamic import of {name.value}")
            for name in names
            if isinstance(name, ast.Constant)
            and isinstance(name.value, str)
            and is_parsing_module(name.value)
        ]
    if target in SUBPROCESS_CALLS:
        return [
            Use(call.lineno, f"shell=True passed to {target}")
            for keyword in call.keywords
            if keyword.arg == "shell"
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is True
        ]
    return []


def use_line(use: Use) -> int:
    """Return the line a use starts on, the key uses are put in line order by."""
    return use.line


def parsing_findings(parsed: Parsed) -> tuple[Finding, ...]:
    """Return one finding per prohibited use in the parsed file, in line order: its anchor and the construct."""
    collector = Collector()
    collector.walk(parsed.tree, collector.module)
    for scope in collector.scopes:
        for name in scope.globals | scope.nonlocals:
            declared = scope.declared_scope(name)
            if declared is not None and declared is not scope:
                targets = scope.bindings.pop(name, set())
                if targets:
                    declared.bindings.setdefault(name, set()).update(targets)
    uses = list(collector.uses)
    for call, scope in collector.calls:
        uses.extend(call_uses(call, scope))
    return tuple(
        Finding(f"{parsed.source.given}:{use.line}: {use.construct}")
        for use in sorted(uses, key=use_line)
    )


def check(run: Run) -> Outcome:
    """Parse every file of the run under the pinned grammar and list the prohibited uses in the files under gauntlet/.

    A file that cannot be parsed, or whose tree is too deep to walk, is one the gate did not finish. GateError when the
    project pins no Python.
    """
    version = pinned_version(run.project)
    product = run.project.root / PRODUCT
    lines: list[Line] = []
    for source in run.sources:
        parsed = parse(source, version)
        if isinstance(parsed, Unfinished):
            lines.append(parsed)
        elif source.absolute.is_relative_to(product):
            try:
                lines.extend(parsing_findings(parsed))
            except RecursionError as error:
                lines.append(Unfinished(f"{source.given}: RecursionError: {error}"))
    return Outcome(lines=tuple(lines))


GATE = Gate(name="check_shell", check=check)


def main(paths: Sequence[Path]) -> int:
    """Run the gate over the paths, in the working directory's project, and return its exit code."""
    return run_gate(GATE, paths)


if __name__ == "__main__":
    run_main(GATE)
