public main:
    mov rax, 0
    call inc_rax
    call inc_rax
    mov rcx, dword [rax]
    hlt rax

private inc_rax:
    enter
    add rax, 1
    leave
