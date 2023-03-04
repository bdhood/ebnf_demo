from src.grammar import Grammar
from src.parser import Parser
import pprint

with open('examples/pascal-like/pascal-like.ebnf', 'r') as f:
    grammar = Grammar()
    if not grammar.load(f.read()):
        exit(1)
    
with open('examples/pascal-like/source.pas', 'r') as f:
    parser = Parser(grammar)
    ast = parser.parse(f.read())
    if ast == None:
        parser.print_errors()
    pprint.pprint(ast)

