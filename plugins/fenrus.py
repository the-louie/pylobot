# coding: utf-8
from commands import Command
from ll_utils import LLUtils
import hashlib
from random import randrange
import datetime
import time
import logging
logger = logging.getLogger('landlady')

class Fenrus(Command):
	def __init__(self):
		self.bot = None

		self.master_channel = '#dreamhack.crew'
		self.slave_channels = ['#dreamhack', '#dreamhack.info']

		self.last_sync_time = 0

	def on_connected(self, event):
		self.client = event['client']
		self.bot = event['bot']
		self.swarm = self.client.swarm
		self.server = self.client.server

	# if someone joins the master chan (and it isn't us) we should
	# voice them in all the slave channels.
	def on_join(self, event):
		bot_obj = event['bot']
		netw_obj = event['client'].server
		chan_obj = event['channel']
		user_obj = event['user']

		if  chan_obj.name != self.master_channel:
			return
		targetnick = user_obj.nick

		logger.debug("(fenrus) %s joined masterchannel (%s)", targetnick, chan_obj.name)

		if targetnick == netw_obj.mynick:
			delay = float(randrange(1200, 3000)/10)
			bot_obj.add_timer(datetime.timedelta(0, delay), False, self.sync_channels)
		else:
			if self.swarm.enabled and not self.swarm.nick_matches(targetnick):
				return False

			for slave_channel_name in self.slave_channels:
				logger.debug("(fenrus) slave_channel_name: %s", slave_channel_name)
				try:
					slave_channel = netw_obj.channel_by_name(slave_channel_name)
					if not slave_channel.has_nick(targetnick):
						continue
					flags = slave_channel.get_flags(targetnick)
				except Exception, e:
					logger.error("(fenrus) EXCEPTION: %s: %s", e.__class__.__name__, e)
					return

				if not flags or ("+" not in flags and "@" not in flags):
					self.client.send('MODE %s +v %s' % (slave_channel_name, targetnick))

	def sync_channels(self):
		logger.debug("(fenrus) sync_channels")
		delay = float(randrange(3000, 12000)/10)
		self.bot.add_timer(datetime.timedelta(0, delay), False, self.sync_channels)
		# don't sync too often
		if time.time() - self.last_sync_time < 300:
			return
		self.last_sync_time = time.time()

		try:
			master_channel = self.server.channel_by_name(self.master_channel)
			master_users = master_channel.user_list
		except Exception, e:
			logger.error("(fenrus) %s %s", e.__class__.__name__, e)
			return

		for master_user in master_users:
			if self.swarm.enabled and not self.swarm.nick_matches(master_user.nick):
				continue

			for slave_channel_name in self.slave_channels:
				slave_channel = self.server.channel_by_name(slave_channel_name)
				if not slave_channel.has_op(self.server.mynick):
					continue
				if not slave_channel.has_nick(master_user.nick):
					continue
				flags = master_user.channel_flags(slave_channel_name)
				if not flags or ("+" not in flags and "@" not in flags):
					self.client.send('MODE %s +v %s' % (slave_channel_name, master_user.nick))















