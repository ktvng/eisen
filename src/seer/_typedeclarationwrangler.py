from __future__ import annotations

from alpaca.utils import Wrangler
from alpaca.clr import CLRList, CLRToken
from alpaca.concepts import Type, TypeFactory, TypeClass, Context, TypeClass2, TypeClassFactory

from seer._params import Params
from seer._common import asls_of_type, ContextTypes

from seer._callconfigurer import CallConfigurer
from seer._common import asls_of_type, ContextTypes, SeerInstance

# better because this is single purpose.
class ModuleWrangler2(Wrangler):
    def apply(self, params: Params):
        return self._apply([params], [params])

    def sets_module(f):
        def decorator(fn, params: Params):
            params.oracle.add_module(params.asl, params.mod)
            return f(fn, params)
        return decorator

    # params comes pre-build with the global module
    @Wrangler.default
    @sets_module
    def start_(fn, params: Params) -> Context:
        for child in params.asl:
            fn.apply(params.but_with(asl=child))

    @Wrangler.covers(asls_of_type("mod"))
    @sets_module
    def mod_(fn, params: Params) -> Context:
        new_mod = Context(
            name=params.asl.first().value,
            type=ContextTypes.mod, 
            parent=params.mod)

        for child in params.asl:
            fn.apply(params.but_with(
                asl=child, 
                mod=new_mod))

    @Wrangler.covers(lambda params: isinstance(params.asl, CLRToken))
    def token_(fn, params: Params) -> None:
        return None

class TypeClassWrangler(Wrangler):
    def apply(self, params: Params) -> TypeClass2:
        return self._apply([params], [params])

    @Wrangler.covers(asls_of_type("type"))
    def type_(fn, params: Params) -> TypeClass2:
        # eg. (type int)
        token: CLRToken = params.asl.first()
        if token.type != "TAG":
            raise Exception(f"(type ...) must be a TAG attribute, but got {token.type} instead")

        found_type = params.mod.get_typeclass_by_name(token.value)
        if found_type:
            return found_type
        raise Exception(f"unknown type! {token.value}")

    @Wrangler.covers(asls_of_type("interface_type"))
    def interface_type_(fn, params: Params) -> TypeClass2:
        # eg. (interface_type name)
        token: CLRToken = params.asl.first()
        if token.type != "TAG":
            raise Exception(f"(type ...) must be a TAG attribute, but got {token.type} instead")

        found_type = params.mod.get_typeclass_by_name(token.value)
        if found_type:
            return found_type
        raise Exception(f"unknown type! {token.value}")

    @Wrangler.covers(asls_of_type(":"))
    def colon_(fn, params: Params) -> TypeClass2:
        # eg. (: name (type int))
        return fn.apply(params.but_with(asl=params.asl.second()))

    @Wrangler.covers(asls_of_type("prod_type", "types"))
    def prod_type_(fn, params: Params) -> TypeClass2:
        # eg.  (prod_type
        #           (: name1 (type int))
        #           (: name2 (type str)))
        # eg. (types (type int) (type str))
        component_types = [fn.apply(params.but_with(asl=component)) for component in params.asl]
        return TypeClassFactory.produce_tuple_type(components=component_types, global_mod=params.global_mod)

    @Wrangler.covers(asls_of_type("fn_type_in", "fn_type_out"))
    def fn_type_out(fn, params: Params) -> TypeClass2:
        # eg. (fn_type_in/out (type(s) ...))
        if len(params.asl) == 0:
            return params.mod.resolve_type(TypeClassFactory.produce_novel_type("void"))
        return fn.apply(params.but_with(asl=params.asl.first()))

    @Wrangler.covers(asls_of_type("fn_type")) 
    def fn_type_(fn, params: Params) -> TypeClass2:
        # eg. (fn_type (fn_type_in ...) (fn_type_out ...))
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(params.but_with(asl=params.asl.first())),
            ret=fn.apply(params.but_with(asl=params.asl.second())),
            mod=params.global_mod)

    @Wrangler.covers(asls_of_type("args", "rets"))
    def args_(fn, params: Params) -> TypeClass2:
        # eg. (args (type ...))
        if params.asl:
            return fn.apply(params.but_with(asl=params.asl.first()))
        return TypeClassFactory.produce_novel_type("void", params.global_mod)

    @Wrangler.covers(asls_of_type("def", "create"))
    def def_(fn, params: Params) -> TypeClass2:
        # eg. (def name (args ...) (rets ...) (seq ...))
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(params.but_with(asl=params.asl.second())),
            ret=fn.apply(params.but_with(asl=params.asl.third())),
            mod=params.global_mod)
    
    @Wrangler.covers(asls_of_type("struct", "interface"))
    def struct_(fn, params: Params) -> TypeClass2:
        raise Exception("this should not be used to produce struct types")
    
# add types as proto* classification, as these are the declarations
class TypeDeclarationWrangler(Wrangler):
    def apply(self, params: Params) -> None:
        return self._apply([params], [params])

    def adds_typeclass(f):
        def decorator(fn, params: Params) -> None:
            result: TypeClass2 = f(fn, params)
            params.mod.add_typeclass(result)
        return decorator

    @Wrangler.covers(asls_of_type("struct"))
    @adds_typeclass
    def struct_(fn, params: Params) -> TypeClass2:
        return TypeClassFactory.produce_proto_struct_type(
            name=params.asl_get_struct_name(),
            mod=params.asl_get_mod())

    @Wrangler.covers(asls_of_type("interface"))
    @adds_typeclass
    def interface_(fn, params: Params) -> TypeClass2:
        return TypeClassFactory.produce_proto_struct_type(
            name=params.asl_get_interface_name(),
            mod=params.asl_get_mod())

    @Wrangler.covers(asls_of_type("start", "mod"))
    def general_(fn, params: Params):
        for child in params.asl:
            fn.apply(params.but_with(asl=child))

    @Wrangler.default
    def default_(fn, params: Params):
        return

class FinalizeProtoWrangler(Wrangler):
    def apply(self, params: Params) -> None:
        return self._apply([params], [params])

    @classmethod
    def _get_component_names(cls, components: list[CLRList]) -> list[str]:
        if any([component.type != ":" for component in components]):
            raise Exception("expected all components to have type ':'")
        return [component.first().value for component in components]

    @Wrangler.covers(asls_of_type("start", "mod"))
    def general_(fn, params: Params):
        for child in params.asl:
            fn.apply(params.but_with(asl=child)) 
 
    @Wrangler.covers(asls_of_type("struct"))
    def struct_(fn, params: Params) -> None:
        # eg. (struct name (: ...) (: ...) ... (create ...))
        mod = params.asl_get_mod()
        this_struct_typeclass = mod.get_typeclass_by_name(params.asl.first().value)

        # there can be multiple interfaces implemented
        interfaces: list[TypeClass2] = []

        # this looks like (impls name1 name2)
        impls_asl = params.asl.second()
        for child in impls_asl:
            # TODO: currently we only allow the interface to be looked up in the same
            # module as the struct. In general, we need to allow interfaces from arbitrary
            # modules.
            interfaces.append(mod.get_typeclass_by_name(child.value))

        component_asls = [child for child in params.asl if child.type == ":" or child.type == ":="]
        this_struct_typeclass.finalize(
            components=[TypeClassWrangler().apply(params.but_with(asl=child)) for child in component_asls],
            component_names=FinalizeProtoWrangler._get_component_names(component_asls), 
            inherits=interfaces)

    @Wrangler.covers(asls_of_type("interface"))
    def interface_(fn, params: Params) -> None:
        # eg. (interface name (: ...) ...)
        mod = params.asl_get_mod()
        this_interface_typeclass = mod.get_typeclass_by_name(params.asl.first().value)
        
        # TODO: consider whether or not to allow interfaces to inherit from other interfaces
        component_asls = [child for child in params.asl if child.type == ":" or child.type == ":="]
        this_interface_typeclass.finalize(
            components=[TypeClassWrangler().apply(params.but_with(asl=child)) for child in component_asls],
            component_names=FinalizeProtoWrangler._get_component_names(component_asls), 
            inherits=[])

    @Wrangler.default
    def default_(fn, params: Params) -> None:
        return


class FunctionWrangler(Wrangler):
    def apply(self, params: Params):
        if self.debug and isinstance(params.asl, CLRList):
            print("\n"*64)
            print(params.inspect())
            print("\n"*4)
            input()
        return self._apply([params], [params])

    @Wrangler.default
    def start_(fn, params: Params):
        for child in params.asl:
            fn.apply(params.but_with(asl=child))

    @Wrangler.covers(lambda params: isinstance(params.asl, CLRToken))
    def token_(fn, params: Params) -> None:
        return None

    # we need to pass down the struct name for the create method
    @Wrangler.covers(asls_of_type("struct"))
    def struct_(fn, params: Params) -> None:
        for child in params.asl:
            fn.apply(params.but_with(asl=child, struct_name=params.asl_get_struct_name()))

    @Wrangler.covers(asls_of_type("def"))
    def def_i(fn, params: Params):
        mod = params.asl_get_mod()
        new_type = TypeClassWrangler().apply(params.but_with(mod=mod))
        params.mod.add_typeclass(new_type)
        params.oracle.add_instances(
            asl=params.asl,
            instances = [params.mod.add_instance(
                SeerInstance(
                    name=params.asl.first().value,
                    type=new_type,
                    context=mod,
                    asl=params.asl))])

    @Wrangler.covers(asls_of_type("create"))
    def create_i(fn, params: Params):
        mod = params.asl_get_mod()
        # add the struct name as the first parameter
        params.asl._list.insert(0, CLRToken(type_chain=["TAG"], value=params.struct_name))
        new_type = TypeClassWrangler().apply(params.but_with(mod=mod))
        params.mod.add_typeclass(new_type)
        params.oracle.add_instances(
            asl=params.asl,
            instances=[params.mod.add_instance(
                SeerInstance(
                    name=params.struct_name,
                    type=new_type,
                    context=params.mod,
                    asl=params.asl,
                    is_constructor=True))])























class TypeFlowWrangler2(Wrangler):
    def __init__(self, debug: bool = False):
        super().__init__(debug=debug)
        # self.debug = True

    def apply(self, params: Params) -> TypeClass2:
        if self.debug and isinstance(params.asl, CLRList):
            print("\n"*64)
            print(params.inspect())
            print("\n"*4)
            input()
        return self._apply([params], [params])

    def adds_typeclass(f):
        def decorator(fn, params: Params):
            result: TypeClass2 = f(fn, params)
            params.mod.add_typeclass(result)
            return result
        return decorator

    def records_typeclass(f):
        def decorator(fn, params: Params):
            result: TypeClass2 = f(fn, params)
            params.oracle.add_typeclass(params.asl, result)
            return result
        return decorator

    @Wrangler.covers(asls_of_type("fn_type"))
    @records_typeclass
    def fn_type_(fn, params: Params) -> TypeClass2:
        type = TypeClassWrangler().apply(params)
        return type

    no_action = ["start", "return", "seq"] 
    @Wrangler.covers(asls_of_type(*no_action))
    @records_typeclass
    def no_action_(fn, params: Params) -> TypeClass2:
        for child in params.asl:
            fn.apply(params.but_with(asl=child))
        return params.void_type

    @Wrangler.covers(asls_of_type("."))
    @records_typeclass
    def dot_(fn, params: Params) -> TypeClass2:
        parent_typeclass = fn.apply(params.but_with(asl=params.asl.head()))
        attr_name = params.asl[1].value
        attr_type = parent_typeclass.get_member_attribute_by_name(attr_name)
        return attr_type

    # TODO: will this work for a::b()?
    @Wrangler.covers(asls_of_type("::"))
    @records_typeclass
    def scope_(fn, params: Params) -> TypeClass2:
        next_mod = params.starting_mod.get_child_module_by_name(params.asl.first().value)
        return fn.apply(params.but_with(
            asl=params.asl.second(),
            starting_mod=next_mod,
            mod=next_mod))

    @Wrangler.covers(asls_of_type("tuple", "params", "prod_type"))
    @adds_typeclass
    @records_typeclass
    def tuple_(fn, params: Params) -> TypeClass2:
        return TypeClassFactory.produce_tuple_type(
            components=[fn.apply(params.but_with(asl=child)) for child in params.asl],
            global_mod=params.global_mod)

    @Wrangler.covers(asls_of_type("cond"))
    @records_typeclass
    def cond_(fn, params: Params) -> TypeClass2:
        for child in params.asl:
            fn.apply(params.but_with(asl=child))
        return params.void_type

    @Wrangler.covers(asls_of_type("if"))
    @records_typeclass
    def if_(fn, params: Params) -> TypeClass2:
        for child in params.asl:
            fn.apply(params.but_with(
                asl=child, 
                mod=Context(
                    name="if",
                    type=ContextTypes.block,
                    parent=params.mod)))
        return params.void_type

    @Wrangler.covers(asls_of_type("while"))
    @records_typeclass
    def while_(fn, params: Params) -> TypeClass2:
        fn.apply(params.but_with(
            asl=params.asl.first(),
            mod=Context(name="while", type=ContextTypes.block, parent=params.mod)))
        return params.void_type

    @Wrangler.covers(asls_of_type(":"))
    @records_typeclass
    def colon_(fn, params: Params) -> TypeClass2:
        if isinstance(params.asl.first(), CLRToken):
            names = [params.asl.first().value]
        else:
            if params.asl.first().type != "tags":
                raise Exception(f"Expected tags but got {params.asl.first().type}")
            names = [token.value for token in params.asl.first()]

        type = fn.apply(params.but_with(asl=params.asl.second()))
        instances = []
        for name in names:
            instances.append(
                params.mod.add_instance(
                    SeerInstance(name, type, params.mod, params.asl, is_ptr=params.is_ptr)))
        params.oracle.add_instances(params.asl, instances)
        return type

    @Wrangler.covers(asls_of_type("fn"))
    @adds_typeclass
    @records_typeclass
    def fn_(fn, params: Params) -> TypeClass2:
        if isinstance(params.asl.first(), CLRToken):
            name = params.asl.first().value
            # special case. TODO: fix this
            if name == "print":
                return TypeClassFactory.produce_function_type(
                        arg=params.void_type,
                        ret=params.void_type,
                        mod=params.global_mod)

            instance: SeerInstance = params.mod.get_instance_by_name(name=name)
            params.oracle.add_instances(params.asl, instance)
        else:
            type = fn.apply(params.but_with(asl=params.asl.first()))
            return type

        return instance.type

    @Wrangler.covers(asls_of_type("call"))
    @records_typeclass
    def call_(fn, params: Params) -> TypeClass2:
        fn_type = fn.apply(params.but_with(asl=params.asl.first()))

        # still need to type flow through the params passed to the function
        fn.apply(params.but_with(asl=params.asl.second()))
        return fn_type.get_return_type()

    @Wrangler.covers(asls_of_type("raw_call"))
    @records_typeclass
    def raw_call(fn, params: Params) -> TypeClass2:
        # e.g. (raw_call (expr ...) (fn name) (params ...))
        # because the first element can be a list itself, we need to expand it first
        first_type = fn.apply(params.but_with(asl=params.asl.first()))

        CallConfigurer.process(params)
        fn_type = fn.apply(params.but_with(asl=params.asl.first()))

        # still need to type flow through the params passed to the function
        fn.apply(params.but_with(asl=params.asl.second()))
        return fn_type.get_return_type()
         
    @Wrangler.covers(asls_of_type("struct"))
    @records_typeclass
    def struct(fn, params: Params) -> TypeClass2:
        name = params.asl.first().value
        # SeerEnsure.struct_has_unique_names(params)
        # pass struct name into context so the create method knows where it is defined
        # TODO: shouldn't add members to module
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child))
        return params.void_type

    @Wrangler.covers(asls_of_type("interface"))
    @records_typeclass
    def interface(fn, params: Params) -> TypeClass2:
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child))
        return params.void_type 

    @Wrangler.covers(asls_of_type("cast"))
    @records_typeclass
    def cast(fn, params: Params) -> TypeClass2:
        # (cast (ref name) (type into))
        left_typeclass = fn.apply(params.but_with(asl=params.asl.first()))
        right_typeclass = fn.apply(params.but_with(asl=params.asl.second()))

        if right_typeclass in left_typeclass.inherits:
            return right_typeclass

        raise Exception(f"TODO handle cast error {left_typeclass} != {right_typeclass}")

    @Wrangler.covers(asls_of_type("impls"))
    @records_typeclass
    def impls(fn, params: Params) -> TypeClass2:
        return params.void_type

    @Wrangler.covers(asls_of_type("mod"))
    @records_typeclass
    def mod(fn, params: Params) -> TypeClass2:
        name = params.asl.first().value
        child_mod = params.mod.get_child_module_by_name(name)
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child, mod=child_mod))
        return params.void_type
 


    @Wrangler.covers(asls_of_type("def", "create"))
    @records_typeclass
    def fn(fn, params: Params) -> TypeClass2:
        params.oracle.add_module_of_propagated_type(params.asl, params.mod)
        local_mod = Context(
            name=params.asl.first().value,
            type=ContextTypes.fn,
            parent=params.mod)
        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child, mod=local_mod))
        return params.void_type

    binary_ops = ['+', '-', '/', '*', '&&', '||', '<', '>', '<=', '>=', '==', '!=', '+=', '-=', '*=', '/='] 
    @Wrangler.covers(asls_of_type(*binary_ops))
    @records_typeclass
    def binary_ops(fn, params: Params) -> TypeClass2:
        left_type = fn.apply(params.but_with(asl=params.asl.first()))
        right_type = fn.apply(params.but_with(asl=params.asl.second()))

        if left_type != right_type:
            raise Exception("TODO: gracefully handle exception")

        return left_type


    @Wrangler.covers(lambda params: isinstance(params.asl, CLRToken))
    @adds_typeclass
    @records_typeclass
    def token_(fn, params: Params) -> TypeClass2:
        # TODO: make this nicer
        if params.asl.type in ["str", "int", "bool"]:
            return TypeClassFactory.produce_novel_type(name=params.asl.type, global_mod=params.global_mod)
        else:
            raise Exception(f"unexpected token type of {params.asl.type}")

    # cases for ilet:
    # - inference
    #       let x = 4
    #       (let x 4)
    @Wrangler.covers(asls_of_type("ilet"))
    @adds_typeclass
    @records_typeclass
    def idecls_(fn, params: Params):
        name = params.asl.first().value

        if isinstance(params.asl.second(), CLRToken):
            type=TypeClassFactory.produce_novel_type(
                name=params.asl.second().type,
                global_mod=params.global_mod)
            typeclass = TypeClass2.create_general(type)
        else:
            typeclass = fn.apply(params.but_with(asl=params.asl.second()))

        params.oracle.add_instances(
            asl=params.asl, 
            instances=[params.mod.add_instance(SeerInstance(
                name, 
                typeclass, 
                params.mod, 
                params.asl))])
        return typeclass
        
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
    @records_typeclass
    def decls_(fn, params: Params):
        if isinstance(params.asl.first(), CLRList) and params.asl.first().type == "tags":
            names = [token.value for token in params.asl.first()]
            types = [fn.apply(params.but_with(asl=child)) for child in params.asl.second()]

            instances = []
            for name, type in zip(names, types):
                instances.append(
                    params.mod.add_instance(SeerInstance(name, type, params.mod, params.asl)))
            params.oracle.add_instances(params.asl, instances)
            return params.void_type

        elif isinstance(params.asl.first(), CLRList) and params.asl.first().type == ":":
            type = fn.apply(params.but_with(asl=params.asl.first()))
            params.oracle.add_instances(
                asl=params.asl,
                instances=params.oracle.get_instances(params.asl.first()))
            return type

        else:
            raise Exception(f"Unexpected format: {params.asl}")

    @Wrangler.covers(asls_of_type("type", "type?", "type*"))
    @records_typeclass
    def _type1(fn, params: Params) -> TypeClass2:
        type = params.mod.get_typeclass_by_name(name=params.asl.first().value)
        mod = params.mod.get_module_of_type(name=params.asl.first().value)
        
        # TODO: handle if type not found
        params.oracle.add_module_of_propagated_type(params.asl, mod)
        return type

    @Wrangler.covers(asls_of_type("="))
    @records_typeclass
    def assigns(fn, params: Params) -> TypeClass2:
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
    @records_typeclass
    def larrow_(fn, params: Params) -> TypeClass2:
        left_type = fn.apply(params.but_with(asl=params.asl[0]))
        right_type = fn.apply(params.but_with(asl=params.asl[1]))

        # TODO: validations

        return left_type

    @Wrangler.covers(asls_of_type("ref"))
    @records_typeclass
    def ref_(fn, params: Params) -> TypeClass2:
        name = params.asl.first().value
        instance = params.mod.get_instance_by_name(name)
        if not instance:
            raise Exception("TODO: gracefully handle instance not being found")

        params.oracle.add_instances(params.asl, instance)
        return instance.type

    @Wrangler.covers(asls_of_type("args"))
    @records_typeclass
    def args_(fn, params: Params) -> TypeClass2:
        if not params.asl:
            return params.void_type
        type = fn.apply(params.but_with(asl=params.asl.first(), is_ptr=False))
        return type

    @Wrangler.covers(asls_of_type("rets"))
    @records_typeclass
    def rets_(fn, params: Params) -> TypeClass2:
        if not params.asl:
            return params.void_type
        type = fn.apply(params.but_with(asl=params.asl.first(), is_ptr=True))
        return type
