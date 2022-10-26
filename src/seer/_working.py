from __future__ import annotations
import re

from alpaca.utils import Visitor
from alpaca.clr import CLRList, CLRToken
from alpaca.concepts import Context, TypeClass, TypeClassFactory

from seer._params import Params
from seer._common import asls_of_type, ContextTypes
from seer._exceptions import Exceptions

from seer._callconfigurer import CallConfigurer
from seer._common import asls_of_type, ContextTypes, SeerInstance, Module
from seer._nodedata import NodeData
from seer._nodetypes import Nodes


class InitializeNodeData(Visitor):
    def apply(self, state: Params) -> None:
        return self._apply([state], [state])

    @Visitor.default
    def default_(fn, state: Params) -> None:
        state.asl.data = NodeData()
        for child in state.get_child_asls():
            fn.apply(state.but_with(asl=child))
        
################################################################################
# this parses the asl and creates the module structure of the program.
class ModuleWrangler2(Visitor):
    def apply(self, state: Params):
        return self._apply([state], [state])

    # set the module inside which a given asl resides.
    def sets_module(f):
        def decorator(fn, state: Params):
            state.assign_module()
            return f(fn, state)
        return decorator

    @Visitor.default
    @sets_module
    def default_(fn, state: Params) -> Module:
        for child in state.get_child_asls():
            fn.apply(state.but_with(asl=child))

    @Visitor.covers(asls_of_type("mod"))
    @sets_module
    def mod_(fn, state: Params) -> Module:
        # create a new module; the name of the module is stored as a CLRToken
        # in the first position of the module asl.
        new_mod = Module(
            name=state.first_child().value,
            type=ContextTypes.mod, 
            parent=state.mod)

        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child, 
                mod=new_mod))


################################################################################
# this parses the asl into a typeclass. certain asls define types. these are:
#   type, interface_type, prod_type, types, fn_type_in, fn_type_out, fn_type, args, rets
#   def, create, struct, interface
class TypeclassParser(Visitor):
    def apply(self, state: Params) -> TypeClass:
        return self._apply([state], [state])

    @Visitor.covers(asls_of_type("type"))
    def type_(fn, state: Params) -> TypeClass:
        # eg. (type int)
        token: CLRToken = state.first_child()
        if token.type != "TAG":
            raise Exception(f"(type ...) must be a TAG attribute, but got {token.type} instead")

        found_type = state.get_module().get_typeclass_by_name(token.value)
        if found_type:
            return found_type
        raise Exception(f"unknown type! {token.value}")

    @Visitor.covers(asls_of_type("interface_type"))
    def interface_type_(fn, state: Params) -> TypeClass:
        # eg. (interface_type name)
        token: CLRToken = state.first_child()
        if token.type != "TAG":
            raise Exception(f"(type ...) must be a TAG attribute, but got {token.type} instead")

        found_type = state.get_module().get_typeclass_by_name(token.value)
        if found_type:
            return found_type
        raise Exception(f"unknown type! {token.value}")

    @Visitor.covers(asls_of_type(":"))
    def colon_(fn, state: Params) -> TypeClass:
        # eg. (: name (type int))
        return fn.apply(state.but_with(asl=state.second_child()))

    @Visitor.covers(asls_of_type("prod_type", "types"))
    def prod_type_(fn, state: Params) -> TypeClass:
        # eg.  (prod_type
        #           (: name1 (type int))
        #           (: name2 (type str)))
        # eg. (types (type int) (type str))
        component_types = [fn.apply(state.but_with(asl=component)) for component in state.asl]
        return TypeClassFactory.produce_tuple_type(components=component_types, global_mod=state.global_mod)

    @Visitor.covers(asls_of_type("fn_type_in", "fn_type_out"))
    def fn_type_out(fn, state: Params) -> TypeClass:
        # eg. (fn_type_in/out (type(s) ...))
        if len(state.asl) == 0:
            return state.get_module().resolve_type(TypeClassFactory.produce_novel_type("void"))
        return fn.apply(state.but_with(asl=state.first_child()))

    @Visitor.covers(asls_of_type("fn_type")) 
    def fn_type_(fn, state: Params) -> TypeClass:
        # eg. (fn_type (fn_type_in ...) (fn_type_out ...))
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(state.but_with(asl=state.first_child())),
            ret=fn.apply(state.but_with(asl=state.second_child())),
            mod=state.global_mod)

    @Visitor.covers(asls_of_type("args", "rets"))
    def args_(fn, state: Params) -> TypeClass:
        # eg. (args (type ...))
        if state.asl:
            return fn.apply(state.but_with(asl=state.first_child()))
        return TypeClassFactory.produce_novel_type("void", state.global_mod)

    @Visitor.covers(asls_of_type("def", "create", ":="))
    def def_(fn, state: Params) -> TypeClass:
        node = Nodes.CommonFunction(state)
        return TypeClassFactory.produce_function_type(
            arg=fn.apply(state.but_with(asl=node.get_args_asl())),
            ret=fn.apply(state.but_with(asl=node.get_rets_asl())),
            mod=state.global_mod)
    
    @Visitor.covers(asls_of_type("struct", "interface"))
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
class TypeDeclarationWrangler(Visitor):
    def apply(self, state: Params) -> None:
        return self._apply([state], [state])

    def adds_typeclass_to_module(f):
        def decorator(fn, state: Params) -> None:
            result: TypeClass = f(fn, state)
            state.get_module().add_typeclass(result)
        return decorator

    @Visitor.covers(asls_of_type("struct"))
    @adds_typeclass_to_module
    def struct_(fn, state: Params) -> TypeClass:
        return TypeClassFactory.produce_proto_struct_type(
            name=Nodes.Struct(state).get_struct_name(),
            mod=state.get_module())

    @Visitor.covers(asls_of_type("interface"))
    @adds_typeclass_to_module
    def interface_(fn, state: Params) -> TypeClass:
        return TypeClassFactory.produce_proto_interface_type(
            name=Nodes.Interface(state).get_interface_name(),
            mod=state.get_module())

    @Visitor.covers(asls_of_type("start", "mod"))
    def general_(fn, state: Params):
        for child in state.get_child_asls():
            fn.apply(state.but_with(asl=child))

    @Visitor.default
    def default_(fn, state: Params):
        # nothing to do by default
        return


################################################################################
# this finalizes a proto_struct/proto_interface into a struct/interface typeclass.
# we need to separate declaration and definition because types may refer back to
# themselves, or to other types which have yet to be defined, but exist in the 
# same module.
class FinalizeProtoInterfaceWrangler(Visitor):
    def apply(self, state: Params) -> None:
        return self._apply([state], [state])

    @Visitor.covers(asls_of_type("start", "mod"))
    def general_(fn, state: Params):
        for child in state.get_child_asls():
            fn.apply(state.but_with(asl=child)) 
 
    @Visitor.covers(asls_of_type("interface"))
    def interface_(fn, state: Params) -> None:
        node = Nodes.Interface(state)
        this_interface_typeclass = node.get_this_typeclass()
        
        # TODO: consider whether or not to allow interfaces to inherit from other interfaces
        this_interface_typeclass.finalize(
            components=[TypeclassParser().apply(state.but_with(asl=child)) for child in node.get_child_attribute_asls()],
            component_names=node.get_child_attribute_names(),
            inherits=[])

    @Visitor.default
    def default_(fn, state: Params) -> None:
        # nothing to do by default
        return


class FinalizeProtoStructWrangler(Visitor):
    def apply(self, state: Params) -> None:
        return self._apply([state], [state])

    @Visitor.covers(asls_of_type("start", "mod"))
    def general_(fn, state: Params):
        for child in state.get_child_asls():
            fn.apply(state.but_with(asl=child)) 
 
    @Visitor.covers(asls_of_type("struct"))
    def struct_(fn, state: Params) -> None:
        node = Nodes.Struct(state)
        this_struct_typeclass = node.get_this_typeclass()

        interfaces: list[TypeClass] = node.get_implemented_interfaces()
        this_struct_typeclass.finalize(
            components=[TypeclassParser().apply(state.but_with(asl=asl)) for asl in node.get_child_attribute_asls()],
            component_names=node.get_child_attribute_names(),
            inherits=interfaces)

        for interface in interfaces:
            Validate.implementation_is_complete(state, this_struct_typeclass, interface)

    @Visitor.default
    def default_(fn, state: Params) -> None:
        # nothing to do by default
        return




################################################################################
# this creates the function instances from (create ...) and (def ) asls. the 
# instances get added to the module so they can be used and called.
class FunctionWrangler(Visitor):
    def apply(self, state: Params):
        if self.debug and isinstance(state.asl, CLRList):
            print("\n"*64)
            print(state.inspect())
            print("\n"*4)
            input()
        return self._apply([state], [state])

    @Visitor.covers(asls_of_type("start", "mod"))
    def start_(fn, state: Params):
        for child in state.get_child_asls():
            fn.apply(state.but_with(asl=child))

    @Visitor.default
    def default_(fn, state: Params) -> None:
        return None

    @Visitor.covers(asls_of_type("struct"))
    def struct_(fn, state: Params) -> None:
        node = Nodes.Struct(state)
        # we need to pass down the struct name because the (create ...) asl will 
        # take on the name of the struct. 
        #
        # for example, a struct named MyStruct will have a constructor method 
        # called via MyStruct(...), so the (create ...)  method inside the 
        # (struct MyStruct ... ) asl needs context as to the struct it is inside.
        fn.apply(state.but_with(
            asl=node.get_create_asl(),
            struct_name=node.get_struct_name()))

    @Visitor.covers(asls_of_type("def"))
    def def_(fn, state: Params):
        mod = state.get_module()
        state.assign_instances(mod.add_instance(
            SeerInstance(
                name=Nodes.Def(state).get_function_name(),
                type=TypeclassParser().apply(state.but_with(mod=mod)),
                context=mod,
                asl=state.asl)))


    @Visitor.covers(asls_of_type("create"))
    def create_(fn, state: Params):
        node = Nodes.Create(state)
        # we need to normalize the create asl before we can use the TypeclassParser
        # on it. see method documentation for why.
        node.normalize(struct_name=state.struct_name)
        mod = state.get_module()

        # the name of the constructor is the same as the struct
        state.assign_instances(mod.add_instance(
            SeerInstance(
                name=state.struct_name,
                type=TypeclassParser().apply(state.but_with(mod=mod)),
                context=mod,
                asl=state.asl,
                is_constructor=True)))

















################################################################################
# this evaluates the flow of typeclasses throughout the asl, and records which 
# typeclass flows up through each asl.
class TypeClassFlowWrangler(Visitor):
    def __init__(self, debug: bool = False):
        super().__init__(debug=debug)
        # self.debug = True

    def apply(self, state: Params) -> TypeClass:
        if self.debug and isinstance(state.asl, CLRList):
            print("\n"*64)
            print(state.inspect())
            print("\n"*4)
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


    @Visitor.covers(asls_of_type("fn_type"))
    @records_typeclass
    @passes_if_critical_exception
    def fn_type_(fn, state: Params) -> TypeClass:
        return TypeclassParser().apply(state)


    no_action = ["start", "return", "seq", "cond", "mod"] 
    @Visitor.covers(asls_of_type(*no_action))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def no_action_(fn, state: Params) -> TypeClass:
        for child in state.get_child_asls():
            fn.apply(state.but_with(asl=child))


    @Visitor.covers(asls_of_type("!"))
    @records_typeclass
    @passes_if_critical_exception
    def not_(fn, state: Params) -> TypeClass:
        return fn.apply(state.but_with(asl=state.first_child()))


    @Visitor.covers(asls_of_type("."))
    @records_typeclass
    @passes_if_critical_exception
    def dot_(fn, state: Params) -> TypeClass:
        parent_typeclass = fn.apply(state.but_with(asl=state.first_child()))
        name = state.second_child().value
        result = Validate.has_member_attribute(state, parent_typeclass, name)
        if result.failed():
            return result.get_failure_type()
        return parent_typeclass.get_member_attribute_by_name(name)


    # TODO: will this work for a::b()?
    @Visitor.covers(asls_of_type("::"))
    @records_typeclass
    @passes_if_critical_exception
    def scope_(fn, state: Params) -> TypeClass:
        next_mod = state.starting_mod.get_child_module_by_name(state.first_child().value)
        return fn.apply(state.but_with(
            asl=state.second_child(),
            starting_mod=next_mod,
            mod=next_mod))


    @Visitor.covers(asls_of_type("tuple", "params", "prod_type"))
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
        return fn.apply(state.but_with(asl=state.first_child()))


    @Visitor.covers(asls_of_type("if"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def if_(fn, state: Params) -> TypeClass:
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child, 
                context=Context(
                    name="if",
                    type=ContextTypes.block,
                    parent=state.get_parent_context())))


    @Visitor.covers(asls_of_type("while"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def while_(fn, state: Params) -> TypeClass:
        fn.apply(state.but_with(
            asl=state.first_child(),
            context=Context(
                name="while", 
                type=ContextTypes.block, 
                parent=state.get_parent_context())))


    @Visitor.covers(asls_of_type(":"))
    @records_typeclass
    @passes_if_critical_exception
    def colon_(fn, state: Params) -> TypeClass:
        node = Nodes.Colon(state)
        names = node.get_names()
        typeclass = fn.apply(state.but_with(asl=node.get_type_asl()))

        instances = []
        for name in names:
            result = Validate.name_is_unbound(state, name)
            if not result.failed():
                instances.append(state.context.add_instance(SeerInstance(
                    name=name, 
                    type=typeclass, 
                    context=state.get_module(), 
                    asl=state.asl, 
                    is_ptr=state.is_ptr)))
        state.assign_instances(instances)
        return typeclass


    @Visitor.covers(asls_of_type("fn"))
    @records_typeclass
    @passes_if_critical_exception
    def fn_(fn, state: Params) -> TypeClass:
        node = Nodes.Fn(state)
        if node.is_print():
            # TODO: handle this better
            return TypeClassFactory.produce_function_type(
                    arg=state.void_type,
                    ret=state.void_type,
                    mod=state.global_mod)
        if node.is_simple():
            result = Validate.function_instance_exists(state)
            if result.failed():
                return result.get_failure_type()

            instance = result.get_found_instance()
            state.assign_instances(instance)
            return instance.type
        else:
            return fn.apply(state.but_with(asl=state.first_child()))


    @Visitor.covers(asls_of_type("call"))
    @records_typeclass
    @passes_if_critical_exception
    def call_(fn, state: Params) -> TypeClass:
        fn_type = fn.apply(state.but_with(asl=state.first_child()))
        if fn_type == state.abort_signal:
            return state.abort_signal

        # still need to type flow through the params passed to the function
        params_type = fn.apply(state.but_with(asl=state.second_child()))

        # TODO: make this nicer. aka. figure out a better way to get the function name
        if state.first_child().type == "fn":
            fn_node = Nodes.Fn(state.but_with(asl=state.first_child()))
            if not fn_node.is_print():
                fn_in_type = fn_type.get_argument_type()
                result = Validate.correct_argument_types(state, state.first_child().first().value, fn_in_type, params_type)
                if result.failed():
                    return result.get_failure_type()

        return fn_type.get_return_type()


    @Visitor.covers(asls_of_type("raw_call"))
    @records_typeclass
    @passes_if_critical_exception
    def raw_call(fn, state: Params) -> TypeClass:
        # e.g. (raw_call (expr ...) (fn name) (state ...))
        # because the first element can be a list itself, we need to apply the 
        # fn over it to get the flowed out type.
        fn.apply(state.but_with(asl=state.first_child()))

        # this will actually change state.asl, converting (raw_call ...) into (call ...)
        CallConfigurer.process(state)
        # print(state.asl)

        # now we have converted the (raw_call ...) into a normal (call ...) asl 
        # so we can apply fn to the state again with the new asl.
        return fn.apply(state)
         

    @Visitor.covers(asls_of_type("struct", "interface"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def struct(fn, state: Params) -> TypeClass:
        # currently structs/interfaces have the same get_child_asls structure
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child,
                context=Context(
                    name="struct",
                    type=ContextTypes.block,
                    parent=None)))


    @Visitor.covers(asls_of_type("cast"))
    @records_typeclass
    @passes_if_critical_exception
    def cast(fn, state: Params) -> TypeClass:
        # (cast (ref name) (type into))
        left_typeclass = fn.apply(state.but_with(asl=state.first_child()))
        right_typeclass = fn.apply(state.but_with(asl=state.second_child()))

        result = Validate.castable_types(state, 
            type=left_typeclass, 
            cast_into_type=right_typeclass)
        if result.failed():
            return result.get_failure_type()
        return right_typeclass


    @Visitor.covers(asls_of_type("impls"))
    @records_typeclass
    @passes_if_critical_exception
    def impls(fn, state: Params) -> TypeClass:
        return state.void_type


    @Visitor.covers(asls_of_type("def", "create", ":="))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def fn(fn, state: Params) -> TypeClass:
        # inside the FunctionWrangler, (def ...) and (create ...) asls have been
        # normalized to have the same signature. therefore we can treat them identically
        # here, more or less.

        parent_context = state.get_parent_context() if state.asl.type == "def" else None
        fn_context = Context(
            name=Nodes.Def(state).get_function_name(),
            type=ContextTypes.fn,
            parent=parent_context)

        for child in state.get_child_asls():
            fn.apply(state.but_with(asl=child, context=fn_context))


    # we don't need to add/record typeclasses because this is a CLRToken
    @Visitor.covers(lambda state: isinstance(state.asl, CLRToken))
    @passes_if_critical_exception
    def token_(fn, state: Params) -> TypeClass:
        # TODO: make this nicer
        if state.asl.type in ["str", "int", "bool"]:
            return TypeClassFactory.produce_novel_type(name=state.asl.type, global_mod=state.global_mod)
        else:
            raise Exception(f"unexpected token type of {state.asl.type}")


    @Visitor.covers(asls_of_type("ilet"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def idecls_(fn, state: Params):
        node = Nodes.Ilet(state)
        names = node.get_names()
        typeclass = fn.apply(state.but_with(asl=state.second_child()))

        if node.assigns_a_tuple():
            typeclasses = typeclass.components
        else:
            typeclasses = [typeclass]

        result = Validate.tuple_sizes_match(state, names, typeclasses)
        if result.failed():
            state.critical_exception.set(True)
            return 

        instances = []
        for name, typeclass in zip(names, typeclasses):
            result = Validate.name_is_unbound(state, name)
            if result.failed():
                return 

            if typeclass is state.abort_signal:
                state.critical_exception.set(True)
                return

            instance = SeerInstance(
                name, 
                typeclass, 
                state.get_module(), 
                state.asl)

            instances.append(instances)
            state.context.add_instance(instance)

        state.assign_instances(instances)


    @Visitor.covers(asls_of_type("val", "var", "mut_val", "mut_var", "let"))
    @records_typeclass
    @passes_if_critical_exception
    @returns_void_type
    def decls_(fn, state: Params):
        # validations occur inside the (: ...) asl 
        fn.apply(state.but_with(asl=state.first_child()))
        state.assign_instances(state.but_with(asl=state.first_child()).get_instances())

    @Visitor.covers(asls_of_type("type", "type?", "type*"))
    @records_typeclass
    @passes_if_critical_exception
    def _type1(fn, state: Params) -> TypeClass:
        return state.get_module().get_typeclass_by_name(name=state.first_child().value)


    binary_ops = ["+", "-", "/", "*", "and", "or", "+=", "-=", "*=", "/="] 
    @Visitor.covers(asls_of_type(*binary_ops))
    @records_typeclass
    @passes_if_critical_exception
    def binary_ops(fn, state: Params) -> TypeClass:
        left_type = fn.apply(state.but_with(asl=state.first_child()))
        right_type = fn.apply(state.but_with(asl=state.second_child()))

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type
    
    boolean_return_ops = ["<", ">", "<=", ">=", "==", "!=",]
    @Visitor.covers(asls_of_type(*boolean_return_ops))
    @records_typeclass
    @passes_if_critical_exception
    def boolean_return_ops_(fn, state: Params) -> TypeClass:
        left_type = fn.apply(state.but_with(asl=state.first_child()))
        right_type = fn.apply(state.but_with(asl=state.second_child()))

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return state.get_bool_type()


    @Visitor.covers(asls_of_type("="))
    @records_typeclass
    @passes_if_critical_exception
    def assigns(fn, state: Params) -> TypeClass:
        left_type = fn.apply(state.but_with(asl=state.first_child()))
        right_type = fn.apply(state.but_with(asl=state.second_child()))

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type
        

    @Visitor.covers(asls_of_type("<-"))
    @records_typeclass
    @passes_if_critical_exception
    def larrow_(fn, state: Params) -> TypeClass:
        left_type = fn.apply(state.but_with(asl=state.first_child()))
        right_type = fn.apply(state.but_with(asl=state.second_child()))

        result = Validate.equivalent_types(state, left_type, right_type)
        if result.failed():
            return result.get_failure_type()
        return left_type


    @Visitor.covers(asls_of_type("ref"))
    @records_typeclass
    @passes_if_critical_exception
    def ref_(fn, state: Params) -> TypeClass:
        result = Validate.instance_exists(state)
        if result.failed():
            return result.get_failure_type()

        instance = result.get_found_instance()
        state.assign_instances(instance)
        return instance.type


    @Visitor.covers(asls_of_type("args"))
    @records_typeclass
    @passes_if_critical_exception
    def args_(fn, state: Params) -> TypeClass:
        if not state.asl:
            return state.void_type
        return fn.apply(state.but_with(asl=state.first_child(), is_ptr=False))


    @Visitor.covers(asls_of_type("rets"))
    @records_typeclass
    @passes_if_critical_exception
    def rets_(fn, state: Params) -> TypeClass:
        if not state.asl:
            return state.void_type
        return fn.apply(state.but_with(asl=state.first_child(), is_ptr=True))


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
        name = state.first_child().value
        instance = state.context.get_instance_by_name(name)
        if instance is None:
            state.report_exception(Exceptions.UndefinedVariable(
                msg=f"'{name}' is not defined",
                line_number=state.asl.line_number))
            return Validate._abort_signal(state) 
        return Validate._success(return_obj=instance)


    @classmethod
    def function_instance_exists(cls, state: Params) -> ValidationResult:
        name = state.first_child().value
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
        