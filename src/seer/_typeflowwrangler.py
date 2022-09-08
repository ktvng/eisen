from __future__ import annotations

from alpaca.asts import CLRList, CLRToken
from alpaca.utils import Wrangler
from alpaca.concepts import Context, TypeFactory, Instance, Type

from seer._params import Params
from seer._typewrangler import TypeWrangler
from seer._common import asls_of_type, ContextTypes, SeerInstance

class TypeFlowWrangler(Wrangler):
    def apply(self, params: Params) -> Type:
        return self._apply([params], [params])

    @classmethod
    def void_type(cls, params: Params):
        return params.mod.resolve_type(TypeFactory.produce_novel_type("void"))

    @Wrangler.covers(asls_of_type("fn_type"))
    def fn_type_(fn, params: Params) -> Type:
        type = TypeWrangler().apply(params)
        params.asl.returns_type = type
        return type

    no_action = ["start", "return", "seq", "prod_type"]
    @Wrangler.covers(asls_of_type(*no_action))
    def no_action_(fn, params: Params) -> Type:
        for child in params.asl:
            fn.apply(params.but_with(asl=child))
        params.asl.returns_type = TypeFlowWrangler.void_type(params)
        return params.asl.returns_type

    @Wrangler.covers(asls_of_type("."))
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
    @Wrangler.covers(asls_of_type("::"))
    def scope_(fn, params: Params) -> Type:
        return fn.apply(params.but_with(
            asl=params.asl.second(),
            starting_mod=params.starting_mod.get_child_module_by_name(params.asl.first().value)))

    @Wrangler.covers(asls_of_type("tuple"))
    def tuple_(fn, params: Params) -> Type:
        components = [fn.apply(params.but_with(asl=child)) for child in params.asl]
        params.asl.returns_type = params.mod.resolve_type(
            type=TypeFactory.produce_tuple_type(components))

        return params.asl.returns_type

    @Wrangler.covers(asls_of_type("cond"))
    def cond_(fn, params: Params) -> Type:
        for child in params.asl:
            fn.apply(params.but_with(asl=child))
        params.asl.returns_type = TypeFlowWrangler.void_type(params)
        return params.asl.returns_type

    @Wrangler.covers(asls_of_type("if"))
    def if_(fn, params: Params) -> Type:
        for child in params.asl:
            fn.apply(params.but_with(
                asl=child, 
                mod=Context(
                    name="if",
                    type=ContextTypes.block,
                    parent=params.mod)))
        params.asl.returns_type = TypeFlowWrangler.void_type(params)
        return params.asl.returns_type

    @Wrangler.covers(asls_of_type("while"))
    def while_(fn, params: Params) -> Type:
        fn.apply(params.but_with(
            asl=params.asl.first(),
            mod=Context(name="while", type=ContextTypes.block, parent=params.mod)))
        params.asl.returns_type = TypeFlowWrangler.void_type(params)
        return params.asl.returns_type

    @Wrangler.covers(asls_of_type(":"))
    def colon_(fn, params: Params) -> Type:
        params.asl.returns_type = fn.apply(params.but_with(asl=params.asl[1]))
        return params.asl.returns_type

    @Wrangler.covers(asls_of_type("fn"))
    def fn_(fn, params: Params) -> Type:
        name = params.asl.first().value
        # special case. TODO: fix this
        if name == "print":
            params.asl.returns_type = params.mod.resolve_type(
                type=TypeFactory.produce_function_type(
                    arg=TypeFlowWrangler.void_type(params),
                    ret=TypeFlowWrangler.void_type(params)))
            return params.asl.returns_type
        instance: Instance = params.starting_mod.get_instance_by_name(name=name)
        params.asl.instances = [instance]
        params.asl.returns_type = instance.type
        return params.asl.returns_type

    @Wrangler.covers(asls_of_type("params"))
    def params_(fn, params: Params) -> Type:
        component_types = [fn.apply(params.but_with(asl=child)) for child in params.asl]
        params.asl.returns_type = params.mod.resolve_type(
            type=TypeFactory.produce_tuple_type(component_types))
        return params.asl.returns_type

    @Wrangler.covers(asls_of_type("call"))
    def call(fn, params: Params) -> Type:
        fn_type = fn.apply(params.but_with(asl=params.asl.first()))
        params.asl.returns_type = fn_type.get_return_type()

        # still need to type flow through the params passed to the function
        fn.apply(params.but_with(asl=params.asl.second()))
        return params.asl.returns_type
         
    @Wrangler.covers(asls_of_type("struct"))
    def struct(fn, params: Params) -> Type:
        name = params.asl.first().value
        # SeerEnsure.struct_has_unique_names(params)
        # pass struct name into context so the create method knows where it is defined
        # TODO: shouldn't add members to module
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child))
        params.asl.returns_type = TypeFlowWrangler.void_type(params)
        return params.asl.returns_type

    @Wrangler.covers(asls_of_type("mod"))
    def mod(fn, params: Params) -> Type:
        name = params.asl.first().value
        child_mod = params.mod.get_child_module_by_name(name)
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child, mod=child_mod))
        params.asl.returns_type = TypeFlowWrangler.void_type(params)
        return params.asl.returns_type
 
    @Wrangler.covers(asls_of_type("create"))
    def create_(fn, params: Params):
        local_mod = Context(
            name="create",
            type=ContextTypes.fn,
            parent=params.mod)
        for child in params.asl:
            fn.apply(params.but_with(asl=child, mod=local_mod))

        params.asl.returns_type = TypeFlowWrangler.void_type(params)
        return params.asl.returns_type
    
    @Wrangler.covers(asls_of_type("def"))
    def fn(fn, params: Params) -> Type:
        local_mod = Context(
            name=params.asl.first().value,
            type=ContextTypes.fn,
            parent=params.mod)
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child, mod=local_mod))

        params.asl.returns_type = TypeFlowWrangler.void_type(params)
        return params.asl.returns_type

    binary_ops = ['+', '-', '/', '*', '&&', '||', '<', '>', '<=', '>=', '==', '!=', '+=', '-=', '*=', '/='] 
    @Wrangler.covers(asls_of_type(*binary_ops))
    def binary_ops(fn, params: Params) -> Type:
        left_type = fn.apply(params.but_with(asl=params.asl[0]))
        right_type = fn.apply(params.but_with(asl=params.asl[1]))

        if left_type != right_type:
            raise Exception("TODO: gracefully handle exception")

        params.asl.returns_type = left_type 
        return params.asl.returns_type

    @Wrangler.covers(asls_of_type(":"))
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

    @Wrangler.covers(lambda params: isinstance(params.asl, CLRToken))
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
    @Wrangler.covers(asls_of_type('val', 'var', 'mut_val', 'mut_var', 'let'))
    def decls_(fn, params: Params):
        if isinstance(params.asl.first(), CLRList) and params.asl.first().type == "tags":
            names = [token.value for token in params.asl.first()]
            types = [fn.apply(params.but_with(asl=child)) for child in params.asl.second()]

            params.asl.instances = []
            for name, type in zip(names, types):
                params.asl.instances.append(
                    params.mod.add_instance(SeerInstance(name, type, params.mod)))

            params.asl.returns_type = TypeFlowWrangler.void_type(params)
            return params.asl.returns_type
        elif isinstance(params.asl.first(), CLRList) and params.asl.first().type == ":":
            params.asl.returns_type = fn.apply(params.but_with(asl=params.asl.first()))
            name = params.asl.first().instances[0].name
            params.asl.instances = [params.mod.add_instance(
                SeerInstance(name, params.asl.returns_type, params.mod))]
            return params.asl.returns_type

        else:
            raise Exception(f"Unexpected format: {params.asl}")

    @Wrangler.covers(asls_of_type("type", "type?", "type*"))
    def _type1(fn, params: Params) -> Type:
        params.asl.returns_type = params.mod.get_type_by_name(
            name=params.asl.first().value)
        return params.asl.returns_type

    @Wrangler.covers(asls_of_type("="))
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
    def larrow_(fn, params: Params) -> Type:
        left_type = fn.apply(params.but_with(asl=params.asl[0]))
        right_type = fn.apply(params.but_with(asl=params.asl[1]))

        # TODO: validations

        return left_type

    @Wrangler.covers(asls_of_type("ref"))
    def ref_(fn, params: Params) -> Type:
        name = params.asl.first().value
        instance = params.mod.get_instance_by_name(name)
        if not instance:
            raise Exception("TODO: gracefully handle instance not being found")

        params.asl.instances = [instance]
        params.asl.returns_type = instance.type 
        return instance.type

    @Wrangler.covers(asls_of_type("args"))
    def args_(fn, params: Params) -> Type:
        if not params.asl:
            return TypeFlowWrangler.void_type(params)
        type = fn.apply(params.but_with(asl=params.asl.first(), is_ptr=False))
        params.asl.returns_type = type
        return type

    @Wrangler.covers(asls_of_type("rets"))
    def rets_(fn, params: Params) -> Type:
        if not params.asl:
            return TypeFlowWrangler.void_type(params)
        type = fn.apply(params.but_with(asl=params.asl.first(), is_ptr=True))
        params.asl.returns_type = type
        return type
