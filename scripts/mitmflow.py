#!/usr/bin/env python
#
# Simple script showing how to read a mitmproxy dump file
# PS -- This garbage only works on python 2.7, because mitmproxy only 2.7
import urlparse
from libmproxy import flow
import json, sys

x = []
for filename in sys.argv[1:]:

    with open(filename, "rb") as f:
        freader = flow.FlowReader(f)
        last = list(freader.stream())[-1]
        params = dict(urlparse.parse_qsl(last.request.get_decoded_content()))
        del params['__VIEWSTATE']
        del params['__EVENTVALIDATION']
        x.append(params)

import pdb; pdb.set_trace()


ny = {'ctl00$ContentPlaceHolder1$btnSearch': 'Search Legislation',
 'ctl00$ContentPlaceHolder1$chkID': 'on',
 'ctl00$ContentPlaceHolder1$chkText': 'on',
 'ctl00$ContentPlaceHolder1$lstTypeBasic': 'All Types',
 'ctl00$ContentPlaceHolder1$lstYears': 'This Month',
 'ctl00_RadScriptManager1_TSM': ';;System.Web.Extensions, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35:en-US:fa6755fd-da1a-49d3-9eb4-1e473e780ecd:ea597d4b:b25378d2;Telerik.Web.UI, Version=2014.1.403.45, Culture=neutral, PublicKeyToken=121fae78165ba3d4:en-US:68d9452f-f268-45b2-8db7-8c3bbf305b8d:16e4e7cd:f7645509:24ee1bba:e330518b:88144a7a:1e771326:8e6f0d33:ed16cbdc:f46195d3:19620875:874f8ea2:cda80b3:383e4ce8:2003d0b8:aa288e2d:258f1c72:c128760b:c8618e41:1a73651d:333f8d94:58366029',
 'ctl00_tabTop_ClientState': '{"selectedIndexes":["1"],"logEntries":[],"scrollState":{}}'}

mc = {'ctl00$ContentPlaceHolder1$btnSearch': 'Search Legislation',
 'ctl00$ContentPlaceHolder1$chkID': 'on',
 'ctl00$ContentPlaceHolder1$chkText': 'on',
 'ctl00$ContentPlaceHolder1$lstTypeBasic': 'All Types',
 'ctl00$ContentPlaceHolder1$lstYears': 'This Year',
 'ctl00_RadScriptManager1_TSM': ';;System.Web.Extensions, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35:en-US:fa6755fd-da1a-49d3-9eb4-1e473e780ecd:ea597d4b:b25378d2;Telerik.Web.UI, Version=2014.1.403.45, Culture=neutral, PublicKeyToken=121fae78165ba3d4:en-US:68d9452f-f268-45b2-8db7-8c3bbf305b8d:16e4e7cd:f7645509:24ee1bba:e330518b:88144a7a:1e771326:8e6f0d33:ed16cbdc:f46195d3:19620875:874f8ea2:cda80b3:383e4ce8:2003d0b8:aa288e2d:258f1c72:c128760b:c8618e41:1a73651d:333f8d94:58366029',
 'ctl00_tabTop_ClientState': '{"selectedIndexes":["0"],"logEntries":[],"scrollState":{}}'}

import pdb; pdb.set_trace()
# x1 = {'ctl00$ButtonAlerts': None,
#  'ctl00$ContentPlaceHolder1$btnClear': 'Clear Criteria',
#  'ctl00$ContentPlaceHolder1$btnClear2': 'Clear Criteria',
#  'ctl00$ContentPlaceHolder1$btnSearch': 'Search Legislation',
#  'ctl00$ContentPlaceHolder1$btnSearch2': 'Search Legislation',
#  'ctl00$ContentPlaceHolder1$chkEconomicDisclosure': None,
#  'ctl00$ContentPlaceHolder1$chkKeyLegislation': None,
#  'ctl00$ContentPlaceHolder1$lstInControlOf': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstIndexedUnder': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstMax': '100',
#  'ctl00$ContentPlaceHolder1$lstSponsoredBy': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstStatus': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstType': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstWard': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstYearsAdvanced': 'All Years',
#  'ctl00$ContentPlaceHolder1$radFileCreated': '=',
#  'ctl00$ContentPlaceHolder1$radFinalAction': '=',
#  'ctl00$ContentPlaceHolder1$txtFil': None,
#  'ctl00$ContentPlaceHolder1$txtFileCreated1': '',
#  'ctl00$ContentPlaceHolder1$txtFileCreated1$dateInput': None,
#  'ctl00$ContentPlaceHolder1$txtFileCreated2': '',
#  'ctl00$ContentPlaceHolder1$txtFileCreated2$dateInput': None,
#  'ctl00$ContentPlaceHolder1$txtFinalAction1': '',
#  'ctl00$ContentPlaceHolder1$txtFinalAction1$dateInput': None,
#  'ctl00$ContentPlaceHolder1$txtFinalAction2': '',
#  'ctl00$ContentPlaceHolder1$txtFinalAction2$dateInput': None,
#  'ctl00$ContentPlaceHolder1$txtText': None,
#  'ctl00$ContentPlaceHolder1$txtTit': None,
#  'ctl00_ContentPlaceHolder1_RadToolTipManager1_ClientState': None,
#  'ctl00_ContentPlaceHolder1_gridMain_ClientState': None,
#  'ctl00_ContentPlaceHolder1_lstInControlOf_ClientState': None,
#  'ctl00_ContentPlaceHolder1_lstIndexedUnder_ClientState': None,
#  'ctl00_ContentPlaceHolder1_lstMax_ClientState': None,
#  'ctl00_ContentPlaceHolder1_lstSponsoredBy_ClientState': None,
#  'ctl00_ContentPlaceHolder1_lstStatus_ClientState': None,
#  'ctl00_ContentPlaceHolder1_lstType_ClientState': None,
#  'ctl00_ContentPlaceHolder1_lstWard_ClientState': None,
#  'ctl00_ContentPlaceHolder1_lstYearsAdvanced_ClientState': None,
#  'ctl00_ContentPlaceHolder1_menuMain_ClientState': None,
#  'ctl00_ContentPlaceHolder1_txtFileCreated1_ClientState': None,
#  'ctl00_ContentPlaceHolder1_txtFileCreated1_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,6,18]]',
#  'ctl00_ContentPlaceHolder1_txtFileCreated1_calendar_SD': '[]',
#  'ctl00_ContentPlaceHolder1_txtFileCreated1_dateInput_ClientState': None,
#  'ctl00_ContentPlaceHolder1_txtFileCreated2_ClientState': None,
#  'ctl00_ContentPlaceHolder1_txtFileCreated2_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,6,18]]',
#  'ctl00_ContentPlaceHolder1_txtFileCreated2_calendar_SD': '[]',
#  'ctl00_ContentPlaceHolder1_txtFileCreated2_dateInput_ClientState': None,
#  'ctl00_ContentPlaceHolder1_txtFinalAction1_ClientState': None,
#  'ctl00_ContentPlaceHolder1_txtFinalAction1_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,6,18]]',
#  'ctl00_ContentPlaceHolder1_txtFinalAction1_calendar_SD': '[]',
#  'ctl00_ContentPlaceHolder1_txtFinalAction1_dateInput_ClientState': None,
#  'ctl00_ContentPlaceHolder1_txtFinalAction2_ClientState': None,
#  'ctl00_ContentPlaceHolder1_txtFinalAction2_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,6,18]]',
#  'ctl00_ContentPlaceHolder1_txtFinalAction2_calendar_SD': '[]',
#  'ctl00_ContentPlaceHolder1_txtFinalAction2_dateInput_ClientState': None,
#  'ctl00_RadScriptManager1_TSM': '',
#  'ctl00_tabTop_ClientState': None}

# x2 = {'__EVENTTARGET': 'ctl00$ContentPlaceHolder1$btnSwitch',
#  'ctl00$ContentPlaceHolder1$lstInControlOf': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstIndexedUnder': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstMax': '100',
#  'ctl00$ContentPlaceHolder1$lstSponsoredBy': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstStatus': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstType': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstWard': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstYearsAdvanced': 'All Years',
#  'ctl00$ContentPlaceHolder1$radFileCreated': '=',
#  'ctl00$ContentPlaceHolder1$radFinalAction': '=',
#  'ctl00_ContentPlaceHolder1_txtFileCreated1_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,6,18]]',
#  'ctl00_ContentPlaceHolder1_txtFileCreated1_calendar_SD': '[]',
#  'ctl00_ContentPlaceHolder1_txtFileCreated1_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
#  'ctl00_ContentPlaceHolder1_txtFileCreated2_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,6,18]]',
#  'ctl00_ContentPlaceHolder1_txtFileCreated2_calendar_SD': '[]',
#  'ctl00_ContentPlaceHolder1_txtFileCreated2_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
#  'ctl00_ContentPlaceHolder1_txtFinalAction1_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,6,18]]',
#  'ctl00_ContentPlaceHolder1_txtFinalAction1_calendar_SD': '[]',
#  'ctl00_ContentPlaceHolder1_txtFinalAction1_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
#  'ctl00_ContentPlaceHolder1_txtFinalAction2_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,6,18]]',
#  'ctl00_ContentPlaceHolder1_txtFinalAction2_calendar_SD': '[]',
#  'ctl00_ContentPlaceHolder1_txtFinalAction2_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
#  'ctl00_RadScriptManager1_TSM': ';;System.Web.Extensions, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35:en-US:fa6755fd-da1a-49d3-9eb4-1e473e780ecd:ea597d4b:b25378d2;Telerik.Web.UI, Version=2014.1.403.45, Culture=neutral, PublicKeyToken=121fae78165ba3d4:en-US:68d9452f-f268-45b2-8db7-8c3bbf305b8d:16e4e7cd:f7645509:24ee1bba:e330518b:88144a7a:1e771326:8e6f0d33:ed16cbdc:f46195d3:19620875:874f8ea2:cda80b3:383e4ce8:2003d0b8:aa288e2d:258f1c72:8674cba1:7c926187:b7778d6c:c08e9f8a:a51ee93e:59462f1:c128760b:c8618e41:1a73651d:333f8d94:58366029',
#  'ctl00_tabTop_ClientState': '{"selectedIndexes":["1"],"logEntries":[],"scrollState":{}}'}

# x3 = {'__EVENTTARGET': 'ctl00$ContentPlaceHolder1$btnSwitch',
#  'ctl00$ContentPlaceHolder1$lstInControlOf': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstIndexedUnder': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstMax': '1000',
#  'ctl00$ContentPlaceHolder1$lstSponsoredBy': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstStatus': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstType': '-Select-',
#  'ctl00$ContentPlaceHolder1$lstYearsAdvanced': 'This Month',
#  'ctl00$ContentPlaceHolder1$radFinalAction': '=',
#  'ctl00$ContentPlaceHolder1$radOnAgenda': '=',
#  'ctl00_ContentPlaceHolder1_txtFinalAction1_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,6,18]]',
#  'ctl00_ContentPlaceHolder1_txtFinalAction1_calendar_SD': '[]',
#  'ctl00_ContentPlaceHolder1_txtFinalAction1_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
#  'ctl00_ContentPlaceHolder1_txtFinalAction2_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,6,18]]',
#  'ctl00_ContentPlaceHolder1_txtFinalAction2_calendar_SD': '[]',
#  'ctl00_ContentPlaceHolder1_txtFinalAction2_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
#  'ctl00_ContentPlaceHolder1_txtOnAgenda1_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,6,18]]',
#  'ctl00_ContentPlaceHolder1_txtOnAgenda1_calendar_SD': '[]',
#  'ctl00_ContentPlaceHolder1_txtOnAgenda1_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
#  'ctl00_ContentPlaceHolder1_txtOnAgenda2_calendar_AD': '[[1980,1,1],[2099,12,30],[2014,6,18]]',
#  'ctl00_ContentPlaceHolder1_txtOnAgenda2_calendar_SD': '[]',
#  'ctl00_ContentPlaceHolder1_txtOnAgenda2_dateInput_ClientState': '{"enabled":true,"emptyMessage":"","validationText":"","valueAsString":"","minDateStr":"1980-01-01-00-00-00","maxDateStr":"2099-12-31-00-00-00","lastSetTextBoxValue":""}',
#  'ctl00_RadScriptManager1_TSM': ';;System.Web.Extensions, Version=4.0.0.0, Culture=neutral, PublicKeyToken=31bf3856ad364e35:en-US:fa6755fd-da1a-49d3-9eb4-1e473e780ecd:ea597d4b:b25378d2;Telerik.Web.UI, Version=2014.1.403.45, Culture=neutral, PublicKeyToken=121fae78165ba3d4:en-US:68d9452f-f268-45b2-8db7-8c3bbf305b8d:16e4e7cd:f7645509:24ee1bba:e330518b:88144a7a:1e771326:8e6f0d33:ed16cbdc:f46195d3:19620875:874f8ea2:cda80b3:383e4ce8:2003d0b8:aa288e2d:258f1c72:8674cba1:7c926187:b7778d6c:c08e9f8a:a51ee93e:59462f1:c128760b:c8618e41:1a73651d:333f8d94:58366029',
#  'ctl00_tabTop_ClientState': '{"selectedIndexes":["1"],"logEntries":[],"scrollState":{}}'}

# import pdb; pdb.set_trace()