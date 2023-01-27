from __future__ import annotations

class AbstractParams:
    def __init__(self, **kwargs):
        self._attrs = []
        for key, val in kwargs.items():
            self._attrs.append(key)
            self.__setattr__(key, val)

    def _init(self, **kwargs):
        self._attrs = []
        for key, val in kwargs.items():
            self._attrs.append(key)
            self.__setattr__(key, val)

    def _but_with(self, **kwargs) -> AbstractParams:
        filtered_kwargs = {}
        for k, v in kwargs.items():
            if k in self._attrs and v is not None:
                filtered_kwargs[k] = v
        updated_attrs = { **self.__dict__, **filtered_kwargs}
        del updated_attrs["_attrs"]
        return type(self)(**updated_attrs)

    def _get(self) -> dict:
        kwargs = {}
        for attr in self._attrs:
            kwargs[attr] = getattr(self, attr)

        return kwargs
