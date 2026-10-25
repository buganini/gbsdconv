"""TagsView declarations for the gbsdconv interface."""
from ..common import *

from .. import metadata
from .. import operations as ops
from .shared import FilePicker


class TagsView(PUIView):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.state = app.state

    def content(self):
        _ = self.state.revision
        FilePicker(self.app)
        with HBox():
            for field in metadata.FIELDS:
                Checkbox(field.title(), self.state('tag_' + field), disabled=self.state.busy)
        with HBox():
            Checkbox('Recover Latin-1 mojibake', self.state('recover_latin1'), disabled=self.state.busy)
            Checkbox('Clear comment', self.state('remove_comment'), disabled=self.state.busy)
            Checkbox('ID3v2.3', self.state('id3v23'), disabled=self.state.busy)
            Checkbox('Remove ID3v1', self.state('remove_id3v1'), disabled=self.state.busy)
            Checkbox('Keep backups', self.state('backup'), disabled=self.state.busy)
        with HBox():
            Button('Preview tags', disabled=self.state.busy or not self.state.focused).click(self.app.preview_tags)
            Button('Convert selected media…', disabled=self.state.busy or not self.app.checked).click(self.app.apply_tags)
            Label('Tag output must be UTF-8. Year and track are preserved.')
        with Table(columnHeader=['Field', 'Original', 'Converted']).layout(weight=1):
            if self.app.tag_preview:
                original, converted, _ = self.app.tag_preview
                for field in (*metadata.FIELDS, 'year', 'track'):
                    with TableNode().id(field):
                        TableNode(field.title())
                        TableNode(ops.display(original[field]))
                        TableNode(ops.display(converted[field]))
        if not self.app.tag_preview:
            Label('Preview the focused file before converting. TagLib is only needed for this page.')
