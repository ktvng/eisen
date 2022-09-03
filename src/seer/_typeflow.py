from __future__ import annotations
import re

from alpaca.asts import CLRList, CLRToken
from alpaca.config import Config
from alpaca.validator import AbstractModule, AbstractType, AbstractException
from alpaca.utils import AbstractFlags, TransformFunction, PartialTransform
from alpaca.validator import Type, Context, TypeFactory, Instance, AbstractParams

class ContextTypes:
    mod = "module"
    fn = "fn"
    block = "block"

class Flags(AbstractFlags):
    is_ret = "is_ret"
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
            exceptions: list[AbstractException]
            ):

        self.config = config
        self.asl = asl
        self.txt = txt
        self.mod = mod
        self.flags = flags
        self.struct_name = struct_name
        self.starting_mod = starting_mod
        self.exceptions = exceptions

    def but_with(self,
            config: Config = None,
            asl: CLRList = None,
            txt: str = None,
            mod: Context = None,
            starting_mod: Config = None,
            flags: Flags = None,
            struct_name: str = None,
            exceptions: list[AbstractException] = None
            ):

        return self._but_with(config=config, asl=asl, txt=txt, mod=mod, starting_mod=starting_mod,
            flags=flags, struct_name=struct_name, exceptions=exceptions)

    def report_exception(self, e: AbstractException):
        self.exceptions.append(e)

    def __str__(self) -> str:
        return self.asl.type

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
            return predefined_type

        return params.mod.resolve_type(
            type=TypeFactory.produce_novel_type(token.value));

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

# resolve a reference tag inside a scope chain
class ScopeResolutionTransducer(TransformFunction):
    def apply(self, params: Params) -> Context:
        return self._apply([params], [params])

    @TransformFunction.covers(asl_of_type("::"))
    def scope_(fn, params: Params) -> Context:
        if isinstance(params.asl.first(), CLRToken):
            # base case
            starting_mod = params.starting_mod.get_child_module_by_name(params.asl.first().value)
        else:
            starting_mod = params.starting_mod
        return starting_mod.get_child_module_by_name(params.asl.second().value)

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
            exceptions=[])

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
            name=params.asl.first().value,
            type=new_type,
            context=params.mod)]

    @TransformFunction.covers(asl_of_type("create"))
    def create_i(fn, params: Params):
        params.asl.module = params.mod
        new_type = ModuleTransducer.parse_type(params)
        params.mod.resolve_type(new_type)
        params.asl.instances = [params.mod.add_instance(
            name="create_" + params.struct_name,
            type=new_type,
            context=params.mod)]

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
    def scope_(fn, params: Params) ->Type:
        if isinstance(params.asl.first(), CLRToken):
            # mod1::type_name
            # (:: mod1 type_name)
            look_in_mod = params.starting_mod.get_child_module_by_name(params.asl.first().value)
        else:
            # mod1::mod2::type_name
            # eg. (:: (:: mod1 mod2) type_name))))))
            look_in_mod = ScopeResolutionTransducer().apply(params)
        type = look_in_mod.get_type_by_name(params.asl.second().value)
        params.asl.returns_type = type
        return type

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
        instance: Instance = params.mod.get_instance_by_name(name=name)
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
                params.mod.add_instance(name, type, params.mod))

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

    # cases for let:
    # - standard
    #       let x: int
    #       (let (: x (type int)))
    # - interence
    #       let x = 4
    #       (let x 4)
    # - multiple standard
    #       let x, y: int
    #       (let (: (tags x y) (type int)))
    # - multiple inference
    #       let x, y = 4, 4
    #       (let (tags x y ) (tuple 4 4))
    @TransformFunction.covers(asls_of_type(['val', 'var', 'mut_val', 'mut_var', 'let']))
    def decls_(fn, params: Params):
        if isinstance(params.asl.first(), CLRToken) and isinstance(params.asl.second(), CLRToken):
            name = params.asl.first().value
            type = params.mod.resolve_type(
                type=TypeFactory.produce_novel_type(params.asl.second().type))

            params.asl.instances = [params.mod.add_instance(name, type, params.mod)]
            params.asl.returns_type = type
            return type
        elif isinstance(params.asl.first(), CLRList) and params.asl.first().type == "tags":
            names = [token.value for token in params.asl.first()]
            types = [fn.apply(params.but_with(asl=child)) for child in params.asl.second()]

            params.asl.instances = []
            for name, type in zip(names, types):
                params.asl.instances.append(
                    params.mod.add_instance(name, type, params.mod))

            params.asl.returns_type = TypeFlowTransducer.void_type(params)
            return params.asl.returns_type
        elif isinstance(params.asl.first(), CLRList) and params.asl.first().type == ":":
            params.asl.returns_type = fn.apply(params.but_with(asl=params.asl.first()))
            name = params.asl.first().instances[0].name
            params.asl.instances = [params.mod.add_instance(name, params.asl.returns_type, params.mod)]
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

        params.asl.returns_type = instance.type 
        return instance.type

    @TransformFunction.covers(asls_of_type(["args", "rets"]))
    def args_(fn, params: Params) -> Type:
        if not params.asl:
            return TypeFlowTransducer.void_type(params)
        type = fn.apply(params.but_with(asl=params.asl.first()))
        params.asl.returns_type = type
        return type

class InstanceTransducer(TransformFunction):
    pass


































class Utils:
    base_prefix = ""

    @classmethod
    def get_mod_prefix(cls, mod: Context):
        prefix = ""
        while mod is not None:
            prefix = mod.name + "_" + prefix
            mod = mod.parent
        return Utils.base_prefix + prefix

    # TODO:
    @classmethod
    def c_declaration_for(cls, instance: Instance):
        # TODO: need to work for */? suffixed novel types
        if instance.type.is_novel():
            return f"{instance.type.name} {instance.name}"
        if instance.type.is_function():
            name = Utils.c_name_for(instance)
            return f"{CTypeTransducer().run(instance.type, instance.context, name=name)}"
        if instance.type.is_struct():
            name = Utils.c_name_for(instance)
            return f"struct {name}"

    @classmethod
    def c_name_for(cls, instance: Instance):
        # TODO: need to work for */? suffixed novel types
        if instance.type.is_novel() or instance.type.is_struct():
            return instance.name
        if instance.type.is_function():
            return Utils.get_mod_prefix(instance.context) + instance.name
        
        raise NotImplementedError()

class CTypeTransducer(TransformFunction):
    class Params(AbstractParams):
        def __init__(self, 
                name: str,
                type: Type,
                mod: Context,
                as_pointers: bool,
                index: SharedCounter
                ):

            self.name = name
            self.type = type
            self.mod = mod
            self.as_pointers = as_pointers
            self.index = index

        def but_with(self,
                name: str = None,
                type: Type = None,
                mod: Context = None,
                as_pointers: bool = None,
                index: SharedCounter = None,
                ):

            return self._but_with(name=name, type=type, mod=mod, as_pointers=as_pointers, index=index)


    def __init__(self):
        super().__init__()

    def run(self, type: Type, mod: Context, name: str = "") -> str:
        return self.apply(CTypeTransducer.Params(name, type, mod,  False, SharedCounter(0)))

    def apply(self, params: CTypeTransducer.Params) -> str:
        return self._apply([params.type], [params])

    @classmethod
    def generic_function_name(cls, params) -> str:
        params.index += 1
        return f"fn_{params.index}"

    def type_of_construction(construction: str):
        def predicate(type: Type):
            return type.construction == construction
        return predicate

    @TransformFunction.covers(type_of_construction("function"))
    def function_(fn, params: CTypeTransducer.Params) -> str:
        name = params.name if params.name else CTypeTransducer.generic_function_name(params)
        args = fn.apply(params.but_with(
            name="",
            type=params.type.components[0]))
        rets = fn.apply(params.but_with(
            name="",
            type=params.type.components[1], 
            as_pointers=True))

        if args and rets:
            full_params = ", ".join([args, rets])
        elif args:
            full_params = args
        elif rets:
            full_params = rets
        else:
            full_params = ""

        return f"void (*{name})({full_params})"

    @TransformFunction.covers(type_of_construction("novel"))
    def novel_(fn, params: CTypeTransducer.Params) -> str:
        suffix = "*" if params.as_pointers else ""
        if params.type.name == "int":
            return "int" + suffix
        if params.type.name == "void":
            return ""
        if params.type.name == "str":
            return "str" + suffix

        raise Exception(f"{fn} unimplemented for {params.type}")

    @TransformFunction.covers(type_of_construction("tuple"))
    def tuple_(fn, params: CTypeTransducer.Params) -> str:
        return ", ".join([fn.apply(params.but_with(type=component))
            for component in params.type.components])

    @TransformFunction.covers(type_of_construction("struct"))
    def struct_(fn, params: CTypeTransducer.Params) -> str:
        suffix = "*" if params.as_pointers else ""
        prefix = Utils.get_mod_prefix(params.mod)
        return f"struct {prefix}{params.type.name}{suffix}"

















# TODO: params should take an instance
class CodeTransducer(TransformFunction):
    def __init__(self):
        super().__init__()

    def apply(self, params: Params) -> list[str]:
        return self._apply(
            match_args=[params.asl],
            fn_args=[params])

    @TransformFunction.covers(lambda x: isinstance(x, CLRToken))
    def token_(self, params: Params) -> list[str]:
        return [params.asl.value]

    @TransformFunction.covers(lambda x: x.type == "start")
    def pass_through_(self, params: Params) -> list[str]:
        parts = []
        for child in params.asl:
            parts += self.apply(params.but_with(asl=child))
        return parts
 
    # TODO think about use_struct_ptr
    @TransformFunction.covers(lambda x: x.type == ".")
    def dot_(self, params: CodeTransducer.Params) -> list[str]:
        if params.asl.head().type == "ref":
            parts = self.apply(params.but_with(
                asl=params.asl.head(),
                flags=params.flags.but_without(Flags.use_struct_ptr)))
            return parts + [".", params.asl.second().value]
        
        return (self.apply(params.but_with(asl=params.asl.head())) + 
            [".", params.asl.second().value])

    @TransformFunction.covers(lambda x: x.type == "cond")
    def cond_(self, params: Params) -> list[str]:
        return ([] 
            + ["("] 
            + self.apply(params.but_with(asl=params.asl.first()))
            + [")", " {\n"]
            + self.apply(params.but_with(asl=params.asl.second()))
            + ["}"])

    @TransformFunction.covers(lambda x: x.type == "if")
    def if_(self, params: Params) -> list[str]:
        parts = ["if "] + self.apply(params.but_with(asl=params.asl.first()))
        for child in params.asl[1:]:
            if child.type == "cond":
                parts += [" else if "] + self.apply(params.but_with(asl=child))
            else:
                parts += [" else {\n"] + self.apply(params.but_with(asl=child)) + ["}"]
        return parts

    @TransformFunction.covers(lambda x: x.type == "while")
    def while_(self, params: Params) -> list[str]:
        return ["while "] + self.apply(params.but_with(asl=params.asl.first()))
        
    @TransformFunction.covers(lambda x: x.type == "mod")
    def mod_(self, params: Params) -> list[str]:
        parts = []
        # ignore the first entry in the list as it is the name token
        for child in params.asl[1:]:
            parts += self.apply(params.but_with(asl=child))
        return parts

    @TransformFunction.covers(lambda x: x.type == "struct")
    def struct_(fn, params: Params):
        full_name = Helpers.get_mod_prefix(params.asl.module) + params.asl.first().value

        parts = [full_name, " {\n", f"int __nrefs__;\n"]
        struct_members: list[CLRList] = [asl for asl in params.asl[1:] if asl.type != "create"]

        for child in struct_members:
            additional_parts = fn.apply(params.but_with(asl=child))
            if additional_parts:
                parts += additional_parts + [";\n"]
        parts.append("};\n\n")

        method_members: list[CLRList] = [asl for asl in params.asl[1:] if asl.type != "create"]
        for child in method_members:
            additional_parts = fn.apply(params.but_with(asl=child))
            if additional_parts:
                parts += additional_parts + [";\n"]

        return parts

    @TransformFunction.covers(lambda x: x.type == ":")
    def colon_(self, params: Params) -> Type:
        if params.asl.returns_type.is_function():
            return [CTypeTransducer().run(type=params.asl.returns_type, mod=params.mod)]

        return [Utils.c_name_for(params.asl.instances[0])] 

    @TransformFunction.covers(lambda x: x.type == "args")
    def args_(self, params: Params) -> Type:
        if len(params.asl) == 0:
            return []
        return self.apply(params.but_with(asl=params.asl.head()))

    @classmethod
    def _write_function(cls, self, args: CLRList, rets: CLRList, seq: CLRList, params: Params) -> list[str]:
        instance: Instance = params.asl.instances[0]
        parts = [f"void {Utils.c_name_for(instance)}("]
        
        # args
        args_parts = self.apply(params.but_with(
            asl=args,
            flags=params.flags.but_with(Flags.use_ptr)))
        if args_parts:
            parts += ["/*args*/ "] + args_parts

        # rets
        if rets:
            # append ", " after args
            if args: parts.append(", ")
            parts += ["/*rets*/ "] + self.apply(params.but_with(asl=rets))
        
        parts.append(") {\n")

        # seq
        guard = []
        if False: #params.use_guard:
            guard = ["void* __end__;\n", "v2_guard_get_end(&__end__);\n"]
        seq_parts = guard + self.apply(params.but_with(asl=seq)) 

        parts += seq_parts
        parts.append("}\n\n")
        return parts 

    @TransformFunction.covers(lambda x: x.type == "create")
    def create_(self, params: CodeTransducer.Params):
        args = params.asl[0]
        rets = None if len(params.asl) == 2 else params.asl[1]
        seq = params.asl[-1]
        return CodeTransducer._write_function(self, args, rets, seq, params)

    @TransformFunction.covers(lambda x: x.type == "def")
    def def_(self, params: Params) -> list[str]:
        args = params.asl[1]
        rets = None if len(params.asl) == 3 else params.asl[2]
        seq = params.asl[-1]
        return CodeTransducer._write_function(self, args, rets, seq, params)

    @TransformFunction.covers(lambda x: x.type == "rets")
    def rets_(self, params: Params) -> list[str]:
        parts = self.apply(params.but_with(asl=params.asl.head()))
        return parts
            
    @TransformFunction.covers(lambda x: x.type == "seq")
    def seq_(self, params: Params) -> list[str]:
        parts = []
        for child in params.asl:
            parts += self.apply(params.but_with(asl=child)) + [";\n"]
        return parts

    @TransformFunction.covers(lambda x: x.type == "let")
    def let_(self, params: Params) -> list[str]:
        parts = []

        # TODO: allow this to work with multiple objects, params.asl.instances
        instances: list[Instance] = params.asl.instances
        for instance in instances:
            # case for (let (: x (type int)))
            if len(params.asl) == 1:
                parts += [Utils.c_declaration_for(instance), ";\n"]
            elif isinstance(params.asl[1], CLRList) and params.asl[1].type == "::":
                parts += [Utils.c_declaration_for(instance), ";\n"]
            else:
                parts += [Utils.c_declaration_for(instance), " = "] + self.apply(params.but_with(asl=params.asl[1])) +[";\n"]

        return parts[:-1]

    @TransformFunction.covers(lambda x: x.type == "val")
    def val_(self, params: Params) -> list[str]:
        instances: list[Instance] = params.asl.instances

        parts = []
        for instance in instances:
            if len(params.asl) == 1:
                return [Utils.c_declaration_for(instance), ";\n"]

            return [Utils.c_declaration_for(instance), " = "] + self.apply(params.but_with(
                asl=params.asl[1],
                flags=params.flags.but_with(Flags.use_addr))) + [";\n"]

        return parts

    @TransformFunction.covers(lambda x: x.type == "var")
    def var_(self, params: CodeTransducer.Params):
        return []
        # TODO: Think about
        
        obj: Object = params.asl.data
        obj = obj[0]
        if len(params.asl) == 1:
            return [f"struct var_ptr {obj.name}"]

        return ([f"struct var_ptr {obj.name} = ", "{0};\n"]
            + [f"{obj.name}.value = "] 
            + self.apply(params.but_with(
                asl=params.asl[1],
                flags=params.flags.but_with(Flags.use_addr))))

    @TransformFunction.covers(lambda x: x.type == "return")
    def return_(self, params: Params) -> list[str]:
        return ["return"]

    @TransformFunction.covers(lambda x: x.type == "ref")
    def ref_(self, params: CodeTransducer.Params):
        raise NotImplementedError()
        instance: Instance = params.asl.instances[0]


        if Helpers.is_function_type(obj):
            return ["&", Helpers.global_name_for(obj)]

        if obj.is_var:
            # TODO: global_name_for is overloaded for both resolving fn names and giving primitives types
            type_name = Helpers.global_name_for(obj)
            name = f"(({type_name}){obj.name}.value)"
            if Flags.keep_as_ptr in params.flags:
                return [f"{obj.name}.value"]
        else:
            name = obj.name

        # case for local variables
        prefix = Helpers.get_prefix(obj, params)
        parts = [prefix, name]

        # ensure proper order of operations with prefix
        if prefix:
            parts = ["("] + parts + [")"]

        return parts

    def _single_equals_(self, l: CLRList, r: CLRList, params: CodeTransducer.Params):
        raise NotImplementedError()
        left_obj: Object = l.data
        # TODO: fix for multiple equals in let
        if isinstance(left_obj, list):
            left_obj = left_obj[0]
        name = left_obj.name

        post_parts = []
        if left_obj.is_var and params.use_guard:
            type_name = Helpers.global_name_for(left_obj)
            name = f"(({type_name}*)&{left_obj.name}.value)"
            post_parts = [";\n", f"v2_var_guard(&{left_obj.name}, __end__)"]

            if r.type == "call":
                final_parts = self.apply(params.but_with(
                    asl=r, 
                    name_of_rets=[name]))

                pre_parts = [] if not params.pre_parts else params.pre_parts
                return pre_parts + final_parts + post_parts

        # special case if assignment comes from a method call
        if r.type == "call":
            final_parts = self.apply(params.but_with(
                asl=r, 
                name_of_rets=["&" + name]))

            pre_parts = [] if not params.pre_parts else params.pre_parts
            return pre_parts + final_parts + post_parts

        parts = self.apply(params.but_with(
            asl=l, 
            flags=params.flags.but_with(Flags.keep_as_ptr)))

        if isinstance(r, CLRToken):
            parts.append(" = ")
            parts.append(r.value)
            return parts + post_parts

        right_obj: Object = r.data
        assign_flags = Helpers.get_right_child_flags_for_assignment(left_obj, right_obj, params) 
        parts += ([" = "]
            + self.apply(params.but_with(asl=r, flags=assign_flags)))
        
        return parts  + post_parts

    @TransformFunction.covers(lambda x: x.type == "=")
    def equals_(self, params: CodeTransducer.Params):
        raise NotImplementedError()
        parts = []
        pre_parts = []
        if CodeTransducer.requires_pre_parts(params):
            use_params = params.but_with(pre_parts=pre_parts)
        else:
            use_params = params

        if params.asl.head().type == "tuple":
            left_child_asls = [child for child in params.asl[0]]
            right_child_asls = [child for child in params.asl[1]]

            for l, r in zip(left_child_asls, right_child_asls):
                parts += self._single_equals_(l, r, use_params)
                parts.append(";\n")
            
            # remove trailing ";\n"
            return pre_parts + parts[:-1] 

        else:
            return self._single_equals_(params.asl[0], params.asl[1], use_params)

    @TransformFunction.covers(lambda x: x.type == "<-")
    def larrow_(self, params: CodeTransducer.Params):
        raise NotImplementedError()
        # TODO: consolidate this
        def _binary_op(op: str, fn, l: CLRList, r: CLRList, params: CodeTransducer.Params):
            return (["("]
                    + fn.apply(params.but_with(asl=l))
                    + [f" {op} "]
                    + fn.apply(params.but_with(asl=r))
                    + [")"])

        def binary_op(op : str):
            def op_fn(fn, params: CodeTransducer.Params):
                return _binary_op(op, fn, params.asl[0], params.asl[1], params)
            return op_fn

        if params.asl.head().type == "tuple":
            parts = []
            left_child_asls = [child for child in params.asl[0]]
            right_child_asls = [child for child in params.asl[1]]
            for l, r in zip(left_child_asls, right_child_asls):
                parts += _binary_op("=", l, r, params)
                parts.append(";\n")

            # remove final ";\n"
            return parts[:-1]
        else:
            fn = binary_op("=")
            return fn(self, params)

    def binary_op(op : str):
        return []
        def _binary_op(op: str, fn, l: CLRList, r: CLRList, params: CodeTransducer.Params):
            return (["("]
                + fn.apply(params.but_with(asl=l))
                + [f" {op} "]
                + fn.apply(params.but_with(asl=r))
                + [")"])

        def op_fn(fn, params: CodeTransducer.Params):
            return _binary_op(op, fn, params.asl[0], params.asl[1], params)
        return op_fn

    plus_ = PartialTransform(lambda x: x.type == "+", binary_op("+"))
    minus_= PartialTransform(lambda x: x.type == "-", binary_op("-"))
    times_= PartialTransform(lambda x: x.type == "*", binary_op("*"))
    divide_= PartialTransform(lambda x: x.type == "/", binary_op("/"))
    leq_ = PartialTransform(lambda x: x.type == "<=", binary_op("<="))
    geq_ = PartialTransform(lambda x: x.type == ">=", binary_op(">="))
    greater_ = PartialTransform(lambda x: x.type == ">", binary_op(">"))
    lesser_ = PartialTransform(lambda x: x.type == "<", binary_op("<"))
    plus_eq_ = PartialTransform(lambda x: x.type == "+=", binary_op("+="))
    minus_eq_ = PartialTransform(lambda x: x.type == "-=", binary_op("-="))
    eq_ = PartialTransform(lambda x: x.type == "==", binary_op("=="))
    or_ = PartialTransform(lambda x: x.type == "||", binary_op("||"))
    and_ = PartialTransform(lambda x: x.type == "&&", binary_op("&&"))

    @TransformFunction.covers(lambda x: x.type == "prod_type")
    def prod_type_(self, params: CodeTransducer.Params):
        raise NotImplementedError()
        parts = self.apply(params.but_with(asl=params.asl.head()))
        for child in params.asl[1:]:
            parts += [", "] + self.apply(params.but_with(asl=child))
        
        return parts

    @classmethod
    def _define_variables_for_return(cls, ret_type: OldType, params: CodeTransducer.Params):
        types = []
        if ret_type.classification == AbstractType.tuple_classification:
            types += ret_type.components
        else:
            types = [ret_type]

        var_names = []
        for type in types:
            tmp_name = f"__{params.n_hidden_vars}__"
            params.n_hidden_vars += 1
            listir_code = f"(let (: {tmp_name} (type {type.name()})))"
            clrlist = ListIRParser.run(params.config, listir_code)
            # use none as these fields will not be used
            vparams = VParams(
                config = params.config,
                asl = clrlist,
                txt = None,
                mod = params.asl.data.mod,
                fns = SeerValidator(),
                context = AbstractModule(),
                flags = None,
                struct_name = None)

            SeerValidator().apply(vparams)

            params.pre_parts += self.apply(params.but_with(asl=clrlist))
            params.pre_parts.append(";\n")
            var_names.append(tmp_name)

        return var_names

    @TransformFunction.covers(lambda x: x.type == "call")
    def call_(self, params: CodeTransducer.Params):
        raise NotImplementedError()
        # first check if the method is special
        if params.asl.head().type == "fn":
            name = params.asl.head().head_value()
            if name == "print":
                parts = ["printf("] + self.apply(params.but_with(asl=params.asl[1])) + [")"]
                return parts

        obj: Object = params.asl.data

        # a function which is passed in as an argument/return value has no prefix
        prefix = "" if obj.is_arg or obj.is_ret else CodeTransducer.get_mod_prefix(obj.mod)
        full_name = prefix + obj.name 

        var_names = []
        ret_parts = []
        if params.pre_parts is not None:
            if params.name_of_rets:
                var_names = params.name_of_rets
                ret_parts = [", " + var for var in var_names]
            else:
                ret_type: OldType = obj.type.ret
                var_names = CodeTransducer._define_variables_for_return(ret_type, params)
                ret_parts = [", &" + var for var in var_names]
                

        if obj.type.arg is None:
            arg_types = []
        elif obj.type.arg.classification == AbstractType.tuple_classification:
            arg_types = obj.type.arg.components
        else:
            arg_types = [obj.type.arg]
        

        expected_types = arg_types
        parameter_parts = []
        for child, expected_type in zip(params.asl[1], expected_types):
            these_flags = params.flags.but_with(Flags.use_struct_ptr)
            if expected_type.is_ptr:
                these_flags = these_flags.but_with(Flags.keep_as_ptr)

            parameter_parts += self.apply(
                params.but_with(asl=child, flags=these_flags, name_of_rets=[]))
            parameter_parts.append(", ")

        if parameter_parts:
            parameter_parts = parameter_parts[:-1]

        if not parameter_parts and ret_parts:
            # remove ", "
            ret_parts[0] = ret_parts[0][2:]

        fn_call_parts = ([full_name, "(",] 
            + parameter_parts
            + ret_parts
            + [")"])

        if params.pre_parts:
            params.pre_parts += fn_call_parts + [";\n"]
            return var_names

        return fn_call_parts
 
    @TransformFunction.covers(lambda x: x.type == "params")
    def params_(self, params: CodeTransducer.Params):
        raise NotImplementedError()
        if len(params.asl) == 0:
            return []
        parts = self.apply(params.but_with(asl=params.asl.head()))
        for child in params.asl[1:]:
            parts += [", "] + self.apply(params.but_with(asl=child))
        return parts

class Flags:
    use_struct_ptr = "use_struct_ptr"
    use_ptr = "use_ptr"
    use_addr = "use_addr"
    keep_as_ptr = "keep_as_ptr"

    def __init__(self, flags: list[str] = []):
        self._flags = flags

    def __getitem__(self, x) -> str:
        return self._flags.__getitem__(x)

    def __setitem__(self, x, y: str) -> str:
        return self._flags.__setitem__(x, y)

    def __len__(self) -> int:
        return len(self._flags)

    def but_with(self, *args) -> Flags:
        return Flags(list(set(list(args) + self._flags)))
    
    def but_without(self, *args) -> Flags:
        return Flags([f for f in self._flags if f not in args])

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

class Helpers:
    @classmethod
    def is_primitive_type(cls, obj: Object):
        return obj.type.classification == AbstractType.base_classification 

    @classmethod
    def is_function_type(cls, obj: Object):
        return obj.type.classification == AbstractType.function_classification

    @classmethod
    def is_struct_type(cls, obj: Object):
        return obj.type.classification == AbstractType.struct_classification

    @classmethod
    def _global_name(cls, name : str, mod : AbstractModule):
        return CodeTransducer.get_mod_prefix(mod) + name

    @classmethod
    def global_name_for(cls, obj: Object):
        ptr = "*" if obj.is_ptr else ""
        if Helpers.is_primitive_type(obj):
            name = obj.type.name()
            if name[-1] == "*" or name[-1] == "?":
                name = name[:-1]

            return name + ptr
        elif Helpers.is_function_type(obj):
            return Helpers._global_name(obj.name, obj.mod)
        elif Helpers.is_struct_type(obj):
            return "struct " + Helpers._global_name(obj.type.name(), obj.type.mod) + ptr

    @classmethod
    def get_c_function_pointer(cls, obj: Object, params: CodeTransducer.Params) -> str:
        typ = obj.type
        if not Helpers.is_function_type(obj):
            raise Exception(f"required a function type; got {typ.classification} instead")

        args = ""
        args += cls._to_function_pointer_arg(typ.arg, params)
        rets = cls._to_function_pointer_arg(typ.ret, params, as_pointers=True)
        if rets:
            args += ", " + rets

        return f"void (*{obj.name})({args})" 

    @classmethod
    def _to_function_pointer_arg(cls, typ: OldType, params: CodeTransducer.Params, as_pointers: bool = False) -> str:
        if typ is None:
            return ""

        if typ.classification == AbstractType.base_classification:
            if typ._name == "int":
                return "int";
            else:
                raise Exception("unimpl")

        elif typ.classification == AbstractType.tuple_classification:
            suffix = "*" if as_pointers else ""
            return ", ".join(
                [cls._to_function_pointer_arg(x, params) + suffix for x in typ.components])
        elif typ.classification == OldType.named_product_type_name:
            return Helpers._global_name_for_type(typ, params.mod)

    @classmethod
    def type_is_pointer(cls, obj: Object, params: CodeTransducer.Params):
        return (Flags.use_ptr in params.flags and not Helpers.is_primitive_type(obj)
            or obj.is_ret)

    @classmethod
    def should_deref(cls, obj: Object, params: CodeTransducer.Params):
        return (obj.is_ret 
            or (obj.is_arg and not Helpers.is_primitive_type(obj))
            or (obj.is_ptr and Flags.keep_as_ptr not in params.flags)
            or obj.is_val 
            )

    @classmethod
    def should_keep_lhs_as_ptr(cls, l: Object, r: Object, params: CodeTransducer.Params):
        return ((l.is_ptr and r.is_ptr)
        )

    @classmethod
    def should_addrs(cls, obj: Object, params: CodeTransducer.Params):
        return ((Flags.use_struct_ptr in params.flags and not Helpers.is_primitive_type(obj))
            or (Flags.use_addr in params.flags and Helpers.is_primitive_type(obj))
            )

    @classmethod
    def get_right_child_flags_for_assignment(cls, l: Object, r: Object, params: CodeTransducer.Params):
        # ptr to ptr
        if l.is_ptr and r.is_ptr:
            return params.flags.but_with(Flags.keep_as_ptr)
        # ptr to let
        if l.is_ptr and not r.is_ptr:
            return params.flags.but_with(Flags.use_addr)


    @classmethod
    def get_prefix(cls, obj: Object, params: CodeTransducer.Params):
        if Helpers.type_is_pointer(obj, params):
            return "*"
        elif Helpers.should_deref(obj, params):
            return "*"
        elif Helpers.should_addrs(obj, params):
            return "&"
        
        return ""
