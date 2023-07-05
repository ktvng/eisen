from __future__ import annotations
from alpaca.config import Config
from alpaca.clr import AST, ASTElements
from alpaca.parser import CommonBuilder

class Builder(CommonBuilder):
    @CommonBuilder.for_procedure("nothing")
    def convert_decl_(
            fn,
            config: Config,
            components: ASTElements,
            name: str,
            *args) -> ASTElements:
        return []
