class DateGetter:
    '''Parse a date using the datetime format string defined in
    the current jxn's config.
    '''
    def _get_date(self, label_text):
        fmt = self.get_config_value('datetime_format')
        text = self.get_field_text(label_text)
        if text is not None:
            dt = datetime.strptime(text, fmt)
            dt = self.cfg.datetime_add_tz(dt)
            return dt


class BillsFields(FieldAggregator, DateGetter):

    text_fields = (
        'law_number', 'type', 'status',
        'name', 'version', 'sponsor_office')

    def get_intro_data(self):
        return self._get_date('intro_date')

    def get_file_created(self):
        return self._get_date('file_created')

    def gen_sources(self):
        grouped = collections.defaultdict(set)
        for note, url in self.chainmap['sources'].items():
            grouped[url].add(note)
        for url, notes in grouped.items():
            yield dict(url=url, note=', '.join(sorted(notes)))


class BillsSearchForm(FirefoxForm):
    '''Model the legistar "Legislation" search form.
    '''
    sources_note = 'bill search table'

    def is_advanced_search(self):
        switch_el_id = self.cfg.BILL_SEARCH_SWITCH_EL_ID
        switch_el = self.firefox.find_element_by_id(switch_el_id)
        switch_el_text = switch_el.text.lower()
        if self.cfg.BILL_SEARCH_SWITCH_SIMPLE in switch_el_text:
            return True
        return False

    def switch_to_advanced_search(self):
        switch_el_id = self.cfg.BILL_SEARCH_SWITCH_EL_ID
        switch_el = self.firefox.find_element_by_id(switch_el_id)
        switch_el.click()

    def fill_out_form(self):
        if not self.is_advanced_search():
            self.switch_to_advanced_search()

        max_results_id = "ctl00_ContentPlaceHolder1_lstMax"
        self.set_dropdown(max_results_id, 'All')

        years_id = "ctl00_ContentPlaceHolder1_lstYearsAdvanced"
        self.set_dropdown(years_id, 'This Year')


class BillsDetailView(DetailView, BillsFields):
    sources_note = 'bill detail'
    text_fields = ('version', 'name')

    def get_file_number(self):
        return self.get_field_text('file_number')

    def get_title(self):
        title = self.get_field_text('title')
        # If no title, re-use type (i.e., "Resolution")
        if not title:
            title = self.get_field_text('type')
        return title

    def get_agenda_date(self):
        return self._get_date('agenda')

    def get_enactment_date(self):
        return self._get_date('enactment_date')

    def get_final_action(self):
        return self._get_date('final_action')

    def gen_sponsors(self):
        sponsors = self.get_field_text('sponsors')
        for name in re.split(r',\s+', sponsors):
            name = name.strip()
            if name:
                yield dict(name=name)

    def gen_documents(self):
        for el in self.xpath('attachments', './/a'):
            data = ElementAccessor(el)
            url = data.get_url()

            media_type = 'application/pdf'

            yield dict(
                name=data.get_text(),
                links=[dict(
                    url=data.get_url(),
                    media_type=media_type)])

    def gen_action(self):
        yield from self.Form(self)

    def gen_identifiers(self):
        '''Yield out the internal legistar bill id and guid found
        in the detail page url.
        '''
        detail_url = self.chainmap['sources'][self.sources_note]
        url = urlparse(detail_url)
        for idtype, ident in parse_qsl(url.query):
            if idtype == 'options' or ident == 'Advanced':
                continue
            yield dict(
                scheme="legistar_" + idtype.lower(),
                identifier=ident)

    def get_legislative_session(self):
        dates = []
        labels = ('agenda', 'created')
        for label in labels:
            labeltext = self.get_label_text(label, skipitem=False)
            if labeltext not in self.field_data.keys():
                continue
            if not self.field_data[labeltext]:
                continue
            data = self.field_data[labeltext][0]
            fmt = self.get_config_value('datetime_format')
            text = data.get_text()
            if text is not None:
                dt = datetime.strptime(text, fmt)
                dt = self.cfg.datetime_add_tz(dt)
                dates.append(dt)

        _, actions = self.gen_action()
        for action in actions:
            dates.append(action['date'])

        if dates:
            return str(max(dates).year)

        self.critical('Need session date.')


class BillsDetailTableRow(TableRow, FieldAggregator, DateGetter):
    sources_node = 'bill action table'
    disable_aggregator_funcs = True
    text_fields = (
        ('action_by', 'organization'),
        ('action', 'text'),
        'version',
        'result',
        'journal_page',
        )

    def get_detail_viewtype(self):
        return BillsDetailAction

    def get_detail_url(self):
        return self.get_media_url('action_details')

    def get_date(self):
        return self._get_date('date')

    def _get_media(self, label):
        '''Given a field label, get it's url (if any) and send a head
        request to determine the content_type. Return a dict.
        '''
        data = self.get_field_data(label)
        url = data.get_url()
        if url is None:
            raise self.SkipItem()
        self.info('Sending HEAD request for %r' % url)
        media_type = 'application/pdf'
        return dict(
            name=data.get_text(),
            links=[dict(
                url=data.get_url(),
                media_type=media_type)])

    @make_item('media', wrapwith=list)
    def gen_media(self):
        for label in self.get_config_value('pupa_media'):
            try:
                yield self._get_media(label)
            except self.SkipItem:
                continue


class BillsDetailAction(DetailView, ActionBase):
    sources_note = 'bill action detail'

    text_fields = (
        'file_number', 'type', 'title', 'mover', 'seconder',
        'result', 'agenda_note', 'minutes_note', 'action',
        'action_text')

    @make_item('votes', wrapwith=list)
    def gen_votes(self):
        table_path = self.get_config_value('table_class')
        Table = resolve_name(table_path)
        yield from self.make_child(Table, self)

    @make_item('sources', wrapwith=list)
    def gen_sources(self):
        yield dict(url=self.url, note='action detail')


class BillsDetailActionTable(Table, ActionBase):
    sources_note = 'bill action detail table'

    def get_table_cell_type(self):
        path = self.get_config_value('tablecell_class')
        return resolve_name(path)

    def get_table_row_type(self):
        path = self.get_config_value('tablerow_class')
        return resolve_name(path)


class BillsDetailActionTableRow(TableRow, ActionBase):
    sources_node = 'bill action detail table'
    text_fields = ('person', 'vote')


def _get_date(date):
    if isinstance(date, datetime.datetime):
        return date.strftime('%Y-%m-%d')
    else:
        return date

class ActionAdapter(Adapter):
    aliases = [('text', 'description')]
    extras_keys = ['version', 'media', 'result']
    drop_keys = ['sources', 'journal_page']

    #make_item('date')
    def get_date(self):
        return _get_date(self.data['date'])


class VoteAdapter(Adapter):
    pupa_model = pupa.scrape.Vote
    text_fields = ['organization']
    aliases = [
        ('text', 'motion_text'),
        ]
    drop_keys = ['date']
    extras_keys = ['version', 'media', 'journal_page']

    #make_item('identifier')
    def get_identifier(self):
        '''The internal legistar bill id and guid found
        in the detail page url.
        '''
        i = self.data.pop('i')
        for source in self.data['sources']:
            if not 'historydetail' in source['url'].lower():
                continue
            url = urlparse(source['url'])
            ids = {}
            for idtype, ident in parse_qsl(url.query):
                if idtype == 'options':
                    continue
                ids[idtype.lower()] = ident
            return ids['guid']

        # The vote has no "action details" page, thus no identifier.
        # Fudge one based on the bill's guid.
        for source in self.bill_adapter.data['identifiers']:
            if source['scheme'] != 'legistar_guid':
                continue
            return '%s-vote%d' % (source['identifier'], i)


    #make_item('start_date')
    def get_date(self):
        return _get_date(self.data.get('date'))

    #make_item('result')
    def get_result(self):
        if not self.data['result']:
            raise self.SkipItem()
        result = self.get_vote_result(self.data['result'])
        return result

    #make_item('votes', wrapwith=list)
    def gen_votes(self):
        for data in self.data['votes']:
            if not data:
                continue
            res = {}
            res['option'] = self.get_vote_option(data['vote'])
            res['note'] = data['vote']
            res['voter'] = data['person']
            yield res

    def get_instance(self, **extra_instance_data):
        data = self.get_instance_data()
        data.update(extra_instance_data)

        motion_text = data['motion_text']
        data['classification'] = self.classify_motion_text(motion_text)

        # Drop the org if necessary. When org is the top-level org, omit.
        if self.should_drop_organization(data):
            data.pop('organization', None)

        vote_data_list = data.pop('votes')
        extras = data.pop('extras')
        sources = data.pop('sources')

        data.pop('i', None)
        vote = self.pupa_model(**data)

        counts = collections.Counter()
        for vote_data in vote_data_list:
            counts[vote_data['option']] += 1
            vote.vote(**vote_data)

        for option, value in counts.items():
            vote.set_count(option, value)

        for source in sources:
            vote.add_source(**source)

        vote.extras.update(extras)

        # Skip no-result "votes"
        # https://sfgov.legistar.com/LegislationDetail.aspx?ID=1866659&GUID=A23A12AB-C833-4235-81A1-02AD7B8E7CF0&Options=Advanced&Search
        if vote.result is None:
            return

        return vote

    # ------------------------------------------------------------------------
    # Overridables
    # ------------------------------------------------------------------------
    def get_vote_result(self, result):
        '''Noramalizes the vote result value using the default values on
        Config base, possibly overridded by jxn.BILL_VOTE_RESULT_MAP.
        '''
        result = result.replace('-', ' ').lower()
        result = self.cfg._BILL_VOTE_RESULT_MAP[result]
        return result

    def get_vote_option(self, option_text):
        '''Noramalizes the vote option value using the default values on
        Config base, possibly overridded by jxn.BILL_VOTE_OPTION_MAP.
        '''
        option_text = option_text.replace('-', ' ').lower()
        return self.cfg._BILL_VOTE_OPTION_MAP[option_text]

    def should_drop_organization(self, data):
        '''If this function returns True, the org is dropped from the vote obj.

        XXX: Right now, always drops the org.
        '''
        return True

    def classify_motion_text(self, motion_text):
        '''Jurisdiction configs can override this to determine how
        vote motions will be classified.
        '''
        return []


class BillsAdapter(Adapter):
    pupa_model = pupa.scrape.Bill
    aliases = [
        ('file_number', 'identifier'),
        ]
    extras_keys = [
        'law_number', 'status']

    #make_item('classification')
    def get_classn(self):
        return self.get_bill_classification(self.data.pop('type'))

    #make_item('actions', wrapwith=list)
    def gen_actions(self):
        for data in self.data.get('actions'):
            data = dict(data)
            data.pop('votes')
            action = self.make_child(ActionAdapter, data).get_instance_data()
            if action['description'] is None:
                action['description'] = ''
            yield action

    #make_item('sponsorships')
    def get_sponsorships(self):
        return self.data.get('sponsors', [])

    #make_item('votes', wrapwith=list)
    def gen_votes(self):
        for i, data in enumerate(self.data.get('actions')):
            data['i'] = i
            converter = self.make_child(VoteAdapter, data)
            converter.bill_adapter = self
            more_data = dict(
                legislative_session=self.data['legislative_session'])
            vote = converter.get_instance(**more_data)
            if vote is not None and vote.votes:
                yield vote

    #make_item('subject')
    def _gen_subjects(self, wrapwith=list):
        yield from self.gen_subjects()

    def get_instance(self):
        '''Build a pupa instance from the data.
        '''
        data = self.get_instance_data()
        data_copy = dict(data)

        # Allow jxns to define what bills get dropped.
        if self.should_drop_bill(data_copy):
            return

        bill = pupa.scrape.Bill(
            identifier=data['identifier'],
            legislative_session=data['legislative_session'],
            classification=data.get('classification', []),
            title=data['title'],
            )

        for action in data.pop('actions'):
            action.pop('extras')
            self.drop_action_organization(action)
            bill.add_action(**action)

        for sponsorship in data.pop('sponsorships'):
            if not self.should_drop_sponsor(sponsorship):
                kwargs = dict(
                    classification=self.get_sponsor_classification(sponsorship),
                    entity_type=self.get_sponsor_entity_type(sponsorship),
                    primary=self.get_sponsor_primary(sponsorship))
                kwargs.update(sponsorship)
                bill.add_sponsorship(**kwargs)

        for source in data.pop('sources'):
            bill.add_source(**source)

        bill.extras.update(data.pop('extras'))

        for identifier in data.pop('identifiers'):
            bill.add_identifier(**identifier)

        if bill.title is None:
            bill.title = ''

        yield bill

        for vote in data.pop('votes'):
            vote.set_bill(bill)
            self.vote_cache[vote.identifier] = vote
            yield vote

    @CachedAttr
    def vote_cache(self):
        '''So we don't dupe any votes. Maps identifier to vote obj.
        '''
        return {}

    # ------------------------------------------------------------------------
    # Overridables: sponsorships
    # ------------------------------------------------------------------------
    def should_drop_sponsor(self, data):
        '''If this function retruns True, the sponsor is dropped.
        '''
        return False

    def get_sponsor_classification(self, data):
        '''Return the sponsor's pupa classification. Legistar generally
        doesn't provide any info like this, so we just return "".
        '''
        return 'sponsor'

    def get_sponsor_entity_type(self, data):
        '''Return the sponsor's pupa entity type.
        '''
        return 'person'

    def get_sponsor_primary(self, data):
        '''Return whether the sponsor is primary. Legistar generally doesn't
        provide this.
        '''
        return False

    # ------------------------------------------------------------------------
    # Overridables: actions
    # ------------------------------------------------------------------------
    def drop_action_organization(self, data):
        '''
        XXX: This temporarily drops the action['organization'] from all
        actions. See pupa issue #105 https://github.com/opencivicdata/pupa/issues/105/

        When the organization is the top-level org, it doesn't get set
        on the action.
        '''
        data.pop('organization', None)

    # ------------------------------------------------------------------------
    # Overridables: miscellaneous
    # ------------------------------------------------------------------------
    def get_bill_classification(self, billtype):
        '''Convert the legistar bill `type` column into
        a pupa classification array.
        '''
        # Try to get the classn from the subtype.
        classn = getattr(self, '_BILL_CLASSIFICATIONS', {})
        classn = dict(classn).get(billtype)
        if classn is not None:
            return [classn]

        # Bah, no matches--try to guess it.
        type_lower = billtype.lower()
        for classn in dict(ocd_common.BILL_CLASSIFICATION_CHOICES):
            if classn in type_lower:
                return [classn]

        # None found; return emtpy array.
        return []
