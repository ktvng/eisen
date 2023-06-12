from __future__ import annotations

from alpaca.concepts import Module, Context, TypeFactory, AbstractParams, AbstractException
from alpaca.config import Config
from alpaca.clr import CLRList

from eisen.common.restriction import PrimitiveRestriction, NoRestriction


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
    attrs = ["config", "asl", "txt", "context", "mod", "exceptions", "critical_exception"]

    def __init__(self,
            config: Config,
            asl: CLRList,
            txt: str,
            context: Context,
            mod: Module,
            exceptions: list[AbstractException],
            critical_exception: SharedBool = SharedBool(False),
            print_to_watcher: bool = False,
            inside_constructor: bool = False,
            watcher: Watcher = None,
            ):

        if watcher is None:
            watcher = Watcher()
        self._init(config=config, asl=asl, txt=txt, context=context,
            mod=mod, exceptions=exceptions, critical_exception=critical_exception,
            print_to_watcher=print_to_watcher, inside_constructor=inside_constructor,
            watcher=watcher)

    def but_with(self,
            asl: CLRList = None,
            context: Context = None,
            mod: Module = None,
            inside_constructor: bool = None
            ) -> BaseState:

        return self._but_with(
            asl=asl,
            context=context,
            mod=mod,
            inside_constructor=inside_constructor)

    @classmethod
    def create_initial(cls, config: Config, asl: CLRList, txt: str, print_to_watcher: bool=False) -> BaseState:
        global_mod = Module("")
        global_mod.add_defined_type("int", TypeFactory.produce_novel_type("int").with_restriction(PrimitiveRestriction()))
        global_mod.add_defined_type("str", TypeFactory.produce_novel_type("str").with_restriction(PrimitiveRestriction()))
        global_mod.add_defined_type("flt", TypeFactory.produce_novel_type("flt").with_restriction(PrimitiveRestriction()))
        global_mod.add_defined_type("bool", TypeFactory.produce_novel_type("bool").with_restriction(PrimitiveRestriction()))
        global_mod.add_defined_type("void", TypeFactory.produce_novel_type("void").with_restriction(NoRestriction()))

        return BaseState(
            config=config,
            asl=asl,
            txt=txt,
            context=None,
            mod=global_mod,
            exceptions=[],
            print_to_watcher=print_to_watcher)
