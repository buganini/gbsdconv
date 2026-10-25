"""Read, preview and save media fields through the private TagLib bridge."""
from contextlib import contextmanager
import os
import shutil
import tempfile

from taglib import load
from .operations import backup_file, error_count, signature

FIELDS = ('title', 'artist', 'album', 'comment', 'genre')


@contextmanager
def media_file(filename):
    library = load()
    handle = library.taglib_file_new(os.fsencode(filename))
    if not handle:
        raise ValueError(f'Unsupported or unreadable media file: {filename}')
    try:
        if not library.taglib_file_is_valid(handle):
            raise ValueError(f'Invalid media file: {filename}')
        yield library, handle
    finally:
        library.taglib_tag_free_strings()
        library.taglib_file_free(handle)


def read(filename):
    with media_file(filename) as (library, handle):
        tag = library.taglib_file_tag(handle)
        values = {field: (getattr(library, 'taglib_tag_' + field)(tag) or b'') for field in FIELDS}
        values.update({field: getattr(library, 'taglib_tag_' + field)(tag) for field in ('year', 'track')})
        return values


def preview(filename, converter, enabled=FIELDS, remove_comment=False, recover_latin1=True):
    before = signature(filename)
    original = read(filename)
    converter.score_clear()
    converter.score_train(os.fsencode(filename))
    fields = [field for field in FIELDS if field in enabled and not (field == 'comment' and remove_comment)]
    values = []
    for field in fields:
        value = original[field]
        if recover_latin1:
            try:
                value = value.decode('utf-8').encode('latin1')
            except UnicodeError:
                pass
        values.append(value)
    converted = converter.conv_list(values)
    if error_count(converter):
        raise ValueError('Metadata conversion reported errors; no tags were modified.')
    result = dict(original)
    for field, value in zip(fields, converted):
        value.decode('utf-8')  # TagLib setters require UTF-8, unlike arbitrary file output.
        if b'\0' in value:
            raise ValueError('Metadata cannot contain NUL bytes.')
        result[field] = value
    if remove_comment:
        result['comment'] = b''
    return original, result, before


def save(filename, result, before, backup=True, id3v23=True, remove_id3v1=True):
    if os.path.islink(filename) or signature(filename) != before:
        raise ValueError(f'File changed since preview or is a symlink: {filename}')
    for field in FIELDS:
        result[field].decode('utf-8')
        if b'\0' in result[field]:
            raise ValueError('Metadata cannot contain NUL bytes.')
    # TagLib identifies some formats by suffix. Work on a copy so a failed save
    # cannot damage the original, even when the user disables backups.
    fd, temporary = tempfile.mkstemp(prefix='.gbsdconv-', suffix=os.path.splitext(filename)[1],
                                     dir=os.path.dirname(filename))
    os.close(fd)
    try:
        shutil.copyfile(filename, temporary)
        with media_file(temporary) as (library, handle):
            tag = library.taglib_file_tag(handle)
            for field in FIELDS:
                getattr(library, 'taglib_tag_set_' + field)(tag, result[field])
            mpeg = library.taglib_mpeg_file(handle)
            if mpeg and id3v23:
                success = library.taglib_mpeg_file_save3(mpeg, 0xffff, 0, 3)
            else:
                success = library.taglib_file_save(handle)
            if not success:
                raise OSError(f'TagLib could not save {filename}')
            if mpeg and remove_id3v1 and not library.taglib_mpeg_file_strip(mpeg, 1):
                raise OSError(f'TagLib could not remove ID3v1 tags from {filename}')
        with open(temporary, 'rb') as converted:
            os.fsync(converted.fileno())
        shutil.copystat(filename, temporary)
        if signature(filename) != before:
            raise ValueError(f'File changed during conversion: {filename}')
        if backup:
            backup_file(filename)
        os.replace(temporary, filename)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
