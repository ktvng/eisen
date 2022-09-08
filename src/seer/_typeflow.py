from __future__ import annotations
import re

from alpaca.asts import CLRList, CLRToken
from alpaca.config import Config
from alpaca.validator import AbstractException
from alpaca.utils import AbstractFlags, TransformFunction
from alpaca.validator import Type, Context, TypeFactory, Instance, AbstractParams

class ContextTypes:
    mod = "module"
    fn = "fn"
    block = "block"

class Flags(AbstractFlags):
    is_ptr = "is_ptr"
    is_arg = "is_arg"

class Params(AbstractParams):
    def __init__(self, 
            config: Config, 
            asl: CLRList, 
            txt: str,
            mod: Context,
            starting_mod: Context,
            flags: Flags,
            struct_name: str,
            exceptions: list[AbstractException],
            is_ptr: bool,
            ):

        self.config = config
        self.asl = asl
        self.txt = txt
        self.mod = mod
        self.flags = flags
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
            flags: Flags = None,
            struct_name: str = None,
            exceptions: list[AbstractException] = None,
            is_ptr: bool = None,
            ):

        return self._but_with(config=config, asl=asl, txt=txt, mod=mod, starting_mod=starting_mod,
            flags=flags, struct_name=struct_name, exceptions=exceptions, is_ptr=is_ptr)

    def report_exception(self, e: AbstractException):
        self.exceptions.append(e)

    def __str__(self) -> str:
        return self.asl.type

class SeerInstance(Instance):
    def __init__(self, name: str, type: Type, context: Context, is_ptr=False):
        super().__init__(name, type, context)
        self.is_ptr = is_ptr

def asl_of_type(name: str):
    def predicate(params: Params):
        return params.asl.type == name
    return predicate

def asls_of_type(names: list[str]):
    def predicate(params: Params):
        return params.asl.type in names
    return predicate

# generate a type within a module
class TypeTransducer(TransformFunction):
    def apply(self, params: Params) -> Type:
        return self._apply([params], [params])

    @classmethod
    def _get_component_names(cls, components: list[CLRList]) -> list[str]:
        if any([component.type != ":" for component in components]):
            raise Exception("expected all components to have type ':'")

        return [component.first().value for component in components]

    @classmethod
    def _asl_has_return_clause(cls, asl: CLRList):
        return len(asl) == 4

    @TransformFunction.covers(asl_of_type("type"))
    def type_(fn, params: Params) -> Type:
        # eg. (type int)
        token: CLRToken = params.asl.head()
        if token.type != "TAG":
            raise Exception(f"(type ...) must be a TAG attribute, but got {token.type} instead")
        predefined_type = params.mod.get_type_by_name(token.value)
        if predefined_type:
            params.asl.returns_type = predefined_type
            return predefined_type

        params.asl.returns_type = params.mod.resolve_type(
            type=TypeFactory.produce_novel_type(token.value));
        
        return params.asl.returns_type

    @TransformFunction.covers(asl_of_type(":"))
    def colon_(fn, params: Params) -> Type:
        # eg. (: name (type int))
        return fn.apply(params.but_with(asl=params.asl.second()))

    @TransformFunction.covers(asl_of_type("prod_type"))
    def prod_type_(fn, params: Params) -> Type:
        # eg.  (prod_type
        #           (: name1 (type int))
        #           (: name2 (type str)))
        component_types = [fn.apply(params.but_with(asl=component)) for component in params.asl]
        return params.mod.resolve_type(
            type=TypeFactory.produce_tuple_type(components=component_types))

    @TransformFunction.covers(asl_of_type("types"))
    def types_(fn, params: Params) -> Type:
        # eg. (types (type int) (type str))
        component_types = [fn.apply(params.but_with(asl=component)) for component in params.asl]
        return params.mod.resolve_type(
            type=TypeFactory.produce_tuple_type(components=component_types))

    @TransformFunction.covers(asls_of_type(["fn_type_in", "fn_type_out"]))
    def fn_type_out(fn, params: Params) -> Type:
        # eg. (fn_type_in/out (type(s) ...))
        if len(params.asl) == 0:
            return params.mod.resolve_type(TypeFactory.produce_novel_type("void"))
        return params.mod.resolve_type(
            type=fn.apply(params.but_with(asl=params.asl.first())))

    @TransformFunction.covers(asl_of_type("fn_type")) 
    def fn_type_(fn, params: Params) -> Type:
        # eg. (fn_type (fn_type_in ...) (fn_type_out ...))
        return params.mod.resolve_type(
            type=TypeFactory.produce_function_type(
                arg=fn.apply(params.but_with(asl=params.asl.first())),
                ret=fn.apply(params.but_with(asl=params.asl.second()))))

    @TransformFunction.covers(asls_of_type(["args", "rets"]))
    def args_(fn, params: Params) -> Type:
        # eg. (args (type ...))
        if params.asl:
            return fn.apply(params.but_with(asl=params.asl.first()))
        return TypeFactory.produce_novel_type("void")

    @TransformFunction.covers(asl_of_type("create"))
    def create_(fn, params: Params) -> Type:
        # eg. (create (args ...) (rets ...) (seq ...))
        return params.mod.resolve_type(
            type=TypeFactory.produce_function_type(
                arg=fn.apply(params.but_with(asl=params.asl.first())),
                ret=fn.apply(params.but_with(asl=params.asl.second()))))

    @TransformFunction.covers(asl_of_type("def"))
    def def_(fn, params: Params) -> Type:
        # eg. (def name (args ...) (rets ...) (seq ...))
        if TypeTransducer._asl_has_return_clause(params.asl):
            return params.mod.resolve_type(
                type=TypeFactory.produce_function_type(
                    arg=fn.apply(params.but_with(asl=params.asl.second())),
                    ret=fn.apply(params.but_with(asl=params.asl.third()))))
        else:
            return params.mod.resolve_type(
                type=TypeFactory.produce_function_type(
                    arg=fn.apply(params.but_with(asl=params.asl.second())),
                    ret=TypeFactory.produce_novel_type("void")))

    @TransformFunction.covers(asl_of_type("struct"))
    def struct_(fn, params: Params) -> Type:
        # eg. (struct name (: ...) (: ...) ... (create ...))
        attributes = [component for component in params.asl if component.type == ":"]
        return params.mod.resolve_type(
            type=TypeFactory.produce_struct_type(
                name=params.asl.first().value,
                components=[fn.apply(params.but_with(asl=component)) for component in attributes],
                component_names=TypeTransducer._get_component_names(attributes)))

# generate the module structure and add types to the respective modules
class ModuleTransducer(TransformFunction):
    def apply(self, params: Params):
        return self._apply([params], [params])

    @classmethod
    def init_params(cls, config: Config, asl: CLRList, txt: str):
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
            flags=Flags(),
            struct_name=None,
            exceptions=[],
            is_ptr=False)

    @classmethod
    def parse_type(cls, params: Params) -> Type:
        return TypeTransducer().apply(params)
    
    @TransformFunction.covers(asl_of_type("start"))
    def start_i(fn, params: Params):
        params.asl.module = params.mod
        for child in params.asl:
            fn.apply(params.but_with(asl=child))

    @TransformFunction.covers(asl_of_type("struct"))
    def struct_i(fn, params: Params):
        params.asl.module = params.mod
        params.mod.resolve_type(ModuleTransducer.parse_type(params))
        for child in params.asl:
            fn.apply(params.but_with(asl=child, struct_name=params.asl.first().value))

    @TransformFunction.covers(asl_of_type("mod"))
    def mod_i(fn, params: Params):
        params.asl.module = params.mod
        child_mod = Context(
            name=params.asl.first().value,
            type=ContextTypes.mod, 
            parent=params.mod)

        for child in params.asl:
            fn.apply(params.but_with(
                asl=child, 
                mod=child_mod))

    @TransformFunction.covers(asl_of_type("def"))
    def def_i(fn, params: Params):
        params.asl.module = params.mod
        new_type = ModuleTransducer.parse_type(params)
        params.mod.resolve_type(new_type)
        params.asl.instances = [params.mod.add_instance(
            SeerInstance(
                name=params.asl.first().value,
                type=new_type,
                context=params.mod))]

    @TransformFunction.covers(asl_of_type("create"))
    def create_i(fn, params: Params):
        params.asl.module = params.mod
        new_type = ModuleTransducer.parse_type(params)
        params.mod.resolve_type(new_type)
        params.asl.instances = [params.mod.add_instance(
            SeerInstance(
                name="create_" + params.struct_name,
                type=new_type,
                context=params.mod))]

    @TransformFunction.covers(asls_of_type(["TAG", ":"]))
    def TAG_i(fn, params: Params):
        return

    @TransformFunction.default
    def default_(fn, params: Params):
        params.asl.module = params.mod

class TypeFlowTransducer(TransformFunction):
    def apply(self, params: Params) -> Type:
        return self._apply([params], [params])

    @classmethod
    def void_type(cls, params: Params):
        return params.mod.resolve_type(TypeFactory.produce_novel_type("void"))

    @TransformFunction.covers(asls_of_type(["fn_type"]))
    def fn_type_(fn, params: Params) -> Type:
        type = TypeTransducer().apply(params)
        params.asl.returns_type = type
        return type

    no_action = ["start", "return", "seq", "prod_type"]
    @TransformFunction.covers(asls_of_type(no_action))
    def no_action_(fn, params: Params) -> Type:
        for child in params.asl:
            fn.apply(params.but_with(asl=child))
        params.asl.returns_type = TypeFlowTransducer.void_type(params)
        return params.asl.returns_type

    @TransformFunction.covers(asl_of_type("."))
    def dot_(fn, params: Params) -> Type:
        parent_type = fn.apply(params.but_with(asl=params.asl.head()))
        attr_name = params.asl[1].value
        attr_type = parent_type.get_member_attribute_by_name(attr_name)
        params.asl.returns_type = attr_type

        return params.asl.returns_type

    # TODO: better way to do this
    @classmethod
    def _get_global_mod(cls, params: Params):
        while params.mod.parent:
            return cls._get_global_mod(params.but_with(mod=params.mod.parent))
        return params.mod

    # TODO: will this work for a::b()?
    @TransformFunction.covers(asl_of_type("::"))
    def scope_(fn, params: Params) -> Type:
        return fn.apply(params.but_with(
            asl=params.asl.second(),
            starting_mod=params.starting_mod.get_child_module_by_name(params.asl.first().value)))

    @TransformFunction.covers(asl_of_type("tuple"))
    def tuple_(fn, params: Params) -> Type:
        components = [fn.apply(params.but_with(asl=child)) for child in params.asl]
        params.asl.returns_type = params.mod.resolve_type(
            type=TypeFactory.produce_tuple_type(components))

        return params.asl.returns_type

    @TransformFunction.covers(asl_of_type("cond"))
    def cond_(fn, params: Params) -> Type:
        for child in params.asl:
            fn.apply(params.but_with(asl=child))
        params.asl.returns_type = TypeFlowTransducer.void_type(params)
        return params.asl.returns_type

    @TransformFunction.covers(asl_of_type("if"))
    def if_(fn, params: Params) -> Type:
        for child in params.asl:
            fn.apply(params.but_with(
                asl=child, 
                mod=Context(
                    name="if",
                    type=ContextTypes.block,
                    parent=params.mod)))
        params.asl.returns_type = TypeFlowTransducer.void_type(params)
        return params.asl.returns_type

    @TransformFunction.covers(asl_of_type("while"))
    def while_(fn, params: Params) -> Type:
        fn.apply(params.but_with(
            asl=params.asl.first(),
            mod=Context(name="while", type=ContextTypes.block, parent=params.mod)))
        params.asl.returns_type = TypeFlowTransducer.void_type(params)
        return params.asl.returns_type

    @TransformFunction.covers(asl_of_type(":"))
    def colon_(fn, params: Params) -> Type:
        params.asl.returns_type = fn.apply(params.but_with(asl=params.asl[1]))
        return params.asl.returns_type

    @TransformFunction.covers(asl_of_type("fn"))
    def fn_(fn, params: Params) -> Type:
        name = params.asl.first().value
        # special case. TODO: fix this
        if name == "print":
            params.asl.returns_type = params.mod.resolve_type(
                type=TypeFactory.produce_function_type(
                    arg=TypeFlowTransducer.void_type(params),
                    ret=TypeFlowTransducer.void_type(params)))
            return params.asl.returns_type
        instance: Instance = params.starting_mod.get_instance_by_name(name=name)
        params.asl.instances = [instance]
        params.asl.returns_type = instance.type
        return params.asl.returns_type

    @TransformFunction.covers(asl_of_type("params"))
    def params_(fn, params: Params) -> Type:
        component_types = [fn.apply(params.but_with(asl=child)) for child in params.asl]
        params.asl.returns_type = params.mod.resolve_type(
            type=TypeFactory.produce_tuple_type(component_types))
        return params.asl.returns_type

    @TransformFunction.covers(asl_of_type("call"))
    def call(fn, params: Params) -> Type:
        fn_type = fn.apply(params.but_with(asl=params.asl.first()))
        params.asl.returns_type = fn_type.get_return_type()

        # still need to type flow through the params passed to the function
        fn.apply(params.but_with(asl=params.asl.second()))
        return params.asl.returns_type
         
    @TransformFunction.covers(asl_of_type("struct"))
    def struct(fn, params: Params) -> Type:
        name = params.asl.first().value
        # SeerEnsure.struct_has_unique_names(params)
        # pass struct name into context so the create method knows where it is defined
        # TODO: shouldn't add members to module
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child))
        params.asl.returns_type = TypeFlowTransducer.void_type(params)
        return params.asl.returns_type

    @TransformFunction.covers(asl_of_type("mod"))
    def mod(fn, params: Params) -> Type:
        name = params.asl.first().value
        child_mod = params.mod.get_child_module_by_name(name)
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child, mod=child_mod))
        params.asl.returns_type = TypeFlowTransducer.void_type(params)
        return params.asl.returns_type
 
    @TransformFunction.covers(asl_of_type("create"))
    def create_(fn, params: Params):
        local_mod = Context(
            name="create",
            type=ContextTypes.fn,
            parent=params.mod)
        for child in params.asl:
            fn.apply(params.but_with(asl=child, mod=local_mod))

        params.asl.returns_type = TypeFlowTransducer.void_type(params)
        return params.asl.returns_type
    
    @TransformFunction.covers(asl_of_type("def"))
    def fn(fn, params: Params) -> Type:
        local_mod = Context(
            name=params.asl.first().value,
            type=ContextTypes.fn,
            parent=params.mod)
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child, mod=local_mod))

        params.asl.returns_type = TypeFlowTransducer.void_type(params)
        return params.asl.returns_type

    binary_ops = ['+', '-', '/', '*', '&&', '||', '<', '>', '<=', '>=', '==', '!=', '+=', '-=', '*=', '/='] 
    @TransformFunction.covers(asls_of_type(binary_ops))
    def binary_ops(fn, params: Params) -> Type:
        left_type = fn.apply(params.but_with(asl=params.asl[0]))
        right_type = fn.apply(params.but_with(asl=params.asl[1]))

        if left_type != right_type:
            raise Exception("TODO: gracefully handle exception")

        params.asl.returns_type = left_type 
        return params.asl.returns_type

    @TransformFunction.covers(asl_of_type(":"))
    def colon_(fn, params: Params) -> Type:
        if isinstance(params.asl.first(), CLRToken):
            names = [params.asl.first().value]
        else:
            if params.asl.first().type != "tags":
                raise Exception(f"Expected tags but got {params.asl.first().type}")
            names = [token.value for token in params.asl.first()]

        type = fn.apply(params.but_with(asl=params.asl.second()))
        params.asl.instances = []
        for name in names:
            params.asl.instances.append(
                params.mod.add_instance(
                    SeerInstance(name, type, params.mod, is_ptr=params.is_ptr)))

        params.asl.returns_type = type
        return type

    @TransformFunction.covers(lambda params: isinstance(params.asl, CLRToken))
    def token_(fn, params: Params) -> Type:
        # TODO: make this nicer
        if params.asl.type in ["str", "int", "bool"]:
            return params.mod.resolve_type(
                type=TypeFactory.produce_novel_type(name=params.asl.type))
        else:
            raise Exception(f"unexpected token type of {params.asl.type}")

    # cases for ilet:
    # - inference
    #       let x = 4
    #       (let x 4)
    @TransformFunction.covers(asl_of_type("ilet"))
    def idecls_(fn, params: Params):
        name = params.asl.first().value
        type = params.mod.resolve_type(
            type=TypeFactory.produce_novel_type(params.asl.second().type))

        params.asl.instances = [params.mod.add_instance(SeerInstance(name, type, params.mod))]
        params.asl.returns_type = type
        return type
        
    # cases for let:
    # - standard
    #       let x: int
    #       (let (: x (type int)))
    # - multiple standard
    #       let x, y: int
    #       (let (: (tags x y) (type int)))
    # - multiple inference
    #       let x, y = 4, 4
    #       (let (tags x y ) (tuple 4 4))
    @TransformFunction.covers(asls_of_type(['val', 'var', 'mut_val', 'mut_var', 'let']))
    def decls_(fn, params: Params):
        if isinstance(params.asl.first(), CLRList) and params.asl.first().type == "tags":
            names = [token.value for token in params.asl.first()]
            types = [fn.apply(params.but_with(asl=child)) for child in params.asl.second()]

            params.asl.instances = []
            for name, type in zip(names, types):
                params.asl.instances.append(
                    params.mod.add_instance(SeerInstance(name, type, params.mod)))

            params.asl.returns_type = TypeFlowTransducer.void_type(params)
            return params.asl.returns_type
        elif isinstance(params.asl.first(), CLRList) and params.asl.first().type == ":":
            params.asl.returns_type = fn.apply(params.but_with(asl=params.asl.first()))
            name = params.asl.first().instances[0].name
            params.asl.instances = [params.mod.add_instance(
                SeerInstance(name, params.asl.returns_type, params.mod))]
            return params.asl.returns_type

        else:
            raise Exception(f"Unexpected format: {params.asl}")

    @TransformFunction.covers(asls_of_type(["type", "type?", "type*"]))
    def _type1(fn, params: Params) -> Type:
        params.asl.returns_type = params.mod.get_type_by_name(
            name=params.asl.first().value)
        return params.asl.returns_type

    @TransformFunction.covers(asl_of_type("="))
    def assigns(fn, params: Params) -> Type:
        left_type = fn.apply(params.but_with(asl=params.asl[0]))
        right_type = fn.apply(params.but_with(asl=params.asl[1]))
        
        # TODO: validations

        # if left_type != right_type:
        #     params.report_exception(
        #         Exceptions.TypeMismatch(
        #             msg = f"expected {left_type} but got {right_type}",
        #             line_number=params.asl.line_number))

        return left_type 

    @TransformFunction.covers(asl_of_type("<-"))
    def larrow_(fn, params: Params) -> Type:
        left_type = fn.apply(params.but_with(asl=params.asl[0]))
        right_type = fn.apply(params.but_with(asl=params.asl[1]))

        # TODO: validations

        return left_type

    @TransformFunction.covers(asl_of_type("ref"))
    def ref_(fn, params: Params) -> Type:
        name = params.asl.first().value
        instance = params.mod.get_instance_by_name(name)
        if not instance:
            raise Exception("TODO: gracefully handle instance not being found")

        params.asl.instances = [instance]
        params.asl.returns_type = instance.type 
        return instance.type

    @TransformFunction.covers(asl_of_type("args"))
    def args_(fn, params: Params) -> Type:
        if not params.asl:
            return TypeFlowTransducer.void_type(params)
        type = fn.apply(params.but_with(asl=params.asl.first(), is_ptr=False))
        params.asl.returns_type = type
        return type

    @TransformFunction.covers(asl_of_type("rets"))
    def rets_(fn, params: Params) -> Type:
        if not params.asl:
            return TypeFlowTransducer.void_type(params)
        type = fn.apply(params.but_with(asl=params.asl.first(), is_ptr=True))
        params.asl.returns_type = type
        return type
