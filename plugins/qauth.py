# coding: utf-8
from commands import Command
import datetime

class QAuth(Command):
	def __init__(self):
		self.bot = None
		self.client = None
		self.server = None

	def on_connected(self, event):
		self.bot = event['bot']
		self.client = event['client']
		self.server = event['client'].server

		if self.bot.settings.qauth:
			qauth = self.bot.settings.qauth
			print "Sending AUTH %s %s" % (qauth[0], qauth[1])
			self.client.tell('q@cserve.quakenet.org','AUTH %s %s' % (qauth[0], qauth[1]))
			self.client.send('MODE %s +x' % self.server.mynick)
			self.bot.add_timer(datetime.timedelta(seconds=15), False, self.de_deferr)

	def de_deferr(self):
		print "Dedeferrig joins"
		self.bot.settings.deferred_join_swarm = False
