from __future__ import annotations
import re
from sys import base_prefix

from alpaca.config import Config
from alpaca.asts import CLRList, CLRToken

from seer._validator import AbstractModule

from error import Raise

class TranspilerFunctions:
    pass

class TranspilerParams():
    attrs = ['config', 'asl', 'functions', 'mod_prefix', 'mod']

    def __init__(self,
            config : Config,
            asl : CLRList,
            functions : dict,
            mod_prefix : str,
            mod : AbstractModule):

        self.config = config
        self.asl = asl
        self.functions = functions
        self.mod_prefix = mod_prefix
        self.mod = mod


    def given(self,
            config : Config = None,
            asl : CLRList = None,
            functions : dict = None,
            mod_prefix : str = None,
            mod : AbstractModule = None):

        new_params = TranspilerParams.new_from(self)
        if config is not None:
            new_params.config = config
        if asl is not None:
            new_params.asl = asl
        if functions is not None:
            new_params.functions = functions
        if mod_prefix is not None:
            new_params.mod_prefix = mod_prefix
        if mod is not None:
            new_params.mod = mod
        
        return new_params

    @classmethod
    def new_from(cls, params : TranspilerParams, overrides : dict = {}) -> TranspilerParams:
        new_params = TranspilerParams(
            params.config,
            params.asl,
            params.functions,
            params.mod_prefix,
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
        params = TranspilerParams(config, asl, functions, Transpiler.base_prefix, mod)
        parts = Transpiler.transpile(params)
        code = Transpiler._postformat(parts)
        print("="*80)
        print(code)
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
        return "void main() {\n  " + Transpiler.base_prefix + "main();\n}\n"


        
class SeerFunctions(TranspilerFunctions):
    @classmethod
    def global_name(cls, name : str, params : TranspilerParams):
        return params.mod_prefix + name

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
            "=": self.binary_op("="),
            "ref": self.ref_,
            "+": self.binary_op("+"),
            "rets": self.rets_,
            "prod_type": self.prod_type_,
            "call": self.call_,
            "params": self.params_,
        }

    def pass_through_(self, params : TranspilerParams):
        parts = []
        for child in params.asl:
            parts += Transpiler.transpile(params.given(asl=child))

        return parts

    def mod_(self, params : TranspilerParams):
        name = params.asl[0].value
        new_prefix = params.mod_prefix + name + "_"
        parts = []
        for child in params.asl[1:]:
            parts += Transpiler.transpile(params.given(asl=child, mod_prefix=new_prefix))

        return parts

    def struct_(self, params : TranspilerParams):
        name = params.asl[0].value
        parts = [f"struct {SeerFunctions.global_name(name, params)}", " {\n"]
        for child in params.asl[1:]:
            parts += Transpiler.transpile(params.given(asl=child)) + [";\n"]
        
        parts.append("};\n")
        return parts

    def colon_(self, params : TranspilerParams):
        name = params.asl[0].value
        type = params.asl[1][0].value
        return [f"{type} {name}"]

    def def_(self, params : TranspilerParams):
        name = params.asl[0].value
        parts = [f"void {SeerFunctions.global_name(name, params)}(/*args*/ "]

        # args
        parts += Transpiler.transpile(params.given(asl=params.asl[1])) 

        # rets
        if len(params.asl) == 4:
            parts += [", /*rets*/ "] + Transpiler.transpile(params.given(asl=params.asl[2]))
        
        parts.append(") {\n")

        # seq
        parts += Transpiler.transpile(params.given(asl=params.asl[-1])) 
        parts.append("}\n")
        return parts

    def args_(self, params : TranspilerParams):
        if len(params.asl) == 0:
            return []

        return Transpiler.transpile(params.given(asl=params.asl[0]))

    def rets_(self, params : TranspilerParams):
        parts = Transpiler.transpile(params.given(asl=params.asl[0]))

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
            parts += Transpiler.transpile(params.given(asl=child)) + [";\n"]
         
        return parts

    def let_(self, params : TranspilerParams):
        if isinstance(params.asl[0], CLRList):
            return Transpiler.transpile(params.given(asl=params.asl[0]))
        name = params.asl[0].value
        # TODO make good
        type = params.asl[1].type

        return [f"{type} {name} = {params.asl[1].value}"]

    def return_(self, params : TranspilerParams):
        return ["return"]

    def ref_(self, params : TranspilerParams):
        return [params.asl[0].value]
    
    def binary_op(self, op : str):
        def op_fn(params : TranspilerParams):
            parts = []
            parts += (Transpiler.transpile(params.given(asl=params.asl[0])) 
                + [f" {op} "]
                + Transpiler.transpile(params.given(asl=params.asl[1])))

            return parts
        
        return op_fn

    def prod_type_(self, params : TranspilerParams):
        parts = Transpiler.transpile(params.given(asl=params.asl[0]))
        for child in params.asl[1:]:
            parts += [", "] + Transpiler.transpile(params.given(asl=child))
        
        return parts

    def call_(self, params : TranspilerParams):
        fn_name = params.asl[0][0].value
        if fn_name == "print":
            parts = ["printf("] + Transpiler.transpile(params.given(asl=params.asl[1])) + [")"]
            return parts

        Raise.error("call_ unimplemented")

    def params_(self, params : TranspilerParams):
        if len(params.asl) == 0:
            return []

        parts = Transpiler.transpile(params.given(asl=params.asl[0]))
        if len(params.asl) == 1:
            return parts

        for child in params.asl[1:]:
            parts += [", "] + Transpiler.transpile(params.given(asl=child))

        return parts
            