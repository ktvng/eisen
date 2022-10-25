from __future__ import annotations
import email
from sys import stdout
from typing import Any, Callable
import re

from alpaca.clr import CLRToken, CLRList
from alpaca.utils import Wrangler

from seer._common import asls_of_type
from seer._params import Params

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

# either value is primitive value, value is dict for struct, or value is asl for function
class InterpreterObject:
    def __init__(self, value: Any):
        self.value = value

    def _binary_ops(self, o: InterpreterObject, f: Callable[[Any, Any], Any]):
        if not isinstance(o, InterpreterObject):
            raise Exception(f"Error: expected interpreter object, but got {type(o)}")
        return InterpreterObject(f(self.value, o.value))

    def __add__(self, o: Any):
        return self._binary_ops(o, lambda_map["+"])

    def __sub__(self, o: Any):
        return self._binary_ops(o, lambda_map["-"])

    def __mul__(self, o: Any):
        return self._binary_ops(o, lambda_map["*"])

    def __truediv__(self, o: Any):
        return self._binary_ops(o, lambda_map["/"])

    def __floordiv__(self, o: Any):
        return self._binary_ops(o, lambda_map["/"])

    def __lt__(self, o: Any):
        return self._binary_ops(o, lambda_map["<"])

    def __le__(self, o: Any):
        return self._binary_ops(o, lambda_map["<="])

    def __eq__(self, o: Any):
        return self._binary_ops(o, lambda_map["=="])

    def __ne__(self, o: Any):
        return self._binary_ops(o, lambda_map["!="])

    def __gt__(self, o: Any):
        return self._binary_ops(o, lambda_map[">"])

    def __ge__(self, o: Any):
        return self._binary_ops(o, lambda_map[">="])

    def __str__(self) -> str:
        return str(self.value)

    def get(self, key: str): 
        if not isinstance(self.value, dict):
            raise Exception("Interpreter object must be a dict (for struct)")
        found = self.value.get(key, None)
        if found is None:
            new_obj = InterpreterObject(None)
            self.value[key] = new_obj
            found = new_obj
        return found




class AstInterpreter(Wrangler):
    def __init__(self, redirect_output=False):
        super().__init__()
        self.stdout = "";
        self.redirect_output = redirect_output

    def apply(self, params: Params) -> list[InterpreterObject]:
        # print(params.asl)
        return self._apply([params], [params])

    @Wrangler.covers(lambda params: isinstance(params.asl, CLRToken))
    def token_(fn, params: Params):
        value = params.asl.value
        if params.asl.type == "int":
            value = int(params.asl.value)
        if params.asl.type == "bool":
            value = params.asl.value == "true"

        return [InterpreterObject(value)]

    @Wrangler.covers(asls_of_type("+", "-", "/", "*", "<", "<=", "==", "!=", ">", ">="))
    def binop_(fn, params: Params):
        left = fn.apply(params.but_with(asl=params.asl.first()))[0]
        right = fn.apply(params.but_with(asl=params.asl.second()))[0]
        return [lambda_map[params.asl.type](left, right)]

    @Wrangler.covers(asls_of_type("and"))
    def and_(fn, params: Params):
        left = fn.apply(params.but_with(asl=params.asl.first()))[0]
        right = fn.apply(params.but_with(asl=params.asl.second()))[0]
        return [InterpreterObject(left.value and right.value)] 

    @Wrangler.covers(asls_of_type("or"))
    def or_(fn, params: Params):
        left = fn.apply(params.but_with(asl=params.asl.first()))[0]
        right = fn.apply(params.but_with(asl=params.asl.second()))[0]
        return [InterpreterObject(left.value or right.value)] 

    @Wrangler.covers(asls_of_type("let"))
    def let_(fn, params: Params):
        return fn.apply(params.but_with(asl=params.asl.first()))

    @Wrangler.covers(asls_of_type(":"))
    def colon_(fn, params: Params):
        if isinstance(params.asl.first(), CLRToken):
            names = [params.asl.first().value]
        else:
            names = [tag.value for tag in params.asl.first()]

        if params.asl.second().type == "type":
            # this is the case (let (: tags x y z) (type int))
            # we create a new object for each name
            objs = [InterpreterObject(None) for name in names]
        else:
            objs = fn.apply(params.but_with(asl=params.asl.second()))

        for name, obj in zip(names, objs):
            params.objs[name] = obj
        return objs

    @Wrangler.covers(asls_of_type("="))
    def eqs_(fn, params: Params):
        left = fn.apply(params.but_with(asl=params.asl.first()))
        right = fn.apply(params.but_with(asl=params.asl.second()))
        for l, r in zip(left, right):
            l.value = r.value
        return []

    @Wrangler.covers(asls_of_type("!"))
    def not_(fn, params: Params):
        objs = fn.apply(params.but_with(asl=params.asl.first()))
        x = [InterpreterObject(not objs[0].value)]
        return x

    @Wrangler.covers(asls_of_type("tuple"))
    def tuple(fn, params: Params):
        objs = []
        for child in params.asl:
            objs += fn.apply(params.but_with(asl=child))
        return objs

    @Wrangler.covers(asls_of_type("+=", "-=", "/=", "*="))
    def asseqs_(fn, params: Params):
        # because (= (ref name) ...)
        name = params.asl.first().first().value

        left = params.objs[name]
        right = fn.apply(params.but_with(asl=params.asl.second()))[0]
        new_obj = lambda_map[params.asl.type[0]](left, right)
        params.objs[name].value = new_obj.value
        return []

    @Wrangler.covers(asls_of_type("mod", "struct", "interface", "return"))
    def skip_(fn, params: Params):
        return

    @Wrangler.covers(asls_of_type("def"))
    def def_(fn, params: Params):
        fn_name = params.asl.first().value
        if fn_name == "main":
            # apply to the seq
            fn.apply(params.but_with(asl=params.asl[-1]))
        return []

    @Wrangler.covers(asls_of_type("start", "seq"))
    def exec_(fn, params: Params):
        for child in params.asl:
            fn.apply(params.but_with(asl=child))
        return []

    @Wrangler.covers(asls_of_type("ilet"))
    def ilet_(fn, params: Params):
        # this is the case for (ilet (tags x y) (...))
        if isinstance(params.asl.first(), CLRList):
            names = [token.value for token in params.asl.first()]
            # this handles if (...) is a (call ...)
            if params.asl.second().type == "call":
                values = fn.apply(params.but_with(asl=params.asl.second()))

            # this handles if (...) is a (tuple ...)
            else:
                values = [fn.apply(params.but_with(asl=child))[0] for child in params.asl.second()]
        else:
            names = [params.asl.first().value]
            values = [fn.apply(params.but_with(asl=params.asl.second()))[0]]
        
        for name, value in zip(names, values):
            params.objs[name] = value
        return []

    @Wrangler.covers(asls_of_type("cast"))
    def cast_(fn, params: Params):
        return fn.apply(params.but_with(asl=params.asl.first()))

    @Wrangler.covers(asls_of_type("call"))
    def call_(fn, params: Params):
        # get the asl of type (fn <name>)
        fn_asl = fn._unravel_scoping(params.asl.first())

        if isinstance(fn_asl.first(), CLRToken) and fn_asl.first().value == "print":
            args = [fn.apply(params.but_with(asl=asl))[0] for asl in params.asl.second()]
            if fn.redirect_output:
                fn.stdout += PrintFunction.emulate(fn.stdout, *args)
            else:
                PrintFunction.emulate(None, *args)
            
            return []

        # this case is if we are looking pu the function inside a struct
        if fn_asl.first().type == ".":
            obj = fn.apply(params.but_with(asl=fn_asl.first()))[0]
            fn_instance = obj.value
        # this case is if we are looking up a local function or a function in the closure
        else:
            found_fn = params.objs.get(fn_asl.first().value, None)
            if found_fn:
                fn_instance = found_fn.value
            else:
                # we need to drop into the original CLR which defines the original function
                # in order to get the return types.
                fn_instance = params.oracle.get_instances(fn_asl)[0]

        asl_defining_the_function = fn_instance.asl

        # enter a new object context
        fn_objs = {}

        # add parameters to the context; creates a new object so we don't override the 
        # existing object when we change it in the function.
        param_names = fn._get_param_names(asl_defining_the_function)
        for name, param in zip(param_names, params.asl.second()):
            obj = fn.apply(params.but_with(asl=param))[0]
            fn_objs[name] = InterpreterObject(obj.value)

        # add return values to the context
        return_values = []
        return_names = fn._get_return_names(asl_defining_the_function)
        for name in return_names:
            if asl_defining_the_function.type == "create":
                obj = InterpreterObject({})
            else:
                obj = InterpreterObject(None)

            fn_objs[name] = obj
            return_values.append(obj)

        # call the function by invoking the seq of the asl_defining_the_function
        fn.apply(params.but_with(
            asl=asl_defining_the_function[-1],
            objs=fn_objs))

        return return_values

    @Wrangler.covers(asls_of_type("ref"))
    def ref_(fn, params: Params):
        name = params.asl.first().value
        local_obj = params.objs.get(name, None)
        if local_obj is not None:
            return [local_obj]

        # this is for functions apparently
        instance = params.oracle.get_instances(params.asl)[0]
        return [InterpreterObject(instance)]
        

    @Wrangler.covers(asls_of_type("."))
    def dot_(fn, params: Params):
        obj = fn.apply(params.but_with(asl=params.asl.first()))[0]
        return [obj.get(params.asl.second().value)]

    @Wrangler.covers(asls_of_type("type"))
    def type_(fn, params: Params):
        return [InterpreterObject(None)]

    @Wrangler.covers(asls_of_type("while"))
    def while_(fn, params: Params):
        result = fn._handle_cond(params.but_with(asl=params.asl.first()))
        while result:
            result = fn._handle_cond(params.but_with(asl=params.asl.first()))
        return []

    @Wrangler.covers(asls_of_type("if"))
    def if_(fn, params: Params):
        for child in params.asl:
            if child.type == "cond":
                was_true = fn._handle_cond(params.but_with(asl=child))
                if was_true:
                    return []
            
            # this will catch the else
            if child.type == "seq":
                fn.apply(params.but_with(asl=child))
                return []

    def _handle_cond(fn, params: Params):
        condition = fn.apply(params.but_with(asl=params.asl.first()))[0]
        if condition.value:
            fn.apply(params.but_with(asl=params.asl.second()))
            return True
        return False

    # TODO: make this shared 
    def _unravel_scoping(self, asl: CLRList) -> CLRList:
        if asl.type != "::" and asl.type != "fn":
            raise Exception(f"unexpected asl type of {asl.type}")
        
        if asl.type == "fn":
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
    def emulate(cls, redirect: str, *args: list[InterpreterObject]) -> str:
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
    def _convert_args_to_strs(cls, args: list[InterpreterObject]) -> list[str]:
        arg_strs = []
        for arg in args:
            if isinstance(arg.value, bool):
                arg_strs.append("true" if arg.value else "false")
            else:
                arg_strs.append(str(arg))
        return arg_strs