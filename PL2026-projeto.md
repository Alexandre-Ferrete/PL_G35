# Construção de um Compilador para Fortran 77 Standard

**Projeto de Processamento de Linguagens 2026**  
Data: 2026-03-10  

## Objetivo
Desenvolver um compilador para a linguagem Fortran 77 (ANSI X3.9-1978).

O compilador deverá:
- Analisar código Fortran
- Interpretar
- Traduzir para representação intermédia ou código de máquina (VM)

---

## Etapas do Projeto

### 1. Análise Léxica
- Implementar lexer com `ply.lex`
- Identificar:
  - Palavras-chave (PROGRAM, INTEGER, REAL, etc.)
  - Identificadores
  - Números
  - Operadores
  - Símbolos especiais

---

### 2. Análise Sintática
- Implementar parser com `ply.yacc`
- Validar estrutura gramatical

---

### 3. Análise Semântica
- Verificar:
  - Tipos
  - Declarações
  - Coerência do código

---

### 4. Tradução de Código
- Gerar:
  - Código VM diretamente **ou**
  - Representação intermédia

---

### 5. Otimização (Valorização)
- Eliminar redundâncias
- Otimizações locais e globais

---

## Testes
- Criar testes
- Validar com programas exemplo

---

## Exemplos

### Olá Mundo
```fortran
PROGRAM HELLO
PRINT *, 'Ola, Mundo!'
END
```

### Fatorial
```fortran
PROGRAM FATORIAL
INTEGER N, I, FAT
FAT = 1
DO 10 I = 1, N
   FAT = FAT * I
10 CONTINUE
END
```

---

## Requisitos Técnicos

### Obrigatório
- Tipos e variáveis
- Expressões
- IF, DO, GOTO
- READ, PRINT

### Valorização
- SUBROUTINE
- FUNCTION

---

## Grupos
- 3 elementos
- Registo até: **05/04/2026**
- Submissão via GitHub

---

## Entrega
- Prazo: **17/05/2026 23:59**

### Conteúdo:
- Código (Python + ply)
- Relatório (máx 10 páginas)
- Testes

---

## Avaliação
- Correção
- Estrutura
- Funcionalidade
- Eficiência
- Defesa

---

Boa sorte!
