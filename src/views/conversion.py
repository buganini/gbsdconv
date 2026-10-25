"""ConversionView declarations for the gbsdconv interface."""
from ..common import *

from ..profiles import PROFILES


class ConversionView(PUIView):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.state = app.state

    def content(self):
        _ = self.state.revision
        with HBox():
            Label('Conversion type')
            with ComboBox(text_model=self.state('conversion_type'), disabled=self.state.busy):
                for name in ('Text', 'File Names', 'File Contents', 'Media Tags'):
                    ComboBoxItem(name)
        Divider()
        Label('Profiles · semicolon-separated candidates are scored automatically')
        with HBox():
            with ComboBox(text_model=self.state('profile')).layout(weight=1):
                for name in PROFILES:
                    ComboBoxItem(name)
            Button('Use profile', disabled=self.state.busy).click(self.app.use_profile)
            Button('Append candidate', disabled=self.state.busy).click(self.app.use_profile, True)
        Divider()
        Label('Build a conversion')
        with HBox():
            for label, name in [('Input codec', 'from'), ('Intermediate codec', 'inter'), ('Output codec', 'to')]:
                with VBox().layout(weight=1):
                    Label(label)
                    with ComboBox(editable=True, text_model=self.state(name + '_codec')):
                        if name == 'inter':
                            ComboBoxItem('None', value='')
                        for codec in self.app.codecs[name]:
                            ComboBoxItem(codec)
            Button('Use codecs', disabled=self.state.busy).click(self.app.use_codecs)
        Label('Intermediate codecs may be entered as a colon-separated chain.')
        with HBox():
            Label('Scoring weights: input errors')
            TextField(self.state('factor_ierr')).layout(width=70)
            Label('output errors')
            TextField(self.state('factor_oerr')).layout(width=70)
            Label('score')
            TextField(self.state('factor_score')).layout(width=70)
            Checkbox('Train from file paths', self.state('train'), disabled=self.state.busy).click(self.app.invalidate)
        Divider()
        Label('Repair helpers')
        with HBox():
            Label('URL source')
            TextField(self.state('url_source'))
            Label('URL target')
            TextField(self.state('url_target'))
            Button('Use URL decoder', disabled=self.state.busy).click(self.app.url_decoder)
        with HBox():
            Label('Original encoding')
            TextField(self.state('mistreat_source'))
            Label('Misread as')
            TextField(self.state('mistreat_target'))
            Button('Use mojibake repair', disabled=self.state.busy).click(self.app.mojibake)
        Spacer()
