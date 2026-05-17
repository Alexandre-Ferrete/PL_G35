PROGRAM MATEMATICA
INTEGER ALVO, R_MOD, R_INT
REAL X, R_ABS, R_REAL, MISTURA

ALVO = -15
X = 5.75

* 1. Testar funcao nativa ABS
R_ABS = ABS(ALVO)
PRINT *, 'ABS DE -15 E: ', R_ABS

c 2. Testar o operador MOD nativo
R_MOD = MOD(23, 5)
PRINT *, 'MOD DE 23 POR 5 E: ', R_MOD

C 3. Testar conversoes explicitas
R_INT = INT(X)
R_REAL = REAL(10)
PRINT *, 'INT DE 5.75 E: ', R_INT
PRINT *, 'REAL DE 10 E: ', R_REAL

! teste comentario
MISTURA = 2 + 3.5 ! 4. Testar mistura de real com inteiro
PRINT *, 'SOMA DE 2 E 3.5 E: ', MISTURA
END