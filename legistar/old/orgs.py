class OrgsFields(FieldAggregator):

    def get_name(self):
        return self.get_field_text('name')

    def get_type(self):
        return self.get_field_text('type')

    def get_meeting_location(self):
        return self.get_field_text('meeting_location')

    def get_num_vacancies(self):
        return self.get_field_text('num_vacancies')

    def get_num_members(self):
        return self.get_field_text('num_members')

    def gen_sources(self):
        grouped = collections.defaultdict(set)
        for note, url in self.sources.items():
            grouped[url].add(note)
        for url, notes in grouped.items():
            yield dict(url=url, note=', '.join(sorted(notes)))

    #make_item('identifiers', wrapwith=list)
    def gen_identifiers(self):
        '''Yield out the internal legistar organization id and guid found
        in the detail page url.
        '''
        detail_url = self.get_field_url('name')
        url = urlparse(detail_url)
        for idtype, ident in parse_qsl(url.query):
            yield dict(
                scheme="legistar_" + idtype.lower(),
                identifier=ident)
