#!/usr/bin/env python
import re
import sys
import csv
import datetime
from splinter import Browser

browser = Browser('phantomjs')

# Yalu: these are the parameters
AIRPORTS = 'BOS YYC YVR YYZ YEG YUL YOW YHZ SFO LAX'.split()
DATES = [datetime.date(2013, 8, 8), datetime.date(2013, 8, 9)]


def main():

    csv_writer = csv.writer(sys.stdout)
    csv_writer.writerow("FROM, TO, STOP1, STOP2, FLIGHT1, FLIGHT2, FLIGHT3, START TIME, STOP TIME, DURATION, PRICE, RECORDED TIME".split(", "))

    for date in DATES:
        for origin, dest in pairs(AIRPORTS):
            try:
                launch_search(sys.stdout, origin, dest, date)
            except Exception, e:
                if isinstance(e, KeyboardInterrupt):
                    raise
                raise
                sys.stderr.write("Failed to run {0} -> {1}\n".format(origin, dest))
                sys.stderr.flush()


def launch_search(output, origin, dest, leave_date, return_date=None):
    browser.visit('http://www.aircanada.com/en/home.html')

    browser.fill_form({
        'org1': origin.upper(),
        'dest1': dest.upper()
    })

    for i, date in enumerate(filter(None, (leave_date, return_date))):
        browser.evaluate_script('document.getElementById("departure{0}").value="{1}"'.format(
            i + 1,
            date.strftime("%d/%m/%Y")
        ))

    browser.evaluate_script('document.getElementById("countryOfResidence").value = "US"')

    if not return_date:
        browser.evaluate_script('document.getElementById("tripType").value = "O"')

    browser.find_by_css('.s_oC_4').click()

    csv_writer = csv.writer(output)

    for row in gather_flight_data(browser, leave_date, origin, dest, 'flightList1'):
        csv_writer.writerow(map(to_str, row))

    if return_date:
        for row in gather_flight_data(browser, return_date, dest, origin, 'flightList2'):
            csv_writer.writerow(map(to_str, row))

    return browser


def gather_flight_data(browser, date, origin, dest, css_class):
    table = browser.find_by_id(css_class)[0]
    rows = table.find_by_tag('tr')
    in_fare = False
    current = origin
    fare_info = {'flights': []}
    for row in rows:
        if not row.visible:
            if fare_info.get('flights'):
                yield show_fare_info(fare_info)
                fare_info = {'flights': []}
            in_fare = False
            current = origin
            continue
        if not (row.has_class('onMiddle') or row.has_class('offMiddle')):
            if fare_info.get('flights'):
                yield show_fare_info(fare_info)
                fare_info = {'flights': []}
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
            fare_info.update({
                'origin': origin.upper(),
                'dest': dest.upper(),
                'price': price,
                'duration': duration
            })

        fare_info.get('flights', []).append({
            'flight': flight_name,
            'start': start_time,
            'stop': stop_time,
            'start_airport': start.upper(),
            'stop_airport': end.upper()
        })

    if fare_info.get('flights'):
        yield show_fare_info(fare_info)


def show_fare_info(fare_info):
    """
    Input:
        {'dest': 'BOS',
         'duration': 452,
         'flights': [{'flight': u'AC110',
                      'start': datetime.datetime(2013, 8, 8, 10, 15),
                      'start_airport': 'YYC',
                      'stop': datetime.datetime(2013, 8, 8, 16, 0),
                      'stop_airport': u'YYZ'},
                     {'flight': u'AC7388',
                      'start': datetime.datetime(2013, 8, 8, 18, 15),
                      'start_airport': u'YYZ',
                      'stop': datetime.datetime(2013, 8, 8, 19, 47),
                      'stop_airport': 'BOS'}],
         'origin': 'YYC',
         'price': u'$662'}
    Output: [FROM, TO, STOP1, STOP2, FLIGHT1, FLIGHT2, FLIGHT3, START TIME, STOP TIME, DURATION, PRICE, RECORDED TIME]
    """
    if len(fare_info.get('flights')) > 3:
        raise Exception("Fare has more than 3 flights: {0})".format(fare_info))

    row = [fare_info['origin'], fare_info['dest']]
    for flight in fare_info.get('flights')[:-1]:
        row.append(flight['stop_airport'])

    row.extend([''] * (3 - len(fare_info['flights'])))

    for flight in fare_info['flights']:
        row.append(flight['flight'])

    row.extend([''] * (3 - len(fare_info['flights'])))

    row.extend([fare_info['flights'][0]['start'],
                fare_info['flights'][-1]['stop'],
                fare_info['duration'],
                fare_info['price'],
                datetime.datetime.now()])

    return row


def pairs(input_list):
    for i in range(len(input_list)):
        for j in range(i):
            yield input_list[i], input_list[j]
            yield input_list[j], input_list[i]


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


connect_re = re.compile(r'\((\w{3,4})\)')
hour_min_re = re.compile(r'(\d{1,2}):(\d{2})\s*\((\d{1,2}-\w{3,4})\)')
plus_days = re.compile(r'(\d{1,2}):(\d{2})\s*\+\s*(\d+) day')


if __name__ == '__main__':
    main()
