import ply.lex as lex

# Keywords
keywords = {
    'program': 'PROGRAM',
    'end': 'END',
    'integer': 'INTEGER',
    'real': 'REAL',
    'logical': 'LOGICAL',
    'if': 'IF',
    'then': 'THEN',
    'else': 'ELSE',
    'do': 'DO',
    'continue': 'CONTINUE',
    'goto': 'GOTO',
    'print': 'PRINT',
    'read': 'READ',
    'function': 'FUNCTION',
    'subroutine': 'SUBROUTINE',
    'return': 'RETURN',
    'call': 'CALL',
    'endif': 'ENDIF',
}

# List of token names
reserved_tokens = tuple(keywords.values())

tokens = (
    'ID',
    'NUMBER',
    'STRING',
    'TRUE', 'FALSE',
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'POWER', 'EQUALS',
    'LPAREN', 'RPAREN', 'COMMA',
    'EQ', 'NE', 'LT', 'LE', 'GT', 'GE', 'AND', 'OR', 'NOT',
) + reserved_tokens

# Regular expressions for simple tokens
t_PLUS = r'\+'
t_MINUS = r'-'
t_DIVIDE = r'/'
t_EQUALS = r'='
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_COMMA = r','

# Logical operators
t_EQ = r'(?i:\.EQ\.)'
t_NE = r'(?i:\.NE\.)'
t_LT = r'(?i:\.LT\.)'
t_LE = r'(?i:\.LE\.)'
t_GT = r'(?i:\.GT\.)'
t_GE = r'(?i:\.GE\.)'
t_AND = r'(?i:\.AND\.)'
t_OR = r'(?i:\.OR\.)'
t_NOT = r'(?i:\.NOT\.)'

# Literais Lógicos
t_TRUE = r'(?i:\.TRUE\.)'
t_FALSE = r'(?i:\.FALSE\.)'

# String
def t_STRING(t):
    r"'([^']|'')*'"
    # Tokeniza literais de string Fortran (aspas simples, '' -> ' dentro da string).
    # Exemplo: 'O''la' -> valor O'la
    t.value = t.value[1:-1].replace("''", "'")
    return t


def t_POWER(t):
    r'\*\*'
    # Operador de potência '**'
    return t

def t_TIMES(t):
    r'\*'
    # Token '*' usado em 'PRINT *' e multiplicação (ambiguidade lexical resolvida em parser)
    return t

# Identifier
def t_ID(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    # Identificadores e palavras reservadas.
    # Normaliza comparando lowercase e converte para token reservado se aplicável.
    t.type = keywords.get(t.value.lower(), 'ID')
    return t

def t_NUMBER(t):
    r'\d+(\.\d+)?([eE][+-]?\d+)?'
    # Reconhece inteiros e reais com notação científica.
    if '.' in t.value or 'e' in t.value.lower():
        t.value = float(t.value)
    else:
        t.value = int(t.value)
    return t

# Comment
def t_COMMENT(t):
    r'(\s*[Cc\*]\s+.*|!.*)'
    pass

# Newline
def t_newline(t):
    r'\n+'
    # Atualiza contador de linhas do lexer para mensagens de erro precisas.
    t.lexer.lineno += len(t.value)

# Ignore whitespace
t_ignore = ' \t'

# Error handling
def t_error(t):
    # Tratamento simples de erro léxico: reporta e ignora o carácter inválido.
    print(f"Illegal character '{t.value[0]}' at line {t.lineno}")
    t.lexer.skip(1)

# Build the lexer
lexer = lex.lex()

# pode ser removido REMOVE 
if __name__ == "__main__":
    # Test the lexer
    data = '''
PROGRAM HELLO
PRINT *, 'Ola, Mundo!'
END
'''
    lexer.input(data)
    while True:
        tok = lexer.token()
        if not tok:
            break
        print(tok)