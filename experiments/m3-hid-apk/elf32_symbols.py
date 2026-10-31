"""Offline ELF32 ARM function-symbol triage, not a disassembler or patcher.

Symbols are optional in stripped proprietary ELF. File offsets are for OFFLINE
review only. ELF VMAs are not runtime ASLR addresses or safe hook locations.
"""
from __future__ import annotations
from dataclasses import dataclass
import struct

TARGETS = (
    'bta_hh_co_set_rpt_rsp', 'uhid_read_event', 'btif_hh_setreport',
    'bta_hh_co_send_hid_info', 'bta_hh_co_open',
)

@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str
    vma: int
    size: int
    file_offset: int | None
    table: str


def _unpack(fmt, data, offset):
    if offset < 0 or offset + struct.calcsize(fmt) > len(data):
        raise ValueError('truncated ELF structure')
    return struct.unpack_from(fmt, data, offset)


def _slice(data, start, size):
    if start < 0 or size < 0 or start + size > len(data):
        raise ValueError('truncated ELF data')
    return data[start:start + size]


def _name(table, index):
    if index >= len(table):
        return ''
    end = table.find(b'\x00', index)
    if end < 0:
        return ''
    return table[index:end].decode('utf-8', 'replace')


def find_symbols(data: bytes, targets=TARGETS):
    if len(data) < 52 or data[:6] != b'\x7fELF\x01\x01':
        raise ValueError('expected little-endian ELF32')
    if _unpack('<H', data, 18)[0] != 40:
        raise ValueError('expected ELF32 ARM')
    (e_phoff, e_shoff) = _unpack('<II', data, 28)
    (e_phentsize, e_phnum, e_shentsize, e_shnum) = _unpack('<HHHH', data, 42)
    if e_phnum and e_phentsize < 32 or e_shnum and e_shentsize < 40:
        raise ValueError('malformed ELF header entry sizes')
    segments = []
    for i in range(e_phnum):
        ph = _unpack('<IIIIIIII', data, e_phoff + i * e_phentsize)
        p_type, p_offset, p_vaddr, _, p_filesz, _, _, _ = ph
        if p_type == 1:  # PT_LOAD
            _slice(data, p_offset, p_filesz)
            segments.append((p_vaddr, p_offset, p_filesz))
    sections = []
    for i in range(e_shnum):
        sections.append(_unpack('<IIIIIIIIII', data, e_shoff + i * e_shentsize))
    results = []
    seen = set()
    for i, sh in enumerate(sections):
        _, kind, _, _, offset, size, table_index, _, _, entsize = sh
        if kind not in (2, 11):  # SYMTAB, DYNSYM
            continue
        if not (0 <= table_index < len(sections)) or entsize < 16:
            raise ValueError('invalid symbol/string table reference')
        strsh = sections[table_index]
        string_table = _slice(data, strsh[4], strsh[5])
        _slice(data, offset, size)
        for p in range(offset, offset + size - 15, entsize):
            name_idx, vma, symbol_size, info, _, section_idx = _unpack('<IIIBBH', data, p)
            name = _name(string_table, name_idx)
            if not name or name not in targets or (info & 0xF) != 2 or section_idx == 0:
                continue
            foff = next((off + vma - base for base, off, leng in segments
                         if base <= vma < base + leng), None)
            dedupe = (name, vma, symbol_size)
            if dedupe in seen:
                continue
            seen.add(dedupe)
            results.append(Symbol(name, 'FUNC', vma, symbol_size, foff,
                                  'DYNSYM' if kind == 11 else 'SYMTAB'))
    return sorted(results, key=lambda s: (s.name, s.vma))
