# coding: utf-8
from commands import Command
from ll_utils import LLUtils
import hashlib
from random import randrange
import datetime
import time

class Fenrus(Command):
	def __init__(self):
		self.bot = None

		self.Util = LLUtils()
		self.Settings = self.Util.Settings

		self.master_channel = '#dreamhack.crew'
		self.slave_channels = ['#dreamhack', '#dreamhack.info']

		self.last_sync_time = 0

	def on_connected(self, bot, network, **kwargs):
		self.bot = bot
		self.Swarm = self.bot.swarm
		self.client = bot.clients[network]
		self.net = self.client.net

	# if someone joins the master chan (and it isn't us) we should
	# voice them in all the slave channels.
	def on_join(self, bot, userhost, channel, network, **kwargs):
		if  channel != self.master_channel:
			return
		targetnick = self.Util.extract_nick(userhost)
		# print "(fenrus) %s joined masterchannel (%s)" % (targetnick, channel)

		if targetnick == self.net.mynick:
			delay = float(randrange(1200, 3000)/10)
			self.bot.add_timer(datetime.timedelta(0, delay), False, self.sync_channels)
		else:
			if self.Settings.swarm_enabled:
				m = hashlib.md5()
				m.update(targetnick)
				hashid = int(m.hexdigest()[0:2],16)
				if not self.Swarm.range[0] <= hashid < self.Swarm.range[1]:
					# print "(fenrus) ESCAPINg hashid: %s swarm-range: %s-%s" % (hashid, self.Swarm.range[0], self.Swarm.range[1])
					return False
				# print "(fenrus) EXECUTING hashid: %s swarm-range: %s-%s" % (hashid, self.Swarm.range[0], self.Swarm.range[1])

			for slave_channel_name in self.slave_channels:
				print "(fenrus) slave_channel_name: %s" % slave_channel_name
				try:
					slave_channel = self.net.channel_by_name(slave_channel_name)
					if not slave_channel.has_nick(targetnick):
						# print "(fenrus) %s not in %s" % (targetnick, slave_channel_name)
						continue
					flags = slave_channel.get_flags(targetnick)
					# print "(fenus) flags: %s" % flags
				except Exception, e:
					print "(fenrus) EXCEPTION: %s: %s" % (e.__class__.__name__, e)
					return

				if not flags or ("+" not in flags and "@" not in flags):
					# print "(fenrus) *** voice *** %s in %s" % (targetnick, slave_channel_name)
					self.client.send('MODE %s +v %s' % (slave_channel_name, targetnick))
				# else:
				# 	print "(fenrus) no action, %s has %s in %s" % (targetnick, flags, slave_channel_name)

	def sync_channels(self):
		print "(fenrus) sync_channels"
		delay = float(randrange(3000, 12000)/10)
		self.bot.add_timer(datetime.timedelta(0, delay), False, self.sync_channels)

		# don't sync too often
		if time.time() - self.last_sync_time < 300:
			return
		self.last_sync_time = time.time()

		try:
			master_channel = self.net.channel_by_name(self.master_channel)
			master_users = master_channel.user_list
		except Exception, e:
			print "(fenrus) ERROR: %s" % e
			return

		for master_user in master_users:
			for slave_channel_name in self.slave_channels:
				slave_channel = self.net.channel_by_name(slave_channel_name)
				if not slave_channel.has_nick(master_user.nick):
					# print "(fenrus) %s not in %s" % (master_user.nick, slave_channel_name)
					continue
				# print "(fenrus) master_user.channel_flags(%s): %s" % (slave_channel_name, master_user.channel_flags(slave_channel_name))
				flags = master_user.channel_flags(slave_channel_name)
				if not flags or ("+" not in flags and "@" not in flags):
					#print "(fenrus) *** voice *** %s in %s" % (master_user.nick, slave_channel_name)
					self.client.send('MODE %s +v %s' % (slave_channel_name, master_user.nick))
				# else:
				# 	print "(fenrus) no action, %s has %s in %s" % (master_user.nick, flags, slave_channel_name)















