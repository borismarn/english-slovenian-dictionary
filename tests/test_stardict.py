import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from tools.stardict import DICTIONARIES, DictionaryError, ROOT, build, entries, verify


class StarDictTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.data = {"##name": "metadata", "pismo": "pismo\nRazlaga.", "pisma": "pisma", "črka": "slovo"}
        for spec in DICTIONARIES.values():
            self.write(spec[0], self.data)

    def write(self, filename, value):
        (self.root / filename).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def export(self, suffix):
        return (self.root / DICTIONARIES["eng-slo"][1]).with_suffix(suffix)

    def test_both_dictionaries_round_trip_without_changing_json(self):
        self.write("slo_ser_sources.json", {"stardict_description": "Vir: Sloleks; CC BY-SA 4.0."})
        for name, spec in DICTIONARIES.items():
            with self.subTest(name=name):
                before = (self.root / spec[0]).read_bytes()
                self.assertEqual(build(self.root, name), 3)
                self.assertEqual(verify(self.root, name), 3)
                self.assertEqual((self.root / spec[0]).read_bytes(), before)
                first = [(self.root / spec[1]).with_suffix(s).read_bytes() for s in (".idx", ".dict", ".ifo")]
                build(self.root, name)
                self.assertEqual(first, [(self.root / spec[1]).with_suffix(s).read_bytes() for s in (".idx", ".dict", ".ifo")])
        header = (self.root / "stardict_slo_ser.ifo").read_text(encoding="utf-8")
        self.assertIn("bookname=Slovensko-srbski slovar", header)
        self.assertIn("description=Vir: Sloleks; CC BY-SA 4.0.", header)

    def test_duplicate_json_keys_are_rejected(self):
        (self.root / "eng_slo.json").write_text('{"word": "one", "word": "two"}')
        with self.assertRaisesRegex(DictionaryError, "Duplicate JSON key"):
            build(self.root, "eng-slo")

    def test_invalid_entries_are_rejected(self):
        for word, value in (("", "empty key"), ("bad\0key", "value"), ("word", " "), ("word", None), ("word", "bad\0value")):
            with self.subTest(word=word, value=value):
                self.write("eng_slo.json", {word: value})
                with self.assertRaises(DictionaryError):
                    entries(self.root, "eng-slo")

    def test_top_level_json_must_be_an_object(self):
        self.write("eng_slo.json", ["word"])
        with self.assertRaisesRegex(DictionaryError, "JSON object"):
            entries(self.root, "eng-slo")

    def test_definition_corruption_is_detected(self):
        build(self.root, "eng-slo")
        self.export(".dict").write_bytes(b"x" + self.export(".dict").read_bytes()[1:])
        with self.assertRaisesRegex(DictionaryError, "Definition mismatch"):
            verify(self.root, "eng-slo")

    def test_truncated_index_is_detected(self):
        build(self.root, "eng-slo")
        self.export(".idx").write_bytes(self.export(".idx").read_bytes()[:-1])
        with self.assertRaisesRegex(DictionaryError, "Truncated index"):
            verify(self.root, "eng-slo")

    def test_wrong_offset_is_detected(self):
        build(self.root, "eng-slo")
        data = bytearray(self.export(".idx").read_bytes())
        start = data.index(0) + 1
        data[start:start + 4] = struct.pack(">I", 1)
        self.export(".idx").write_bytes(data)
        with self.assertRaisesRegex(DictionaryError, "Index mismatch"):
            verify(self.root, "eng-slo")

    def test_trailing_data_is_detected(self):
        for suffix in (".idx", ".dict"):
            with self.subTest(suffix=suffix):
                build(self.root, "eng-slo")
                self.export(suffix).write_bytes(self.export(suffix).read_bytes() + b"x")
                with self.assertRaisesRegex(DictionaryError, "trailing"):
                    verify(self.root, "eng-slo")

    def test_header_corruption_is_detected(self):
        build(self.root, "eng-slo")
        self.export(".ifo").write_text("not a StarDict header\n")
        with self.assertRaisesRegex(DictionaryError, "Invalid StarDict header"):
            verify(self.root, "eng-slo")

    def test_header_count_is_checked(self):
        build(self.root, "eng-slo")
        value = self.export(".ifo").read_text().replace("wordcount=3", "wordcount=4")
        self.export(".ifo").write_text(value)
        with self.assertRaisesRegex(DictionaryError, "header does not match"):
            verify(self.root, "eng-slo")

    def test_failed_build_preserves_existing_export(self):
        build(self.root, "slo-ser")
        files = [(self.root / "stardict_slo_ser").with_suffix(s) for s in (".idx", ".dict", ".ifo")]
        before = [path.read_bytes() for path in files]
        self.write("slo_ser_sources.json", {"stardict_description": "bad\nfield=value"})
        with self.assertRaisesRegex(DictionaryError, "single line"):
            build(self.root, "slo-ser")
        self.assertEqual([path.read_bytes() for path in files], before)
        self.assertFalse(list(self.root.glob(".stardict-*")))

    def test_command_runs_from_a_different_directory(self):
        script = ROOT / "tools" / "stardict.py"
        result = subprocess.run([sys.executable, str(script), "build", "--root", str(self.root)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("slo-ser: build OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
