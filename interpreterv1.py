from intbase import InterpreterBase
from intbase import ErrorType
from brewparse import parse_program

class Interpreter(InterpreterBase):
    Map  = dict() #holds variables
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor

    def get_func(self, ast):
        funcs = ast.get('functions')
        # functions = []
        
        for func in funcs:
            if func.elem_type == super().FUNC_NODE and func.get('name') == 'main':
                return func
        
        super().error(ErrorType.NAME_ERROR, "No main()  function was found",)


        
    def run(self, program):
        self.Map.clear()
        ast = parse_program(program)

        function = self.get_func(ast)
        main_func_node = function.get('statements')

        # for statement in main_func_node:
        #     if statement.elem_type == super().VAR_DEF_NODE:
        #         self.Map[statement.get('name')] = None
        
        self.run_func(main_func_node)
        

    def run_func(self, func_node):
        # for each statement_node in func_node.statements:
		# 	run_statement(statement_node)
        for node in func_node:
            self.run_statement(node)


    def do_definition(self, node):
        var_name = node.get('name')
        if var_name in self.Map:
            super().error(ErrorType.NAME_ERROR, f"Variable {var_name} defined more than once",)
        self.Map[var_name] = None


    def do_func_call(self, node):
        #get function either print or inputi
        func = node.get('name')
        #print
        if func == "print":
            args = node.get('args')
            output = ""
            for a in args:
                #if it is " "
                if a.get('val') is not None:
                    value = a.get('val')
                    output += str(value)
                #if its a variable
                elif a.get('name') is not None:
                    var_name = a.get('name')
    
                    if var_name in self.Map:
                        #defined but no value assigned
                        if self.Map[var_name] is None:
                            output += "aloha"
                        else:
                            value = self.Map[var_name]
                            output+=str(value)
                    else:
                        super().error(ErrorType.NAME_ERROR, f"Variable {var_name} is not defined",)
                #if expression
                else:
                    var = self.evaluate_expression(a)
                    output += str(var)
            #print
            super().output(output)
        #if function is inputi, return value
        elif func == "inputi":
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
        else:
            super().error(ErrorType.NAME_ERROR, f"Function {func} has not been defined",)
            
    
    def run_statement(self, statement_node):
        #define a variable
        if statement_node.elem_type == super().VAR_DEF_NODE:
            self.do_definition(statement_node)
        #call a function
        if statement_node.elem_type == super().FCALL_NODE:
            self.do_func_call(statement_node)
        #assign a variable
        if statement_node.elem_type == "=":
            self.do_assignment(statement_node)

    def get_target_variable_name(self, node):
        name = node.get('name')
        return name
    
    def get_expression_node(self, statement_node):
        expression = statement_node.get('expression')
        return expression 

    def evaluate_expression(self, node):
        #+ or -
        if node.elem_type == "+" or node.elem_type == "-":
            op1 = self.evaluate_expression(node.get('op1'))
            op2 = self.evaluate_expression(node.get('op2'))
            # #recursion for if theres another expression inside the expression
            # if(op1.elem_type == '-' or op1.elem_type == '+'):
            #     self.evaluate_expression(op1)
            # elif(op2.elem_type == '-' or op1.elem_type == '+'):
            #     self.evaluate_expression(op2)
            #solve expression 
            if isinstance(op1, str) or isinstance(op2, str):
                super().error(ErrorType.TYPE_ERROR, "Incompatible types for arithmetic operation")
        
            if node.elem_type == "+":
                return op1 + op2
            elif node.elem_type == "-":
                return op1 - op2
        
        #a function
        elif node.elem_type == super().FCALL_NODE:
            return self.do_func_call(node)
        
        #just a value
        elif node.get('val') is not None:
            return node.get('val')
        
        elif node.get('name') is not None:
            var_name = node.get('name')
            if var_name in self.Map:
                return self.Map[var_name]
            else:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} is not defined",)
       
        else:
            super().error(ErrorType.TYPE_ERROR, "Invalid expression",)
        return 0

    def do_assignment(self, statement_node):
        # print(statement_node)
        #get variable name
        # print(statement_node
        target_var_name = self.get_target_variable_name(statement_node)
        #check if variable is alrdy defined
        if target_var_name not in self.Map:
            super().error(ErrorType.NAME_ERROR, f"Variable {target_var_name} has not been defined",)
        #get the expression part
        source_node = self.get_expression_node(statement_node)
        #solve nexpression and return value
        resulting_value = self.evaluate_expression(source_node)
       #assign value to variable
        self.Map[target_var_name] = resulting_value
        
# def main():
#     program = """
#   func main() {
#     var x;
#     x = 5 + 6;
#     x = "bar";
#     x = 3;
#     print(x);
#     print();
# }




# """

#     interpreter = Interpreter()
#     interpreter.run(program)  

# main()