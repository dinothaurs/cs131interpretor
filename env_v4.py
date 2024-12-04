class Exception(Exception):
    def __init__(self, message):
        self.message = message
    
    def get_excep(self):
        return self.message
# The EnvironmentManager class keeps a mapping between each variable name (aka symbol)
# in a brewin program and the Value object, which stores a type, and a value.
class Closure:
    def __init__(self, expression, environment):
        self.expression = expression
        self.environment = environment 
        self.value = None
        self.evaluated = False
    
    def set_val(self, value):
        self.value = value
        self.evaluated = True

    def get_val(self):
        return self.value

    def is_evaluated(self):
        return self.evaluated
    
    def get_closure(self):
        return self.expression, self.environment
    

class EnvironmentManager:
    def __init__(self):
        self.environment = []

    # returns a VariableDef object
    def get(self, symbol):
        cur_func_env = self.environment[-1]
        for env in reversed(cur_func_env):
            if symbol in env:
                # print(symbol)
                return env[symbol]

        return None

    def set(self, symbol, value):
        cur_func_env = self.environment[-1]
        for env in reversed(cur_func_env):
            if symbol in env:
                env[symbol] = value
                return True

        return False

    # create a new symbol in the top-most environment, regardless of whether that symbol exists
    # in a lower environment
    def create(self, symbol, value):
        cur_func_env = self.environment[-1]
        if symbol in cur_func_env[-1]:   # symbol already defined in current scope
            return False
        cur_func_env[-1][symbol] = value
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