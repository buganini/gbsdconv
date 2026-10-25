"""Filesystem operations, independent of Qt. Previews never modify user files."""
from dataclasses import dataclass
import fnmatch
import os
from pathlib import Path
import shutil
import stat
import tempfile

from .profiles import TEXT_EXTENSIONS


def display(value):
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return str(value).encode('utf-8', 'replace').decode('utf-8')


def error_count(converter):
    counters = converter.counter()
    return counters.get('IERR', 0) + counters.get('OERR', 0)


def signature(filename):
    value = os.lstat(filename)
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def collect_paths(paths, recursive=False):
    found = {}
    for path in paths:
        path = os.path.abspath(os.fspath(path))
        if not os.path.lexists(path):
            raise FileNotFoundError(path)
        found[path] = None
        if recursive and os.path.isdir(path) and not os.path.islink(path):
            def fail(error):
                raise error
            for parent, dirs, files in os.walk(path, followlinks=False, onerror=fail):
                for name in sorted(dirs + files):
                    found[os.path.join(parent, name)] = None
    return sorted(found)


def matches(filename, pattern):
    for token in pattern.split(';'):
        token = token.strip()
        if not token:
            continue
        if token == r'\a':
            return True
        if token == r'\l' and os.path.islink(filename):
            return True
        if token == r'\d' and os.path.isdir(filename) and not os.path.islink(filename):
            return True
        if token == r'\f' and os.path.isfile(filename) and not os.path.islink(filename):
            return True
        if not token.startswith('\\'):
            if token.startswith('.'):
                token = '*' + token
            if fnmatch.fnmatch(os.path.basename(filename).lower(), token.lower()):
                return True
    return False


def kind(filename):
    if os.path.islink(filename):
        return 'Link'
    return 'Folder' if os.path.isdir(filename) else 'File'


@dataclass
class Rename:
    source: str
    destination: str
    original_signature: tuple
    direct_destination: str = ''
    target: str = ''
    original_target: str = ''
    error: str = ''

    @property
    def changed(self):
        return self.source != self.destination or self.target != self.original_target


def map_path(path, mapping):
    """Apply planned directory renames as well as the leaf's own rename."""
    parent, name = os.path.split(path)
    if parent == path:
        return path
    renamed = os.path.basename(mapping.get(path, path))
    return os.path.join(map_path(parent, mapping), renamed) if parent else renamed


def destination_exists(source, destination):
    if source == destination or not os.path.lexists(destination):
        return False
    # A case-only rename on APFS/HFS+ resolves to the source itself. An actual
    # second directory entry (including a hard link) must still be rejected.
    if os.lstat(source).st_ino == os.lstat(destination).st_ino:
        return os.path.basename(destination) in os.listdir(os.path.dirname(destination))
    return True


def preview_names(paths, converter):
    records = []
    for filename in paths:
        record = Rename(filename, filename, signature(filename))
        try:
            name = os.fsdecode(converter.conv(os.fsencode(os.path.basename(filename))))
            if error_count(converter):
                raise ValueError('Conversion reported invalid or unrepresentable characters.')
            if name in ('', '.', '..') or '\0' in name or os.sep in name or (os.altsep and os.altsep in name):
                raise ValueError('The converted name is not a valid filename.')
            record.direct_destination = os.path.join(os.path.dirname(filename), name)
            if destination_exists(filename, record.direct_destination):
                raise FileExistsError('Destination already exists.')
        except (ValueError, OSError) as error:
            record.error = str(error)
            record.direct_destination = filename
        records.append(record)
    mapping = {item.source: item.direct_destination for item in records}
    destinations = {}
    for item in records:
        item.destination = map_path(item.source, mapping)
        destinations.setdefault(os.path.normcase(item.destination), []).append(item)
        if os.path.islink(item.source):
            item.original_target = os.readlink(item.source)
            resolved = os.path.normpath(os.path.join(os.path.dirname(item.source), item.original_target))
            new_target = map_path(resolved, mapping)
            item.target = item.original_target
            if new_target != resolved or os.path.dirname(item.destination) != os.path.dirname(item.source):
                item.target = new_target if os.path.isabs(item.original_target) else os.path.relpath(new_target, os.path.dirname(item.destination))
    for group in destinations.values():
        if len(group) > 1:
            for item in group:
                item.error = 'Multiple items would have the same destination.'
    return records


def apply_names(records):
    if any(item.error for item in records):
        raise ValueError('Resolve all filename errors before applying this preview.')
    for item in records:
        if signature(item.source) != item.original_signature:
            raise ValueError(f'File changed since preview: {item.source}')
        if destination_exists(item.source, item.direct_destination):
            raise FileExistsError(item.direct_destination)
    completed, changed_links = [], []
    try:
        # Children move before their parents. No cwd changes are needed.
        for item in sorted(records, key=lambda row: row.source.count(os.sep), reverse=True):
            if item.direct_destination != item.source:
                if destination_exists(item.source, item.direct_destination):
                    raise FileExistsError(item.direct_destination)
                os.rename(item.source, item.direct_destination)
                completed.append(item)
        for item in records:
            if item.target != item.original_target:
                replace_link(item.destination, item.target)
                changed_links.append(item)
    except OSError:
        for item in reversed(changed_links):
            replace_link(item.destination, item.original_target)
        for item in reversed(completed):
            os.rename(item.direct_destination, item.source)
        raise
    return sum(item.changed for item in records)


def replace_link(filename, target):
    # Reserve a private directory so symlink creation cannot race a guessed name.
    with tempfile.TemporaryDirectory(prefix='.gbsdconv-link-', dir=os.path.dirname(filename)) as temporary:
        link = os.path.join(temporary, 'link')
        os.symlink(target, link)
        os.replace(link, filename)


def backup_file(filename):
    backup = filename + '.bsdconv.bak'
    created = False
    try:
        with open(backup, 'xb') as target:
            created = True
            with open(filename, 'rb') as source:
                shutil.copyfileobj(source, target)
        shutil.copystat(filename, backup)
    except FileExistsError:
        raise FileExistsError(f'Backup already exists: {backup}') from None
    except Exception:
        if created:
            os.unlink(backup)
        raise
    return backup


def content_candidates(paths, text_only=True):
    return [name for name in paths if os.path.isfile(name) and not os.path.islink(name)
            and (not text_only or Path(name).suffix.lower() in TEXT_EXTENSIONS)]


def preview_content(filename, converter, limit=1024 * 1024):
    with open(filename, 'rb') as source:
        value = source.read(limit + 1)
    truncated = len(value) > limit
    value = value[:limit]
    result = converter.conv(value)
    return value, result, dict(converter.counter()), truncated


def convert_file(filename, converter, backup=True):
    before = signature(filename)
    if not stat.S_ISREG(os.lstat(filename).st_mode):
        raise ValueError('Content conversion requires a regular file, not a symlink.')
    selected = converter.select_file(filename)
    fd, temporary = tempfile.mkstemp(prefix='.gbsdconv-', dir=os.path.dirname(filename))
    try:
        with os.fdopen(fd, 'wb') as target, open(filename, 'rb') as source:
            converter.convert_stream(source, target, selected)
            if error_count(converter):
                raise ValueError(f'Conversion errors; original file preserved: {filename}')
            target.flush()
            os.fsync(target.fileno())
        shutil.copystat(filename, temporary)
        if signature(filename) != before:
            raise ValueError(f'File changed during conversion: {filename}')
        if backup:
            backup_file(filename)
        os.replace(temporary, filename)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return dict(converter.counter())
