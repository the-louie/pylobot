# coding: utf-8
from commands import Command
import datetime

class AutoJoin(Command):
	def __init__(self):
		self.bot = None

	def on_connected(self, event):
		self.bot = event['bot']
		self.join_all_channels()

	def join_all_channels(self):
		if self.bot.settings.deferred_join_all:
			self.bot.add_timer(datetime.timedelta(seconds=10), False, self.join_all_channels)
			return

		for channel in self.bot.settings.server['channels']:
			if len(channel) == 2:
				self.bot.join(channel[0], channel[1])
			elif len(channel) == 1:
				self.bot.join(channel[0])
