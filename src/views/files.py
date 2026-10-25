"""FilesView declarations for the gbsdconv interface."""
from ..common import *

from .. import operations as ops


class FilesView(PUIView):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.state = app.state

    def content(self):
        _ = self.state.revision
        with HBox():
            Button('Add files…', disabled=self.state.busy).click(self.app.add_files)
            Button('Add folder…', disabled=self.state.busy).click(self.app.add_folder)
            Checkbox('Include subfolders', self.state('recursive'), disabled=self.state.busy)
            Spacer()
            Button('Remove selected', disabled=self.state.busy).click(self.app.remove_selected)
            Button('Clear list', disabled=self.state.busy).click(self.app.clear_files)
        with HBox():
            with ComboBox(text_model=self.state('filter_profile'), disabled=self.state.busy).change(self.app.set_filter):
                for name in ('All', 'Files', 'Folders', 'Links', 'Text files', 'Media files'):
                    ComboBoxItem(name)
            TextField(self.state('filter'), self.state('filter'), placeholder='*.txt;*.srt or \\a, \\f, \\d, \\l').layout(weight=1)
            Button('Select matching', disabled=self.state.busy).click(self.app.filter_items, True)
            Button('Deselect matching', disabled=self.state.busy).click(self.app.filter_items, False)
        with HBox():
            Button('Select all', disabled=self.state.busy).click(self.app.select_all, True)
            Button('Select none', disabled=self.state.busy).click(self.app.select_all, False)
            Button('Invert selection', disabled=self.state.busy).click(self.app.invert)
            Label('Click the first column to toggle an item; click its path to focus it.')
        with Table(columnHeader=['Selected', 'Kind', 'Path']).layout(weight=1).ref('gbsdconv.files'):
            for path in self.app.paths:
                with TableNode().id(path):
                    TableNode('✓' if path in self.app.checked else '').click(self.app.toggle, path)
                    TableNode(ops.kind(path)).click(self.app.focus, path)
                    TableNode(ops.display(path)).click(self.app.focus, path)
        if not self.app.paths:
            Label('Add files or a folder to preview filenames, contents and media tags.')
