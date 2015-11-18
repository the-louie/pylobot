# coding: utf-8
from commands import Command
import datetime
import logging
logger = logging.getLogger('landlady')

class AutoJoin(Command):
	def __init__(self):
		self.bot = None

	def on_connected(self, event):
		self.bot = event['bot']
		self.join_all_channels()

	def join_all_channels(self):
		if self.bot.client.deferred_join_all:
			logger.debug("(AutoJoin:join_all_channels) Joining defered, checking in 10s.")
			self.bot.add_timer(datetime.timedelta(seconds=10), False, self.join_all_channels)
			return

		logger.debug("(AutoJoin:join_all_channels) Joining channels:")
		for channel in self.bot.settings.server['channels']:
			if len(channel) == 2:
				logger.debug("(AutoJoin:join_all_channels)\t* %s (%s)" % (channel[0], channel[1]))
				self.bot.join(channel[0], channel[1])
			elif len(channel) == 1:
				logger.debug("(AutoJoin:join_all_channels)\t* %s" % (channel[0],))
				self.bot.join(channel[0])
