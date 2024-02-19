from __future__ import annotations

from alpaca.concepts import (TypeFactory2, TypeManifest,
                             NovelType, VoidType, NilType, FunctionType, TupleType, StructType,
                             TraitType, Corpus, TypeDeclaration)

from eisen.common.binding import Binding

class NewTypeFactory:
    classes = {
        "novel": NovelType,
        "struct": StructType,
        "trait": TraitType,
        "nil": NilType,
        "void": VoidType,
        "tuple": TupleType,
        "function": FunctionType,
        "declaration": TypeDeclaration,
        "manifest": TypeManifest,
    }

    @staticmethod
    def get(corpus: Corpus) -> TypeFactory2:
        return TypeFactory2(corpus,
                            NewTypeFactory.classes)
