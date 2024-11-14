class Nil:
    def __bool__(self):
        return False

nil = Nil()