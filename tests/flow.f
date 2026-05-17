PROGRAM FLOW_EXTENSIVE
    INTEGER X, Y, Z
    X = 1
    Y = 2
    Z = 3
    GOTO 100
    
    ! Unreachable Code: Todo este bloco intermédio será inteiramente apagado
    X = X + 10
    Y = Y * 5
    Z = Z - 1
    GOTO 200
    
100 CONTINUE
    X = Y + Z
    GOTO 300
    
    ! Mais código inalcançável e rótulos mortos
200 CONTINUE
    X = 999
    
300 CONTINUE
    PRINT *, X
    
    ! Dead Labels: Rótulos declarados mas nunca referenciados por nenhum GOTO/IF
400 CONTINUE
500 CONTINUE
END