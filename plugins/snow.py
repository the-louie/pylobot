# coding: utf-8
from commands import Command

class Snow(Command):
	def __init__(self):
		self.op_channel = '#dreamhack.op2'
		self.swarm_channel = '#dreamhack.swarm'
		self.output_channel = '#dreamhack.c&c'

	def on_privmsg(self, event):
		"""
		Expose some functions
		"""
		client = event['client']
		source = event['source']
		target = event['target']
		message = event['message']

		if source is None: # unknown source, unknown error
			return None
		if target is not None: # target isn't me
			return None

		if source.in_channel(self.op_channel) or source.in_channel(self.swarm_channel): # it's an op or a bot
			return

		output = "<%s> %s" % (source.nick, message)
		client.tell(self.output_channel, output)
