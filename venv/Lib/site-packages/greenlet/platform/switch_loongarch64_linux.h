#define STACK_REFPLUS 1

#ifdef SLP_EVAL
#define STACK_MAGIC 0

#define REGS_TO_SAVE "s0", "s1", "s2", "s3", "s4", "s5", \
                    "s6", "s7", "s8", "fp", \
                    "f24", "f25", "f26", "f27", "f28", "f29", "f30", "f31"

static int
slp_switch(void)
{
    int ret;
    long *stackref, stsizediff;
    __asm__ volatile ("" : : : REGS_TO_SAVE);
    __asm__ volatile ("move %0, $sp" : "=r" (stackref) : );
    {
        SLP_SAVE_STATE(stackref, stsizediff);
        __asm__ volatile (
            "add.d $sp, $sp, %0\n\t"
            : /* no outputs */
            : "r" (stsizediff)
        );
        SLP_RESTORE_STATE();
    }
    __asm__ volatile ("" : : : REGS_TO_SAVE);
    __asm__ volatile ("move %0, $zero" : "=r" (ret) : );
    return ret;
}

#endif
