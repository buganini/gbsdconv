import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsdconvs import Bsdconvs
from src import operations as ops


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def file(self, name='sample.txt', data=b'hello'):
        path = self.root / name
        path.write_bytes(data)
        return str(path)

    def test_candidate_selection_and_training(self):
        with Bsdconvs('UTF-8:SCORE:UTF-8;BIG5:SCORE:UTF-8', train=True) as converter:
            converter.score_train('中文')
            self.assertEqual(converter.conv('中文'.encode('big5')), '中文'.encode())
            self.assertEqual(converter.conv_list(['中文'.encode('big5'), b'hello']), ['中文'.encode(), b'hello'])
            converter.score_clear()

    def test_invalid_configuration(self):
        for spec in ('', 'NO-SUCH-CODEC:UTF-8'):
            with self.assertRaises(ValueError):
                Bsdconvs(spec)
        with self.assertRaises(ValueError):
            Bsdconvs('UTF-8:UTF-8', factors=(float('nan'), 0, 1))

    def test_streaming_multibyte_boundary_and_backup(self):
        original = b'a' * 65535 + '中文'.encode() * 22000
        filename = self.file(data=original)
        with Bsdconvs('UTF-8:UTF-16LE') as converter:
            ops.convert_file(filename, converter)
        self.assertEqual(Path(filename).read_bytes(), original.decode().encode('utf-16-le'))
        self.assertEqual(Path(filename + '.bsdconv.bak').read_bytes(), original)
        self.assertFalse(list(self.root.glob('.gbsdconv-*')))

    def test_invalid_input_keeps_original(self):
        filename = self.file(data=b'abc\xff')
        with Bsdconvs('UTF-8:UTF-8') as converter, self.assertRaises(ValueError):
            ops.convert_file(filename, converter)
        self.assertEqual(Path(filename).read_bytes(), b'abc\xff')
        self.assertFalse(Path(filename + '.bsdconv.bak').exists())

    def test_existing_backup_never_overwritten(self):
        filename = self.file()
        backup = Path(filename + '.bsdconv.bak')
        backup.write_bytes(b'previous')
        with Bsdconvs('UTF-8:UPPER:UTF-8') as converter, self.assertRaises(FileExistsError):
            ops.convert_file(filename, converter)
        self.assertEqual(Path(filename).read_bytes(), b'hello')
        self.assertEqual(backup.read_bytes(), b'previous')
        Path(filename).unlink()
        with self.assertRaises(FileExistsError):
            ops.backup_file(filename)
        self.assertEqual(backup.read_bytes(), b'previous')

    def test_partial_backup_is_removed(self):
        filename = self.file()
        with patch.object(ops.shutil, 'copyfileobj', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                ops.backup_file(filename)
        self.assertFalse(Path(filename + '.bsdconv.bak').exists())

    def test_nested_rename_and_symlink(self):
        folder = self.root / 'lower'
        folder.mkdir()
        (folder / 'name.txt').write_bytes(b'unchanged')
        (folder / 'pointer').symlink_to('name.txt')
        paths = ops.collect_paths([folder], recursive=True)
        with Bsdconvs('UTF-8:UPPER:UTF-8') as converter:
            records = ops.preview_names(paths, converter)
        self.assertFalse(any(row.error for row in records))
        self.assertEqual(ops.apply_names(records), 3)
        self.assertEqual((self.root / 'LOWER' / 'NAME.TXT').read_bytes(), b'unchanged')
        self.assertEqual(os.readlink(self.root / 'LOWER' / 'POINTER'), 'NAME.TXT')
        self.assertEqual((self.root / 'LOWER' / 'POINTER').read_bytes(), b'unchanged')

    def test_rename_conflict_and_stale_preview(self):
        filename = self.file('one.txt')
        self.file('other.txt')
        class SameName:
            def conv(self, value):
                return b'same.txt'
            def counter(self):
                return {}
        records = ops.preview_names([filename, str(self.root / 'other.txt')], SameName())
        self.assertTrue(all(row.error for row in records))
        with self.assertRaises(ValueError):
            ops.apply_names(records)
        with Bsdconvs('UTF-8:UPPER:UTF-8') as converter:
            records = ops.preview_names([filename], converter)
        Path(filename).write_bytes(b'changed after preview')
        with self.assertRaises(ValueError):
            ops.apply_names(records)
        self.assertTrue(Path(filename).exists())

    def test_rename_failure_rolls_back(self):
        filenames = [self.file('one'), self.file('two')]
        with Bsdconvs('UTF-8:UPPER:UTF-8') as converter:
            records = ops.preview_names(filenames, converter)
        original = os.rename
        def fail_second(source, destination):
            if source == filenames[1]:
                raise OSError('rename failed')
            return original(source, destination)
        with patch.object(ops.os, 'rename', side_effect=fail_second), self.assertRaises(OSError):
            ops.apply_names(records)
        self.assertTrue(all(Path(filename).exists() for filename in filenames))

    def test_symlinks_not_followed_for_content_or_recursion(self):
        filename = self.file()
        link = self.root / 'link.txt'
        link.symlink_to(filename)
        self.assertEqual(ops.content_candidates([str(link), filename]), [filename])
        with Bsdconvs('UTF-8:UTF-8') as converter, self.assertRaises(ValueError):
            ops.convert_file(str(link), converter)
        self.assertTrue(ops.matches(str(link), r'\l'))
        self.assertFalse(ops.matches(str(link), r'\f'))


if __name__ == '__main__':
    unittest.main()
