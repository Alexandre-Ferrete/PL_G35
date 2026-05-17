import re
from typing import List

BINOPS = {'ADD', 'SUB', 'MUL', 'DIV', 'POW', 'EQ', 'NE', 'LT', 'GT', 'LE', 'GE', 'AND', 'OR'}

def _parse_push_value(token: str):
    # token is the part after PUSH
    t = token.strip()
    if not t:
        return None
    up = t.upper()
    if up == '.TRUE.':
        return True
    if up == '.FALSE.':
        return False
    if t.startswith("'") and t.endswith("'"):
        return t[1:-1]
    try:
        if '.' in t:
            return float(t)
        return int(t)
    except ValueError:
        return t

def _format_push_value(val):
    if isinstance(val, bool):
        return '.TRUE.' if val else '.FALSE.'
    if isinstance(val, str):
        return f"'{val}'"
    return str(val)

class Optimizer:
    def __init__(self, level=0):
        self.level = level

    def optimize(self, instructions: List[str]) -> List[str]:
        instrs = list(instructions)
        if self.level == 1:
            instrs = self.constant_folding(instrs)
            instrs = self.peephole_optimization(instrs)
            # Note: remove_redundant_loads is unsafe without full stack analysis,
            # so it's disabled by default. Keep it implemented for future refinement.
            instrs = self.remove_unreachable_code(instrs)
            instrs = self.remove_dead_labels(instrs)
        elif self.level == 2:
            instrs = self.simplify_constant_branches(instrs)
            instrs = self.remove_dead_labels(instrs)
            instrs = self.remove_unreachable_code(instrs)
            instrs = self.remove_dead_labels(instrs)
            instrs = self.remove_jumps_to_next_label(instrs)
            instrs = self.remove_dead_labels(instrs)
        elif self.level >= 3:
            instrs = self.constant_folding(instrs)
            instrs = self.peephole_optimization(instrs)
            instrs = self.remove_unreachable_code(instrs)
            instrs = self.remove_dead_labels(instrs)

            instrs = self.simplify_constant_branches(instrs)
            instrs = self.remove_dead_labels(instrs)
            instrs = self.remove_unreachable_code(instrs)
            instrs = self.remove_dead_labels(instrs)
            instrs = self.remove_jumps_to_next_label(instrs)
            instrs = self.remove_dead_labels(instrs)
        return instrs

    def constant_folding(self, instrs: List[str]) -> List[str]:
        changed = True
        while changed:
            changed = False
            i = 0
            out = []
            while i < len(instrs):
                if i + 2 < len(instrs):
                    a = instrs[i].strip()
                    b = instrs[i + 1].strip()
                    c = instrs[i + 2].strip()
                    if a.upper().startswith(('PUSH ', 'PUSHI ', 'PUSHF ', 'PUSHS ')) and b.upper().startswith(('PUSH ', 'PUSHI ', 'PUSHF ', 'PUSHS ')) and c.split()[0].upper() in BINOPS:
                        v1 = _parse_push_value(a.split(maxsplit=1)[1])
                        v2 = _parse_push_value(b.split(maxsplit=1)[1])
                        op = c.split()[0].upper()
                        if isinstance(v1, (int, float, bool, str)) and isinstance(v2, (int, float, bool, str)):
                            try:
                                if op == 'ADD': res = v1 + v2
                                elif op == 'SUB': res = v1 - v2
                                elif op == 'MUL': res = v1 * v2
                                elif op == 'DIV':
                                    # integer division semantics preserved for ints
                                    if isinstance(v1, int) and isinstance(v2, int):
                                        res = int(v1 / v2) if v2 != 0 else 0
                                    else:
                                        res = v1 / v2 if v2 != 0 else 0
                                elif op == 'POW': res = v1 ** v2
                                elif op == 'EQ': res = 1 if v1 == v2 else 0
                                elif op == 'NE': res = 1 if v1 != v2 else 0
                                elif op == 'LT': res = 1 if v1 < v2 else 0
                                elif op == 'GT': res = 1 if v1 > v2 else 0
                                elif op == 'LE': res = 1 if v1 <= v2 else 0
                                elif op == 'GE': res = 1 if v1 >= v2 else 0
                                elif op == 'AND': res = 1 if v1 and v2 else 0
                                elif op == 'OR': res = 1 if v1 or v2 else 0
                                else:
                                    raise Exception('unsupported')
                                if isinstance(res, float) and not isinstance(res, bool):
                                    out.append(f"PUSHF {_format_push_value(res)}")
                                elif isinstance(res, str):
                                    out.append(f"PUSHS {_format_push_value(res)}")
                                else:
                                    out.append(f"PUSHI {_format_push_value(res)}")
                                i += 3
                                changed = True
                                continue
                            except Exception:
                                pass
                out.append(instrs[i])
                i += 1
            instrs = out
        return instrs

    def remove_dead_labels(self, instrs: List[str]) -> List[str]:
        # Collect referenced labels from JMP/JZ/JUMP/PUSHA/CALL (user functions)
        # Use case-insensitive matching because the VM treats labels case-insensitively
        referenced = set()
        for line in instrs:
            parts = line.split(maxsplit=1)
            if not parts:
                continue
            op = parts[0].upper()
            arg = parts[1] if len(parts) > 1 else None
            if op in ('JMP', 'JZ', 'JUMP', 'PUSHA') and arg:
                referenced.add(arg.split()[0].upper())
            if op == 'CALL' and arg:
                referenced.add(arg.split()[0].upper())

        out = []
        for idx, line in enumerate(instrs):
            stripped = line.strip()
            if stripped.endswith(':'):
                lbl = stripped[:-1]
                # Keep function labels and referenced labels (case-insensitive)
                if lbl.upper().startswith('FUNC_') or lbl.upper() in referenced:
                    out.append(line)
                else:
                    # drop the label line
                    continue
            else:
                out.append(line)
        return out

    def peephole_optimization(self, instrs: List[str]) -> List[str]:
        """Remove neutral operations: PUSH 0 / ADD, PUSH 1 / MUL, PUSH 0 / MUL"""
        changed = True
        while changed:
            changed = False
            out = []
            i = 0
            while i < len(instrs):
                if i + 1 < len(instrs):
                    curr = instrs[i].strip()
                    nextt = instrs[i + 1].strip()
                    
                    # PUSH 0 / ADD => remove both (neutral)
                    if curr.upper().startswith(('PUSH ', 'PUSHI ')) and nextt.upper() == 'ADD':
                        v = _parse_push_value(curr.split(maxsplit=1)[1])
                        if v == 0:
                            i += 2
                            changed = True
                            continue
                    
                    # PUSH 1 / MUL => remove both (neutral)
                    if curr.upper().startswith(('PUSH ', 'PUSHI ')) and nextt.upper() == 'MUL':
                        v = _parse_push_value(curr.split(maxsplit=1)[1])
                        if v == 1:
                            i += 2
                            changed = True
                            continue
                    
                    # PUSH 0 / MUL => replace with PUSH 0
                    if curr.upper().startswith(('PUSH ', 'PUSHI ')) and nextt.upper() == 'MUL':
                        v = _parse_push_value(curr.split(maxsplit=1)[1])
                        if v == 0:
                            out.append("PUSHI 0")
                            i += 2
                            changed = True
                            continue
                
                out.append(instrs[i])
                i += 1
            instrs = out
        return instrs

    def remove_unreachable_code(self, instrs: List[str]) -> List[str]:
        """Remove code after unconditional jumps until next label"""
        out = []
        i = 0
        while i < len(instrs):
            out.append(instrs[i])
            line = instrs[i].strip()
            
            # If this is an unconditional jump, skip until next label
            if line.upper().startswith(('JMP ', 'JUMP ')):
                i += 1
                while i < len(instrs):
                    line = instrs[i].strip()
                    # Stop if we hit a label
                    if line.endswith(':'):
                        break
                    i += 1
                continue
            
            i += 1
        return out

    def simplify_constant_branches(self, instrs: List[str]) -> List[str]:
        """Simplify branches when the condition is a compile-time constant."""
        out = []
        i = 0
        while i < len(instrs):
            if i + 1 < len(instrs):
                curr = instrs[i].strip()
                nxt = instrs[i + 1].strip()
                parts = nxt.split(maxsplit=1)
                if len(parts) == 2 and parts[0].upper() == 'JZ':
                    value = None
                    if curr.upper().startswith(('PUSH ', 'PUSHI ', 'PUSHF ', 'PUSHS ')):
                        try:
                            value = _parse_push_value(curr.split(maxsplit=1)[1])
                        except Exception:
                            value = None
                    if isinstance(value, (int, float, bool)):
                        target = parts[1].strip()
                        if value == 0 or value is False:
                            # Always jump: remove the push and turn JZ into JMP.
                            out.append(f"JMP {target}")
                        else:
                            # Never jump: remove both instructions.
                            pass
                        i += 2
                        continue
            out.append(instrs[i])
            i += 1
        return out

    def remove_jumps_to_next_label(self, instrs: List[str]) -> List[str]:
        """Remove unconditional jumps that target the next fallthrough label block."""
        out = []
        i = 0
        while i < len(instrs):
            line = instrs[i].strip()
            parts = line.split(maxsplit=1)
            if len(parts) == 2 and parts[0].upper() in ('JMP', 'JUMP'):
                target = parts[1].strip().upper()
                j = i + 1
                labels_ahead = set()
                while j < len(instrs):
                    nxt = instrs[j].strip()
                    if not nxt.endswith(':'):
                        break
                    labels_ahead.add(nxt[:-1].strip().upper())
                    j += 1
                if target in labels_ahead:
                    i += 1
                    continue
            out.append(instrs[i])
            i += 1
        return out

    def remove_redundant_loads(self, instrs: List[str]) -> List[str]:
        """Remove STOREX / PUSHX patterns (store then immediately load is redundant)"""
        out = []
        i = 0
        while i < len(instrs):
            if i + 1 < len(instrs):
                curr = instrs[i].strip().upper()
                nextt = instrs[i + 1].strip().upper()
                
                # STOREL X / PUSHL X => just remove STOREL, keep PUSHL
                if curr.startswith('STOREL ') and nextt.startswith('PUSHL '):
                    curr_var = curr.split()[1]
                    next_var = nextt.split()[1]
                    if curr_var == next_var:
                        # Keep the STORE, skip the immediate LOAD (PUSHL)
                        out.append(instrs[i])
                        i += 2
                        continue
                
                # STOREG X / PUSHG X => just remove STOREG, keep PUSHG
                if curr.startswith('STOREG ') and nextt.startswith('PUSHG '):
                    curr_var = curr.split()[1]
                    next_var = nextt.split()[1]
                    if curr_var == next_var:
                        # Keep the STORE, skip the immediate LOAD (PUSHG)
                        out.append(instrs[i])
                        i += 2
                        continue
            
            out.append(instrs[i])
            i += 1
        return out