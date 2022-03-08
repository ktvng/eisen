from __future__ import annotations
import re

from alpaca.config import Config
from alpaca.asts import CLRList, CLRToken

from seer._validator import AbstractModule, Typing, AbstractObject

from error import Raise

class TranspilerFunctions:
    pass

class TranspilerParams():
    attrs = ['config', 'asl', 'functions', 'mod']

    def __init__(self,
            config : Config,
            asl : CLRList,
            functions : dict,
            mod : AbstractModule):

        self.config = config
        self.asl = asl
        self.functions = functions
        self.mod = mod


    def but_with(self,
            config : Config = None,
            asl : CLRList = None,
            functions : dict = None,
            mod : AbstractModule = None):

        new_params = TranspilerParams.new_from(self)
        if config is not None:
            new_params.config = config
        if asl is not None:
            new_params.asl = asl
        if functions is not None:
            new_params.functions = functions
        if mod is not None:
            new_params.mod = mod
        
        return new_params

    @classmethod
    def new_from(cls, params : TranspilerParams, overrides : dict = {}) -> TranspilerParams:
        new_params = TranspilerParams(
            params.config,
            params.asl,
            params.functions,
            params.mod)

        for k, v in overrides:
            if k in TranspilerParams.attrs:
                setattr(new_params, k, v)
        
        return new_params

class Transpiler():
    base_prefix = "__SEER_"
    @classmethod
    def run(cls, config : Config, asl : CLRList, functions : TranspilerFunctions, mod : AbstractModule):
        functions = functions.get_build_map()
        params = TranspilerParams(config, asl, functions, mod)
        parts = Transpiler.transpile(params)
        code = Transpiler._postformat(parts)
        cls._add_method_decls(mod)
        return code

    @classmethod
    def transpile(cls, params : TranspilerParams):
        if isinstance(params.asl, CLRToken):
            return [params.asl.value]

        fn = Transpiler._get_function(params)
        return fn(params)

    @classmethod
    def _get_function(cls, params : TranspilerParams):
        asl_type = params.asl.type
        fn = params.functions.get(asl_type, None)
        if fn is None:
            Raise.error(f"no function to build {asl_type}")

        return fn

    @classmethod
    def _postformat(cls, parts : list[str]):
        txt = "".join(parts)
        indent = "  ";
        level = 0

        parts = txt.split("\n")
        formatted_txt = ""
        for part in parts:
            level -= part.count('}')
            formatted_txt += indent*level + part + "\n"
            level += part.count('{')

        return cls._add_includes() + formatted_txt + cls._add_main_method()

    @classmethod
    def _add_includes(cls):
        return "#include <stdio.h>\n\n"

    @classmethod
    def _add_main_method(cls):
        return "void main() {\n  " + Transpiler.base_prefix + "global_main();\n}\n"

    @classmethod
    def _get_all_function_in_module(cls, mod : AbstractModule):
        objs = mod.context.objs_in_scope._objs.values()
        fn_objs = [o for o in objs if o.type.type == Typing.function_type_name]

        for child in mod.child_modules:
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
            mod = mod.parent_module

        return Transpiler.base_prefix + prefix


        
class SeerFunctions(TranspilerFunctions):
    @classmethod
    def global_name(cls, name : str, mod : AbstractModule):
        return Transpiler.get_mod_prefix(mod) + name

    @classmethod
    def global_name_for_type(cls, token_type : Typing.Type, mod : AbstractModule):
        # case if is primitive
        if token_type.type == Typing.base_type_name:
            type_name = token_type.name()
        else:
            type_name = "struct " + SeerFunctions.global_name(token_type.name(), mod)

        return type_name

    indent = "  "

    def get_build_map(self):
        return {
            "start": self.pass_through_,
            "mod": self.mod_,
            "struct": self.struct_,
            ":": self.colon_,
            "def": self.def_,
            "args": self.args_,
            "seq": self.seq_,
            "let": self.let_,
            "return": self.return_,
            "=": self.equals_,
            "ref": self.ref_,
            "+": self.binary_op("+"),
            "<": self.binary_op("<"),
            "rets": self.rets_,
            "prod_type": self.prod_type_,
            "call": self.call_,
            "params": self.params_,
            "while": self.while_,
        }

    def pass_through_(self, params : TranspilerParams):
        parts = []
        for child in params.asl:
            parts += Transpiler.transpile(params.but_with(asl=child))

        return parts

    def while_(self, params: TranspilerParams):
        cond = params.asl[0]
        parts = ["while ("]
        parts += Transpiler.transpile(params.but_with(asl=cond[0]))
        parts += [") ", "{\n"]
        parts += Transpiler.transpile(params.but_with(asl=cond[1]))
        parts += ["}"]

        return parts
        

    def mod_(self, params : TranspilerParams):
        parts = []
        for child in params.asl[1:]:
            parts += Transpiler.transpile(params.but_with(asl=child))

        return parts

    def struct_(self, params : TranspilerParams):
        obj: AbstractObject = params.asl.data
        full_name = SeerFunctions.global_name(obj.name, obj.mod)
        parts = [f"struct {full_name}", " {\n"]
        for child in params.asl[1:]:
            parts += Transpiler.transpile(params.but_with(asl=child)) + [";\n"]
        
        parts.append("};\n")
        return parts

    def colon_(self, params : TranspilerParams):
        obj: AbstractObject = params.asl.data
        type_name = SeerFunctions.global_name_for_type(obj.type, obj.mod)
        return [f"{type_name} {obj.name}"]

    def def_(self, params : TranspilerParams):
        obj: AbstractObject = params.asl.data
        parts = [f"void {SeerFunctions.global_name(obj.name, obj.mod)}(/*args*/ "]

        # args
        parts += Transpiler.transpile(params.but_with(asl=params.asl[1])) 

        # rets
        if len(params.asl) == 4:
            parts += [", /*rets*/ "] + Transpiler.transpile(params.but_with(asl=params.asl[2]))
        
        parts.append(") {\n")

        # seq
        parts += Transpiler.transpile(params.but_with(asl=params.asl[-1])) 
        parts.append("}\n")
        return parts

    def args_(self, params : TranspilerParams):
        if len(params.asl) == 0:
            return []

        return Transpiler.transpile(params.but_with(asl=params.asl[0]))

    def rets_(self, params : TranspilerParams):
        parts = Transpiler.transpile(params.but_with(asl=params.asl[0]))

        # need to add '*' to make it a pointer
        def amend(part : str):
            match = re.match(r"(\w+) \w+", part)
            if match:
                return part.replace(match.group(1), match.group(1) + "*")
            return part

        return [amend(part) for part in parts]
            
                



    def seq_(self, params : TranspilerParams):
        parts = []
        for child in params.asl:
            parts += Transpiler.transpile(params.but_with(asl=child)) + [";\n"]
         
        return parts

    def let_(self, params : TranspilerParams):
        if isinstance(params.asl[0], CLRList):
            return Transpiler.transpile(params.but_with(asl=params.asl[0]))

        obj: AbstractObject = params.asl.data
        type_name = SeerFunctions.global_name_for_type(obj.type, obj.mod)

        return [f"{type_name} {obj.name} = {params.asl[1].value}"]

    def return_(self, params : TranspilerParams):
        return ["return"]

    def ref_(self, params : TranspilerParams):
        prefix = "*" if params.asl.data.is_ret else ""
        return [prefix, params.asl[0].value]

    def equals_(self, params : TranspilerParams):
        # special case if we are assigning from a function; else it is trivial
        if isinstance(params.asl[1], CLRList) and params.asl[1].type == "call":
            parts = []
            parts += Transpiler.transpile(params.but_with(asl=params.asl[1]))

            # remove end ')'
            parts = parts[:-1]

            parts.append(", ")
            parts.append("&")
            parts += Transpiler.transpile(params.but_with(asl=params.asl[0]))
            parts.append(")")
            return parts


        else:
            binary_op_fn = SeerFunctions.binary_op(self, "=")
            return binary_op_fn(params)
    
    def binary_op(self, op : str):
        def op_fn(params : TranspilerParams):
            parts = []
            parts += (Transpiler.transpile(params.but_with(asl=params.asl[0])) 
                + [f" {op} "]
                + Transpiler.transpile(params.but_with(asl=params.asl[1])))

            return parts
        
        return op_fn

    def prod_type_(self, params : TranspilerParams):
        parts = Transpiler.transpile(params.but_with(asl=params.asl[0]))
        for child in params.asl[1:]:
            parts += [", "] + Transpiler.transpile(params.but_with(asl=child))
        
        return parts

    def call_(self, params : TranspilerParams):
        name = params.asl[0][0].value
        if name == "print":
            parts = ["printf("] + Transpiler.transpile(params.but_with(asl=params.asl[1])) + [")"]
            return parts

        obj: AbstractObject = params.asl.data
        prefix = Transpiler.get_mod_prefix(obj.mod)
        full_name = prefix + obj.name 

        parts = [full_name, "("] + Transpiler.transpile(params.but_with(asl=params.asl[1])) + [")"]
        return parts

    def params_(self, params : TranspilerParams):
        if len(params.asl) == 0:
            return []

        parts = Transpiler.transpile(params.but_with(asl=params.asl[0]))
        if len(params.asl) == 1:
            return parts

        for child in params.asl[1:]:
            parts += [", "] + Transpiler.transpile(params.but_with(asl=child))

        return parts
            