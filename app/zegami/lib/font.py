# Copyright 2017 Zegami Ltd

"""Tools for loading font and rendering characters."""

import freetype
import PIL.Image
import PIL.ImageOps


def load_face(path):
    return freetype.Face(path)


def render_glyph(face, char, filename):
    """Render a glyph to an image on disk."""
    face.set_char_size(256 * 256)
    face.load_char(
        char, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
    _do_render(face.glyph.bitmap, filename)


def _do_render(bitmap, filename):
    """Hackish rendering into png on disk using PIL."""
    bb = bytes(bytearray(bitmap.buffer))
    # Using pitch below is bogus, should adjust for width after
    img = PIL.Image.frombytes("L", (bitmap.pitch, bitmap.rows), bb)
    img = img.resize((img.width // 2, img.height // 2), PIL.Image.BILINEAR)
    img = PIL.ImageOps.expand(img, 10)
    img = PIL.ImageOps.invert(img)
    img.save(filename)
