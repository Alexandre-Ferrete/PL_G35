# AST_NODES.PY - Definição da Árvore de Sintaxe Abstrata
# Este ficheiro contém as classes que representam os nós da árvore que o 
# Parser irá construir.

class Node:
    """Classe base para todos os nós da árvore."""
    def __repr__(self):
        return f"{self.__class__.__name__}"

# NÓ RAIZ E ESTRUTURA DE PROGRAMA
class Program(Node):
    def __init__(self, name, body, functions=None):
        self.name = name    # Nome do programa (ID)
        self.body = body    # Lista de statements (instruções)
        self.functions = functions or []

# EXPRESSÕES (Tudo o que produz um VALOR)
class Expression(Node):
    pass

class BinOp(Expression):
    """Binary Operations: A + B, X * Y, I .EQ. J"""
    def __init__(self, left, op, right):
        self.left = left
        self.op = op
        self.right = right

class UnaryOp(Expression):
    """Unary Operations: -X, .NOT. A"""
    def __init__(self, op, expr):
        self.op = op
        self.expr = expr

class Variable(Expression):
    """Represents the use of a variable by its name (ID)"""
    def __init__(self, name):
        self.name = name

class ArrayAccess(Expression):
    """Acesso indexado a um array: A(I)"""
    def __init__(self, name, index):
        self.name = name
        self.index = index

class Literal(Expression):
    """Classe base para valores constantes (Inteiros, Reais, Strings)"""
    def __init__(self, value, type):
        self.value = value
        self.type = type # 'INTEGER', 'REAL', 'STRING', 'LOGICAL'

class FunctionCall(Expression):
    """Chamada de função: MOD(x, y)"""
    def __init__(self, name, args):
        self.name = name
        self.args = args

class FunctionDef(Node):
    """Definição de função: INTEGER FUNCTION F(X, Y)"""
    def __init__(self, name, return_type, params, body):
        self.name = name
        self.return_type = return_type
        self.params = params
        self.body = body

class SubroutineDef(Node):
    """Definição de subrotina: SUBROUTINE S(X, Y)"""
    def __init__(self, name, params, body):
        self.name = name
        self.params = params
        self.body = body

# STATEMENTS (Instruções que EXECUTAM uma ação)
class Statement(Node):
    pass

class Assignment(Statement):
    """Atribuição: VAR = EXPRESSAO"""
    def __init__(self, variable, expression):
        self.variable = variable
        self.expression = expression

class PrintStmt(Statement):
    """Comando: PRINT *, expr1, expr2..."""
    def __init__(self, expressions):
        self.expressions = expressions # Lista de expressões a imprimir

class ReadStmt(Statement):
    """Comando: READ *, var1, var2..."""
    def __init__(self, variables):
        self.variables = variables

class IfStmt(Statement):
    """Estrutura: IF (cond) THEN ... ELSE ... ENDIF"""
    def __init__(self, condition, then_branch, else_branch=None):
        self.condition = condition
        self.then_branch = then_branch # Lista de statements
        self.else_branch = else_branch # Lista de statements (opcional)

class DoStmt(Statement):
    """Estrutura: DO label var = start, end, step [body/terminal]"""
    def __init__(self, label, var, start, end, step=None, body=None, terminal=None):
        self.label = label
        self.var = var
        self.start = start
        self.end = end
        self.step = step
        self.body = body or []
        self.terminal = terminal

class GotoStmt(Statement):
    """Comando: GOTO label"""
    def __init__(self, label):
        self.label = label

class LabelStmt(Statement):
    """Representa uma linha com rótulo: 10 CONTINUE"""
    def __init__(self, label, statement):
        self.label = label
        self.statement = statement

class ContinueStmt(Statement):
    """Representa CONTINUE (no-op)."""
    pass

class ReturnStmt(Statement):
    """Representa RETURN."""
    pass

class CallStmt(Statement):
    """Chamada de subrotina/procedimento como statement."""
    def __init__(self, name, args):
        self.name = name
        self.args = args

# DECLARAÇÕES
class Declaration(Node):
    """Exemplo: INTEGER A, B, C"""
    def __init__(self, data_type, variables):
        self.data_type = data_type # 'INTEGER', 'REAL', etc.
        self.variables = variables # Lista de IDs

class ArrayDecl(Node):
    """Declaração de array: A(5)"""
    def __init__(self, name, size):
        self.name = name
        self.size = size