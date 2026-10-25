"""Declarative PUI desktop UI."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os

from .common import *
from PySide6 import QtCore
from bsdconv import Bsdconv
from bsdconvs import Bsdconvs

from . import metadata
from . import operations as ops
from .profiles import PROFILES, TEXT_EXTENSIONS, MEDIA_EXTENSIONS
from .views import TextView, FilesView, ConversionView, FilenamesView, ContentsView, TagsView


class Completion(QtCore.QObject):
    finished = QtCore.Signal(object, object)


class CloseGuard(QtCore.QObject):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.Close and self.owner.state.busy:
            self.owner.state.status = 'An operation is running. Close the window after it finishes.'
            event.ignore()
            return True
        return False


class Window(BaseWindow):
    def __init__(self, owner):
        super().__init__(title='gbsdconv', size=(1120, 780),
                         icon=str(Path(__file__).parent / 'assets' / 'gbsdconv.png'))
        self.owner = owner

    def update(self, prev=None):
        super().update(prev)
        if prev is None:
            self.ui.installEventFilter(self.owner.close_guard)


class Application(BaseApplication):
    def __init__(self, paths=()):
        super().__init__(title='gbsdconv')
        self.state = State()
        self.state.expression = 'UTF-8:UTF-8'
        self.state.profile = 'UTF-8 passthrough'
        self.state.from_codec, self.state.inter_codec, self.state.to_codec = 'UTF-8', '', 'UTF-8'
        self.state.url_source, self.state.url_target = 'UTF-8', 'UTF-8'
        self.state.mistreat_source, self.state.mistreat_target = 'BIG5', 'ISO-8859-1'
        self.state.factor_ierr, self.state.factor_oerr, self.state.factor_score = -10.0, -10.0, 1.0
        self.state.train = False
        self.state.input_text, self.state.output_text = '', ''
        self.state.text_info = 'Type or paste text to convert.'
        self.state.preview_encoding = 'utf-8'
        self.state.recursive = True
        self.state.filter = r'\a'
        self.state.filter_profile = 'All'
        self.state.focused = ''
        self.state.text_only = True
        self.state.backup = True
        self.state.content_before, self.state.content_after, self.state.content_info = '', '', ''
        self.state.recover_latin1, self.state.remove_comment = True, False
        self.state.id3v23, self.state.remove_id3v1 = True, True
        for field in metadata.FIELDS:
            setattr(self.state, 'tag_' + field, True)
        self.state.status = 'Ready — select a conversion, then preview the result.'
        self.state.busy, self.state.revision = False, 0
        self.state.tab = 'text'
        self.paths = ops.collect_paths(paths) if paths else []
        self.checked = set(self.paths)
        self.names = []
        self.names_key = None
        self.tag_preview = None
        self.output_bytes = b''
        self.has_text_result = False
        self.codecs = {name: sorted(Bsdconv.modules_list(value), key=str.casefold)
                       for name, value in [('from', Bsdconv.FROM), ('inter', Bsdconv.INTER), ('to', Bsdconv.TO)]}
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='gbsdconv')
        self.completion = Completion()
        self.completion.finished.connect(self._completed, QtCore.Qt.ConnectionType.QueuedConnection)
        self.close_guard = CloseGuard(self)
        self.window = None

    def content(self):
        _ = self.state.revision
        with Window(self) as window:
            self.window = window
            with VBox().layout(padding=16):
                with HBox():
                    Label('gbsdconv').style(fontSize=24, fontWeight=600)
                    Label('Text & file encoding converter')
                    Spacer()
                    Label(f'{len(self.checked)} selected / {len(self.paths)} items')
                with HBox():
                    Label('Conversion')
                    TextField(self.state('expression'), self.state('expression'), placeholder='UTF-8:UTF-8;BIG5:UTF-8').input(self.invalidate).layout(weight=1)
                    Button('Validate', disabled=self.state.busy).click(self.validate)
                with Tabs(model=self.state('tab')).layout(weight=1):
                    with Tab('Text').id('text'):
                        TextView(self)
                    with Tab('Files').id('files'):
                        FilesView(self)
                    with Tab('Conversion').id('conversion'):
                        ConversionView(self)
                    with Tab('Filenames').id('names'):
                        FilenamesView(self)
                    with Tab('File contents').id('contents'):
                        ContentsView(self)
                    with Tab('Media tags').id('tags'):
                        TagsView(self)
                Divider()
                Label(('Working…  ' if self.state.busy else '') + self.state.status)

    def config(self):
        return self.state.expression, self.state.train, (self.state.factor_ierr, self.state.factor_oerr, self.state.factor_score)

    def preview_key(self):
        return self.config(), tuple(sorted(self.checked))

    def invalidate(self, event=None):
        self.names_key = None
        self.state.status = 'Conversion changed. Validate or create a new preview.'

    def refresh(self, message=None):
        self.state.revision += 1
        if message is not None:
            self.state.status = message

    def submit(self, action, callback):
        if self.state.busy:
            return
        self.state.busy = True
        self.state.status = 'Processing…'
        future = self.executor.submit(action)
        future.add_done_callback(lambda result: self.completion.finished.emit(callback, result))

    def _completed(self, callback, future):
        self.state.busy = False
        try:
            callback(future.result())
        except Exception as error:
            self.state.status = str(error)
        self.refresh()

    @staticmethod
    def counters_text(counters):
        return f"Input errors: {counters.get('IERR', 0)} · Output errors: {counters.get('OERR', 0)}"

    def validate(self, event=None):
        try:
            with Bsdconvs(*self.config()):
                pass
            self.state.status = 'Conversion is valid.'
        except Exception as error:
            self.state.status = str(error)

    def use_profile(self, event=None, append=False):
        value = PROFILES[self.state.profile]
        self.state.expression = self.state.expression.rstrip(';') + ';' + value if append else value
        self.invalidate()

    def use_codecs(self, event=None):
        self.state.expression = ':'.join(value.strip(':') for value in
                                       (self.state.from_codec, self.state.inter_codec, self.state.to_codec) if value)
        self.invalidate()

    def url_decoder(self, event=None):
        self.state.expression = f'ESCAPE,{self.state.url_target}:UNICODE,BYTE|SKIP,{self.state.url_source}:UTF-8'
        self.invalidate()

    def mojibake(self, event=None):
        self.state.expression = f'UTF-8:{self.state.mistreat_target}|{self.state.mistreat_source}:UTF-8'
        self.invalidate()

    def convert_text(self, event=None):
        config, text, encoding = self.config(), self.state.input_text, self.state.preview_encoding
        def action():
            with Bsdconvs(*config) as converter:
                result = converter.conv(text)
                return result, result.decode(encoding, 'replace'), converter.counter(), converter.specs[converter.lastc]
        def done(result):
            self.output_bytes, self.state.output_text, counters, spec = result
            self.has_text_result = True
            self.state.text_info = self.counters_text(counters) + ' · ' + spec
            self.state.status = f'Converted {len(self.output_bytes)} bytes.'
        self.submit(action, done)

    def copy_text(self, event=None):
        self.ui.clipboard().setText(self.state.output_text)
        self.state.status = 'Result copied.'

    def save_text(self, event=None):
        filename = SaveFile(default='converted.txt', title='Save converted bytes')
        if filename:
            try:
                Path(filename).write_bytes(self.output_bytes)
                self.state.status = f'Saved {filename}'
            except OSError as error:
                self.state.status = str(error)

    def add_paths(self, paths):
        recursive = self.state.recursive
        def done(result):
            self.paths = sorted(set(self.paths).union(result))
            self.checked.update(result)
            self.names_key = None
            if not self.state.focused:
                self.state.focused = next((p for p in result if os.path.isfile(p) and not os.path.islink(p)), '')
            self.state.status = f'Added {len(result)} items.'
        self.submit(lambda: ops.collect_paths(paths, recursive), done)

    def add_files(self, event=None):
        paths = OpenFiles(title='Add files')
        if paths:
            self.add_paths(paths)

    def add_folder(self, event=None):
        path = OpenDirectory(title='Add folder')
        if path:
            self.add_paths([path])

    def clear_files(self, event=None):
        self.paths.clear()
        self.checked.clear()
        self.names.clear()
        self.tag_preview = None
        self.state.focused = ''
        self.refresh('File list cleared.')

    def remove_selected(self, event=None):
        self.paths = [path for path in self.paths if path not in self.checked]
        self.checked.clear()
        self.names.clear()
        if self.state.focused not in self.paths:
            self.state.focused = ''
        self.refresh('Selected items removed from the list.')

    def focus(self, event, path):
        if not self.state.busy:
            self.state.focused = path if os.path.isfile(path) and not os.path.islink(path) else ''
            self.state.status = ops.display(path)

    def toggle(self, event, path):
        if self.state.busy:
            return
        if path in self.checked:
            self.checked.remove(path)
        else:
            self.checked.add(path)
        self.refresh()

    def select_all(self, event, selected):
        self.checked = set(self.paths) if selected else set()
        self.refresh()

    def invert(self, event=None):
        self.checked = set(self.paths) - self.checked
        self.refresh()

    def set_filter(self, event=None):
        self.state.filter = {'All': r'\a', 'Files': r'\f', 'Folders': r'\d', 'Links': r'\l',
                             'Text files': ';'.join(sorted(TEXT_EXTENSIONS)),
                             'Media files': ';'.join(sorted(MEDIA_EXTENSIONS))}[self.state.filter_profile]

    def filter_items(self, event, selected):
        matched = {path for path in self.paths if ops.matches(path, self.state.filter)}
        self.checked = self.checked | matched if selected else self.checked - matched
        self.refresh(f'{len(matched)} matching items.')

    def preview_names(self, event=None):
        key = self.preview_key()
        config, paths = key
        def action():
            with Bsdconvs(*config) as converter:
                for path in paths:
                    converter.score_train(os.fsencode(path))
                return ops.preview_names(paths, converter)
        def done(records):
            self.names, self.names_key = records, key
            self.state.status = f'{sum(row.changed for row in records)} changes · {sum(bool(row.error) for row in records)} errors'
        self.submit(action, done)

    def apply_names(self, event=None):
        if self.names_key != self.preview_key():
            self.state.status = 'Selection or conversion changed. Preview again.'
            return
        records = list(self.names)
        if not Confirm(f'Rename {sum(row.changed for row in records)} items using this preview?', title='Apply filename changes'):
            return
        def done(count):
            mapping = {row.source: row.direct_destination for row in records}
            self.paths = [ops.map_path(path, mapping) for path in self.paths]
            self.checked = {ops.map_path(path, mapping) for path in self.checked}
            if self.state.focused:
                self.state.focused = ops.map_path(self.state.focused, mapping)
            self.names, self.names_key = [], None
            self.state.status = f'Renamed {count} items.'
        self.submit(lambda: ops.apply_names(records), done)

    def preview_contents(self, event=None):
        config, filename = self.config(), self.state.focused
        def action():
            with Bsdconvs(*config) as converter:
                converter.score_train(os.fsencode(filename))
                return ops.preview_content(filename, converter)
        def done(result):
            original, converted, counters, truncated = result
            self.state.content_before, self.state.content_after = ops.display(original), ops.display(converted)
            self.state.content_info = self.counters_text(counters) + (' · First 1 MiB only' if truncated else '')
            self.state.status = f'Previewed {ops.display(filename)}'
        self.submit(action, done)

    @staticmethod
    def batch(paths, operation):
        completed, failed = 0, []
        for filename in paths:
            try:
                operation(filename)
                completed += 1
            except Exception as error:
                failed.append(f'{ops.display(filename)}: {error}')
        return completed, failed

    def batch_done(self, result):
        completed, failed = result
        self.state.status = f'Completed {completed} files; {len(failed)} failed.'
        if failed:
            Warning('\n'.join(failed), title='Files not converted')

    def apply_contents(self, event=None):
        paths = ops.content_candidates(sorted(self.checked), self.state.text_only)
        if not paths:
            self.state.status = 'No matching regular files are selected.'
            return
        backup, config = self.state.backup, self.config()
        if not Confirm(f'Convert the contents of {len(paths)} files? ' +
                          ('Backups will be kept.' if backup else 'Backups are disabled.'), title='Convert file contents'):
            return
        def action():
            with Bsdconvs(*config) as converter:
                def convert(filename):
                    converter.score_clear()
                    converter.score_train(os.fsencode(filename))
                    return ops.convert_file(filename, converter, backup)
                return self.batch(paths, convert)
        self.submit(action, self.batch_done)

    def tag_options(self):
        return tuple(field for field in metadata.FIELDS if getattr(self.state, 'tag_' + field)), self.state.remove_comment, self.state.recover_latin1

    def preview_tags(self, event=None):
        config, filename, options = self.config(), self.state.focused, self.tag_options()
        def action():
            with Bsdconvs(*config) as converter:
                return metadata.preview(filename, converter, *options)
        def done(result):
            self.tag_preview = result
            self.state.status = f'Previewed tags: {ops.display(filename)}'
        self.submit(action, done)

    def apply_tags(self, event=None):
        paths = [path for path in sorted(self.checked) if os.path.isfile(path) and not os.path.islink(path)
                 and Path(path).suffix.lower() in MEDIA_EXTENSIONS]
        if not paths:
            self.state.status = 'Select media files on the Files tab.'
            return
        config, options = self.config(), self.tag_options()
        save_options = self.state.backup, self.state.id3v23, self.state.remove_id3v1
        if not Confirm(f'Convert media tags in {len(paths)} files? ' +
                          ('Backups will be kept.' if save_options[0] else 'Backups are disabled.'), title='Convert media tags'):
            return
        def action():
            with Bsdconvs(*config) as converter:
                def convert(filename):
                    _, result, before = metadata.preview(filename, converter, *options)
                    metadata.save(filename, result, before, *save_options)
                return self.batch(paths, convert)
        self.submit(action, self.batch_done)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='gbsdconv — GUI for the bsdconv encoding converter')
    parser.add_argument('paths', nargs='*', help='Files or folders to add to the list')
    args = parser.parse_args()
    app = Application(args.paths)
    try:
        app.run()
    finally:
        app.executor.shutdown(wait=True)


if __name__ == '__main__':
    main()
