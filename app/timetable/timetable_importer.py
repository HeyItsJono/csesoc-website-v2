# myUNSW to Google Calendar Timetable Importer
# More or less written by Chris Lam
# Cleaned up/Google Calendar stuff removed by HeyItsJono

import httplib2
from bs4 import BeautifulSoup
import re
import urllib2
import cookielib
import re
import urllib
import base64

import datetime

unsw_start_dates = {
   '11s1':'28/2/2011',
   '11s2':'18/7/2011',
   '12s1':'27/2/2012',
   '12s2':'16/7/2012',
   '13s1':'4/3/2013',
   '13s2':'29/7/2013',
   '14s1':'3/3/2014',
   '14s2':'28/7/2014',
   '15s1':'2/3/2015',
   '15s2':'27/7/2015',
   '16s1':'29/2/2016',
   '16s2':'25/7/2016'
}

days = {"Mon":0, "Tue":1, "Wed":2, "Thu":3, "Fri":4}

login_url='https://ssologin.unsw.edu.au/cas/login?service=https%3A%2F%2Fmy.unsw.edu.au%2Famserver%2FUI%2FLogin%3Fmodule%3DISISWSSO%26IDToken1%3D'

timetable_url='https://my.unsw.edu.au/active/studentTimetable/timetable.xml'

def getTimetable(zUser, zPass, semester):
	jar = cookielib.CookieJar()
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(jar))
	# CSRF Token or something. We need to steal it from SSO
	# into our cookie jar to go open the timetable page
	stupid_thing = re.findall(r'_cNoOpConversation.*?"', opener.open(login_url).read())[0].replace('"', '')
	data = {'username': zUser, 'password': zPass, '_eventId': 'submit', 'lt': stupid_thing}
	opener.open(login_url, urllib.urlencode(data))
	data = {}
	if semester:
		source = opener.open(timetable_url).read().replace('\n', '')
		if "sectionHeading" not in source:
			return ''
		s = BeautifulSoup(source)
		bsds = s.find('input', {'name': 'bsdsSequence'})['value']
		data = {'term': semester, 'bsdsSubmit-commit': 'Get Timetable', 'bsdsSequence': bsds}
	return opener.open(timetable_url, urllib.urlencode(data)).read()

def CreateClassEvent(title, content, where, start_time, end_time):
	event = {
	'summary': title,
	'description': content,
	'location': where,
	'start': {
	'dateTime' : start_time,
	'timeZone': 'Australia/Sydney',
	},
	'end': {
	'dateTime': end_time,
	'timeZone': 'Australia/Sydney',
	}
	}
	return event

def getSemester(zu, zp):
	source = getTimetable(zu, zp, None)
	if "sectionHeading" not in source:
		raise Exception("Bad timetable source, possibly incorrect login details or myunsw daily dose of downtime (12am-2am or whatever)", {})

	# parsing shit
	s = BeautifulSoup(source.replace("\n",""))
	select_html = s.find("select", {'name': 'term'})
	select_html['style'] = 'width: 400px;'
	return (None,
	{
	'semester_select_html': select_html.prettify(),
	'source': source
	})


def export(source):
	events = []
	
	f = source.replace('\r', '')

	if "sectionHeading" not in f:
		raise Exception("Bad timetable source, possibly incorrect login details or myunsw daily dose of downtime (12am-2am or whatever)")

	# parsing shit
	s = BeautifulSoup(f.replace("\n",""))
	sem = re.sub(r'.*Semester (\d+) \S\S(\d+).*', u'\\2s\\1', s.find("option", {'selected':'true'}).text)
	title = sem + " Timetable"

	if not re.match(r'\d\ds\d', sem):
		current_time = datetime.datetime.now()
		sem = '%ds%d' % (current_time.year % 100, 1 if current_time.month < 7 else 2)

	####################################################
	#  LOOK EVERYONE, I'M THROWING YOUR PASSWORDS AWAY #
	####################################################
	zp = ''

	# Summer courses have N1 and N2 right after each other
	if s.find(text="N1").findNext("table").findNext("td").text == "N2":
		week_after_midsem_break = int(s.find(text="N2").findNext("table").findNext("td").text)
	else:
		week_after_midsem_break = int(s.find(text="N1").findNext("table").findNext("td").text)

	courses = [x.contents[0] for x in s.findAll("td", {"class":"sectionHeading"})]

	#print "Parsing calendar to make events"

	for course in courses:
		# FINGERS CROSSED THAT THE TIMETABLE PAGE NEVER CHANGES
		classes = s.find(text=course).findNext("table").findAll("tr", {"class": re.compile("data")})
		class_type, class_code, day, time, weeks, place, current_detail = ['' for x in xrange(7)]
		for c in classes:
			class_details = [(x.contents[0] if x.contents else "") for x in c.findAll("td", recursive=False)]
			details_generator = (current_detail for current_detail in class_details)

			current_detail = details_generator.next()
			
			if current_detail.strip() != "&nbsp;" and u"\xa0" not in class_details:
				legacy_type = current_detail
				class_type = current_detail
			elif u"\xa0" in class_details:
				class_type = legacy_type

			current_detail = details_generator.next()

			if current_detail.strip() not in days:
				class_code = current_detail
				day = details_generator.next().strip()
			else:
				day = current_detail.strip()
			
			time = details_generator.next()
			
			weeks = details_generator.next()
			
			place = details_generator.next()
			
			current_detail = ' '.join(details_generator.next().findAll(text=True))
			
			if time.find(" - ") == -1:
				continue
			start, end = time.split(" - ")
			start = datetime.datetime.strptime(unsw_start_dates[sem] + ' ' + start, "%d/%m/%Y %I:%M%p")
			end = datetime.datetime.strptime(unsw_start_dates[sem] + ' ' + end, "%d/%m/%Y %I:%M%p")
			
			course = course.split()[0]
			
			weeks_list = []
			for week in weeks.split(","):
				if "N" in week:
					print "Did not process %s %s %s because of non-integer week"
					continue
				if "-" in week:
					weeks_list += range(int(week.split("-")[0]), int(week.split("-")[1])+1)
				else:
					weeks_list += [int(week)]
			
			weeks = weeks_list
			
			for week in weeks:
				if week < week_after_midsem_break:
					week -= 1
				thisStart = start + datetime.timedelta(7 * week + days[day])
				thisEnd = end + datetime.timedelta(7 * week + days[day])

				thisEvent = CreateClassEvent('%s %s' % (course, class_type),
				"Instructor: %s, Class Code: %s" % (current_detail.strip(), class_code),
				place,
				thisStart.strftime('%Y-%m-%dT%H:%M:%S.000'),
				thisEnd.strftime('%Y-%m-%dT%H:%M:%S.000'))
				events.append(thisEvent)
	return events

def exportByScraping(zu, zp, semester, code, full_path):
	source = getTimetable(zu, zp, semester)
	return export(source, code, full_path)

if __name__ == '__main__':
	export(getTimetable(zu, zp, None))
