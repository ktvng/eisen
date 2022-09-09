from __future__ import annotations

from alpaca.clr import CLRList, CLRToken
from alpaca.utils import Wrangler
from alpaca.concepts import Context, TypeFactory, Instance, Type

from seer._params import Params
from seer._typewrangler import TypeWrangler
from seer._common import asls_of_type, ContextTypes, SeerInstance

class TypeFlowWrangler(Wrangler):
    def __init__(self, debug: bool = False):
        super().__init__(debug=debug)
        self.void_type = TypeFactory.produce_novel_type("void")

    def apply(self, params: Params) -> Type:
        if self.debug and isinstance(params.asl, CLRList):
            print("\n"*64)
            print(params.inspect())
            print("\n"*4)
            input()
        return self._apply([params], [params])

    # assign the type return by 'f' to the 'returns_type' attribute of the abstract
    # syntax list stored in params.asl
    def assigns_type(f):
        def decorator(fn, params: Params):
            result: Type = f(fn, params)
            params.asl.returns_type = result
            return result
        return decorator

    @Wrangler.covers(asls_of_type("fn_type"))
    @assigns_type
    def fn_type_(fn, params: Params) -> Type:
        type = TypeWrangler().apply(params)
        return type

    no_action = ["start", "return", "seq", "prod_type"]
    @Wrangler.covers(asls_of_type(*no_action))
    @assigns_type
    def no_action_(fn, params: Params) -> Type:
        for child in params.asl:
            fn.apply(params.but_with(asl=child))
        return fn.void_type

    @Wrangler.covers(asls_of_type("."))
    @assigns_type
    def dot_(fn, params: Params) -> Type:
        parent_type = fn.apply(params.but_with(asl=params.asl.head()))
        attr_name = params.asl[1].value
        attr_type = parent_type.get_member_attribute_by_name(attr_name)
        return attr_type

    # TODO: will this work for a::b()?
    @Wrangler.covers(asls_of_type("::"))
    @assigns_type
    def scope_(fn, params: Params) -> Type:
        return fn.apply(params.but_with(
            asl=params.asl.second(),
            starting_mod=params.starting_mod.get_child_module_by_name(params.asl.first().value)))

    @Wrangler.covers(asls_of_type("tuple"))
    @assigns_type
    def tuple_(fn, params: Params) -> Type:
        components = [fn.apply(params.but_with(asl=child)) for child in params.asl]
        return params.mod.resolve_type(
            type=TypeFactory.produce_tuple_type(components))

    @Wrangler.covers(asls_of_type("cond"))
    @assigns_type
    def cond_(fn, params: Params) -> Type:
        for child in params.asl:
            fn.apply(params.but_with(asl=child))
        return fn.void_type

    @Wrangler.covers(asls_of_type("if"))
    @assigns_type
    def if_(fn, params: Params) -> Type:
        for child in params.asl:
            fn.apply(params.but_with(
                asl=child, 
                mod=Context(
                    name="if",
                    type=ContextTypes.block,
                    parent=params.mod)))
        return fn.void_type

    @Wrangler.covers(asls_of_type("while"))
    @assigns_type
    def while_(fn, params: Params) -> Type:
        fn.apply(params.but_with(
            asl=params.asl.first(),
            mod=Context(name="while", type=ContextTypes.block, parent=params.mod)))
        return fn.void_type

    @Wrangler.covers(asls_of_type(":"))
    @assigns_type
    def colon_(fn, params: Params) -> Type:
        return fn.apply(params.but_with(asl=params.asl[1]))

    @Wrangler.covers(asls_of_type("fn"))
    @assigns_type
    def fn_(fn, params: Params) -> Type:
        name = params.asl.first().value
        # special case. TODO: fix this
        if name == "print":
            return params.mod.resolve_type(
                type=TypeFactory.produce_function_type(
                    arg=fn.void_type,
                    ret=fn.void_type))
        instance: Instance = params.starting_mod.get_instance_by_name(name=name)
        params.asl.instances = [instance]
        return instance.type

    @Wrangler.covers(asls_of_type("params"))
    @assigns_type
    def params_(fn, params: Params) -> Type:
        component_types = [fn.apply(params.but_with(asl=child)) for child in params.asl]
        return params.mod.resolve_type(
            type=TypeFactory.produce_tuple_type(component_types))

    @Wrangler.covers(asls_of_type("call"))
    @assigns_type
    def call(fn, params: Params) -> Type:
        fn_type = fn.apply(params.but_with(asl=params.asl.first()))

        # still need to type flow through the params passed to the function
        fn.apply(params.but_with(asl=params.asl.second()))
        return fn_type.get_return_type()
         
    @Wrangler.covers(asls_of_type("struct"))
    @assigns_type
    def struct(fn, params: Params) -> Type:
        name = params.asl.first().value
        # SeerEnsure.struct_has_unique_names(params)
        # pass struct name into context so the create method knows where it is defined
        # TODO: shouldn't add members to module
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child))
        return fn.void_type

    @Wrangler.covers(asls_of_type("mod"))
    @assigns_type
    def mod(fn, params: Params) -> Type:
        name = params.asl.first().value
        child_mod = params.mod.get_child_module_by_name(name)
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child, mod=child_mod))
        return fn.void_type
 
    @Wrangler.covers(asls_of_type("create"))
    @assigns_type
    def create_(fn, params: Params):
        local_mod = Context(
            name="create",
            type=ContextTypes.fn,
            parent=params.mod)
        for child in params.asl:
            fn.apply(params.but_with(asl=child, mod=local_mod))
        return fn.void_type
    
    @Wrangler.covers(asls_of_type("def"))
    @assigns_type
    def fn(fn, params: Params) -> Type:
        local_mod = Context(
            name=params.asl.first().value,
            type=ContextTypes.fn,
            parent=params.mod)
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child, mod=local_mod))
        return fn.void_type

    binary_ops = ['+', '-', '/', '*', '&&', '||', '<', '>', '<=', '>=', '==', '!=', '+=', '-=', '*=', '/='] 
    @Wrangler.covers(asls_of_type(*binary_ops))
    @assigns_type
    def binary_ops(fn, params: Params) -> Type:
        left_type = fn.apply(params.but_with(asl=params.asl[0]))
        right_type = fn.apply(params.but_with(asl=params.asl[1]))

        if left_type != right_type:
            raise Exception("TODO: gracefully handle exception")

        return left_type

    @Wrangler.covers(asls_of_type(":"))
    @assigns_type
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

        return type

    @Wrangler.covers(lambda params: isinstance(params.asl, CLRToken))
    @assigns_type
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
    @Wrangler.covers(asls_of_type("ilet"))
    @assigns_type
    def idecls_(fn, params: Params):
        name = params.asl.first().value
        type = params.mod.resolve_type(
            type=TypeFactory.produce_novel_type(params.asl.second().type))

        params.asl.instances = [params.mod.add_instance(SeerInstance(name, type, params.mod))]
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
    @Wrangler.covers(asls_of_type('val', 'var', 'mut_val', 'mut_var', 'let'))
    @assigns_type
    def decls_(fn, params: Params):
        if isinstance(params.asl.first(), CLRList) and params.asl.first().type == "tags":
            names = [token.value for token in params.asl.first()]
            types = [fn.apply(params.but_with(asl=child)) for child in params.asl.second()]

            params.asl.instances = []
            for name, type in zip(names, types):
                params.asl.instances.append(
                    params.mod.add_instance(SeerInstance(name, type, params.mod)))
            return fn.void_type

        elif isinstance(params.asl.first(), CLRList) and params.asl.first().type == ":":
            type = fn.apply(params.but_with(asl=params.asl.first()))
            name = params.asl.first().instances[0].name
            params.asl.instances = [params.mod.add_instance(
                SeerInstance(name, type, params.mod))]
            return type

        else:
            raise Exception(f"Unexpected format: {params.asl}")

    @Wrangler.covers(asls_of_type("type", "type?", "type*"))
    @assigns_type
    def _type1(fn, params: Params) -> Type:
        return params.mod.get_type_by_name(name=params.asl.first().value)

    @Wrangler.covers(asls_of_type("="))
    @assigns_type
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

    @Wrangler.covers(asls_of_type("<-"))
    @assigns_type
    def larrow_(fn, params: Params) -> Type:
        left_type = fn.apply(params.but_with(asl=params.asl[0]))
        right_type = fn.apply(params.but_with(asl=params.asl[1]))

        # TODO: validations

        return left_type

    @Wrangler.covers(asls_of_type("ref"))
    @assigns_type
    def ref_(fn, params: Params) -> Type:
        name = params.asl.first().value
        instance = params.mod.get_instance_by_name(name)
        if not instance:
            raise Exception("TODO: gracefully handle instance not being found")

        params.asl.instances = [instance]
        return instance.type

    @Wrangler.covers(asls_of_type("args"))
    @assigns_type
    def args_(fn, params: Params) -> Type:
        if not params.asl:
            return fn.void_type
        type = fn.apply(params.but_with(asl=params.asl.first(), is_ptr=False))
        return type

    @Wrangler.covers(asls_of_type("rets"))
    @assigns_type
    def rets_(fn, params: Params) -> Type:
        if not params.asl:
            return fn.void_type
        type = fn.apply(params.but_with(asl=params.asl.first(), is_ptr=True))
        return type
