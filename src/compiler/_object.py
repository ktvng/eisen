class Object():
    def __init__(self, ir_obj, type : str, name="", is_initialized=True):
        self._ir_obj = ir_obj
        self.type = type
        self.name = name
        self.is_initialized = is_initialized

    def is_callable(self):
        return self.is_function()

    def is_function(self):
        return ") -> (" in self.type 

    def is_variable(self):
        return not self.is_function()

    def get_ir(self):
        return self._ir_obj

    def get_tag_value(self):
        return self._ir_obj
    
    def get_function_io(self):
        stripstr = lambda x : x.strip()
        params_str, return_str = list(map(stripstr, self.type.split("->")))
        params_str = params_str[1:-1]
        return_str = return_str[1:-1]

        params = list(map(stripstr, params_str.split(",")))
        returns = list(map(stripstr, return_str.split(",")))

        return params, returns

    def matches_type(self, type : str) -> bool:
        return self.type == type

class Stub(Object):
    def __init__(self, type : str, name="", is_initialized=True):
        self._tag_value = None
        super().__init__(None, type, name, is_initialized)

    def set_tag_value(self, val : str):
        self._tag_value = val 

    def get_tag_value(self):
        return self._tag_value
