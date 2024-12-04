# document that we won't have a return inside the init/update of a for loop

import copy
from enum import Enum

from brewparse import parse_program
from env_v4 import EnvironmentManager, Closure, Exception
from intbase import InterpreterBase, ErrorType
from type_value4 import Type, Value, create_value, get_printable


class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2
    RAISE = 3


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}

    # methods
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)
        self.trace_output = trace_output
        self.__setup_ops()

    # run a program that's provided in a string
    # usese the provided Parser found in brewparse.py to parse the program
    # into an abstract syntax tree (ast)
    def run(self, program):
        ast = parse_program(program)
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()
        val = self.__call_func_aux("main", [])
        if isinstance(val, tuple) and isinstance(val[1], Exception):
            super().error(ErrorType.FAULT_ERROR, "Raise statement must be caught")

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            func_name = func_def.get("name")
            num_params = len(func_def.get("args"))
            if func_name not in self.func_name_to_ast:
                self.func_name_to_ast[func_name] = {}
            self.func_name_to_ast[func_name][num_params] = func_def

    def __get_func_by_name(self, name, num_params):
        if name not in self.func_name_to_ast:
            super().error(ErrorType.NAME_ERROR, f"Function {name} not found")
        candidate_funcs = self.func_name_to_ast[name]
        if num_params not in candidate_funcs:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {name} taking {num_params} params not found",
            )
        return candidate_funcs[num_params]

    def __run_statements(self, statements):
        self.env.push_block()
        for statement in statements:
            if self.trace_output:
                print(statement)
            status, return_val = self.__run_statement(statement)
            if status == ExecStatus.RETURN:
                self.env.pop_block()
                return (status, return_val)
            elif status == ExecStatus.RAISE:
                self.env.pop_block()
                return (status, return_val)

        self.env.pop_block()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __run_statement(self, statement):
        status = ExecStatus.CONTINUE
        return_val = None
        if statement.elem_type == InterpreterBase.FCALL_NODE:
            val = self.__call_func(statement)
            if not isinstance(val, Value) and val[0] == ExecStatus.RAISE:
                status = ExecStatus.RAISE
                return_val = val[1]
        elif statement.elem_type == InterpreterBase.TRY_NODE:
            status, return_val = self.__call_try(statement)
        elif statement.elem_type == InterpreterBase.RAISE_NODE:
            status, return_val = self.__call_raise(statement)
        elif statement.elem_type == InterpreterBase.CATCH_NODE:
            pass
        elif statement.elem_type == "=":
            #TODO MAYBE
            self.__assign(statement)
        elif statement.elem_type == InterpreterBase.VAR_DEF_NODE:
            self.__var_def(statement)
        elif statement.elem_type == InterpreterBase.RETURN_NODE:
            status, return_val = self.__do_return(statement)
        elif statement.elem_type == Interpreter.IF_NODE:
            status, return_val = self.__do_if(statement)
        elif statement.elem_type == Interpreter.FOR_NODE:
            status, return_val = self.__do_for(statement)

        return (status, return_val)

    def __call_try(self, statement):
        self.env.push_block() 
        try:
            status, return_value = self.__run_statements(statement.get("statements"))
            if status == ExecStatus.RAISE:
                raise return_value  
        except Exception as e:
            excep = e.get_excep()
            catchers = statement.get("catchers")
            for catch in catchers:
                catch_type = catch.get("exception_type")
                if excep == catch_type:
                    self.env.push_block()  
                    self.env.create(catch_type, e)
                    status, return_value = self.__run_statements(catch.get("statements"))
                    self.env.pop_block()  
                    if status == ExecStatus.RAISE:  
                        raise return_value
                    break
            else:
                self.env.pop_block()
                return (ExecStatus.RAISE, e)
        self.env.pop_block()  
        return ExecStatus.CONTINUE, Interpreter.NIL_VALUE

    def __call_raise(self, raise_statement):
        exception = raise_statement.get("exception_type")
        value = self.__eval_expr(exception)
        if not isinstance(value.value(), str):
            super().error(ErrorType.TYPE_ERROR, "Raise statement must evaluate to a string")
        exception_instance = Exception(value.value())
        return (ExecStatus.RAISE, exception_instance)

    def __call_func(self, call_node):
        func_name = call_node.get("name")
        actual_args = call_node.get("args")
        return self.__call_func_aux(func_name, actual_args)

    def __call_func_aux(self, func_name, actual_args):
        if func_name == "print":
            try:
                return self.__call_print(actual_args)
            except Exception as e:
                return (ExecStatus.RAISE, e)
        if func_name == "inputi" or func_name == "inputs":
            return self.__call_input(func_name, actual_args)

        func_ast = self.__get_func_by_name(func_name, len(actual_args))
        formal_args = func_ast.get("args")
        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            ) 

        # first evaluate all of the actual parameters and associate them with the formal parameter names
        args = {}
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            # result = copy.copy(self.__eval_expr(actual_ast))
            environment = self.__make_copy(actual_ast)
            # print(expression, " check ", environment)
            result = Closure(actual_ast, environment)
            arg_name = formal_ast.get("name")
            args[arg_name] = result

        # then create the new activation record 
        self.env.push_func()
        # and add the formal arguments to the activation record
        for arg_name, value in args.items():
          self.env.create(arg_name, value)
        status, return_val = self.__run_statements(func_ast.get("statements"))
        if status == ExecStatus.RAISE:
            self.env.pop_func()
            return ExecStatus.RAISE, return_val
        self.env.pop_func()
        return return_val

    def __call_print(self, args):
        output = ""
        for arg in args:
            result = self.__eval_expr(arg)  # result is a Value object
            val = get_printable(result)
            if isinstance(val, Exception):
                # print("value of print", val)
                return (ExecStatus.RAISE, val)
            output = output + val
        super().output(output)
        return Interpreter.NIL_VALUE

    def __call_input(self, name, args):
        if args is not None and len(args) == 1:
            result = self.__eval_expr(args[0])
            super().output(get_printable(result))
        elif args is not None and len(args) > 1:
            super().error(
                ErrorType.NAME_ERROR, "No inputi() function that takes > 1 parameter"
            )
        inp = super().get_input()
        if name == "inputi":
            return Value(Type.INT, int(inp))
        if name == "inputs":
            return Value(Type.STRING, inp)

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        # value_obj = self.__eval_expr(assign_ast.get("expression"))
        expression = assign_ast.get("expression")
        environment = self.__make_copy(expression)
        # print(expression, " check ", environment)
        value_obj = Closure(expression, environment)
        if not self.env.set(var_name, value_obj):
            super().error(
                ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment"
            )

    def __make_copy(self, expr_ast):
        env = {}
        stack = [expr_ast]

        while stack:
            expr = stack.pop()
            if expr.elem_type == InterpreterBase.VAR_NODE:
                var_name = expr.get("name")
                value = self.env.get(var_name)
                if value is not None:
                    env[var_name] = value
            elif expr.elem_type in Interpreter.BIN_OPS:
                stack.append(expr.get("op1"))
                stack.append(expr.get("op2"))
            elif expr.elem_type in [Interpreter.NEG_NODE, Interpreter.NOT_NODE]:
                 stack.append(expr.get("op1"))
            elif expr.elem_type == InterpreterBase.FCALL_NODE:
                for arg in expr.get("args"):
                    stack.append(arg)
        return env
    
    def __var_def(self, var_ast):
        var_name = var_ast.get("name")
        if not self.env.create(var_name, Interpreter.NIL_VALUE):
            super().error(
                ErrorType.NAME_ERROR, f"Duplicate definition for variable {var_name}"
            )

    def __eval_expr(self, expr_ast):
        if expr_ast.elem_type == InterpreterBase.NIL_NODE:
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_NODE:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_NODE:
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_NODE:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.VAR_NODE:
            var_name = expr_ast.get("name")
            val = self.env.get(var_name)
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
            if isinstance(val, Closure):
                return self.__eval_closure(val)
            return val
        if expr_ast.elem_type == InterpreterBase.FCALL_NODE:
            return self.__call_func(expr_ast)
            # return Closure(expr_ast, self.env.environment)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            result =  self.__eval_op(expr_ast)
            return result
        if expr_ast.elem_type == Interpreter.NEG_NODE:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_NODE:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x)

    def __eval_closure(self, closure):
        if closure.is_evaluated():
            return closure.get_val()
        expr, closure_env = closure.get_closure()
        self.env.push_func()
        self.env.environment[-1][0] = closure_env

        try:
            result = self.__eval_expr(expr)
            closure.set_val(result)
        finally:
            self.env.pop_func()
        return result

    def __eval_op(self, arith_ast):
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        #short circuiting
        if isinstance(left_value_obj, tuple) and isinstance(left_value_obj[1], Exception):
            return left_value_obj
        if arith_ast.elem_type == '&&' and left_value_obj.value() == False:
            return Value(Type.BOOL, False)
        if arith_ast.elem_type == '||' and left_value_obj.value() == True:
            return Value(Type.BOOL, True)
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))

        if arith_ast.elem_type == '/' and right_value_obj.value() == 0:
            return (ExecStatus.RAISE, Exception("div0"))
        # if isinstance(left_value_obj, Closure):
        #     left_value_obj = self.__eval_closure(left_value_obj)
        #     # print("left", left_value_obj)
        # if isinstance(right_value_obj, Closure):
        #     right_value_obj = self.__eval_closure(right_value_obj)
        #     # print("right", right_value_obj)

        check = self.__compatible_types(arith_ast.elem_type, left_value_obj, right_value_obj
        )
        if (isinstance(check, tuple) and isinstance(check[1], Exception)):
            return check
        # print("arith check", arith_ast)
        if not check:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {left_value_obj.type()}",
            )
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        val = f(left_value_obj, right_value_obj)
        return val

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!="]:
            return True
        if (isinstance(obj1, tuple) and isinstance(obj1[1], Exception)):
            return obj1
        if (isinstance(obj2, tuple) and isinstance(obj2[1], Exception)):
            return obj2
        return obj1.type() == obj2.type()

    def __eval_unary(self, arith_ast, t, f):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        if value_obj.type() != t:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible type for {arith_ast.elem_type} operation",
            )
        return Value(t, f(value_obj.value()))
    
    def __setup_ops(self):
        self.op_to_lambda = {}
        # set up operations on integers
        self.op_to_lambda[Type.INT] = {}
        self.op_to_lambda[Type.INT]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.INT]["-"] = lambda x, y: Value(
            x.type(), x.value() - y.value()
        )
        self.op_to_lambda[Type.INT]["*"] = lambda x, y: Value(
            x.type(), x.value() * y.value()
        )
        self.op_to_lambda[Type.INT]["/"] = lambda x, y: Value(
            x.type(), x.value() // y.value()
        )
        self.op_to_lambda[Type.INT]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.INT]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )
        self.op_to_lambda[Type.INT]["<"] = lambda x, y: Value(
            Type.BOOL, x.value() < y.value()
        )
        self.op_to_lambda[Type.INT]["<="] = lambda x, y: Value(
            Type.BOOL, x.value() <= y.value()
        )
        self.op_to_lambda[Type.INT][">"] = lambda x, y: Value(
            Type.BOOL, x.value() > y.value()
        )
        self.op_to_lambda[Type.INT][">="] = lambda x, y: Value(
            Type.BOOL, x.value() >= y.value()
        )
        #  set up operations on strings
        self.op_to_lambda[Type.STRING] = {}
        self.op_to_lambda[Type.STRING]["+"] = lambda x, y: Value(
            x.type(), x.value() + y.value()
        )
        self.op_to_lambda[Type.STRING]["=="] = lambda x, y: Value(
            Type.BOOL, x.value() == y.value()
        )
        self.op_to_lambda[Type.STRING]["!="] = lambda x, y: Value(
            Type.BOOL, x.value() != y.value()
        )
        #  set up operations on bools
        self.op_to_lambda[Type.BOOL] = {}
        self.op_to_lambda[Type.BOOL]["&&"] = lambda x, y: Value(
            x.type(), x.value() and y.value()
        )
        self.op_to_lambda[Type.BOOL]["||"] = lambda x, y: Value(
            x.type(), x.value() or y.value()
        )
        self.op_to_lambda[Type.BOOL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.BOOL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

        #  set up operations on nil
        self.op_to_lambda[Type.NIL] = {}
        self.op_to_lambda[Type.NIL]["=="] = lambda x, y: Value(
            Type.BOOL, x.type() == y.type() and x.value() == y.value()
        )
        self.op_to_lambda[Type.NIL]["!="] = lambda x, y: Value(
            Type.BOOL, x.type() != y.type() or x.value() != y.value()
        )

    def __do_if(self, if_ast):
        cond_ast = if_ast.get("condition")
        result = self.__eval_expr(cond_ast)
        # print("condition", result)
        if isinstance(result, tuple) and isinstance(result[1], Exception):
            return (ExecStatus.RAISE, result[1])
        if isinstance(result, Closure):
            result = self.__eval_closure(result)
        if result.type() != Type.BOOL:
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible type for if condition",
            )
        if result.value():
            statements = if_ast.get("statements")
            status, return_val = self.__run_statements(statements)
            return (status, return_val)
        else:
            else_statements = if_ast.get("else_statements")
            if else_statements is not None:
                status, return_val = self.__run_statements(else_statements)
                return (status, return_val)

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_for(self, for_ast):
        init_ast = for_ast.get("init") 
        cond_ast = for_ast.get("condition")
        update_ast = for_ast.get("update") 

        self.__run_statement(init_ast)  # initialize counter variable
        run_for = Interpreter.TRUE_VALUE
        while run_for.value():
            run_for = self.__eval_expr(cond_ast)  # check for-loop condition
            if isinstance(run_for, tuple) and isinstance(run_for[1], Exception):
                return run_for
            if run_for.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for for condition",
                )
            if run_for.value():
                statements = for_ast.get("statements")
                status, return_val = self.__run_statements(statements)
                if status == ExecStatus.RAISE:
                    return status, return_val
                if status == ExecStatus.RETURN:
                    return status, return_val
                self.__run_statement(update_ast)  # update counter variable

        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __do_return(self, return_ast):
        expr_ast = return_ast.get("expression")
        if expr_ast is None:
            return (ExecStatus.RETURN, Interpreter.NIL_VALUE)
        value_obj = copy.copy(self.__eval_expr(expr_ast))
        return (ExecStatus.RETURN, value_obj)
    

# def main():
#     program = """
# func main() {
#   var r;
#   r = "10";
#   raise r;
# }
#     """

#     interpreter = Interpreter()
#     interpreter.run(program)  

# main()

