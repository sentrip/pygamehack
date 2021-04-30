
#include "config.h"

namespace pygamehack {


class InstructionIter;


// Operands for the instruction
struct Operand {
    enum Type { 
        NONE,               // operand not present
        MEMORY,             // memory operand ([eax], [0], etc.)
        REGISTER,           // register operand (eax, mm0, etc.)
        IMMEDIATE,          // immediate operand (0x1234)
    };

    Type type;              // Operand type (register, memory, etc)
    int reg;                // Register (if any)
    int basereg;            // Base register (if any)
    int indexreg;           // Index register (if any)
    int scale;              // Scale (if any)
    int dispbytes;          // Displacement bytes (0 = no displacement)
    int dispoffset;         // Displacement value offset
    int immbytes;           // Immediate bytes (0 = no immediate)
    int immoffset;          // Immediate value offset
    int sectionbytes;       // Section prefix bytes (0 = no section prefix)
    u16 section;            // Section prefix value
    u32 displacement;       // Displacement value
    u32 immediate;          // Immediate value
    int flags;              // Operand flags
};


// struct INSTRUCTION is used to interface the library
struct Instruction {
    using iterator = InstructionIter;
    using SearchableCode = std::tuple<std::string /* aob */, usize /* offset */, usize /* offset size */>;

    // Mode
    enum Mode {
        M32,  // 32-bit
        M16   // 16-bit
    };
    // Disassembling format
    enum Format {
        ATT,
        INTEL,
    };
    // Type
    enum Type {
        PRIV = 107 // See external/libdasm.h - lines [188:302] for full definition
    };
    
    int length;             // Instruction length
    Type type;              // Instruction type
    Mode mode;              // Addressing mode
    u8 opcode;              // Actual opcode
    u8 modrm;               // MODRM byte
    u8 sib;                 // SIB byte
    int modrm_offset;       // MODRM byte offset
    int extindex;           // Extension table index
    int fpuindex;           // FPU table index
    int dispbytes;          // Displacement bytes (0 = no displacement)
    int immbytes;           // Immediate bytes (0 = no immediate)
    int sectionbytes;       // Section prefix bytes (0 = no section prefix)
    Operand op1;            // First operand (if any)
    Operand op2;            // Second operand (if any)
    Operand op3;            // Additional operand (if any)
    void* ptr;              // Pointer to instruction table (internal use only)
    int flags;              // Instruction flags
    short eflags_affected;  // Process eflags affected
    short eflags_used;      // Processor eflags used by this instruction
    int iop_written;        // mask of affected implied registers (written)
    int iop_read;           // mask of affected implied registers (read)

    string to_string(Format fmt = Format::ATT);

    static Instruction from_string(string code, Mode m = Mode::M32);

    static string to_readable_code(string code, Format fmt = Format::ATT, Mode m = Mode::M32);

    static SearchableCode extract_searchable_bytes(const string& raw_code, usize last_instruction_offset = UINT32_MAX);
};


class InstructionIter {
public:
    using Pair = std::pair<usize, Instruction>;

    InstructionIter(const string& code, Instruction::Mode m, bool break_on_return, usize offset = 0);
    // Deref
    Pair operator*() const;
    // Pre increment
    InstructionIter& operator++();
    // Equality
    bool operator==(const InstructionIter& other) const;
    bool operator!=(const InstructionIter& other) const;

private:
    const char* code{};
    usize code_size{};
    usize offset{};
    Instruction::Mode mode{};
    bool break_on_return{};
    Instruction instruction;
};

}


#define FOR_EACH_INSTRUCTION_TYPE(F) \
F((Instruction::Type)0, "ASC"); \
F((Instruction::Type)1, "DCL"); \
F((Instruction::Type)2, "MOV"); \
F((Instruction::Type)3, "MOVSR"); \
F((Instruction::Type)4, "ADD"); \
F((Instruction::Type)5, "XADD"); \
F((Instruction::Type)6, "ADC"); \
F((Instruction::Type)7, "SUB"); \
F((Instruction::Type)8, "SBB"); \
F((Instruction::Type)9, "INC"); \
F((Instruction::Type)10, "DEC"); \
F((Instruction::Type)11, "DIV"); \
F((Instruction::Type)12, "IDIV"); \
F((Instruction::Type)13, "NOT"); \
F((Instruction::Type)14, "NEG"); \
F((Instruction::Type)15, "STOS"); \
F((Instruction::Type)16, "LODS"); \
F((Instruction::Type)17, "SCAS"); \
F((Instruction::Type)18, "MOVS"); \
F((Instruction::Type)19, "MOVSX"); \
F((Instruction::Type)20, "MOVZX"); \
F((Instruction::Type)21, "CMPS"); \
F((Instruction::Type)22, "SHX"); \
F((Instruction::Type)23, "ROX"); \
F((Instruction::Type)24, "MUL"); \
F((Instruction::Type)25, "IMUL"); \
F((Instruction::Type)26, "EIMUL"); \
F((Instruction::Type)27, "XOR"); \
F((Instruction::Type)28, "LEA"); \
F((Instruction::Type)29, "XCHG"); \
F((Instruction::Type)30, "CMP"); \
F((Instruction::Type)31, "TEST"); \
F((Instruction::Type)32, "PUSH"); \
F((Instruction::Type)33, "AND"); \
F((Instruction::Type)34, "OR"); \
F((Instruction::Type)35, "POP"); \
F((Instruction::Type)36, "JMP"); \
F((Instruction::Type)37, "JMPC"); \
F((Instruction::Type)38, "JECXZ"); \
F((Instruction::Type)39, "SETC"); \
F((Instruction::Type)40, "MOVC"); \
F((Instruction::Type)41, "LOOP"); \
F((Instruction::Type)42, "CALL"); \
F((Instruction::Type)43, "RET"); \
F((Instruction::Type)44, "ENTER"); \
F((Instruction::Type)45, "INT"); \
F((Instruction::Type)46, "BT"); \
F((Instruction::Type)47, "BTS"); \
F((Instruction::Type)48, "BTR"); \
F((Instruction::Type)49, "BTC"); \
F((Instruction::Type)50, "BSF"); \
F((Instruction::Type)51, "BSR"); \
F((Instruction::Type)52, "BSWAP"); \
F((Instruction::Type)53, "SGDT"); \
F((Instruction::Type)54, "SIDT"); \
F((Instruction::Type)55, "SLDT"); \
F((Instruction::Type)56, "LFP"); \
F((Instruction::Type)57, "CLD"); \
F((Instruction::Type)58, "STD"); \
F((Instruction::Type)59, "XLAT"); \
F((Instruction::Type)60, "FCMOVC"); \
F((Instruction::Type)61, "FADD"); \
F((Instruction::Type)62, "FADDP"); \
F((Instruction::Type)63, "FIADD"); \
F((Instruction::Type)64, "FSUB"); \
F((Instruction::Type)65, "FSUBP"); \
F((Instruction::Type)66, "FISUB"); \
F((Instruction::Type)67, "FSUBR"); \
F((Instruction::Type)68, "FSUBRP"); \
F((Instruction::Type)69, "FISUBR"); \
F((Instruction::Type)70, "FMUL"); \
F((Instruction::Type)71, "FMULP"); \
F((Instruction::Type)72, "FIMUL"); \
F((Instruction::Type)73, "FDIV"); \
F((Instruction::Type)74, "FDIVP"); \
F((Instruction::Type)75, "FDIVR"); \
F((Instruction::Type)76, "FDIVRP"); \
F((Instruction::Type)77, "FIDIV"); \
F((Instruction::Type)78, "FIDIVR"); \
F((Instruction::Type)79, "FCOM"); \
F((Instruction::Type)80, "FCOMP"); \
F((Instruction::Type)81, "FCOMPP"); \
F((Instruction::Type)82, "FCOMI"); \
F((Instruction::Type)83, "FCOMIP"); \
F((Instruction::Type)84, "FUCOM"); \
F((Instruction::Type)85, "FUCOMP"); \
F((Instruction::Type)86, "FUCOMPP"); \
F((Instruction::Type)87, "FUCOMI"); \
F((Instruction::Type)88, "FUCOMIP"); \
F((Instruction::Type)89, "FST"); \
F((Instruction::Type)90, "FSTP"); \
F((Instruction::Type)91, "FIST"); \
F((Instruction::Type)92, "FISTP"); \
F((Instruction::Type)93, "FISTTP"); \
F((Instruction::Type)94, "FLD"); \
F((Instruction::Type)95, "FILD"); \
F((Instruction::Type)96, "FICOM"); \
F((Instruction::Type)97, "FICOMP"); \
F((Instruction::Type)98, "FFREE"); \
F((Instruction::Type)99, "FFREEP"); \
F((Instruction::Type)100, "FXCH"); \
F((Instruction::Type)101, "SYSENTER"); \
F((Instruction::Type)102, "FPU_CTRL"); \
F((Instruction::Type)103, "FPU"); \
F((Instruction::Type)104, "MMX"); \
F((Instruction::Type)105, "SSE"); \
F((Instruction::Type)106, "OTHER"); \
F((Instruction::Type)107, "PRIV");
