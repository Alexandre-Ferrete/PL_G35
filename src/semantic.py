import ast_nodes as ast
try:
    from src import builtin_defs as bdefs
except ImportError:
    import builtin_defs as bdefs


class SemanticError(Exception):
    pass


class SemanticAnalyzer:
    def __init__(self):
        self.symbol_table    = {}
        self.function_table  = {}
        self.current_function = None
        self.declared_labels = set()
        self.pending_gotos   = []

    def analyze(self, node):
        return self.visit(node)

    def _is_builtin_function(self, name):
        return bdefs.is_builtin(name)

    def _get_symbol_info(self, name):
        key = name.upper()
        if key not in self.symbol_table:
            raise SemanticError(f"Error: Variable '{name}' not declared.")
        info = self.symbol_table[key]
        if isinstance(info, dict):
            if info.get('type') is None:
                raise SemanticError(f"Error: Variable '{name}' has no declared type.")
            return info
        return {'type': info, 'kind': 'scalar'}

    def _normalize_do_loops(self, statements):
        normalized, loop_stack = [], []
        body = lambda: loop_stack[-1]["node"].body if loop_stack else normalized
        for stmt in statements:
            if isinstance(stmt, ast.DoStmt):
                stmt.body = []; stmt.terminal = None
                body().append(stmt)
                loop_stack.append({"label": stmt.label, "node": stmt})
            elif isinstance(stmt, ast.LabelStmt) and loop_stack and loop_stack[-1]["label"] == stmt.label:
                if stmt.label in self.declared_labels:
                    raise SemanticError(f"Error: Duplicate label {stmt.label}.")
                self.declared_labels.add(stmt.label)
                loop_stack[-1]["node"].terminal = stmt.statement
                loop_stack.pop()
            else:
                body().append(stmt)
        if loop_stack:
            raise SemanticError(f"Semantic error: DO without closing label '{loop_stack[-1]['label']}'.")
        return normalized

    def visit(self, node):
        if node is None: return
        return getattr(self, f'visit_{type(node).__name__}', self.generic_visit)(node)

    def generic_visit(self, node):
        raise SemanticError(f"No visitor method defined for {type(node).__name__}")

    def visit_Program(self, node):
        node.body = self._normalize_do_loops(node.body)
        for fn in getattr(node, 'functions', []):
            self.function_table[fn.name.upper()] = {
                'return_type': getattr(fn, 'return_type', 'VOID'),
                'params': getattr(fn, 'params', []),
            }
        for stmt in node.body:
            if isinstance(stmt, ast.Declaration): self.visit(stmt)
        for stmt in node.body:
            if not isinstance(stmt, ast.Declaration): self.visit(stmt)
        for fn in getattr(node, 'functions', []):
            self.visit(fn)
        for label, _ in self.pending_gotos:
            if label not in self.declared_labels:
                raise SemanticError(f"Semantic error: GOTO to non-existent label '{label}'.")

    def visit_Declaration(self, node):
        for item in node.variables:
            is_array = isinstance(item, ast.ArrayDecl)
            name = item.name.upper() if is_array else (item if isinstance(item, str) else str(item)).upper()
            if name in self.symbol_table:
                existing = self.symbol_table[name]
                # Allow parameter or result re-declaration with matching type
                if isinstance(existing, dict) and existing.get('param') and (existing['type'] is None or existing['type'] == node.data_type):
                    existing['type'] = node.data_type; continue
                if isinstance(existing, dict) and existing.get('result') and existing['type'] == node.data_type:
                    continue
                raise SemanticError(f"Error: Variable '{name}' already declared.")
            if is_array:
                if not isinstance(item.size, int) or item.size <= 0:
                    raise SemanticError(f"Error: Invalid size for array '{item.name}'.")
                self.symbol_table[name] = {'type': node.data_type, 'kind': 'array', 'size': item.size}
            else:
                self.symbol_table[name] = {'type': node.data_type, 'kind': 'scalar'}

    def visit_Assignment(self, node):
        if isinstance(node.variable, ast.ArrayAccess):
            info = self._get_symbol_info(node.variable.name)
            if info['kind'] != 'array':
                raise SemanticError(f"Error: Variable '{node.variable.name}' is not an array.")
            if self.visit(node.variable.index) not in ('INTEGER', 'REAL'):
                raise SemanticError(f"Error: Invalid index for array '{node.variable.name}'.")
            var_type = info['type']
        else:
            info = self._get_symbol_info(node.variable.name)
            if info['kind'] != 'scalar':
                raise SemanticError(f"Error: Variable '{node.variable.name}' is an array and requires an index.")
            var_type = info['type']
        expr_type = self.visit(node.expression)
        if var_type != expr_type and ('STRING' in (var_type, expr_type)):
            raise SemanticError(f"Error: Type mismatch between {var_type} and {expr_type}.")

    def visit_BinOp(self, node):
        lt = self.visit(node.left)
        rt = self.visit(node.right)
        op = node.op
        if op in ('.EQ.', '.NE.', '.LT.', '.LE.', '.GT.', '.GE.', '.AND.', '.OR.'):
            return 'LOGICAL'
        if lt == 'STRING' or rt == 'STRING':
            raise SemanticError(f"Error: Operation '{op}' not allowed with strings.")
        if op == '/' and lt == 'INTEGER' and rt == 'INTEGER':
            return 'INTEGER'
        return 'REAL' if lt == 'REAL' or rt == 'REAL' else 'INTEGER'

    def visit_UnaryOp(self, node):
        t = self.visit(node.expr)
        if node.op == '.NOT.' and t not in ('LOGICAL', 'INTEGER'):
            raise SemanticError(f"Error: .NOT. applied to invalid type ({t})")
        if node.op == '-' and t not in ('INTEGER', 'REAL'):
            raise SemanticError("Error: Unary '-' applied to non-numeric type.")
        return 'LOGICAL' if node.op == '.NOT.' else t

    def visit_Variable(self, node):
        return self._get_symbol_info(node.name)['type']

    def visit_ArrayAccess(self, node):
        info = self._get_symbol_info(node.name)
        if info['kind'] != 'array':
            raise SemanticError(f"Error: Variable '{node.name}' is not an array.")
        if self.visit(node.index) not in ('INTEGER', 'REAL'):
            raise SemanticError(f"Error: Invalid index for array '{node.name}'.")
        return info['type']

    def visit_Literal(self, node):
        return node.type

    def visit_FunctionCall(self, node):
        for arg in node.args: self.visit(arg)
        name = node.name.upper()
        if name in self.symbol_table:
            info = self._get_symbol_info(node.name)
            if info['kind'] == 'array':
                if len(node.args) != 1:
                    raise SemanticError(f"Error: Array '{node.name}' requires exactly one index.")
                if self.visit(node.args[0]) not in ('INTEGER', 'REAL'):
                    raise SemanticError(f"Error: Invalid index for array '{node.name}'.")
                return info['type']
        if not self._is_builtin_function(name) and name not in self.function_table:
            raise SemanticError(f"Error: Function '{node.name}' not declared.")
        if name in self.function_table:
            return self.function_table[name]['return_type']
        return bdefs.RETURN_TYPES.get(name, 'INTEGER')

    def visit_PrintStmt(self, node):
        for expr in node.expressions: self.visit(expr)

    def visit_CallStmt(self, node):
        self.visit_FunctionCall(ast.FunctionCall(node.name, node.args))

    def visit_ReadStmt(self, node):
        for var in node.variables:
            if isinstance(var, ast.ArrayAccess):
                info = self._get_symbol_info(var.name)
                if info['kind'] != 'array':
                    raise SemanticError(f"Error: Variable '{var.name}' in READ is not an array.")
                self.visit(var.index)
            else:
                self._get_symbol_info(var.name)

    def visit_IfStmt(self, node):
        if self.visit(node.condition) not in ('LOGICAL', 'INTEGER'):
            raise SemanticError("Error: IF condition must be LOGICAL or INTEGER.")
        for s in node.then_branch: self.visit(s)
        for s in (node.else_branch or []): self.visit(s)

    def visit_DoStmt(self, node):
        self._get_symbol_info(node.var.name)
        self.visit(node.start); self.visit(node.end)
        if node.step:
            self.visit(node.step)
            if isinstance(node.step, ast.Literal) and node.step.value == 0:
                raise SemanticError("Error: DO step cannot be zero.")
        for s in node.body: self.visit(s)
        if node.terminal: self.visit(node.terminal)

    def visit_GotoStmt(self, node):
        self.pending_gotos.append((node.label, None))

    def visit_LabelStmt(self, node):
        if node.label in self.declared_labels:
            raise SemanticError(f"Error: Duplicate label {node.label}.")
        self.declared_labels.add(node.label)
        self.visit(node.statement)

    def visit_ContinueStmt(self, node): return None
    def visit_ReturnStmt(self, node):   return None

    def _visit_routine(self, node, result_entry):
        saved = (self.symbol_table, self.declared_labels, self.pending_gotos, self.current_function)
        self.symbol_table    = {**result_entry, **{p.upper(): {'type': None, 'kind': 'scalar', 'param': True} for p in node.params}}
        self.declared_labels = set()
        self.pending_gotos   = []
        self.current_function = node.name.upper()
        node.body = self._normalize_do_loops(node.body)
        for item in node.body: self.visit(item)
        for label, _ in self.pending_gotos:
            if label not in self.declared_labels:
                raise SemanticError(f"Semantic error: GOTO to non-existent label '{label}' in '{node.name}'.")
        self.symbol_table, self.declared_labels, self.pending_gotos, self.current_function = saved

    def visit_FunctionDef(self, node):
        self._visit_routine(node, {node.name.upper(): {'type': node.return_type, 'kind': 'scalar', 'result': True}})

    def visit_SubroutineDef(self, node):
        self._visit_routine(node, {})