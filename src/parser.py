from .grammar import Grammar

class Parser:

    def __eval_statement_op_and(self, ast_node, statement, source, index):
        _index = index
        for i in statement['statements']:
            _result, _index = self.__eval_statement(ast_node, i, source, _index)
            if _result == False:
                return False, index
        return True, _index
    
    def __eval_statement_op_or(self, ast_node, statement, source, index):
        for i in statement['statements']:
            _result, _index = self.__eval_statement(ast_node, i, source, index)
            if _result:
                return True, _index
        return False, index

    def __eval_statement_op_nand(self, ast_node, statement, source, index):
        for i in range(len(statement['statements'])):
            _result, _index = self.__eval_statement(ast_node, statement['statements'][i], source, index)
            if i == 0 and _result:
                __index = _index
            elif i == 0 and not _result:
                return False, index
            elif _result:
                return False, index
        return True, __index

    def __eval_statement_op(self, ast_node, statement, source, index):
        if statement['op'] == ',':
            return self.__eval_statement_op_and(ast_node, statement, source, index)
        elif statement['op'] == '|':
            return self.__eval_statement_op_or(ast_node, statement, source, index)
        elif statement['op'] == '-':
            return self.__eval_statement_op_nand(ast_node, statement, source, index)
        elif len(statement['statements']) == 1:
            return self.__eval_statement(ast_node, statement['statements'][0], source, index)
        else:
            print('__eval_statement_op unhandled statement ', statement)
            return False, index

    def __eval_statement(self, ast_node, statement, source, index):
        _type = statement['type']
        if _type == '{}':
            while True:
                temp_ast_node = ast_node.copy()

                _result, _index = self.__eval_statement_op(temp_ast_node, statement, source, index)
                if _result == True and _index > index:
                    if 'statements' in temp_ast_node:
                        ast_node['statements'] = temp_ast_node['statements']
                    if 'value' in ast_node:
                        ast_node['value'] = temp_ast_node['value']
                    result = _result
                    index = _index
                else:
                    return True, index
        elif _type == '[]':
            temp_ast_node = ast_node.copy()
            result, _index = self.__eval_statement_op(temp_ast_node, statement, source, index)
            if result == True:
                if 'statements' in temp_ast_node:
                    ast_node['statements'] = temp_ast_node['statements']
                if 'value' in ast_node:
                    ast_node['value'] = temp_ast_node['value']
                return True, _index
            else:
                return True, index
        elif _type in ['rule', '()']:
            return self.__eval_statement_op(ast_node, statement, source, index)
        elif _type == 'var':
            return self.__parse_recurse(ast_node, statement['value'], source, index)
        elif _type == 'str':
            value = statement['value']
            if source[index:index+len(value)] == value:
                ast_node['value'] += value
                return True, index+len(value)
            else:
                return False, index
        elif _type == 'spec':
            value = statement['value']
            if value in self.special_map.keys():
                if source[index] in self.special_map[value]:
                    ast_node['value'] += str(source[index])
                    return True, index + 1
                else:
                    return False, index
            else:
                print('Error unhandled special code', statement)
                return False, index
        else:
            print('unhandled 8')
            return False, index
        
    def __parse_recurse(self, ast_node, rule_name, source, index):
        if not 'statements' in ast_node:
            ast_node['statements'] = [{'rule': rule_name, 'value': ''}]
        else:
            ast_node['statements'].append({'rule': rule_name, 'value': ''})
        rule = self.grammar.get_rule(rule_name)
        if rule == False:
            ast_node['statements'].pop()
            return False, index
        else:
            result, _index = self.__eval_statement(ast_node['statements'][-1], rule, source, index)
            if result:
                self.error_stack = []
                if not 'value' in ast_node:
                    ast_node['value'] = ''
                elif len(ast_node['statements'][-1]['value']) > 0:
                    ast_node['value'] += ast_node['statements'][-1]['value']
                return result, _index
            else:
                self.error_stack.append(f'error line: {str(self.__get_line_number(source, index))}  rule: \'{rule_name}\'  character: \'{source[index]}\'')
                ast_node['statements'].pop()
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
        self.grammar = grammar
        self.error_stack = []
        self.special_map = {
            'white space characters': " \t\r\n",
            'all visible characters': ''.join([chr(i) for i in range(0x20, 0x7f)])
        }

    def parse(self, source: str):
        ast_root = {}
        result, index = self.__parse_recurse(ast_root, 'program', source, 0)
        if result and index == len(source):
            return ast_root
        else:
            return None

    def print_errors(self):
        for err in reversed(self.error_stack):
            print(err)
