from __future__ import annotations

import alpaca
from alpaca.clr._clr import CLRList

class parser():
    @classmethod
    def run(cls, txt: str) -> CLRList:
        config = alpaca.config.parser.run("./src/alpaca/assets/types.gm")
        tokens = alpaca.lexer.run(txt, config, callback=None)
        asl = alpaca.parser.run(config, tokens, alpaca.parser.CommonBuilder(), algo="cyk")
        return asl
