import sys
import re
import os

class Token:
    def __init__(self, type_, value, line=0):
        self.type = type_
        self.value = value
        self.line = line

KEYWORDS = {
    'execute', 'self', 'invoque', 'at', 'existe', 'give', 'to',
    'imprimate', 'choise', 'with', 'message', 'check', 'do', 'no',
    'but', 'absolute', 'exponentiate', 'value', 'from', 'doing',
    'onTrue', 'onFalse', 'for', 'and', 'exist',
}

def tokenize(source):
    tokens = []
    lines = source.split('\n')
    for lineno, line in enumerate(lines, 1):
        i = 0
        while i < len(line):
            if line[i] in ' \t':
                i += 1
                continue
            if line[i] == '[':
                j = line.find(']', i)
                j = j if j != -1 else len(line) - 1
                tokens.append(Token('COMMENT', line[i:j+1], lineno))
                i = j + 1
                continue
            if line[i] == '<' and i+1 < len(line) and line[i+1] == '"':
                j = line.find('">', i+2)
                if j == -1: j = len(line) - 2
                tokens.append(Token('STRING_LIT', line[i+2:j], lineno))
                i = j + 2
                continue
            if line[i] == '"':
                j = line.find('"', i+1)
                j = j if j != -1 else len(line) - 1
                tokens.append(Token('STRING', line[i+1:j], lineno))
                i = j + 1
                continue
            if line[i] == '{':
                j = line.find('}', i)
                j = j if j != -1 else len(line) - 1
                tokens.append(Token('BRACE', line[i+1:j], lineno))
                i = j + 1
                continue
            if line[i].isdigit() or (line[i] == '-' and i+1 < len(line) and line[i+1].isdigit()):
                j = i + 1 if line[i] == '-' else i
                while j < len(line) and (line[j].isdigit() or line[j] == '.'): j += 1
                tokens.append(Token('NUMBER', line[i:j], lineno))
                i = j
                continue
            if i+1 < len(line) and line[i:i+2] in ('>=', '<=', '!=', '=='):
                tokens.append(Token('OP', line[i:i+2], lineno))
                i += 2
                continue
            if line[i] in '+-*/%<>=!':
                tokens.append(Token('OP', line[i], lineno))
                i += 1
                continue
            if line[i] == '/':
                tokens.append(Token('SLASH', '/', lineno))
                i += 1
                continue
            if line[i] == ':':
                tokens.append(Token('COLON', ':', lineno))
                i += 1
                continue
            if line[i].isalpha() or line[i] == '_':
                j = i
                while j < len(line) and (line[j].isalnum() or line[j] in '_$'): j += 1
                word = line[i:j]
                if '$' in word: tokens.append(Token('METHOD_CALL', word, lineno))
                elif word in KEYWORDS: tokens.append(Token('KW', word, lineno))
                else: tokens.append(Token('IDENT', word, lineno))
                i = j
                continue
            tokens.append(Token('OTHER', line[i], lineno))
            i += 1
        tokens.append(Token('NEWLINE', '\n', lineno))
    return tokens

class MacLaireError(Exception):
    def __init__(self, message, line=0):
        self.message = message
        self.line = line
        super().__init__(message)

class Interpreter:
    def __init__(self, source, invoque_dir='.'):
        self.source = source
        self.invoque_dir = invoque_dir
        self.vars = {}
        self.file_map = {}
        self.initialized = False

    def _strip_comment(self, line):
        return re.sub(r'\[.*?\]', '', line).strip()

    def _get_val(self, token):
        if isinstance(token, (int, float)): return token
        s = str(token)
        if re.match(r'^-?\d+(\.\d+)?$', s):
            f = float(s)
            return int(f) if f == int(f) else f
        return self.vars.get(s, s)

    def _eval_expr(self, parts):
        if not parts: return None
        if len(parts) == 1: return self._get_val(parts[0])
        if len(parts) >= 3:
            a = self._get_val(parts[0])
            op = parts[1]
            b = self._get_val(parts[2])
            ops = {
                '+': lambda: (str(a)+str(b) if isinstance(a,str) or isinstance(b,str) else a+b),
                '-': lambda: a - b, '*': lambda: a * b,
                '/': lambda: a / b if b != 0 else exec('raise Exception("division by zero")'),
                '==': lambda: a == b, '!=': lambda: a != b,
                '>': lambda: a > b, '<': lambda: a < b,
                '>=': lambda: a >= b, '<=': lambda: a <= b
            }
            return ops[op]()
        return ' '.join(str(self._get_val(p)) for p in parts)

    def _collect_block(self, lines, start):
        body, depth, i = [], 0, start
        while i < len(lines):
            l = self._strip_comment(lines[i])
            if l == '/':
                if depth == 0: return body, i + 1
                depth -= 1
            elif re.search(r'\bdo\b', l) or l.endswith(':'): depth += 1
            body.append(lines[i])
            i += 1
        return body, i

    def run(self):
        lines = [l for l in self.source.split('\n') if self._strip_comment(l)]
        self._exec_lines(lines)

    def _exec_lines(self, lines):
        i = 0
        while i < len(lines):
            res = self._exec_line(lines, i)
            i = res if res is not None else i + 1

    def _exec_line(self, lines, i):
        line = self._strip_comment(lines[i])
        if not line: return None
        parts = line.split()
        cmd = parts[0]

        if cmd == 'execute' and parts[1] == '{self}':
            self.initialized = True
            return None
        if not self.initialized: raise MacLaireError("Missing 'execute {self}'", i+1)

        if cmd == 'existe':
            self.vars[parts[1]] = None
        elif 'give' in parts and 'to' in parts:
            idx = parts.index('give')
            self.vars[parts[0]] = self._eval_expr(parts[idx+2:])
        elif cmd.startswith('imprimate'):
            if 'variable' in cmd:
                print(self.vars.get(parts[1], "Undefined"))
            else:
                m = re.search(r'<"(.*?)">', lines[i])
                print(m.group(1) if m else "")
        elif cmd == 'choise':
            msg = re.search(r'<"(.*?)">', lines[i]).group(1)
            target = re.search(r'give to (\w+)', lines[i]).group(1)
            val = input(msg + " ")
            self.vars[target] = int(val) if 'int' in lines[i] else val
        elif cmd == 'check':
            cond = line[6:line.find('do')].strip()
            body, next_i = self._collect_block(lines, i+1)
            if self._eval_expr(cond.split()): self._exec_lines(body)
            return next_i
        elif cmd == 'onTrue':
            cond = line[7:line.find('do')].strip().split()
            body, next_i = self._collect_block(lines, i+1)
            while self._eval_expr(cond): self._exec_lines(body)
            return next_i
        return None

if __name__ == '__main__':
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r', encoding='utf-8') as f:
            Interpreter(f.read()).run()