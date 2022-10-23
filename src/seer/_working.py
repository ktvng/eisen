from __future__ import annotations

from alpaca.utils import Wrangler
from alpaca.clr import CLRList, CLRToken
from alpaca.concepts import Context, TypeClass, TypeClassFactory

from seer._params import Params
from seer._common import asls_of_type, ContextTypes
from seer._exceptions import Exceptions

from seer._callconfigurer import CallConfigurer
from seer._common import asls_of_type, ContextTypes, SeerInstance, Module


################################################################################
# this parses the asl and creates the module structure of the program.
class ModuleWrangler2(Wrangler):
    def apply(self, params: Params):
        return self._apply([params], [params])

    # set the module inside which a given asl resides.
    def sets_module(f):
        def decorator(fn, params: Params):
            params.oracle.add_module(params.asl, params.mod)
            return f(fn, params)
        return decorator

    @Wrangler.default
    @sets_module
    def default_(fn, params: Params) -> Context:
        for child in params.asl:
            fn.apply(params.but_with(asl=child))

    @Wrangler.covers(asls_of_type("mod"))
    @sets_module
    def mod_(fn, params: Params) -> Context:
        # create a new module; the name of the module is stored as a CLRToken
        # in the first position of the module asl.
        new_mod = Module(
            name=params.asl.first().value,
            type=ContextTypes.mod, 
            parent=params.mod)

        for child in params.asl:
            fn.apply(params.but_with(
                asl=child, 
                mod=new_mod))

    @Wrangler.covers(lambda params: isinstance(params.asl, CLRToken))
    def token_(fn, params: Params) -> None:
        # nothing to do if we are given a CLRToken
        return None


################################################################################
# this parses the asl into a typeclass. certain asls define types. these are:
#   type, interface_type, prod_type, types, fn_type_in, fn_type_out, fn_type, args, rets
#   def, create, struct, interface
class TypeClassWrangler(Wrangler):
    def apply(self, params: Params) -> TypeClass:
        return self._apply([params], [params])

    @Wrangler.covers(asls_of_type("type"))
    def type_(fn, params: Params) -> TypeClass:
        # eg. (type int)
        token: CLRToken = params.asl.first()
        if token.type != "TAG":
            raise Exception(f"(type ...) must be a TAG attribute, but got {token.type} instead")

        found_type = params.asl_get_mod().get_typeclass_by_name(token.value)
        if found_type:
            return found_type
        raise Exception(f"unknown type! {token.value}")

    @Wrangler.covers(asls_of_type("interface_type"))
    def interface_type_(fn, params: Params) -> TypeClass:
        # eg. (interface_type name)
        token: CLRToken = params.asl.first()
        if token.type != "TAG":
            raise Exception(f"(type ...) must be a TAG attribute, but got {token.type} instead")

        found_type = params.asl_get_mod().get_typeclass_by_name(token.value)
        if found_type:
            return found_type
        raise Exception(f"unknown type! {token.value}")

    @Wrangler.covers(asls_of_type(":"))
    def colon_(fn, params: Params) -> TypeClass:
        # eg. (: name (type int))
        return fn.apply(params.but_with(asl=params.asl.second()))

    @Wrangler.covers(asls_of_type(":="))
    def eq_colon_(fn, params: Params) -> TypeClass:
        # eg. (:= name (args ...) (rets ...) (seq ...))
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(params.but_with(asl=params.asl.second())),
            ret=fn.apply(params.but_with(asl=params.asl.third())),
            mod=params.global_mod)


    @Wrangler.covers(asls_of_type("prod_type", "types"))
    def prod_type_(fn, params: Params) -> TypeClass:
        # eg.  (prod_type
        #           (: name1 (type int))
        #           (: name2 (type str)))
        # eg. (types (type int) (type str))
        component_types = [fn.apply(params.but_with(asl=component)) for component in params.asl]
        return TypeClassFactory.produce_tuple_type(components=component_types, global_mod=params.global_mod)

    @Wrangler.covers(asls_of_type("fn_type_in", "fn_type_out"))
    def fn_type_out(fn, params: Params) -> TypeClass:
        # eg. (fn_type_in/out (type(s) ...))
        if len(params.asl) == 0:
            return params.asl_get_mod().resolve_type(TypeClassFactory.produce_novel_type("void"))
        return fn.apply(params.but_with(asl=params.asl.first()))

    @Wrangler.covers(asls_of_type("fn_type")) 
    def fn_type_(fn, params: Params) -> TypeClass:
        # eg. (fn_type (fn_type_in ...) (fn_type_out ...))
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(params.but_with(asl=params.asl.first())),
            ret=fn.apply(params.but_with(asl=params.asl.second())),
            mod=params.global_mod)

    @Wrangler.covers(asls_of_type("args", "rets"))
    def args_(fn, params: Params) -> TypeClass:
        # eg. (args (type ...))
        if params.asl:
            return fn.apply(params.but_with(asl=params.asl.first()))
        return TypeClassFactory.produce_novel_type("void", params.global_mod)

    @Wrangler.covers(asls_of_type("def", "create"))
    def def_(fn, params: Params) -> TypeClass:
        # eg. (def name (args ...) (rets ...) (seq ...))
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(params.but_with(asl=params.asl.second())),
            ret=fn.apply(params.but_with(asl=params.asl.third())),
            mod=params.global_mod)
    
    @Wrangler.covers(asls_of_type("struct", "interface"))
    def struct_(fn, params: Params) -> TypeClass:
        # this method should not be reached. Instead, struct/interface typeclasses
        # should be created as a proto_struct/proto_interface by the
        # TypeDeclarationWrangler
        raise Exception("this should not be used to produce struct types")


################################################################################
# parses (struct ...) and (interface ...) asls into a proto_struct/proto_interface
# typeclass, which represents the declaration of the typeclass without the actual
# definition.
#
# see FinalizeProtoWrangler for more details.
class TypeDeclarationWrangler(Wrangler):
    def apply(self, params: Params) -> None:
        return self._apply([params], [params])

    def adds_typeclass_to_module(f):
        def decorator(fn, params: Params) -> None:
            result: TypeClass = f(fn, params)
            params.asl_get_mod().add_typeclass(result)
        return decorator

    @Wrangler.covers(asls_of_type("struct"))
    @adds_typeclass_to_module
    def struct_(fn, params: Params) -> TypeClass:
        return TypeClassFactory.produce_proto_struct_type(
            name=params.asl_get_struct_name(),
            mod=params.asl_get_mod())

    @Wrangler.covers(asls_of_type("interface"))
    @adds_typeclass_to_module
    def interface_(fn, params: Params) -> TypeClass:
        return TypeClassFactory.produce_proto_struct_type(
            name=params.asl_get_interface_name(),
            mod=params.asl_get_mod())

    @Wrangler.covers(asls_of_type("start", "mod"))
    def general_(fn, params: Params):
        for child in params.asl:
            fn.apply(params.but_with(asl=child))

    @Wrangler.default
    def default_(fn, params: Params):
        # nothing to do by default
        return


################################################################################
# this finalizes a proto_struct/proto_interface into a struct/interface typeclass.
# we need to separate declaration and definition because types may refer back to
# themselves, or to other types which have yet to be defined, but exist in the 
# same module.
class FinalizeProtoInterfaceWrangler(Wrangler):
    def apply(self, params: Params) -> None:
        return self._apply([params], [params])

    # returns the names (in order) for all components in a list of CLRlists.
    @classmethod
    def _get_component_names(cls, components: list[CLRList]) -> list[str]:
        if any([component.type != ":" for component in components]):
            raise Exception("expected all components to have type ':'")
        return [component.first().value for component in components]

    @Wrangler.covers(asls_of_type("start", "mod"))
    def general_(fn, params: Params):
        for child in params.asl:
            fn.apply(params.but_with(asl=child)) 
 
    @Wrangler.covers(asls_of_type("interface"))
    def interface_(fn, params: Params) -> None:
        # eg. (interface name (: ...) ...)
        mod = params.asl_get_mod()
        this_interface_typeclass = mod.get_typeclass_by_name(params.asl.first().value)
        
        # TODO: consider whether or not to allow interfaces to inherit from other interfaces
        component_asls = [child for child in params.asl if child.type == ":" or child.type == ":="]
        this_interface_typeclass.finalize(
            components=[TypeClassWrangler().apply(params.but_with(asl=child)) for child in component_asls],
            component_names=FinalizeProtoInterfaceWrangler._get_component_names(component_asls), 
            inherits=[])

    @Wrangler.default
    def default_(fn, params: Params) -> None:
        # nothing to do by default
        return


class FinalizeProtoStructWrangler(Wrangler):
    def apply(self, params: Params) -> None:
        return self._apply([params], [params])

    # returns the names (in order) for all components in a list of CLRlists.
    @classmethod
    def _get_component_names(cls, components: list[CLRList]) -> list[str]:
        if any([component.type != ":" and component.type != ":=" for component in components]):
            raise Exception("expected all components to have type ':' or ':=")
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
        interfaces: list[TypeClass] = []

        # this looks like (impls name1 name2)
        if len(params.asl) >= 2 and isinstance(params.asl.second(), CLRList) and params.asl.second().type == "impls":
            impls_asl = params.asl.second()
            for child in impls_asl:
                # TODO: currently we only allow the interface to be looked up in the same
                # module as the struct. In general, we need to allow interfaces from arbitrary
                # modules.
                interfaces.append(mod.get_typeclass_by_name(child.value))

        component_asls = [child for child in params.asl if child.type == ":" or child.type == ":="]
        this_struct_typeclass.finalize(
            components=[TypeClassWrangler().apply(params.but_with(asl=child)) for child in component_asls],
            component_names=FinalizeProtoStructWrangler._get_component_names(component_asls), 
            inherits=interfaces)

        for interface in interfaces:
            Validate.implementation_is_complete(params, this_struct_typeclass, interface)


    @Wrangler.default
    def default_(fn, params: Params) -> None:
        # nothing to do by default
        return




################################################################################
# this creates the function instances from (create ...) and (def ) asls. the 
# instances get added to the module so they can be used and called.
class FunctionWrangler(Wrangler):
    def apply(self, params: Params):
        if self.debug and isinstance(params.asl, CLRList):
            print("\n"*64)
            print(params.inspect())
            print("\n"*4)
            input()
        return self._apply([params], [params])

    @Wrangler.default
    def default_(fn, params: Params):
        for child in params.asl:
            fn.apply(params.but_with(asl=child))

    @Wrangler.covers(lambda params: isinstance(params.asl, CLRToken))
    def token_(fn, params: Params) -> None:
        return None

    @Wrangler.covers(asls_of_type("struct"))
    def struct_(fn, params: Params) -> None:
        # we need to pass down the struct name because the (create ...) asl will 
        # take on the name of the struct. 
        #
        # for example, a struct named MyStruct will have a constructor method 
        # called via MyStruct(...), so the (create ...)  method inside the 
        # (struct MyStruct ... ) asl needs context as to the struct it is inside.
        for child in params.asl:
            fn.apply(params.but_with(asl=child, struct_name=params.asl_get_struct_name()))

    @Wrangler.covers(asls_of_type("def"))
    def def_(fn, params: Params):
        mod = params.asl_get_mod()
        new_type = TypeClassWrangler().apply(params.but_with(mod=mod))
        params.asl_get_mod().add_typeclass(new_type)
        params.oracle.add_instances(
            asl=params.asl,
            instances = [params.asl_get_mod().add_instance(
                SeerInstance(
                    name=params.asl.first().value,
                    type=new_type,
                    context=mod,
                    asl=params.asl))])


    @Wrangler.covers(asls_of_type("create"))
    def create_(fn, params: Params):
        mod = params.asl_get_mod()
        # add the struct name as the first parameter. this normalize the structure
        # of (def ...) and (create ...) asls so we can use the same code to process
        # them
        params.asl._list.insert(0, CLRToken(type_chain=["TAG"], value=params.struct_name))
        new_type = TypeClassWrangler().apply(params.but_with(mod=mod))
        params.asl_get_mod().add_typeclass(new_type)
        params.oracle.add_instances(
            asl=params.asl,
            instances=[params.asl_get_mod().add_instance(
                SeerInstance(
                    name=params.struct_name,
                    type=new_type,
                    context=params.asl_get_mod(),
                    asl=params.asl,
                    is_constructor=True))])

















################################################################################
# this evaluates the flow of typeclasses throughout the asl, and records which 
# typeclass flows up through each asl.
class TypeClassFlowWrangler(Wrangler):
    def __init__(self, debug: bool = False):
        super().__init__(debug=debug)
        # self.debug = True

    def apply(self, params: Params) -> TypeClass:
        if self.debug and isinstance(params.asl, CLRList):
            print("\n"*64)
            print(params.inspect())
            print("\n"*4)
            input()
        return self._apply([params], [params])

    # this records the typeclass which flows up through this node (params.asl) 
    # so that it can be referenced later via params.asl_get_typeclass()
    def records_typeclass(f):
        def decorator(fn, params: Params):
            result: TypeClass = f(fn, params)
            params.oracle.add_typeclass(params.asl, result)
            return result
        return decorator

    # this guards the function such that if there is a critical exception thrown
    # downstream, the method will skip execution.
    def passes_if_critical_exception(f):
        def decorator(fn, params: Params):
            if params.critical_exception:
                return params.void_type,
            return f(fn, params)
        return decorator

    # this signifies that the void type should be returned. abstract this so if 
    # the void_type is changed, we can easily configure it here.
    def returns_void_type(f):
        def decorator(fn, params: Params):
            f(fn, params)
            return params.void_type
        return decorator


    @Wrangler.covers(asls_of_type("fn_type"))
    @records_typeclass
    @passes_if_critical_exception
    def fn_type_(fn, params: Params) -> TypeClass:
        return TypeClassWrangler().apply(params)


    no_action = ["start", "return", "seq", "cond"] 
    @Wrangler.covers(asls_of_type(*no_action))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def no_action_(fn, params: Params) -> TypeClass:
        for child in params.asl:
            fn.apply(params.but_with(asl=child))


    @Wrangler.covers(asls_of_type("."))
    @records_typeclass
    @passes_if_critical_exception
    def dot_(fn, params: Params) -> TypeClass:
        parent_typeclass = fn.apply(params.but_with(asl=params.asl.first()))
        return parent_typeclass.get_member_attribute_by_name(
            name=params.asl.second().value)


    # TODO: will this work for a::b()?
    @Wrangler.covers(asls_of_type("::"))
    @records_typeclass
    @passes_if_critical_exception
    def scope_(fn, params: Params) -> TypeClass:
        next_mod = params.starting_mod.get_child_module_by_name(params.asl.first().value)
        return fn.apply(params.but_with(
            asl=params.asl.second(),
            starting_mod=next_mod,
            mod=next_mod))


    @Wrangler.covers(asls_of_type("tuple", "params", "prod_type"))
    @records_typeclass
    @passes_if_critical_exception
    def tuple_(fn, params: Params) -> TypeClass:
        if len(params.asl) > 1:
            return TypeClassFactory.produce_tuple_type(
                components=[fn.apply(params.but_with(asl=child)) for child in params.asl],
                global_mod=params.global_mod)
        # if there is only one child, then we simply pass the type back, not as a tuple
        return fn.apply(params.but_with(asl=params.asl.first()))


    @Wrangler.covers(asls_of_type("if"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def if_(fn, params: Params) -> TypeClass:
        for child in params.asl:
            fn.apply(params.but_with(
                asl=child, 
                context=Context(
                    name="if",
                    type=ContextTypes.block,
                    parent=params.get_parent_context())))


    @Wrangler.covers(asls_of_type("while"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def while_(fn, params: Params) -> TypeClass:
        fn.apply(params.but_with(
            asl=params.asl.first(),
            context=Context(
                name="while", 
                type=ContextTypes.block, 
                parent=params.get_parent_context())))


    @Wrangler.covers(asls_of_type(":"))
    @records_typeclass
    @passes_if_critical_exception
    def colon_(fn, params: Params) -> TypeClass:
        if isinstance(params.asl.first(), CLRToken):
            names = [params.asl.first().value]
        else:
            # TODO: will we ever get here? probably
            if params.asl.first().type != "tags":
                raise Exception(f"Expected tags but got {params.asl.first().type}")
            names = [token.value for token in params.asl.first()]

        type = fn.apply(params.but_with(asl=params.asl.second()))
        instances = []
        for name in names:
            result = Validate.name_is_unbound(params, name)
            if not result.failed():
                instances.append(
                    params.context.add_instance(
                        SeerInstance(name, type, params.asl_get_mod(), params.asl, is_ptr=params.is_ptr)))
        params.oracle.add_instances(params.asl, instances)
        return type


    @Wrangler.covers(asls_of_type("fn"))
    @records_typeclass
    @passes_if_critical_exception
    def fn_(fn, params: Params) -> TypeClass:
        if isinstance(params.asl.first(), CLRToken):
            name = params.asl.first().value
            # special case. TODO: fix this
            if name == "print":
                return TypeClassFactory.produce_function_type(
                        arg=params.void_type,
                        ret=params.void_type,
                        mod=params.global_mod)

            result = Validate.function_instance_exists(params)
            if result.failed():
                return result.get_failure_type()

            instance = result.get_found_instance()
            params.oracle.add_instances(params.asl, instance)
            return instance.type
        else:
            return fn.apply(params.but_with(asl=params.asl.first()))



    @Wrangler.covers(asls_of_type("call"))
    @records_typeclass
    @passes_if_critical_exception
    def call_(fn, params: Params) -> TypeClass:
        fn_type = fn.apply(params.but_with(asl=params.asl.first()))
        if fn_type == params.abort_signal:
            return params.abort_signal

        # still need to type flow through the params passed to the function
        params_type = fn.apply(params.but_with(asl=params.asl.second()))

        # TODO: make this nicer. aka. figure out a better way to get the function name
        fn_name = ""
        if params.asl.first().type == "fn" and isinstance(params.asl.first().first(), CLRToken):
            fn_name = params.asl.first().first().value
        if fn_name != "print":
            fn_in_type = fn_type.get_argument_type()
            result = Validate.correct_argument_types(params, fn_name, fn_in_type, params_type)
            if result.failed():
                return result.get_failure_type()

        return fn_type.get_return_type()


    @Wrangler.covers(asls_of_type("raw_call"))
    @records_typeclass
    @passes_if_critical_exception
    def raw_call(fn, params: Params) -> TypeClass:
        # e.g. (raw_call (expr ...) (fn name) (params ...))
        # because the first element can be a list itself, we need to apply the 
        # fn over it to get the flowed out type.
        fn.apply(params.but_with(asl=params.asl.first()))

        # this will actually change params.asl, converting (raw_call ...) into (call ...)
        CallConfigurer.process(params)
        # print(params.asl)

        # now we have converted the (raw_call ...) into a normal (call ...) asl 
        # so we can apply fn to the params again with the new asl.
        return fn.apply(params)
         

    @Wrangler.covers(asls_of_type("struct", "interface"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def struct(fn, params: Params) -> TypeClass:
        # ignore the first element because this is the CLRToken storing the name
        for child in params.asl[1:]:
            fn.apply(params.but_with(
                asl=child,
                context=Context(
                    name="struct",
                    type=ContextTypes.block,
                    parent=None)))


    @Wrangler.covers(asls_of_type("cast"))
    @records_typeclass
    @passes_if_critical_exception
    def cast(fn, params: Params) -> TypeClass:
        # (cast (ref name) (type into))
        left_typeclass = fn.apply(params.but_with(asl=params.asl.first()))
        right_typeclass = fn.apply(params.but_with(asl=params.asl.second()))

        result = Validate.castable_types(params, 
            type=left_typeclass, 
            cast_into_type=right_typeclass)
        if result.failed():
            return result.get_failure_type()
        return right_typeclass


    @Wrangler.covers(asls_of_type("impls"))
    @records_typeclass
    @passes_if_critical_exception
    def impls(fn, params: Params) -> TypeClass:
        return params.void_type


    @Wrangler.covers(asls_of_type("mod"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def mod(fn, params: Params) -> TypeClass:
        name = params.asl.first().value
        for child in params.asl[1:]:
            fn.apply(params.but_with(
                asl=child, 
                mod=params.asl_get_mod().get_child_module_by_name(name)))


    @Wrangler.covers(asls_of_type("def", "create", ":="))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def fn(fn, params: Params) -> TypeClass:
        # inside the FunctionWrangler, (def ...) and (create ...) asls have been
        # normalized to have the same signature. therefore we can treat them identically
        # here

        parent_context = params.get_parent_context() if params.asl.type == "def" else None
        fn_context = Context(
            name=params.asl.first().value,
            type=ContextTypes.fn,
            parent=parent_context)

        for child in params.asl[1:]:
            fn.apply(params.but_with(asl=child, context=fn_context))


    # we don't need to add/record typeclasses because this is a CLRToken
    @Wrangler.covers(lambda params: isinstance(params.asl, CLRToken))
    @passes_if_critical_exception
    def token_(fn, params: Params) -> TypeClass:
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
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def idecls_(fn, params: Params):
        if isinstance(params.asl.first(), CLRList):
            names = [token.value for token in params.asl.first()]
            typeclasses = [fn.apply(params.but_with(asl=child)) for child in params.asl.second()]
        else:
            names = [params.asl.first().value]
            typeclasses = [fn.apply(params.but_with(asl=params.asl.second()))]

        instances = []
        for name, typeclass in zip(names, typeclasses):
            result = Validate.name_is_unbound(params, name)
            if result.failed():
                return 

            if type is params.abort_signal:
                params.critical_exception.set(True)
                return

            instances.append(SeerInstance(
                name, 
                typeclass, 
                params.asl_get_mod(), 
                params.asl))

        params.oracle.add_instances(params.asl, instances)
        for instance in instances:
            params.context.add_instance(instance)


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
    @Wrangler.covers(asls_of_type("val", "var", "mut_val", "mut_var", "let"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def decls_(fn, params: Params):
        if isinstance(params.asl.first(), CLRList) and params.asl.first().type == "tags":
            names = [token.value for token in params.asl.first()]
            types = [fn.apply(params.but_with(asl=child)) for child in params.asl.second()]

            instances = []
            for name, type in zip(names, types):
                result = Validate.name_is_unbound(params, name)
                if not result.failed():
                    instances.append(
                        params.context.add_instance(SeerInstance(name, type, params.asl_get_mod(), params.asl)))
            params.oracle.add_instances(params.asl, instances)

        elif isinstance(params.asl.first(), CLRList) and params.asl.first().type == ":":
            # validations occur inside the (: ...) asl 
            type = fn.apply(params.but_with(asl=params.asl.first()))
            params.oracle.add_instances(
                asl=params.asl,
                instances=params.oracle.get_instances(params.asl.first()))

    @Wrangler.covers(asls_of_type("type", "type?", "type*"))
    @records_typeclass
    @passes_if_critical_exception
    def _type1(fn, params: Params) -> TypeClass:
        return params.asl_get_mod().get_typeclass_by_name(name=params.asl.first().value)


    binary_ops = ["+", "-", "/", "*", "&&", "||", "<", ">", "<=", ">=", "==", "!=", "+=", "-=", "*=", "/="] 
    @Wrangler.covers(asls_of_type(*binary_ops))
    @records_typeclass
    @passes_if_critical_exception
    def binary_ops(fn, params: Params) -> TypeClass:
        left_type = fn.apply(params.but_with(asl=params.asl.first()))
        right_type = fn.apply(params.but_with(asl=params.asl.second()))

        result = Validate.equivalent_types(params, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type


    @Wrangler.covers(asls_of_type("="))
    @records_typeclass
    @passes_if_critical_exception
    def assigns(fn, params: Params) -> TypeClass:
        left_type = fn.apply(params.but_with(asl=params.asl.first()))
        right_type = fn.apply(params.but_with(asl=params.asl.second()))

        result = Validate.equivalent_types(params, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type
        

    @Wrangler.covers(asls_of_type("<-"))
    @records_typeclass
    @passes_if_critical_exception
    def larrow_(fn, params: Params) -> TypeClass:
        left_type = fn.apply(params.but_with(asl=params.asl.first()))
        right_type = fn.apply(params.but_with(asl=params.asl.second()))

        result = Validate.equivalent_types(params, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type


    @Wrangler.covers(asls_of_type("ref"))
    @records_typeclass
    @passes_if_critical_exception
    def ref_(fn, params: Params) -> TypeClass:
        result = Validate.instance_exists(params)
        if result.failed():
            return result.get_failure_type()

        instance = result.get_found_instance()
        params.oracle.add_instances(params.asl, instance)
        return instance.type


    @Wrangler.covers(asls_of_type("args"))
    @records_typeclass
    @passes_if_critical_exception
    def args_(fn, params: Params) -> TypeClass:
        if not params.asl:
            return params.void_type
        type = fn.apply(params.but_with(asl=params.asl.first(), is_ptr=False))
        return type


    @Wrangler.covers(asls_of_type("rets"))
    @records_typeclass
    @passes_if_critical_exception
    def rets_(fn, params: Params) -> TypeClass:
        if not params.asl:
            return params.void_type
        type = fn.apply(params.but_with(asl=params.asl.first(), is_ptr=True))
        return type


class ValidationResult():
    def __init__(self, result: bool, return_obj: TypeClass | SeerInstance):
        self.result = result
        self.return_obj = return_obj

    def failed(self) -> bool:
        return not self.result

    def get_failure_type(self) -> TypeClass:
        return self.return_obj

    def get_found_instance(self) -> SeerInstance:
        return self.return_obj


################################################################################
# performs the actual validations
class Validate:
    @classmethod
    def _abort_signal(cls, params: Params) -> ValidationResult:
        return ValidationResult(result=False, return_obj=params.abort_signal)

    @classmethod
    def _success(cls, return_obj=None) -> ValidationResult:
        return ValidationResult(result=True, return_obj=return_obj)

    @classmethod
    def equivalent_types(cls, params: Params, type1: TypeClass, type2: TypeClass) -> ValidationResult:
        if any([params.abort_signal in (type1, type2)]):
            return Validate._abort_signal(params) 

        if type1 != type2:
            params.report_exception(Exceptions.TypeMismatch(
                msg=f"'{type1}' != '{type2}'",
                line_number=params.asl.line_number))
            return Validate._abort_signal(params) 
        return Validate._success(type1)


    @classmethod
    def correct_argument_types(cls, params: Params, name: str, fn_type: TypeClass, given_type: TypeClass) -> ValidationResult:
        if any([params.abort_signal in (fn_type, given_type)]):
            return Validate._abort_signal(params) 

        if fn_type != given_type:
            params.report_exception(Exceptions.TypeMismatch(
                msg=f"function '{name}' takes '{fn_type}' but was given '{given_type}'",
                line_number=params.asl.line_number))
            return Validate._abort_signal(params) 
        return Validate._success(fn_type)


    @classmethod
    def instance_exists(cls, params: Params) -> ValidationResult:
        name = params.asl.first().value
        instance = params.context.get_instance_by_name(name)
        if instance is None:
            params.report_exception(Exceptions.UndefinedVariable(
                msg=f"'{name}' is not defined",
                line_number=params.asl.line_number))
            return Validate._abort_signal(params) 
        return Validate._success(return_obj=instance)


    @classmethod
    def function_instance_exists(cls, params: Params) -> ValidationResult:
        name = params.asl.first().value
        instance = params.context.get_instance_by_name(name)
        if instance is None:
            params.report_exception(Exceptions.UndefinedFunction(
                msg=f"'{name}' is not defined",
                line_number=params.asl.line_number))
            return Validate._abort_signal(params) 
        return Validate._success(return_obj=instance)

    
    @classmethod
    def name_is_unbound(cls, params: Params, name: str) -> ValidationResult:
        if params.context.find_instance(name) is not None:
            params.report_exception(Exceptions.RedefinedIdentifier(
                msg=f"'{name}' is in use",
                line_number=params.asl.line_number))
            return Validate._abort_signal(params)
        return Validate._success(return_obj=None)

    
    @classmethod
    def castable_types(cls, params: Params, type: TypeClass, cast_into_type: TypeClass) -> ValidationResult:
        if any([params.abort_signal in (type, cast_into_type)]):
            return Validate._abort_signal(params) 

        if cast_into_type not in type.inherits:
            params.report_exception(Exceptions.CastIncompatibleTypes(
                msg=f"'{type}' cannot be cast into '{cast_into_type}'",
                line_number=params.asl.line_number))
            return Validate._abort_signal(params)
        return Validate._success(return_obj=None)


    @classmethod
    def implementation_is_complete(cls, params: Params, type: TypeClass, inherited_type: TypeClass) -> ValidationResult:
        encountered_exception = False
        for name, required_attribute_type in zip(inherited_type.component_names, inherited_type.components):
            if type.has_member_attribute_with_name(name):
                attribute_type = type.get_member_attribute_by_name(name)
                if attribute_type != required_attribute_type:
                    encountered_exception = True
                    params.report_exception(Exceptions.AttributeMismatch(
                        msg=f"'{type}' has attribute '{name}' of '{attribute_type}', but '{required_attribute_type}' is required to inherit '{inherited_type}'",
                        line_number=params.asl.line_number))
            else:
                encountered_exception = True
                params.report_exception(Exceptions.MissingAttribute(
                    msg=f"'{type}' is missing attribute '{name}' required to inherit '{inherited_type}'",
                    line_number=params.asl.line_number))

        if encountered_exception:
            return Validate._abort_signal(params)
        return Validate._success()
        