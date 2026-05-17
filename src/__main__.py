import argparse
import sys
import os

# Ensure src/ is in sys.path for direct script execution
_src_dir = os.path.dirname(os.path.abspath(__file__))
if _src_dir not in sys.path:
    # Garante que o diretório `src/` está no `sys.path` quando executado como script.
    sys.path.insert(0, _src_dir)

from lexer import lexer
from parser import parser
from semantic import SemanticAnalyzer
from bm_codegen import BMCodeGenerator

def main():
    # Ponto de entrada do CLI: uso obrigatório:
    #   python src/__main__.py main <test.f> <opt(0|1|2|3)> <output.asm> [--vm]
    parser_cli = argparse.ArgumentParser(description='Compilador Fortran 77 para BM')
    parser_cli.add_argument('mode', choices=['main'], help="Subcomando. Use 'main' para compilar um ficheiro de teste")
    parser_cli.add_argument('test', help='Ficheiro fonte (.f) a compilar')
    parser_cli.add_argument('opt', choices=['0', '1', '2', '3'], help='Nível de otimização: 0 (sem), 1 (O1), 2 (O2), 3 (O1+O2)')
    parser_cli.add_argument('output', help='Ficheiro de saída .asm')
    parser_cli.add_argument('--vm', action='store_true', help='Executar na VM após compilar (opcional)')
    args = parser_cli.parse_args()

    try:
        with open(args.test, 'r') as f:
            data = f.read()

        print(f"Compiling: {args.test}")
        print("-" * 40)

        # 1. Parsing e Análise Semântica Tradicionais
        tree = parser.parse(data)
        analyzer = SemanticAnalyzer()
        analyzer.analyze(tree)

        opt_level = int(args.opt)

        # 2. [FASE PRÉ-CODEGEN] Otimização da AST (Níveis 2 e 3)
        if opt_level in (2, 3):
            try:
                from ast_optimizer import ASTOptimizer
                tree = ASTOptimizer().optimize(tree)
                print("[OPT] Nível de Otimização AST (Pré-Codegen) aplicado com sucesso.")
            except Exception as e:
                print(f"AST Optimizer error: {e}")

        # 3. Geração de Código Máquina
        code = BMCodeGenerator(analyzer.symbol_table, analyzer.function_table).generate(tree)

        # 4. [FASE PÓS-CODEGEN] Otimização Textual/Peephole (Níveis 1 e 3)
        if opt_level in (1, 3):
            try:
                from optimizer import Optimizer
                instr_lines = code.splitlines()
                # Forçamos o level=3 interno para invocar todas as táticas de texto juntas
                opt = Optimizer(level=opt_level)
                optimized = opt.optimize(instr_lines)
                code = "\n".join(optimized)
                print("[OPT] Nível de Otimização Assembly (Pós-Codegen) aplicado com sucesso.")
            except Exception as e:
                print(f"Post-codegen Optimizer error: {e}")
        
        # Normalize to Unix line endings (LF) and write bytes directly
        code_clean = code.replace('\r\n', '\n').replace('\r', '\n')
        if not code_clean.endswith('\n'):
            code_clean += '\n'

        with open(args.output, 'wb') as f:
            f.write(code_clean.encode('ascii')) 
            
        print(f"[OK] Code generated: {args.output}")

        if args.vm:
            print("-" * 40)
            print("BM code generated. Run the output with the professor-provided VM.")
            print("-" * 40)
        else:
            print("BM code generated. Use the professor-provided VM to execute it.")

    except FileNotFoundError:
        print(f"Error: File '{args.input}' not found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()