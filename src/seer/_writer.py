from __future__ import annotations

from alpaca.clr import CLRList, CLRToken
from alpaca.utils import Wrangler

from seer._common import asls_of_type

class SeerWriter(Wrangler):
    def run(self, asl: CLRList) -> str:
        parts = self.apply(asl)
        raw_text = "".join(parts)
        return SeerWriter.indent(raw_text)

    @classmethod
    def indent(cls, txt: str) -> str:
        indent = "    ";
        level = 0

        parts = txt.split("\n")
        formatted_txt = ""
        for part in parts:
            level -= part.count('}')
            formatted_txt += indent*level + part + "\n"
            level += part.count('{')

        return formatted_txt


    def apply(self, asl: CLRList) -> list[str]:
        return self._apply([asl], [asl])

    @Wrangler.covers(lambda x: isinstance(x, CLRToken))
    def token_(fn, asl: CLRToken):
        return [asl.value]

    @Wrangler.covers(asls_of_type("start"))
    def start_(fn, asl: CLRList):
        parts = []
        for child in asl:
            parts += fn.apply(child) + ["\n"]
        return parts

    @Wrangler.covers(asls_of_type("struct"))
    def struct_(fn, asl: CLRList):
        parts = ["struct ", *fn.apply(asl.first()), " {\n"]
        for child in asl[1:]:
            parts += fn.apply(child) + ["\n"]
        return parts + ["}\n"]

    @Wrangler.covers(asls_of_type("mod"))
    def mod_(fn, asl: CLRList):
        parts = ["mod ",
            *fn.apply(asl.first()),
            " {\n"]
        for child in asl[1:]:
            parts += fn.apply(child) + ["\n"]
        parts += ["}\n"]
        return parts
 
    @Wrangler.covers(asls_of_type(":"))
    def colon_(fn, asl: CLRList):
        return [*fn.apply(asl.first()), 
            ": ",
            *fn.apply(asl.second())]
 
    @Wrangler.covers(asls_of_type("create"))
    def create_(fn, asl: CLRList):
        return ["create(",
            *fn.apply(asl.first()),
            ") -> ",
            *fn.apply(asl.second()),
            *fn.apply(asl.third())]

    @Wrangler.covers(asls_of_type("type", "fn_type_in", "args", "rets", "fn_type_out", "ref", "fn"))
    def pass_(fn, asl: CLRList):
        if not asl:
            return []
        return fn.apply(asl.first())
 
    @Wrangler.covers(asls_of_type("prod_type", "params"))
    def prod_type(fn, asl: CLRList):
        parts = []
        if asl:
            parts += fn.apply(asl.first())
        for child in asl[1:]:
            parts += [", ", *fn.apply(child)]
        return parts
 
    @Wrangler.covers(asls_of_type("def"))
    def def_(fn, asl: CLRList):
        return ["fn ",
            *fn.apply(asl.first()),
            "("
            *fn.apply(asl.second()),
            ") -> ",
            *fn.apply(asl.third()),
            *fn.apply(asl[-1])]
    
    @Wrangler.covers(asls_of_type("fn_type"))
    def fn_type_(fn, asl: CLRList):
        return ["(",
            *fn.apply(asl.first()),
            ") -> ",
            *fn.apply(asl.second())]
    
    @Wrangler.covers(asls_of_type("ilet"))
    def ilet(fn, asl: CLRList):
        return ["let ", *fn.apply(asl.first()), " = ", *fn.apply(asl.second())]

    @Wrangler.covers(asls_of_type("let"))
    def let_(fn, asl: CLRList):
        return ["let ", *fn.apply(asl.first())]
 
    @Wrangler.covers(asls_of_type("while"))
    def while_(fn, asl: CLRList):
        return ["while ", *fn.apply(asl.first())]
 
    @Wrangler.covers(asls_of_type("seq"))
    def seq_(fn, asl: CLRList):
        parts = []
        for child in asl:
            parts += fn.apply(child) + ["\n"]
        return ["{\n", *parts, "}\n"]
 
    @Wrangler.covers(asls_of_type("cond"))
    def cond_(fn, asl: CLRList):
        return ["(", *fn.apply(asl.first()), ") ", *fn.apply(asl.second())]
      
    @Wrangler.covers(asls_of_type(["<", ">", "<=", ">=", "+", "-", "/", "*", "+=", "=", "==", ".", "::"]))
    def bin_op_(fn, asl: CLRList):
        if asl.type in [".", "::"]:
            operator = asl.type
        else:
            operator = f" {asl.type} "
        return [*fn.apply(asl.first()), operator, *fn.apply(asl.second())]
 
    @Wrangler.covers(asls_of_type("call"))
    def call_(fn, asl: CLRList):
        return [*fn.apply(asl.first()), "(", *fn.apply(asl.second()), ")"]
    
    # TODO: need to work with elseif
    @Wrangler.covers(asls_of_type("if"))
    def if_(fn, asl: CLRList):
        return ["if ", *fn.apply(asl.first())]

    @Wrangler.covers(asls_of_type("return"))
    def return_(fn, asl: CLRList):
        return ["return"]
  