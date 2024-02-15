from __future__ import annotations

from typing import Self
from alpaca.concepts import Module, Context, TypeFactory, AbstractParams, AbstractException
from alpaca.config import Config
from alpaca.clr import AST

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
            global_module: Module = None
            ):

        if watcher is None:
            watcher = Watcher()
        builtin_functions = {} if builtin_functions is None else builtin_functions
        self._init(config=config, ast=ast, txt=txt, context=context,
            mod=mod, exceptions=exceptions, critical_exception=critical_exception,
            print_to_watcher=print_to_watcher,
            watcher=watcher, builtin_functions=builtin_functions,
            global_module=global_module)

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
        global_mod.add_defined_type("int", TypeFactory.produce_novel_type("int").with_modifier(Binding.data))
        global_mod.add_defined_type("str", TypeFactory.produce_novel_type("str").with_modifier(Binding.data))
        global_mod.add_defined_type("flt", TypeFactory.produce_novel_type("flt").with_modifier(Binding.data))
        global_mod.add_defined_type("bool", TypeFactory.produce_novel_type("bool").with_modifier(Binding.data))
        global_mod.add_defined_type("void", TypeFactory.produce_novel_type("void"))
        global_mod.add_defined_type("Self", TypeFactory.produce_novel_type("Self").with_modifier(Binding.void))

        return BaseState(
            config=config,
            ast=ast,
            txt=txt,
            context=None,
            mod=global_mod,
            exceptions=[],
            print_to_watcher=print_to_watcher,
            global_module=global_mod)
