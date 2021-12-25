from alpaca.compiler._object import Object

class Stub(Object):
    def __init__(self, type : str, name="", is_initialized=True):
        self._tag_value = None
        super().__init__(None, type, name, is_initialized)

    def set_tag_value(self, val : str):
        self._tag_value = val 

    def get_tag_value(self):
        return self._tag_value
