#!/usr/bin/env python
import re
import sys
import csv
import datetime
from splinter import Browser

browser = Browser('phantomjs')

connect_re = re.compile(r'\((\w{3,4})\)')
hour_min_re = re.compile(r'(\d{1,2}):(\d{2})\s*\((\d{1,2}-\w{3,4})\)')
plus_days = re.compile(r'(\d{1,2}):(\d{2})\s*\+\s*(\d+) day')

AIRPORTS = 'BOS YYC YVR YYZ YEG YUL YOW YHZ SFO LAX'.split()


def main():
    start_date = datetime.date(2013, 7, 30)
    stop_date = datetime.date(2013, 7, 31)
    for origin, dest in pairs(AIRPORTS):
        launch_search(sys.stdout, origin, dest,
                      start_date, stop_date)


def launch_search(output, origin, dest, leave_date, return_date):
    browser.visit('http://www.aircanada.com/en/home.html')

    browser.fill_form({
        'org1': origin.upper(),
        'dest1': dest.upper()
    })

    for i, date in enumerate((leave_date, return_date)):
        browser.evaluate_script('document.getElementById("departure{0}").value="{1}"'.format(
            i + 1,
            date.strftime("%d/%m/%Y")
        ))

    browser.evaluate_script('document.getElementById("countryOfResidence").value = "US"')

    browser.find_by_css('.s_oC_4').click()

    csv_writer = csv.writer(output)

    for row in gather_flight_data(browser, leave_date, origin, dest, 'flightList1'):
        csv_writer.writerow(map(to_str, row))

    for row in gather_flight_data(browser, return_date, dest, origin, 'flightList2'):
        csv_writer.writerow(map(to_str, row))
    return browser


def gather_flight_data(browser, date, origin, dest, css_class):
    table = browser.find_by_id(css_class)[0]
    rows = table.find_by_tag('tr')
    in_fare = False
    current = origin
    for row in rows:
        if not row.visible:
            in_fare = False
            current = origin
            continue
        if not (row.has_class('onMiddle') or row.has_class('offMiddle')):
            in_fare = False
            continue
        cells = row.find_by_tag('td')
        if len(cells) < 7:
            continue
        flight_name = cells[1].text

        start_time = get_datetime(date, cells[2].text)
        stop_time = get_datetime(date, cells[3].text)

        start = current
        m = connect_re.search(cells[6].text)
        if m:
            current = end = m.group(1)
        else:
            end = dest

        if not in_fare:
            in_fare = True
            if 'h' in cells[5].text:
                hour, minutes = map(int, cells[5].text.split('hr'))
                duration = hour * 60 + minutes
            if row.find_by_css('.formattedCurrencyParent'):
                price = row.find_by_css('.formattedCurrencyParent').text
            yield ['', origin.upper(), dest.upper(), price,
                   duration]

        yield [flight_name, '', '', '', '',
               start_time, stop_time,
               start.upper(), end.upper()]


def pairs(input_list):
    for i in range(len(input_list)):
        for j in range(i):
            yield input_list[i], input_list[j]


def get_datetime(date, time):
    m = hour_min_re.search(time.strip())
    m2 = plus_days.search(time.strip())
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        date = datetime.datetime.strptime(m.group(3) + '-' + str(date.year),
                                          '%d-%b-%Y').date()
    elif m2:
        hour, minute = int(m2.group(1)), int(m2.group(2))
        result = datetime.datetime.combine(date, datetime.time(hour, minute))
        return result + datetime.timedelta(days=int(m2.group(3)))
    else:
        hour, minute = map(int, time.strip().split(':'))
        if hasattr(date, 'date'):
            date = date.date()
    return datetime.datetime.combine(date, datetime.time(hour, minute))


def to_str(obj):
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, unicode):
        return obj.encode('utf8', 'ignore')
    elif isinstance(obj, datetime.datetime):
        return obj.strftime("%m/%d/%Y %H:%M")
    elif isinstance(obj, datetime.date):
        return obj.strftime("%m/%d/%Y")
    elif isinstance(obj, datetime.timedelta):
        return str(int(obj.seconds / 60))
    else:
        return str(obj)

if __name__ == '__main__':
    main()
