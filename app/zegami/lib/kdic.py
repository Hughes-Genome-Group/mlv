# coding: utf-8
#
# Copyright 2017 Zegami Ltd

"""In memory representation of kanjidic."""

import codecs
import gzip
import re


# Use unicode type regardless of python version
text = type(u"")

# Overly complex regexp for parsing kanjidic
_pat = re.compile(
    u"^(?P<char>[^ ]+)"
    u" (?P<jis>[0-9a-fA-F]+)"
    u" U(?P<unicode>[0-9a-f]+)"
    u" B(?P<classification>\\d+)"
    u"(?: C\\d+)?"
    u"(?: G(?P<grade>\\d+)\\b)?"
    u" S(?P<stroke_count>\\d+)\\b"
    u"(?: S\\d+)*"
    u"(?: [FJHNVDPIMEKLOXZ][^ ]+)*"
    u"(?P<four_corner>(?: Q[.\\d]+)*)"
    u"(?: [DZYW][^ ]+)*"
    u"(?P<on_readings>(?: [-ア-ンー]+)*)"
    u"(?P<kun_readings>(?: [-.あ-ん]+)*)"
    u"(?: T\\d+(?: [-.あ-んア-ンー]+)+)*"
    u"(?P<translations>(?: {[^}]+})*)"
    u" $", re.UNICODE)


def optint(string_or_none):
    if string_or_none is None:
        return None
    return int(string_or_none)


def multi(sep):
    def _strip_and_split(string):
        return string.strip(sep).split(sep)
    return _strip_and_split


split = text.split
corners = multi(" Q")
trans = multi("} {")


class Kanji(object):

    __slots__ = (
        "char", "jis", "unicode", "classification", "stroke_count", "grade",
        "four_corner", "on_readings", "kun_readings", "translations")

    _conversions = dict(zip(__slots__, (
        text, text, text, int, int, optint, corners, split, split, trans)))

    def __init__(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])

    @classmethod
    def from_line(cls, line):
        match = _pat.match(line)
        if match is None:
            raise ValueError("unparsable line {!r}".format(line))
        d = match.groupdict()
        return cls(**dict((k, cls._conversions[k](d[k])) for k in d))

    @classmethod
    def header_row(cls):
        return "id\t{}\n".format(
            "\t".join(n.replace("_", " ") for n in cls.__slots__[1:]))

    def to_row(self):
        return "\t".join(self._as_data(k) for k in self.__slots__) + "\n"

    def _as_data(self, key):
        value = getattr(self, key, None)
        if value is None:
            return ""
        if isinstance(value, list):
            return ",".join(v.replace(",", "\\,") for v in value)
        return text(value)

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, ", ".join(
            "{}={!r}".format(k, getattr(self, k)) for k in self.__slots__
            if getattr(self, k, None) is not None))

    def __str__(self):
        some_translations = self.translations[:2]
        if len(self.translations) > 2:
            some_translations.append("...")
        return "{!r} {}".format(self.char, " / ".join(some_translations))


class KanjiDic(object):

    ENCODING = "EUC_JP"
    HEADER_START = b"# KANJIDIC JIS X 0208 Kanji Information File/"

    def __init__(self, line_iter):
        self.kanji = [Kanji.from_line(line) for line in line_iter]

    def __len__(self):
        return len(self.kanji)

    def __repr__(self):
        return "<{} len={}>".format(self.__class__.__name__, len(self))

    @classmethod
    def from_file(cls, fileobj):
        first = fileobj.readline()
        if not first.startswith(cls.HEADER_START):
            raise ValueError("Not a kanjidic file")
        return cls(line.decode(cls.ENCODING) for line in fileobj)

    @classmethod
    def from_gzip(cls, gzip_filename):
        with gzip.GzipFile(gzip_filename) as f:
            return cls.from_file(f)

    def extend(self, other):
        self.kanji.extend(other.kanji)

    def to_tsv(self, tsv_filename):
        with codecs.open(tsv_filename, "wb", encoding='utf-8') as f:
            f.write(Kanji.header_row())
            f.writelines(k.to_row() for k in self.kanji)


class KanjiDic0212(KanjiDic):

    HEADER_START = b"# KANJD212 JIS X 0212 Kanji Information File/"
