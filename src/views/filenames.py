"""FilenamesView declarations for the gbsdconv interface."""
from ..common import *

from .. import operations as ops


class FilenamesView(PUIView):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.state = app.state

    def content(self):
        _ = self.state.revision
        with HBox():
            Button('Preview selected names', disabled=self.state.busy).click(self.app.preview_names)
            Button('Apply preview', disabled=self.state.busy or not self.app.names or self.app.names_key != self.app.preview_key()
                      or any(row.error for row in self.app.names)).click(self.app.apply_names)
            Label('Folders are renamed after their children. Selected symlink targets follow renamed items.')
        with Table(columnHeader=['Current path', 'New path / link target', 'Status']).layout(weight=1):
            for row in self.app.names:
                with TableNode().id(row.source):
                    TableNode(ops.display(row.source))
                    suffix = ' → ' + row.target if row.target else ''
                    TableNode(ops.display(row.destination + suffix))
                    TableNode(row.error or ('Ready' if row.changed else 'Unchanged'))
        if not self.app.names:
            Label('Select items on the Select Files tab, then preview their converted names here.')
