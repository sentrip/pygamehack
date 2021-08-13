#ifndef INSTRUCTION_H
#define INSTRUCTION_H

#include "config.h"
#include <Zydis/Zydis.h>

#include <tuple>
#include <vector>

namespace pygamehack {
    

struct Instruction: public ZydisDecodedInstruction {
    class Decoder;
    class Iterator;
    using SearchableCode = std::tuple<string /* aob */, uptr /* offset */, usize /* offset size */>;
    
    enum class MachineMode {
        /**
         * 64 bit mode.
         */
        LONG_64,
        /**
         * 32 bit protected mode.
         */
        LONG_COMPAT_32,
        /**
         * 16 bit protected mode.
         */
        LONG_COMPAT_16,
        /**
         * 32 bit protected mode.
         */
        LEGACY_32,
        /**
         * 16 bit protected mode.
         */
        LEGACY_16,
        /**
         * 16 bit real mode.
         */
        REAL_16,
    };
    
    enum class AddressWidth {
        WIDTH_16,
        WIDTH_32,
        WIDTH_64,
    };

    enum class Format {
        /**
         * Generates `AT&T`-style disassembly.
         */
        ATT,
        /**
         * Generates `Intel`-style disassembly.
         */
        INTEL,
        /**
         * Generates `MASM`-style disassembly that is directly accepted as input for
         * the `MASM` assembler.
         *
         * The runtime-address is ignored in this mode.
         */
        INTEL_MASM,
    };
};


class Instruction::Decoder {
public:
    struct IterWrapper;

    Decoder(MachineMode mode, AddressWidth address_width);
    
    void        set_format(Format format);

    bool        decode(Instruction& instruction, const u8* data, usize size) const;
    
    string      format(const Instruction& instruction, u64 runtime_address = UINT64_MAX) const;

    SearchableCode extract_searchable_bytes(const string& raw_code, uptr target_instruction_offset, usize max_size = UINT32_MAX) const;

private:
    ZydisDecoder decoder{};
    ZydisFormatter formatter{};
};


class Instruction::Iterator {
public:
    using Pair = std::pair<uptr, Instruction>;

    explicit Iterator(const Decoder* decoder = nullptr, const u8* data = nullptr, usize size = 0);
    string format(u64 runtime_address = UINT64_MAX) const;
    // Deref
    Pair operator*() const;
    const Instruction* operator->() const;
    // Pre increment
    Iterator& operator++();
    // Equality
    bool operator==(const Iterator& other) const;
    bool operator!=(const Iterator& other) const;

private:
    Instruction instruction{};
    const Decoder* decoder{};
    std::vector<u8> _data{};
    uptr _offset{};
    bool done{};
};

}

#endif
