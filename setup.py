from pathlib import Path
import os
import subprocess
import sys
from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext


class BridgeBuild(build_ext):
    def get_export_symbols(self, ext):
        # This library is loaded through ctypes, not Python's module importer.
        return []


prefix = os.environ.get('TAGLIB_PREFIX')
if not prefix and sys.platform == 'darwin':
    try:
        prefix = subprocess.check_output(['brew', '--prefix', 'taglib'], text=True,
                                         stderr=subprocess.DEVNULL, timeout=10).strip()
    except (OSError, subprocess.SubprocessError):
        prefix = '/opt/homebrew/opt/taglib' if Path('/opt/homebrew').exists() else '/usr/local'
prefix = prefix or '/usr/local'
setup(cmdclass={'build_ext': BridgeBuild}, ext_modules=[Extension(
    'src._taglib', ['taglib/tag_c.cpp'],
    include_dirs=[str(Path(prefix) / 'include' / 'taglib'), '/usr/include/taglib'],
    library_dirs=[str(Path(prefix) / 'lib')], libraries=['tag'],
    define_macros=[('MAKE_TAGLIB_C_LIB', '1')],
    language='c++', extra_compile_args=['/std:c++17' if sys.platform == 'win32' else '-std=c++17'],
    optional=True,
)])
