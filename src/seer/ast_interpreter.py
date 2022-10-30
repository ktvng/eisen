from __future__ import annotations

from typing import Any, Callable
import re

from alpaca.clr import CLRToken, CLRList
from alpaca.utils import Visitor
from alpaca.concepts import Restriction2

from seer.common import asls_of_type
from seer.common.params import Params
from seer.validation.nodetypes import Nodes

lambda_map = {
    "+": lambda x, y: x + y,
    "-": lambda x, y: x - y,
    "/": lambda x, y: x // y,
    "*": lambda x, y: x * y,
    "<": lambda x, y: x < y,
    "<=": lambda x, y: x <= y,
    "==": lambda x, y: x == y,
    "!=": lambda x, y: x != y,
    ">": lambda x, y: x > y,
    ">=": lambda x, y: x >= y,
    "or": lambda x, y: x or y,
    "and": lambda x, y: x and y,
}

class Primitive:
    def __init__(self, value: Any):
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

class Obj:
    def __init__(self, value: Any, name: str = "anon", is_var: bool = False):
        self.value = value
        self.name = name
        self.is_var = is_var

    @classmethod
    def apply_binary_operation(cls, op: str, obj1: Obj, obj2: Obj):
        if op in lambda_map:
            return Obj(lambda_map[op](obj1.value, obj2.value))
        else:
            raise Exception(f"unhandled binary operation {op}")

    def __str__(self) -> str:
        return str(self.value)

    def get_debug_str(self) -> str:
        return f"{self.name}:{self.value}"

    def get(self, key: str): 
        if not isinstance(self.value, dict):
            raise Exception(f"Interpreter object must be a dict (for struct), but got {type(self.value)}")
        found = self.value.get(key, None)
        if found is None:
            new_obj = Obj(None)
            self.value[key] = new_obj
            found = new_obj
        return found


class Passer():
    @classmethod
    def pass_by_value(cls, context: dict, l: Obj, r: Obj):
        l.value = r.value

    @classmethod
    def pass_by_reference(cls, context: dict, l: Obj, r: Obj):
        context[l.name] = r

    @classmethod
    def handle_assignment(cls, context: dict, l: Obj, r: Obj):
        if l.is_var:
            cls.pass_by_reference(context, l, r)
        else:
            cls.pass_by_value(context, l, r)

    @classmethod
    def add_var(cls, context: dict, name: str, val: Obj):
        context[name] = val
    
    @classmethod
    def add_let(cls, context: dict, name: str, val: Obj):
        l = Obj(None, name=name)
        context[name] = l
        Passer.pass_by_value(context, l, val)



class ReturnSignal():
    pass


class AstInterpreter(Visitor):
    def __init__(self, redirect_output=False):
        super().__init__()
        self.stdout = "";
        self.redirect_output = redirect_output

    def apply(self, state: Params) -> list[Obj]:
        # print(state.asl)
        return self._route(state.asl, state)

    @Visitor.for_tokens
    def token_(fn, state: Params):
        value = state.asl.value
        if state.asl.type == "int":
            value = int(state.asl.value)
        if state.asl.type == "bool":
            value = state.asl.value == "true"

        return [Obj(value)]

    @Visitor.for_asls("+", "-", "/", "*", "<", "<=", "==", "!=", ">", ">=", "and", "or")
    def binop_(fn, state: Params):
        op = state.asl.type
        left = fn.apply(state.but_with(asl=state.asl.first()))[0]
        right = fn.apply(state.but_with(asl=state.asl.second()))[0]
        return [Obj.apply_binary_operation(op, left, right)]

    @Visitor.for_asls("let")
    def let_(fn, state: Params):
        return fn.apply(state.but_with(asl=state.asl.first()))

    @Visitor.for_asls("var")
    def var_(fn, state: Params):
        objs = fn.apply(state.but_with(asl=state.asl.first()))
        for obj in objs:
            obj.is_var = True
        return objs
    

    @Visitor.for_asls(":")
    def colon_(fn, state: Params):
        if isinstance(state.asl.first(), CLRToken):
            names = [state.asl.first().value]
        else:
            names = [tag.value for tag in state.asl.first()]

        if state.asl.second().type == "type":
            # this is the case (let (: tags x y z) (type int))
            # we create a new object for each name
            objs = [Obj(None, name=name) for name in names]
        else:
            objs = fn.apply(state.but_with(asl=state.asl.second()))

        for name, obj in zip(names, objs):
            state.objs[name] = obj
        return objs


    @Visitor.for_asls("<-")
    def write_(fn, state: Params):
        left = fn.apply(state.but_with(asl=state.asl.first()))
        right = fn.apply(state.but_with(asl=state.asl.second()))
        for l, r in zip(left, right):
            Passer.pass_by_value(state.objs, l, r)
        return [] 

    @Visitor.for_asls("=")
    def eqs_(fn, state: Params):
        left = fn.apply(state.but_with(asl=state.asl.first()))
        right = fn.apply(state.but_with(asl=state.asl.second()))
        for l, r in zip(left, right):
            Passer.handle_assignment(state.objs, l, r)
        return []

    @Visitor.for_asls("!")
    def not_(fn, state: Params):
        objs = fn.apply(state.but_with(asl=state.asl.first()))
        x = [Obj(not objs[0].value)]
        return x

    @Visitor.for_asls("tuple")
    def tuple(fn, state: Params):
        objs = []
        for child in state.asl:
            objs += fn.apply(state.but_with(asl=child))
        return objs

    @Visitor.for_asls("+=", "-=", "/=", "*=")
    def asseqs_(fn, state: Params):
        # because (= (ref name) ...)
        name = state.asl.first().first().value

        left = state.objs[name]
        right = fn.apply(state.but_with(asl=state.asl.second()))[0]

        new_obj = Obj.apply_binary_operation(state.asl.type[0], left, right) 
        Passer.handle_assignment(state.objs, left, new_obj)
        return []

    @Visitor.for_asls("mod", "struct", "interface")
    def skip_(fn, state: Params):
        return []

    @Visitor.for_asls("def")
    def def_(fn, state: Params):
        fn_name = state.asl.first().value
        if fn_name == "main":
            # apply to the seq
            fn.apply(state.but_with(asl=state.asl[-1]))
        return []

    @Visitor.for_asls("start", "seq")
    def exec_(fn, state: Params):
        for child in state.asl:
            result = fn.apply(state.but_with(asl=child))
            if isinstance(result, ReturnSignal):
                return result
        return []

    @Visitor.for_asls("ilet", "ivar")
    def ilet_(fn, state: Params):
        is_var = state.asl.type == "ivar"
        # this is the case for (ilet (tags x y) (...))
        if isinstance(state.asl.first(), CLRList):
            names = [token.value for token in state.asl.first()]
            # this handles if (...) is a (call ...)
            if state.asl.second().type == "call":
                values = fn.apply(state.but_with(asl=state.asl.second()))

            # this handles if (...) is a (tuple ...)
            else:
                values = [fn.apply(state.but_with(asl=child))[0] for child in state.asl.second()]
        else:
            names = [state.asl.first().value]
            values = [fn.apply(state.but_with(asl=state.asl.second()))[0]]
 
        for name, value in zip(names, values):
            if is_var:
                Passer.add_var(state.objs, name, value)
            else:
                Passer.add_let(state.objs, name, value)
        return []

    @Visitor.for_asls("cast")
    def cast_(fn, state: Params):
        return fn.apply(state.but_with(asl=state.asl.first()))

    @Visitor.for_asls("return")
    def return_(fn, state: Params):
        return ReturnSignal()

    @Visitor.for_asls("call")
    def call_(fn, state: Params):
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
            .returned_typeclass
            .get_argument_type()
            .get_restrictions())

        for name, param, restriction in zip(param_names, state.asl.second(), restrictions):
            obj = fn.apply(state.but_with(asl=param))[0]
            new_obj = Obj(None, name=name, is_var=restriction.is_var())
            fn_objs[name] = new_obj
            Passer.handle_assignment(fn_objs, new_obj, obj)

        # add return values to the context
        returned_typeclass = node.get_function_return_type()
        restrictions = returned_typeclass.get_restrictions()
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
    def ref_(fn, state: Params):
        name = state.asl.first().value
        local_obj = state.objs.get(name, None)
        if local_obj is not None:
            return [local_obj]

        # this is for functions apparently
        instance = state.get_instances()[0]
        return [Obj(instance)]
        

    @Visitor.for_asls(".")
    def dot_(fn, state: Params):
        obj = fn.apply(state.but_with(asl=state.asl.first()))[0]
        return [obj.get(state.asl.second().value)]

    @Visitor.for_asls("type")
    def type_(fn, state: Params):
        return Obj(None)

    @Visitor.for_asls("while")
    def while_(fn, state: Params):
        result = fn._handle_cond(state.but_with(asl=state.asl.first()))
        while result:
            result = fn._handle_cond(state.but_with(asl=state.asl.first()))
        return []

    @Visitor.for_asls("if")
    def if_(fn, state: Params):
        for child in state.asl:
            if child.type == "cond":
                was_true = fn._handle_cond(state.but_with(asl=child))
                if isinstance(was_true, ReturnSignal):
                    return ReturnSignal()
                if was_true:
                    return []
            
            # this will catch the else
            if child.type == "seq":
                result = fn.apply(state.but_with(asl=child))
                if isinstance(result, ReturnSignal):
                    return result
                return []

    def _handle_cond(fn, state: Params):
        condition = fn.apply(state.but_with(asl=state.asl.first()))[0]
        if condition.value:
            result = fn.apply(state.but_with(asl=state.asl.second()))
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

class PrintFunction():
    @classmethod
    def emulate(cls, redirect: str, *args: list[Obj]) -> str:
        base = args[0].value
        arg_strs = cls._convert_args_to_strs(args[1:])
        tag_regex = re.compile(r"%\w")
        for arg in arg_strs:
            base = tag_regex.sub(arg, base, count=1)
        if redirect is not None:
            return(base)
        else:
            print(base)
            return ""

    @classmethod
    def _convert_args_to_strs(cls, args: list[Obj]) -> list[str]:
        arg_strs = []
        for arg in args:
            if isinstance(arg.value, bool):
                arg_strs.append("true" if arg.value else "false")
            else:
                arg_strs.append(str(arg))
        return arg_strs
