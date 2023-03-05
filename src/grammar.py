class Grammar:

    def __parse_tokens_append(self, result, state, type):
        result.append({'type':type, 'value': state['buffer'], 'line': state['line_number']})
        state['buffer'] = ''
        return result, state

    def __parse_tokens(self, source):
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
                if len(state['buffer']) > 0:
                    result, state = self.__parse_tokens_append(result, state, 'unknown')
                result.append({'type':'cmd', 'value': source[i], 'line': state['line_number']})
                continue

            print(f'grammar.parse_tokens error line {str(state["line_number"])}: unhandled character "{source[i]}"')
            return None

        return result

    def __parse_rules(self, tokens):
        result = []
        state = {'name':'', 'tokens':[], 'has_equals':False}
        for i in range(len(tokens)):
            _type = tokens[i]['type']
            _value = tokens[i]['value']
            if _type == 'var' and len(state['name']) == 0:
                state['name'] = tokens[i]
            elif _type == 'cmd' and _value == '=' and not state['has_equals']:
                state['has_equals'] = True
            elif _type == 'cmd' and _value == ';' and state['has_equals']:
                if len(state['name']) == 0:
                    print(f'grammar.parse_rules error line {tokens[i]["line"]}: rule name cannot be empty')
                    return None
                if len(state['tokens']) == 0:
                    print(f'grammar.parse_rules error line {tokens[i]["line"]}: rule must have atleast 1 token')
                    return None
                for rule in result:
                    if rule['name']['value'] == state['name']['value']:
                        print(f'grammar.parse_rules error line {tokens[i]["line"]}: rule \'{state["name"]["value"]}\' has already been defined')
                        return None
                result.append({'name': state['name'], 'tokens': state['tokens']})
                state = {'name':'', 'tokens':[], 'has_equals':False}
            elif state['has_equals']:
                state['tokens'].append(tokens[i])
            else:
                print(f'grammar.parse_rules error line {tokens[i]["line"]}: unhandled token [{_type}, \'{_value}\']')
                return None
        if len(state['tokens']) > 0 or len(state['name']) > 0:
            print(f'grammar.parse_rules missing closing \';\' on line {tokens[len(tokens) - 1]["line"]}')
            return None
        return result

    def __parse_statements(self, rule):
        key_map = {'[':']', '{':'}', '(':')'}
        state = {'name':rule['name'], 'root': {'statements':[], 'op': ''}, 'pointer': None, 'op': ''}
        state['pointer'] = state['root']
        for j in range(len(rule['tokens'])):
            token = rule['tokens'][j]
            value = token['value']
            if token['type'] != 'cmd':
                state['pointer']['statements'].append(token)
                continue

            if value in ['(', '[', '{']:
                temp = {'type':value + key_map[value], 'parent':state['pointer'], 'statements': [], 'op': ''}
                state['pointer']['statements'].append(temp)
                state['pointer'] = temp
                continue
            elif value in [')', ']', '}']:
                if 'type' in state['pointer'] and value in state['pointer']['type']:
                    if 'statements' in state['pointer'] and len(state['pointer']['statements']) == 0:
                        print(f'grammar.parse_statements error line {str(token["line"])}: no statements in grouping \'{state["pointer"]["type"]}\'')
                        return None
                    state['pointer'] = state['pointer'].pop('parent')
                    continue
                else:
                    print(f'grammar.parse_statements error line {str(token["line"])}: invalid character \'{value}\'')
                    return None
            elif value in ['|', ',', '-']:
                if state['pointer']['op'] == '':
                    state['pointer']['op'] = value
                    continue
                elif state['pointer']['op'] != value:
                    print(f'grammar.parse_statements error line {str(state["pointer"]["line"])}, do not use both "' + state["pointer"]["op"] + '" and "' + value + '" in a single statement')
                    return None
                else:
                    continue
            else:
                state['pointer']['statements'].append(token)
        
        return {'type': 'rule', 'name': state['name'], 'statements': state['root']['statements'], 'op': state['root']['op']}

    def load(self, grammar_source):
        grammar_tokens = self.__parse_tokens(grammar_source)
        if grammar_tokens == None:
            return False
        tokenized_rules = self.__parse_rules(grammar_tokens)
        if tokenized_rules == None:
            return False
        self.grammar_rules = []
        for rule in tokenized_rules:
            self.grammar_rules.append(self.__parse_statements(rule))
        return not None in self.grammar_rules

    def get_rule(self, rule_name):
        for rule in self.grammar_rules:
            if rule['name']['value'] == rule_name:
                return rule
        print(f'grammar.get_rule error: could not find rule \'{rule_name}\'')
        return None
