from datetime import datetime

from legistar.base.detailview import DetailView


class DetailView(DetailView):
    FormClass = 'legistar.events.detail.form.Form'

    def get_when(self):
        date = self.field_data[self.cfg.EVT_DETAIL_TEXT_DATE].text
        time = self.field_data[self.cfg.EVT_DETAIL_TEXT_TIME].text
        dt = datetime.strptime(
            '%s %s' % (date, time), self.cfg.EVT_DETAIL_DATETIME_FORMAT)
        return dt

    def get_location(self):
        return self.field_data[self.cfg.EVT_DETAIL_TEXT_LOCATION].text

    def asdict(self):
        data = {}
        data['when'] = self.get_when()
        data['location'] = self.get_location()

        # Documents
        documents = data['documents'] = []
        for key in self.cfg.EVT_DETAIL_PUPA_DOCUMENTS:
            field = self.field_data.get(key)
            # This column isn't present on this legistar instance.
            if field is None:
                continue
            if field.is_blank():
                continue
            document = dict(
                name=field.text,
                url=field.url,
                mimetype=field.mimetype)
            documents.append(document)

        # Participants
        participants = data['participants'] = []
        for entity_type, keys in self.cfg.EVT_TABLE_PUPA_PARTICIPANTS.items():
            for key in keys:
                cell = self.field_data[key]
                participant = dict(name=cell.text, type=entity_type)
                participants.append(participant)

        sources = data['sources'] = []
        # sources.append(dict(url=self.form_url))

        form = self.FormClass(self.cfg, doc=self.doc)
        for x in form:
            import pdb; pdb.set_trace()
        # sources.append(dict(url=self.get_detail_url()))
        # sources.append(dict(url=self.get_ical_url()))

        return data