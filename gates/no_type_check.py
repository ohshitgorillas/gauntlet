# Copyright 2026 oh shit, gorillas!
"""Name resolution for the suppression gate: find each reference to a `no_type_check` function in one module, resolving every name by Python's scopes."""

import ast
import bisect
import tokenize
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

TYPING_MODULES = frozenset({"typing", "typing_extensions"})

NO_TYPE_CHECK = frozenset({"no_type_check", "no_type_check_decorator"})


@dataclass(frozen=True)
class Reference:
    """One line that refers to a `no_type_check` function, with every such function it names, joined by commas."""

    line: int
    functions: str


@dataclass(frozen=True)
class Referent:
    """What a binding can make a name refer to: the typing module it names, or the `no_type_check` function it names."""

    module: str | None = None
    function: str | None = None


type ScopeKind = Literal["module", "function", "class", "comprehension", "annotation"]

type Value = Referent | ast.Name | ast.Attribute

type Key = tuple["Scope", str]

type Position = tuple[int, int]


@dataclass(frozen=True)
class Binding:
    """One binding that can make a name refer to a typing module or a `no_type_check` function: a referent it fixes, or a name or attribute it takes, read in `scope`."""

    value: Value
    scope: "Scope"


@dataclass(eq=False)
class Scope:
    """One Python scope: each name bound in it, with every binding there that can make the name a typing module or a `no_type_check` function, and its `global` and `nonlocal` names."""

    kind: ScopeKind
    parent: "Scope | None" = None
    bound: dict[str, list[Binding]] = field(default_factory=dict[str, list[Binding]])
    global_names: set[str] = field(default_factory=set[str])
    nonlocal_names: set[str] = field(default_factory=set[str])

    def bind(
        self, name: str, *values: Value, reader: "Scope | None" = None
    ) -> list[Binding]:
        """Record a binding of `name` made in this scope, which can make it refer to each of `values`, read in `reader`, this scope unless given, and to nothing else, and return the bindings recorded."""
        bindings = [Binding(value, reader or self) for value in values]
        self.bound.setdefault(name, []).extend(bindings)
        return bindings

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

    def classdict(self) -> "Scope | None":
        """Return the class body whose namespace this scope reads before its enclosing scopes: the class an annotation scope, or a chain of them, sits in directly, else None."""
        scope = self
        while scope.kind == "annotation" and scope.parent is not None:
            scope = scope.parent
        return scope if scope is not self and scope.kind == "class" else None

    def outer(self, name: str) -> "Scope | None":
        """Return the nearest enclosing function, annotation or comprehension scope where `name` is local, or None when the name is global there or no such scope binds it."""
        scope = self.enclosing()
        while scope is not None and scope.parent is not None:
            if name in scope.global_names:
                return None
            if name in scope.bound and name not in scope.nonlocal_names:
                return scope
            scope = scope.enclosing()
        return None

    def home(self, name: str) -> "Scope":
        """Return the scope a binding of `name` made here binds in: the module for a `global` name, the scope a `nonlocal` name lives in, else this one."""
        if name in self.global_names:
            return self.module()
        if name in self.nonlocal_names:
            return self.outer(name) or self
        return self

    def homes(self, name: str) -> "list[Scope]":
        """Return each scope whose bindings a use of `name` here can read, by Python's scoping rules.

        A name declared `global` or `nonlocal` here is read where it lives. A name bound here is
        local, but a class body reads one its own namespace lacks from the module. Any other name
        is free: it is read from the nearest enclosing function or annotation scope where it is
        local, else from the module, and an annotation scope inside a class body reads the
        class's namespace first.
        """
        if (
            self.parent is None
            or name in self.global_names
            or name in self.nonlocal_names
        ):
            return [self.home(name)]
        if name in self.bound:
            return [self, self.module()] if self.kind == "class" else [self]
        free = self.outer(name) or self.module()
        classdict = self.classdict()
        return [free] if classdict is None else [classdict, free]

    def assignment_scope(self) -> "Scope":
        """Return the scope an assignment expression here binds its target in: the nearest one that is not a comprehension; its value is still read here."""
        scope = self
        while scope.kind == "comprehension" and scope.parent is not None:
            scope = scope.parent
        return scope


def held(scope: Scope, name: str, referents: dict[Key, set[Referent]]) -> set[Referent]:
    """Return everything a use of `name` in `scope` can refer to: every referent of every binding of it in each scope the use reads."""
    return {
        referent
        for home in scope.homes(name)
        for referent in referents.get((home, name), set[Referent]())
    }


def read_name(expression: ast.Name | ast.Attribute) -> str | None:
    """Return the name whose bindings `expression` depends on: the name itself, or the plain name an attribute is taken of, else None."""
    match expression:
        case ast.Name(id=name) | ast.Attribute(value=ast.Name(id=name)):
            return name
        case _:
            return None


def evaluate(
    expression: ast.Name | ast.Attribute,
    scope: Scope,
    referents: dict[Key, set[Referent]],
) -> set[Referent]:
    """Return what `expression` can refer to in `scope`: what a name can, or the `no_type_check` function an attribute names of a typing module its name can be."""
    match expression:
        case ast.Name(id=name):
            return held(scope, name, referents)
        case ast.Attribute(value=ast.Name(id=name), attr=attribute) if (
            attribute in NO_TYPE_CHECK
        ):
            return {
                Referent(function=f"{referent.module}.{attribute}")
                for referent in held(scope, name, referents)
                if referent.module is not None
            }
        case _:
            return set()


def taken(binding: Binding, referents: dict[Key, set[Referent]]) -> set[Referent]:
    """Return what `binding` can make its name refer to: the referent it fixes, or what the name or attribute it takes can refer to in the scope it is read in."""
    match binding.value:
        case Referent() as referent:
            return {referent}
        case expression:
            return evaluate(expression, binding.scope, referents)


def places(count: int, starred: list[int]) -> tuple[int, int]:
    """Return how many of `count` places unpacking can tell from the front and from the back: every one both ways when none is starred, else those before the first starred place and those after the last."""
    return (starred[0], count - 1 - starred[-1]) if starred else (count, count)


def unpacked(
    target: ast.Tuple | ast.List | ast.MatchSequence, value: ast.expr
) -> list[tuple[ast.expr | ast.pattern, ast.expr]]:
    """Return each part of `target`, a tuple or list target or a sequence pattern, with each item of `value` unpacking can reach it with.

    Only a list, tuple or set display written in place is followed; a value reached through
    another name is not. A starred part takes a list, never an item, and a starred item spreads
    a container reached through another name, so neither is paired. An item of a list or tuple
    reaches the part at its own place, counted from the front before the first starred part or
    item and from the back after the last. An item of a set, whose order is unknown, can reach
    any part of a tuple or list target; a set never matches a sequence pattern, so no item of
    one reaches a part of a sequence pattern.
    """
    parts: Sequence[ast.expr | ast.pattern] = (
        target.patterns if isinstance(target, ast.MatchSequence) else target.elts
    )
    match value:
        case ast.Set(elts=items) if not isinstance(target, ast.MatchSequence):
            return [
                (part, item)
                for part in parts
                if not isinstance(part, ast.Starred)
                for item in items
                if not isinstance(item, ast.Starred)
            ]
        case ast.List(elts=items) | ast.Tuple(elts=items):
            part_front, part_back = places(
                len(parts),
                [
                    index
                    for index, part in enumerate(parts)
                    if isinstance(part, ast.Starred | ast.MatchStar)
                ],
            )
            item_front, item_back = places(
                len(items),
                [
                    index
                    for index, item in enumerate(items)
                    if isinstance(item, ast.Starred)
                ],
            )
            front = [
                (parts[index], items[index])
                for index in range(min(part_front, item_front))
            ]
            return front + [
                (parts[-offset], items[-offset])
                for offset in range(1, min(part_back, item_back) + 1)
            ]
        case _:
            return []


def parameters(arguments: ast.arguments) -> list[ast.arg]:
    """Return every parameter `arguments` declares, positional-only, positional, keyword-only, `*` and `**` alike."""
    optional = [
        parameter
        for parameter in (arguments.vararg, arguments.kwarg)
        if parameter is not None
    ]
    return [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs, *optional]


class Resolver:
    """Find each reference to a `no_type_check` function in one module, resolving every name by Python's scopes.

    No binding is read in order of execution: a use of a name is a reference when any binding
    of the name, in a scope Python's scoping rules resolve the use to, can be the function,
    whether it is conditional, comes after the use, is followed by another binding, is deleted,
    sits behind code that never runs, or is made in a body that never runs, through `global`
    or `nonlocal`. A `for` target and a `match` capture pattern bind to what they take: the
    subject of the `match`, or an item of a list, tuple or set display written in place, save
    that a sequence pattern never matches a set, so its captures over one take nothing; the
    line of a `case` whose captures can take either function is a reference, as an assignment
    line is through its value, and that line is the one its `case` keyword sits on, however
    many lines its pattern spans. A
    generic function, class or type alias reads its type parameters, annotations, bases and
    alias value in an annotation scope of its own, where each type parameter binds to neither
    function; its decorators and default values are read in the scope it is defined in. Nodes
    are scheduled on a stack instead of visited by recursion, so a tree as deep as the parser
    can build is read whole.
    """

    def __init__(self, tokens: Sequence[tokenize.TokenInfo]) -> None:
        """Start with no reference found, given the tokens of the module's source, in source order, the source the tree `run` reads was parsed from.

        The start, line and column, of each name token `case` among them is kept in source
        order, every `case` keyword and any name `case` that is not one, for `case_line` to
        search: the list is built here, from the tokens themselves, so its order and its
        character columns are the ones `case_line` relies on.
        """
        self.case_keywords: list[Position] = [
            token.start
            for token in tokens
            if token.type == tokenize.NAME and token.string == "case"
        ]
        self.references: list[Reference] = []
        self.stack: list[tuple[ast.AST, Scope]] = []
        self.scopes: list[Scope] = []
        self.uses: list[tuple[ast.Name | ast.Attribute, Scope]] = []
        self.cases: list[tuple[int, list[Binding]]] = []

    def run(self, tree: ast.Module) -> list[Reference]:
        """Read `tree` in the module scope and every body defined in it, settle what each name can refer to, and return the references found: each use, and each `case` line, one per case, whose captures can take a `no_type_check` function."""
        self.later(self.scope("module", None), *tree.body)
        while self.stack:
            node, scope = self.stack.pop()
            self.visit(node, scope)
        referents = self.settle()
        for node, scope in self.uses:
            self.refer(node.lineno, evaluate(node, scope, referents))
        for line, captures in self.cases:
            self.refer(
                line,
                {
                    referent
                    for capture in captures
                    for referent in taken(capture, referents)
                },
            )
        return self.references

    def scope(self, kind: ScopeKind, parent: Scope | None) -> Scope:
        """Return a new scope of `kind` inside `parent`, kept to be settled."""
        scope = Scope(kind, parent)
        self.scopes.append(scope)
        return scope

    def case_line(self, pattern: ast.pattern) -> int:
        """Return the line of the `case` keyword `pattern` follows: the last `case` name token before the pattern starts.

        A `case` clause carries no position of its own, and its pattern can start lines below
        its keyword, after an opening parenthesis or a line continuation. Only parentheses,
        comments and line breaks stand between the keyword and the pattern, so no other `case`
        name, a capture named `case` included, comes between them. The pattern's column counts
        bytes and a token's counts characters, but only whitespace, parentheses and the keyword
        itself precede the pattern on its line, so the two agree there.
        """
        before = bisect.bisect_left(
            self.case_keywords, (pattern.lineno, pattern.col_offset)
        )
        return self.case_keywords[before - 1][0]

    def later(self, scope: Scope, *nodes: ast.AST | None) -> None:
        """Schedule each of `nodes` that is present to be read in `scope`."""
        self.stack.extend((node, scope) for node in nodes if node is not None)

    def settle(self) -> dict[Key, set[Referent]]:
        """Return what each name can refer to in each scope it lives in, following every binding that takes another name's referents until none grows."""
        referents: dict[Key, set[Referent]] = {}
        readers: dict[Key, list[tuple[Key, ast.Name | ast.Attribute, Scope]]] = {}
        grown: list[Key] = []
        for scope in self.scopes:
            for name, bindings in scope.bound.items():
                key = (scope.home(name), name)
                for binding in bindings:
                    match binding.value:
                        case Referent() as referent:
                            referents.setdefault(key, set()).add(referent)
                            grown.append(key)
                        case expression:
                            read = read_name(expression)
                            if read is None:
                                continue
                            for home in binding.scope.homes(read):
                                readers.setdefault((home, read), []).append(
                                    (key, expression, binding.scope)
                                )
        while grown:
            for key, expression, scope in readers.get(grown.pop(), []):
                found = evaluate(expression, scope, referents)
                known = referents.setdefault(key, set())
                if not found <= known:
                    known |= found
                    grown.append(key)
        return referents

    def refer(self, line: int, referents: set[Referent]) -> None:
        """Record a reference on `line` naming each `no_type_check` function among `referents`, when there is one."""
        functions = sorted(
            {
                referent.function
                for referent in referents
                if referent.function is not None
            }
        )
        if functions:
            self.references.append(Reference(line=line, functions=", ".join(functions)))

    def assign(self, scope: Scope, target: ast.expr, value: ast.expr) -> None:
        """Bind a plain-name `target` to what `value` can refer to, or schedule any other target to be read and bind each name a tuple or list target takes from `value` to what it takes.

        A tuple or list target is unpacked as a `for` target is: each of its names takes the
        items of a list, tuple or set display written in place that reach it, and a value
        reached through another name is not followed. A name no item reaches, a starred one
        among them, binds to neither function.
        """
        if isinstance(target, ast.Name):
            scope.bind(target.id, *self.values(value))
        else:
            self.later(scope, target)
            self.reach(scope, scope, target, value)

    def values(self, value: ast.expr) -> list[Value]:
        """Return `value` as what a binding to it can refer to when it is a name or an attribute, or nothing when it is any other expression."""
        return [value] if isinstance(value, ast.Name | ast.Attribute) else []

    def reach(
        self,
        scope: Scope,
        reader: Scope,
        target: ast.expr | ast.pattern,
        value: ast.expr,
    ) -> list[Binding]:
        """Bind in `scope` each name that `target`, a `for` target or a `match` pattern, takes from `value`, to what it takes, read in `reader`, and return the bindings made.

        A plain name or a capture pattern takes `value` whole, as each alternative of an
        or-pattern does, and a tuple or list target or a sequence pattern takes the items
        `unpacked` pairs with its parts. A set never matches a sequence pattern, so a sequence
        pattern over a set display takes nothing. Parts are taken from a worklist instead of by
        recursion, as nodes are.
        """
        made: list[Binding] = []
        pending: list[tuple[ast.expr | ast.pattern, ast.expr]] = [(target, value)]
        while pending:
            part, item = pending.pop()
            match part:
                case ast.Name(id=name):
                    made.extend(scope.bind(name, *self.values(item), reader=reader))
                case ast.MatchAs(pattern=inner, name=name):
                    if name is not None:
                        made.extend(scope.bind(name, *self.values(item), reader=reader))
                    if inner is not None:
                        pending.append((inner, item))
                case ast.MatchOr(patterns=alternatives):
                    pending.extend((alternative, item) for alternative in alternatives)
                case ast.Tuple() | ast.List() | ast.MatchSequence():
                    pending.extend(unpacked(part, item))
                case _:
                    pass
        return made

    def iterate(
        self, scope: Scope, reader: Scope, target: ast.expr, iterable: ast.expr
    ) -> None:
        """Bind in `scope` the names of a `for` target to what each item of `iterable`, read in `reader`, reaches them with, when it is a list, tuple or set display written in place; a container reached through another name is not followed."""
        match iterable:
            case ast.List(elts=items) | ast.Tuple(elts=items) | ast.Set(elts=items):
                for item in items:
                    if not isinstance(item, ast.Starred):
                        self.reach(scope, reader, target, item)
            case _:
                pass

    def visit(self, node: ast.AST, scope: Scope) -> None:
        """Read `node` in `scope`: record a use or a binding, or schedule the nodes under it to be read in the scope Python evaluates them in."""
        match node:
            case ast.Name(ctx=ast.Load()):
                self.uses.append((node, scope))
            case ast.Name(id=name):
                scope.bind(name)
            case ast.Attribute(value=value):
                self.uses.append((node, scope))
                self.later(scope, value)
            case ast.Import(names=aliases):
                for alias in aliases:
                    bound = alias.asname or alias.name.partition(".")[0]
                    module = alias.name if alias.asname else bound
                    scope.bind(
                        bound,
                        *(
                            [Referent(module=module)]
                            if module in TYPING_MODULES
                            else []
                        ),
                    )
            case ast.ImportFrom():
                self.import_from(node, scope)
            case ast.Assign(targets=targets, value=value):
                self.later(scope, value)
                for target in targets:
                    self.assign(scope, target, value)
            case ast.AnnAssign(
                target=target, annotation=annotation, value=ast.expr() as value
            ):
                self.later(scope, annotation, value)
                self.assign(scope, target, value)
            case ast.AnnAssign(target=ast.Name(id=name), annotation=annotation):
                self.later(scope, annotation)
                if scope.kind == "function":
                    scope.bind(name)
            case ast.NamedExpr(target=ast.Name(id=name), value=value):
                self.later(scope, value)
                scope.assignment_scope().bind(name, *self.values(value), reader=scope)
            case (
                ast.For(target=target, iter=iterable)
                | ast.AsyncFor(target=target, iter=iterable)
            ):
                self.later(scope, *ast.iter_child_nodes(node))
                self.iterate(scope, scope, target, iterable)
            case ast.Match(subject=subject, cases=cases):
                self.later(scope, *ast.iter_child_nodes(node))
                for case in cases:
                    self.cases.append(
                        (
                            self.case_line(case.pattern),
                            self.reach(scope, scope, case.pattern, subject),
                        )
                    )
            case (
                ast.ListComp(elt=element, generators=generators)
                | ast.SetComp(elt=element, generators=generators)
                | ast.GeneratorExp(elt=element, generators=generators)
            ):
                self.comprehend(scope, generators, element)
            case ast.DictComp(key=key, value=value, generators=generators):
                self.comprehend(scope, generators, key, value)
            case (
                ast.FunctionDef(name=name, args=arguments)
                | ast.AsyncFunctionDef(name=name, args=arguments)
            ):
                self.later(
                    scope,
                    *node.decorator_list,
                    *arguments.defaults,
                    *arguments.kw_defaults,
                )
                scope.bind(name)
                signature = self.generic(scope, node.type_params)
                self.later(signature, *parameters(arguments), node.returns)
                self.function_body(node, signature)
            case ast.Lambda(args=arguments):
                self.later(scope, arguments)
                self.function_body(node, scope)
            case ast.ClassDef(name=name, body=body):
                self.later(scope, *node.decorator_list)
                header = self.generic(scope, node.type_params)
                self.later(header, *node.bases, *node.keywords)
                self.later(self.scope("class", header), *body)
                scope.bind(name)
            case ast.TypeAlias(name=target, type_params=type_params, value=value):
                self.later(scope, target)
                self.later(
                    self.scope("annotation", self.generic(scope, type_params)), value
                )
            case ast.Global(names=names) if scope.parent is not None:
                scope.global_names.update(names)
            case ast.Nonlocal(names=names):
                scope.nonlocal_names.update(names)
            case ast.ExceptHandler(type=kind, name=name, body=body):
                self.later(scope, kind, *body)
                if name is not None:
                    scope.bind(name)
            case ast.MatchAs(name=str() as name) | ast.MatchStar(name=str() as name):
                self.later(scope, *ast.iter_child_nodes(node))
                scope.bind(name)
            case ast.MatchMapping(keys=keys, patterns=patterns, rest=str() as rest):
                self.later(scope, *keys, *patterns)
                scope.bind(rest)
            case _:
                self.later(scope, *ast.iter_child_nodes(node))

    def import_from(self, node: ast.ImportFrom, scope: Scope) -> None:
        """Bind each name `node` imports: a `no_type_check` function from a typing module, its import line a reference, and anything else to neither.

        A star import from a typing module binds both functions; one from any other module
        binds names it does not list, so it binds nothing the gate can name.
        """
        typing = (
            node.module if node.level == 0 and node.module in TYPING_MODULES else None
        )
        for alias in node.names:
            if alias.name == "*":
                if typing is not None:
                    for name in NO_TYPE_CHECK:
                        scope.bind(name, Referent(function=f"{typing}.{name}"))
                continue
            function = (
                f"{typing}.{alias.name}"
                if typing is not None and alias.name in NO_TYPE_CHECK
                else None
            )
            if function is not None:
                self.references.append(Reference(line=alias.lineno, functions=function))
            scope.bind(
                alias.asname or alias.name,
                *([] if function is None else [Referent(function=function)]),
            )

    def comprehend(
        self, scope: Scope, generators: list[ast.comprehension], *results: ast.expr
    ) -> None:
        """Read a comprehension in a scope of its own: its first iterable in `scope`, then each target, condition, later iterable and result inside, each target bound inside to what the items of its iterable reach it with."""
        inner = self.scope("comprehension", scope)
        nodes = [
            part
            for generator in generators
            for part in (generator.iter, generator.target, *generator.ifs)
        ]
        self.later(scope, nodes[0])
        self.later(inner, *nodes[1:], *results)
        for index, generator in enumerate(generators):
            self.iterate(
                inner, inner if index else scope, generator.target, generator.iter
            )

    def generic(self, scope: Scope, type_params: list[ast.type_param]) -> Scope:
        """Return the scope the header of a definition in `scope` is read in: `scope` itself when it declares no type parameter, else an annotation scope of its own where each type parameter binds to neither and its bound is read."""
        if not type_params:
            return scope
        inner = self.scope("annotation", scope)
        for type_param in type_params:
            match type_param:
                case (
                    ast.TypeVar(name=name)
                    | ast.ParamSpec(name=name)
                    | ast.TypeVarTuple(name=name)
                ):
                    inner.bind(name)
                case _:
                    pass
        self.later(inner, *type_params)
        return inner

    def function_body(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda, scope: Scope
    ) -> None:
        """Schedule the body of a function or lambda to be read in a scope of its own inside `scope`, where each parameter binds to neither."""
        inner = self.scope("function", scope)
        for parameter in parameters(node.args):
            inner.bind(parameter.arg)
        if isinstance(node, ast.Lambda):
            self.later(inner, node.body)
        else:
            self.later(inner, *node.body)
