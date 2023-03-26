from .grammar import Grammar, Statement

class AstNode:
    def __init__(self, rule_name: str, line: int, value: str = ''):
        self.rule_name = rule_name
        self.nodes = []
        self.value = value
        self.line = line

    def to_string(self, indent: int = 0) -> str:
        return (
            ' ' * indent) + \
            f'{self.line}: {self.rule_name} -> "{self.value}"\n' + \
            ''.join([i.to_string(indent + 4) for i in self.nodes]
        )

    def to_object(self) -> dict:
        return {
            'rule': self.rule_name,
            'value': self.value,
            'line': self.line,
            'nodes': [i.to_object() for i in self.nodes]
        }

class Ast:
    def __init__(self):
        self.root = AstNode(rule_name='root', line=0)

    def to_string(self) -> str:
        return self.root.to_string()

    def to_object(self) -> dict:
        return self.root.to_object()

class Parser:

    def __eval_statement_op_and(self, node: AstNode, statement: Statement, source, index) -> tuple[bool, int]:
        _index = index
        for i in statement.statements:
            _result, _index = self.__eval_statement(node, i, source, _index)
            if _result == False:
                return False, index
        return True, _index

    def __eval_statement_op_or(self, node: AstNode, statement: Statement, source, index) -> tuple[bool, int]:
        for i in statement.statements:
            _result, _index = self.__eval_statement(node, i, source, index)
            if _result:
                return True, _index
        return False, index

    def __eval_statement_op_nand(self, node: AstNode, statement: Statement, source, index) -> tuple[bool, int]:
        for i in range(len(statement.statements)):
            _result, _index = self.__eval_statement(node, statement.statements[i], source, index)
            if i == 0 and _result:
                __index = _index
            elif i == 0 and not _result:
                return False, index
            elif _result:
                node.value = node.value[:-(i + 1)]
                node.nodes.pop()
                return False, index
        return True, __index

    def __eval_statement_op(self, node: AstNode, statement: Statement, source, index) -> tuple[bool, int]:
        if statement.op == ',':
            return self.__eval_statement_op_and(node, statement, source, index)
        elif statement.op == '|':
            return self.__eval_statement_op_or(node, statement, source, index)
        elif statement.op == '-':
            return self.__eval_statement_op_nand(node, statement, source, index)
        elif len(statement.statements) == 1:
            return self.__eval_statement(node, statement.statements[0], source, index)
        else:
            print('__eval_statement_op unhandled statement:\n', statement.to_string())
            return False, index

    def __eval_group_singular(self, node: AstNode, statement: Statement, source, index) -> tuple[bool, int]:
        result, _index = self.__eval_statement_op(node, statement, source, index)
        if result == True and _index > index:
            return True, _index
        else:
            return False, index

    def __eval_group_optional(self, node: AstNode, statement: Statement, source, index) -> tuple[bool, int]:
        result, _index = self.__eval_statement_op(node, statement, source, index)
        if result == True and _index > index:
            return True, _index
        else:
            return True, index

    def __eval_group_repetitive(self, node: AstNode, statement: Statement, source, index) -> tuple[bool, int]:
        while True:
            _result, _index = self.__eval_statement_op(node, statement, source, index)
            if _result == True and _index > index:
                index = _index
                continue
            else:
                return True, index

    def __eval_statement(self, node: AstNode, statement: Statement, source, index) -> tuple[bool, int]:
        _type = statement.type
        if _type in ['()', 'rule']:
            return self.__eval_group_singular(node, statement, source, index)
        elif _type == '[]':
            return self.__eval_group_optional(node, statement, source, index)
        elif _type == '{}':
            return self.__eval_group_repetitive(node, statement, source, index)
        elif _type == 'var':
            result, _index = self.__parse_recurse(node, statement.value, source, index)
            if result == True and _index > index:
                return True, _index
            else:
                return False, index
        elif _type == 'str':
            value = statement.value
            if index + len(value) > len(source):
                return False, index
            if source[index:index+len(value)] == value:
                node.value += value
                return True, index+len(value)
            else:
                return False, index
        elif _type == 'spec':
            value = statement.value
            if index >= len(source):
                return False, index
            if value in self.special_map.keys():
                if source[index] in self.special_map[value]:
                    node.value += str(source[index])
                    return True, index + 1
                else:
                    return False, index
            else:
                print('Error unhandled special code', statement)
            return False, index
        else:
            print('unhandled 8')
            return False, index
        
    def __parse_recurse(self, node: AstNode, rule_name: str, source, index) -> tuple[bool, int]:
        if len(source) <= index:
            self.error_stack.append(f'error ./{self.filename} \'{node.rule_name}\' rejected on \'{rule_name}\', out of bound character index \'{str(index)}\'')
            return False, index
        node.nodes.append(AstNode(rule_name=rule_name, value='', line = self.__get_line_number(source, index)))
        rule = self.grammar.get_rule(rule_name)
        if rule == None:
            node.nodes.pop()
            return False, index
        result, _index = self.__eval_statement(node.nodes[-1], rule, source, index)
        if result:
            node.value += node.nodes[-1].value
            return result, _index
        else:
            node.nodes.pop()
            self.error_stack.append(f'error ./{self.filename}:{str(self.__get_line_number(source, _index))} \'{node.rule_name}\' rejected on \'{rule_name}\' no match for \'{source[index]}\'')
            return False, index

    def __get_line_number(self, source, index):
        line_count = 1
        for i in range(len(source)):
            if i == index:
                return line_count
            if source[i] == '\n':
                line_count += 1
        return -1

    def __init__(self, grammar: Grammar):
        a_z = ''.join([chr(i) for i in range(ord('a'), ord('z') + 1)])
        A_Z = ''.join([chr(i) for i in range(ord('A'), ord('Z') + 1)])
        _0_9 = '0123456789'
        self.grammar = grammar
        self.error_stack = []
        self.special_map = {
            'white space characters': " \t\r\n",
            'all visible characters': ''.join([chr(i) for i in range(0x20, 0x7f)]),
            'a_z': a_z,
            'A_Z': A_Z,
            'A_z': A_Z + a_z,
            '_0_9': _0_9,
            '_0_9A_Fa_f': _0_9 + "ABCDEF" + "abcdef",
            'A_z0_9': A_Z + a_z + _0_9 
        }

    def parse(self, source: str, filename: str = ''):
        self.filename = filename
        ast = Ast()
        result, index = self.__parse_recurse(ast.root, 'program', source, 0)
        if result and index == len(source):
            ast.root = ast.root.nodes[0]
            return ast
        else:
            return None

    def print_errors(self):
        for err in reversed(self.error_stack):
            print(err)
