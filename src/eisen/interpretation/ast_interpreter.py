from __future__ import annotations

from alpaca.utils import Visitor

import eisen.adapters as adapters
from eisen.interpretation.obj import Obj
from eisen.interpretation.passer import Passer
from eisen.interpretation.printfunction import PrintFunction
from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.state.astinterpreterstate import AstInterpreterState

class ReturnSignal():
    pass

State = AstInterpreterState

class AstInterpreter(Visitor):
    def run(self, state: State_PostInstanceVisitor):
        self.apply(AstInterpreterState.create_from_state_b(state))
        return state

    def apply(self, state: State) -> list[Obj]:
        # print(state.get_ast())
        return self._route(state.get_ast(), state)

    @Visitor.for_tokens
    def token_(fn, state: State):
        value = state.get_ast().value
        if state.get_ast().type == "int":
            value = int(state.get_ast().value)
        if state.get_ast().type == "bool":
            value = (state.get_ast().value == "true")

        return [Obj(value)]

    @Visitor.for_ast_types("+", "-", "/", "*", "<", "<=", "==", "!=", ">", ">=", "and", "or")
    def binop_(fn, state: State):
        left = fn.apply(state.but_with_first_child())[0]
        right = fn.apply(state.but_with_second_child())[0]
        return [Obj.apply_binary_operation(op=state.get_ast().type, obj1=left, obj2=right)]

    @classmethod
    def _handle_colon_like(cls, state: State):
        node = adapters.Typing(state)
        names = node.get_names()
        objs = [Obj(None, name=name) for name in names]
        for name, obj in zip(names, objs):
            state.objs[name] = obj
        return objs

    @Visitor.for_ast_types("let", ":")
    def let_(fn, state: State):
        return AstInterpreter._handle_colon_like(state)

    @Visitor.for_ast_types("var", "var?")
    def var_(fn, state: State):
        objs = AstInterpreter._handle_colon_like(state)
        for obj in objs:
            obj.is_var = True
        return objs

    @Visitor.for_ast_types("<-")
    def write_(fn, state: State):
        left = fn.apply(state.but_with_first_child())
        right = fn.apply(state.but_with_second_child())
        for l, r in zip(left, right):
            Passer.pass_by_value(state.objs, l, r)
        return []

    @Visitor.for_ast_types("=")
    def eqs_(fn, state: State):
        left = fn.apply(state.but_with_first_child())
        right = fn.apply(state.but_with_second_child())
        for l, r in zip(left, right):
            Passer.handle_assignment(state.objs, l, r)
        return []

    @Visitor.for_ast_types("!")
    def not_(fn, state: State):
        objs = fn.apply(state.but_with_first_child())
        return [Obj(not objs[0].value)]

    @Visitor.for_ast_types("tuple", "curried")
    def tuple(fn, state: State):
        objs = []
        for child in state.ast:
            objs += fn.apply(state.but_with(ast=child))
        return objs

    @Visitor.for_ast_types("+=", "-=", "/=", "*=")
    def asseqs_(fn, state: State):
        node = adapters.CompoundAssignment(state)
        left = fn.apply(state.but_with_first_child())[0]
        right = fn.apply(state.but_with_second_child())[0]
        new_obj = Obj.apply_binary_operation(node.get_arithmetic_operation(), left, right)

        Passer.handle_assignment(state.objs, left, new_obj)
        return []

    @Visitor.for_ast_types("mod", "struct", "interface", "variant")
    def skip_(fn, state: State):
        return []

    @Visitor.for_ast_types("def")
    def def_(fn, state: State):
        node = adapters.Def(state)
        if node.get_function_name() == "main":
            fn.apply(state.but_with(ast=node.get_seq_ast()))
        return []

    @Visitor.for_ast_types("start", "seq")
    def exec_(fn, state: State):
        for child in state.ast:
            result = fn.apply(state.but_with(ast=child))
            if isinstance(result, ReturnSignal):
                return result
        return []

    @Visitor.for_ast_types("ilet", "ivar")
    def ilet_(fn, state: State):
        node = adapters.InferenceAssign(state)
        names = node.get_names()
        values = fn.apply(state.but_with_second_child())

        is_var = state.get_ast().type == "ivar"
        for name, value in zip(names, values):
            if is_var:
                Passer.add_var(state.objs, name, value)
            else:
                Passer.add_let(state.objs, name, value)
        return []

    @Visitor.for_ast_types("cast")
    def cast_(fn, state: State):
        return fn.apply(state.but_with_first_child())

    @Visitor.for_ast_types("return")
    def return_(fn, state: State):
        return ReturnSignal()

    @classmethod
    def create_objs_for_function_arguments(cls, node: adapters.Call) -> list[Obj]:
        new_objs = []
        for name, restriction in zip(node.get_param_names(), node.get_function_argument_type().get_restrictions()):
            # create new_obj so changes inside the function don't affect the existing obj
            new_objs.append(Obj(None, name=name, is_var=restriction.is_var()))
        return new_objs

    @Visitor.for_ast_types("call", "is_call")
    def call_(fn, state: State):
        node = adapters.Call(state)
        fnobj: Obj = fn.apply(state.but_with_first_child())[0]

        if node.is_print():
            args = [fn.apply(state.but_with(ast=ast))[0] for ast in state.get_ast().second()]
            redirect_to = True if state.print_to_watcher else None
            state.watcher.txt += PrintFunction.emulate(redirect_to, *args)
            return []

        # enter a new object context
        fn_objs = {}

        # evaluate the parameters and add them as new objects inside the new function context
        param_objs_outside_of_fn = fnobj.curried_params + [fn.apply(node.state.but_with(ast=param))[0] for param in node.get_params()]
        new_objs = []
        for name, restriction in zip(fnobj.param_names, fnobj.param_restrictions):
            # create new_obj so changes inside the function don't affect the existing obj
            new_objs.append(Obj(None, name=name, is_var=restriction.is_var()))

        for inside, outside in zip(new_objs, param_objs_outside_of_fn):
            # add inside objects to the new fn_objs context
            fn_objs[inside.name] = inside
            Passer.handle_assignment(fn_objs, inside, outside)

        # add return values to the new context
        for name, restriction in zip(fnobj.return_names, fnobj.return_restrictions):
            # use a dict in case we are creating a new struct
            obj = Obj({}, name=name, is_var=restriction.is_var())
            fn_objs[name] = obj

        # call the function by invoking the seq of the ast_defining_the_function
        fn.apply(state.but_with(
            ast=adapters.Def(state.but_with(ast=fnobj.ast)).get_seq_ast(),
            objs=fn_objs))

        # get the actual return values
        return_values = []
        for name in fnobj.return_names:
            return_values.append(fn_objs[name])
        return return_values

    @Visitor.for_ast_types("::")
    def modscope_(fn, state: State):
        # TODO: make this work for module variables
        return fn.fn_(fn, state)

    @Visitor.for_ast_types("fn")
    def fn_(fn, state: State):
        # this is for functions apparently
        instance = state.get_instances()[0]
        return [Obj(
            None,
            "anon",
            False,
            instance.ast,
            adapters.Def(state.but_with(ast=instance.ast)).get_arg_names(),
            adapters.Def(state.but_with(ast=instance.ast)).get_ret_names(),
            instance.type.get_argument_type().get_restrictions(),
            instance.type.get_return_type().get_restrictions())]

    @Visitor.for_ast_types("ref")
    def ref_(fn, state: State):
        name = adapters.Ref(state).get_name()
        local_obj = state.objs.get(name, None)
        if local_obj is not None:
            return [local_obj]

        # this is for functions apparently
        instance = state.get_instances()[0]
        return [Obj(instance)]

    @Visitor.for_ast_types(".")
    def dot_(fn, state: State):
        obj = fn.apply(state.but_with_first_child())[0]
        return [obj.get(adapters.Scope(state).get_attribute_name())]

    @Visitor.for_ast_types("type")
    def type_(fn, state: State):
        return Obj(None)

    @Visitor.for_ast_types("while")
    def while_(fn, state: State):
        result = fn._handle_cond(state.but_with_first_child())
        while result:
            result = fn._handle_cond(state.but_with_first_child())
        return []

    @Visitor.for_ast_types("curry_call")
    def curried_(fn, state: State):
        node = adapters.CurriedCall(state)
        fn_obj = Obj(None)
        fn_obj.copy(fn.apply(state.but_with_first_child())[0])
        params = fn.apply(state.but_with(ast=node.get_params_ast()))
        fn_obj.curried_params += params
        return [fn_obj]

    @Visitor.for_ast_types("if")
    def if_(fn, state: State):
        for child in state.ast:
            if child.type == "cond":
                result = fn._handle_cond(state.but_with(ast=child))
                if result:
                    break
                continue
            # this will catch the else stored as (seq ...)
            result = fn.apply(state.but_with(ast=child))
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
