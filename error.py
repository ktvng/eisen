class Raise():
    @classmethod
    def error(cls, msg):
        print("Error:", msg)
 
        # TODO: gracefully
        exit(1)

    @classmethod
    def notice(cls, msg):
        print("Note:", msg)
        
    @classmethod
    def code_error(cls, msg):
        print("Code Error:", msg)
        exit(1)