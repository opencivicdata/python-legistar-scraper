from legistar.base.table import Table, TableRow
from legistar.utils.itemgenerator import make_item


class Table(Table):
    sources_note = 'Event detail table'


class TableRow(TableRow):
    KEY_PREFIX = 'EVT_AGENDA_TABLE'

    # Maps the 'type' field in event detail tables to pupa type.
    typetext_map = {
        'ordinance': 'bill',
        'bill': 'bill',
        'resolution': 'resolution'}

    def _get_type(self):
        typetext = self.get_field_text('type')
        if typetext is not None:
            typetext = typetext.lower()
        return self.typetext_map.get(typetext, 'document')

    @make_item('version')
    def get_version(self):
        return self.get_field_text('version')

    @make_item('agenda_num')
    def get_agenda_num(self):
        return self.get_field_text('agenda_number')

    @make_item('subject')
    def get_subject(self):
        return self.get_field_text('name')

    @make_item('type')
    def get_type(self):
        return self._get_type()

    @make_item('name')
    def get_name(self):
        return self.get_field_text('title')

    @make_item('action')
    def get_action(self):
        return self.get_field_text('action')

    @make_item('result')
    def get_result(self):
        return self.get_field_text('result')

    @make_item('action_details')
    def get_details(self):
        return self.get_field_text('action_details')

    @make_item('video_url')
    def get_video_url(self):
        return self.get_field_url('video')

    @make_item('audio_url')
    def get_audio_url(self):
        return self.get_field_url('audio')

    @make_item('transcript_url')
    def get_transcript_url(self):
        return self.get_field_url('transcript')

    @make_item('file_number')
    def get_file_number(self):
        '''Get the bill id from a table row of related bills on an Event
        detail page.
        '''
        return self.get_field_text('file_number')
