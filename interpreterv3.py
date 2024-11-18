# document that we won't have a return inside the init/update of a for loop

import copy
from enum import Enum

from brewparse import parse_program
from env_v3 import EnvironmentManager
from intbase import InterpreterBase, ErrorType
from type_value3 import Type, Value, TypeCheck, create_value, get_printable



class ExecStatus(Enum):
    CONTINUE = 1
    RETURN = 2


# Main interpreter class
class Interpreter(InterpreterBase):
    # constants
    NIL_VALUE = create_value(InterpreterBase.NIL_DEF)
    TRUE_VALUE = create_value(InterpreterBase.TRUE_DEF)
    BIN_OPS = {"+", "-", "*", "/", "==", "!=", ">", ">=", "<", "<=", "||", "&&"}
    structs = {}
    __TYPES = {"int", "string", "bool", "nil"}

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
        self.__set_up_structs(ast)
        self.__set_up_function_table(ast)
        self.env = EnvironmentManager()
        self.__call_func_aux("main", [])

    def __set_up_structs(self, ast):
        self.structs = {}
        for struct in ast.get('structs'):
            struct_name = struct.get('name')
            struct_dict = {}
            for field in struct.get('fields'):
                field_name = field.get('name')
                field_type = field.get('var_type')
                # print(field_name, field_type)
                val = Value(field_type, field_name)
                struct_dict[field_name] = val
            self.structs[struct_name] = struct_dict

    def __get_struct(self, name):
        if name not in self.structs:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Struct {name} not in structs",
            )
        return self.structs[name]

    def get_struct_field(self, name, field):
        struct = self.__get_struct(name)
        if not field in struct:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Field {field} not in struct {name}",
            )
        return struct[field]

    def __set_up_function_table(self, ast):
        self.func_name_to_ast = {}
        for func_def in ast.get("functions"):
            return_type = func_def.get("return_type")
            if return_type == None:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"{return_type} is None",
                )
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

        self.env.pop_block()
        return (ExecStatus.CONTINUE, Interpreter.NIL_VALUE)

    def __run_statement(self, statement):
        status = ExecStatus.CONTINUE
        return_val = None
        if statement.elem_type == InterpreterBase.FCALL_NODE:
            self.__call_func(statement)
        elif statement.elem_type == "=":
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
    
    def __call_func(self, call_node):
        func_name = call_node.get("name")
        actual_args = call_node.get("args")
        return self.__call_func_aux(func_name, actual_args)

    def __call_func_aux(self, func_name, actual_args):
        if func_name == "print":
            return self.__call_print(actual_args)
        if func_name == "inputi" or func_name == "inputs":
            return self.__call_input(func_name, actual_args)

        func_ast = self.__get_func_by_name(func_name, len(actual_args))
        return_type = func_ast.get('return_type')
        formal_args = func_ast.get("args")
        if len(actual_args) != len(formal_args):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_ast.get('name')} with {len(actual_args)} args not found",
            )
    
        # first evaluate all of the actual parameters and associate them with the formal parameter names
        args = {}
        for formal_ast, actual_ast in zip(formal_args, actual_args):
            result = copy.copy(self.__eval_expr(actual_ast))
            # print("actual parameter", result.type())
            actual_type = result.type()
            arg_name = formal_ast.get("name")
            formal_type = formal_ast.get('var_type')
            if result.type() == Type.INT and formal_type == Type.BOOL:
                result = Value(Type.BOOL, result.value() != 0)
                actual_type = result.type()
            if actual_type == Type.NIL and formal_type in self.structs:
                result = Value(formal_type, super().NIL_NODE)
            elif not actual_type == formal_type:
                super().error(
                    ErrorType.TYPE_ERROR, f"Incompatable types {actual_type} and {formal_type} in parameter passing"
                )
            args[arg_name] = result

        # then create the new activation record 
        self.env.push_func()
        # and add the formal arguments to the activation record
        for arg_name, value in args.items():
          self.env.create(arg_name, value.value(), value.type())
        _, return_val = self.__run_statements(func_ast.get("statements"))
        self.env.pop_func()
        return_val_type = return_val.type()
        # print(return_val_type, return_type)
        if return_type == "void":
            if not return_val_type == super().NIL_NODE:
                super().error(
                    ErrorType.TYPE_ERROR, f"Cannot return type value for void function"
                )
            else:
                return Value(Type.NIL, "void")
        if return_val_type == super().NIL_NODE:
            if return_type == super().INT_NODE:
                return Value(Type.INT, 0)
            elif return_type == super().STRING_NODE:
                return Value(Type.STRING, "")
            elif return_type == super().BOOL_NODE:
                return Value(Type.BOOL, False)
            elif return_type in self.structs:
                return Value(Type.NIL, super().NIL_NODE)
        if return_type == super().BOOL_NODE and return_val_type == super().INT_NODE:
            return_val = self.__coerce_to_bool(return_val)
        elif not return_type == return_val_type and not return_type == "void" :
            super().error(
                ErrorType.TYPE_ERROR, f"Incompatable type for return type: {return_type} and return value type: {return_val_type} in return"
            )
        return return_val

    def __call_print(self, args):
        output = ""
        for arg in args:
            result = self.__eval_expr(arg)  # result is a Value object
            if result.value() == "void":
                super().error(
                    ErrorType.TYPE_ERROR, "Return is void, cannot print"
                )
            if result.type() in self.structs:
                result = result.value()
            output = output + get_printable(result)
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
            val =  Value(Type.INT, int(inp))
            return val
        if name == "inputs":
            return Value(Type.STRING, inp)

    def __get_field(self, var_name):
        fields = var_name.split('.')
        #get from env
        name = self.env.get(fields[0])
        # print("name", name.value())
        if name == None:
            super().error(
                ErrorType.NAME_ERROR, "name {var_name} is not declared"
            )
        if name.type() not in self.structs:
            super().error(
                ErrorType.TYPE_ERROR, "{name} not defined and not a struct type"
            )
        if name.value() == super().NIL_NODE:
            super().error(
                ErrorType.FAULT_ERROR, "value is nil on left of dot"
            )
        if len(fields) == 2:
            #check if field in name
            field = fields[1]
            # print(name.value().value(), name.type())
            if name.type() not in self.structs:
                super().error(
                    ErrorType.TYPE_ERROR, "{name} not defined and not a struct type"
                ) 
            if isinstance(name.value(), Value) and name.value().value() == None:
                super().error(
                    ErrorType.FAULT_ERROR, "not defined yet with new"
                )  
            if field not in name.value():
                super().error(
                    ErrorType.NAME_ERROR, f"{field} not in struct"
                )  
            #the actual struct thats been created alrdy
            struct = name.value()
            field_to_be_assigned = struct.get(field)
            #print("field to be assigned", field_to_be_assigned.value(), field_to_be_assigned.type())
            return field_to_be_assigned
        elif len(fields) > 2:
            for field in fields[1:]:
                if name.type() not in self.structs:
                    super().error(
                        ErrorType.TYPE_ERROR, "{name} not defined and not a struct type"
                    )
                if isinstance(name.value(), Value) and name.value().value() == None:
                    super().error(
                        ErrorType.FAULT_ERROR, "not defined yet with new"
                    ) 
                #get next field
                if field not in name.value():
                    super().error(
                        ErrorType.NAME_ERROR, f"{field} not in struct"
                    ) 
                struct = name.value()
                name = struct.get(field)
            return name
            

    def __assign(self, assign_ast):
        var_name = assign_ast.get("name")
        value_obj = self.__eval_expr(assign_ast.get("expression"))
        # print("return", value_obj)
        # print(assign_ast)
        if '.' in var_name:
            field = self.__get_field(var_name)
            var_type = field.type()
            val_type = value_obj.type()
            # print(value_obj.value())
            # print("val_type", val_type, "var_type", var_type)
            if var_type in self.structs and val_type == Type.NIL:
                pass
            elif val_type == Type.INT and var_type == Type.BOOL:
                value_obj = self.__coerce_to_bool(value_obj)
            elif not val_type == var_type:
                super().error(
                    ErrorType.TYPE_ERROR, f"Incompatable types {var_type} and {val_type} in assignment"
                )
            if not self.env.set_struct(var_name, value_obj):
                super().error(
                    ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment"
                )
        # if isinstance(value_obj, Value):
        #     print("Checked: is value")
        else:
            var = self.env.get(var_name)
            if var == None:
                super().error(
                    ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment"
                )
            var_type = var.type()
            val_type = value_obj.type()
            # print(self.env.get(var_name).value(), value_obj.value(), var_type)
            if var_type in self.structs and val_type == Type.NIL:
                value_obj = Value(var_type, super().NIL_NODE)
            elif var_type == super().BOOL_NODE and val_type == super().INT_NODE:
                # print("attempting to ceorce")
                value_obj = self.__coerce_to_bool(value_obj)
            elif not val_type == var_type:
                super().error(
                    ErrorType.TYPE_ERROR, f"Incompatable types {var_type} and {val_type} in assignment"
                )
            if not self.env.set(var_name, value_obj):
                super().error(
                    ErrorType.NAME_ERROR, f"Undefined variable {var_name} in assignment"
                )
        
    def __var_def(self, var_ast):
        var_name = var_ast.get("name")
        #Variable(name, Value, type)
        type = var_ast.get('var_type')
        if type == Type.INT:
            val = 0
        elif type == Type.STRING:
            val = ""
        elif type == Type.BOOL:
            val = False
        else:
            val = Interpreter.NIL_VALUE
        if not type in self.__TYPES and not type in self.structs:
            super().error(
                ErrorType.TYPE_ERROR, f"Type: {type} not a valid type"
            )
        if not self.env.create(var_name, val, type):
            super().error(
                ErrorType.NAME_ERROR, f"Duplicate definition for variable {var_name}"
            )
    
    def __eval_expr(self, expr_ast):
        # print(expr_ast, expr_ast.elem_type)
        if expr_ast.elem_type == InterpreterBase.NIL_NODE:
            return Interpreter.NIL_VALUE
        if expr_ast.elem_type == InterpreterBase.INT_NODE:
            return Value(Type.INT, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.STRING_NODE:
            return Value(Type.STRING, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.BOOL_NODE:
            return Value(Type.BOOL, expr_ast.get("val"))
        if expr_ast.elem_type == InterpreterBase.VAR_NODE:
            #if dot operator
            if "." in expr_ast.get('name'):
                struct_name = expr_ast.get('name')
                fields = struct_name.split('.')

                name = self.env.get(fields[0])

                #check if struct
                if name.type() not in self.structs:
                    super().error(
                        ErrorType.TYPE_ERROR, f"{fields[0]} not defined or not a struct type"
                    )
                if name.value() == super().NIL_NODE:
                    super().error(
                        ErrorType.FAULT_ERROR, f"Cannot access {fields[0]} because it is nil"
                    )

                cur_struct = name.value()
                for field in fields[1:-1]:
                    # Ensure the current value is a struct
                    # print(cur_struct)
                    if cur_struct == None:
                        super().error(
                            ErrorType.FAULT_ERROR, f"is none"
                        )
                    if not isinstance(cur_struct, dict):
                        super().error(
                            ErrorType.TYPE_ERROR, f"{field} is not a valid field of a struct"
                        )
                    if field not in cur_struct:
                        super().error(
                            ErrorType.FAULT_ERROR, f"{field} not found in struct"
                        )

                    # Move to the next field
                    cur_struct = cur_struct[field].value()

                    # If the value is nil, raise a fault error
                    if cur_struct == super().NIL_NODE:
                        super().error(
                            ErrorType.NAME_ERROR, f"Cannot access {field} because it is nil"
                        )
                # Get the final field and its value/type
                final_field = fields[-1]
                if cur_struct == None:
                    super().error(
                        ErrorType.FAULT_ERROR, f"is none"
                    )
                if not isinstance(cur_struct, dict):
                    super().error(
                        ErrorType.FAULT_ERROR, f"{fields[-1]} is not a valid field of a struct"
                    )
                if final_field not in cur_struct:
                    super().error(
                        ErrorType.NAME_ERROR, f"{final_field} not found in struct"
                    )

                val = cur_struct[final_field].value()
                typ = cur_struct[final_field].type()
                return Value(typ, val)
            
            var_name = expr_ast.get("name")
            val = self.env.get(var_name)
            if val is None:
                super().error(ErrorType.NAME_ERROR, f"Variable {var_name} not found")
            if val.type() in self.structs:
                # print("value in variable", val.value(), var_name, val)
                return Value(val.type(), val.value())
            # print("Variable: ", val)
            return val
        if expr_ast.elem_type == InterpreterBase.FCALL_NODE:
            return self.__call_func(expr_ast)
        if expr_ast.elem_type in Interpreter.BIN_OPS:
            return self.__eval_op(expr_ast)
        if expr_ast.elem_type == Interpreter.NEG_NODE:
            return self.__eval_unary(expr_ast, Type.INT, lambda x: -1 * x)
        if expr_ast.elem_type == Interpreter.NOT_NODE:
            return self.__eval_unary(expr_ast, Type.BOOL, lambda x: not x)
        if expr_ast.elem_type == InterpreterBase.NEW_NODE:
            # print("exp", expr_ast)
            #check sstruct validity
            struct_type = expr_ast.get('var_type')
            if not struct_type in self.structs:
                super().error(ErrorType.TYPE_ERROR, f"Struct type {struct_type} not found")
            struct_def = self.structs[struct_type]
            new_struct = {}
            for obj_name, value in struct_def.items():
                type = value.type()
                name = value.value()
                # print("name", obj_name)
                # print("type", type)
                if type == Type.INT:
                    new_struct[name] = Value(Type.INT, 0)
                elif type == Type.STRING:
                    new_struct[name] = Value(Type.STRING, "")
                elif type == Type.BOOL:
                    new_struct[name] = Value(Type.BOOL, False)
                elif type in self.structs:
                    new_struct[name] = Value(type, super().NIL_NODE)
                else:
                    super().error(
                        ErrorType.TYPE_ERROR, f"Invalid field type {type}"
                    )
            return Value(struct_type, new_struct)
        if expr_ast.elem_tyoe in self.structs:
            print("struct")
        
        
    def __coerce_to_bool(self, value_obj):
        if value_obj.type() == Type.BOOL:
            return value_obj
        elif value_obj.type() == Type.INT:
            # print("Test", value_obj.value() != 0)
            return Value(Type.BOOL, value_obj.value() != 0)
        else:
            super().error(ErrorType.TYPE_ERROR, f"Cannot coerce")
        
    def __eval_op(self, arith_ast):
        # print(arith_ast)
        left_value_obj = self.__eval_expr(arith_ast.get("op1"))
        right_value_obj = self.__eval_expr(arith_ast.get("op2"))
        # print("left", left_value_obj.value(), left_value_obj.type())
        # print("right", right_value_obj.value(), right_value_obj.type())
       
        if left_value_obj.value() == "void" or right_value_obj.value() == "void":
            super().error(
                ErrorType.TYPE_ERROR,
                f"Using return in expression",
            )

        # print(left_value_obj.type(), right_value_obj.type())
        if not left_value_obj.type() == right_value_obj.type() and (left_value_obj.type() in self.structs and right_value_obj.type() in self.structs):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Cannot compare two diff structs",
            )

        if (
            left_value_obj.type() == super().INT_NODE and right_value_obj.type() == super().BOOL_NODE) or (
            left_value_obj.type() == super().BOOL_NODE and right_value_obj.type() == super().INT_NODE) or (
            ):
            if arith_ast.elem_type in ["||", "&&", "==", "!="]:
                left_bool = self.__coerce_to_bool(left_value_obj)
                right_bool = self.__coerce_to_bool(right_value_obj)
                if arith_ast.elem_type == "||":
                    return Value(Type.BOOL, left_bool.value() or right_bool.value())
                elif arith_ast.elem_type == "&&":
                    return Value(Type.BOOL, left_bool.value() and right_bool.value())
                elif arith_ast.elem_type == "==":
                    return Value(Type.BOOL, left_bool.value() == right_bool.value())
                elif arith_ast.elem_type == "!=":
                    return Value(Type.BOOL, left_bool.value() != right_bool.value())

        if (left_value_obj.type() == super().INT_NODE and right_value_obj.type() == super().INT_NODE):
            if arith_ast.elem_type in ["||", "&&"]:
                left_bool = self.__coerce_to_bool(left_value_obj)
                right_bool = self.__coerce_to_bool(right_value_obj)
                if arith_ast.elem_type == "||":
                    return Value(Type.BOOL, left_bool.value() or right_bool.value())
                elif arith_ast.elem_type == "&&":
                    return Value(Type.BOOL, left_bool.value() and right_bool.value())

        
        if not self.__compatible_types(
            arith_ast.elem_type, left_value_obj, right_value_obj
        ):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible types for {arith_ast.elem_type} operation",
            )
        # print("left", left_value_obj)
        if left_value_obj.type() in self.structs and right_value_obj.type() in self.structs:
            if arith_ast.elem_type in ["==", "!="]:
                equal = left_value_obj.value() is right_value_obj.value()
                return Value(Type.BOOL, equal if arith_ast.elem_type == "==" else not equal)

        if left_value_obj.type() == Type.NIL:
            left_is_nil = True
        elif isinstance(left_value_obj.value(), Value) and left_value_obj.value().value() is None:
            left_is_nil = True
        else: 
            left_is_nil = False
        
        if right_value_obj.type() == Type.NIL:
            right_is_nil = True
        elif isinstance(right_value_obj.value(), Value) and right_value_obj.value().value() is None:
            right_is_nil = True
        else: 
            right_is_nil = False

        if left_value_obj.type() in self.structs or right_value_obj.type() in self.structs:
            if arith_ast.elem_type in ["==", "!="]:
                # print(left_value_obj.value(), left_value_obj.type())
                # print(right_value_obj.value(), right_value_obj.type())
                if left_is_nil and right_is_nil:
                    return Value(Type.BOOL, arith_ast.elem_type == "==")
                
                if (left_value_obj.value() == super().NIL_NODE and right_value_obj.type() == Type.NIL) or (
                    left_value_obj.type() == Type.NIL and right_value_obj.value() == super().NIL_NODE
                ):
                    return Value(Type.BOOL, arith_ast.elem_type == "==")

                if left_is_nil or right_is_nil:
                    return Value(Type.BOOL, arith_ast.elem_type == "!=")

                return Value(Type.BOOL, 
                            (left_value_obj.value() == right_value_obj.value()) 
                            if arith_ast.elem_type == "==" 
                            else (left_value_obj.value() != right_value_obj.value()))
        if left_is_nil and right_is_nil:
            if arith_ast.elem_type == "==":
                return Value(Type.BOOL, True)
            elif arith_ast.elem_type == "!=":
                return Value(Type.BOOL, False)
        if left_is_nil and right_value_obj.type() in self.__TYPES:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Cannot compare {right_value_obj.type()} with nil",
            )
        if right_is_nil and left_value_obj.type() in self.__TYPES:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Cannot compare {left_value_obj.type()} with nil",
            )
        
        if arith_ast.elem_type not in self.op_to_lambda[left_value_obj.type()]:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Incompatible operator {arith_ast.elem_type} for type {left_value_obj.type()}",
            )
        f = self.op_to_lambda[left_value_obj.type()][arith_ast.elem_type]
        return f(left_value_obj, right_value_obj)

    def __compatible_types(self, oper, obj1, obj2):
        # DOCUMENT: allow comparisons ==/!= of anything against anything
        if oper in ["==", "!="]:
            return True
        return obj1.type() == obj2.type()

    def __eval_unary(self, arith_ast, t, f):
        value_obj = self.__eval_expr(arith_ast.get("op1"))
        if t == super().BOOL_NODE and value_obj.type() == super().INT_NODE:
            value_obj = self.__coerce_to_bool(value_obj)
        # if t == "bool" and value_obj.type() == "int":
        #     value_obj = Value(Type.BOOL, value_obj.value() != 0)
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
        if result.type() == Type.INT:
            result = Value(Type.BOOL, result.value() != 0)
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
            if run_for.type() == super().INT_NODE:
                run_for = self.__coerce_to_bool(run_for)
            if run_for.type() != Type.BOOL:
                super().error(
                    ErrorType.TYPE_ERROR,
                    "Incompatible type for for condition",
                )
            if run_for.value():
                statements = for_ast.get("statements")
                status, return_val = self.__run_statements(statements)
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
# func test() : void {
#   return;
# }
# func main() : void {
#  print(test());
# }

# """

#     interpreter = Interpreter()
#     interpreter.run(program)  

# main()

#return void assign sjpld fail
# var x1: s;
#   var x2: s;
#   x1 = new s;
#   x2 = new s;
#   x1.a = 5;
#   x2.a = 5;
#   print(x1==x2);
#   print(x1.a==x2.a);
#   print(x1==x1);
#   x1.a = x2.a;
#   print(x1.a == x2.a);