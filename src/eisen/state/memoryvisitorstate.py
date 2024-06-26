from __future__ import annotations

import uuid
from alpaca.concepts import Context, Type

from eisen.state.state_postinstancevisitor import State_PostInstanceVisitor
from eisen.validation.validate import Validate
from eisen.trace.entity import Entity, Angel, Trait
from eisen.trace.shadow import Shadow, Personality
from eisen.trace.memory import Memory, Impression, MemorableSet
from eisen.trace.lval import Lval
from alpaca.clr import AST
from alpaca.concepts import Context, Module
from alpaca.concepts import AbstractException

class MemoryVisitorState(State_PostInstanceVisitor):
    def __init__(self, **kwargs):
        self._init(**kwargs)

    # note: updated_epoch_uids are outside the context but updated inside it
    def but_with(self,
            ast: AST = None,
            context: Context = None,
            function_base_context = None,
            mod: Module = None,
            exceptions: list[AbstractException] = None,
            depth: int = None,
            rets: list[Entity] = None,
            args: list[Entity] = None,
            angels: list[Angel] = None,
            function_parameters: list[Shadow] = None,
            ) -> MemoryVisitorState:

        return self._but_with(
            ast=ast,
            context=context,
            function_base_context=function_base_context,
            mod=mod,
            exceptions=exceptions,
            depth=depth,
            rets=rets,
            args=args,
            angels=angels,
            function_parameters=function_parameters,
            )

    @staticmethod
    def create_from_basestate(state: State_PostInstanceVisitor) -> MemoryVisitorState:
        """
        Create a new instance of MemoryVisitorState from any descendant of State_PostInstanceVisitor

        :param state: The State_PostInstanceVisitor instance
        :type state: State_PostInstanceVisitor
        :return: A instance of MemoryVisitorState
        :rtype: MemoryVisitorState
        """
        return MemoryVisitorState(**state._get(), depth=0,
                                  function_base_context=None,
                                  rets=None, args=None, angels=None,
                                  function_parameters=None)

    def get_depth(self) -> int:
        """
        Return the depth of the current state. Entering a nested block context increases
        the depth by 1.
        """
        return self.depth

    def get_function_base_context(self) -> Context:
        return self.function_base_context

    def add_memory(self, name: str, value: Memory):
        self.get_context().add_obj("memory", name, value)

    def update_memory_to_latest(self, name: str):
        """
        Ensure that the memory referenced by [name] refers to the lastest shadows for all of its
        impressions.
        """
        memory = self.get_memory(name)
        self.add_memory(name, memory.update_to_latest(self))


    def get_memory(self, name: str) -> Memory:
        return self.get_context().get_obj("memory", name)

    def get_memories(self) -> dict[str, Memory]:
        return self.get_context().containers["memory"]

    def get_function_parameters(self) -> list[Shadow]:
        return self.function_parameters

    def add_shadow(self, value: Shadow):
        value.validate_dependencies_outlive_self(self)
        value = value.restore_to_healthy()
        self.get_context().add_obj("shadow", value.entity.uid, value)
        return value


    def get_shadow(self, entity_or_uid: Entity | uuid.UUID) -> Shadow:
        match entity_or_uid:
            case Entity(): return self.get_context().get_obj("shadow", entity_or_uid.uid)
            case uuid.UUID(): return self.get_context().get_obj("shadow", entity_or_uid)

    def get_shadows(self) -> dict[uuid.UUID, Shadow]:
        return self.get_context().containers["shadow"]

    def add_entity(self, name: str, value: Entity):
        self.get_context().add_obj("entity", name, value)

    def get_entity(self, name: str) -> Entity:
        return self.get_context().get_obj("entity", name)

    def get_local_entities(self) -> list[Entity]:
        return self.get_context().containers["entity"].values()

    def get_local_memories(self) -> list[Memory]:
        return self.get_context().containers["memory"].values()

    def get_ret_entities(self) -> list[Entity]:
        return self.rets

    def get_arg_entities(self) -> list[Entity]:
        return self.args

    def update_lvals(self, lvals: list[Lval], rvals: list[Memory]):
        for lval, rval in zip(lvals, rvals):
            self._update_lval(lval, rval)

    def _update_lval_shadow(self, lval: Lval, shadow: Shadow):
        """
        This is the case for code where we construct a new object:

        let x = obj()
        """
        if len(lval.memory.impressions) != 1:
            raise Exception("expected length 1?!")

        for impression in lval.memory.impressions:
            shadow = self.update_source_of_impression(impression, with_shadow=shadow, trait=lval.trait)
            self.update_memory_to_latest(lval.name)

    def _update_lval_attribute(self, lval: Lval, memory: Memory):
        """
        This is the case where we are updating an attribute:

        x.y = z
        """
        for impression in lval.memory.impressions:
            self.update_personality(
                uid=impression.shadow.entity.uid,
                other_personality=Personality({ lval.trait: memory.for_entanglement(impression.entanglement) }),
                root=impression.root)

    def _init_lval_attribute(self, lval: Lval, shadow: Shadow):
        """
        This is the case where we are creating the attribute. We can't use _update_lval_shadow
        because there is no associated memory.

        self.y = z
        """
        for impression in lval.memory.impressions:
            self.update_source_of_impression(impression, with_shadow=shadow, trait=lval.trait)

    def _update_lval_variable(self, lval: Lval, memory: Memory):
        """
        This is the case where we are updating a variable:

        x = y
        """
        memory = self.get_memory(lval.name).update_with(memory)
        if Validate.dependency_outlives_memory(self, memory).failed():
            memory = memory.restore_to_healthy()
        self.add_memory(lval.name, memory)

    def _update_lval(self, lval: Lval, memory_or_shadow: Memory | Shadow):
        # TODO: this is hacky to allow us to create a shadow for an lval that is
        # a let object
        match memory_or_shadow, lval.trait:
            case Shadow(), Trait(value = ""): self._update_lval_shadow(lval, memory_or_shadow)
            case Shadow(), _: self._init_lval_attribute(lval, memory_or_shadow)
            case Memory(), Trait(value = ""): self._update_lval_variable(lval, memory_or_shadow)
            case Memory(), _: self._update_lval_attribute(lval, memory_or_shadow)

    def update_source_of_impression(self, impression: Impression, with_shadow: Shadow, trait: Trait = Trait()) -> Shadow:
        new_shadow = self.get_shadow(impression.shadow.entity)\
            .update_with(with_shadow, impression.root.join(trait), self.get_depth())
        self.add_shadow(new_shadow)
        return new_shadow

    def add_trait(self, shadow: Shadow, trait: Trait, memory: Memory):
        other_personality = Personality( { trait: memory })
        new_shadow = shadow.update_personality(other_personality, root=Trait())
        self.add_shadow(new_shadow)

    def update_personality(self, uid: uuid.UUID, other_personality: Personality, root=Trait()):
        original_shadow = self.get_shadow(uid)
        new_shadow = original_shadow.update_personality(other_personality, root)
        self.add_shadow(new_shadow)

    def _recognize_entity(self, entity: Entity) -> Shadow:
        self.add_entity(entity.name, entity)
        shadow = Shadow(entity=entity)
        self.add_shadow(shadow)
        return shadow

    def create_new_entity(self, name: str, type: Type) -> Entity:
        entity = Entity(name, self.get_depth(), type)
        shadow = self._recognize_entity(entity)
        self.add_memory(entity.name, Memory(
            name=name,
            rewrites=True,
            impressions=MemorableSet.create_over(
                Impression(shadow=shadow,
                           root=Trait())),
            depth=self.get_depth()))
        return entity

    def create_new_angel_memory(self, trait: Trait, entity: Entity) -> Memory:
        angel = Angel(trait=trait, entity=entity)
        self.angels.append(angel)
        angel_shadow = self.but_with(context=self.get_function_base_context())._recognize_entity(angel)
        return Memory(
            rewrites=True,
            impressions=MemorableSet.create_over(Impression(
                shadow=angel_shadow,
                root=Trait())),
            depth=self.get_depth())
