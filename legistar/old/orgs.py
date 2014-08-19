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
