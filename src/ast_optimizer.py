import ast_nodes as ast

class ASTOptimizer:
    def optimize(self, node):
        if node is None:
            return None
        method_name = f'optimize_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_optimize)
        return visitor(node)

    def generic_optimize(self, node):
        # Percorre recursivamente todas as propriedades do nó à procura de sub-nós AST
        for attr, value in list(node.__dict__.items()):
            if isinstance(value, list):
                new_list = []
                for item in value:
                    if isinstance(item, ast.Node):
                        new_list.append(self.optimize(item))
                    else:
                        new_list.append(item)
                setattr(node, attr, new_list)
            elif isinstance(value, ast.Node):
                setattr(node, attr, self.optimize(value))
        return node

    def optimize_BinOp(self, node):
        # Primeiro, otimiza os ramos filhos
        node.left = self.optimize(node.left)
        node.right = self.optimize(node.right)
        
        # Se ambos os lados forem literais numéricos, resolvemos a conta já!
        if isinstance(node.left, ast.Literal) and isinstance(node.right, ast.Literal):
            v1 = node.left.value
            v2 = node.right.value
            op = node.op.upper()
            
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                try:
                    if op == '+': res = v1 + v2
                    elif op == '-': res = v1 - v2
                    elif op == '*': res = v1 * v2
                    elif op == '/': res = v1 / v2 if v2 != 0 else 0
                    elif op == '**': res = v1 ** v2
                    elif op in ('.EQ.', 'EQ'): res = True if v1 == v2 else False
                    elif op in ('.NE.', 'NE'): res = True if v1 != v2 else False
                    elif op in ('.LT.', 'LT'): res = True if v1 < v2 else False
                    elif op in ('.GT.', 'GT'): res = True if v1 > v2 else False
                    elif op in ('.LE.', 'LE'): res = True if v1 <= v2 else False
                    elif op in ('.GE.', 'GE'): res = True if v1 >= v2 else False
                    else: return node
                    
                    if isinstance(res, bool):
                        return ast.Literal('.TRUE.' if res else '.FALSE.', 'LOGICAL')
                    t = 'REAL' if isinstance(res, float) else 'INTEGER'
                    return ast.Literal(res, t)
                except:
                    return node
        return node

    def optimize_UnaryOp(self, node):
        node.expr = self.optimize(node.expr)
        if node.op == '-' and isinstance(node.expr, ast.Literal) and node.expr.type in ('INTEGER', 'REAL'):
            return ast.Literal(-node.expr.value, node.expr.type)
        if node.op.upper() in ('.NOT.', 'NOT') and isinstance(node.expr, ast.Literal) and node.expr.type == 'LOGICAL':
            val = node.expr.value in (True, 1, '.TRUE.', 'TRUE')
            return ast.Literal('.FALSE.' if val else '.TRUE.', 'LOGICAL')
        return node