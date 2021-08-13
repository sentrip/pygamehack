#include "Instruction.h"


namespace pygamehack {

//region Instruction::Decoder

Instruction::Decoder::Decoder(MachineMode mode, AddressWidth address_width)
{
    ZydisDecoderInit(&decoder, ZydisMachineMode(mode), ZydisAddressWidth(address_width));
    set_format(Format::INTEL);
}

void Instruction::Decoder::set_format(Format format)
{
    ZydisFormatterInit(&formatter, ZydisFormatterStyle(format));
}

bool Instruction::Decoder::decode(Instruction& instruction, const u8* data, usize size) const
{
    return ZYAN_SUCCESS(ZydisDecoderDecodeBuffer(&decoder, data, size, &instruction));
}

string Instruction::Decoder::format(const Instruction& instruction, u64 runtime_address) const
{
    string fmt{};
    fmt.resize(256);
    ZydisFormatterFormatInstruction(&formatter, &instruction, fmt.data(), fmt.size(), runtime_address);
    fmt.resize(strnlen_s(fmt.c_str(), fmt.size()));
    return fmt;
}

Instruction::SearchableCode Instruction::Decoder::extract_searchable_bytes(const string& raw_code, uptr target_instruction_offset, usize max_size) const
{
    uptr offset{};
    usize offset_size{};
    uptr searchable_begin{}, searchable_end{};
    std::vector<std::pair<usize, usize>> dynamic_byte_ranges;

    Instruction::Iterator begin{this, (const u8*)raw_code.c_str(), raw_code.size()};
    Instruction::Iterator end{};

    bool has_seen_valid_instruction = false;
    for (auto it = begin; it != end; ++it) {
        const auto [ins_offset, instruction] = *it;

        // Skip empty instructions at the start
//        if (!instruction.opcode && !has_seen_valid_instruction)
//            searchable_begin = ins_offset;
//        has_seen_valid_instruction |= (instruction.opcode != 0);
        
        // Detect dynamic bytes
        if (instruction.raw.disp.size) {
            dynamic_byte_ranges.push_back({ins_offset + instruction.raw.disp.offset, instruction.raw.disp.size >> 3});
        }
        if (instruction.raw.imm->size) {
            dynamic_byte_ranges.push_back({ins_offset + instruction.raw.imm->offset, instruction.raw.imm->size >> 3});
        }
        
        // Detect offset in requested instruction
        if (ins_offset <= target_instruction_offset && (ins_offset + instruction.length) > target_instruction_offset) {
            if (instruction.raw.disp.size) {
                offset = ins_offset + instruction.raw.disp.offset;
                offset_size = instruction.raw.disp.size >> 3;
            }
            else if (instruction.raw.imm->size) {
                offset = ins_offset + instruction.raw.imm->offset;
                offset_size = instruction.raw.imm->size >> 3;
            }
        }

        // Do not read more than the requested number of bytes
        searchable_end = ins_offset + instruction.length;
        if (searchable_end >= max_size) break;
    }
    
    // Extract searchable code range
    PGH_ASSERT(searchable_begin < searchable_end, "Did not find searchable code");
    string searchable_code{raw_code.begin() + searchable_begin, raw_code.begin() + searchable_end};

    // Replace regex special characters with '.'
    for (auto& c: searchable_code) {
        if (c == '[' || c == ']') c = '.';
    }

    // Replace dynamic bytes with '.'
    for (const auto& r: dynamic_byte_ranges) {
        if (r.first >= searchable_begin && (r.first + r.second) <= searchable_end) {
            memset(searchable_code.data() + r.first - searchable_begin, '.', r.second);
        }
    }

    return SearchableCode(std::move(searchable_code), offset - searchable_begin, offset_size);
}

//endregion

//region Instruction::Iterator

Instruction::Iterator::Iterator(const Decoder* decoder, const u8* data, usize size):
    decoder{decoder},
    _data{data, data + size}
{
    if (size) {
        done = !decoder->decode(instruction, data, size);
        _offset = instruction.length;
    }
    else {
        done = true;
    }
}

string Instruction::Iterator::format(u64 runtime_address) const
{
    return decoder->format(instruction, runtime_address);
}

Instruction::Iterator::Pair Instruction::Iterator::operator*() const
{
    return Pair{_offset - instruction.length, instruction};
}

const Instruction* Instruction::Iterator::operator->() const
{
    return &instruction;
}

Instruction::Iterator& Instruction::Iterator::operator++()
{
    done = !decoder->decode(instruction, _data.data() + _offset, _data.size() - _offset);
    _offset += instruction.length;
    return *this;
}

bool Instruction::Iterator::operator==(const Iterator& other) const
{
    return done == other.done;
}

bool Instruction::Iterator::operator!=(const Iterator& other) const
{
    return !(*this == other);
}

//endregion

}
