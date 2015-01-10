# -*- coding: utf-8 -*-
###############################################################################
# This is a self-extracting UI application package for ical_generator_gui.
# Run this script once to extract the packaged application.
# The files will be extracted to ical_generator_gui.py and ical_generator_gui.pyui.
# Make sure that these files do not exist yet.
# To update from an older version, move or delete the old files first.
# After extracting, the application can be found at ical_generator_gui.py.
# This bundle can be deleted after extraction.
###############################################################################
# Packaged using PackUI by dgelessus
# https://github.com/dgelessus/pythonista-scripts/blob/master/UI/PackUI.py
###############################################################################

import console, os.path

NAME     = "ical_generator_gui"
PYFILE   = """import ui
import os
import console
import base64 as b64

import icalendar as ical
import pytz
from datetime import datetime
import timetable_importer
import time
from time import sleep

import sys
import SocketServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
import webbrowser
import threading

green = '1FDB6E'

original_stdout = sys.stdout
original_stderr = sys.stderr

class BasicServer(SocketServer.TCPServer):
	allow_reuse_address = True


class NullifyOutput():
	def write(self, s):
		#write() is never called or used, its just used to validate this class
		#stdout/stderr is momentarily redirected to this class and then dropped
		#so it doesnt appear in the console. This suppresses the error which
		#appears when you use server.socket.close()
		#stderr/stdout normal functions are restored immediately afterward
		pass


class ServerThread(threading.Thread):
	def __init__(self, ip, port):
		super(ServerThread, self).__init__()
		self.ip = ip
		self.port = port
		self.HandlerClass = SimpleHTTPRequestHandler
		self.Protocol = 'HTTP/1.0'
		self.server_address = (self.ip, self.port)
		self.HandlerClass.protocol_version = self.Protocol
		try:
			self.httpd = BasicServer(self.server_address, self.HandlerClass)
		except:
			self.port += 1
			self.server_address = (self.ip, self.port)
			self.httpd = BasicServer(self.server_address, self.HandlerClass)
		self.stoptheserver = threading.Event()
	
	
	def run(self):
		while not self.stoptheserver.isSet():
			self.httpd.handle_request()
	
	
	def join(self, timeout=None):
		self.stoptheserver.set()
		self.httpd.socket.close()
		super(ServerThread, self).join(timeout)


def display(calendar):
	return calendar.to_ical().replace('\\r\\n', '\\n').strip()


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


def readCreds():
	if os.path.isfile('creds.cr'):
		with open('creds.cr', 'r') as file:
			return {'zu':b64.b64decode(file.readline().strip('\\n')),
			        'zp':b64.b64decode(file.readline())}
	else:
		return None


def writeCreds(zu, zp):
	with open('creds.cr', 'w') as file:
		file.write(b64.b64encode(zu) + '\\n' + b64.b64encode(zp))


def saveCreds(zu, zp):
	if readCreds() is None:
		writeCreds(zu, zp)
	elif readCreds()['zu'] == zu and readCreds()['zp'] == zp:
		pass
	else:
		os.remove('creds.cr')
		writeCreds(zu, zp)


def importCal():
	calendar = ical.Calendar()
	calendar.add('prodid', 'HeyItsJono//UNSW-Timetable-Importer//EN')
	calendar.add('version', '2.0')
	events_to_add = makeEvents(timetable_importer.export(timetable_importer.getTimetable(details_screen['zu_field'].text, details_screen['zp_field'].text, None)))
	wait_screen['dlparse'].text_color = green
	wait_screen['make'].text_color = green
	sleep(1)
	for event in events_to_add: calendar.add_component(event)
	wait_screen['add'].text_color = green
	with open('UNSW.ics', 'wb') as file:
		file.write(calendar.to_ical())
	wait_screen['save'].text_color = green
	ui.delay(nav.push_view(export_screen), 2)
	wait_screen['export_button'].alpha = 1
	wait_screen['worklabel'].alpha = 0
	wait_screen['export_button'].enabled = True


def existingAlert():
	return console.alert(title='Existing Calendar found!', message='A previously generated UNSW Timetable file has been found. Would you like to generate a new one or export the existing one? \\nWarning: Generating a new file will replace the existing one.', button1='Use Existing Timetable',button2='Generate New Timetable',hide_cancel_button=True)


def begin_tapped(sender):
	nav.push_view(details_screen)
	if readCreds() is not None:
		details_screen['zu_field'].text = readCreds()['zu']
		details_screen['zp_field'].text = readCreds()['zp']


def clear_tapped(sender):
	if sender.name == 'zu_button':
		sender.superview['zu_field'].text = ''
	elif sender.name == 'zp_button':
		sender.superview['zp_field'].text = ''


def next_tapped(sender):
	zu_field = sender.superview['zu_field'].text
	zp_field = sender.superview['zp_field'].text
	save_details = sender.superview['save_details'].value
	if zu_field != '' and zp_field != '':
		if save_details == True: saveCreds(zu_field, zp_field)
		nav.push_view(wait_screen)
	else:
		console.hud_alert('Please enter credentials before continuing.', icon='error')


@ui.in_background
def import_tapped(sender):
	if os.path.isfile('UNSW.ics'):
		alert_result = existingAlert()
		if alert_result == 0:
			nav.push_view(export_screen)
		elif alert_result == 1:
			os.remove('UNSW.ics')
			worklabel = wait_screen['worklabel']
			import_button = wait_screen['import_button']
			worklabel.alpha = 1
			import_button.alpha = 0
			import_button.enabled = False
			importCal()
	else:
		worklabel = wait_screen['worklabel']
		import_button = wait_screen['import_button']
		worklabel.alpha = 1
		import_button.alpha = 0
		import_button.enabled = False
		importCal()


def toexport_tapped(sender):
	nav.push_view(export_screen)


@ui.in_background
def export_tapped(sender):
	name = sender.name
	if name == 'quicklook_button':
		v.close()
		try:
			sleep(1)
		except:
			try:
				sleep(lambda: float(1))
			except:
				sleep(float(1))
		#weird try/except sleep tree because for some weird reason attempting to
		#quick look a freshly generated .ics causes sleep(1) to throw a type error
		#asking for a function/callable. providing it a lambda returning 1 throws
		#another type error asking for a float.
		console.quicklook('UNSW.ics')
		v.present('sheet')
	elif name == 'cal_button':
		if not server.isAlive():
			server.start()
		webbrowser.open('safari-http://127.0.0.1:' + str(server.port) + '/UNSW.ics')
	elif name == 'gcal_button':
		pass
	elif name == 'cal_info':
		console.alert(title='Calendar Info', message='Choosing Calendar will give you the option to subscribe to your timetable via the stock iOS Calendar app.', button1="OK", hide_cancel_button=True)
	elif name == 'quicklook_info':
		console.alert(title='Quick Look Info', message='Choosing Quick Look will bring up a window allowing you to inspect the events of the timetable and their individual details. It also allows you to open the calendar file in other apps and share it via Mail, Messages and Air Drop. If you mail it to yourself, you can add individual events one by one (or all at once) to a calender of your choosing by viewing it in the iOS stock Mail app.', button1="OK", hide_cancel_button=True)
	elif name == 'gcal_info':
		console.alert(title='Google Calendar Info', message='This feature is currently unavailable. This option will allow you to sync your timetable to your Google account. This can also be subsequently synced to your stock iOS Calendar app.', button1="OK", hide_cancel_button=True)


@ui.in_background
def done_tapped(sender):
	if server.isAlive():
		sys.stdout, sys.stderr = NullifyOutput(), NullifyOutput()
		server.join(3)
		sys.stdout, sys.stderr = original_stdout, original_stderr
	v.close()
	sys.exit()



v = ui.load_view('ical_generator_gui')

wait_screen = v.subviews[1]
export_screen = v.subviews[2]
details_screen = v.subviews[3]
nav = v.subviews[0]
wait_screen['export_button'].enabled = False
export_screen['gcal_button'].enabled = False

server = ServerThread('127.0.0.1', 8000)

if __name__ == '__main__':
	console.clear()
	v.present('sheet')
"""
PYUIFILE = """[{"class":"View","attributes":{"name":"UNSW Timetable Importer","background_color":"RGBA(1.000000,1.000000,1.000000,1.000000)","tint_color":"RGBA(0.056122,0.647092,0.785714,1.000000)","enabled":true,"border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","flex":""},"frame":"{{0, 0}, {552, 2336}}","nodes":[{"class":"NavigationView","attributes":{"enabled":true,"title_bar_color":"RGBA(1.000000,1.000000,1.000000,1.000000)","flex":"","name":"nav","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","title_color":"RGBA(0.330000,0.330000,0.330000,1.000000)","background_color":"RGBA(1.000000,1.000000,1.000000,1.000000)","root_view_name":"UNSW Timetable Importer","uuid":"20A06217-50D5-4FFE-98C4-D9BEA9BDE065"},"frame":"{{0, 0}, {540, 575}}","nodes":[{"class":"Label","attributes":{"font_size":43,"enabled":true,"text":"UNSW Timetable Importer","font_name":"HelveticaNeue-UltraLight","name":"label1","flex":"","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text_color":"RGBA(0.168367,0.494736,0.785714,1.000000)","alignment":"center","uuid":"88509520-74E2-4F6C-8F19-9E3FE90D208B"},"frame":"{{44, 6}, {450.5, 86.5}}","nodes":[]},{"class":"TextView","attributes":{"alignment":"center","autocorrection_type":"no","font_size":22,"font_name":"Avenir-Light","enabled":true,"flex":"","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text":"Welcome to the UNSW Timetable Importer.\\nThis app requires an internet connection to function.\\nPlease press the button to continue.","text_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","name":"textview1","spellchecking_type":"no","editable":false,"uuid":"2725CA27-7A1E-4656-BB4E-3D68AE20A9C4"},"frame":"{{44, 151}, {450.5, 183}}","nodes":[]},{"class":"Button","attributes":{"font_size":17,"enabled":true,"flex":"","font_bold":false,"name":"button1","corner_radius":0,"border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","action":"begin_tapped","border_width":1,"uuid":"CBA67E50-25FD-4337-811F-C87131B9E126","title":"Begin"},"frame":"{{44, 387}, {450.5, 100}}","nodes":[]}]},{"class":"View","attributes":{"name":"2. Wait","background_color":"RGBA(1.000000,1.000000,1.000000,1.000000)","uuid":"5AEF6202-3B97-4D83-8AA8-F2887EEF3D2E","enabled":true,"border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","flex":""},"frame":"{{0, 1166}, {540, 575}}","nodes":[{"class":"Button","attributes":{"background_color":"RGBA(1.000000,1.000000,1.000000,1.000000)","image_name":"ionicons-ios7-arrow-right-32","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","font_size":17,"title":"Export","enabled":true,"flex":"","action":"toexport_tapped","font_bold":false,"alpha":0,"name":"export_button","corner_radius":0,"border_width":1,"uuid":"82BC5D32-D8A4-41C9-9F5C-27030007BD08"},"frame":"{{44, 146}, {450.5, 101.5}}","nodes":[]},{"class":"Label","attributes":{"font_size":43,"enabled":true,"text":"UNSW Timetable Importer","font_name":"HelveticaNeue-UltraLight","name":"label1","flex":"","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text_color":"RGBA(0.168367,0.494737,0.785714,1.000000)","alignment":"left","uuid":"E96969A8-124B-4C4D-B87F-64BC89294C18"},"frame":"{{44, 6}, {450.5, 86.5}}","nodes":[]},{"class":"Label","attributes":{"background_color":"RGBA(1.000000,1.000000,1.000000,1.000000)","alignment":"center","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","font_size":30,"font_name":"Avenir-Light","enabled":true,"flex":"","text":"Working, please wait!","text_color":"RGBA(0.285714,0.285714,0.285714,1.000000)","alpha":0,"name":"worklabel","uuid":"71A0C51A-7B6E-4ED0-8994-1013C3A3E8D3"},"frame":"{{44, 146}, {450.5, 101.5}}","nodes":[]},{"class":"Label","attributes":{"font_size":17,"enabled":true,"text":"Downloading\\/Parsing","flex":"","name":"dlparse","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text_color":"RGBA(0.928571,0.132653,0.132653,1.000000)","alignment":"center","uuid":"45BD951A-4701-4DFF-B1BE-258B6C79AFD6"},"frame":"{{181, 307}, {176.5, 32}}","nodes":[]},{"class":"Label","attributes":{"font_size":17,"enabled":true,"text":"Making events","flex":"","name":"make","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text_color":"RGBA(0.928571,0.132653,0.132653,1.000000)","alignment":"center","uuid":"9A2A01B7-150B-4A5E-866A-8A07FB7C6427"},"frame":"{{181, 347}, {176.5, 32}}","nodes":[]},{"class":"Label","attributes":{"font_size":17,"enabled":true,"text":"Adding events","flex":"","name":"add","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text_color":"RGBA(0.928571,0.132653,0.132653,1.000000)","alignment":"center","uuid":"EF238E3F-D03A-41EE-A6E3-D214FDA2177C"},"frame":"{{181, 387}, {176.5, 32}}","nodes":[]},{"class":"Label","attributes":{"font_size":17,"enabled":true,"text":"Saving calendar","flex":"","name":"save","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text_color":"RGBA(0.928571,0.132653,0.132653,1.000000)","alignment":"center","uuid":"7FEC41D7-339F-4A96-BA57-4DAFAC106DD0"},"frame":"{{181, 427}, {176.5, 32}}","nodes":[]},{"class":"Button","attributes":{"background_color":"RGBA(1.000000,1.000000,1.000000,1.000000)","image_name":"ionicons-archive-24","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","font_size":17,"title":"  Import!","enabled":true,"flex":"","action":"import_tapped","font_bold":false,"alpha":1,"name":"import_button","corner_radius":0,"border_width":1,"uuid":"826A65D9-55AA-4924-A734-0FBB77DF3278"},"frame":"{{44, 146}, {450.5, 101.5}}","nodes":[]}]},{"class":"View","attributes":{"name":"3. Export","background_color":"RGBA(1.000000,1.000000,1.000000,1.000000)","uuid":"A88A865A-8AEE-47A4-8A1F-B9690F025213","enabled":true,"border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","flex":""},"frame":"{{0, 1749}, {540, 575}}","nodes":[{"class":"Button","attributes":{"image_name":"ionicons-ios7-calendar-outline-32","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","font_size":15,"title":"","enabled":true,"flex":"","action":"export_tapped","font_bold":false,"name":"cal_button","corner_radius":0,"border_width":1,"uuid":"C64785F7-F7A6-4546-A7B3-4E7FF7ECA408"},"frame":"{{222, 195}, {100, 100}}","nodes":[]},{"class":"Button","attributes":{"image_name":"ionicons-ios7-search-32","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","font_size":15,"title":"","enabled":true,"flex":"","action":"export_tapped","font_bold":false,"name":"quicklook_button","corner_radius":0,"border_width":1,"uuid":"02CC774C-2C1A-4D70-92D4-4DFC24A792C0"},"frame":"{{44, 195}, {100, 100}}","nodes":[]},{"class":"Button","attributes":{"font_size":15,"enabled":true,"flex":"","font_bold":false,"name":"gcal_button","uuid":"9F32E256-FE03-430C-939A-8AB2A21BF46B","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","border_width":1,"action":"export_tapped","image_name":"ionicons-icon-social-google-plus-outline-32","title":""},"frame":"{{394, 195}, {100, 100}}","nodes":[]},{"class":"Label","attributes":{"font_size":17,"enabled":true,"text":"Quick Look","font_name":"Avenir-Light","name":"label1","flex":"","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","alignment":"center","uuid":"7247DB36-54DB-40F4-9C0E-545FE9136199"},"frame":"{{44, 319}, {100, 32}}","nodes":[]},{"class":"Label","attributes":{"font_size":17,"enabled":true,"text":"Calendar","font_name":"Avenir-Light","name":"label2","flex":"","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","alignment":"center","uuid":"85BE9A35-D05F-4266-A302-EDD28D40A1A5"},"frame":"{{222, 319}, {100, 32}}","nodes":[]},{"class":"Label","attributes":{"font_size":43,"enabled":true,"text":"UNSW Timetable Importer","font_name":"HelveticaNeue-UltraLight","name":"label4","flex":"","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text_color":"RGBA(0.168367,0.494736,0.785714,1.000000)","alignment":"left","uuid":"5EE3ED4A-D156-494A-8B18-6BD76ED0D5BA"},"frame":"{{44, 0}, {450.5, 108.5}}","nodes":[]},{"class":"Button","attributes":{"font_size":15,"enabled":true,"flex":"","font_bold":false,"name":"quicklook_info","uuid":"35DEDDD3-033B-49FF-A327-4F7771132AFC","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","action":"export_tapped","image_name":"ionicons-information-circled-32","title":""},"frame":"{{69, 359}, {50, 50}}","nodes":[]},{"class":"Button","attributes":{"font_size":15,"enabled":true,"flex":"","font_bold":false,"name":"cal_info","uuid":"EEC904D1-436D-4571-B767-D0931EEB2AAC","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","action":"export_tapped","image_name":"ionicons-information-circled-32","title":""},"frame":"{{247, 359}, {50, 50}}","nodes":[]},{"class":"Button","attributes":{"font_size":17,"enabled":true,"flex":"","font_bold":false,"name":"done_button","uuid":"9D3B4527-DEB3-488F-BC67-D39B5858C078","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","border_width":1,"action":"done_tapped","image_name":"ionicons-ios7-checkmark-outline-32","title":"  Done"},"frame":"{{46, 417}, {450.5, 100}}","nodes":[]},{"class":"TextView","attributes":{"alignment":"center","autocorrection_type":"no","font_size":17,"font_name":"Avenir-Light","enabled":true,"flex":"","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text":"Pick an option below or press the info button to find out more.","text_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","name":"textview1","spellchecking_type":"no","editable":false,"uuid":"BA838374-FD2D-4E20-96B7-D185BE3D4855"},"frame":"{{44, 91.5}, {449.5, 61}}","nodes":[]},{"class":"TextView","attributes":{"alignment":"center","autocorrection_type":"no","font_size":17,"font_name":"Avenir-Light","enabled":true,"flex":"","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text":"Google Calendar","text_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","name":"textview2","spellchecking_type":"no","editable":false,"uuid":"AC916F6B-3180-4DBC-A667-FDBD85DBAE92"},"frame":"{{394, 303}, {99.5, 64}}","nodes":[]},{"class":"Button","attributes":{"font_size":15,"enabled":true,"flex":"","font_bold":false,"name":"gcal_info","uuid":"90FB47E6-1826-4B9B-A44F-E37119695597","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","action":"export_tapped","image_name":"ionicons-information-circled-32","title":""},"frame":"{{419, 359}, {50, 50}}","nodes":[]},{"class":"TextView","attributes":{"font_size":13,"enabled":true,"text":"Warning: Please press Done when you are finished to ensure the program exits cleanly.","font_name":"AppleSDGothicNeo-Light","name":"textview3","flex":"","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text_color":"RGBA(0.785714,0.216946,0.056122,1.000000)","alignment":"center","editable":true,"uuid":"09ACCCE9-2BEA-422A-A535-E13AA307C18E"},"frame":"{{45, 149}, {448.5, 38}}","nodes":[]}]},{"class":"View","attributes":{"name":"1. Enter Details","background_color":"RGBA(1.000000,1.000000,1.000000,1.000000)","uuid":"2B2E8653-259A-4B73-A6F3-79E9A3A0E24A","enabled":true,"border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","flex":""},"frame":"{{0, 583}, {540, 575}}","nodes":[{"class":"Label","attributes":{"font_size":43,"enabled":true,"text":"UNSW Timetable Importer","font_name":"HelveticaNeue-UltraLight","name":"label1","flex":"","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text_color":"RGBA(0.168367,0.494736,0.785714,1.000000)","alignment":"center","uuid":"41092D9F-DFE9-4A2C-953F-A124C2B20568"},"frame":"{{44, 6}, {450.5, 86.5}}","nodes":[]},{"class":"TextField","attributes":{"alignment":"center","autocorrection_type":"no","font_size":17,"border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","enabled":true,"flex":"","placeholder":"UNSW zUser","text_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","name":"zu_field","border_style":3,"spellchecking_type":"no","uuid":"650C728E-D747-4413-93E5-E78E2872D351"},"frame":"{{44, 116}, {450.5, 60.5}}","nodes":[]},{"class":"TextField","attributes":{"alignment":"center","autocorrection_type":"no","font_size":17,"border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","enabled":true,"flex":"","placeholder":"UNSW zPass","text_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","name":"zp_field","border_style":3,"spellchecking_type":"no","uuid":"6C03DCEB-1ED1-4CDB-BC6B-02706ED67913","secure":true},"frame":"{{44, 184.5}, {450.5, 60.5}}","nodes":[]},{"class":"Label","attributes":{"font_size":17,"enabled":true,"text":"Save details?","flex":"","name":"label2","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","text_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","alignment":"left","uuid":"BDC13868-DD31-43CB-AA50-0221555EDDBC"},"frame":"{{44, 253}, {109, 32}}","nodes":[]},{"class":"Switch","attributes":{"name":"save_details","value":true,"uuid":"ABF47BAD-62AB-48DD-AF19-E122AB7ABCDD","enabled":true,"border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","flex":""},"frame":"{{161, 254}, {51, 31}}","nodes":[]},{"class":"Button","attributes":{"font_size":17,"enabled":true,"flex":"","font_bold":false,"name":"next_button","uuid":"437E01A9-6CD9-4779-A2B7-D400559377DF","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","border_width":1,"action":"next_tapped","image_name":"ionicons-ios7-arrow-right-32","title":"Next"},"frame":"{{44, 395.5}, {450.5, 104}}","nodes":[]},{"class":"TextView","attributes":{"alignment":"center","autocorrection_type":"no","font_size":15,"border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","enabled":true,"flex":"","text":"Note: Saving details is useful if you don't want to enter your details again in the future but otherwise it's not necessary.","text_color":"RGBA(0.795918,0.834184,0.857143,1.000000)","name":"textview1","spellchecking_type":"no","editable":false,"uuid":"3E3E0252-B1D3-4922-B574-6CF98E264093"},"frame":"{{44, 293}, {450.5, 47}}","nodes":[]},{"class":"Button","attributes":{"image_name":"ionicons-close-circled-24","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","font_size":15,"title":"","enabled":true,"tint_color":"RGBA(0.642857,0.642857,0.642857,1.000000)","flex":"","action":"clear_tapped","font_bold":false,"alpha":0.7000000000000001,"name":"zu_button","uuid":"1BCD9A09-9942-4B3E-8CCF-6D23D8064531"},"frame":"{{469.5, 135.5}, {20, 20}}","nodes":[]},{"class":"Button","attributes":{"image_name":"ionicons-close-circled-24","border_color":"RGBA(0.000000,0.000000,0.000000,1.000000)","font_size":15,"title":"","enabled":true,"tint_color":"RGBA(0.642857,0.642857,0.642857,1.000000)","flex":"","action":"clear_tapped","font_bold":false,"alpha":0.7000000000000001,"name":"zp_button","uuid":"3FE1362A-A9AB-40F0-9F4C-614837AEBFD8"},"frame":"{{469.5, 206}, {20, 20}}","nodes":[]}]}]}]"""

def fix_quotes_out(s):
    return s.replace("\\\"\\\"\\\"", "\"\"\"").replace("\\\\", "\\")

def main():
    if os.path.exists(NAME + ".py"):
        console.alert("Failed to Extract", NAME + ".py already exists.")
        return
    
    if os.path.exists(NAME + ".pyui"):
        console.alert("Failed to Extract", NAME + ".pyui already exists.")
        return
    
    with open(NAME + ".py", "w") as f:
        f.write(fix_quotes_out(PYFILE))
    
    with open(NAME + ".pyui", "w") as f:
        f.write(fix_quotes_out(PYUIFILE))
    
    msg = NAME + ".py and " + NAME + ".pyui were successfully extracted!"
    console.alert("Extraction Successful", msg, "OK", hide_cancel_button=True)
    
if __name__ == "__main__":
    main()
