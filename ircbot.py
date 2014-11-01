import re
import sys
import traceback
import datetime
from copy import copy
from heapq import heappush, heappop
from autoreloader.autoreloader import AutoReloader

import plugin_handler
import error_handler
from ircclient import ircclient

# Call plugins_on_load only on first import
try:
	IRCBot
except NameError:
	plugin_handler.plugins_on_load()

class PriorityQueue:
	def __init__(self):
		self.internal_array = []

	def clear(self):
		self.internal_array = []

	def push(self, item):
		heappush(self.internal_array, item)

	def pop(self):
		return heappop(self.internal_array)

	def empty(self):
		return len(self.internal_array) == 0

	def top(self):
		return self.internal_array[0]

	def delete_by_id(self, id):
		for i in range(len(self.internal_array)):
			if self.internal_array[i].id == id:
				self.internal_array[i] = self.internal_array[-1]
				self.internal_array.pop()
				heapq._siftup(self.internal_array, i)
				return True
		return False




class TimedEvent:
	def __init__(self, trigger_delta, recurring, target, id, args):
		self.trigger_delta = trigger_delta
		self.trigger_time = datetime.datetime.now() + trigger_delta
		self.recurring = recurring
		self.target = target
		self.args = args
		self.id = id

	def trigger(self):
		self.target(*self.args)

	def reset(self):
		self.trigger_time += self.trigger_delta

	def __cmp__(self, other):
		return cmp(self.trigger_time, other.trigger_time)

class IRCBot(AutoReloader):
	def __init__(self, settings):
		self.settings = settings
		self.callbacks = self.get_callbacks()
		self.clients = {}
		self.networks = []
		self.plugins = []
		self.timer_heap = PriorityQueue()
		self.next_timer_beat = None
		self.need_reload = {}
		self.timer_id = 0

		for network in self.settings.networks:
			net_settings = self.settings.networks[network]
			print "Connecting to network %s at %s:%s..." % (network,
			      net_settings['server_address'], net_settings['server_port'])
			self.clients[network] = ircclient.IRCClient(net_settings['server_address'],
								    net_settings['server_port'],
								    net_settings['nick'],
								    net_settings['username'],
								    net_settings['realname'],
								    network,
								    net_settings.setdefault('server_password'))
			self.clients[network].callbacks = copy(self.callbacks)
			self.networks.append(network)

	def get_callbacks(self):
		return { "on_connected": self.on_connected, "on_join": self.on_join,
			 "on_nick_change": self.on_nick_change, "on_notice": self.on_notice,
			 "on_part": self.on_part, "on_privmsg": self.on_privmsg,
			 "on_mode": self.on_mode, "on_quit": self.on_quit, "debug_info": self.debug_info }

	def is_connected(self, network=None):
		if network == None:
			raise DeprecationWarning("network parameter missing")
		return self.clients['networks'].is_connected()

	def execute_plugins(self, network, trigger, *arguments):
		for plugin in plugin_handler.all_plugins():
			try:
				if plugin.__class__.__dict__.has_key(trigger):
					# FIXME this is rather ugly, for compatiblity with pynik
					if plugin.__class__.__dict__[trigger].func_code.co_argcount == len(arguments) + 2:
						plugin.__class__.__dict__[trigger](plugin, self, *arguments) # Call without network
					elif plugin.__class__.__dict__[trigger].func_code.co_argcount == len(arguments) + 3:
						plugin.__class__.__dict__[trigger](plugin, self, *arguments, **{'network': network})
					else:
						raise NotImplementedError("Plugin '%s' argument count missmatch, was %s." % (
								plugin, plugin.__class__.__dict__[trigger].func_code.co_argcount))
			except:
				messages = ['','EXCEPTION:']
				messages.append("%s %s %s" % (network, plugin, sys.exc_info()))
				for row in [[tb[0]+':'+str(tb[1])]+[str(z) for z in tb[2:]] for tb in traceback.extract_tb(sys.exc_info()[2])]:
					messages.append(row)
				messages.append('')

				for message in messages:
					error_handler.output_message(message)
				# error_handler.output_message("*** EXCEPTION ***\n%s %s Plugin '%s' threw exception\nexinfo: '%s'\n" % (
				# 		datetime.datetime.now().strftime("[%H:%M:%S]"),
				# 		network,
				# 		plugin,
				# 		sys.exc_info()

				# 	))
				# error_handler.output_message([tb[0]+':'+str(tb[1])+"\n\t"+"\n\t".join([str(z) for z in tb[2:]]) for tb in traceback.extract_tb(sys.exc_info()[2])])

				if False and trigger != "timer_beat":
					try:
						self.tell(self.settings.admin_network, self.settings.admin_channel,
							  "%s %s Plugin '%s' threw exception, exinfo: '%s', traceback: '%s'" % (
								datetime.datetime.now().strftime("[%H:%M:%S]"), network,
								plugin, sys.exc_info(), traceback.extract_tb(sys.exc_info()[2])[::-1]))
					except:
						error_handler.output_message("%s %s Unable to send exception to admin channel, exinfo: '%s', traceback: '%s'" % (
								datetime.datetime.now().strftime("[%H:%M:%S]"), network,
								sys.exc_info(), traceback.extract_tb(sys.exc_info()[2])))

	def on_connected(self, network):
		self.execute_plugins(network, "on_connected")

	def on_join(self, network, nick, channel):
		self.execute_plugins(network, "on_join", nick, channel)

	def on_nick_change(self, network, old_nick, new_nick):
		self.execute_plugins(network, "on_nick_change", old_nick, new_nick)

	def on_notice(self, network, nick, target, message):
		self.execute_plugins(network, "on_notice", nick, target, message)

	def on_part(self, network, nick, channel, reason):
		self.execute_plugins(network, "on_part", nick, channel, reason)

	def on_privmsg(self, network, nick, target, message):
		self.execute_plugins(network, "on_privmsg", nick, target, message)

	def on_quit(self, network, nick, reason):
		self.execute_plugins(network, "on_quit", nick, reason)

	def on_mode(self, network, nick, channel, mode, target):
		self.execute_plugins(network, "on_mode", nick, channel, mode, target)

	def debug_info(self, *argv):

		for network in self.settings.networks.keys():
			if network in self.networks:
				client = self.clients[network]
				print "(net) name: %s" % client.net.name
				print "(net) nick: %s" % client.net.mynick
				print "(net) channels: %d" % len(client.net.all_channels)
				print "(net) known users: %d" % len(client.net.all_users)

				for channel in client.net.all_channels:
					print "(%s) users: %d" % (channel.name, len(channel.user_list))
					print "(%s) bans: %d" % (channel.name, len(channel.ban_list))
					for ban in channel.ban_list:
						print "(%s)\t * %s (%s @%s)" % (channel.name, ban.banmask, ban.banner_nick, ban.timestamp)




		self.execute_plugins(None, "debug_info");

	def on_reload(self):
		# Check for new channels, if so join them
		for network in self.networks:
			for channel in self.settings.networks[network]['channels']:
				try:
					self.join(network, channel[0], channel[1])
				except IndexError:
					self.join(network, channel[0])

		# Connect to new networks
		for network in self.settings.networks:
			if network not in self.networks:
				net_settings = self.settings.networks[network]
				print "Connecting to new network %s at %s:%s..." % (network,
				      net_settings['server_address'], net_settings['server_port'])
				self.clients[network] = ircclient.IRCClient(net_settings['server_address'],
									    net_settings['server_port'],
									    net_settings['nick'],
									    net_settings['username'],
									    net_settings['realname'],
									    network)
				self.clients[network].callbacks = copy(self.callbacks)
				self.networks.append(network)

	def reload(self):
		self.need_reload['main'] = True
		self.need_reload['ircbot'] = True

	def reload_plugins(self):
		plugin_handler.plugins_on_unload()
		plugin_handler.reload_plugin_modules()
		plugin_handler.plugins_on_load()

	def load_plugin(self, plugin):
		plugin_handler.load_plugin(plugin)

	def join(self, network, channel, password=""):
		return self.clients[network].join(channel, password)

	def send(self, network, line=None):
		if line == None:
			raise DeprecationWarning("network parameter missing")
		return self.clients[network].send(line)

	def send_all_networks(self, line):
		for client in self.clients.values():
			if client.is_connected():
				client.send(line)

	def tell(self, network, target, message=None):
		if message == None:
			raise DeprecationWarning("network parameter missing")
		return self.clients[network].tell(target, message)

	def tick(self):
		# Do reload if necassary
		if self.need_reload.get('ircbot'):
			reload(ircclient)
			reload(plugin_handler)
			self.callbacks = self.get_callbacks()
			for client in self.clients.values():
				client.callbacks = copy(self.callbacks)

			self.need_reload['ircbot'] = False

		# Call timers
		now = datetime.datetime.now()
		while not self.timer_heap.empty() and self.timer_heap.top().trigger_time <= now:
			timer = self.timer_heap.pop()
			timer.trigger()
			if timer.recurring:
				timer.reset()
				self.timer_heap.push(timer)

		for client in self.clients.values():
			client.tick()

		# Call timer_beat in all networks every 1 second
		if not self.next_timer_beat or self.next_timer_beat < now:
			self.next_timer_beat = now + datetime.timedelta(0, 1)
			for network in self.networks:
				self.execute_plugins(network, "timer_beat", now)

	def add_timer(self, delta, recurring, target, *args):
		self.timer_id += 1
		timer = TimedEvent(delta, recurring, target, self.timer_id, args)

		self.timer_heap.push(timer)

		return self.timer_id

