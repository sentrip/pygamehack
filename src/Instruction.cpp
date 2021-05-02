#include "Instruction.h"
#include "external/libdasm.h"
#include <vector>

namespace pygamehack {

static_assert(sizeof(Operand) == sizeof(::OPERAND), "Operand structs do not match");
static_assert(offsetof(Operand, type) == offsetof(::OPERAND, type), "Operand structs do not match");
static_assert(offsetof(Operand, reg) == offsetof(::OPERAND, reg), "Operand structs do not match");
static_assert(offsetof(Operand, basereg) == offsetof(::OPERAND, basereg), "Operand structs do not match");
static_assert(offsetof(Operand, indexreg) == offsetof(::OPERAND, indexreg), "Operand structs do not match");
static_assert(offsetof(Operand, scale) == offsetof(::OPERAND, scale), "Operand structs do not match");
static_assert(offsetof(Operand, dispbytes) == offsetof(::OPERAND, dispbytes), "Operand structs do not match");
static_assert(offsetof(Operand, dispoffset) == offsetof(::OPERAND, dispoffset), "Operand structs do not match");
static_assert(offsetof(Operand, immbytes) == offsetof(::OPERAND, immbytes), "Operand structs do not match");
static_assert(offsetof(Operand, immoffset) == offsetof(::OPERAND, immoffset), "Operand structs do not match");
static_assert(offsetof(Operand, sectionbytes) == offsetof(::OPERAND, sectionbytes), "Operand structs do not match");
static_assert(offsetof(Operand, section) == offsetof(::OPERAND, section), "Operand structs do not match");
static_assert(offsetof(Operand, displacement) == offsetof(::OPERAND, displacement), "Operand structs do not match");


static_assert(sizeof(Instruction) == sizeof(::INSTRUCTION), "Instruction structs do not match");
static_assert(offsetof(Instruction, length) == offsetof(::INSTRUCTION, length), "Instruction structs do not match");
static_assert(offsetof(Instruction, type) == offsetof(::INSTRUCTION, type), "Instruction structs do not match");
static_assert(offsetof(Instruction, mode) == offsetof(::INSTRUCTION, mode), "Instruction structs do not match");
static_assert(offsetof(Instruction, opcode) == offsetof(::INSTRUCTION, opcode), "Instruction structs do not match");
static_assert(offsetof(Instruction, modrm) == offsetof(::INSTRUCTION, modrm), "Instruction structs do not match");
static_assert(offsetof(Instruction, sib) == offsetof(::INSTRUCTION, sib), "Instruction structs do not match");
static_assert(offsetof(Instruction, modrm_offset) == offsetof(::INSTRUCTION, modrm_offset), "Instruction structs do not match");
static_assert(offsetof(Instruction, extindex) == offsetof(::INSTRUCTION, extindex), "Instruction structs do not match");
static_assert(offsetof(Instruction, fpuindex) == offsetof(::INSTRUCTION, fpuindex), "Instruction structs do not match");
static_assert(offsetof(Instruction, dispbytes) == offsetof(::INSTRUCTION, dispbytes), "Instruction structs do not match");
static_assert(offsetof(Instruction, immbytes) == offsetof(::INSTRUCTION, immbytes), "Instruction structs do not match");
static_assert(offsetof(Instruction, sectionbytes) == offsetof(::INSTRUCTION, sectionbytes), "Instruction structs do not match");
static_assert(offsetof(Instruction, op1) == offsetof(::INSTRUCTION, op1), "Instruction structs do not match");
static_assert(offsetof(Instruction, op2) == offsetof(::INSTRUCTION, op2), "Instruction structs do not match");
static_assert(offsetof(Instruction, op3) == offsetof(::INSTRUCTION, op3), "Instruction structs do not match");
static_assert(offsetof(Instruction, ptr) == offsetof(::INSTRUCTION, ptr), "Instruction structs do not match");
static_assert(offsetof(Instruction, flags) == offsetof(::INSTRUCTION, flags), "Instruction structs do not match");
static_assert(offsetof(Instruction, eflags_affected) == offsetof(::INSTRUCTION, eflags_affected), "Instruction structs do not match");
static_assert(offsetof(Instruction, eflags_used) == offsetof(::INSTRUCTION, eflags_used), "Instruction structs do not match");
static_assert(offsetof(Instruction, iop_written) == offsetof(::INSTRUCTION, iop_written), "Instruction structs do not match");
static_assert(offsetof(Instruction, iop_read) == offsetof(::INSTRUCTION, iop_read), "Instruction structs do not match");



static void 
do_extract_searchable_byte_ranges(
        const string& raw_code, 
        usize last_instruction_offset,
        usize& begin,
        usize& offset,
        usize& instruction_offset,
        usize& offset_size,
        std::vector<std::pair<usize, usize>>& regions_to_replace)
{
    // Function to parse each property of each instruction operand
    auto parse_instruction = [&](const Instruction& ins, const Operand& op, usize off, usize size){
        // Replace dynamic bytes with dots
        regions_to_replace.push_back({offset + off - begin, size});
        
        // Detect offset and offset size
        if (op.displacement && (offset + ins.length) == last_instruction_offset) {
            instruction_offset = offset + off - begin;
            offset_size = size;
        }
    };

    // Iterate instructions to get searchable code range
    auto end = InstructionIter(raw_code, Instruction::Mode::M32, true, UINT32_MAX);
    for (auto it = InstructionIter(raw_code, Instruction::Mode::M32, true); it != end; ++it) {
    
        const auto [ins_offset, ins] = *it;
        offset = ins_offset;

        // Skip empty instructions at the start
        if (ins.opcode == 0 && !begin) {
            begin = offset + ins.length;
        }

        #define DO_OP_PROP(ins, opname, prop, func) \
            if (ins.opname.prop##bytes) func(ins, ins.opname, ins.opname.prop##offset, ins.opname.prop##bytes)

        #define DO_OP(ins, opname, func) \
            DO_OP_PROP(ins, opname, disp, func); \
            DO_OP_PROP(ins, opname, imm, func)

        DO_OP(ins, op1, parse_instruction);
        DO_OP(ins, op2, parse_instruction);
        DO_OP(ins, op3, parse_instruction);

        #undef DO_OP_PROP
        #undef DO_OP
    }
}



Instruction Instruction::from_string(string code, Mode m)
{
    Instruction inst{};
    ::get_instruction((::INSTRUCTION*)&inst, (unsigned char*)code.data(), (::Mode)m);
    return inst;
}

string Instruction::to_string(Format fmt)
{
    string inst_str;
    inst_str.resize(512);
    ::get_instruction_string((::INSTRUCTION*)this, (::Format)fmt, 0, inst_str.data(), int(inst_str.size()));
    inst_str.resize(strnlen_s(inst_str.c_str(), 512));
    return inst_str;
}

string Instruction::to_readable_code(string code, Format fmt, Mode m)
{
    string instruction;
    instruction.resize(256);
    Instruction inst;
    ::get_instruction((::INSTRUCTION*)&inst, (unsigned char*)code.data(), (::Mode)m);
    ::get_instruction_string((::INSTRUCTION*)&inst, (::Format)fmt, 0, instruction.data(), int(instruction.size()));
    return instruction;
}

Instruction::SearchableCode Instruction::extract_searchable_bytes(const string& raw_code, usize last_instruction_offset)
{
    usize begin = 0, offset = 0, instruction_offset = 0, offset_size = 0;
    std::vector<std::pair<usize, usize>> regions_to_replace;
    
    do_extract_searchable_byte_ranges(raw_code, last_instruction_offset, 
        begin, offset, instruction_offset, offset_size, regions_to_replace);

    if (begin > offset) {
        return SearchableCode{};
    }

    // Get searchable code section from raw code
    string searchable_code{raw_code.c_str() + begin, raw_code.c_str() + offset + 1};

    // Replace regex special characters with '.'
    for (auto& c: searchable_code) {
        if (c == '[' || c == ']') c = '.';
    }

    // Replace dynamic bytes with dots
    for (const auto& region: regions_to_replace) {
        if (region.first >= begin && (region.first + region.second) <= (offset + 1)) {
            memset(searchable_code.data() + region.first - begin, '.', region.second);
        }
    }
    
    // Remove empty bytes at the start
    usize empty_offset = 0;
    // while (searchable_code[empty_offset] == '.') empty_offset++;
    // if (empty_offset) searchable_code.erase(searchable_code.begin(), searchable_code.begin() + empty_offset);

    return SearchableCode{std::move(searchable_code), instruction_offset + empty_offset, offset_size};
}



InstructionIter::InstructionIter(const string& code, Instruction::Mode m, bool break_on_return, usize offset):
    code{code.c_str()},
    code_size{code.size()},
    offset{offset},
    mode{m},
    break_on_return{break_on_return}
{
    if (offset != UINT32_MAX) {
        instruction = Instruction::from_string(code.c_str() + offset, mode);
    }
}

InstructionIter::Pair InstructionIter::operator*() const 
{
    return {offset, instruction};
}

InstructionIter& InstructionIter::operator++() 
{
    if (offset >= code_size || (break_on_return && (::Instruction)instruction.type == ::INSTRUCTION_TYPE_RET)) {
        offset = UINT32_MAX;
    }

    if (offset != UINT32_MAX) {
        offset += instruction.length;
        instruction = Instruction::from_string(code + offset, mode);
    }
    
    return *this;
}

bool InstructionIter::operator==(const InstructionIter& other) const
{
    return mode == other.mode && code == other.code && offset == other.offset;
}

bool InstructionIter::operator!=(const InstructionIter& other) const
{
    return !(*this == other);
}

}
