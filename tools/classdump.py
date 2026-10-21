#!/usr/bin/env python3
"""Minimal Java .class inspector.

Reads a .class file (or a class entry inside a jar) and dumps:
  - header (version, this/super class)
  - UTF-8 constants (strings / names / descriptors)
  - declared methods with descriptors
  - declared fields with descriptors
  - implemented interfaces

Used because Visual Paradigm ships a JRE without javap.

Usage:
  python classdump.py <file.class>
  python classdump.py <archive.jar> <internal/Name.class>
  python classdump.py <archive.jar> --grep <substring>
"""
import struct
import sys
import zipfile

CONST_SIZES = {
    3: 4, 4: 4, 5: 8, 6: 8, 7: 2, 8: 2, 9: 4, 10: 4, 11: 4, 12: 4,
    15: 3, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2,
}


class ClassFile:
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.consts = {}
        self.parse()

    def u1(self):
        v = self.data[self.pos]
        self.pos += 1
        return v

    def u2(self):
        v = struct.unpack_from('>H', self.data, self.pos)[0]
        self.pos += 2
        return v

    def u4(self):
        v = struct.unpack_from('>I', self.data, self.pos)[0]
        self.pos += 4
        return v

    def parse(self):
        magic = self.u4()
        if magic != 0xCAFEBABE:
            raise ValueError('not a class file')
        self.minor = self.u2()
        self.major = self.u2()
        n = self.u2()
        i = 1
        while i < n:
            tag = self.u1()
            if tag == 1:
                ln = self.u2()
                raw = self.data[self.pos:self.pos + ln]
                self.pos += ln
                try:
                    s = raw.decode('utf-8', 'replace')
                except Exception:
                    s = ''
                self.consts[i] = ('utf8', s)
            elif tag in (5, 6):
                self.consts[i] = ('wide', None)
                i += 1
            elif tag in CONST_SIZES:
                self.consts[i] = ('raw%d' % tag, self.data[self.pos:self.pos + CONST_SIZES[tag]])
                self.pos += CONST_SIZES[tag]
            else:
                raise ValueError('bad const tag %d at %d' % (tag, self.pos))
            i += 1
        self.access = self.u2()
        self.this_idx = self.u2()
        self.super_idx = self.u2()
        ic = self.u2()
        self.interfaces = [self.class_name(self.u2()) for _ in range(ic)]
        self.fields = self.members()
        self.methods = self.members()

    def utf(self, idx):
        e = self.consts.get(idx)
        return e[1] if e and e[0] == 'utf8' else None

    def class_name(self, idx):
        e = self.consts.get(idx)
        if not e or e[0] != 'raw7':
            return None
        return self.utf(struct.unpack('>H', e[1])[0])

    def members(self):
        out = []
        n = self.u2()
        for _ in range(n):
            acc = self.u2()
            name = self.utf(self.u2())
            desc = self.utf(self.u2())
            ac = self.u2()
            for _ in range(ac):
                self.u2()          # attribute_name_index
                ln = self.u4()     # attribute_length
                self.pos += ln
            out.append((acc, name, desc))
        return out

    def strings(self):
        return sorted({e[1] for e in self.consts.values() if e[0] == 'utf8'})


def fmt_access(a):
    bits = []
    for bit, name in ((0x1, 'public'), (0x2, 'private'), (0x4, 'protected'), (0x8, 'static'),
                      (0x10, 'final'), (0x400, 'abstract'), (0x200, 'interface')):
        if a & bit:
            bits.append(name)
    return '|'.join(bits) or 'package'


def dump(cf, title):
    lines = []
    lines.append('=== %s ===' % title)
    lines.append('classfile version %d.%d  access=%s' % (cf.major, cf.minor, fmt_access(cf.access)))
    lines.append('this=%s  super=%s' % (cf.class_name(cf.this_idx), cf.class_name(cf.super_idx)))
    if cf.interfaces:
        lines.append('implements: %s' % ', '.join(x or '?' for x in cf.interfaces))
    if cf.fields:
        lines.append('-- fields --')
        for acc, name, desc in cf.fields:
            lines.append('  %-28s %s' % (name, desc))
    if cf.methods:
        lines.append('-- methods --')
        for acc, name, desc in cf.methods:
            lines.append('  %-28s %s' % (name, desc))
    lines.append('-- string constants --')
    for s in cf.strings():
        if len(s) <= 200:
            lines.append('  ' + s)
    return '\n'.join(lines)


def load(path, entry=None):
    if entry is None:
        with open(path, 'rb') as f:
            return f.read()
    with zipfile.ZipFile(path) as z:
        return z.read(entry)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    target = argv[1]
    if len(argv) >= 3 and argv[2] == '--grep':
        pat = argv[3].lower()
        with zipfile.ZipFile(target) as z:
            for info in z.infolist():
                if info.filename.lower().endswith('.class') and pat in info.filename.lower():
                    print(dump(ClassFile(z.read(info.filename)), info.filename))
                    print()
        return 0
    entry = argv[2] if len(argv) >= 3 else None
    print(dump(ClassFile(load(target, entry)), entry or target))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
