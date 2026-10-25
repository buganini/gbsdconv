"""TextView declarations for the gbsdconv interface."""
from ..common import *



class TextView(PUIView):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.state = app.state

    def content(self):
        _ = self.state.revision
        with HBox():
            Button('Convert text', disabled=self.state.busy).click(self.app.convert_text)
            Button('Copy result', disabled=not self.app.has_text_result or self.state.busy).click(self.app.copy_text)
            Button('Save result…', disabled=not self.app.has_text_result or self.state.busy).click(self.app.save_text)
            Spacer()
            Label('Preview encoding')
            TextField(self.state('preview_encoding'), self.state('preview_encoding')).layout(width=140)
        with Splitter().layout(weight=1):
            with VBox():
                Label('Input · UTF-8 text')
                TextEdit(self.state('input_text'), self.state('input_text'), placeholder='Paste text here…').layout(weight=1).ref('gbsdconv.text.input')
            with VBox():
                Label('Converted result')
                TextEdit(self.state('output_text'), readonly=True).layout(weight=1).ref('gbsdconv.text.output')
        Label(self.state.text_info)
        Label('The preview uses the encoding above. Save result writes the exact converted bytes.')
