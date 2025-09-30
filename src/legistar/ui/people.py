from .base import LegistarScraper


class LegistarPersonScraper(LegistarScraper):
    MEMBERLIST = None
    ALL_MEMBERS = None

    def council_members(self, extra_args=None, follow_links=True):
        payload = {}
        if extra_args:
            payload.update(extra_args)
            page = self.lxmlize(self.MEMBERLIST, payload)
            payload.update(self.session_secrets(page))

        if self.ALL_MEMBERS:
            payload["__EVENTTARGET"] = "ctl00$ContentPlaceHolder1$menuPeople"
            payload["__EVENTARGUMENT"] = self.ALL_MEMBERS

        for page in self.pages(self.MEMBERLIST, payload):
            table = page.xpath(
                "//table[@id='ctl00_ContentPlaceHolder1_gridPeople_ctl00']"
            )[0]

            for councilman, headers, row in self.parse_data_table(table):
                if follow_links and type(councilman["Person Name"]) == dict:

                    detail_url = councilman["Person Name"]["url"]
                    councilman_details = self.lxmlize(detail_url)
                    detail_div = councilman_details.xpath(
                        ".//div[@id='ctl00_ContentPlaceHolder1_pageDetails']"
                    )[0]

                    councilman.update(self.parse_details(detail_div))

                    img = councilman_details.xpath(
                        "//img[@id='ctl00_ContentPlaceHolder1_imgPhoto']"
                    )
                    if img:
                        councilman["Photo"] = img[0].get("src")

                    committee_table = councilman_details.xpath(
                        "//table[@id='ctl00_ContentPlaceHolder1_gridDepartments_ctl00']"
                    )[0]
                    committees = self.parse_data_table(committee_table)

                    yield councilman, committees

                else:
                    yield councilman
