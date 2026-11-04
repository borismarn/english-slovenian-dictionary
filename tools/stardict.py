"""Build and validate the project's JSON dictionaries using only Python's standard library."""

import argparse
import json
import os
from pathlib import Path
import struct
import tempfile


ROOT = Path(__file__).resolve().parents[1]
DICTIONARIES = {
    "eng-slo": ("eng_slo.json", "stardict_eng_slo", "stardict_eng_slo", None),
    "slo-ser": ("slo_ser.json", "stardict_slo_ser", "Slovensko-srbski slovar", "slo_ser_sources.json"),
}


class DictionaryError(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DictionaryError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def load_json(path):
    with path.open(encoding="utf-8") as stream:
        result = json.load(stream, object_pairs_hook=unique_object)
    if not isinstance(result, dict):
        raise DictionaryError(f"Expected a JSON object: {path}")
    return result


def entries(root, name):
    data = load_json(root / DICTIONARIES[name][0])
    result = []
    for word, definition in data.items():
        if word.startswith("##"):
            continue
        if not word or "\0" in word:
            raise DictionaryError(f"Invalid headword: {word!r}")
        if not isinstance(definition, str) or not definition.strip() or "\0" in definition:
            raise DictionaryError(f"Invalid definition for {word!r}")
        result.append((word, definition))
    return sorted(result)


def description(root, name):
    metadata = DICTIONARIES[name][3]
    if metadata is None or not (root / metadata).exists():
        return None
    value = load_json(root / metadata).get("stardict_description")
    if value is not None and (not isinstance(value, str) or any(c in value for c in "\r\n\0")):
        raise DictionaryError("StarDict description must be a single line of text")
    return value


def header(root, name, count, index_size):
    fields = {
        "version": "3.0.0",
        "bookname": DICTIONARIES[name][2],
        "wordcount": str(count),
        "idxfilesize": str(index_size),
        "sametypesequence": "m",
    }
    note = description(root, name)
    if note is not None:
        fields["description"] = note
    return fields


def verify(root, name, *, base=None, items=None):
    root = Path(root)
    base = Path(base) if base is not None else root / DICTIONARIES[name][1]
    items = entries(root, name) if items is None else items
    index = base.with_suffix(".idx").read_bytes()
    position = offset = 0
    with base.with_suffix(".dict").open("rb") as body:
        for word, definition in items:
            end = index.find(b"\0", position)
            if end < 0 or end + 9 > len(index):
                raise DictionaryError(f"Truncated index at {word!r}")
            try:
                actual_word = index[position:end].decode("utf-8")
            except UnicodeDecodeError as error:
                raise DictionaryError("Invalid UTF-8 in index") from error
            start, size = struct.unpack(">II", index[end + 1:end + 9])
            expected = definition.encode("utf-8")
            if actual_word != word or start != offset or size != len(expected):
                raise DictionaryError(f"Index mismatch at {word!r}")
            if body.read(size) != expected:
                raise DictionaryError(f"Definition mismatch at {word!r}")
            offset += size
            position = end + 9
        if position != len(index) or body.read(1):
            raise DictionaryError("Unexpected trailing index or dictionary data")
    lines = base.with_suffix(".ifo").read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "StarDict's dict ifo file":
        raise DictionaryError("Invalid StarDict header")
    pairs = []
    for line in lines[1:]:
        if "=" not in line:
            raise DictionaryError("Malformed StarDict header field")
        pairs.append(line.split("=", 1))
    if unique_object(pairs) != header(root, name, len(items), len(index)):
        raise DictionaryError("StarDict header does not match the JSON dictionary")
    return len(items)


def build(root, name):
    root = Path(root)
    items = entries(root, name)
    basename = DICTIONARIES[name][1]
    # Validate staged files before replacing an existing usable export.
    with tempfile.TemporaryDirectory(prefix=".stardict-", dir=root) as temporary:
        base = Path(temporary) / basename
        offset = index_size = 0
        with base.with_suffix(".dict").open("wb") as body, base.with_suffix(".idx").open("wb") as index:
            for word, definition in items:
                head = word.encode("utf-8")
                value = definition.encode("utf-8")
                if offset + len(value) > 0xFFFFFFFF:
                    raise DictionaryError("Dictionary exceeds StarDict's 32-bit size limit")
                body.write(value)
                record = head + b"\0" + struct.pack(">II", offset, len(value))
                index.write(record)
                index_size += len(record)
                offset += len(value)
        fields = header(root, name, len(items), index_size)
        base.with_suffix(".ifo").write_text(
            "StarDict's dict ifo file\n" + "\n".join(f"{key}={value}" for key, value in fields.items()) + "\n",
            encoding="utf-8",
        )
        verify(root, name, base=base, items=items)
        for suffix in (".dict", ".idx", ".ifo"):
            os.replace(base.with_suffix(suffix), (root / basename).with_suffix(suffix))
    return len(items)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "verify", "stats"))
    parser.add_argument("--dictionary", choices=("all", *DICTIONARIES), default="all")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    names = DICTIONARIES if args.dictionary == "all" else (args.dictionary,)
    try:
        for name in names:
            if args.action == "stats":
                items = entries(args.root, name)
                print(f"{name}: {len(items):,} entries; {sum(chr(10) in value for _, value in items):,} multiline definitions")
            else:
                count = {"build": build, "verify": verify}[args.action](args.root, name)
                print(f"{name}: {args.action} OK ({count:,} entries)")
    except (DictionaryError, OSError, json.JSONDecodeError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
