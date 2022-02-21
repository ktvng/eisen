from __future__ import annotations
from alpaca.parser._abstractbuilder import AbstractBuilder
from alpaca.asts import CLRList, CLRRawList, CLRToken
from error import Raise
from alpaca.config import Config

class CommonBuilder2(AbstractBuilder):
    build_map = {}

    def _build_procedure(build_map, name):
        def _decorator(f):
            def pure_f(*args, **kwargs):
                return f(CommonBuilder2, *args, **kwargs)
                
            build_map[name] = pure_f

            return f

        return _decorator

    @classmethod
    def flatten_components(cls, components : list[CLRToken | CLRList | CLRRawList]) -> CLRRawList:
        flattened_components = []
        for comp in components:
            if isinstance(comp, list):
                flattened_components += comp
            else:
                flattened_components.append(comp)

        return flattened_components

    @classmethod
    @_build_procedure(build_map, "build")
    def build(cls,
            config : Config,
            components : CLRRawList, 
            build_name : str, 
            *args) -> CLRRawList:

        flattened_components = CommonBuilder2.flatten_components(components)
        if not flattened_components:
            Raise.code_error("flattened_components must not be empty")

        newCLRList = CLRList(build_name, flattened_components)
        newCLRList.line_number = flattened_components[0].line_number
        return [newCLRList]


    @classmethod
    @_build_procedure(build_map, "pool")
    def pool_(cls, 
            config : Config, 
            components : CLRRawList, 
            *args) -> CLRRawList:

        pass_up_list = []
        for component in components:
            if isinstance(component, list):
                pass_up_list += component
            elif isinstance(component, CLRToken) | isinstance(component, CLRList):
                pass_up_list.append(component)
            else:
                print(type(component))
                Raise.code_error("reverse engineering with pooling must be either CLRRawList, CLRList, or CLRToken")

        return pass_up_list


    @classmethod
    @_build_procedure(build_map, "pass")
    def pass_(cls, 
            config : Config, 
            components : CLRRawList, 
            *args) -> CLRRawList:

        return components


    @classmethod
    @_build_procedure(build_map, "convert")
    def convert_(cls, 
            config : Config, 
            components : CLRRawList, 
            name : str, 
            *args) -> CLRRawList:

        if len(components) != 1:
            Raise.code_error("expects size of 1")

        if isinstance(components[0], CLRList):
            components[0].set_type(name)
        elif isinstance(components[0], CLRToken):
            components = [CLRList(name, components)]
        return components