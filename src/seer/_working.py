from __future__ import annotations
import re

from alpaca.utils import Wrangler
from alpaca.clr import CLRList, CLRToken
from alpaca.concepts import Context, TypeClass, TypeClassFactory

from seer._params import Params
from seer._common import asls_of_type, ContextTypes
from seer._exceptions import Exceptions

from seer._callconfigurer import CallConfigurer
from seer._common import asls_of_type, ContextTypes, SeerInstance, Module
from seer._nodedata import NodeData


class InitializeNodeData(Wrangler):
    def apply(self, state: Params) -> None:
        return self._apply([state], [state])

    @Wrangler.default
    def default_(fn, state: Params) -> None:
        state.asl.data = NodeData()
        for child in state.asl:
            if isinstance(child, CLRList):
                fn.apply(state.but_with(asl=child))
        
################################################################################
# this parses the asl and creates the module structure of the program.
class ModuleWrangler2(Wrangler):
    def apply(self, state: Params):
        return self._apply([state], [state])

    # set the module inside which a given asl resides.
    def sets_module(f):
        def decorator(fn, state: Params):
            state.assign_module()
            return f(fn, state)
        return decorator

    @Wrangler.default
    @sets_module
    def default_(fn, state: Params) -> Module:
        for child in state.asl:
            if isinstance(child, CLRList):
                fn.apply(state.but_with(asl=child))

    @Wrangler.covers(asls_of_type("mod"))
    @sets_module
    def mod_(fn, state: Params) -> Module:
        # create a new module; the name of the module is stored as a CLRToken
        # in the first position of the module asl.
        new_mod = Module(
            name=state.asl.first().value,
            type=ContextTypes.mod, 
            parent=state.mod)

        for child in state.asl:
            fn.apply(state.but_with(
                asl=child, 
                mod=new_mod))


################################################################################
# this parses the asl into a typeclass. certain asls define types. these are:
#   type, interface_type, prod_type, types, fn_type_in, fn_type_out, fn_type, args, rets
#   def, create, struct, interface
class TypeClassWrangler(Wrangler):
    def apply(self, state: Params) -> TypeClass:
        return self._apply([state], [state])

    @Wrangler.covers(asls_of_type("type"))
    def type_(fn, state: Params) -> TypeClass:
        # eg. (type int)
        token: CLRToken = state.asl.first()
        if token.type != "TAG":
            raise Exception(f"(type ...) must be a TAG attribute, but got {token.type} instead")

        found_type = state.get_module().get_typeclass_by_name(token.value)
        if found_type:
            return found_type
        raise Exception(f"unknown type! {token.value}")

    @Wrangler.covers(asls_of_type("interface_type"))
    def interface_type_(fn, state: Params) -> TypeClass:
        # eg. (interface_type name)
        token: CLRToken = state.asl.first()
        if token.type != "TAG":
            raise Exception(f"(type ...) must be a TAG attribute, but got {token.type} instead")

        found_type = state.get_module().get_typeclass_by_name(token.value)
        if found_type:
            return found_type
        raise Exception(f"unknown type! {token.value}")

    @Wrangler.covers(asls_of_type(":"))
    def colon_(fn, state: Params) -> TypeClass:
        # eg. (: name (type int))
        return fn.apply(state.but_with(asl=state.asl.second()))

    @Wrangler.covers(asls_of_type(":="))
    def eq_colon_(fn, state: Params) -> TypeClass:
        # eg. (:= name (args ...) (rets ...) (seq ...))
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(state.but_with(asl=state.asl.second())),
            ret=fn.apply(state.but_with(asl=state.asl.third())),
            mod=state.global_mod)


    @Wrangler.covers(asls_of_type("prod_type", "types"))
    def prod_type_(fn, state: Params) -> TypeClass:
        # eg.  (prod_type
        #           (: name1 (type int))
        #           (: name2 (type str)))
        # eg. (types (type int) (type str))
        component_types = [fn.apply(state.but_with(asl=component)) for component in state.asl]
        return TypeClassFactory.produce_tuple_type(components=component_types, global_mod=state.global_mod)

    @Wrangler.covers(asls_of_type("fn_type_in", "fn_type_out"))
    def fn_type_out(fn, state: Params) -> TypeClass:
        # eg. (fn_type_in/out (type(s) ...))
        if len(state.asl) == 0:
            return state.get_module().resolve_type(TypeClassFactory.produce_novel_type("void"))
        return fn.apply(state.but_with(asl=state.asl.first()))

    @Wrangler.covers(asls_of_type("fn_type")) 
    def fn_type_(fn, state: Params) -> TypeClass:
        # eg. (fn_type (fn_type_in ...) (fn_type_out ...))
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(state.but_with(asl=state.asl.first())),
            ret=fn.apply(state.but_with(asl=state.asl.second())),
            mod=state.global_mod)

    @Wrangler.covers(asls_of_type("args", "rets"))
    def args_(fn, state: Params) -> TypeClass:
        # eg. (args (type ...))
        if state.asl:
            return fn.apply(state.but_with(asl=state.asl.first()))
        return TypeClassFactory.produce_novel_type("void", state.global_mod)

    @Wrangler.covers(asls_of_type("def", "create"))
    def def_(fn, state: Params) -> TypeClass:
        # eg. (def name (args ...) (rets ...) (seq ...))
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(state.but_with(asl=state.asl.second())),
            ret=fn.apply(state.but_with(asl=state.asl.third())),
            mod=state.global_mod)
    
    @Wrangler.covers(asls_of_type("struct", "interface"))
    def struct_(fn, state: Params) -> TypeClass:
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
    def apply(self, state: Params) -> None:
        return self._apply([state], [state])

    def adds_typeclass_to_module(f):
        def decorator(fn, state: Params) -> None:
            result: TypeClass = f(fn, state)
            state.get_module().add_typeclass(result)
        return decorator

    @Wrangler.covers(asls_of_type("struct"))
    @adds_typeclass_to_module
    def struct_(fn, state: Params) -> TypeClass:
        return TypeClassFactory.produce_proto_struct_type(
            name=state.asl_get_struct_name(),
            mod=state.get_module())

    @Wrangler.covers(asls_of_type("interface"))
    @adds_typeclass_to_module
    def interface_(fn, state: Params) -> TypeClass:
        return TypeClassFactory.produce_proto_interface_type(
            name=state.asl_get_interface_name(),
            mod=state.get_module())

    @Wrangler.covers(asls_of_type("start", "mod"))
    def general_(fn, state: Params):
        for child in state.asl:
            fn.apply(state.but_with(asl=child))

    @Wrangler.default
    def default_(fn, state: Params):
        # nothing to do by default
        return


################################################################################
# this finalizes a proto_struct/proto_interface into a struct/interface typeclass.
# we need to separate declaration and definition because types may refer back to
# themselves, or to other types which have yet to be defined, but exist in the 
# same module.
class FinalizeProtoInterfaceWrangler(Wrangler):
    def apply(self, state: Params) -> None:
        return self._apply([state], [state])

    # returns the names (in order) for all components in a list of CLRlists.
    @classmethod
    def _get_component_names(cls, components: list[CLRList]) -> list[str]:
        if any([component.type != ":" for component in components]):
            raise Exception("expected all components to have type ':'")
        return [component.first().value for component in components]

    @Wrangler.covers(asls_of_type("start", "mod"))
    def general_(fn, state: Params):
        for child in state.asl:
            fn.apply(state.but_with(asl=child)) 
 
    @Wrangler.covers(asls_of_type("interface"))
    def interface_(fn, state: Params) -> None:
        # eg. (interface name (: ...) ...)
        mod = state.get_module()
        this_interface_typeclass = mod.get_typeclass_by_name(state.asl.first().value)
        
        # TODO: consider whether or not to allow interfaces to inherit from other interfaces
        component_asls = [child for child in state.asl if child.type == ":" or child.type == ":="]
        this_interface_typeclass.finalize(
            components=[TypeClassWrangler().apply(state.but_with(asl=child)) for child in component_asls],
            component_names=FinalizeProtoInterfaceWrangler._get_component_names(component_asls), 
            inherits=[])

    @Wrangler.default
    def default_(fn, state: Params) -> None:
        # nothing to do by default
        return


class FinalizeProtoStructWrangler(Wrangler):
    def apply(self, state: Params) -> None:
        return self._apply([state], [state])

    # returns the names (in order) for all components in a list of CLRlists.
    @classmethod
    def _get_component_names(cls, components: list[CLRList]) -> list[str]:
        if any([component.type != ":" and component.type != ":=" for component in components]):
            raise Exception("expected all components to have type ':' or ':=")
        return [component.first().value for component in components]

    @Wrangler.covers(asls_of_type("start", "mod"))
    def general_(fn, state: Params):
        for child in state.asl:
            fn.apply(state.but_with(asl=child)) 
 
    @Wrangler.covers(asls_of_type("struct"))
    def struct_(fn, state: Params) -> None:
        # eg. (struct name (: ...) (: ...) ... (create ...))
        mod = state.get_module()
        this_struct_typeclass = mod.get_typeclass_by_name(state.asl.first().value)

        # there can be multiple interfaces implemented
        interfaces: list[TypeClass] = []

        # this looks like (impls name1 name2)
        if len(state.asl) >= 2 and isinstance(state.asl.second(), CLRList) and state.asl.second().type == "impls":
            impls_asl = state.asl.second()
            for child in impls_asl:
                # TODO: currently we only allow the interface to be looked up in the same
                # module as the struct. In general, we need to allow interfaces from arbitrary
                # modules.
                interfaces.append(mod.get_typeclass_by_name(child.value))

        component_asls = [child for child in state.asl if child.type == ":" or child.type == ":="]
        this_struct_typeclass.finalize(
            components=[TypeClassWrangler().apply(state.but_with(asl=child)) for child in component_asls],
            component_names=FinalizeProtoStructWrangler._get_component_names(component_asls), 
            inherits=interfaces)

        for interface in interfaces:
            Validate.implementation_is_complete(state, this_struct_typeclass, interface)


    @Wrangler.default
    def default_(fn, state: Params) -> None:
        # nothing to do by default
        return




################################################################################
# this creates the function instances from (create ...) and (def ) asls. the 
# instances get added to the module so they can be used and called.
class FunctionWrangler(Wrangler):
    def apply(self, state: Params):
        if self.debug and isinstance(state.asl, CLRList):
            print("\n"*64)
            print(state.inspect())
            print("\n"*4)
            input()
        return self._apply([state], [state])

    @Wrangler.default
    def default_(fn, state: Params):
        for child in state.asl:
            fn.apply(state.but_with(asl=child))

    @Wrangler.covers(lambda state: isinstance(state.asl, CLRToken))
    def token_(fn, state: Params) -> None:
        return None

    @Wrangler.covers(asls_of_type("struct"))
    def struct_(fn, state: Params) -> None:
        # we need to pass down the struct name because the (create ...) asl will 
        # take on the name of the struct. 
        #
        # for example, a struct named MyStruct will have a constructor method 
        # called via MyStruct(...), so the (create ...)  method inside the 
        # (struct MyStruct ... ) asl needs context as to the struct it is inside.
        for child in state.asl:
            fn.apply(state.but_with(asl=child, struct_name=state.asl_get_struct_name()))

    @Wrangler.covers(asls_of_type("def"))
    def def_(fn, state: Params):
        mod = state.get_module()
        new_type = TypeClassWrangler().apply(state.but_with(mod=mod))
        state.get_module().add_typeclass(new_type)
        state.assign_instances(
            [state.get_module().add_instance(
                SeerInstance(
                    name=state.asl.first().value,
                    type=new_type,
                    context=mod,
                    asl=state.asl))])


    @Wrangler.covers(asls_of_type("create"))
    def create_(fn, state: Params):
        mod = state.get_module()
        # add the struct name as the first parameter. this normalize the structure
        # of (def ...) and (create ...) asls so we can use the same code to process
        # them
        state.asl._list.insert(0, CLRToken(type_chain=["TAG"], value=state.struct_name))
        new_type = TypeClassWrangler().apply(state.but_with(mod=mod))
        state.get_module().add_typeclass(new_type)
        state.assign_instances(
            [state.get_module().add_instance(
                SeerInstance(
                    name=state.struct_name,
                    type=new_type,
                    context=state.get_module(),
                    asl=state.asl,
                    is_constructor=True))])

















################################################################################
# this evaluates the flow of typeclasses throughout the asl, and records which 
# typeclass flows up through each asl.
class TypeClassFlowWrangler(Wrangler):
    def __init__(self, debug: bool = False):
        super().__init__(debug=debug)
        # self.debug = True

    def apply(self, state: Params) -> TypeClass:
        if self.debug and isinstance(state.asl, CLRList):
            print("\n"*64)
            print(state.inspect())
            print("\n"*64)
            input()
        return self._apply([state], [state])

    # this records the typeclass which flows up through this node (state.asl) 
    # so that it can be referenced later via state.get_returned_typeclass()
    def records_typeclass(f):
        def decorator(fn, state: Params):
            result: TypeClass = f(fn, state)
            state.assign_returned_typeclass(result)
            return result
        return decorator

    # this guards the function such that if there is a critical exception thrown
    # downstream, the method will skip execution.
    def passes_if_critical_exception(f):
        def decorator(fn, state: Params):
            if state.critical_exception:
                return state.void_type,
            return f(fn, state)
        return decorator

    # this signifies that the void type should be returned. abstract this so if 
    # the void_type is changed, we can easily configure it here.
    def returns_void_type(f):
        def decorator(fn, state: Params):
            f(fn, state)
            return state.void_type
        return decorator


    @Wrangler.covers(asls_of_type("fn_type"))
    @records_typeclass
    @passes_if_critical_exception
    def fn_type_(fn, state: Params) -> TypeClass:
        return TypeClassWrangler().apply(state)


    no_action = ["start", "return", "seq", "cond"] 
    @Wrangler.covers(asls_of_type(*no_action))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def no_action_(fn, state: Params) -> TypeClass:
        for child in state.asl:
            fn.apply(state.but_with(asl=child))

    @Wrangler.covers(asls_of_type("!"))
    @records_typeclass
    @passes_if_critical_exception
    def not_(fn, state: Params) -> TypeClass:
        return fn.apply(state.but_with(asl=state.asl.first()))


    @Wrangler.covers(asls_of_type("."))
    @records_typeclass
    @passes_if_critical_exception
    def dot_(fn, state: Params) -> TypeClass:
        parent_typeclass = fn.apply(state.but_with(asl=state.asl.first()))
        name = state.asl.second().value
        result = Validate.has_member_attribute(state, parent_typeclass, name)
        if result.failed():
            return result.get_failure_type()
        return parent_typeclass.get_member_attribute_by_name(name)


    # TODO: will this work for a::b()?
    @Wrangler.covers(asls_of_type("::"))
    @records_typeclass
    @passes_if_critical_exception
    def scope_(fn, state: Params) -> TypeClass:
        next_mod = state.starting_mod.get_child_module_by_name(state.asl.first().value)
        return fn.apply(state.but_with(
            asl=state.asl.second(),
            starting_mod=next_mod,
            mod=next_mod))


    @Wrangler.covers(asls_of_type("tuple", "params", "prod_type"))
    @records_typeclass
    @passes_if_critical_exception
    def tuple_(fn, state: Params) -> TypeClass:
        if len(state.asl) == 0:
            return state.void_type
        if len(state.asl) > 1:
            return TypeClassFactory.produce_tuple_type(
                components=[fn.apply(state.but_with(asl=child)) for child in state.asl],
                global_mod=state.global_mod)
        # if there is only one child, then we simply pass the type back, not as a tuple
        return fn.apply(state.but_with(asl=state.asl.first()))


    @Wrangler.covers(asls_of_type("if"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def if_(fn, state: Params) -> TypeClass:
        for child in state.asl:
            fn.apply(state.but_with(
                asl=child, 
                context=Context(
                    name="if",
                    type=ContextTypes.block,
                    parent=state.get_parent_context())))


    @Wrangler.covers(asls_of_type("while"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def while_(fn, state: Params) -> TypeClass:
        fn.apply(state.but_with(
            asl=state.asl.first(),
            context=Context(
                name="while", 
                type=ContextTypes.block, 
                parent=state.get_parent_context())))


    @Wrangler.covers(asls_of_type(":"))
    @records_typeclass
    @passes_if_critical_exception
    def colon_(fn, state: Params) -> TypeClass:
        if isinstance(state.asl.first(), CLRToken):
            names = [state.asl.first().value]
        else:
            # TODO: will we ever get here? probably
            if state.asl.first().type != "tags":
                raise Exception(f"Expected tags but got {state.asl.first().type}")
            names = [token.value for token in state.asl.first()]

        type = fn.apply(state.but_with(asl=state.asl.second()))
        instances = []
        for name in names:
            result = Validate.name_is_unbound(state, name)
            if not result.failed():
                instances.append(
                    state.context.add_instance(
                        SeerInstance(name, type, state.get_module(), state.asl, is_ptr=state.is_ptr)))
        state.assign_instances(instances)
        return type


    @Wrangler.covers(asls_of_type("fn"))
    @records_typeclass
    @passes_if_critical_exception
    def fn_(fn, state: Params) -> TypeClass:
        if isinstance(state.asl.first(), CLRToken):
            name = state.asl.first().value
            # special case. TODO: fix this
            if name == "print":
                return TypeClassFactory.produce_function_type(
                        arg=state.void_type,
                        ret=state.void_type,
                        mod=state.global_mod)

            result = Validate.function_instance_exists(state)
            if result.failed():
                return result.get_failure_type()

            instance = result.get_found_instance()
            state.assign_instances(instance)
            return instance.type
        else:
            return fn.apply(state.but_with(asl=state.asl.first()))



    @Wrangler.covers(asls_of_type("call"))
    @records_typeclass
    @passes_if_critical_exception
    def call_(fn, state: Params) -> TypeClass:
        fn_type = fn.apply(state.but_with(asl=state.asl.first()))
        if fn_type == state.abort_signal:
            return state.abort_signal

        # still need to type flow through the state passed to the function
        state_type = fn.apply(state.but_with(asl=state.asl.second()))

        # TODO: make this nicer. aka. figure out a better way to get the function name
        fn_name = ""
        if state.asl.first().type == "fn" and isinstance(state.asl.first().first(), CLRToken):
            fn_name = state.asl.first().first().value
        if fn_name != "print":
            fn_in_type = fn_type.get_argument_type()
            result = Validate.correct_argument_types(state, fn_name, fn_in_type, state_type)
            if result.failed():
                return result.get_failure_type()

        return fn_type.get_return_type()


    @Wrangler.covers(asls_of_type("raw_call"))
    @records_typeclass
    @passes_if_critical_exception
    def raw_call(fn, state: Params) -> TypeClass:
        # e.g. (raw_call (expr ...) (fn name) (state ...))
        # because the first element can be a list itself, we need to apply the 
        # fn over it to get the flowed out type.
        fn.apply(state.but_with(asl=state.asl.first()))

        # this will actually change state.asl, converting (raw_call ...) into (call ...)
        CallConfigurer.process(state)
        # print(state.asl)

        # now we have converted the (raw_call ...) into a normal (call ...) asl 
        # so we can apply fn to the state again with the new asl.
        return fn.apply(state)
         

    @Wrangler.covers(asls_of_type("struct", "interface"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def struct(fn, state: Params) -> TypeClass:
        # ignore the first element because this is the CLRToken storing the name
        for child in state.asl[1:]:
            fn.apply(state.but_with(
                asl=child,
                context=Context(
                    name="struct",
                    type=ContextTypes.block,
                    parent=None)))


    @Wrangler.covers(asls_of_type("cast"))
    @records_typeclass
    @passes_if_critical_exception
    def cast(fn, state: Params) -> TypeClass:
        # (cast (ref name) (type into))
        left_typeclass = fn.apply(state.but_with(asl=state.asl.first()))
        right_typeclass = fn.apply(state.but_with(asl=state.asl.second()))

        result = Validate.castable_types(state, 
            type=left_typeclass, 
            cast_into_type=right_typeclass)
        if result.failed():
            return result.get_failure_type()
        return right_typeclass


    @Wrangler.covers(asls_of_type("impls"))
    @records_typeclass
    @passes_if_critical_exception
    def impls(fn, state: Params) -> TypeClass:
        return state.void_type


    @Wrangler.covers(asls_of_type("mod"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def mod(fn, state: Params) -> TypeClass:
        name = state.asl.first().value
        for child in state.asl[1:]:
            fn.apply(state.but_with(
                asl=child, 
                mod=state.get_module().get_child_module_by_name(name)))


    @Wrangler.covers(asls_of_type("def", "create", ":="))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def fn(fn, state: Params) -> TypeClass:
        # inside the FunctionWrangler, (def ...) and (create ...) asls have been
        # normalized to have the same signature. therefore we can treat them identically
        # here

        parent_context = state.get_parent_context() if state.asl.type == "def" else None
        fn_context = Context(
            name=state.asl.first().value,
            type=ContextTypes.fn,
            parent=parent_context)

        for child in state.asl[1:]:
            fn.apply(state.but_with(asl=child, context=fn_context))


    # we don't need to add/record typeclasses because this is a CLRToken
    @Wrangler.covers(lambda state: isinstance(state.asl, CLRToken))
    @passes_if_critical_exception
    def token_(fn, state: Params) -> TypeClass:
        # TODO: make this nicer
        if state.asl.type in ["str", "int", "bool"]:
            return TypeClassFactory.produce_novel_type(name=state.asl.type, global_mod=state.global_mod)
        else:
            raise Exception(f"unexpected token type of {state.asl.type}")


    # cases for ilet:
    # - inference
    #       let x = 4
    #       (let x 4)
    @Wrangler.covers(asls_of_type("ilet"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def idecls_(fn, state: Params):
        if isinstance(state.asl.first(), CLRList):
            names = [token.value for token in state.asl.first()]
            typeclasses = [fn.apply(state.but_with(asl=child)) for child in state.asl.second()]
        else:
            names = [state.asl.first().value]
            typeclasses = [fn.apply(state.but_with(asl=state.asl.second()))]

        result = Validate.tuple_sizes_match(state, names, typeclasses)
        if result.failed():
            state.critical_exception.set(True)
            return 

        instances = []
        for name, typeclass in zip(names, typeclasses):
            result = Validate.name_is_unbound(state, name)
            if result.failed():
                return 

            if type is state.abort_signal:
                state.critical_exception.set(True)
                return

            instances.append(SeerInstance(
                name, 
                typeclass, 
                state.get_module(), 
                state.asl))

        state.assign_instances(instances)
        for instance in instances:
            state.context.add_instance(instance)


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
    def decls_(fn, state: Params):
        if isinstance(state.asl.first(), CLRList) and state.asl.first().type == "tags":
            names = [token.value for token in state.asl.first()]
            types = [fn.apply(state.but_with(asl=child)) for child in state.asl.second()]

            instances = []
            for name, type in zip(names, types):
                result = Validate.name_is_unbound(state, name)
                if not result.failed():
                    instances.append(
                        state.context.add_instance(SeerInstance(name, type, state.get_module(), state.asl)))
            state.assign_instances(instances)

        elif isinstance(state.asl.first(), CLRList) and state.asl.first().type == ":":
            # validations occur inside the (: ...) asl 
            type = fn.apply(state.but_with(asl=state.asl.first()))
            state.assign_instances(state.but_with(asl=state.asl.first()).get_instances())

    @Wrangler.covers(asls_of_type("type", "type?", "type*"))
    @records_typeclass
    @passes_if_critical_exception
    def _type1(fn, state: Params) -> TypeClass:
        return state.get_module().get_typeclass_by_name(name=state.asl.first().value)


    binary_ops = ["+", "-", "/", "*", "and", "or", "+=", "-=", "*=", "/="] 
    @Wrangler.covers(asls_of_type(*binary_ops))
    @records_typeclass
    @passes_if_critical_exception
    def binary_ops(fn, state: Params) -> TypeClass:
        left_type = fn.apply(state.but_with(asl=state.asl.first()))
        right_type = fn.apply(state.but_with(asl=state.asl.second()))

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type
    
    boolean_return_ops = ["<", ">", "<=", ">=", "==", "!=",]
    @Wrangler.covers(asls_of_type(*boolean_return_ops))
    @records_typeclass
    @passes_if_critical_exception
    def boolean_return_ops_(fn, state: Params) -> TypeClass:
        left_type = fn.apply(state.but_with(asl=state.asl.first()))
        right_type = fn.apply(state.but_with(asl=state.asl.second()))

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return state.get_bool_type()


    @Wrangler.covers(asls_of_type("="))
    @records_typeclass
    @passes_if_critical_exception
    def assigns(fn, state: Params) -> TypeClass:
        left_type = fn.apply(state.but_with(asl=state.asl.first()))
        right_type = fn.apply(state.but_with(asl=state.asl.second()))

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type
        

    @Wrangler.covers(asls_of_type("<-"))
    @records_typeclass
    @passes_if_critical_exception
    def larrow_(fn, state: Params) -> TypeClass:
        left_type = fn.apply(state.but_with(asl=state.asl.first()))
        right_type = fn.apply(state.but_with(asl=state.asl.second()))

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type


    @Wrangler.covers(asls_of_type("ref"))
    @records_typeclass
    @passes_if_critical_exception
    def ref_(fn, state: Params) -> TypeClass:
        result = Validate.instance_exists(state)
        if result.failed():
            return result.get_failure_type()

        instance = result.get_found_instance()
        state.assign_instances(instance)
        return instance.type


    @Wrangler.covers(asls_of_type("args"))
    @records_typeclass
    @passes_if_critical_exception
    def args_(fn, state: Params) -> TypeClass:
        if not state.asl:
            return state.void_type
        type = fn.apply(state.but_with(asl=state.asl.first(), is_ptr=False))
        return type


    @Wrangler.covers(asls_of_type("rets"))
    @records_typeclass
    @passes_if_critical_exception
    def rets_(fn, state: Params) -> TypeClass:
        if not state.asl:
            return state.void_type
        type = fn.apply(state.but_with(asl=state.asl.first(), is_ptr=True))
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
    def _abort_signal(cls, state: Params) -> ValidationResult:
        return ValidationResult(result=False, return_obj=state.abort_signal)

    @classmethod
    def _success(cls, return_obj=None) -> ValidationResult:
        return ValidationResult(result=True, return_obj=return_obj)

    @classmethod
    def equivalent_types(cls, state: Params, type1: TypeClass, type2: TypeClass) -> ValidationResult:
        if any([state.abort_signal in (type1, type2)]):
            return Validate._abort_signal(state) 

        if type1 != type2:
            state.report_exception(Exceptions.TypeMismatch(
                msg=f"'{type1}' != '{type2}'",
                line_number=state.asl.line_number))
            return Validate._abort_signal(state) 
        return Validate._success(type1)


    @classmethod
    def tuple_sizes_match(cls, state: Params, lst1: list, lst2: list):
        if len(lst1) != len(lst2):
            state.report_exception(Exceptions.TupleSizeMismatch(
                msg=f"expected tuple of size {len(lst1)} but got {len(lst2)}",
                line_number=state.asl.line_number))
            return Validate._abort_signal(state)
        return Validate._success()


    @classmethod
    def correct_argument_types(cls, state: Params, name: str, fn_type: TypeClass, given_type: TypeClass) -> ValidationResult:
        if any([state.abort_signal in (fn_type, given_type)]):
            return Validate._abort_signal(state) 

        if fn_type != given_type:
            state.report_exception(Exceptions.TypeMismatch(
                msg=f"function '{name}' takes '{fn_type}' but was given '{given_type}'",
                line_number=state.asl.line_number))
            return Validate._abort_signal(state) 
        return Validate._success(fn_type)


    @classmethod
    def instance_exists(cls, state: Params) -> ValidationResult:
        name = state.asl.first().value
        instance = state.context.get_instance_by_name(name)
        if instance is None:
            state.report_exception(Exceptions.UndefinedVariable(
                msg=f"'{name}' is not defined",
                line_number=state.asl.line_number))
            return Validate._abort_signal(state) 
        return Validate._success(return_obj=instance)


    @classmethod
    def function_instance_exists(cls, state: Params) -> ValidationResult:
        name = state.asl.first().value
        instance = state.context.get_instance_by_name(name)
        if instance is None:
            state.report_exception(Exceptions.UndefinedFunction(
                msg=f"'{name}' is not defined",
                line_number=state.asl.line_number))
            return Validate._abort_signal(state) 
        return Validate._success(return_obj=instance)

    
    @classmethod
    def name_is_unbound(cls, state: Params, name: str) -> ValidationResult:
        if state.context.find_instance(name) is not None:
            state.report_exception(Exceptions.RedefinedIdentifier(
                msg=f"'{name}' is in use",
                line_number=state.asl.line_number))
            return Validate._abort_signal(state)
        return Validate._success(return_obj=None)


    @classmethod
    def has_member_attribute(cls, state: Params, typeclass: TypeClass, attribute_name: str) -> ValidationResult:
        if not typeclass.has_member_attribute_with_name(attribute_name):
            state.report_exception(Exceptions.MissingAttribute(
                f"'{typeclass}' does not have member attribute '{attribute_name}'",
                line_number=state.asl.line_number))
            return Validate._abort_signal(state)
        return Validate._success(return_obj=None)

    
    @classmethod
    def castable_types(cls, state: Params, type: TypeClass, cast_into_type: TypeClass) -> ValidationResult:
        if any([state.abort_signal in (type, cast_into_type)]):
            return Validate._abort_signal(state) 

        if cast_into_type not in type.inherits:
            state.report_exception(Exceptions.CastIncompatibleTypes(
                msg=f"'{type}' cannot be cast into '{cast_into_type}'",
                line_number=state.asl.line_number))
            return Validate._abort_signal(state)
        return Validate._success(return_obj=None)


    @classmethod
    def implementation_is_complete(cls, state: Params, type: TypeClass, inherited_type: TypeClass) -> ValidationResult:
        encountered_exception = False
        for name, required_attribute_type in zip(inherited_type.component_names, inherited_type.components):
            if type.has_member_attribute_with_name(name):
                attribute_type = type.get_member_attribute_by_name(name)
                if attribute_type != required_attribute_type:
                    encountered_exception = True
                    state.report_exception(Exceptions.AttributeMismatch(
                        msg=f"'{type}' has attribute '{name}' of '{attribute_type}', but '{required_attribute_type}' is required to inherit '{inherited_type}'",
                        line_number=state.asl.line_number))
            else:
                encountered_exception = True
                state.report_exception(Exceptions.MissingAttribute(
                    msg=f"'{type}' is missing attribute '{name}' required to inherit '{inherited_type}'",
                    line_number=state.asl.line_number))

        if encountered_exception:
            return Validate._abort_signal(state)
        return Validate._success()
        