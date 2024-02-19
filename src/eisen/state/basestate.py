from __future__ import annotations

from typing import Self
from alpaca.concepts import Module, Context, AbstractParams, AbstractException, Corpus, TypeFactory2
from alpaca.config import Config
from alpaca.clr import AST

from eisen.common.typefactory import NewTypeFactory
from eisen.common.eiseninstance import FunctionInstance
from eisen.common.binding import Binding
from eisen.state._basemixins import BaseMixins

class SharedBool():
    def __init__(self, value: bool):
        self.value = value

    def __bool__(self) -> bool:
        return self.value

    def set(self, value: bool):
        self.value = value

class Watcher():
    def __init__(self):
        self.txt = ""

    def write(self, content: str):
        self.txt += content

class SharedCounter():
    def __init__(self, n: int):
        self.value = n

    def __add__(self, other):
        return self.value + other

    def __iadd__(self, other):
        self.value += other
        return self

    def __str__(self):
        return str(self.value)

    def set(self, val: int):
        self.n = val

static_exceptions = []

class BaseState(AbstractParams, BaseMixins):
    attrs = ["config", "ast", "txt", "context", "mod", "exceptions", "critical_exception"]

    def __init__(self,
            config: Config,
            ast: AST,
            txt: str,
            context: Context,
            mod: Module,
            exceptions: list[AbstractException],
            critical_exception: SharedBool = SharedBool(False),
            print_to_watcher: bool = False,
            watcher: Watcher = None,
            builtin_functions: dict[str, FunctionInstance] = None,
            global_module: Module = None,
            corpus: Corpus = None,
            type_factory: TypeFactory2 = None
            ):

        if watcher is None:
            watcher = Watcher()
        builtin_functions = {} if builtin_functions is None else builtin_functions
        self._init(config=config, ast=ast, txt=txt, context=context,
            mod=mod, exceptions=exceptions, critical_exception=critical_exception,
            print_to_watcher=print_to_watcher,
            watcher=watcher, builtin_functions=builtin_functions,
            global_module=global_module, corpus=corpus, type_factory=type_factory)

    def but_with(self,
            ast: AST = None,
            context: Context = None,
            mod: Module = None,
            inside_constructor: bool = None
            ) -> Self:

        return self._but_with(
            ast=ast,
            context=context,
            mod=mod,
            inside_constructor=inside_constructor)

    @classmethod
    def create_initial(cls, config: Config, ast: AST, txt: str, print_to_watcher: bool=False) -> BaseState:
        global_mod = Module("")

        corpus = Corpus()
        factory = NewTypeFactory.get(corpus)
        factory.declare_novel_type("int", namespace="")
        factory.declare_novel_type("str", namespace="")
        factory.declare_novel_type("flt", namespace="")
        factory.declare_novel_type("bool", namespace="")
        factory.declare_void_type(modifier=Binding.void)
        factory.declare_novel_type("Self", namespace="")
        factory.declare_novel_type("_abort_", namespace="_abort_")

        return BaseState(
            config=config,
            ast=ast,
            txt=txt,
            context=None,
            mod=global_mod,
            exceptions=[],
            print_to_watcher=print_to_watcher,
            global_module=global_mod,
            corpus=corpus,
            type_factory=factory)
