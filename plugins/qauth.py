# coding: utf-8
from commands import Command
import datetime

class QAuth(Command):
	def __init__(self):
		self.bot = None
		self.client = None
		self.net = None

	def on_connected(self, bot, network, **kwargs):
		self.bot = bot
		self.client = bot.clients[network]
		self.net = self.client.net

		if self.bot.settings.qauth:
			qauth = self.bot.settings.qauth
			print "Sending AUTH %s %s" % (qauth[0], qauth[1])
			self.client.tell('q@cserve.quakenet.org','AUTH %s %s' % (qauth[0], qauth[1]))
			self.client.send('MODE %s +x' % self.net.mynick)
			self.bot.add_timer(datetime.timedelta(seconds=15), False, self.de_deferr)

	def de_deferr(self):
		print "Dedeferrig joins"
		self.bot.settings.deferred_join = False
