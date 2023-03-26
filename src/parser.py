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

class Parser:
    def __eval_statement_op_and(self, node: AstNode, statement: Statement, index) -> tuple[bool, int]:
        _index = index
        for i in statement.statements:
            _result, _index = self.__eval_statement(node, i, _index)
            if _result == False:
                return False, index
        return True, _index

    def __eval_statement_op_or(self, node: AstNode, statement: Statement, index) -> tuple[bool, int]:
        for i in statement.statements:
            _result, _index = self.__eval_statement(node, i, index)
            if _result:
                return True, _index
        return False, index

    def __eval_statement_op_nand(self, node: AstNode, statement: Statement, index) -> tuple[bool, int]:
        for i in range(len(statement.statements)):
            _result, _index = self.__eval_statement(node, statement.statements[i], index)
            if i == 0 and _result:
                __index = _index
            elif i == 0 and not _result:
                return False, index
            elif _result:
                node.value = node.value[:-(i + 1)]
                node.nodes.pop()
                return False, index
        return True, __index

    def __eval_statement_op(self, node: AstNode, statement: Statement, index) -> tuple[bool, int]:
        if statement.op == ',':
            return self.__eval_statement_op_and(node, statement, index)
        elif statement.op == '|':
            return self.__eval_statement_op_or(node, statement, index)
        elif statement.op == '-':
            return self.__eval_statement_op_nand(node, statement, index)
        elif len(statement.statements) == 1:
            return self.__eval_statement(node, statement.statements[0], index)
        else:
            print('__eval_statement_op unhandled statement:\n', statement.to_string())
            return False, index

    def __eval_group_singular(self, node: AstNode, statement: Statement, index) -> tuple[bool, int]:
        result, _index = self.__eval_statement_op(node, statement, index)
        if result == True and _index > index:
            return True, _index
        else:
            return False, index

    def __eval_group_optional(self, node: AstNode, statement: Statement, index) -> tuple[bool, int]:
        result, _index = self.__eval_statement_op(node, statement, index)
        if result == True and _index > index:
            return True, _index
        else:
            return True, index

    def __eval_group_repetitive(self, node: AstNode, statement: Statement, index) -> tuple[bool, int]:
        while True:
            _result, _index = self.__eval_statement_op(node, statement, index)
            if _result == True and _index > index:
                index = _index
                continue
            else:
                return True, index

    def __eval_statement(self, node: AstNode, statement: Statement, index) -> tuple[bool, int]:
        _type = statement.type
        if _type in ['()', 'rule']:
            return self.__eval_group_singular(node, statement, index)
        elif _type == '[]':
            return self.__eval_group_optional(node, statement, index)
        elif _type == '{}':
            return self.__eval_group_repetitive(node, statement, index)
        elif _type == 'var':
            result, _index = self.__parse_recurse(node, statement.value, index)
            if result == True and _index > index:
                return True, _index
            else:
                return False, index
        elif _type == 'str':
            value = statement.value
            if index + len(value) > len(self.source):
                return False, index
            if self.source[index:index+len(value)] == value:
                node.value += value
                return True, index+len(value)
            else:
                return False, index
        elif _type == 'spec':
            value = statement.value
            if index >= len(self.source):
                return False, index
            if value in self.special_map.keys():
                if self.source[index] in self.special_map[value]:
                    node.value += str(self.source[index])
                    return True, index + 1
                else:
                    return False, index
            else:
                print('Error unhandled special code', statement)
            return False, index
        else:
            self.error_stack.append(f'error ./{self.filename}:{str(self.__get_line_number(index))} \'{node.rule_name}\' unknown statement.type \'{_type}\'')
            return False, index
        
    def __parse_recurse(self, node: AstNode, rule_name: str, index) -> tuple[bool, int]:
        if len(self.source) <= index:
            self.error_stack.append(f'error ./{self.filename} \'{node.rule_name}\' rejected on \'{rule_name}\', out of bound character index \'{str(index)}\'')
            return False, index
        node.nodes.append(AstNode(rule_name=rule_name, value='', line = self.__get_line_number(index)))
        rule = self.grammar.get_rule(rule_name)
        if rule == None:
            node.nodes.pop()
            return False, index
        result, _index = self.__eval_statement(node.nodes[-1], rule, index)
        if result:
            node.value += node.nodes[-1].value
            return result, _index
        else:
            node.nodes.pop()
            self.error_stack.append(f'error ./{self.filename}:{str(self.__get_line_number(_index))} \'{node.rule_name}\' rejected on \'{rule_name}\' no match for \'{self.source[index]}\'')
            return False, index

    def __get_line_number(self, index):
        line_count = 1
        for i in range(len(self.source)):
            if i == index:
                return line_count
            if self.source[i] == '\n':
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

    def parse(self, source: str, filename: str = '') -> AstNode:
        self.filename = filename
        self.source = source
        root = AstNode(rule_name='root', line=0)
        result, index = self.__parse_recurse(root, 'program', 0)
        if result and index == len(source):
            return root.nodes[0]
        else:
            return None

    def print_errors(self):
        for err in reversed(self.error_stack):
            print(err)
