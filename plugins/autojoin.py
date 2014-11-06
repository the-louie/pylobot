# coding: utf-8
from commands import Command
import datetime

class AutoJoin(Command):
	def __init__(self):
		self.bot = None

	def on_connected(self, event):
		self.bot = event['bot']
		self.join_all_channels(event['client'].net.name)

	def join_all_channels(self, network):
		if self.bot.settings.deferred_join:
			self.bot.add_timer(datetime.timedelta(seconds=10), False, self.join_all_channels, network)
			return

		for channel in self.bot.settings.networks[network]['channels']:
			if len(channel) == 2:
				self.bot.join(network, channel[0], channel[1])
			elif len(channel) == 1:
				self.bot.join(network, channel[0])
