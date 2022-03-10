from __future__ import annotations

from alpaca.config import Config
from alpaca.asts import CLRList
from alpaca.validator._validator import Validator

def run(config : Config, asl : CLRList, fns : Typing.Any, txt : str):
    return Validator.run(config, asl, fns, txt)