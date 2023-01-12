from __future__ import annotations

from alpaca.utils import Visitor

from eisen.common.state import State
from eisen.validation.nodetypes import Nodes
from eisen.interpretation.obj import Obj
from eisen.interpretation.passer import Passer
from eisen.interpretation.printfunction import PrintFunction

class ReturnSignal():
    pass

class AstInterpreter(Visitor):
    def __init__(self, redirect_output=False):
        super().__init__()
        self.stdout = "";
        self.redirect_output = redirect_output

    def apply(self, state: State) -> list[Obj]:
        # print(state.asl)
        return self._route(state.asl, state)

    @Visitor.for_tokens
    def token_(fn, state: State):
        value = state.asl.value
        if state.asl.type == "int":
            value = int(state.asl.value)
        if state.asl.type == "bool":
            value = (state.asl.value == "true")

        return [Obj(value)]

    @Visitor.for_asls("+", "-", "/", "*", "<", "<=", "==", "!=", ">", ">=", "and", "or")
    def binop_(fn, state: State):
        left = fn.apply(state.but_with_first_child())[0]
        right = fn.apply(state.but_with_second_child())[0]
        return [Obj.apply_binary_operation(op=state.get_asl().type, obj1=left, obj2=right)]

    @Visitor.for_asls("let")
    def let_(fn, state: State):
        return fn.apply(state.but_with_first_child())

    @Visitor.for_asls("var", "var?")
    def var_(fn, state: State):
        objs = fn.apply(state.but_with_first_child())
        for obj in objs:
            obj.is_var = True
        return objs

    @Visitor.for_asls(":")
    def colon_(fn, state: State):
        node = Nodes.Colon(state)
        names = node.get_names()
        objs = [Obj(None, name=name) for name in names]
        for name, obj in zip(names, objs):
            state.objs[name] = obj
        return objs

    @Visitor.for_asls("<-")
    def write_(fn, state: State):
        left = fn.apply(state.but_with_first_child())
        right = fn.apply(state.but_with_second_child())
        for l, r in zip(left, right):
            Passer.pass_by_value(state.objs, l, r)
        return []

    @Visitor.for_asls("=")
    def eqs_(fn, state: State):
        left = fn.apply(state.but_with_first_child())
        right = fn.apply(state.but_with_second_child())
        for l, r in zip(left, right):
            Passer.handle_assignment(state.objs, l, r)
        return []

    @Visitor.for_asls("!")
    def not_(fn, state: State):
        objs = fn.apply(state.but_with_first_child())
        return [Obj(not objs[0].value)]

    @Visitor.for_asls("tuple")
    def tuple(fn, state: State):
        objs = []
        for child in state.asl:
            objs += fn.apply(state.but_with(asl=child))
        return objs

    @Visitor.for_asls("+=", "-=", "/=", "*=")
    def asseqs_(fn, state: State):
        node = Nodes.CompoundAssignment(state)
        name = node.get_name()

        left = state.objs[name]
        right = fn.apply(state.but_with_second_child())[0]
        new_obj = Obj.apply_binary_operation(node.get_arithmetic_operation(), left, right)

        Passer.handle_assignment(state.objs, left, new_obj)
        return []

    @Visitor.for_asls("mod", "struct", "interface", "variant")
    def skip_(fn, state: State):
        return []

    @Visitor.for_asls("def")
    def def_(fn, state: State):
        node = Nodes.Def(state)
        if node.get_function_name() == "main":
            fn.apply(state.but_with(asl=node.get_seq_asl()))
        return []

    @Visitor.for_asls("start", "seq")
    def exec_(fn, state: State):
        for child in state.asl:
            result = fn.apply(state.but_with(asl=child))
            if isinstance(result, ReturnSignal):
                return result
        return []

    @Visitor.for_asls("ilet", "ivar")
    def ilet_(fn, state: State):
        node = Nodes.IletIvar(state)
        names = node.get_names()
        values = fn.apply(state.but_with_second_child())

        is_var = state.asl.type == "ivar"
        for name, value in zip(names, values):
            if is_var:
                Passer.add_var(state.objs, name, value)
            else:
                Passer.add_let(state.objs, name, value)
        return []

    @Visitor.for_asls("cast")
    def cast_(fn, state: State):
        return fn.apply(state.but_with_first_child())

    @Visitor.for_asls("return")
    def return_(fn, state: State):
        return ReturnSignal()

    @classmethod
    def create_objs_for_function_arguments(cls, node: Nodes.Call) -> list[Obj]:
        new_objs = []
        for name, restriction in zip(node.get_param_names(), node.get_function_argument_type().get_restrictions()):
            # create new_obj so changes inside the function don't affect the existing obj
            new_objs.append(Obj(None, name=name, is_var=restriction.is_var()))
        return new_objs

    @Visitor.for_asls("call")
    def call_(fn, state: State):
        node = Nodes.Call(state)

        if node.is_print():
            args = [fn.apply(state.but_with(asl=asl))[0] for asl in state.asl.second()]
            redirect_to = True if fn.redirect_output else None
            fn.stdout += PrintFunction.emulate(redirect_to, *args)
            return []

        # enter a new object context
        fn_objs = {}

        # evaluate the parameters and add them as new objects inside the new function context
        param_objs_outside_of_fn = [fn.apply(node.state.but_with(asl=param))[0] for param in node.get_params()]
        param_objs_inside_of_fn = AstInterpreter.create_objs_for_function_arguments(node)
        for inside, outside in zip(param_objs_inside_of_fn, param_objs_outside_of_fn):
            # add inside objects to the new fn_objs context
            fn_objs[inside.name] = inside
            Passer.handle_assignment(fn_objs, inside, outside)

        # add return values to the new context
        return_names = node.get_return_names()
        for name, restriction in zip(return_names, node.get_function_return_restrictions()):
            # use a dict in case we are creating a new struct
            obj = Obj({}, name=name, is_var=restriction.is_var())
            fn_objs[name] = obj

        # call the function by invoking the seq of the asl_defining_the_function
        fn.apply(state.but_with(
            asl=Nodes.Def(state.but_with(asl=node.get_asl_defining_the_function())).get_seq_asl(),
            objs=fn_objs))

        # get the actual return values
        return_values = []
        for name in return_names:
            return_values.append(fn_objs[name])
        return return_values

    @Visitor.for_asls("ref")
    def ref_(fn, state: State):
        name = Nodes.Ref(state).get_name()
        local_obj = state.objs.get(name, None)
        if local_obj is not None:
            return [local_obj]

        # this is for functions apparently
        instance = state.get_instances()[0]
        return [Obj(instance)]

    @Visitor.for_asls(".")
    def dot_(fn, state: State):
        obj = fn.apply(state.but_with_first_child())[0]
        return [obj.get(Nodes.Scope(state).get_attribute_name())]

    @Visitor.for_asls("type")
    def type_(fn, state: State):
        return Obj(None)

    @Visitor.for_asls("while")
    def while_(fn, state: State):
        result = fn._handle_cond(state.but_with_first_child())
        while result:
            result = fn._handle_cond(state.but_with_first_child())
        return []

    @Visitor.for_asls("if")
    def if_(fn, state: State):
        for child in state.asl:
            if child.type == "cond":
                result = fn._handle_cond(state.but_with(asl=child))
                if result:
                    break
                continue
            # this will catch the else stored as (seq ...)
            result = fn.apply(state.but_with(asl=child))
        if isinstance(result, ReturnSignal):
            return ReturnSignal()
        return []

    def _handle_cond(fn, state: State):
        condition = fn.apply(state.but_with_first_child())[0]
        if condition.value:
            result = fn.apply(state.but_with_second_child())
            if isinstance(result, ReturnSignal):
                return result
            return True
        return False
