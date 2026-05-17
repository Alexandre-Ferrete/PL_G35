import ast_nodes as ast
try:
    from src import builtin_defs as bdefs
except ImportError:
    import builtin_defs as bdefs
from semantic import SemanticError

# Tabelas de mapeamento: operador Fortran -> instrução BM
_INT_ARITH = {'+': 'add', '-': 'sub', '*': 'mul', '/': 'div', '%': 'mod'}
_REAL_ARITH = {'+': 'fadd', '-': 'fsub', '*': 'fmul', '/': 'fdiv'}
_INT_CMP  = {'.LT.': 'inf',  '.LE.': 'infeq', '.GT.': 'sup',  '.GE.': 'supeq'}
_REAL_CMP = {'.LT.': 'finf', '.LE.': 'finfeq', '.GT.': 'fsup', '.GE.': 'fsupeq'}
_WRITE    = {'INTEGER': 'writei', 'LOGICAL': 'writei', 'REAL': 'writef', 'STRING': 'writes'}
_READ_CVT = {'INTEGER': 'atoi', 'REAL': 'atof'}


class BMCodeGenerator:
    def __init__(self, symbol_table=None, function_table=None):
        self.symbol_table   = symbol_table or {}
        self.function_table = function_table or {}
        self.instructions   = []
        self._label_n       = 0
        self.global_layout  = {}
        self.func_layouts   = {}   # func_name -> {slots, slot_count, array_inits, result_offset}
        self.func_labels    = {}   # func_name -> asm label string
        self.current_fn     = None
        self.current_layout = {}
        self.temp_stack     = []   # rastreia blocos pushn 2 dos DO

    # --- Infra ---

    def new_label(self, hint='L'):
        self._label_n += 1
        return f"{hint}{self._label_n}"

    def emit(self, s): self.instructions.append(s)

    @staticmethod
    def _make_label(name: str) -> str:
        """Sanitiza nomes de funções para labels BM (a VM não tolera underscores)."""
        return f"F{name.replace('_', '')}"

    def visit(self, node):
        if node is None: return None
        return getattr(self, f'visit_{type(node).__name__}', self._nyi)(node)

    def _nyi(self, node):
        raise NotImplementedError(f"No visitor for {type(node).__name__}")

    # --- Layout: mapeia nomes de variáveis para offsets gp/fp ---

    def _decl_slot(self, variable, data_type, offset):
        if isinstance(variable, ast.ArrayDecl):
            return variable.name.upper(), {'kind': 'array', 'type': data_type, 'offset': offset, 'size': variable.size}
        name = (variable if isinstance(variable, str) else variable.name).upper()
        return name, {'kind': 'scalar', 'type': data_type, 'offset': offset}

    def _build_global_layout(self, body):
        slots, offset, array_inits = {}, 0, []
        for stmt in body:
            if not isinstance(stmt, ast.Declaration): continue
            for v in stmt.variables:
                name, slot = self._decl_slot(v, stmt.data_type, offset)
                if name in slots: continue
                slots[name] = slot
                if slot['kind'] == 'array':
                    array_inits.append((name, offset, slot['size']))
                offset += 1
        self.global_layout = {'slots': slots, 'slot_count': offset, 'array_inits': array_inits}

    def _build_func_layout(self, node):
        name = node.name.upper()
        if name in self.func_layouts: return
        params = [p.upper() for p in getattr(node, 'params', [])]
        is_func = getattr(node, 'return_type', 'VOID') != 'VOID'
        argc = len(params)
        
        # CORREÇÃO: Parâmetros começam em -2 devido ao Return Address em -1
        slots = {p: {'kind': 'param', 'type': None, 'offset': -(argc - i)} for i, p in enumerate(params)}
        if is_func:
            # CORREÇÃO: Valor de retorno fica logo abaixo dos parâmetros
            slots[name] = {'kind': 'result', 'type': node.return_type, 'offset': -(argc + 1)}
            
        seen = set(params) | ({name} if is_func else set())
        
        offset, array_inits = 0, []
        for stmt in getattr(node, 'body', []):
            if not isinstance(stmt, ast.Declaration): continue
            for v in stmt.variables:
                vname, slot = self._decl_slot(v, stmt.data_type, offset)
                if vname in seen: continue
                seen.add(vname); slot['offset'] = offset; slots[vname] = slot
                if slot['kind'] == 'array': array_inits.append((vname, offset, slot['size']))
                offset += 1
                
        # Preencher tipos dos parâmetros a partir das declarações
        for stmt in getattr(node, 'body', []):
            if not isinstance(stmt, ast.Declaration): continue
            for v in stmt.variables:
                vname = (v if isinstance(v, str) else getattr(v, 'name', str(v))).upper()
                if vname in slots and slots[vname]['kind'] == 'param':
                    slots[vname]['type'] = stmt.data_type
                    
        self.func_layouts[name] = {
            'slots': slots, 
            'slot_count': offset,
            'array_inits': array_inits,
            'result_offset': -(argc + 1) if is_func else None, 
            'param_count': argc,
        }
        self.func_labels[name] = self._make_label(name)

    def _find(self, name):
        key = name.upper()
        if self.current_fn and key in self.current_layout.get('slots', {}):
            return 'local', self.current_layout['slots'][key]
        if key in self.global_layout.get('slots', {}):
            return 'global', self.global_layout['slots'][key]
        raise SemanticError(f"Variable '{name}' not found in layout.")

    def _load(self, scope, offset):
        self.emit(f"{'pushl' if scope == 'local' else 'pushg'} {offset}")

    def _store(self, scope, offset):
        self.emit(f"{'storel' if scope == 'local' else 'storeg'} {offset}")

    def _temp_base(self):
        layout = self.current_layout or self.global_layout
        if self.current_fn:
            return layout.get('slot_count', 0) + sum(self.temp_stack)
        else:
            # No escopo global, as variáveis começam em 0, logo o próximo espaço livre é slot_count
            return layout.get('slot_count', 0) + sum(self.temp_stack)

    def _array_init(self, name, offset, size, scope):
        # Coloca primeiro o tamanho na pilha e depois chama o allocn sozinho
        self.emit(f"pushi {size}")
        self.emit("allocn")
        self.emit(f"{'storeg' if scope == 'global' else 'storel'} {offset}")

    # --- Coerção de tipos ---

    def _coerce2real(self, lt, rt):
        if lt == 'INTEGER' and rt == 'REAL':   self.emit('swap'); self.emit('itof'); self.emit('swap')
        elif lt == 'REAL' and rt == 'INTEGER': self.emit('itof')

    def _coerce2int(self, lt, rt):
        if   lt == 'REAL' and rt == 'INTEGER': self.emit('swap'); self.emit('ftoi'); self.emit('swap')
        elif lt == 'INTEGER' and rt == 'REAL': self.emit('ftoi')
        elif lt == 'REAL' and rt == 'REAL':    self.emit('ftoi'); self.emit('swap'); self.emit('ftoi'); self.emit('swap')

    def _convert(self, src, dst):
        if src == dst: return
        self.emit('itof' if dst == 'REAL' else 'ftoi')

    # --- Visitors ---

    def visit_Program(self, node):
        self._build_global_layout(node.body)
        self.emit('start')
        if self.global_layout['slot_count']:
            self.emit(f"pushn {self.global_layout['slot_count']}")
        for name, offset, size in self.global_layout['array_inits']:
            self._array_init(name, offset, size, 'global')
        for stmt in node.body:
            if not isinstance(stmt, ast.Declaration): self.visit(stmt)
        self.emit('stop')
        for fn in getattr(node, 'functions', []): self.visit(fn)

    def visit_Declaration(self, node): pass

    def visit_Literal(self, node):
        if node.type == 'INTEGER':   self.emit(f"pushi {int(node.value)}")
        elif node.type == 'REAL':    self.emit(f"pushf {float(node.value)}")
        elif node.type == 'LOGICAL': self.emit(f"pushi {1 if node.value in [True, 1, '.TRUE.', 'TRUE'] else 0}")
        else:                        self.emit(f'pushs "{str(node.value)}"')
        return node.type

    def visit_Variable(self, node):
        scope, info = self._find(node.name)
        self._load(scope, info['offset'])
        return info['type']

    def visit_ArrayAccess(self, node):
        scope, info = self._find(node.name)
        self._load(scope, info['offset'])
        self.visit(node.index)
        self.emit('pushi 1'); self.emit('sub'); self.emit('loadn')
        return info['type']

    def visit_UnaryOp(self, node):
        t = self.visit(node.expr)
        op = node.op.upper()
        if op == '-':
            if t == 'REAL': self.emit('pushf 0.0'); self.emit('swap'); self.emit('fsub')
            else:           self.emit('pushi 0');   self.emit('swap'); self.emit('sub')
        elif op == '.NOT.':
            self.emit('not')
        return t

    def visit_BinOp(self, node):
        op = node.op.upper()
        
        # INTERCETAR A POTÊNCIA (**) ANTES DE IR AO DICIONÁRIO
        if op == '**':
            # 1. Avalia a base (o lado esquerdo) e põe o valor na stack
            lt = self.visit(node.left)
            
            # 2. Se for um quadrado (** 2), duplicamos o valor na stack e multiplicamos!
            if isinstance(node.right, ast.Literal) and node.right.value == 2:
                self.emit('dup 1') # Duplica o valor que está no topo da stack
                if lt == 'REAL':
                    self.emit('fmul')
                    return 'REAL'
                else:
                    self.emit('mul')
                    return 'INTEGER'
            else:
                # Se meterem um expoente que não seja 2, avisamos que a VM não aguenta
                raise SemanticError("O backend da VM apenas suporta potencias de expoente 2 fixo em tempo de execucao.")

        # Código original do teu visit_BinOp para o resto dos operadores
        lt = self.visit(node.left)
        rt = self.visit(node.right)
        use_real = lt == 'REAL' or rt == 'REAL'

        if op == '.AND.':   self.emit('mul');  return 'INTEGER'
        if op == '.OR.':    self.emit('add');  self.emit('pushi 0'); self.emit('sup'); return 'INTEGER'
        if op in ('.EQ.', '.NE.'):
            if use_real: self._coerce2real(lt, rt)
            self.emit('equal')
            if op == '.NE.': self.emit('not')
            return 'INTEGER'
        if op in _INT_CMP:
            if use_real: self._coerce2real(lt, rt); self.emit(_REAL_CMP[op])
            else:        self.emit(_INT_CMP[op])
            return 'INTEGER'
        if use_real:
            self._coerce2real(lt, rt); self.emit(_REAL_ARITH.get(op, op)); return 'REAL'
        self.emit(_INT_ARITH.get(op, op)); return 'INTEGER'

    def visit_FunctionCall(self, node):
        name = node.name.upper()
        try:
            scope, info = self._find(node.name)
            if info['kind'] == 'array':
                self._load(scope, info['offset']); self.visit(node.args[0])
                self.emit('pushi 1'); self.emit('sub'); self.emit('loadn')
                return info['type']
        except SemanticError: pass

        if bdefs.is_builtin(name):
            arg_types = [self.visit(a) for a in node.args]
            return self._emit_builtin(name, arg_types)

        info = self.function_table.get(name, {})
        ret = info.get('return_type', 'INTEGER')
        if ret != 'VOID': self.emit('pushi 0')
        for a in node.args: self.visit(a)
        label = self.func_labels.setdefault(name, self._make_label(name))
        self.emit(f'pusha {label}'); self.emit('call')
        if node.args: self.emit(f'pop {len(node.args)}')
        return ret

    def _emit_builtin(self, name, arg_types):
        t = arg_types[0] if arg_types else 'INTEGER'
        if name == 'MOD':  self._coerce2int(arg_types[0], arg_types[1]); self.emit('mod'); return 'INTEGER'
        if name == 'INT':  self._convert(t, 'INTEGER'); return 'INTEGER'
        if name == 'REAL': self._convert(t, 'REAL');    return 'REAL'
        if name == 'ABS':  return self._emit_abs(t)
        if name in ('SIN', 'COS', 'TAN'):
            self._convert(t, 'REAL')
            self.emit({'SIN': 'fsin', 'COS': 'fcos', 'TAN': 'ftan'}[name])
            return 'REAL'
        raise SemanticError(f"Builtin '{name}' not supported by BM backend.")

    def _emit_abs(self, t):
        pos, end = self.new_label('ABSP'), self.new_label('ABSE')
        self.emit('dup 1')
        if t == 'REAL':
            self.emit('pushf 0.0'); self.emit('finf'); self.emit(f'jz {pos}')
            self.emit('pushf 0.0'); self.emit('swap'); self.emit('fsub')
        else:
            self.emit('pushi 0'); self.emit('inf'); self.emit(f'jz {pos}')
            self.emit('pushi 0'); self.emit('swap'); self.emit('sub')
        self.emit(f'jump {end}'); self.emit(f'{pos}:'); self.emit(f'{end}:')
        return t

    def visit_Assignment(self, node):
        if isinstance(node.variable, ast.ArrayAccess):
            scope, info = self._find(node.variable.name)
            self._load(scope, info['offset'])
            self.visit(node.variable.index); self.emit('pushi 1'); self.emit('sub')
            self.visit(node.expression); self.emit('storen'); return
        name = node.variable.name.upper()
        if self.current_fn and name == self.current_fn:
            slot = self.current_layout['slots'].get(name)
            if slot and slot['kind'] == 'result':
                self.visit(node.expression); self.emit(f"storel {slot['offset']}"); return
        scope, info = self._find(node.variable.name)
        self.visit(node.expression); self._store(scope, info['offset'])

    def visit_PrintStmt(self, node):
        for i, expr in enumerate(node.expressions):
            if i > 0:
                self.emit('pushs " "')
                self.emit('writes')
                
            t = self.visit(expr)
            self.emit(_WRITE.get(t, 'writei'))
        self.emit('writeln')

    def visit_ReadStmt(self, node):
        for var in node.variables:
            if isinstance(var, ast.ArrayAccess):
                scope, info = self._find(var.name)
                self._load(scope, info['offset'])
                self.visit(var.index); self.emit('pushi 1'); self.emit('sub')
                self.emit('read'); self.emit(_READ_CVT.get(info['type'], 'atoi'))
                self.emit('storen')
            else:
                scope, info = self._find(var.name)
                self.emit('read'); self.emit(_READ_CVT.get(info['type'], 'atoi'))
                self._store(scope, info['offset'])

    def visit_IfStmt(self, node):
        l_end = self.new_label('IFE')
        self.visit(node.condition)
        if node.else_branch:
            l_else = self.new_label('IFL')
            self.emit(f'jz {l_else}')
            for s in node.then_branch: self.visit(s)
            self.emit(f'jump {l_end}'); self.emit(f'{l_else}:')
            for s in node.else_branch: self.visit(s)
        else:
            self.emit(f'jz {l_end}')
            for s in node.then_branch: self.visit(s)
        self.emit(f'{l_end}:')

    def visit_DoStmt(self, node):
        scope, info = self._find(node.var.name)
        tb = self._temp_base()
        self.emit('pushn 2'); self.temp_stack.append(2)
        self.visit(node.start); self._store(scope, info['offset'])
        self.visit(node.end);   self.emit(f'storel {tb}')
        if node.step: self.visit(node.step)
        else:         self.emit('pushi 1')
        self.emit(f'storel {tb + 1}')

        chk, bdy, end, neg = (self.new_label(x) for x in ('DOCHK', 'DOBDY', 'DOEND', 'DONEG'))
        self.emit(f'{chk}:')
        self.emit(f'pushl {tb + 1}'); self.emit('pushi 0'); self.emit('sup'); self.emit(f'jz {neg}')
        self._load(scope, info['offset']); self.emit(f'pushl {tb}'); self.emit('infeq')
        self.emit(f'jz {end}'); self.emit(f'jump {bdy}')
        self.emit(f'{neg}:')
        self._load(scope, info['offset']); self.emit(f'pushl {tb}'); self.emit('supeq')
        self.emit(f'jz {end}')
        self.emit(f'{bdy}:')
        for stmt in node.body: self.visit(stmt)
        if node.terminal is not None:
            self.emit(f'USERL{node.label}:'); self.visit(node.terminal)
        self._load(scope, info['offset']); self.emit(f'pushl {tb + 1}'); self.emit('add')
        self._store(scope, info['offset'])
        self.emit(f'jump {chk}'); self.emit(f'{end}:'); self.emit('pop 2'); self.temp_stack.pop()

    def visit_GotoStmt(self, node):     self.emit(f'jump USERL{node.label}')
    def visit_LabelStmt(self, node):    self.emit(f'USERL{node.label}:'); self.visit(node.statement)
    def visit_ContinueStmt(self, node): self.emit('nop')
    def visit_ReturnStmt(self, node):   self.emit('return')

    def visit_CallStmt(self, node):
        name = node.name.upper()
        for a in node.args: self.visit(a)
        label = self.func_labels.setdefault(name, self._make_label(name))
        self.emit(f'pusha {label}'); self.emit('call')
        # Write modified args back in reverse push order (Fortran pass-by-reference semantics).
        # After RETURN the stack still holds the (possibly modified) arg copies.
        for a in reversed(node.args):
            if isinstance(a, ast.Variable):
                scope, info = self._find(a.name)
                self._store(scope, info['offset'])
            else:
                self.emit('pop 1')

    def _visit_routine(self, node, return_type):
        name = node.name.upper()
        self._build_func_layout(node)
        label = self.func_labels.setdefault(name, self._make_label(name))
        self.emit(f'{label}:')
        saved = (self.current_fn, self.current_layout, self.temp_stack)
        self.current_fn, self.current_layout, self.temp_stack = name, self.func_layouts[name], []
        if self.current_layout['slot_count']:
            self.emit(f"pushn {self.current_layout['slot_count']}")
        for vname, offset, size in self.current_layout['array_inits']:
            self._array_init(vname, offset, size, 'local')
        for stmt in node.body:
            if not isinstance(stmt, ast.Declaration): self.visit(stmt)
        self.emit('return')
        self.current_fn, self.current_layout, self.temp_stack = saved

    def visit_FunctionDef(self, node):   self._visit_routine(node, node.return_type)
    def visit_SubroutineDef(self, node): self._visit_routine(node, 'VOID')

    def generate(self, tree):
        for fn in getattr(tree, 'functions', []):
            self._build_func_layout(fn)
        self.visit(tree)
        return '\n'.join(self.instructions)