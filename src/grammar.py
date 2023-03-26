import json
from collections.abc import Iterable

class Token:
    def __init__(self, type: str, value: str, line: int):
        self.type = type
        self.value = value
        self.line = line

    def to_string(self):
        return f'{self.type} \'{self.value}\' line {self.line}'

class Statement:
    def __init__(self, type: str, line: int, op: str = '', statements: Iterable = [], value: str = ''):
        self.type = type
        self.line = line
        self.op = op
        self.statements = statements
        if self.statements == []:
            self.statements = []
        self.value = value
        return
    
    def to_string(self, indent: int = 0):
        return f'line {self.line}: {str(" " * indent)} {self.type}:\'{self.value}\' {self.op}\n' + ''.join([i.to_string(indent+4) for i in self.statements])

class Grammar:

    def __parse_tokens_append(self, result, state, type):
        result.append(Token(type=type, value=state['buffer'], line=state['line_number']))
        state['buffer'] = ''
        return result, state

    def __parse_tokens(self, source) -> Iterable[Token]:
        result = []
        state = {'in_comment':False, 'in_string':False, 'string_char': '', 'prev_is_escape': False, 'in_special':False, 'in_variable':False, 'line_number': 1, 'buffer': ''}
        for i in range(len(source)):
            if source[i] == '\n':
                state['line_number'] += 1

            # comments (* and *)
            if not state['in_comment'] and source[i] == '(' and len(source) > i + 1 and source[i + 1] == '*':
                state['in_comment'] = True
                continue
            elif state['in_comment'] and source[i] == ')' and i - 1 >= 0 and source[i - 1] == '*':
                state['in_comment'] = False
                continue
            elif state['in_comment']:
                continue

            # strings "example" or 'example'
            if not state['in_string'] and source[i] in ['"', "'"]:
                state['string_char'] = source[i]
                state['in_string'] = True
                continue
            elif state['in_string']:
                if not state['prev_is_escape'] and source[i] == state['string_char']:
                    result, state = self.__parse_tokens_append(result, state, 'str')
                    state['in_string'] = False
                elif source[i] == '\\' and not state['prev_is_escape']:
                    state['prev_is_escape'] = True
                elif state['prev_is_escape']:
                    state['prev_is_escape'] = False
                    if source[i] == '\\':
                        state['buffer'] += '\\'
                    elif source[i] == 'n':
                        state['buffer'] += '\n'
                    elif source[i] == 't':
                        state['buffer'] += '\t'
                    else:
                        print(f'grammar.parse_tokens error line {str(state["line_number"])} invalid escape code \'\\{source[i]}\'')
                        return None
                else:
                    state['buffer'] += source[i]
                continue

            # special "? special name ?"
            if not state['in_special'] and source[i] == '?':
                state['in_special'] = True
                continue
            elif state['in_special'] and source[i] == '?':
                state['buffer'] = state['buffer'].strip()
                result, state = self.__parse_tokens_append(result, state, 'spec')
                state['in_special'] = False
                continue
            elif state['in_special']:
                state['buffer'] += source[i]
                continue

            # variables, matches [a-zA-Z][a-zA-Z \t]* and trims trailing whitepace
            if source[i].isalnum():
                state['in_variable'] = True
            elif state['in_variable'] and not source[i].isalnum() and source[i] != ' ' and source[i] != '\t':
                state['in_variable'] = False
                while state['buffer'][len(state['buffer']) - 1] in [' ', '\t']:
                    state['buffer'] = state['buffer'][:-1]
                result, state = self.__parse_tokens_append(result, state, 'var')
            if state['in_variable']:
                state['buffer'] += source[i]
                continue

            # ignore whitespace
            if source[i] in [' ', '\t', '\r', '\n']:
                continue

            # if command char add buffer and command char to tokens
            if source[i] in ['(', ')', '{', '}', ',', '|', '-', '[', ']', '=', ';']:
                if len(state['buffer']) == 0:
                    state['buffer'] = source[i]
                    result, state = self.__parse_tokens_append(result, state, 'cmd')
                continue

            print(f'grammar.parse_tokens error line {str(state["line_number"])}: unhandled character "{source[i]}"')
            return None

        return result

    def __parse_rules(self, tokens: Iterable[Token]) -> Iterable[Statement]:
        result = []
        state = {'name':'', 'tokens':[], 'has_equals':False}
        for i in range(len(tokens)):
            _type = tokens[i].type
            _value = tokens[i].value
            if _type == 'var' and len(state['name']) == 0:
                state['name'] = tokens[i].value
            elif _type == 'cmd' and _value == '=' and not state['has_equals']:
                state['has_equals'] = True
            elif _type == 'cmd' and _value == ';' and state['has_equals']:
                if len(state['name']) == 0:
                    print(f'grammar.parse_rules error line {tokens[i].line}: rule name cannot be empty')
                    return None
                if len(state['tokens']) == 0:
                    print(f'grammar.parse_rules error line {tokens[i].line}: rule must have atleast 1 token')
                    return None
                for rule in result:
                    if rule.value == state['name']:
                        print(f'grammar.parse_rules error line {tokens[i].line}: rule \'{state["name"]}\' has already been defined')
                        return None

                result.append(self.__parse_rule(state['name'], state['tokens']))
                state = {'name':'', 'tokens':[], 'has_equals':False}
            elif state['has_equals']:
                state['tokens'].append(tokens[i])
            else:
                print(f'grammar.parse_rules error line {tokens[i].line}: unhandled token [{_type}, \'{_value}\']')
                return None
        if len(state['tokens']) > 0 or len(state['name']) > 0:
            print(f'grammar.parse_rules missing closing \';\' on line {tokens[len(tokens) - 1].line}')
            return None
        return result
    
    def __parse_rule(self, name, tokens: Iterable[Token]) -> Statement:
        key_map = {'[':']', '{':'}', '(':')'}
        root = Statement(type='rule', value=name, line=tokens[0].line)
        pointer = root
        parent_stack = []
        for j in range(len(tokens)):
            token: Token = tokens[j]
            value = token.value
            if token.type != 'cmd':
                pointer.statements.append(Statement(line=token.line, type=token.type, value=token.value))
            elif value in ['(', '[', '{']:
                temp = Statement(type=value + key_map[value], line=token.line, statements=[])
                pointer.statements.append(temp)
                parent_stack.append(pointer)
                pointer = temp
            elif value in [')', ']', '}']:
                if value in pointer.type:
                    if len(pointer.statements) == 0:
                        print(f'grammar.__parse_rule error line {str(token.line)}: no statements in grouping \'{pointer.type}\'')
                        return None
                    pointer = parent_stack.pop()
                else:                    
                    print(f'grammar.__parse_rule error line {str(token.line)}: invalid character \'{value}\'')
                    return None    
            elif value in ['|', ',', '-']:
                if pointer.op == '':
                    pointer.op = value
                elif pointer.op != value:
                    print(f'grammar.parse_statements error line {str(pointer.line)}, do not use both "' + pointer.op + '" and "' + value + '" in a single statement')
                    return None
            else:
                pointer.statements.append(Statement(line=token.line, type=token.type, value=token.value))
        return root

    def load(self, grammar_source):
        grammar_tokens = self.__parse_tokens(grammar_source)
        if grammar_tokens == None:
            return False
        self.grammar_rules = self.__parse_rules(grammar_tokens)
        if self.grammar_rules == None:
            return False
        return not None in self.grammar_rules

    def get_rule(self, rule_name: str) -> dict:
        for statement in self.grammar_rules:
            if statement.value == rule_name:
                return statement
        print(f'grammar.get_rule error: could not find rule \'{rule_name}\'')
        return None
