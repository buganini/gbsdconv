"""ContentsView declarations for the gbsdconv interface."""
from ..common import *

from .shared import FilePicker


class ContentsView(PUIView):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.state = app.state

    def content(self):
        _ = self.state.revision
        FilePicker(self.app)
        with HBox():
            Button('Preview file', disabled=self.state.busy or not self.state.focused).click(self.app.preview_contents)
            Checkbox('Text files only', self.state('text_only'), disabled=self.state.busy)
            Checkbox('Keep .bsdconv.bak backups', self.state('backup'), disabled=self.state.busy)
            Spacer()
            Button('Convert selected files…', disabled=self.state.busy or not self.app.checked).click(self.app.apply_contents)
        with Splitter().layout(weight=1):
            with VBox():
                Label('Original · UTF-8 preview')
                TextEdit(self.state('content_before'), readonly=True).layout(weight=1)
            with VBox():
                Label('Converted · UTF-8 preview')
                TextEdit(self.state('content_after'), readonly=True).layout(weight=1)
        Label(self.state.content_info or 'Preview reads at most 1 MiB. Conversion processes the complete file.')
