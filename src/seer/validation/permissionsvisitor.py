from __future__ import annotations

from alpaca.utils import Visitor
from alpaca.clr import CLRList, CLRToken
from alpaca.concepts import Context

from seer.common import asls_of_type, ContextTypes, binary_ops, boolean_return_ops
from seer.common.params import Params
from seer.common.restriction import Restriction

from seer.validation.nodetypes import Nodes
from seer.validation.validate import Validate

class PermissionsVisitor(Visitor):
    def apply(self, state: Params) -> list[Restriction]:
        if self.debug and isinstance(state.asl, CLRList):
            print("\n"*64)
            print(state.inspect())
            print("\n"*4)
            input()
        return self._apply([state], [state])

    @Visitor.covers(asls_of_type("def", "create"))
    def defs_(fn, state: Params) -> list[Restriction]:
        node = Nodes.CommonFunction(state)
        fn_context = Context(
            name=node.get_name(),
            type=ContextTypes.fn,
            parent=None)

        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child,
                context=fn_context))
        return []

    @Visitor.covers(asls_of_type("args", "rets", "prod_type"))
    def args_(fn, state: Params) -> list[Restriction]:
        for child in state.get_child_asls():
            restrictions = fn.apply(state.but_with(asl=child))
            for restriction in restrictions:
                restriction.mark_as_initialized()
        return []

    @Visitor.covers(asls_of_type(":"))
    def colon_(fn, state: Params) -> list[Restriction]:
        instance = state.get_instances()[0]
        if instance.type.restriction is not None and instance.type.restriction.is_var():
            restriction = Restriction.create_var()
        elif instance.type.is_novel():
            # pass primitives by value
            restriction = Restriction.for_let_of_novel_type()
        else:
            # pass everything else by reference (variable)
            restriction = Restriction.create_var()

        state.add_restriction(instance.name, restriction)
        return [restriction]

    @Visitor.covers(asls_of_type("interface"))
    def none_(fn, state: Params) -> list[Restriction]:
        return []
 
    @Visitor.covers(asls_of_type("struct"))
    def struct_(fn, state: Params) -> list[Restriction]:
        node = Nodes.Struct(state)
        if node.has_create_asl():
            fn.apply(state.but_with(asl=node.get_create_asl()))
        return []

    @Visitor.covers(asls_of_type("if"))
    def if_(fn, state: Params) -> list[Restriction]:
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child, 
                context=Context(
                    name="if",
                    type=ContextTypes.block,
                    parent=state.get_parent_context())))
        return []


    @Visitor.covers(asls_of_type("while"))
    def while_(fn, state: Params) -> list[Restriction]:
        fn.apply(state.but_with(
            asl=state.first_child(),
            context=Context(
                name="while", 
                type=ContextTypes.block, 
                parent=state.get_parent_context())))
        return []


    @Visitor.covers(asls_of_type("start", "mod", "seq", "cond"))
    def seq_(fn, state: Params) -> Restriction:
        for child in state.get_child_asls():
            fn.apply(state.but_with(
                asl=child,
                mod=state.get_node_data().module))
        return []

    @Visitor.covers(asls_of_type("ref"))
    def ref_(fn, state: Params) -> list[Restriction]:
        node = Nodes.Ref(state)
        return [state.get_restriction_for(node.get_name())]

    @Visitor.covers(asls_of_type("let"))
    def let_(fn, state: Params) -> list[Restriction]:
        for instance in state.get_instances():
            if instance.type.is_novel():
                restriction = Restriction.for_let_of_novel_type()
            else:
                restriction = Restriction.create_let()
            state.add_restriction(instance.name, restriction)
        return []


    @Visitor.covers(asls_of_type("ilet"))
    def ilet_(fn, state: Params) -> list[Restriction]:
        right_restrictions = fn.apply(state.but_with(asl=state.second_child()))
        for instance, right_restriction in zip(state.get_instances(), right_restrictions):
            if instance.type.is_novel():
                left_restriction = Restriction.for_let_of_novel_type()
            else:
                left_restriction = Restriction.create_let()

            state.add_restriction(instance.name, left_restriction)
            Validate.assignment_restrictions_met(state, left_restriction, right_restriction)
            left_restriction.mark_as_initialized()
        return []


    @Visitor.covers(asls_of_type("ivar"))
    def ivar_(fn, state: Params) -> list[Restriction]:
        right_restrictions = fn.apply(state.but_with(asl=state.second_child()))
        for instance, right_restriction in zip(state.get_instances(), right_restrictions):
            left_restriction = Restriction.create_var()

            state.add_restriction(instance.name, left_restriction)
            Validate.assignment_restrictions_met(state, left_restriction, right_restriction)
            left_restriction.mark_as_initialized()
        return []


    
    @Visitor.covers(asls_of_type("var"))
    def var_(fn, state: Params) -> list[Restriction]:
        for instance in state.get_instances():
            state.add_restriction(instance.name, Restriction.create_var())
        return []


    @Visitor.covers(asls_of_type("tuple", "params"))
    def tuple_(fn, state: Params) -> list[Restriction]:
        restrictions = []
        for child in state.get_all_children():
            restrictions += fn.apply(state.but_with(asl=child))
        return restrictions
    
    @Visitor.covers(asls_of_type("="))
    def equals_(fn, state: Params) -> Restriction:
        node = Nodes.Assignment(state)
        left_restrictions = fn.apply(state.but_with(asl=state.first_child()))
        right_restrictions = fn.apply(state.but_with(asl=state.second_child()))

        for left_restriction, right_restriction in zip(left_restrictions, right_restrictions):
            Validate.assignment_restrictions_met(state, left_restriction, right_restriction)
            # must mark as initialized after we check critera, otherwise checks may fail
            # if this is where the first initialization occurs
            left_restriction.mark_as_initialized()
        return []

    @Visitor.covers(asls_of_type("."))
    def dot_(fn, state: Params) -> Restriction:
        # TODO: figure this out
        return [Restriction.create_none()]
        node = Nodes.Scope(state)
        # if we are accessing a primitive attribute, then remove it's restriction.
        if state.get_returned_typeclass().is_novel():
            return Restriction.none
        return fn.apply(state.but_with(asl=node.get_asl_defining_restriction()))

    @Visitor.covers(asls_of_type("call"))
    def call_(fn, state: Params) -> list[Restriction]:
        node = Nodes.Call(state)

        if node.is_print():
            return [Restriction.create_none()]


        argument_converted_restrictions = []
        # handle argument restrictions
        argument_typeclass = node.get_argument_type()
        restrictions = argument_typeclass.get_restrictions()
        unpacked_argument_typeclasses = [argument_typeclass] if not argument_typeclass.is_tuple() else argument_typeclass.components
        for r, tc in zip(restrictions, unpacked_argument_typeclasses):
            if r.is_let() and tc.is_novel():
                argument_converted_restrictions.append(Restriction.for_let_of_novel_type())
            elif r.is_let():
                argument_converted_restrictions.append(Restriction.create_var(is_init=False))
            elif r.is_var():
                argument_converted_restrictions.append(Restriction.create_var(is_init=False))
        
        param_restrictions = fn.apply(state.but_with(asl=node.get_params_asl()))
        for left, right in zip(argument_converted_restrictions, param_restrictions):
            Validate.parameter_assignment_restrictions_met(state, left, right)
 

        # handle returned restrictions
        returned_typeclass = node.get_function_return_type()
        unpacked_return_typeclasses = [returned_typeclass] if not returned_typeclass.is_tuple() else returned_typeclass.components
        restrictions = returned_typeclass.get_restrictions()
        converted_restrictions = []
        for restriction, tc in zip(restrictions, unpacked_return_typeclasses):
            if restriction.is_let() and tc.is_novel():
                converted_restrictions.append(Restriction.for_let_of_novel_type())
            elif restriction.is_let():
                converted_restrictions.append(Restriction.create_let(is_init=False))
            elif restriction.is_var():
                converted_restrictions.append(Restriction.create_var(is_init=False))
        return converted_restrictions

    @Visitor.covers(asls_of_type("cast"))
    def cast_(fn, state: Params) -> list[Restriction]:
        # restriction is carried over from the first child
        return fn.apply(state.but_with(asl=state.first_child()))

    @Visitor.covers(asls_of_type(*(binary_ops + boolean_return_ops), "!"))
    def ops_(fn, state: Params) -> list[Restriction]:
        return [Restriction.create_literal()]

    @Visitor.covers(lambda state: isinstance(state.asl, CLRToken))
    def token_(fn, state: Params) -> list[Restriction]:
        return [Restriction.create_literal()]

    
    @Visitor.default
    def default_(fn, state: Params) -> Restriction:
        print("UNHANDLED", state.asl)
        return [Restriction.create_none()]













