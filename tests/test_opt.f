PROGRAM TEST
      INTEGER A, B, C, D, E
      A = 10 + 20
      B = A * 1
      C = A * 0
      D = B + 0
      GOTO 10
      E = 100
10    CONTINUE
      PRINT *, A, B, C, D
END