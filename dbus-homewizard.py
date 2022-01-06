#! /usr/bin/python3 -u

import dbus
import os
import requests
import sys

from argparse import ArgumentParser
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

# Victron packages
sys.path.insert(1, os.path.join(os.path.dirname(__file__), './ext/velib_python'))
from vedbus import VeDbusService
from ve_utils import exit_on_error

import logging
log = logging.getLogger()

NAME = os.path.basename(__file__)
VERSION = '0.1'

# We define these classes to avoid connection sharing to dbus. This is to allow
# more than one service to be held by a single python process.
class SystemBus(dbus.bus.BusConnection):
	def __new__(cls):
		return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SYSTEM)

class SessionBus(dbus.bus.BusConnection):
	def __new__(cls):
		return dbus.bus.BusConnection.__new__(cls, dbus.bus.BusConnection.TYPE_SESSION)

def dbusConnection():
	return SessionBus() if 'DBUS_SESSION_BUS_ADDRESS' in os.environ else SystemBus()

class EnergyMeter(object):
	""" Represent a meter object on dbus. """

	def __init__(self, base, host):
		# Get static data
		json = requests.get('http://{}/api'.format(host)).json()
		serial = json['serial']

		self.host = host
		self.service = service = VeDbusService(
			"{}.homewizard_{}".format(base, serial), bus=dbusConnection())

		# Add objects required by ve-api
		service.add_path('/Mgmt/ProcessName', NAME)
		service.add_path('/Mgmt/ProcessVersion', VERSION)
		service.add_path('/Mgmt/Connection', host)
		service.add_path('/DeviceInstance', 0)
		service.add_path('/ProductId', 0xFFFF)
		service.add_path('/ProductName', "HomeWizard - {}".format(json['product_type']))
		service.add_path('/FirmwareVersion', json['firmware_version'])
		service.add_path('/Serial', serial)
		service.add_path('/Connected', 1)

		_kwh = lambda p, v: ('{:.2f}kWh'.format(v))
		_a = lambda p, v: (str(v) + 'A')
		_w = lambda p, v: (str(v) + 'W')
		_v = lambda p, v: (str(v) + 'V')
		_m3 = lambda p, v: (str(v) + 'm3')

		# Grid data
		service.add_path('/Ac/Energy/Forward', None, gettextcallback=_kwh)
		service.add_path('/Ac/Energy/Reverse', None, gettextcallback=_kwh)
		service.add_path('/Ac/L1/Current', None, gettextcallback=_a)
		service.add_path('/Ac/L1/Energy/Forward', None, gettextcallback=_kwh)
		service.add_path('/Ac/L1/Energy/Reverse', None, gettextcallback=_kwh)
		service.add_path('/Ac/L1/Power', None, gettextcallback=_w)
		service.add_path('/Ac/L1/Voltage', None, gettextcallback=_v)
		service.add_path('/Ac/L2/Current', None, gettextcallback=_a)
		service.add_path('/Ac/L2/Energy/Forward', None, gettextcallback=_kwh)
		service.add_path('/Ac/L2/Energy/Reverse', None, gettextcallback=_kwh)
		service.add_path('/Ac/L2/Power', None, gettextcallback=_w)
		service.add_path('/Ac/L2/Voltage', None, gettextcallback=_v)
		service.add_path('/Ac/L3/Current', None, gettextcallback=_a)
		service.add_path('/Ac/L3/Energy/Forward', None, gettextcallback=_kwh)
		service.add_path('/Ac/L3/Energy/Reverse', None, gettextcallback=_kwh)
		service.add_path('/Ac/L3/Power', None, gettextcallback=_w)
		service.add_path('/Ac/L3/Voltage', None, gettextcallback=_v)
		service.add_path('/Ac/Power', None, gettextcallback=_w)

		# Additional data
		service.add_path('/Meter/Model', None)
		service.add_path('/Meter/Version', None)
		service.add_path('/Gas/Usage', None, gettextcallback=_m3)
		service.add_path('/Gas/Timestamp', None)

		GLib.timeout_add(1000, exit_on_error, self._handletimertick)

	# Called on a one second timer
	def _handletimertick(self):
		json = requests.get('http://{}/api/v1/data'.format(self.host)).json()
		self.update(json)
		return True  # keep timer running

	def set_path(self, path, value):
		if self.service[path] != value:
			self.service[path] = value

	def update(self, json):
		self.set_path('/Ac/Energy/Forward', json['total_power_import_t1_kwh'] + json['total_power_import_t2_kwh'])
		self.set_path('/Ac/Energy/Reverse', json['total_power_export_t1_kwh'] + json['total_power_export_t2_kwh'])
		self.set_path('/Ac/Power', json['active_power_w'])
		self.set_path('/Ac/L1/Power', json['active_power_l1_w'])
		self.set_path('/Ac/L2/Power', json['active_power_l2_w'])
		self.set_path('/Ac/L3/Power', json['active_power_l3_w'])
		self.set_path('/Gas/Usage', json['total_gas_m3'])
		self.set_path('/Gas/Timestamp', json['gas_timestamp'])
		self.set_path('/Meter/Model', json['meter_model'])
		self.set_path('/Meter/Version', json['smr_version'])

def main():
	parser = ArgumentParser(add_help=True)
	parser.add_argument('-d', '--debug', help='Enable debug logging', action='store_true')
	parser.add_argument('host', help='Hostname or IP address of HomeWizard device')
	parser.add_argument('--servicebase',
		   help='Base service name on dbus, default is com.victronenergy',
		   default='com.victronenergy.grid')

	args = parser.parse_args()

	logging.basicConfig(format='%(levelname)-8s %(message)s',
						level=(logging.DEBUG if args.debug else logging.INFO))

	# Have a mainloop, so we can send/receive asynchronous calls to and from dbus
	DBusGMainLoop(set_as_default=True)

	meter = EnergyMeter(args.servicebase, args.host)

	# Start and run the mainloop
	mainloop = GLib.MainLoop()
	mainloop.run()

if __name__ == '__main__':
	main()
