from intbase import InterpreterBase
from intbase import ErrorType
from brewparse import parse_program
from env_v2 import EnvironmentManager
from helper import nil, Nil

class Interpreter(InterpreterBase):
    Map_func = dict() #holds functions
    return_value = False
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor
        self.env_manager = EnvironmentManager()

    def get_func(self, ast):
        funcs = ast.get('functions')
        # functions = []
        #func: name: foo, args: [], return_type: None, statements: [fcall: name: print, args: [string: val: hello world!]]
        #func: name: main, args: [], return_type: None, statements: [fcall: name: foo, args: []]

        #add functions to map
        for func in funcs:
            if func.elem_type == super().FUNC_NODE:
                num_param = len(func.get('args'))
                self.Map_func[func.get('name'), num_param] = func
                # print(func)

        #check for main    
        if ('main', 0) not in self.Map_func:
            super().error(ErrorType.NAME_ERROR, "No main()  function was found",)
        # print(self.Map_func['main'])
        return self.Map_func[('main', 0)]

    def run(self, program):
        self.Map_func.clear()
        ast = parse_program(program)

        function = self.get_func(ast)
        main_func_node = function.get('statements')
        
        self.run_func(main_func_node)

    def run_defined_func(self, node):
        #func: name: main, args: [], return_type: None, statements: [fcall: name: foo, args: [int: val: 5]]
        #get function
        func_name = node.get('name')
        param_num = len(node.get('args'))

        if func_name == "print":
            value = self.run_print(node)
            return value
        #if function is inputi, return value
        elif func_name == "inputi":
            return self.run_inputi(node)
        elif func_name == "inputs":
            return self.run_inputs(node)
        
        if (func_name, param_num) not in self.Map_func:
            super().error(ErrorType.NAME_ERROR, f"Function {func_name} with {param_num} parameters not defined",)
        
        func_node = self.Map_func[func_name, param_num]
        parameters = func_node.get('args')
        #get variables passed in
        variables = node.get('args')

        #create new scope for new func
        self.env_manager.push_scope()

        for var, param in zip(variables, parameters):
            if var.get('val') is not None:
                value = var.get('val')
            else:
                value = self.evaluate_expression(var)
            param_name = param.get('name')
            self.env_manager.set_variable(param_name, value)
            # self.Map[param_name] = value
        
        #run statements
        func_statements = func_node.get('statements')
        for node in func_statements:
            result = self.run_statement(node)
            # if  result == nil:
            #     self.env_manager.pop_scope()
            #     return result
            # in case of return
            if node.elem_type == super().RETURN_NODE:
                self.env_manager.pop_scope()
                return result
            if not result == None:
                self.env_manager.pop_scope()
                return result
        #exit scope when done
        self.env_manager.pop_scope()
        return nil

    def do_definition(self, node):
        var_name = node.get('name')
        #found in current scope
        if self.env_manager.is_variable_in_scope(var_name):
            super().error(ErrorType.NAME_ERROR, f"Variable {var_name} defined more than once",)
        # if var_name in self.Map:
        #     super().error(ErrorType.NAME_ERROR, f"Variable {var_name} defined more than once",)
        self.env_manager.set_variable(var_name, None)
        return nil

    def run_inputi(self, node):
        arg_node = node.get('args')
        print_out = ""
        #get arg list
        if len(arg_node) == 1:
            print_out = arg_node[0].get('val')
            super().output(print_out)
        elif len(arg_node) > 1:
            super().error(ErrorType.NAME_ERROR, f"No inputi() function found that takes > 1 parameter",)
        val = int(super().get_input())
        return val
    
    def run_inputs(self, node):
        arg_node = node.get('args')
        print_out = ""
        if len(arg_node) == 1:
            print_out = arg_node[0].get('val')
            super().output(print_out)
        elif len(arg_node) > 1:
            super().error(ErrorType.NAME_ERROR, f"No inputi() function found that takes > 1 parameter",)
        val = str(super().get_input())
        return val

    def run_print(self, node):
        args = node.get('args')
        output = ""
        for a in args:
            # If it is a function
            if a.elem_type == super().FCALL_NODE:
                #print('fcal')
                value = self.run_defined_func(a)
            elif a.get('val') is not None:
                value = a.get('val')
            # If it's a variable
            elif a.get('name') is not None:
                var_name = a.get('name')
                #TODO: check var
                value = self.env_manager.get_variable(var_name)
            # If it's an expression
            else:
                value = self.evaluate_expression(a)
            # Print the output
            if isinstance(value, bool):
                value = self.convert_bool(value)
            if value is not None:
                output += str(value)
            else:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} is not defined")
        super().output(output)
        return nil
        
    def convert_bool(self, val):
        if val == True:
            value = "true"
        else:
            value = "false"
        return value
    
    def run_func(self, func_node):
        # for each statement_node in func_node.statements:
		# 	run_statement(statement_node)
        for node in func_node:
            value = self.run_statement(node)
            if node.elem_type == super().RETURN_NODE:
                return value
            if not value == None:
                return value
        return nil
    
    def run_if(self, node):
        #<: op1: [var: name: x], op2: [int: val: 0]
        condition = node.get('condition')
        #evaluate condition
        result = self.evaluate_expression(condition)
        if not isinstance(result, bool):
            super().error(ErrorType.TYPE_ERROR, "not a boolean")
        else_statements = node.get('else_statements')
        if result == True:
            #create new scope
            self.env_manager.push_scope()
            #run statements
            statements = node.get('statements')
            val = self.run_func(statements)
            #assign if changed anythingto outer
            self.env_manager.pop_scope()
            return val
        elif result == False:
            else_statements = node.get('else_statements')
            if not else_statements == None:
                val = self.run_func(else_statements)
                self.env_manager.pop_scope()
                return val
        return nil
    
    def run_for(self, node):
        #create scope
        init = node.get('init')
        condition = node.get('condition')
        update = node.get('update')
        statements = node.get('statements')

        self.env_manager.push_scope()
        self.run_statement(init)
        value = nil
        while True:
            result = self.evaluate_expression(condition)
            if not isinstance(result, bool):
                super().error(ErrorType.TYPE_ERROR, "not a boolean")
            if not isinstance(result, bool):
                self.error(ErrorType.TYPE_ERROR, "condition in for-loop is not a bool")
            if not result:
                break
            self.env_manager.push_scope()
            value = self.run_func(statements)
            if not value == nil:
                self.env_manager.pop_scope()
                return value
            self.env_manager.pop_scope()
            self.do_assignment(update)

        self.env_manager.pop_scope()
        return nil

    def run_statement(self, statement_node):
        #define a variable
        if statement_node.elem_type == super().VAR_DEF_NODE:
            self.do_definition(statement_node)
        #call a function
        elif statement_node.elem_type == super().FCALL_NODE:
            val = self.run_defined_func(statement_node)
            if not val == nil:
                return val
        #assign a variable
        elif statement_node.elem_type == "=":
            self.do_assignment(statement_node)
        elif statement_node.elem_type == super().IF_NODE:
            val = self.run_if(statement_node)
            if not val == nil:
                return val
        elif statement_node.elem_type == super().FOR_NODE:
            val = self.run_for(statement_node)
            if not val == nil:
                return val
        elif statement_node.elem_type == super().RETURN_NODE:
            #TODO: different kinds of return
            expression_node = statement_node.get('expression')
            if expression_node == None:
                return None
            if expression_node.elem_type == "fcall":
                value = self.run_defined_func(expression_node)
                return value
            var_name = expression_node.get('name')
            #if variable
            if not expression_node.get('name') == None:
                value = self.env_manager.get_variable(var_name)
                if value is not None:
                    return value
                else:
                    super().error(ErrorType.NAME_ERROR, f"Variable {var_name} is not defined")
            elif not expression_node.get('val') == None:
                value = expression_node.get('val')
                return value
            else:
                value = self.evaluate_expression(expression_node)
                return value

    def get_target_variable_name(self, node):
        name = node.get('name')
        return name
    
    def get_expression_node(self, statement_node):
        expression = statement_node.get('expression')
        return expression 

    def evaluate_add_sub(self, node):
        op1 = self.evaluate_expression(node.get('op1'))
        op2 = self.evaluate_expression(node.get('op2'))
        if node.elem_type == "+" and isinstance(op1, str) and isinstance(op2, str):
            return op1 + op2
        if not isinstance(op1, int) or not isinstance(op2, int) or isinstance(op1, bool) or isinstance(op2, bool):
            super().error(ErrorType.TYPE_ERROR, "Incompatible types for arithmetic operation")
        if node.elem_type == "+":
            return op1 + op2
        elif node.elem_type == "-":
            return op1 - op2
    
    def evaluate_mul_div(self, node):
        op1 = self.evaluate_expression(node.get('op1'))
        op2 = self.evaluate_expression(node.get('op2'))
        
        # mult and division
        if not isinstance(op1, int) or not isinstance(op2, int) or isinstance(op1, bool) or isinstance(op2, bool):
            super().error(ErrorType.TYPE_ERROR, "Incompatible types for arithmetic operation")
        
        if node.elem_type == "*":
            return op1 * op2
        elif node.elem_type == "/":
            return op1 // op2

    def evaluate_expression(self, node):
        #add true or false
        if node.elem_type == super().BOOL_NODE:
            val = node.get('val')
            if val:
                return True
            else:
                return False
        #nil
        elif node.elem_type == super().NIL_NODE:
            return nil
        #+ or -
        elif node.elem_type in ["+", "-"]:
            return self.evaluate_add_sub(node)
        elif node.elem_type in ["*", "/"]:
            return self.evaluate_mul_div(node)
            
        elif node.elem_type == super().NEG_NODE:
            op1 = self.evaluate_expression(node.get('op1'))
            if not isinstance(op1, int):
                super().error(ErrorType.TYPE_ERROR, "Incompatible type for arithmetic operator")
            return -op1
        elif node.elem_type in ["==", "!=", "<", "<=", ">", ">=", "||", "&&"]:
            op1 = self.evaluate_expression(node.get('op1'))
            op2 = self.evaluate_expression(node.get('op2'))
            if isinstance(op1, Nil) or isinstance(op2, Nil):
                if node.elem_type in ["==", "!="]:
                    if node.elem_type == "==":
                        return op1 == op2
                    else:
                        return op1 != op2
                else:
                    super().error(ErrorType.TYPE_ERROR, "cannot use nil")
                    
            if node.elem_type in ["==", "!="]:
                if type(op1) is not type(op2):
                    if node.elem_type == "==":
                        return False
                    else:
                        return True
                else:
                    if node.elem_type == "==":
                        return op1 == op2
                    else:
                        return op1 != op2
            
            if node.elem_type in ["||", "&&"]:
                if not isinstance(op1, bool) or not isinstance(op2, bool):
                    super().error(ErrorType.TYPE_ERROR, "Incompatible type for binary operator")
                if node.elem_type == "||":
                    return bool(op1) or bool(op2)
                else: 
                    return bool(op1) and bool(op2)

            # For comparison operators, ensure both operands are integers or compatible types
            if not isinstance(op1, int) and not isinstance(op2, int):
                super().error(ErrorType.TYPE_ERROR, "Incompatible type for comparison operator")

            if isinstance(op1, bool) or isinstance(op2, bool):
                super().error(ErrorType.TYPE_ERROR, "Incompatible type for comparison operator")

            if node.elem_type == "<":
                return op1 < op2 
            if node.elem_type == "<=":
                return op1 <= op2 
            if node.elem_type == ">":
                return op1 > op2 
            if node.elem_type == ">=":
                return op1 >= op2 

        elif node.elem_type == "!":
            op1 = self.evaluate_expression(node.get('op1'))
            if not isinstance(op1, bool):
                super().error(ErrorType.TYPE_ERROR, "Incompatible types for boolean operation")
            return not op1
        
        #a function
        elif node.elem_type == super().FCALL_NODE:
            return self.run_defined_func(node)
        #just a value
        elif node.get('val') is not None:
            return node.get('val')
        elif node.get('name') is not None:
            var_name = node.get('name')
            val = self.env_manager.get_variable(var_name)
            return val
        else:
            super().error(ErrorType.TYPE_ERROR, "Invalid expression",)
        return nil

    def do_assignment(self, statement_node):
        target_var_name = self.get_target_variable_name(statement_node)
        #check if variable is alrdy defined
        #if not defined in any of scopes, error
        if not self.env_manager.is_variable_defined(target_var_name):
            super().error(ErrorType.NAME_ERROR, f"Variable {target_var_name} has not been defined")
        #get the expression part
        source_node = self.get_expression_node(statement_node)
        #solve nexpression and return value
        resulting_value = self.evaluate_expression(source_node)
        #case where not in current scope
        if not self.env_manager.is_variable_in_scope(target_var_name):
            scope = self.env_manager.find_scope(target_var_name)
            self.env_manager.change_var(scope, target_var_name, resulting_value)
        else:
            self.env_manager.set_variable(target_var_name, resulting_value)
        
        #Case 1: defined outside of if or for scope, find scope, then assign
        #Case 2: defined inside of if or for scope, assign
        return nil
# def main():
#     program = """
# func main() {
#   print(fact(5));
# }

# func fact(n) {
#   if (n <= 1) { return 1; }
#   return n * fact(n-1);
# }


# """

#     interpreter = Interpreter()
#     interpreter.run(program)  

# main()