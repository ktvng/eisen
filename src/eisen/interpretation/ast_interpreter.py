from __future__ import annotations

from alpaca.clr import CLRToken, CLRList
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

    @Visitor.for_asls("var")
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

    @Visitor.for_asls("mod", "struct", "interface")
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

    @Visitor.for_asls("call")
    def call_(fn, state: State):
        node = Nodes.Call(state)
        
        # get the asl of type (fn <name>)
        fn_asl = fn._unravel_scoping(state.asl.first())

        if isinstance(fn_asl.first(), CLRToken) and fn_asl.first().value == "print":
            args = [fn.apply(state.but_with(asl=asl))[0] for asl in state.asl.second()]
            if fn.redirect_output:
                fn.stdout += PrintFunction.emulate(fn.stdout, *args)
            else:
                PrintFunction.emulate(None, *args)
            
            return []

        # this case is if we are looking pu the function inside a struct
        if fn_asl.first().type == ".":
            obj = fn.apply(state.but_with(asl=fn_asl.first()))[0]
            fn_instance = obj.value
        # this case is if we are looking up a local function or a function in the closure
        else:
            found_fn = state.objs.get(fn_asl.first().value, None)
            if found_fn:
                fn_instance = found_fn.value
            else:
                # we need to drop into the original CLR which defines the original function
                # in order to get the return types.
                fn_instance = state.but_with(asl=fn_asl).get_instances()[0]

        asl_defining_the_function = fn_instance.asl

        # enter a new object context
        fn_objs = {}

        # add parameters to the context; creates a new object so we don't override the 
        # existing object when we change it in the function.
        param_names = fn._get_param_names(asl_defining_the_function)
        restrictions  = (state.but_with(asl=state.first_child())
            .get_node_data()
            .returned_type
            .get_argument_type()
            .get_restrictions())

        for name, param, restriction in zip(param_names, state.asl.second(), restrictions):
            obj = fn.apply(state.but_with(asl=param))[0]
            new_obj = Obj(None, name=name, is_var=restriction.is_var())
            fn_objs[name] = new_obj
            Passer.handle_assignment(fn_objs, new_obj, obj)

        # add return values to the context
        returned_type = node.get_function_return_type()
        restrictions = returned_type.get_restrictions()
        return_names = fn._get_return_names(asl_defining_the_function)
        for name, r in zip(return_names, restrictions):
            is_var =  r.is_var()
            if asl_defining_the_function.type == "create":
                obj = Obj({}, name=name, is_var=is_var)
            else:
                obj = Obj(None, name=name, is_var=is_var)

            fn_objs[name] = obj

        # call the function by invoking the seq of the asl_defining_the_function
        fn.apply(state.but_with(
            asl=asl_defining_the_function[-1],
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

    # TODO: make this shared 
    def _unravel_scoping(self, asl: CLRList) -> CLRList:
        if asl.type != "::" and asl.type != "disjoint_fn" and asl.type != "fn":
            raise Exception(f"unexpected asl type of {asl.type}")
        
        if asl.type == "disjoint_fn" or asl.type == "fn":
            return asl
        return self._unravel_scoping(asl=asl.second())

    def _get_param_names(self, asl: CLRList) -> list[str]:
        # fn -> args -> first arg
        if not asl.second():
            return []

        first_arg = asl.second().first()
        if first_arg.type == "prod_type":
            return [colon.first().value for colon in first_arg]
        else:
            return [first_arg.first().value]

    def _get_return_names(self, asl: CLRList) -> list[str]:
        # fn -> args -> first arg
        if not asl.third():
            return []

        first_arg = asl.third().first()
        if first_arg.type == "prod_type":
            return [colon.first().value for colon in first_arg]
        else:
            return [first_arg.first().value]
