from type_value3 import Value
# The EnvironmentManager class keeps a mapping between each variable name (aka symbol)
# in a brewin program and the Value object, which stores a type, and a value.
class Variable:
    def __init__(self, value, type):
        self.v = Value(type, value)
        self.t = type
    def type(self):
        return self.t
    def value(self):
        return self.v
    
class EnvironmentManager:
    def __init__(self):
        self.environment = []


    # returns a VariableDef object
    def get(self, symbol):
        cur_func_env = self.environment[-1]
        for env in reversed(cur_func_env):
            if symbol in env:
                return env[symbol]

        return None

    def set(self, symbol, value):
        cur_func_env = self.environment[-1]
        for env in reversed(cur_func_env):
            if symbol in env:
                env[symbol] = value
                return True

        return False

    def set_struct(self, symbol, value):
        cur_func_env = self.environment[-1]
        fields = symbol.split('.')
        for env in reversed(cur_func_env):
            if fields[0] in env:
                struct = env[fields[0]]
                struct_values = struct.value()
                if len(fields) == 2:
                    field = fields[1]
                    for i in struct_values:
                        if i == field:
                            struct_values[i] = value
                            return True
                if len(fields) > 2:
                    for field in fields[1:-1]:
                        if field in struct_values:
                            struct_values = struct_values[field].value()
                            # print("value of struct value", struct_values.value())
                    # struct_values = struct_values[fields[-1]]
                    struct_values[fields[-1]] = value
                    return True
        return False
    


    # create a new symbol in the top-most environment, regardless of whether that symbol exists
    # in a lower environment
    def create(self, symbol, value, type):
        cur_func_env = self.environment[-1]
        if symbol in cur_func_env[-1]:   # symbol already defined in current scope
            return False
        cur_func_env[-1][symbol] = Value(type, value)
        return True

    # used when we enter a new function - start with empty dictionary to hold parameters.
    def push_func(self):
        self.environment.append([{}])  # [[...]] -> [[...], [{}]]

    def push_block(self):
        cur_func_env = self.environment[-1]
        cur_func_env.append({})  # [[...],[{....}] -> [[...],[{...}, {}]]

    def pop_block(self):
        cur_func_env = self.environment[-1]
        cur_func_env.pop() 

    # used when we exit a nested block to discard the environment for that block
    def pop_func(self):
        self.environment.pop()