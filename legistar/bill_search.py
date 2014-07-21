'''Why, why does this hacky module exists, you might ask? I spent days
trying to get legistar to respond to advanced search form queries the
right way. Finally, I decided that reverse engineering this piece garbage
is just not worth my time. So this module replays the requests that
Firefox sends, captured earlier through mitmproxy. The client object
maintains the state of the aspx app, and it just works. Burn the sevel hells,
legistar, you crufty, HTTP-misunderstanding, second-rate, monumental Microsofty
antipattern.
'''
import requests
import lxml.html
import logging
import pprint


logging.basicConfig(level=logging.DEBUG)


class Client:

    def __init__(self):
        self.session = requests.Session()
        self.state = dict.fromkeys((
            '__EVENTVALIDATION',
            '__VIEWSTATE',
            '__EVENTTARGET',
            '__EVENTARGUMENT',
            ), '')
        req = requests.Request(method="GET", url='http://nyc.legistar.com/Legislation.aspx')
        resp = self.session.send(req.prepare())
        # self.write_resp(req, resp)
        self.update_state(resp)

    def hydrate_request(self, data):
        req = requests.Request(**data)
        return req

    def update_state(self, resp):
        '''Get the weird ASPX client state nonsense from the response
        and update the Client's state so it can be sent with future requests.
        '''
        doc = lxml.html.fromstring(resp.text)
        form = dict(doc.forms[0].fields)
        for key in set(self.state.keys()) & set(form.keys()):
            self.state[key] = form.get(key)

    def update_request(self, request):
        if request.method != 'POST':
            return
        update_keys = set(self.state.keys()) & set(request.data.keys())
        update_keys |= set(['__VIEWSTATE', '__EVENTVALIDATION'])
        for key in update_keys:
            if self.state[key]:
                request.data[key] = self.state[key]

    def write_resp(self, req, resp):
        with open('resp.html', 'wb') as f:
            f.write(resp.content)
            _data = dict(req.data)
            _data.pop('__VIEWSTATE', None)
            pprint.pprint(_data)
            import pdb; pdb.set_trace()

    def send(self, req):
        if isinstance(req, dict):
            req = self.hydrate_request(req)
        self.update_request(req)
        resp = self.session.send(req.prepare())
        self.update_state(resp)
        # self.write_resp(req, resp)
        return resp

req1 = {
    'method': 'POST',
    'url': 'http://nyc.legistar.com/Legislation.aspx',

    'cookies': {
        ' Setting-61-ASP.calendar_aspx.gridCalendar.SortExpression': 'MeetingStartDate DESC',
        ' Setting-61-ASP.legislation_aspx.gridMain.SortExpression': 'MatterID DESC',
        ' Setting-61-Calendar Body': 'All',
        ' Setting-61-Calendar Options': 'info|',
        ' Setting-61-Calendar Year': 'This Month',
        ' Setting-61-Legislation Type': 'All',
        ' Setting-61-Legislation Year': 'This Year',
        # ' __atuvc': '13%7C29',
        # ' __utma': '196938163.1626544919.1405688217.1405698268.1405700259.5',
        # ' __utmb': '196938163.2.10.1405700259',
        # ' __utmc': '196938163',
        # ' __utmz': '196938163.1405688217.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)',
        'Setting-61-Legislation Options': 'ID|Text|'
        },

    'data': {
        '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$btnSwitch',
        'ctl00$ContentPlaceHolder1$chkID': 'on',
        'ctl00$ContentPlaceHolder1$chkText': 'on',
        'ctl00$ContentPlaceHolder1$lstTypeBasic': 'All Types',
        'ctl00$ContentPlaceHolder1$lstYears': 'This Year',
        'ctl00_RadScriptManager1_TSM': (
            ';;System.Web.Extensions, Version=4.0.0.0, Culture=neutral, '
            'PublicKeyToken=31bf3856ad364e35:en-US:fa6755fd-da1a-49d3-9eb4-1e473e780ecd:ea597d4b:b25378d2;'
            'Telerik.Web.UI, Version=2014.1.403.45, Culture=neutral, '
            'PublicKeyToken=121fae78165ba3d4:en-US:68d9452f-f268-45b2-8db7-8c3bbf305b8d:16e4e7cd:f76'
            '45509:24ee1bba:e330518b:88144a7a:1e771326:8e6f0d33:ed16cbdc:f46195d3:19620875:874f8ea2:'
            'cda80b3:383e4ce8:2003d0b8:aa288e2d:258f1c72:c128760b:c8618e41:1a73651d:333f8d94:58366029'),
        'ctl00_tabTop_ClientState': '{"selectedIndexes":["1"],"logEntries":[],"scrollState":{}}'
        },

    'headers': {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Content-Length': '37519',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 'Setting-61-Legislation Options=ID|Text|; Setting-61-Legislation Year=This Year; Setting-61-Legislation Type=All; Setting-61-ASP.legislation_aspx.gridMain.SortExpression=MatterID DESC; __utma=196938163.1626544919.1405688217.1405698268.1405700259.5; __utmc=196938163; __utmz=196938163.1405688217.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); __atuvc=13%7C29; Setting-61-Calendar Options=info|; Setting-61-Calendar Year=This Month; Setting-61-Calendar Body=All; Setting-61-ASP.calendar_aspx.gridCalendar.SortExpression=MeetingStartDate DESC; __utmb=196938163.2.10.1405700259',
        'Host': 'nyc.legistar.com',
        'Referer': 'http://nyc.legistar.com/Legislation.aspx',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0'
        },

    }

req2 = {
    'method': 'POST',
    'url': 'http://nyc.legistar.com/Legislation.aspx',

    'cookies': {
        ' Setting-61-ASP.calendar_aspx.gridCalendar.SortExpression': 'MeetingStartDate DESC',
        ' Setting-61-ASP.legislation_aspx.gridMain.SortExpression': 'MatterID DESC',
        ' Setting-61-Calendar Body': 'All',
        ' Setting-61-Calendar Options': 'info|',
        ' Setting-61-Calendar Year': 'This Month',
        ' Setting-61-Legislation Type': 'All',
        ' Setting-61-Legislation Year': 'This Year',
        # ' __atuvc': '14%7C29',
        # ' __utma': '196938163.1626544919.1405688217.1405698268.1405700259.5',
        # ' __utmb': '196938163.3.10.1405700259',
        # ' __utmc': '196938163',
        # ' __utmz': '196938163.1405688217.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)',
        'Setting-61-Legislation Options': 'ID|Text|'
        },

    'data': {
        'ctl00$ContentPlaceHolder1$btnSearch2': 'Search Legislation',
        'ctl00$ContentPlaceHolder1$lstInControlOf': '-Select-',
        'ctl00$ContentPlaceHolder1$lstIndexedUnder': '-Select-',
        'ctl00$ContentPlaceHolder1$lstMax': 'All',
        'ctl00$ContentPlaceHolder1$lstSponsoredBy': '-Select-',
        'ctl00$ContentPlaceHolder1$lstStatus': '-Select-',
        'ctl00$ContentPlaceHolder1$lstType': '-Select-',
        'ctl00$ContentPlaceHolder1$lstYearsAdvanced': 'This Year',
        'ctl00$ContentPlaceHolder1$radFinalAction': '=',
        'ctl00$ContentPlaceHolder1$radOnAgenda': '=',
        'ctl00_ContentPlaceHolder1_lstMax_ClientState': '{"logEntries":[],"value":"1000000","text":"All","enabled":true,"checkedIndices":[],"checkedItemsTextOverflows":false}',
        'ctl00_ContentPlaceHolder1_txtFinalAction1_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,7,18]]',
        'ctl00_ContentPlaceHolder1_txtFinalAction1_calendar_SD': '[]',
        'ctl00_ContentPlaceHolder1_txtFinalAction1_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
        'ctl00_ContentPlaceHolder1_txtFinalAction2_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,7,18]]',
        'ctl00_ContentPlaceHolder1_txtFinalAction2_calendar_SD': '[]',
        'ctl00_ContentPlaceHolder1_txtFinalAction2_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
        'ctl00_ContentPlaceHolder1_txtOnAgenda1_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,7,18]]',
        'ctl00_ContentPlaceHolder1_txtOnAgenda1_calendar_SD': '[]',
        'ctl00_ContentPlaceHolder1_txtOnAgenda1_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
        'ctl00_ContentPlaceHolder1_txtOnAgenda2_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,7,18]]',
        'ctl00_ContentPlaceHolder1_txtOnAgenda2_calendar_SD': '[]',
        'ctl00_ContentPlaceHolder1_txtOnAgenda2_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
        'ctl00_RadScriptManager1_TSM': ';;System.Web.Extensions, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35:en-US:fa6755fd-da1a-49d3-9eb4-1e473e780ecd:ea597d4b:b25378d2;Telerik.Web.UI, Version=2014.1.403.45, Culture=neutral, PublicKeyToken=121fae78165ba3d4:en-US:68d9452f-f268-45b2-8db7-8c3bbf305b8d:16e4e7cd:f7645509:24ee1bba:e330518b:88144a7a:1e771326:8e6f0d33:ed16cbdc:f46195d3:19620875:874f8ea2:cda80b3:383e4ce8:2003d0b8:aa288e2d:258f1c72:8674cba1:7c926187:b7778d6c:c08e9f8a:a51ee93e:59462f1:c128760b:c8618e41:1a73651d:333f8d94:58366029',
        'ctl00_tabTop_ClientState': '{"selectedIndexes":["1"],"logEntries":[],"scrollState":{}}'
        },

    'headers': {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Content-Length': '834864',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 'Setting-61-Legislation Options=ID|Text|; Setting-61-Legislation Year=This Year; Setting-61-Legislation Type=All; Setting-61-ASP.legislation_aspx.gridMain.SortExpression=MatterID DESC; __utma=196938163.1626544919.1405688217.1405698268.1405700259.5; __utmc=196938163; __utmz=196938163.1405688217.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); __atuvc=14%7C29; Setting-61-Calendar Options=info|; Setting-61-Calendar Year=This Month; Setting-61-Calendar Body=All; Setting-61-ASP.calendar_aspx.gridCalendar.SortExpression=MeetingStartDate DESC; __utmb=196938163.3.10.1405700259',
        'Host': 'nyc.legistar.com',
        'Referer': 'http://nyc.legistar.com/Legislation.aspx',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0'
        },
    }


req3 = {
    'method': 'POST',
    'url': 'http://nyc.legistar.com/Legislation.aspx',

    'cookies': {
        ' Setting-61-ASP.calendar_aspx.gridCalendar.SortExpression': 'MeetingStartDate DESC',
        ' Setting-61-ASP.legislation_aspx.gridMain.SortExpression': 'MatterID DESC',
        ' Setting-61-Calendar Body': 'All',
        ' Setting-61-Calendar Options': 'info|',
        ' Setting-61-Calendar Year': 'This Month',
        ' Setting-61-Legislation Type': '',
        ' Setting-61-Legislation Year': 'This Year',
        # ' __atuvc': '15%7C29',
        # ' __utma': '196938163.1626544919.1405688217.1405698268.1405700259.5',
        # ' __utmb': '196938163.4.10.1405700259',
        # ' __utmc': '196938163',
        # ' __utmz': '196938163.1405688217.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none)',
        'Setting-61-Legislation Options': 'ID|Text|'
        },

    'data': {
        '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$gridMain$ctl00$ctl02$ctl00$ctl04',
        'ctl00$ContentPlaceHolder1$lstInControlOf': '-Select-',
        'ctl00$ContentPlaceHolder1$lstIndexedUnder': '-Select-',
        'ctl00$ContentPlaceHolder1$lstMax': 'All',
        'ctl00$ContentPlaceHolder1$lstSponsoredBy': '-Select-',
        'ctl00$ContentPlaceHolder1$lstStatus': '-Select-',
        'ctl00$ContentPlaceHolder1$lstType': '-Select-',
        'ctl00$ContentPlaceHolder1$lstYearsAdvanced': 'This Year',
        'ctl00$ContentPlaceHolder1$radFinalAction': '=',
        'ctl00$ContentPlaceHolder1$radOnAgenda': '=',
        'ctl00_ContentPlaceHolder1_txtFinalAction1_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,7,18]]',
        'ctl00_ContentPlaceHolder1_txtFinalAction1_calendar_SD': '[]',
        'ctl00_ContentPlaceHolder1_txtFinalAction1_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
        'ctl00_ContentPlaceHolder1_txtFinalAction2_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,7,18]]',
        'ctl00_ContentPlaceHolder1_txtFinalAction2_calendar_SD': '[]',
        'ctl00_ContentPlaceHolder1_txtFinalAction2_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
        'ctl00_ContentPlaceHolder1_txtOnAgenda1_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,7,18]]',
        'ctl00_ContentPlaceHolder1_txtOnAgenda1_calendar_SD': '[]',
        'ctl00_ContentPlaceHolder1_txtOnAgenda1_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
        'ctl00_ContentPlaceHolder1_txtOnAgenda2_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,7,18]]',
        'ctl00_ContentPlaceHolder1_txtOnAgenda2_calendar_SD': '[]',
        'ctl00_ContentPlaceHolder1_txtOnAgenda2_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
        'ctl00_RadScriptManager1_TSM': ';;System.Web.Extensions, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35:en-US:fa6755fd-da1a-49d3-9eb4-1e473e780ecd:ea597d4b:b25378d2;Telerik.Web.UI, Version=2014.1.403.45, Culture=neutral, PublicKeyToken=121fae78165ba3d4:en-US:68d9452f-f268-45b2-8db7-8c3bbf305b8d:16e4e7cd:f7645509:24ee1bba:e330518b:88144a7a:1e771326:8e6f0d33:ed16cbdc:f46195d3:19620875:874f8ea2:cda80b3:383e4ce8:2003d0b8:aa288e2d:258f1c72:8674cba1:7c926187:b7778d6c:c08e9f8a:a51ee93e:59462f1:c128760b:c8618e41:1a73651d:333f8d94:58366029',
        'ctl00_tabTop_ClientState': '{"selectedIndexes":["1"],"logEntries":[],"scrollState":{}}'
        },

    'headers': {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Content-Length': '953155',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 'Setting-61-Legislation Options=ID|Text|; Setting-61-Legislation Year=This Year; Setting-61-Legislation Type=; Setting-61-ASP.legislation_aspx.gridMain.SortExpression=MatterID DESC; __utma=196938163.1626544919.1405688217.1405698268.1405700259.5; __utmc=196938163; __utmz=196938163.1405688217.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); __atuvc=15%7C29; Setting-61-Calendar Options=info|; Setting-61-Calendar Year=This Month; Setting-61-Calendar Body=All; Setting-61-ASP.calendar_aspx.gridCalendar.SortExpression=MeetingStartDate DESC; __utmb=196938163.4.10.1405700259',
        'Host': 'nyc.legistar.com',
        'Referer': 'http://nyc.legistar.com/Legislation.aspx',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0'
        },
    }



def incr_page(req):
    event_target = req['data']['__EVENTTARGET']
    event_target = event_target[:-1] + str(int(event_target[-1]) + 2)
    req['data']['__EVENTTARGET'] = event_target
    return req


def gen_responses():
    client = Client()
    # Switch to advanced search.
    client.send(req1)
    # Submit.
    yield client.send(req2)
    # Get page 2.
    yield client.send(req3)
    # Get pages 3 and up.
    while True:
        yield client.send(incr_page(req3))
