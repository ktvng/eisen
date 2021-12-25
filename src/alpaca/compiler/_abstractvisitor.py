from alpaca.compiler._exceptions import Exceptions

class AbstractVisitor():
    build_map = {}
    _encountered_fatal_exception = False

    @classmethod
    def new_global_context(cls, module):
        pass

    @classmethod
    def exception_callback(cls, exception : Exceptions.AbstractException):
        pass

    @classmethod
    def init(cls, text):
        pass

    @classmethod
    def finally_handle_exceptions(cls):
        pass

    pass
