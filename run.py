from src.grammar import Grammar
from src.parser import Parser, AstNode
import json

examples = [
    'pas',
    'asm',
    'test'
]

for i in examples:
    with open(f'examples/{i}/{i}.ebnf', 'r') as f:
        grammar = Grammar()
        if not grammar.load(f.read()):
            exit(1)
        
    with open(f'examples/{i}/source.{i}', 'r') as f:
        parser = Parser(grammar)
        ast = parser.parse(f.read(), filename=f'examples/{i}/source.{i}')
        if ast == None:
            print("error:")
            parser.print_errors()
            exit(1)

    with open(f'examples/{i}/ast.json', 'w') as f:
        f.write(json.dumps(ast.to_object(), indent=4))

