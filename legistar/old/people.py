class MembershipAdapter(Adapter):
    '''Convert a legistar scraper's membership into a pupa-compliant membership.  '''
    pupa_model = pupa.scrape.Membership
    extras_keys = ['appointed_by']

    def stringify_date(self, dt):
        '''Given a datetime string, stringify it to a date,
        assuming there is no time portion associated with the date.
        Complain if there is.
        '''
        if not dt:
            raise self.SkipItem()
        else:
            return dt.strftime('%Y-%m-%d')

    #make_item('start_date')
    def get_start_date(self):
        return self.stringify_date(self.data.get('start_date'))

    #make_item('end_date')
    def get_end_date(self):
        return self.stringify_date(self.data.get('end_date'))

    #make_item('organization_id')
    def get_org_id(self):
        return self.data['organization_id']

    #make_item('role')
    def get_org_id(self):
        '''Role defaults to empty string.
        '''
        return self.data['role'] or ''

    def get_instance(self, **extra_instance_data):
        # Get instance data.
        instance_data = self.get_instance_data()
        instance_data.update(extra_instance_data)
        extras = instance_data.pop('extras')

        # Create the instance.
        instance = self.pupa_model(**instance_data)
        instance.extras.update(extras)

        return instance


class MembershipConverter(Converter):
    adapter = MembershipAdapter

    def __iter__(self):
        yield from self.create_memberships()

    def get_legislature(self):
        '''Gets previously scrape legislature org.
        '''
        return self.config.org_cache[self.cfg.TOPLEVEL_ORG_MEMBERSHIP_NAME]

    def get_org(self, org_name):
        '''Gets or creates the org with name equal to
        kwargs['name']. Caches the result.
        '''
        created = False
        orgs = self.config.org_cache

        # Get the org.
        org = orgs.get(org_name)

        if org is not None:
            # Cache hit.
            return created, org

        # Create the org.
        classification = self.cfg.get_org_classification(org_name)
        org = pupa.scrape.Organization(
            name=org_name, classification=classification)
        for source in self.person.sources:
            org.add_source(**source)
        created = True

        # Cache it.
        orgs[org_name] = org

        if org is not None:
            # Cache hit.
            return created, org

        # Add a source to the org.
        for source in self.person.sources:
            if 'detail' in source['note']:
                org.add_source(**source)

        return created, org

    def create_membership(self, data):
        '''Retrieves the matching committee and adds this person
        as a member of the committee.
        '''
        if 'person_id' not in data:
            data['person_id'] = self.person._id

        # Also drop memberships in dropped orgs.
        if hasattr(self.cfg, 'should_drop_organization'):
            if 'org' in data:
                if self.cfg.should_drop_organization(dict(name=data['org'])):
                    return

        # Get the committee.
        if 'organization_id' not in data:
            org_name = data.pop('org')
            created, org = self.get_org(org_name)
            if created:
                yield org

            # Add the person and org ids.
            data['organization_id'] = org._id

        # Convert the membership to pupa object.
        adapter = self.make_child(self.adapter, data)
        membership = adapter.get_instance()

        yield membership
