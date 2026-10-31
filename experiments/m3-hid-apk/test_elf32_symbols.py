"""Pure-Python synthetic ELF32 tests; no ARM toolchain required."""
import struct
import unittest
from elf32_symbols import find_symbols


def fixture(function_name='bta_hh_co_set_rpt_rsp'):
    data = bytearray(0x400)
    data[:6] = b'\x7fELF\x01\x01'
    struct.pack_into('<H', data, 18, 40)  # ARM
    struct.pack_into('<II', data, 28, 52, 0x200)  # phoff, shoff
    struct.pack_into('<HHHH', data, 42, 32, 1, 40, 3)
    # PT_LOAD: VMA 0x1000+file offset; entire ELF mapped for this fixture
    struct.pack_into('<IIIIIIII', data, 52, 1, 0, 0x1000, 0, len(data), len(data), 5, 0x1000)
    names = b'\0' + function_name.encode('utf-8') + b'\0'
    data[0x80:0x80 + len(names)] = names
    # 3 section headers: NULL, STRTAB, DYNSYM
    struct.pack_into('<IIIIIIIIII', data, 0x200 + 40, 0, 3, 0, 0, 0x80, len(names), 0, 0, 1, 0)
    struct.pack_into('<IIIIIIIIII', data, 0x200 + 80, 0, 11, 0, 0, 0xA0, 32, 1, 0, 4, 16)
    # second dynsym record (offset 0xB0), FUNC, vma 0x1200 -> offset 0x200
    struct.pack_into('<IIIBBH', data, 0xB0, 1, 0x1200, 16, 2, 0, 1)
    return bytes(data)


class ELF32SymbolTests(unittest.TestCase):
    def test_matching_dynamic_function_with_file_offset(self):
        result = find_symbols(fixture())
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, 'bta_hh_co_set_rpt_rsp')
        self.assertEqual(result[0].file_offset, 0x200)
        self.assertEqual(result[0].vma, 0x1200)

    def test_unmatched_symbol_not_misrepresented_as_missing_function(self):
        self.assertEqual(find_symbols(fixture('not_a_target')), [])

    def test_truncated_file_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'truncated'):
            find_symbols(fixture()[:0x210])

    def test_wrong_architecture_rejected(self):
        d=bytearray(fixture())
        struct.pack_into('<H', d, 18, 62)
        with self.assertRaisesRegex(ValueError, 'ARM'):
            find_symbols(bytes(d))

    def test_wrong_endian_rejected(self):
        d=bytearray(fixture())
        d[5]=2
        with self.assertRaisesRegex(ValueError, 'little-endian'):
            find_symbols(bytes(d))

if __name__ == '__main__':
    unittest.main()
