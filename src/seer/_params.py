from __future__ import annotations

from alpaca.validator import AbstractParams, AbstractException
from alpaca.concepts import Context, TypeFactory
from alpaca.config import Config
from alpaca.clr import CLRList

from seer._common import ContextTypes

class Params(AbstractParams):
    def __init__(self, 
            config: Config, 
            asl: CLRList, 
            txt: str,
            mod: Context,
            starting_mod: Context,
            struct_name: str,
            exceptions: list[AbstractException],
            is_ptr: bool,
            ):

        self.config = config
        self.asl = asl
        self.txt = txt
        self.mod = mod
        self.struct_name = struct_name
        self.starting_mod = starting_mod
        self.exceptions = exceptions
        self.is_ptr = is_ptr

    def but_with(self,
            config: Config = None,
            asl: CLRList = None,
            txt: str = None,
            mod: Context = None,
            starting_mod: Config = None,
            struct_name: str = None,
            exceptions: list[AbstractException] = None,
            is_ptr: bool = None,
            ):

        return self._but_with(config=config, asl=asl, txt=txt, mod=mod, starting_mod=starting_mod,
            struct_name=struct_name, exceptions=exceptions, is_ptr=is_ptr)

    def report_exception(self, e: AbstractException):
        self.exceptions.append(e)

    def __str__(self) -> str:
        return self.asl.type

    def inspect(self) -> str:
        if isinstance(self.asl, CLRList):
            instance_strs = ("N/A" if self.asl.instances is None 
                else ", ".join([str(i) for i in self.asl.instances]))

            children_strs = []
            for child in self.asl:
                if isinstance(child, CLRList):
                    children_strs.append(f"({child.type} )")
                else:
                    children_strs.append(str(child))
            asl_info_str = f"({self.asl.type} {' '.join(children_strs)})"
            if len(asl_info_str) > 64:
                asl_info_str = asl_info_str[:64] + "..."

            return f"""
INSPECT ==================================================
----------------------------------------------------------
ASL: {asl_info_str}
{self.asl}

----------------------------------------------------------
Module: {self.mod.name} {self.mod.type}
{self.mod}

Type: {self.asl.returns_type}
Instances: {instance_strs}
"""
        else:
            return f"""
INSPECT ==================================================
Token: {self.asl}
"""

    @classmethod
    def create_initial(cls, config: Config, asl: CLRList, txt: str) -> Params:
        global_mod = Context("global", type=ContextTypes.mod)
        global_mod.add_type(TypeFactory.produce_novel_type("int"))
        global_mod.add_type(TypeFactory.produce_novel_type("str"))
        global_mod.add_type(TypeFactory.produce_novel_type("flt"))
        global_mod.add_type(TypeFactory.produce_novel_type("bool"))
        global_mod.add_type(TypeFactory.produce_novel_type("int*"))
        global_mod.add_type(TypeFactory.produce_novel_type("str*"))
        global_mod.add_type(TypeFactory.produce_novel_type("flt*"))
        global_mod.add_type(TypeFactory.produce_novel_type("bool*"))
        global_mod.add_type(TypeFactory.produce_novel_type("int?"))
        global_mod.add_type(TypeFactory.produce_novel_type("str?"))
        global_mod.add_type(TypeFactory.produce_novel_type("flt?"))
        global_mod.add_type(TypeFactory.produce_novel_type("bool?"))

        return Params(
            config=config, 
            asl=asl,
            txt=txt,
            mod=global_mod,
            starting_mod=global_mod,
            struct_name=None,
            exceptions=[],
            is_ptr=False)
