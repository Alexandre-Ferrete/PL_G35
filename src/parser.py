import ply.yacc as yacc
from lexer import tokens
import ast_nodes as ast

# 1. PRECEDÊNCIA
# A ordem define a hierarquia: o que está mais abaixo tem maior prioridade.
precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('left', 'EQ', 'NE', 'LT', 'LE', 'GT', 'GE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE'),
    ('right', 'POWER'),
    ('right', 'UMINUS'), # Unary minus (e.g., -5)
)

# 2. REGRAS GRAMATICAIS
# Raiz do programa
def p_program(p):
    # Regra principal: define a estrutura de um programa Fortran simples.
    # Sintaxe: PROGRAM ID <declarations> <statements> END <optional functions>
    'program : PROGRAM ID declarations_opt statements END function_defs_opt'
    p[0] = ast.Program(p[2], p[3] + p[4], p[6])

def p_empty(p):
    # Produz uma lista vazia usada em listas opcionais (e.g., parâmetros vazios).
    'empty :'
    p[0] = []

def p_function_defs_opt(p):
    # Alternativa: zero ou mais definições de função após o corpo principal.
    '''function_defs_opt : function_defs
                         | empty'''
    p[0] = p[1]

def p_function_defs(p):
    # Lista recursiva de definições de função.
    '''function_defs : function_defs function_def
                     | function_def'''
    if len(p) == 3:
        p[1].append(p[2])
        p[0] = p[1]
    else:
        p[0] = [p[1]]

# Lista de instruções (recursiva para aceitar várias linhas)
def p_statements(p):
    # Sequência de instruções; produz sempre uma lista de statements.
    '''statements : statements statement
                  | statement'''
    if len(p) == 3:
        p[1].append(p[2])
        p[0] = p[1]
    else:
        p[0] = [p[1]]

# Categorias de instruções suportadas
def p_statement(p):
    # Qualquer statement suportado pelo parser.
    '''statement : assignment
                 | print_stmt
                 | read_stmt
                 | call_stmt
                 | if_stmt
                 | do_stmt
                 | goto_stmt
                 | label_stmt
                 | continue_stmt
                 | return_stmt'''
    p[0] = p[1]

def p_declarations_opt(p):
    # Bloco opcional de declarações: usado no início de PROGRAM e FUNCTION.
    '''declarations_opt : declarations_opt declaration
                        | empty'''
    if len(p) == 3:
        if p[1] is None:
            p[0] = [p[2]]
        else:
            p[1].append(p[2])
            p[0] = p[1]
    else:
        p[0] = []

# --- DECLARAÇÕES ---
def p_declaration(p):
    # Declaração de variáveis: e.g., INTEGER A, B, C ou A(10)
    'declaration : type declarator_list'
    p[0] = ast.Declaration(p[1], p[2])

def p_type(p):
    # Tipos suportados pelo subset: INTEGER, REAL, LOGICAL
    '''type : INTEGER
        | REAL
        | LOGICAL'''
    p[0] = p[1]

def p_declarator_list(p):
    # Lista de declaradores, suporta arrays com sintaxe ID(NUMBER)
    '''declarator_list : declarator_list COMMA declarator
                       | declarator'''
    if len(p) == 4:
        p[1].append(p[3])
        p[0] = p[1]
    else:
        p[0] = [p[1]]

def p_id_list(p):
    # Alias: lista de IDs reutilizada para parâmetros e declaradores.
    'id_list : declarator_list'
    p[0] = p[1]

def p_declarator(p):
    # Declarador simples ou declaração de array com tamanho literal.
    '''declarator : ID
                  | ID LPAREN NUMBER RPAREN'''
    if len(p) == 2:
        p[0] = p[1]
    else:
        p[0] = ast.ArrayDecl(p[1], p[3])

# --- COMANDOS DE I/O ---
def p_print_stmt(p):
    # Comando PRINT: usa '*' seguido de lista de expressões.
    'print_stmt : PRINT TIMES COMMA expression_list'
    p[0] = ast.PrintStmt(p[4])

def p_read_stmt(p):
    # Comando READ: lê variáveis da entrada.
    'read_stmt : READ TIMES COMMA varref_list'
    p[0] = ast.ReadStmt(p[4])

def p_varref_list(p):
    # Lista de referências a variáveis (para READ).
    '''varref_list : varref_list COMMA varref
                   | varref'''
    if len(p) == 4:
        p[1].append(p[3])
        p[0] = p[1]
    else:
        p[0] = [p[1]]

def p_varref(p):
    # Referência a variável simples ou a um elemento de array.
    '''varref : ID
              | ID LPAREN expression_list RPAREN'''
    if len(p) == 2:
        p[0] = ast.Variable(p[1])
    else:
        p[0] = ast.ArrayAccess(p[1], p[3][0])

def p_expression_list(p):
    # Lista de expressões separadas por vírgula.
    '''expression_list : expression_list COMMA expression
                       | expression'''
    if len(p) == 4:
        p[1].append(p[3])
        p[0] = p[1]
    else:
        p[0] = [p[1]]

# --- ATRIBUIÇÃO E FLUXO ---
def p_assignment(p):
    # Atribuição de expressão a variável/array.
    'assignment : varref EQUALS expression'
    p[0] = ast.Assignment(p[1], p[3])

def p_goto_stmt(p):
    # GOTO com rótulo numérico.
    'goto_stmt : GOTO NUMBER'
    if not isinstance(p[2], int):
        raise SyntaxError(f"GOTO label must be an integer (line {p.lineno(2)})")
    p[0] = ast.GotoStmt(p[2])

def p_label_stmt(p):
    # Linha com rótulo: ex. 10 CONTINUE
    'label_stmt : NUMBER statement'
    if not isinstance(p[1], int):
        raise SyntaxError(f"Line label must be an integer (line {p.lineno(1)})")
    p[0] = ast.LabelStmt(p[1], p[2])

def p_continue_stmt(p):
    # COMANDO CONTINUE (no-op em muitos casos).
    'continue_stmt : CONTINUE'
    p[0] = ast.ContinueStmt()

def p_return_stmt(p):
    # RETURN dentro de funções.
    'return_stmt : RETURN'
    p[0] = ast.ReturnStmt()

def p_call_stmt(p):
    # Chamada a subrotina/procedimento como statement (CALL name(args)).
    '''call_stmt : CALL ID LPAREN empty RPAREN
                  | CALL ID LPAREN expression_list RPAREN'''
    if len(p) == 6 and p[4] == []:
        p[0] = ast.CallStmt(p[2], [])
    else:
        p[0] = ast.CallStmt(p[2], p[4])

def p_if_stmt(p):
    # Estrutura condicional IF com THEN [ELSE] e END/ENDIF.
    '''if_stmt : IF LPAREN expression RPAREN THEN statements endif
               | IF LPAREN expression RPAREN THEN statements ELSE statements endif'''
    if len(p) == 10:
        p[0] = ast.IfStmt(p[3], p[6], p[8])
    else:
        p[0] = ast.IfStmt(p[3], p[6])

def p_endif(p):
    # Aceita tanto ENDIF como END para terminar um IF.
    '''endif : ENDIF
             | END'''
    p[0] = p[1]

def p_do_stmt(p):
    # DO label var = start, end [, step]
    # Suporta forma com e sem step.
    '''do_stmt : DO NUMBER ID EQUALS expression COMMA expression
               | DO NUMBER ID EQUALS expression COMMA expression COMMA expression'''
    if len(p) == 8:
        step = None
        end_expr = p[7]
    else:
        step = p[9]
        end_expr = p[7]
    p[0] = ast.DoStmt(p[2], ast.Variable(p[3]), p[5], end_expr, step)

def p_function_def(p):
    # Definição de função com tipo de retorno, nome, parâmetros, declarações e corpo.
    'function_def : type FUNCTION ID LPAREN param_list RPAREN declarations_opt function_items END'
    p[0] = ast.FunctionDef(p[3], p[1], p[5], p[7] + p[8])

def p_subroutine_def(p):
    # Definição de subrotina: nome, parâmetros, declarações e corpo.
    'subroutine_def : SUBROUTINE ID LPAREN param_list RPAREN declarations_opt function_items END'
    p[0] = ast.SubroutineDef(p[2], p[4], p[6] + p[7])

def p_param_list(p):
    # Lista de parâmetros (pode ser vazia).
    '''param_list : id_list
                  | empty'''
    p[0] = p[1]

def p_function_items(p):
    # Lista de statements dentro do corpo de uma função (declaracoes são prévias).
    '''function_items : function_items function_item
                      | function_item'''
    if len(p) == 3:
        p[1].append(p[2])
        p[0] = p[1]
    else:
        p[0] = [p[1]]

def p_function_defs_subs(p):
    # Também aceita subrotinas na mesma lista de rotinas.
    '''function_defs : function_defs subroutine_def
                     | subroutine_def'''
    if len(p) == 3:
        p[1].append(p[2])
        p[0] = p[1]
    else:
        p[0] = [p[1]]

def p_function_item(p):
    # Item do corpo da função: statements apenas (declarations devem estar no bloco de declarações).
    '''function_item : statement'''
    p[0] = p[1]

# --- EXPRESSÕES ---
def p_expression_binop(p):
    # Operações binárias: aritméticas, relacionais e lógicas.
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression
                  | expression POWER expression
                  | expression EQ expression
                  | expression NE expression
                  | expression LT expression
                  | expression LE expression
                  | expression GT expression
                  | expression GE expression
                  | expression AND expression
                  | expression OR expression'''
    p[0] = ast.BinOp(p[1], p[2], p[3])

def p_expression_unary(p):
    # Operações unárias: negativo e .NOT.
    '''expression : MINUS expression %prec UMINUS
                  | NOT expression'''
    p[0] = ast.UnaryOp(p[1], p[2])

def p_expression_group(p):
    # Agrupamento por parêntesis: ( expression )
    'expression : LPAREN expression RPAREN'
    p[0] = p[2]

def p_expression_primary(p):
    '''expression : ID
                  | ID LPAREN expression_list RPAREN
                  | REAL LPAREN expression_list RPAREN
                  | INTEGER LPAREN expression_list RPAREN
                  | literal'''
    if len(p) == 5:
        # p[1] pode vir como o token REAL ou INTEGER, convertemos para string
        func_name = str(p[1])
        p[0] = ast.FunctionCall(func_name, p[3])
    elif isinstance(p[1], str) and p[1] not in ['.TRUE.', '.FALSE.']:
        p[0] = ast.Variable(p[1])
    else:
        p[0] = p[1]

def p_literal(p):
    # Literais: números, strings e lógicos (.TRUE./.FALSE.).
    '''literal : NUMBER
               | STRING
               | TRUE
               | FALSE'''
    val = p[1]
    if isinstance(val, int): t = 'INTEGER'
    elif isinstance(val, float): t = 'REAL'
    elif str(val).upper() in ['.TRUE.', '.FALSE.', 'TRUE', 'FALSE']: t = 'LOGICAL'
    else: t = 'STRING'
    p[0] = ast.Literal(val, t)

# --- ERRO ---
def p_error(p):
    # Tratamento de erro sintático: eleva SyntaxError com informação.
    if p:
        raise SyntaxError(f"Syntax error at token '{p.value}' (line {p.lineno})")
    else:
        raise SyntaxError("Syntax error: unexpected end of file")

# Build
parser = yacc.yacc()