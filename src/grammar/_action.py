class Action():
    def __init__(self, type : str, value : str = ""):
        self.type = type
        self.value = value

    def __str__(self):
        return f"{self.type} {self.value}"