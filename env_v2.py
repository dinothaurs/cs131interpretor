class EnvironmentManager:
    def __init__(self):
        self.scopes = [{}] 

    def push_scope(self):
        self.scopes.append({})

    def pop_scope(self):
        if self.scopes:
            return self.scopes.pop()

    def set_variable(self, var, val):
        if not self.scopes:
            self.push_scope()
        #assign to top
        self.scopes[-1][var] = val

    def get_variable(self, var):
        print("looking for barable", var)
        for scope in reversed(self.scopes):
            if var in scope:
                print("found", var, scope[var])
                return scope[var]
        return None  
    
    def get_variable_in_scope(self, var):
        print("looking for barable", var)
        for x in self.scopes[-1]:
            if x == var:
                print("found", var)
                return self.scopes[-1][x]
        return None
    
    def get_scope(self):
        #top scope
        return self.scopes[-1]
    
    #for assigning to fix scoping issue
    def update(self, inner_scope):
        current = self.get_scope()
        for var, val in inner_scope.items():
            current[var] = val

    #check
    def is_variable_defined(self, var):
        for scope in self.scopes:
            if var in scope:
                return True
        return False
    
    def find_scope(self, var):
        for scope in self.scopes:
            if var in scope:
                return scope
        return None
    
    def change_var(self, scope, var, val):
        scope[var] = val
    
    def is_variable_in_scope(self, var):
        if var in self.scopes[-1]:
            return True
        return False
    
    #logic; so if variable defined(we check every single scope), then if it is alrdy defined we change it
    #if not in any scope thennn we do it in top most scope yes




