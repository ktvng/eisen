from __future__ import annotations
import re

from alpaca.config import Config
from alpaca.asts import CLRList, CLRToken
from alpaca.validator import AbstractModule

from seer._validator import Type, Object, Validator, Seer 
from seer._listir import ListIRParser


from error import Raise

class TranspilerFunctions:
    pass

class Flags:
    use_struct_ptr = "use_struct_ptr"
    use_ptr = "use_ptr"
    use_addr = "use_addr"
    keep_as_ptr = "keep_as_ptr"

    def __init__(self, flags: list[str] = []):
        self._flags = flags

    def __getitem__(self, x) -> str:
        return self._flags.__getitem__(x)

    def __setitem__(self, x, y: str) -> str:
        return self._flags.__setitem__(x, y)

    def __len__(self) -> int:
        return len(self._flags)

    def but_with(self, *args) -> Flags:
        return Flags(list(set(list(args) + self._flags)))
    
    def but_without(self, *args) -> Flags:
        return Flags([f for f in self._flags if f not in args])

class TranspilerParams():
    def __init__(self,
            config : Config,
            asl : CLRList,
            functions : dict,
            mod : AbstractModule,
            n_hidden_vars : int,
            flags : Flags,
            pre_parts: list[str],
            post_parts: list[str],
            name_of_rets: list[str],
            use_guard: bool,
            ):

        self.config = config
        self.asl = asl
        self.functions = functions
        self.mod = mod
        self.n_hidden_vars = n_hidden_vars
        self.flags = flags
        self.pre_parts = pre_parts
        self.post_parts = post_parts
        self.name_of_rets = name_of_rets
        self.use_guard = use_guard

    def but_with(self,
            config : Config = None,
            asl : CLRList = None,
            functions : dict = None,
            mod : AbstractModule = None,
            n_hidden_vars : int = None,
            flags : Flags = None,
            pre_parts: list[str] = None,
            post_parts: list[str] = None,
            name_of_rets: list[str] = None,
            use_guard: bool = None,
            ):

        params = TranspilerParams(
            self.config if config is None else config,
            self.asl if asl is None else asl,
            self.functions if functions is None else functions,
            self.mod if mod is None else mod,
            self.n_hidden_vars if n_hidden_vars is None else n_hidden_vars,
            self.flags if flags is None else flags,
            self.pre_parts if pre_parts is None else pre_parts,
            self.post_parts if post_parts is None else post_parts,
            self.name_of_rets if name_of_rets is None else name_of_rets,
            self.use_guard if use_guard is None else use_guard,
            )

        return params


class SharedCounter():
    def __init__(self, n: int):
        self.value = n

    def __add__(self, other):
        return self.value + other

    def __iadd__(self, other):
        self.value += other
        return self

    def __str__(self):
        return str(self.value)

class Helpers:
    @classmethod
    def is_primitive_type(cls, obj: Object):
        return obj.type.classification == Type.base_type_name

    @classmethod
    def is_function_type(cls, obj: Object):
        return obj.type.classification == Type.function_type_name

    @classmethod
    def is_named_product_type(cls, obj: Object):
        return obj.type.classification == Type.named_product_type_name

    @classmethod
    def _global_name(cls, name : str, mod : AbstractModule):
        return Transpiler.get_mod_prefix(mod) + name

    @classmethod
    def global_name_for(cls, obj: Object):
        ptr = "*" if obj.is_ptr else ""
        if Helpers.is_primitive_type(obj):
            name = obj.type.name()
            if name[-1] == "*" or name[-1] == "?":
                name = name[:-1]

            return name + ptr
        elif Helpers.is_function_type(obj):
            return Helpers._global_name(obj.name, obj.mod)
        elif Helpers.is_named_product_type(obj):
            return "struct " + Helpers._global_name(obj.type.name(), obj.type.mod) + ptr

    @classmethod
    def get_c_function_pointer(cls, obj: Object, params: TranspilerParams) -> str:
        typ = obj.type
        if typ.classification != Type.function_type_name:
            raise Exception(f"required a function type; got {typ.classification} instead")

        args = ""
        args += cls._to_function_pointer_arg(typ.arg, params)
        rets = cls._to_function_pointer_arg(typ.ret, params, as_pointers=True)
        if rets:
            args += ", " + rets

        return f"void (*{obj.name})({args})" 

    @classmethod
    def _to_function_pointer_arg(cls, typ: Type, params: TranspilerParams, as_pointers: bool = False) -> str:
        if typ is None:
            return ""

        if typ.classification == Type.base_type_name:
            if typ._name == "int":
                return "int";
            else:
                raise Exception("unimpl")

        elif typ.classification == Type.product_type_name:
            suffix = "*" if as_pointers else ""
            return ", ".join(
                [cls._to_function_pointer_arg(x, params) + suffix for x in typ.components])
        elif typ.classification == Type.named_product_type_name:
            return Helpers._global_name_for_type(typ, params.mod)

    @classmethod
    def type_is_pointer(cls, obj: Object, params: TranspilerParams):
        return (Flags.use_ptr in params.flags and not Helpers.is_primitive_type(obj)
            or obj.is_ret)

    @classmethod
    def should_deref(cls, obj: Object, params: TranspilerParams):
        return (obj.is_ret 
            or (obj.is_arg and not Helpers.is_primitive_type(obj))
            or (obj.is_ptr and Flags.keep_as_ptr not in params.flags)
            or obj.is_val 
            )

    @classmethod
    def should_keep_lhs_as_ptr(cls, l: Object, r: Object, params: TranspilerParams):
        return ((l.is_ptr and r.is_ptr)
        )

    @classmethod
    def should_addrs(cls, obj: Object, params: TranspilerParams):
        return ((Flags.use_struct_ptr in params.flags and not Helpers.is_primitive_type(obj))
            or (Flags.use_addr in params.flags and Helpers.is_primitive_type(obj))
            )

    @classmethod
    def get_right_child_flags_for_assignment(cls, l: Object, r: Object, params: TranspilerParams):
        # ptr to ptr
        if l.is_ptr and r.is_ptr:
            return params.flags.but_with(Flags.keep_as_ptr)
        # ptr to let
        if l.is_ptr and not r.is_ptr:
            return params.flags.but_with(Flags.use_addr)


    @classmethod
    def get_prefix(cls, obj: Object, params: TranspilerParams):
        if Helpers.type_is_pointer(obj, params):
            return "*"
        elif Helpers.should_deref(obj, params):
            return "*"
        elif Helpers.should_addrs(obj, params):
            return "&"
        
        return ""

class Transpiler():
    base_prefix = ""
    @classmethod
    def run(cls, config: Config, asl: CLRList, functions: TranspilerFunctions, mod: AbstractModule):
        functions = functions.get_build_map()
        params = TranspilerParams(config, asl, functions, mod, SharedCounter(0), Flags(), None, None, [], True)
        parts = Transpiler.transpile(params)
        code = Transpiler._postformat(parts, params)
        cls._add_method_decls(mod)
        return code

    @classmethod
    def transpile(cls, params: TranspilerParams):
        if isinstance(params.asl, CLRToken):
            return [params.asl.value]

        fn = Transpiler._get_function(params)
        return fn(params)

    @classmethod
    def _get_function(cls, params: TranspilerParams):
        asl_type = params.asl.type
        fn = params.functions.get(asl_type, None)
        if fn is None:
            Raise.error(f"transpiler: no function to build {asl_type}")

        return fn

    @classmethod
    def _postformat(cls, parts: list[str], params: TranspilerParams):
        txt = "".join(parts)
        indent = "  ";
        level = 0

        parts = txt.split("\n")
        formatted_txt = ""
        for part in parts:
            if re.match(r"struct var_ptr \w+ = \{0\};", part.strip()):
                formatted_txt += indent*level + part + "\n"
                continue
            level -= part.count('}')
            formatted_txt += indent*level + part + "\n"
            level += part.count('{')
        
        return cls._add_includes() + cls._add_guard_code(params) + formatted_txt + cls._add_main_method(params)

    @classmethod
    def _add_guard_code(cls, params: TranspilerParams):
        if params.use_guard:
            with open("./guardv2.c", 'r') as f:
                return f.read()
        return ""

    @classmethod
    def _add_includes(cls):
        return "#include <stdio.h>\n#include <stdatomic.h>\n#include <stdbool.h>\n\n"

    @classmethod
    def _add_main_method(cls, params: TranspilerParams):
        return "void main() {\n  " + Transpiler.base_prefix + "global_main();\n}\n"

    @classmethod
    def _get_all_function_in_module(cls, mod : AbstractModule):
        objs = mod.objects.values()
        fn_objs = [o for o in objs if o.type.classification == Type.function_type_name]

        for child in mod.children:
            fn_objs += cls._get_all_function_in_module(child)

        return fn_objs

    @classmethod
    def _add_method_decls(cls, mod : AbstractModule):
        fn_objs = cls._get_all_function_in_module(mod)

    @classmethod
    def get_mod_prefix(cls, mod : AbstractModule):
        prefix = ""
        while mod is not None:
            prefix = mod.name + "_" + prefix
            mod = mod.parent

        return Transpiler.base_prefix + prefix
     
class SeerFunctions(TranspilerFunctions):
    @classmethod
    def contains_call(cls, asl: CLRList):
        if isinstance(asl, CLRToken):
            return False
        elif asl.type == "call":
            return True
        return any([cls.contains_call(child) for child in asl])

    @classmethod
    def requires_pre_parts(cls, params: TranspilerParams):
        return params.pre_parts is None and cls.contains_call(params.asl)

    @classmethod
    def is_primitive_type(cls, type : Type):
        return type.classification == Type.base_type_name

    @classmethod
    def _global_name(cls, name : str, mod : AbstractModule):
        return Transpiler.get_mod_prefix(mod) + name

    indent = "  "

    def get_build_map(self):
        return {
            "start": self.pass_through_,
            "mod": self.mod_,
            "struct": self.struct_,
            ":": self.colon_,
            "create": self.create_,
            "def": self.def_,
            "args": self.args_,
            "seq": self.seq_,
            "let": self.let_,
            "var": self.var_,
            "val": self.val_,
            "return": self.return_,
            "=": self.equals_,
            "<-": self.larrow_,
            "ref": self.ref_,
            "+": self.binary_op("+"),
            "*": self.binary_op("*"),
            "-": self.binary_op("-"),
            "<": self.binary_op("<"),
            ">": self.binary_op(">"),
            "+=": self.binary_op("+="),
            "-=": self.binary_op("-="),
            "==": self.binary_op("=="),
            "||": self.binary_op("||"),
            "&&": self.binary_op("&&"),
            "rets": self.rets_,
            "prod_type": self.prod_type_,
            "call": self.call_,
            "params": self.params_,
            "while": self.while_,
            "cond": self.cond_,
            "if": self.if_,
            ".": self.dot_,
        }

    def pass_through_(self, params: TranspilerParams):
        parts = []
        for child in params.asl:
            parts += Transpiler.transpile(params.but_with(asl=child))
        return parts

    def dot_(self, params: TranspilerParams):
        if params.asl.head().type == "ref":
            parts = Transpiler.transpile(params.but_with(
                asl=params.asl.head(),
                flags=params.flags.but_without(Flags.use_struct_ptr)))
            return parts + [".", params.asl[1].value]
        
        return Transpiler.transpile(params.but_with(asl=params.asl.head())) + \
            [".", params.asl[1].value]

    def cond_(self, params: TranspilerParams):
        return ([] 
            + ["("] 
            + Transpiler.transpile(params.but_with(asl=params.asl[0]))
            + [")", " {\n"]
            + Transpiler.transpile(params.but_with(asl=params.asl[1]))
            + ["}"])

    def if_(self, params: TranspilerParams):
        parts = ["if "] + Transpiler.transpile(params.but_with(asl=params.asl[0]))
        for child in params.asl[1:]:
            if child.type == "cond":
                parts += [" else if "] + Transpiler.transpile(params.but_with(asl=child))
            else:
                parts += [" else {\n"] + Transpiler.transpile(params.but_with(asl=child)) + ["}"]
        return parts

    def while_(self, params: TranspilerParams):
        return ["while "] + Transpiler.transpile(params.but_with(asl=params.asl[0]))
        
    def mod_(self, params: TranspilerParams):
        parts = []
        # ignore the first entry in the list as it is the name token
        for child in params.asl[1:]:
            parts += Transpiler.transpile(params.but_with(asl=child))

        return parts

    def struct_(self, params: TranspilerParams):
        obj: Object = params.asl.data
        full_name = Helpers.global_name_for(obj)

        post_parts = []
        parts = [full_name, " {\n", f"int __nrefs__;\n"]
        for child in params.asl[1:]:
            additional_parts = Transpiler.transpile(
                params.but_with(asl=child, post_parts=post_parts)) 
            if additional_parts:
                parts += additional_parts + [";\n"]
        parts.append("};\n\n")
        return parts + post_parts

    def colon_(self, params: TranspilerParams):
        obj: Object = params.asl.data
        if obj.type.classification == Type.function_type_name:
            return [Helpers.get_c_function_pointer(obj, params)]
        full_name = Helpers.global_name_for(obj)
        ptr = "*" if Helpers.type_is_pointer(obj, params) else ""
        return [f"{full_name}{ptr} {obj.name}"]

    def args_(self, params: TranspilerParams):
        if len(params.asl) == 0:
            return []
        return Transpiler.transpile(params.but_with(asl=params.asl.head()))

    @classmethod
    def _write_function(self, args: CLRList, rets: CLRList, seq: CLRList, params: TranspilerParams):
        obj: Object = params.asl.data
        parts = [f"void {SeerFunctions._global_name(obj.name, obj.mod)}("]
        
        # args
        args_parts = Transpiler.transpile(params.but_with(
            asl=args,
            flags=params.flags.but_with(Flags.use_ptr)))
        if args_parts:
            parts += ["/*args*/ "] + args_parts

        # rets
        if rets:
            # append ", " after args
            if args: parts.append(", ")
            parts += ["/*rets*/ "] + Transpiler.transpile(params.but_with(asl=rets))
        
        parts.append(") {\n")

        # seq
        guard = []
        if params.use_guard:
            guard = ["void* __end__;\n", "v2_guard_get_end(&__end__);\n"]
        seq_parts = guard + Transpiler.transpile(params.but_with(asl=seq)) 

        # code for old guard format
        # if params.use_guard:
        #     seq_parts += (["enter_method();"] 
        #         + seq_parts 
        #         + ["free_guard(obj.__nrefs__, sizeof(obj type), obj addr);"] # for all objs
        #         + ["free_safe_ptr(ptr addr, objrefs addr);"] # for all objs
        #         + ["exit_method();"])

        parts += seq_parts
        parts.append("}\n\n")
        return parts 

    def create_(self, params: TranspilerParams):
        args = params.asl[0]
        rets = None if len(params.asl) == 2 else params.asl[1]
        seq = params.asl[-1]
        params.post_parts += self._write_function(args, rets, seq, params)
        return []


    def def_(self, params: TranspilerParams):
        args = params.asl[1]
        rets = None if len(params.asl) == 3 else params.asl[2]
        seq = params.asl[-1]
        return self._write_function(args, rets, seq, params)

    def rets_(self, params: TranspilerParams):
        parts = Transpiler.transpile(params.but_with(asl=params.asl.head()))
        return parts
            
    def seq_(self, params: TranspilerParams):
        parts = []
        for child in params.asl:
            parts += Transpiler.transpile(params.but_with(asl=child)) + [";\n"]
        return parts

    def let_(self, params: TranspilerParams):
        if isinstance(params.asl.head(), CLRList):
            return Transpiler.transpile(params.but_with(asl=params.asl.head()))

        obj: Object = params.asl.data
        type_name = Helpers.global_name_for(obj)

        if isinstance(params.asl[1], CLRList) and params.asl[1].type == "::":
            return [f"{type_name} {obj.name}"]

        return [f"{type_name} {obj.name} = "] + Transpiler.transpile(params.but_with(asl=params.asl[1]))

    def val_(self, params: TranspilerParams):
        if isinstance(params.asl.head(), CLRList):
            return Transpiler.transpile(params.but_with(asl=params.asl.head()))
        
        obj: Object = params.asl.data
        type_name = Helpers.global_name_for(obj)
        return [f"{type_name} {obj.name} = "] + Transpiler.transpile(params.but_with(
            asl=params.asl[1],
            flags=params.flags.but_with(Flags.use_addr)))


    def var_(self, params: TranspilerParams):
        # TODO: Think about
        if isinstance(params.asl.head(), CLRList):
            return Transpiler.transpile(params.but_with(asl=params.asl.head()))
        
        obj: Object = params.asl.data
        type_name = Helpers.global_name_for(obj)
        return ([f"struct var_ptr {obj.name} = ", "{0};\n"]
            + [f"{obj.name}.value = "] 
            + Transpiler.transpile(params.but_with(
                asl=params.asl[1],
                flags=params.flags.but_with(Flags.use_addr))))

    def return_(self, params: TranspilerParams):
        return ["return"]

    def ref_(self, params: TranspilerParams):
        obj: Object = params.asl.data

        if Helpers.is_function_type(obj):
            return ["&", Helpers.global_name_for(obj)]

        if obj.is_var:
            # TODO: global_name_for is overloaded for both resolving fn names and giving primitives types
            type_name = Helpers.global_name_for(obj)
            name = f"(({type_name}){obj.name}.value)"
            if Flags.keep_as_ptr in params.flags:
                return [f"{obj.name}.value"]
        else:
            name = obj.name

        # case for local variables
        prefix = Helpers.get_prefix(obj, params)
        parts = [prefix, name]

        # ensure proper order of operations with prefix
        if prefix:
            parts = ["("] + parts + [")"]

        return parts

    def _single_equals_(self, l: CLRList, r: CLRList, params: TranspilerParams):
        left_obj: Object = l.data
        name = left_obj.name

        post_parts = []
        if left_obj.is_var and params.use_guard:
            type_name = Helpers.global_name_for(left_obj)
            name = f"(({type_name}*)&{left_obj.name}.value)"
            post_parts = [";\n", f"v2_var_guard(&{left_obj.name}, __end__)"]

            if r.type == "call":
                final_parts = Transpiler.transpile(params.but_with(
                    asl=r, 
                    name_of_rets=[name]))

                pre_parts = [] if not params.pre_parts else params.pre_parts
                return pre_parts + final_parts + post_parts

        # special case if assignment comes from a method call
        if r.type == "call":
            final_parts = Transpiler.transpile(params.but_with(
                asl=r, 
                name_of_rets=["&" + name]))

            pre_parts = [] if not params.pre_parts else params.pre_parts
            return pre_parts + final_parts + post_parts

        parts = Transpiler.transpile(params.but_with(
            asl=l, 
            flags=params.flags.but_with(Flags.keep_as_ptr)))

        if isinstance(r, CLRToken):
            parts.append(" = ")
            parts.append(r.value)
            return parts + post_parts

        right_obj: Object = r.data
        assign_flags = Helpers.get_right_child_flags_for_assignment(left_obj, right_obj, params) 
        parts += ([" = "]
            + Transpiler.transpile(params.but_with(asl=r, flags=assign_flags)))
        
        return parts  + post_parts

    def equals_(self, params: TranspilerParams):
        parts = []
        pre_parts = []
        if SeerFunctions.requires_pre_parts(params):
            use_params = params.but_with(pre_parts=pre_parts)
        else:
            use_params = params

        if params.asl.head().type == "tuple":
            left_child_asls = [child for child in params.asl[0]]
            right_child_asls = [child for child in params.asl[1]]

            for l, r in zip(left_child_asls, right_child_asls):
                parts += self._single_equals_(l, r, use_params)
                parts.append(";\n")
            
            # remove trailing ";\n"
            return pre_parts + parts[:-1] 

        else:
            return self._single_equals_(params.asl[0], params.asl[1], use_params)

    def larrow_(self, params: TranspilerParams):
        if params.asl.head().type == "tuple":
            parts = []
            left_child_asls = [child for child in params.asl[0]]
            right_child_asls = [child for child in params.asl[1]]
            for l, r in zip(left_child_asls, right_child_asls):
                parts += SeerFunctions._binary_op(self, "=", l, r, params)
                parts.append(";\n")

            # remove final ";\n"
            return parts[:-1]
        else:
            fn = SeerFunctions.binary_op(self, "=")
            return fn(params)

    def _binary_op(self, op: str, l: CLRList, r: CLRList, params: TranspilerParams):
        return (["("]
                + Transpiler.transpile(params.but_with(asl=l))
                + [f" {op} "]
                + Transpiler.transpile(params.but_with(asl=r))
                + [")"])

    def binary_op(self, op : str):
        def op_fn(params: TranspilerParams):
            return self._binary_op(op, params.asl[0], params.asl[1], params)
        return op_fn

    def prod_type_(self, params: TranspilerParams):
        parts = Transpiler.transpile(params.but_with(asl=params.asl.head()))
        for child in params.asl[1:]:
            parts += [", "] + Transpiler.transpile(params.but_with(asl=child))
        
        return parts

    @classmethod
    def _define_variables_for_return(cls, ret_type: Type, params: TranspilerParams):
        types = []
        if ret_type.classification == Type.product_type_name:
            types += ret_type.components
        else:
            types = [ret_type]

        var_names = []
        for type in types:
            tmp_name = f"__{params.n_hidden_vars}__"
            params.n_hidden_vars += 1
            listir_code = f"(let (: {tmp_name} (type {type.name()})))"
            clrlist = ListIRParser.run(params.config, listir_code)
            vparams = Validator.Params(
                params.config, 
                clrlist, 
                Seer(), 
                [], 
                params.asl.data.mod,
                Context(), 
                "")
            Validator.validate(vparams)

            params.pre_parts += Transpiler.transpile(params.but_with(asl=clrlist))
            params.pre_parts.append(";\n")
            var_names.append(tmp_name)

        return var_names

    def call_(self, params: TranspilerParams):
        if params.asl.head().type == "fn":
            name = params.asl.head()[0].value
            if name == "print":
                parts = ["printf("] + Transpiler.transpile(params.but_with(asl=params.asl[1])) + [")"]
                return parts

        obj: Object = params.asl.data
        if obj.is_arg or obj.is_ret:
            prefix = ""
        else:
            prefix = Transpiler.get_mod_prefix(obj.mod)

        full_name = prefix + obj.name 

        var_names = []
        if params.pre_parts is not None:
            if params.name_of_rets:
                var_names = params.name_of_rets
            else:
                ret_type: Type = obj.type.ret
                var_names = SeerFunctions._define_variables_for_return(ret_type, params)

        if obj.type.arg is None:
            arg_types = []
        elif obj.type.arg.classification == Type.product_type_name:
            arg_types = obj.type.arg.components
        else:
            arg_types = [obj.type.arg]
        
        # if obj.type.ret is None:
        #     ret_types = []
        # elif obj.type.arg.type == Type.product_type_name:
        #     ret_types = obj.type.arg.components
        # else:
        #     ret_types = [obj.type.ret]

        expected_types = arg_types
        parameter_parts = []
        for child, expected_type in zip(params.asl[1], expected_types):
            these_flags = params.flags.but_with(Flags.use_struct_ptr)
            if expected_type.is_ptr:
                these_flags = these_flags.but_with(Flags.keep_as_ptr)

            parameter_parts += Transpiler.transpile(
                params.but_with(asl=child, flags=these_flags, name_of_rets=[]))
            parameter_parts.append(", ")

        if parameter_parts:
            parameter_parts = parameter_parts[:-1]

        ret_parts = [", " + var for var in var_names]
        if not parameter_parts and ret_parts:
            # remove ", "
            ret_parts[0] = ret_parts[0][2:]

        fn_call_parts = ([full_name, "(",] 
            + parameter_parts
            + ret_parts
            + [")"])

        if params.pre_parts:
            params.pre_parts += fn_call_parts + [";\n"]
            return var_names

        return fn_call_parts
 
    def params_(self, params: TranspilerParams):
        if len(params.asl) == 0:
            return []

        parts = Transpiler.transpile(params.but_with(asl=params.asl.head()))
        if len(params.asl) == 1:
            return parts

        for child in params.asl[1:]:
            parts += [", "] + Transpiler.transpile(params.but_with(asl=child))

        return parts

        