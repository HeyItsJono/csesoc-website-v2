import icalendar as ical
import pytz
from datetime import datetime
import timetable_importer
from getpass import getpass

def display(calendar):
	return calendar.to_ical().replace('\r\n', '\n').strip()

def convertDt(dt, timezone):
	dt = dt.split('-')
	for x in dt[2].split('T'): dt.append(x)
	del dt[2]
	for x in dt[3].split(':'): dt.append(x)
	del dt[3]
	if dt[5] == '00.000': dt[5] = '0'
	if dt[4] == '00': dt[4] = '0'
	dt = [int(x) for x in dt]
	return datetime(dt[0], dt[1], dt[2], dt[3], dt[4], dt[5], tzinfo = pytz.timezone(timezone))
	

def makeEvents(events):
	event_list =[]
	uid = 7777
	for event in events:
		dtstart = convertDt(event['start']['dateTime'], event['start']['timeZone'])
		dtend = convertDt(event['end']['dateTime'], event['end']['timeZone'])
		event_instance = ical.Event()
		event_instance.add('summary', event['summary'])
		event_instance.add('description', event['description'])
		event_instance.add('location', event['location'])
		event_instance.add('dtstart', dtstart)
		event_instance.add('dtend', dtend)
		event_instance.add('uid', uid)
		event_instance['dtstart'].to_ical()
		event_instance['dtend'].to_ical()
		event_list.append(event_instance)
		uid += 1
	return event_list
		

if __name__ == '__main__':
	# Create a calendar
	zu = raw_input('UNSW zUser: ')
	zp = getpass('UNSW zPass: ')
	print 'Working...'
	calendar = ical.Calendar()
	calendar.add('prodid', 'HeyItsJono//UNSW-Timetable-Importer//EN')
	calendar.add('version', '2.0')
	events_to_add = makeEvents(timetable_importer.export(timetable_importer.getTimetable(zu, zp, None)))
	print "Adding Events..."
	for event in events_to_add: calendar.add_component(event)
	print display(calendar)
	with open('UNSW.ics', 'wb') as file:
		file.write(calendar.to_ical())
	print "Done!"
