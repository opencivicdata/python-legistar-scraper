from .base import LegistarScraper

class LegistarPersonScraper(LegistarScraper):
    MEMBERLIST = None

    def councilMembers(self, follow_links=True) :
        for page in self.pages(self.MEMBERLIST) :
            table = page.xpath(
                "//table[@id='ctl00_ContentPlaceHolder1_gridPeople_ctl00']")[0]

            for councilman, headers, row in self.parseDataTable(table):
                if follow_links and type(councilman['Person Name']) == dict:

                    detail_url = councilman['Person Name']['url']
                    councilman_details = self.lxmlize(detail_url)
                    detail_div = councilman_details.xpath(".//div[@id='ctl00_ContentPlaceHolder1_pageDetails']")[0]

                    councilman.update(self.parseDetails(detail_div))

                    img = councilman_details.xpath(
                        "//img[@id='ctl00_ContentPlaceHolder1_imgPhoto']")
                    if img :
                        councilman['Photo'] = img[0].get('src')

                    committee_table = councilman_details.xpath(
                        "//table[@id='ctl00_ContentPlaceHolder1_gridDepartments_ctl00']")[0]
                    committees = self.parseDataTable(committee_table)

                    yield councilman, committees

                else :
                    yield councilman
