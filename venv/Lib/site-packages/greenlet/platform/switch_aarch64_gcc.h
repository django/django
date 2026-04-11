/*
 * this is the internal transfer function.
 *
 * HISTORY
 * 07-Sep-16 Add clang support using x register naming. Fredrik Fornwall
 * 13-Apr-13 Add support for strange GCC caller-save decisions
 * 08-Apr-13 File creation. Michael Matz
 *
 * NOTES
 *
 * Simply save all callee saved registers
 *
 */

#define STACK_REFPLUS 1

#ifdef SLP_EVAL
#define STACK_MAGIC 0
#define REGS_TO_SAVE "x19", "x20", "x21", "x22", "x23", "x24", "x25", "x26", \
                     "x27", "x28", "x30" /* aka lr */, \
                     "v8", "v9", "v10", "v11", \
                     "v12", "v13", "v14", "v15"

/*
 * Recall:
   asm asm-qualifiers ( AssemblerTemplate
                 : OutputOperands
                 [ : InputOperands
                 [ : Clobbers ] ])

 or  (if asm-qualifiers contains 'goto')

   asm asm-qualifiers ( AssemblerTemplate
                      : OutputOperands
                      : InputOperands
                      : Clobbers
                      : GotoLabels)

 and OutputOperands are

   [ [asmSymbolicName] ] constraint (cvariablename)

 When a name is given, refer to it as ``%[the name]``.
 When not given, ``%i`` where ``i`` is the zero-based index.

 constraints starting with ``=`` means only writing; ``+`` means
 reading and writing.

 This is followed by ``r`` (must be register) or ``m`` (must be memory)
 and these can be combined.

 The ``cvariablename`` is actually an lvalue expression.

 In AArch65, 31 general purpose registers. If named X0... they are
 64-bit. If named W0... they are the bottom 32 bits of the
 corresponding 64 bit register.

 XZR and WZR are hardcoded to 0, and ignore writes.

 Arguments are in X0..X7. C++ uses X0 for ``this``. X0 holds simple return
 values (?)

 Whenever a W register is written, the top half of the X register is zeroed.
 */

static int
slp_switch(void)
{
	int err;
	void *fp;
        /* Windowz uses a 32-bit long on a 64-bit platform, unlike the rest of
           the world, and in theory we can be compiled with GCC/llvm on 64-bit
           windows. So we need a fixed-width type.
        */
        int64_t *stackref, stsizediff;
        __asm__ volatile ("" : : : REGS_TO_SAVE);
	__asm__ volatile ("str x29, %0" : "=m"(fp) : : );
        __asm__ ("mov %0, sp" : "=r" (stackref));
        {
                SLP_SAVE_STATE(stackref, stsizediff);
                __asm__ volatile (
                    "add sp,sp,%0\n"
                    "add x29,x29,%0\n"
                    :
                    : "r" (stsizediff)
                    );
		SLP_RESTORE_STATE();
		/* SLP_SAVE_STATE macro contains some return statements
		   (of -1 and 1).  It falls through only when
		   the return value of slp_save_state() is zero, which
		   is placed in x0.
		   In that case we (slp_switch) also want to return zero
		   (also in x0 of course).
		   Now, some GCC versions (seen with 4.8) think it's a
		   good idea to save/restore x0 around the call to
		   slp_restore_state(), instead of simply zeroing it
		   at the return below.  But slp_restore_state
		   writes random values to the stack slot used for this
		   save/restore (from when it once was saved above in
		   SLP_SAVE_STATE, when it was still uninitialized), so
		   "restoring" that precious zero actually makes us
		   return random values.  There are some ways to make
		   GCC not use that zero value in the normal return path
		   (e.g. making err volatile, but that costs a little
		   stack space), and the simplest is to call a function
		   that returns an unknown value (which happens to be zero),
		   so the saved/restored value is unused.

                   Thus, this line stores a 0 into the ``err`` variable
                   (which must be held in a register for this instruction,
                    of course). The ``w`` qualifier causes the instruction
                    to use W0 instead of X0, otherwise we get a warning
                    about a value size mismatch (because err is an int,
                    and aarch64 platforms are LP64: 32-bit int, 64 bit long
                   and pointer).
                */
           __asm__ volatile ("mov %w0, #0" : "=r" (err));
        }
        __asm__ volatile ("ldr x29, %0" : : "m" (fp) :);
        __asm__ volatile ("" : : : REGS_TO_SAVE);
        return err;
}

#endif
