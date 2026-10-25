from pathlib import Path
import struct
import tempfile
import unittest
import wave
from unittest.mock import patch

from bsdconvs import Bsdconvs
from src import metadata
from src.operations import signature
from taglib import load


class MetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            load()
        except RuntimeError as error:
            raise unittest.SkipTest(str(error))

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.filename = str(Path(self.directory.name) / 'music.wav')
        with wave.open(self.filename, 'wb') as sound:
            sound.setnchannels(1)
            sound.setsampwidth(2)
            sound.setframerate(8000)
            sound.writeframes(b'\0' * 1600)
        # RIFF INFO is a real fixture read by TagLib, including numeric fields.
        fields = {b'INAM': b'hello', b'IART': b'artist', b'ICMT': b'comment', b'ICRD': b'2026', b'IPRT': b'7'}
        chunks = []
        for key, value in fields.items():
            value += b'\0'
            chunks.append(key + struct.pack('<I', len(value)) + value + (b'\0' if len(value) % 2 else b''))
        info = b'INFO' + b''.join(chunks)
        data = Path(self.filename).read_bytes() + b'LIST' + struct.pack('<I', len(info)) + info
        Path(self.filename).write_bytes(data[:4] + struct.pack('<I', len(data) - 8) + data[8:])

    def test_preview_save_preserves_disabled_and_numeric_fields(self):
        original_bytes = Path(self.filename).read_bytes()
        with Bsdconvs('UTF-8:UPPER:UTF-8') as converter:
            original, result, before = metadata.preview(self.filename, converter, enabled=('title',), recover_latin1=False)
        self.assertEqual(original['title'], b'hello')
        self.assertEqual(original['year'], 2026)
        self.assertEqual(original['track'], 7)
        self.assertEqual(Path(self.filename).read_bytes(), original_bytes)
        metadata.save(self.filename, result, before)
        saved = metadata.read(self.filename)
        self.assertEqual(saved['title'], b'HELLO')
        self.assertEqual(saved['artist'], b'artist')
        self.assertEqual(saved['year'], 2026)
        self.assertEqual(saved['track'], 7)
        self.assertEqual(Path(self.filename + '.bsdconv.bak').read_bytes(), original_bytes)

    def test_failed_tag_save_preserves_original(self):
        original = Path(self.filename).read_bytes()
        result = metadata.read(self.filename)
        with patch.object(metadata, 'media_file', side_effect=OSError('save failed')):
            with self.assertRaises(OSError):
                metadata.save(self.filename, result, signature(self.filename), backup=False)
        self.assertEqual(Path(self.filename).read_bytes(), original)
        self.assertFalse(list(Path(self.directory.name).glob('.gbsdconv-*')))

    def test_stale_tag_preview_rejected(self):
        before = signature(self.filename)
        result = metadata.read(self.filename)
        with open(self.filename, 'ab') as file:
            file.write(b'changed')
        with self.assertRaises(ValueError):
            metadata.save(self.filename, result, before)


if __name__ == '__main__':
    unittest.main()
