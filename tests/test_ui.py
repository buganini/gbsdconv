import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from PySide6 import QtCore, QtTest, QtWidgets
from src.app import Application


class UITests(unittest.TestCase):
    def test_native_controls_and_async_operations(self):
        app = Application()
        app.sync()
        self.addCleanup(app.executor.shutdown)
        self.addCleanup(lambda: app.window.ui.close())

        def settle():
            deadline = time.monotonic() + 10
            while True:
                app.ui.processEvents()
                QtTest.QTest.qWait(10)
                if not app.state.busy:
                    app.ui.processEvents()
                    break
                self.assertLess(time.monotonic(), deadline, 'Background operation timed out')

        def click(label):
            settle()
            buttons = [button for button in app.window.ui.findChildren(QtWidgets.QPushButton) if button.text() == label]
            self.assertEqual(len(buttons), 1)
            self.assertTrue(buttons[0].isEnabled(), label)
            QtTest.QTest.mouseClick(buttons[0], QtCore.Qt.MouseButton.LeftButton)
            settle()

        settle()
        tabs = app.window.ui.findChild(QtWidgets.QTabWidget)

        def tab_labels():
            return [tabs.tabText(index) for index in range(tabs.count())]

        def select_tab(label):
            tabs.setCurrentIndex(tab_labels().index(label))
            settle()
            self.assertEqual(tabs.tabText(tabs.currentIndex()), label)

        def select_type(value, operation):
            select_tab('Setup')
            radios = app.window.ui.findChildren(QtWidgets.QRadioButton)
            self.assertEqual([radio.text() for radio in radios],
                             ['Text', 'File Names', 'File Contents', 'Media Tags'])
            selector = next(radio for radio in radios if radio.text() == value)
            self.assertTrue(selector.isEnabled())
            QtTest.QTest.mouseClick(selector, QtCore.Qt.MouseButton.LeftButton,
                                   pos=QtCore.QPoint(10, selector.height() // 2))
            settle()
            self.assertEqual([radio.text() for radio in radios if radio.isChecked()], [value])
            self.assertEqual(app.state.conversion_type, value)
            self.assertEqual(tab_labels(), ['Setup', operation] if value == 'Text'
                             else ['Setup', 'Select Files', operation])
            self.assertEqual(tabs.currentIndex(), 0)

        self.assertEqual(app.state.conversion_type, 'Text')
        self.assertEqual([radio.text() for radio in app.window.ui.findChildren(QtWidgets.QRadioButton)
                          if radio.isChecked()], ['Text'])
        self.assertEqual(tab_labels(), ['Setup', 'Text'])
        self.assertEqual(tabs.currentIndex(), 0)
        select_tab('Text')
        expression = next(field for field in app.window.ui.findChildren(QtWidgets.QLineEdit)
                          if field.placeholderText().startswith('UTF-8:UTF-8;'))
        expression.setText('UTF-8:UPPER:UTF-8')
        editor = next(field for field in app.window.ui.findChildren(QtWidgets.QPlainTextEdit)
                      if not field.isReadOnly())
        editor.setPlainText('hello 中文')
        click('Convert text')
        self.assertEqual(app.output_bytes, 'HELLO 中文'.encode())
        self.assertEqual(app.state.output_text, 'HELLO 中文')
        click('Copy result')
        self.assertEqual(app.ui.clipboard().text(), 'HELLO 中文')

        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / 'example.txt'
            filename.write_bytes(b'hello')
            app.add_paths([str(filename)])
            settle()
            self.assertEqual(app.checked, {str(filename)})
            select_type('File Contents', 'File Contents')
            select_tab('Select Files')
            table = next(table for table in app.window.ui.findChildren(QtWidgets.QTableView) if table.isVisible())
            index = table.model().index(0, 0)
            QtTest.QTest.mouseClick(table.viewport(), QtCore.Qt.MouseButton.LeftButton, pos=table.visualRect(index).center())
            settle()
            self.assertEqual(app.checked, set())
            click('Select all')
            self.assertEqual(app.checked, {str(filename)})

            select_tab('File Contents')
            click('Preview file')
            self.assertEqual(app.state.content_after, 'HELLO')
            with patch('src.app.Confirm', return_value=True):
                click('Convert selected files…')
            self.assertEqual(filename.read_bytes(), b'HELLO')
            self.assertEqual(Path(str(filename) + '.bsdconv.bak').read_bytes(), b'hello')

            select_type('File Names', 'File Names')
            select_tab('File Names')
            click('Preview selected names')
            self.assertEqual(len(app.names), 1)
            self.assertFalse(app.names[0].error)
            with patch('src.app.Confirm', return_value=True):
                click('Apply preview')
            self.assertEqual(app.paths, [str(filename.with_name('EXAMPLE.TXT'))])
            self.assertEqual(Path(app.paths[0]).read_bytes(), b'HELLO')

            select_type('Media Tags', 'Media Tags')
            self.assertEqual(app.checked, set(app.paths))
            for index in range(tabs.count()):
                tabs.setCurrentIndex(index)
                settle()
                self.assertEqual(tabs.currentIndex(), index)
            select_tab('Select Files')
            table = next(table for table in app.window.ui.findChildren(QtWidgets.QTableView) if table.isVisible())
            app.clear_files()
            settle()
            self.assertEqual(app.paths, [])
            self.assertEqual(table.model().rowCount(QtCore.QModelIndex()), 0)
            select_type('Text', 'Text')
            select_tab('Text')
            editor = next(field for field in app.window.ui.findChildren(QtWidgets.QPlainTextEdit)
                          if not field.isReadOnly())
            self.assertEqual(editor.toPlainText(), 'hello 中文')
            self.assertEqual(app.state.output_text, 'HELLO 中文')
            self.assertEqual(app.state.expression, 'UTF-8:UPPER:UTF-8')
            click('Convert text')
            self.assertEqual(app.state.output_text, 'HELLO 中文')


if __name__ == '__main__':
    unittest.main()
