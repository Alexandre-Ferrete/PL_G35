start
pushn 7
pushi -15
storeg 0
pushf 5.75
storeg 3
pushg 0
dup 1
pushi 0
inf
jz ABSP1
pushi 0
swap
sub
ABSP1:
storeg 4
pushs "ABS DE -15 E: "
writes
pushs " "
writes
pushg 4
writef
writeln
pushi 23
pushi 5
mod
storeg 1
pushs "MOD DE 23 POR 5 E: "
writes
pushs " "
writes
pushg 1
writei
writeln
pushg 3
ftoi
storeg 2
pushi 10
itof
storeg 5
pushs "INT DE 5.75 E: "
writes
pushs " "
writes
pushg 2
writei
writeln
pushs "REAL DE 10 E: "
writes
pushs " "
writes
pushg 5
writef
writeln
pushf 5.5
storeg 6
pushs "SOMA DE 2 E 3.5 E: "
writes
pushs " "
writes
pushg 6
writef
writeln
stop
