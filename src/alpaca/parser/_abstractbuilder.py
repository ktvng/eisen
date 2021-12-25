from __future__ import annotations

class AbstractBuilder():
    build_map = {}

    @classmethod
    def build_procedure(cls, build_map, name):
        def _decorator(f):
            build_map[name] = f
            return f

        return _decorator
        
    pass

