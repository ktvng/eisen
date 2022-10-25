from __future__ import annotations
import glob
from typing import TYPE_CHECKING

from alpaca.validator import AbstractParams, AbstractException
from alpaca.concepts import Context, TypeFactory, TypeClassFactory, TypeClass
from alpaca.config import Config
from alpaca.clr import CLRList

from seer._common import ContextTypes
from seer._oracle import Oracle
from seer._nodedata import NodeData

if TYPE_CHECKING:
    from seer._ast_interpreter import InterpreterObject
    from seer._common import Module, SeerInstance


class SharedBool():
    def __init__(self, value: bool):
        self.value = value
    
    def __bool__(self) -> bool:
        return self.value

    def set(self, value: bool):
        self.value = value

class Params(AbstractParams):
    def __init__(self, 
            config: Config, 
            asl: CLRList, 
            txt: str,
            context: Context,
            mod: Module,
            starting_mod: Module,
            global_mod: Module,
            void_type: TypeClass,
            struct_name: str,
            exceptions: list[AbstractException],
            is_ptr: bool,
            oracle: Oracle,
            critical_exception: SharedBool = SharedBool(False),
            
            # used for interpreter
            objs: dict[str, InterpreterObject] = {},
            ):

        self.config = config
        self.asl = asl
        self.txt = txt
        self.context = context
        self.mod = mod
        self.struct_name = struct_name
        self.starting_mod = starting_mod
        self.global_mod = global_mod
        self.void_type = void_type
        self.exceptions = exceptions
        self.is_ptr = is_ptr
        self.oracle = oracle
        self.critical_exception = critical_exception

        self.objs = objs

    def but_with(self,
            config: Config = None,
            asl: CLRList = None,
            txt: str = None,
            context: Context = None,
            mod: Context = None,
            starting_mod: Context = None,
            global_mod: Context = None,
            struct_name: str = None,
            exceptions: list[AbstractException] = None,
            is_ptr: bool = None,
            oracle: Oracle = None,

            # used for interpreter
            objs: dict[str, InterpreterObject] = None,
            ) -> Params:

        return self._but_with(config=config, asl=asl, txt=txt, context=context, mod=mod, 
            starting_mod=starting_mod,
            struct_name=struct_name, exceptions=exceptions, is_ptr=is_ptr, oracle=oracle,
            objs=objs, global_mod=global_mod, 

            # these cannot be changed by input params 
            void_type=self.void_type, critical_exception=self.critical_exception)

    def report_exception(self, e: AbstractException):
        self.exceptions.append(e)

    def __str__(self) -> str:
        return self.asl.type

    def inspect(self) -> str:
        if isinstance(self.asl, CLRList):
            instances = None
            try:
                instances = self.get_instances(self.asl)
            except:
                pass
            
            instance_strs = ("N/A" if instances is None 
                else ", ".join([str(i) for i in instances]))

            children_strs = []
            for child in self.asl:
                if isinstance(child, CLRList):
                    children_strs.append(f"({child.type} )")
                else:
                    children_strs.append(str(child))
            asl_info_str = f"({self.asl.type} {' '.join(children_strs)})"
            if len(asl_info_str) > 64:
                asl_info_str = asl_info_str[:64] + "..."

            type = "N/A"
            try:
                type = self.oracle.get_propagated_type(self.asl)
            except:
                pass

            return f"""
INSPECT ==================================================
----------------------------------------------------------
ASL: {asl_info_str}
{self.asl}

----------------------------------------------------------
Module: {self.mod.name} {self.mod.type}
{self.mod}

Type: {type}
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
        global_mod.add_type(TypeFactory.produce_novel_type("void"))

        global_mod.add_typeclass(TypeClassFactory.produce_novel_type("int", global_mod=global_mod))
        global_mod.add_typeclass(TypeClassFactory.produce_novel_type("str", global_mod=global_mod))
        global_mod.add_typeclass(TypeClassFactory.produce_novel_type("flt", global_mod=global_mod))
        global_mod.add_typeclass(TypeClassFactory.produce_novel_type("bool", global_mod=global_mod))
        # global_mod.add_typeclass(TypeClassFactory.produce_novel_type("int*", global_mod=global_mod))
        # global_mod.add_typeclass(TypeClassFactory.produce_novel_type("str*", global_mod=global_mod))
        # global_mod.add_typeclass(TypeClassFactory.produce_novel_type("flt*", global_mod=global_mod))
        # global_mod.add_typeclass(TypeClassFactory.produce_novel_type("bool*", global_mod=global_mod))
        # global_mod.add_typeclass(TypeClassFactory.produce_novel_type("int?", global_mod=global_mod))
        # global_mod.add_typeclass(TypeClassFactory.produce_novel_type("str?", global_mod=global_mod))
        # global_mod.add_typeclass(TypeClassFactory.produce_novel_type("flt?", global_mod=global_mod))
        # global_mod.add_typeclass(TypeClassFactory.produce_novel_type("bool?", global_mod=global_mod))
        global_mod.add_typeclass(TypeClassFactory.produce_novel_type("void", global_mod=global_mod))

        void_type = TypeClassFactory.produce_novel_type("void", global_mod=global_mod)
        global_mod.add_typeclass(void_type)

        return Params(
            config=config, 
            asl=asl,
            txt=txt,
            context=None,
            mod=global_mod,
            starting_mod=global_mod,
            global_mod=global_mod,
            void_type=void_type,
            struct_name=None,
            exceptions=[],
            is_ptr=False,
            oracle=Oracle())

    def get_node_data(self) -> NodeData:
        return self.asl.data

    def assign_module(self):
        self.get_node_data().module = self.mod

    def get_module(self) -> Module:
        return self.get_node_data().module

    def assign_returned_typeclass(self, typeclass: TypeClass):
        self.oracle.add_typeclass(self.asl, typeclass)
        # self.get_node_data().returned_typeclass = typeclass

    def get_returned_typeclass(self):
        return self.oracle.get_typeclass(self.asl)

    def assign_instances(self, instances: list[SeerInstance]):
        self.oracle.add_instances(self.asl, instances)

    def get_instances(self) -> list[SeerInstance]:
        return self.oracle.get_instances(self.asl)

    def asl_get_struct_name(self) -> str:
        if isinstance(self.asl, CLRList) and self.asl.type == "struct":
            return self.asl.first().value
        raise Exception(f"cannot call method on {self.asl}")

    def asl_get_interface_name(self) -> str:
        if isinstance(self.asl, CLRList) and self.asl.type == "interface":
            return self.asl.first().value
        raise Exception(f"cannot call method on {self.asl}")

    def get_parent_context(self) -> Context:
        # if no current context, use the module as the parent context
        if self.context is None:
            return self.get_module()
        return self.context

    def get_bool_type(self) -> TypeClass:
        return self.global_mod.get_typeclass_by_name("bool")

    abort_signal = TypeClassFactory.produce_novel_type("_abort_", global_mod=None)