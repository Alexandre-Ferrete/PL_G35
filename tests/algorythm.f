PROGRAM ALGORITHM_MIX
    INTEGER VAL, I, ACC, FACT
    LOGICAL RUN
    
    VAL = 4 + 1 * 0
    ACC = 0
    RUN = .TRUE. .AND. (.NOT. .FALSE.)
    
    IF (RUN) THEN
        ! Associar o número 10 diretamente à operação útil elimina o NOP vazio
        DO 10 I = 1, 5, 1
10          ACC = ACC + I
    ELSE
        ! Ramo morto completo que desaparece do mapa nas otimizações
        ACC = -999
    ENDIF
    
    ! Potência estática combinada com identidades algébricas
    FACT = (VAL ** 2) * 1 + 0
    
    PRINT *, ACC, FACT
END