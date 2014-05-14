import collections
from datetime import datetime

from legistar.base.field import FieldAggregator
from legistar.utils.itemgenerator import make_item


class EventFields(FieldAggregator):

    @make_item('when')
    def get_when(self):
        date_key = self.get_label_text('date')
        date = self.field_data[date_key].get_text()
        time_key = self.get_label_text('time')
        time = self.field_data[time_key].get_text()
        datetime_format = self.get_config_value('DATETIME_FORMAT')
        dt = datetime.strptime('%s %s' % (date, time), datetime_format)
        return dt

    @make_item('location')
    def get_location(self):
        key = self.get_label_text('location')
        return self.field_data[key].get_text()

    @make_item('documents', wrapwith=list)
    def gen_documents(self):
        for key in self.get_config_value('PUPA_DOCUMENTS'):
            field = self.field_data.get(key)
            # This column isn't present on this legistar instance.
            if field is None:
                continue
            elif field.is_blank():
                continue
            elif field.get_url() is None:
                continue
            document = dict(
                name=field.get_text(),
                url=field.get_url(),
                mimetype=field.get_mimetype())
            yield document

    @make_item('participants', wrapwith=list)
    def gen_participants(self):
        participant_fields = self.get_config_value('PUPA_PARTICIPANTS')
        for entity_type, keys in participant_fields.items():
            for key in keys:
                cell = self.field_data[key]
                participant = dict(name=cell.text, type=entity_type)
                yield participant

    @make_item('sources', wrapwith=list)
    def gen_sources(self):
        grouped = collections.defaultdict(set)
        for note, url in self.ctx['sources'].items():
            grouped[url].add(note)
        for url, notes in grouped.items():
            yield dict(url=url, note=', '.join(notes))
