from __future__ import annotations

class AbstractParams:
    def __init__(self, **kwargs):
        for key, val in kwargs.items():
            self.__setattr__(key, val)

    def _but_with(self, **kwargs) -> AbstractParams:
        filtered_kwargs = {}
        for k, v in kwargs.items():
            if v is not None:
                filtered_kwargs[k] = v
        # filtered_kwargs = dict({(k, v) for k, v in kwargs.items() if v is not None})
        updated_attrs = { **self.__dict__, **filtered_kwargs}
        return type(self)(**updated_attrs)

