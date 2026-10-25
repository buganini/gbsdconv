"""Lazy loading of the private TagLib bridge; the GUI also runs without it."""
import ctypes as C
import os
from pathlib import Path

_library = None


def load():
    global _library
    if _library is not None:
        return _library
    root = Path(__file__).parent
    candidates = []
    if os.environ.get('GBSDCONV_TAGLIB'):
        candidates.append(Path(os.environ['GBSDCONV_TAGLIB']))
    candidates.extend(sorted((root / 'src').glob('_taglib*')))
    candidates.append(root / 'gbsdconv_taglib.so')
    errors = []
    for filename in candidates:
        if not filename.is_file():
            continue
        try:
            library = C.CDLL(str(filename))
            break
        except OSError as error:
            errors.append(str(error))
    else:
        detail = '\n'.join(errors)
        raise RuntimeError('Media tags require the TagLib bridge. Install TagLib, then run '
                           '`python -m pip install --force-reinstall --no-deps .`.\n' + detail)
    def bind(name, args, result):
        function = getattr(library, name)
        function.argtypes = args
        function.restype = result
    bind('taglib_file_new', [C.c_char_p], C.c_void_p)
    bind('taglib_file_is_valid', [C.c_void_p], C.c_int)
    bind('taglib_file_save', [C.c_void_p], C.c_int)
    bind('taglib_file_free', [C.c_void_p], None)
    bind('taglib_file_tag', [C.c_void_p], C.c_void_p)
    bind('taglib_tag_free_strings', [], None)
    for field in ('title', 'artist', 'album', 'comment', 'genre'):
        bind('taglib_tag_' + field, [C.c_void_p], C.c_char_p)
        bind('taglib_tag_set_' + field, [C.c_void_p, C.c_char_p], None)
    for field in ('year', 'track'):
        bind('taglib_tag_' + field, [C.c_void_p], C.c_uint)
    bind('taglib_mpeg_file', [C.c_void_p], C.c_void_p)
    bind('taglib_mpeg_file_save3', [C.c_void_p, C.c_int, C.c_int, C.c_int], C.c_int)
    bind('taglib_mpeg_file_strip', [C.c_void_p, C.c_int], C.c_int)
    _library = library
    return library
