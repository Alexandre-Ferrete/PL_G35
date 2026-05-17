import matplotlib.pyplot as plt
import numpy as np

# 1. Definição dos nomes dos testes (Eixo X)
testes = [
    'Teste 1:\nAlgébrico', 
    'Teste 2:\nFluxo Morto', 
    'Teste 3:\nDesvios Estáticos', 
    'Teste 4:\nMisto Integral'
]

# 2. Dados estatísticos de exemplo (Número de linhas/instruções geradas no .asm)
# Substitui estes números pelos valores reais obtidos no teu compilador!
o0 = [54, 46, 58, 68]  # Sem otimização
o1 = [26, 28, 44, 48]  # Otimização Local
o2 = [26, 22, 24, 38]  # Otimização de Fluxo
o3 = [18, 16, 12, 24]  # Otimização Cíclica Agressiva

# Configuração lógica do posicionamento das barras agrupadas
x = np.arange(len(testes))  # Localização dos grupos
width = 0.18                 # Largura individual de cada barra

# 3. Desenho das barras utilizando o contexto ativo (sem acionar .figure())
plt.bar(x - 1.5*width, o0, width, label='-opt 0 (Base)', color='#d9534f', edgecolor='black', linewidth=0.5)
plt.bar(x - 0.5*width, o1, width, label='-opt 1 (Local)', color='#f0ad4e', edgecolor='black', linewidth=0.5)
plt.bar(x + 0.5*width, o2, width, label='-opt 2 (Fluxo)', color='#5bc0de', edgecolor='black', linewidth=0.5)
plt.bar(x + 1.5*width, o3, width, label='-opt 3 (Agressivo)', color='#5cb85c', edgecolor='black', linewidth=0.5)

# 4. Customização e Formatação do Gráfico
plt.ylabel('Tamanho do Código (Número de Instruções Assembly)', fontsize=10, fontweight='bold')
plt.title('Impacto dos Níveis de Otimização no Volume de Código Gerado', fontsize=11, fontweight='bold', pad=15)
plt.xticks(x, testes, fontsize=9)
plt.grid(axis='y', linestyle='--', alpha=0.5)

# Posicionamento elegante da legenda informativa
plt.legend(frameon=True, facecolor='white', edgecolor='none', fontsize=9)

# 5. Ajuste de margens e exportação direta e limpa para imagem de alta resolução
plt.tight_layout()
plt.savefig('evolucao_otimizacoes.png', dpi=300)
print("Sucesso: O ficheiro 'evolucao_otimizacoes.png' foi gerado e guardado corretamente!")