from __future__ import annotations
import re

import alpaca
from alpaca.config import Config
from alpaca.clr import CLRList, CLRToken
from alpaca.validator import AbstractModule, AbstractType
from alpaca.utils import Visitor, PartialTransform

from seer._validator import OldType, Object, SeerValidator 
from seer._validator import Params as VParams

class SeerTranspiler(Visitor):
    base_prefix = ""
    def __init__(self):
        super().__init__()

    def run(self, config: Config, asl: CLRList, mod: AbstractModule):
        params = SeerTranspiler.Params(config, asl, mod, SharedCounter(0), Flags(), None, None, [], True)
        parts = self.apply(params)
        code = self._postformat(parts, params)
        return code

    def apply(self, params: SeerTranspiler.Params):
        return self._apply(
            match_args=[params.asl],
            fn_args=[params])

    class Params():
        def __init__(self,
                config : Config,
                asl : CLRList,
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
                mod : AbstractModule = None,
                n_hidden_vars : int = None,
                flags : Flags = None,
                pre_parts: list[str] = None,
                post_parts: list[str] = None,
                name_of_rets: list[str] = None,
                use_guard: bool = None,
                ):

            params = SeerTranspiler.Params(
                self.config if config is None else config,
                self.asl if asl is None else asl,
                self.mod if mod is None else mod,
                self.n_hidden_vars if n_hidden_vars is None else n_hidden_vars,
                self.flags if flags is None else flags,
                self.pre_parts if pre_parts is None else pre_parts,
                self.post_parts if post_parts is None else post_parts,
                self.name_of_rets if name_of_rets is None else name_of_rets,
                self.use_guard if use_guard is None else use_guard,
                )

            return params

    @classmethod
    def _postformat(cls, parts: list[str], params: SeerTranspiler.Params):
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
    def _add_guard_code(cls, params: SeerTranspiler.Params):
        if params.use_guard:
            with open("./guardv2.c", 'r') as f:
                return f.read()
        return ""

    @classmethod
    def _add_includes(cls):
        return "#include <stdio.h>\n#include <stdatomic.h>\n#include <stdbool.h>\n\n"

    @classmethod
    def _add_main_method(cls, params: SeerTranspiler.Params):
        return "void main() {\n  " + SeerTranspiler.base_prefix + "global_main();\n}\n"

    @classmethod
    def _get_all_function_in_module(cls, mod : AbstractModule):
        objs = mod.objects.values()
        fn_objs = [o for o in objs if Helpers.is_function_type(o)]

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

        return SeerTranspiler.base_prefix + prefix

    @classmethod
    def contains_call(cls, asl: CLRList):
        if isinstance(asl, CLRToken):
            return False
        elif asl.type == "call":
            return True
        return any([cls.contains_call(child) for child in asl])

    @classmethod
    def requires_pre_parts(cls, params: SeerTranspiler.Params):
        return params.pre_parts is None and cls.contains_call(params.asl)

    @classmethod
    def is_primitive_type(cls, type : OldType):
        return type.classification == AbstractType.base_classification

    @classmethod
    def _global_name(cls, name : str, mod : AbstractModule):
        return SeerTranspiler.get_mod_prefix(mod) + name

    @Visitor.covers(lambda x: isinstance(x, CLRToken))
    def token_(self, params: SeerTranspiler.Params):
        return [params.asl.value]

    @Visitor.covers(lambda x: x.type == "start")
    def pass_through_(self, params: SeerTranspiler.Params):
        parts = []
        for child in params.asl:
            parts += self.apply(params.but_with(asl=child))
        return parts

    @Visitor.covers(lambda x: x.type == ".")
    def dot_(self, params: SeerTranspiler.Params):
        if params.asl.head().type == "ref":
            parts = self.apply(params.but_with(
                asl=params.asl.head(),
                flags=params.flags.but_without(Flags.use_struct_ptr)))
            return parts + [".", params.asl[1].value]
        
        return self.apply(params.but_with(asl=params.asl.head())) + \
            [".", params.asl[1].value]

    @Visitor.covers(lambda x: x.type == "cond")
    def cond_(self, params: SeerTranspiler.Params):
        return ([] 
            + ["("] 
            + self.apply(params.but_with(asl=params.asl[0]))
            + [")", " {\n"]
            + self.apply(params.but_with(asl=params.asl[1]))
            + ["}"])

    @Visitor.covers(lambda x: x.type == "if")
    def if_(self, params: SeerTranspiler.Params):
        parts = ["if "] + self.apply(params.but_with(asl=params.asl[0]))
        for child in params.asl[1:]:
            if child.type == "cond":
                parts += [" else if "] + self.apply(params.but_with(asl=child))
            else:
                parts += [" else {\n"] + self.apply(params.but_with(asl=child)) + ["}"]
        return parts

    @Visitor.covers(lambda x: x.type == "while")
    def while_(self, params: SeerTranspiler.Params):
        return ["while "] + self.apply(params.but_with(asl=params.asl[0]))
        
    @Visitor.covers(lambda x: x.type == "mod")
    def mod_(self, params: SeerTranspiler.Params):
        parts = []
        # ignore the first entry in the list as it is the name token
        for child in params.asl[1:]:
            parts += self.apply(params.but_with(asl=child))

        return parts

    @Visitor.covers(lambda x: x.type == "struct")
    def struct_(self, params: SeerTranspiler.Params):
        obj: Object = params.asl.data
        full_name = Helpers.global_name_for(obj)

        post_parts = []
        parts = [full_name, " {\n", f"int __nrefs__;\n"]
        for child in params.asl[1:]:
            additional_parts = self.apply(
                params.but_with(asl=child, post_parts=post_parts)) 
            if additional_parts:
                parts += additional_parts + [";\n"]
        parts.append("};\n\n")
        return parts + post_parts

    @Visitor.covers(lambda x: x.type == ":")
    def colon_(self, params: SeerTranspiler.Params):
        obj: Object = params.asl.data
        if Helpers.is_function_type(obj):
            return [Helpers.get_c_function_pointer(obj, params)]
        full_name = Helpers.global_name_for(obj)
        ptr = "*" if Helpers.type_is_pointer(obj, params) else ""
        return [f"{full_name}{ptr} {obj.name}"]

    @Visitor.covers(lambda x: x.type == "args")
    def args_(self, params: SeerTranspiler.Params):
        if len(params.asl) == 0:
            return []
        return self.apply(params.but_with(asl=params.asl.head()))

    @classmethod
    def _write_function(cls, self, args: CLRList, rets: CLRList, seq: CLRList, params: SeerTranspiler.Params):
        obj: Object = params.asl.data
        parts = [f"void {SeerTranspiler._global_name(obj.name, obj.mod)}("]
        
        # args
        args_parts = self.apply(params.but_with(
            asl=args,
            flags=params.flags.but_with(Flags.use_ptr)))
        if args_parts:
            parts += ["/*args*/ "] + args_parts

        # rets
        if rets:
            # append ", " after args
            if args: parts.append(", ")
            parts += ["/*rets*/ "] + self.apply(params.but_with(asl=rets))
        
        parts.append(") {\n")

        # seq
        guard = []
        if params.use_guard:
            guard = ["void* __end__;\n", "v2_guard_get_end(&__end__);\n"]
        seq_parts = guard + self.apply(params.but_with(asl=seq)) 

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

    @Visitor.covers(lambda x: x.type == "create")
    def create_(self, params: SeerTranspiler.Params):
        args = params.asl[0]
        rets = None if len(params.asl) == 2 else params.asl[1]
        seq = params.asl[-1]
        params.post_parts += SeerTranspiler._write_function(self, args, rets, seq, params)
        return []

    @Visitor.covers(lambda x: x.type == "def")
    def def_(self, params: SeerTranspiler.Params):
        args = params.asl[1]
        rets = None if len(params.asl) == 3 else params.asl[2]
        seq = params.asl[-1]
        return SeerTranspiler._write_function(self, args, rets, seq, params)

    @Visitor.covers(lambda x: x.type == "rets")
    def rets_(self, params: SeerTranspiler.Params):
        parts = self.apply(params.but_with(asl=params.asl.head()))
        return parts
            
    @Visitor.covers(lambda x: x.type == "seq")
    def seq_(self, params: SeerTranspiler.Params):
        parts = []
        for child in params.asl:
            parts += self.apply(params.but_with(asl=child)) + [";\n"]
        return parts

    @Visitor.covers(lambda x: x.type == "let")
    def let_(self, params: SeerTranspiler.Params):
        objs: list[Object] = params.asl.data
        # TODO: allow this to work with multiple objects
        obj = objs[0]
        type_name = Helpers.global_name_for(obj)

        # case for (let (: x (type int)))
        if len(params.asl) == 1:
            return [f"{type_name} {obj.name}"]
            
        if isinstance(params.asl[1], CLRList) and params.asl[1].type == "::":
            return [f"{type_name} {obj.name}"]

        return [f"{type_name} {obj.name} = "] + self.apply(params.but_with(asl=params.asl[1]))

    @Visitor.covers(lambda x: x.type == "val")
    def val_(self, params: SeerTranspiler.Params):
        obj: Object = params.asl.data
        obj = obj[0]

        type_name = Helpers.global_name_for(obj)
        if len(params.asl) == 1:
            return [f"{type_name} {obj.name}"]

        return [f"{type_name} {obj.name} = "] + self.apply(params.but_with(
            asl=params.asl[1],
            flags=params.flags.but_with(Flags.use_addr)))


    @Visitor.covers(lambda x: x.type == "var")
    def var_(self, params: SeerTranspiler.Params):
        # TODO: Think about
        
        obj: Object = params.asl.data
        obj = obj[0]
        if len(params.asl) == 1:
            return [f"struct var_ptr {obj.name}"]

        return ([f"struct var_ptr {obj.name} = ", "{0};\n"]
            + [f"{obj.name}.value = "] 
            + self.apply(params.but_with(
                asl=params.asl[1],
                flags=params.flags.but_with(Flags.use_addr))))

    @Visitor.covers(lambda x: x.type == "return")
    def return_(self, params: SeerTranspiler.Params):
        return ["return"]

    @Visitor.covers(lambda x: x.type == "ref")
    def ref_(self, params: SeerTranspiler.Params):
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

    def _single_equals_(self, l: CLRList, r: CLRList, params: SeerTranspiler.Params):
        left_obj: Object = l.data
        # TODO: fix for multiple equals in let
        if isinstance(left_obj, list):
            left_obj = left_obj[0]
        name = left_obj.name

        post_parts = []
        if left_obj.is_var and params.use_guard:
            type_name = Helpers.global_name_for(left_obj)
            name = f"(({type_name}*)&{left_obj.name}.value)"
            post_parts = [";\n", f"v2_var_guard(&{left_obj.name}, __end__)"]

            if r.type == "call":
                final_parts = self.apply(params.but_with(
                    asl=r, 
                    name_of_rets=[name]))

                pre_parts = [] if not params.pre_parts else params.pre_parts
                return pre_parts + final_parts + post_parts

        # special case if assignment comes from a method call
        if r.type == "call":
            final_parts = self.apply(params.but_with(
                asl=r, 
                name_of_rets=["&" + name]))

            pre_parts = [] if not params.pre_parts else params.pre_parts
            return pre_parts + final_parts + post_parts

        parts = self.apply(params.but_with(
            asl=l, 
            flags=params.flags.but_with(Flags.keep_as_ptr)))

        if isinstance(r, CLRToken):
            parts.append(" = ")
            parts.append(r.value)
            return parts + post_parts

        right_obj: Object = r.data
        assign_flags = Helpers.get_right_child_flags_for_assignment(left_obj, right_obj, params) 
        parts += ([" = "]
            + self.apply(params.but_with(asl=r, flags=assign_flags)))
        
        return parts  + post_parts

    @Visitor.covers(lambda x: x.type == "=")
    def equals_(self, params: SeerTranspiler.Params):
        parts = []
        pre_parts = []
        if SeerTranspiler.requires_pre_parts(params):
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

    @Visitor.covers(lambda x: x.type == "<-")
    def larrow_(self, params: SeerTranspiler.Params):
        # TODO: consolidate this
        def _binary_op(op: str, fn, l: CLRList, r: CLRList, params: SeerTranspiler.Params):
            return (["("]
                    + fn.apply(params.but_with(asl=l))
                    + [f" {op} "]
                    + fn.apply(params.but_with(asl=r))
                    + [")"])

        def binary_op(op : str):
            def op_fn(fn, params: SeerTranspiler.Params):
                return _binary_op(op, fn, params.asl[0], params.asl[1], params)
            return op_fn

        if params.asl.head().type == "tuple":
            parts = []
            left_child_asls = [child for child in params.asl[0]]
            right_child_asls = [child for child in params.asl[1]]
            for l, r in zip(left_child_asls, right_child_asls):
                parts += _binary_op("=", l, r, params)
                parts.append(";\n")

            # remove final ";\n"
            return parts[:-1]
        else:
            fn = binary_op("=")
            return fn(self, params)

    def binary_op(op : str):
        def _binary_op(op: str, fn, l: CLRList, r: CLRList, params: SeerTranspiler.Params):
            return (["("]
                + fn.apply(params.but_with(asl=l))
                + [f" {op} "]
                + fn.apply(params.but_with(asl=r))
                + [")"])

        def op_fn(fn, params: SeerTranspiler.Params):
            return _binary_op(op, fn, params.asl[0], params.asl[1], params)
        return op_fn

    plus_ = PartialTransform(lambda x: x.type == "+", binary_op("+"))
    minus_= PartialTransform(lambda x: x.type == "-", binary_op("-"))
    times_= PartialTransform(lambda x: x.type == "*", binary_op("*"))
    divide_= PartialTransform(lambda x: x.type == "/", binary_op("/"))
    leq_ = PartialTransform(lambda x: x.type == "<=", binary_op("<="))
    geq_ = PartialTransform(lambda x: x.type == ">=", binary_op(">="))
    greater_ = PartialTransform(lambda x: x.type == ">", binary_op(">"))
    lesser_ = PartialTransform(lambda x: x.type == "<", binary_op("<"))
    plus_eq_ = PartialTransform(lambda x: x.type == "+=", binary_op("+="))
    minus_eq_ = PartialTransform(lambda x: x.type == "-=", binary_op("-="))
    eq_ = PartialTransform(lambda x: x.type == "==", binary_op("=="))
    or_ = PartialTransform(lambda x: x.type == "||", binary_op("||"))
    and_ = PartialTransform(lambda x: x.type == "&&", binary_op("&&"))

    @Visitor.covers(lambda x: x.type == "prod_type")
    def prod_type_(self, params: SeerTranspiler.Params):
        parts = self.apply(params.but_with(asl=params.asl.head()))
        for child in params.asl[1:]:
            parts += [", "] + self.apply(params.but_with(asl=child))
        
        return parts

    @classmethod
    def _define_variables_for_return(cls, ret_type: OldType, params: SeerTranspiler.Params):
        types = []
        if ret_type.classification == AbstractType.tuple_classification:
            types += ret_type.components
        else:
            types = [ret_type]

        var_names = []
        for type in types:
            tmp_name = f"__{params.n_hidden_vars}__"
            params.n_hidden_vars += 1
            listir_code = f"(let (: {tmp_name} (type {type.name()})))"
            clrlist = alpaca.clr.CLRParser.run(params.config, listir_code)
            # use none as these fields will not be used
            vparams = VParams(
                config = params.config,
                asl = clrlist,
                txt = None,
                mod = params.asl.data.mod,
                fns = SeerValidator(),
                context = AbstractModule(),
                flags = None,
                struct_name = None)

            SeerValidator().apply(vparams)

            params.pre_parts += self.apply(params.but_with(asl=clrlist))
            params.pre_parts.append(";\n")
            var_names.append(tmp_name)

        return var_names

    @Visitor.covers(lambda x: x.type == "call")
    def call_(self, params: SeerTranspiler.Params):
        # first check if the method is special
        if params.asl.head().type == "fn":
            name = params.asl.head().head_value()
            if name == "print":
                parts = ["printf("] + self.apply(params.but_with(asl=params.asl[1])) + [")"]
                return parts

        obj: Object = params.asl.data

        # a function which is passed in as an argument/return value has no prefix
        prefix = "" if obj.is_arg or obj.is_ret else SeerTranspiler.get_mod_prefix(obj.mod)
        full_name = prefix + obj.name 

        var_names = []
        ret_parts = []
        if params.pre_parts is not None:
            if params.name_of_rets:
                var_names = params.name_of_rets
                ret_parts = [", " + var for var in var_names]
            else:
                ret_type: OldType = obj.type.ret
                var_names = SeerTranspiler._define_variables_for_return(ret_type, params)
                ret_parts = [", &" + var for var in var_names]
                

        if obj.type.arg is None:
            arg_types = []
        elif obj.type.arg.classification == AbstractType.tuple_classification:
            arg_types = obj.type.arg.components
        else:
            arg_types = [obj.type.arg]
        

        expected_types = arg_types
        parameter_parts = []
        for child, expected_type in zip(params.asl[1], expected_types):
            these_flags = params.flags.but_with(Flags.use_struct_ptr)
            if expected_type.is_ptr:
                these_flags = these_flags.but_with(Flags.keep_as_ptr)

            parameter_parts += self.apply(
                params.but_with(asl=child, flags=these_flags, name_of_rets=[]))
            parameter_parts.append(", ")

        if parameter_parts:
            parameter_parts = parameter_parts[:-1]

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
 
    @Visitor.covers(lambda x: x.type == "params")
    def params_(self, params: SeerTranspiler.Params):
        if len(params.asl) == 0:
            return []
        parts = self.apply(params.but_with(asl=params.asl.head()))
        for child in params.asl[1:]:
            parts += [", "] + self.apply(params.but_with(asl=child))
        return parts

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
        return obj.type.classification == AbstractType.base_classification 

    @classmethod
    def is_function_type(cls, obj: Object):
        return obj.type.classification == AbstractType.function_classification

    @classmethod
    def is_struct_type(cls, obj: Object):
        return obj.type.classification == AbstractType.struct_classification

    @classmethod
    def _global_name(cls, name : str, mod : AbstractModule):
        return SeerTranspiler.get_mod_prefix(mod) + name

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
        elif Helpers.is_struct_type(obj):
            return "struct " + Helpers._global_name(obj.type.name(), obj.type.mod) + ptr

    @classmethod
    def get_c_function_pointer(cls, obj: Object, params: SeerTranspiler.Params) -> str:
        typ = obj.type
        if not Helpers.is_function_type(obj):
            raise Exception(f"required a function type; got {typ.classification} instead")

        args = ""
        args += cls._to_function_pointer_arg(typ.arg, params)
        rets = cls._to_function_pointer_arg(typ.ret, params, as_pointers=True)
        if rets:
            args += ", " + rets

        return f"void (*{obj.name})({args})" 

    @classmethod
    def _to_function_pointer_arg(cls, typ: OldType, params: SeerTranspiler.Params, as_pointers: bool = False) -> str:
        if typ is None:
            return ""

        if typ.classification == AbstractType.base_classification:
            if typ._name == "int":
                return "int";
            else:
                raise Exception("unimpl")

        elif typ.classification == AbstractType.tuple_classification:
            suffix = "*" if as_pointers else ""
            return ", ".join(
                [cls._to_function_pointer_arg(x, params) + suffix for x in typ.components])
        elif typ.classification == OldType.named_product_type_name:
            return Helpers._global_name_for_type(typ, params.mod)

    @classmethod
    def type_is_pointer(cls, obj: Object, params: SeerTranspiler.Params):
        return (Flags.use_ptr in params.flags and not Helpers.is_primitive_type(obj)
            or obj.is_ret)

    @classmethod
    def should_deref(cls, obj: Object, params: SeerTranspiler.Params):
        return (obj.is_ret 
            or (obj.is_arg and not Helpers.is_primitive_type(obj))
            or (obj.is_ptr and Flags.keep_as_ptr not in params.flags)
            or obj.is_val 
            )

    @classmethod
    def should_keep_lhs_as_ptr(cls, l: Object, r: Object, params: SeerTranspiler.Params):
        return ((l.is_ptr and r.is_ptr)
        )

    @classmethod
    def should_addrs(cls, obj: Object, params: SeerTranspiler.Params):
        return ((Flags.use_struct_ptr in params.flags and not Helpers.is_primitive_type(obj))
            or (Flags.use_addr in params.flags and Helpers.is_primitive_type(obj))
            )

    @classmethod
    def get_right_child_flags_for_assignment(cls, l: Object, r: Object, params: SeerTranspiler.Params):
        # ptr to ptr
        if l.is_ptr and r.is_ptr:
            return params.flags.but_with(Flags.keep_as_ptr)
        # ptr to let
        if l.is_ptr and not r.is_ptr:
            return params.flags.but_with(Flags.use_addr)


    @classmethod
    def get_prefix(cls, obj: Object, params: SeerTranspiler.Params):
        if Helpers.type_is_pointer(obj, params):
            return "*"
        elif Helpers.should_deref(obj, params):
            return "*"
        elif Helpers.should_addrs(obj, params):
            return "&"
        
        return ""