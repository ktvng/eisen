from __future__ import annotations
from typing import TYPE_CHECKING

from alpaca.concepts import Module, Context, TypeFactory, Type, AbstractParams, AbstractException
from alpaca.config import Config
from alpaca.clr import CLRList

from eisen.common.nodedata import NodeData
from eisen.common.eiseninstance import EisenInstance
from eisen.common.restriction import PrimitiveRestriction, NoRestriction, FunctionalRestriction
from eisen.validation.lookupmanager import LookupManager

if TYPE_CHECKING:
    from eisen.interpretation.obj import Obj
    from eisen.common.eiseninstancestate import EisenInstanceState
    from eisen.common.restriction import GeneralRestriction
    from eisen.memory.memcheck import Spread

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

class State(AbstractParams):
    attrs = ["config", "asl", "txt", "context", "mod", "global_mod",
    "struct_name", "exceptions", "is_ptr", "critical_exception"]

    def __init__(self,
            config: Config,
            asl: CLRList,
            txt: str,
            context: Context,
            mod: Module,
            global_mod: Module,
            struct_name: str,
            arg_type: Type,
            exceptions: list[AbstractException],
            is_ptr: bool,
            inside_constructor: bool,
            print_to_watcher: bool = False,
            critical_exception: SharedBool = SharedBool(False),
            watcher: Watcher = None,
            counter: SharedCounter = SharedCounter(0),
            as_ptr: bool = False,

            # used for interpreter
            objs: dict[str, Obj] = None,

            # used for memcheck
            depth: int = 0,
            ):

        self.config = config
        self.asl = asl
        self.txt = txt
        self.context = context
        self.mod = mod
        self.struct_name = struct_name
        self.arg_type = arg_type
        self.global_mod = global_mod
        self.exceptions = exceptions
        self.is_ptr = is_ptr
        self.inside_constructor = inside_constructor
        self.critical_exception = critical_exception

        self.print_to_watcher = print_to_watcher
        self.watcher = Watcher()
        self.counter = counter
        self.as_ptr = as_ptr

        self.objs = objs or {}

        self.depth = depth

    def but_with(self,
            config: Config = None,
            asl: CLRList = None,
            txt: str = None,
            context: Context = None,
            mod: Module = None,
            global_mod: Module = None,
            struct_name: str = None,
            arg_type: Type = None,
            exceptions: list[AbstractException] = None,
            is_ptr: bool = None,
            inside_constructor: bool = None,

            # used for interpreter
            objs: dict[str, Obj] = None,

            # used for transmutation
            as_ptr: bool = None,

            depth: int = None,
            ) -> State:

        return self._but_with(config=config, asl=asl, txt=txt, context=context, mod=mod,
            struct_name=struct_name, exceptions=exceptions, is_ptr=is_ptr,
            arg_type=arg_type,
            objs=objs,global_mod=global_mod, inside_constructor=inside_constructor,

            as_ptr=as_ptr,

            depth=depth,

            # these cannot be changed by input params
            critical_exception=self.critical_exception, watcher=self.watcher,
            print_to_watcher=self.print_to_watcher,
            counter=self.counter,)

    def report_exception(self, e: AbstractException):
        self.exceptions.append(e)

    def __str__(self) -> str:
        return self.asl.type

    def inspect(self) -> str:
        if isinstance(self.asl, CLRList):
            instances = None
            try:
                instances = self.get_instances()
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
                type = self.get_node_data().returned_type
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
    def create_initial(cls, config: Config, asl: CLRList, txt: str, print_to_watcher: bool=False) -> State:
        global_mod = Module("global")
        global_mod.add_defined_type("int", TypeFactory.produce_novel_type("int").with_restriction(PrimitiveRestriction()))
        global_mod.add_defined_type("str", TypeFactory.produce_novel_type("str").with_restriction(PrimitiveRestriction()))
        global_mod.add_defined_type("flt", TypeFactory.produce_novel_type("flt").with_restriction(PrimitiveRestriction()))
        global_mod.add_defined_type("bool", TypeFactory.produce_novel_type("bool").with_restriction(PrimitiveRestriction()))
        global_mod.add_defined_type("void", TypeFactory.produce_novel_type("void"))

        return State(
            config=config,
            asl=asl,
            txt=txt,
            context=None,
            mod=global_mod,
            global_mod=global_mod,
            struct_name=None,
            arg_type=None,
            exceptions=[],
            is_ptr=False,
            inside_constructor=False,
            print_to_watcher=print_to_watcher)

    def get_node_data(self) -> NodeData:
        """canonical way to access data stored in a node"""
        return self.asl.data

    def get_config(self) -> Config:
        """canonical way to access the config"""
        return self.config

    def get_asl(self) -> CLRList:
        """canonical way to access the current asl"""
        return self.asl

    def get_context(self) -> Context | Module:
        """canonical way to access the current context"""
        return self.context

    def get_enclosing_module(self) -> Module:
        """canonical way to access the module enclosing this state"""
        return self.mod

    def get_struct_name(self) -> str:
        """canonical way to access the name of the struct, if applicable"""
        return self.struct_name

    def get_variant_name(self) -> str:
        return self.struct_name

    def get_returned_type(self) -> Type:
        """canonical way to access the type returned from this node"""
        return self.get_node_data().returned_type

    def get_instances(self) -> list[EisenInstance]:
        """canonical way to get instances stored in this node"""
        return self.get_node_data().instances

    def get_nilstate(self, name) -> bool:
        return self.get_context().get_nilstate(name)

    def add_nilstate(self, name: str, nilstate: bool):
        self.get_context().add_nilstate(name, nilstate)

    def get_defined_type(self, name: str) -> Type:
        return LookupManager.resolve_defined_type(name, self.get_enclosing_module())

    def get_arg_type(self) -> Type | None:
        return self.arg_type

    def get_bool_type(self) -> Type:
        return TypeFactory.produce_novel_type("bool").with_restriction(PrimitiveRestriction())

    def get_abort_signal(self) -> Type:
        return TypeFactory.produce_novel_type("_abort_")

    def get_child_asls(self) -> list[CLRList]:
        """canonical way to obtain child CLRLists"""
        return [child for child in self.asl if isinstance(child, CLRList)]

    def get_all_children(self) -> list[CLRList]:
        """canonical way to get all children of the current CLRList"""
        return self.asl._list

    def get_instancestate(self, name: str) -> EisenInstanceState:
        """canonical way to access a InstanceState by name"""
        return self.context.get_instancestate(name)

    def get_line_number(self) -> int:
        """canonical way to access the line number corresponding to this state"""
        return self.asl.line_number

    def get_restriction(self) -> GeneralRestriction:
        return self.get_returned_type().get_restrictions()[0]

    def add_reference_type(self, name: str, type: Type):
        self.get_context().add_reference_type(name, type)

    def lookup_function_instance(self, name: str, type: Type) -> EisenInstance | None:
        """canonical way to lookup a instance for a defined function"""
        return self.get_enclosing_module().get_function_instance(name, type)

    def assign_returned_type(self, type: Type):
        self.get_node_data().returned_type = type

    def assign_instances(self, instances: list[EisenInstance] | EisenInstance):
        if isinstance(instances, EisenInstance):
            instances = [instances]
        self.get_node_data().instances = instances

    def set_instances(self, instances: list[EisenInstance]):
        self.get_node_data().instances = instances

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

    def add_defined_type(self, type: Type):
        self.get_enclosing_module().add_defined_type(type.name, type)

    def add_instancestate(self, instancestate: EisenInstanceState):
        self.context.add_instancestate(instancestate)

    def add_function_instance_to_module(self, instance: EisenInstance):
        self.get_enclosing_module().add_function_instance(instance)

    def apply_fn_to_all_children(self, fn):
        for child in self.asl:
            fn.apply(self.but_with(asl=child))

    def get_void_type(self) -> Type:
        return TypeFactory.produce_novel_type("void").with_restriction(NoRestriction())

    def is_asl(self) -> bool:
        return isinstance(self.asl, CLRList)

    def create_block_context(self) -> Context:
        return Context(
            name="block",
            parent=self.get_context())

    def is_inside_constructor(self) -> bool:
        return self.inside_constructor

    def get_spread(self, name: str) -> Spread:
        return self.get_context().get_spread(name)

    def add_spread(self, name: str, spread: Spread):
        self.get_context().add_spread(name, spread)

    def get_curried_type(self, fn_type: Type, n_curried_args: int) -> Type:
        argument_type = fn_type.get_argument_type()
        if not argument_type.is_tuple():
            if n_curried_args == 1:
                return TypeFactory.produce_function_type(
                    arg=self.get_void_type(),
                    ret=fn_type.get_return_type(),
                    mod=fn_type.mod)
            raise Exception(f"tried to curry more arguments than function allows: {n_curried_args} {fn_type}")

        if len(argument_type.components) - n_curried_args == 1:
            # unpack tuple to just a single type
            curried_fn_args = argument_type.components[-1]
        else:
            curried_fn_args = TypeFactory.produce_tuple_type(argument_type.components[n_curried_args:])
        return TypeFactory.produce_function_type(
            arg=curried_fn_args,
            ret=fn_type.get_return_type(),
            mod=fn_type.mod).with_restriction(FunctionalRestriction())
