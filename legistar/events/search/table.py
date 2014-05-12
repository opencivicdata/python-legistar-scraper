from hercules import CachedAttr

import legistar.events.detail.view
from legistar.base.table import Table, TableRow


class TableRow(TableRow):
    DetailClass = 'legistar.events.detail.view.DetailView'

    def get_name(self):
        return self[self.cfg.EVT_TABLE_TEXT_TOPIC].text

    def get_when(self):
        date = self[self.cfg.EVT_TABLE_TEXT_DATE].text
        time = self[self.cfg.EVT_TABLE_TEXT_TIME].text
        dt = datetime.strptime(
            '%s %s' % (date, time), self.cfg.EVT_TABLE_DATETIME_FORMAT)
        return dt

    def get_end(self):
        end_time = re.search(r'DTEND:([\dT]+)', self.ical_data).group(1)
        dt = datetime.strptime(end_time, r'%Y%m%dT%H%M%S')
        return dt

    def get_location(self):
        return self[self.cfg.EVT_TABLE_TEXT_LOCATION].text

    @CachedAttr
    def ical_data(self):
        print('getting ical data')
        ical_url = self.get_ical_url()
        resp = self.cfg.client.session.get(ical_url)
        return resp.text

    def get_detail_url(self):
        return self[self.cfg.EVT_TABLE_TEXT_DETAILS].url

    def get_ical_url(self):
        return self[self.cfg.EVT_TABLE_TEXT_ICAL].url

    def asdict(self):
        data = {}
        data['name'] = self.get_name()
        data['when'] = self.get_when()
        data['end'] = self.get_end()
        data['location'] = self.get_location()

        # Documents
        documents = data['documents'] = []
        for key in self.cfg.EVT_TABLE_PUPA_DOCUMENTS:
            cell = self.get(key)
            # This column isn't present on this legistar instance.
            if cell is None:
                continue
            if cell.is_blank():
                continue
            document = dict(
                name=cell.text,
                url=cell.url,
                mimetype=cell.mimetype)
            documents.append(document)

        # Participants
        participants = data['participants'] = []
        for entity_type, keys in self.cfg.EVT_TABLE_PUPA_PARTICIPANTS.items():
            for key in keys:
                cell = self[key]
                participant = dict(name=cell.text, type=entity_type)
                participants.append(participant)

        sources = data['sources'] = []
        # sources.append(dict(url=self.form_url))
        sources.append(dict(url=self.get_detail_url()))
        sources.append(dict(url=self.get_ical_url()))

        return data


class Table(Table):
    RowClass = TableRow
