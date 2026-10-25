"""FilePicker declarations for the gbsdconv interface."""
import os

from ..common import *

from .. import operations as ops


class FilePicker(PUIView):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.state = app.state

    def content(self):
        _ = self.state.revision
        with HBox():
            Label('Focused file')
            with ComboBox(text_model=self.state('focused'), disabled=self.state.busy).layout(weight=1):
                ComboBoxItem('Select a file…', value='')
                for path in self.app.paths:
                    if os.path.isfile(path) and not os.path.islink(path):
                        ComboBoxItem(ops.display(path), value=path)
