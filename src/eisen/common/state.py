from __future__ import annotations
from typing import TYPE_CHECKING

from alpaca.validator import AbstractParams, AbstractException
from alpaca.concepts import Context, TypeClassFactory, TypeClass
from alpaca.config import Config
from alpaca.clr import CLRList

from eisen.common import ContextTypes
from eisen.common.nodedata import NodeData
from eisen.common import Module, EisenInstance

if TYPE_CHECKING:
    from eisen.ast_interpreter import InterpreterObject
    from eisen.common.restriction import Restriction


class SharedBool():
    def __init__(self, value: bool):
        self.value = value
    
    def __bool__(self) -> bool:
        return self.value

    def set(self, value: bool):
        self.value = value

class State(AbstractParams):
    def __init__(self, 
            config: Config, 
            asl: CLRList, 
            txt: str,
            context: Context,
            mod: Module,
            global_mod: Module,
            struct_name: str,
            exceptions: list[AbstractException],
            is_ptr: bool,
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
        self.global_mod = global_mod
        self.exceptions = exceptions
        self.is_ptr = is_ptr
        self.critical_exception = critical_exception

        self.objs = objs

    def but_with(self,
            config: Config = None,
            asl: CLRList = None,
            txt: str = None,
            context: Context = None,
            mod: Context = None,
            global_mod: Context = None,
            struct_name: str = None,
            exceptions: list[AbstractException] = None,
            is_ptr: bool = None,

            # used for interpreter
            objs: dict[str, InterpreterObject] = None,
            ) -> State:

        return self._but_with(config=config, asl=asl, txt=txt, context=context, mod=mod, 
            struct_name=struct_name, exceptions=exceptions, is_ptr=is_ptr,
            objs=objs,global_mod=global_mod,

            # these cannot be changed by input params 
            critical_exception=self.critical_exception)

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
                type = self.get_node_data().returned_typeclass
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
    def create_initial(cls, config: Config, asl: CLRList, txt: str) -> State:
        global_mod = Context("global", type=ContextTypes.mod)
        global_mod.add_typeclass(TypeClassFactory.produce_novel_type("int"))
        global_mod.add_typeclass(TypeClassFactory.produce_novel_type("str"))
        global_mod.add_typeclass(TypeClassFactory.produce_novel_type("flt"))
        global_mod.add_typeclass(TypeClassFactory.produce_novel_type("bool"))
        global_mod.add_typeclass(TypeClassFactory.produce_novel_type("void"))

        return State(
            config=config, 
            asl=asl,
            txt=txt,
            context=None,
            mod=global_mod,
            global_mod=global_mod,
            struct_name=None,
            exceptions=[],
            is_ptr=False)

    def get_node_data(self) -> NodeData:
        return self.asl.data

    def get_context(self) -> Context | Module:
        if self.context is not None:
            return self.context
        return self.mod

    def get_enclosing_module(self) -> Module:
        return self.mod

    def assign_returned_typeclass(self, typeclass: TypeClass):
        self.get_node_data().returned_typeclass = typeclass

    def get_returned_typeclass(self) -> TypeClass:
        return self.get_node_data().returned_typeclass

    def assign_instances(self, instances: list[EisenInstance] | EisenInstance):
        if isinstance(instances, EisenInstance):
            instances = [instances]
        self.get_node_data().instances = instances

    def get_instances(self) -> list[EisenInstance]:
        return self.get_node_data().instances

    def get_parent_context(self) -> Context:
        # if no current context, use the module as the parent context
        if self.context is None:
            return self.get_enclosing_module()
        return self.context

    def get_bool_type(self) -> TypeClass:
        return TypeClassFactory.produce_novel_type("bool")

    abort_signal = TypeClassFactory.produce_novel_type("_abort_")

    def but_with_first_child(self) -> State:
        return self.but_with(asl=self.first_child())

    def but_with_second_child(self) -> State:
        return self.but_with(asl=self.second_child())

    def first_child(self) -> CLRList:
        return self.asl.first()

    def second_child(self) -> CLRList:
        return self.asl.second()

    def third_child(self) -> CLRList:
        return self.asl.third()

    def get_child_asls(self) -> list[CLRList]:
        return [child for child in self.asl if isinstance(child, CLRList)]

    def get_all_children(self) -> list[CLRList]:
        return self.asl._list

    def add_restriction(self, name: str, restriction: Restriction):
        self.context.add_obj("restriction", name, restriction)
    
    def get_restriction_for(self, name: str) -> Restriction:
        return self.context.get_obj("restriction", name)

    def apply_fn_to_all_children(self, fn):
        for child in self.asl:
            fn.apply(self.but_with(asl=child))

    def get_void_type(self) -> TypeClass:
        return TypeClassFactory.produce_novel_type("void")

    def get_asl(self) -> CLRList:
        return self.asl

    def get_line_number(self) -> int:
        return self.asl.line_number

    def is_asl(self) -> bool:
        return isinstance(self.asl, CLRList)

    def create_block_context(self, name: str) -> Context:
        return Context(
            name=name,
            type=ContextTypes.block,
            parent=self.get_parent_context())
