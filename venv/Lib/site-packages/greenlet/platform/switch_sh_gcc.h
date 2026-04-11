#define STACK_REFPLUS 1

#ifdef SLP_EVAL
#define STACK_MAGIC 0
#define REGS_TO_SAVE "r8", "r9", "r10", "r11", "r13", \
                     "fr12", "fr13", "fr14", "fr15"

// r12 Global context pointer, GP
// r14 Frame pointer, FP
// r15 Stack pointer, SP

static int
slp_switch(void)
{
    int err;
    void* fp;
    int *stackref, stsizediff;
    __asm__ volatile("" : : : REGS_TO_SAVE);
    __asm__ volatile("mov.l r14, %0" : "=m"(fp) : :);
    __asm__("mov r15, %0" : "=r"(stackref));
    {
        SLP_SAVE_STATE(stackref, stsizediff);
        __asm__ volatile(
            "add %0, r15\n"
            "add %0, r14\n"
            : /* no outputs */
            : "r"(stsizediff));
        SLP_RESTORE_STATE();
        __asm__ volatile("mov r0, %0" : "=r"(err) : :);
    }
    __asm__ volatile("mov.l %0, r14" : : "m"(fp) :);
    __asm__ volatile("" : : : REGS_TO_SAVE);
    return err;
}

#endif
