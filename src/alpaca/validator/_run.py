from __future__ import annotations

from alpaca.validator._validator import Validator

def run(indexer_function, validation_function, params: Validator.Params):
    indexer_function.apply(params)
    validation_function.apply(params)
    return params.mod