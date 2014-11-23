# coding: utf-8
from commands import Command

class Snow(Command):
	def __init__(self):
		self.op_channel = '#dreamhack.op2'
		self.output_channel = '#dreamhack.c&c'

	def on_privmsg(self, event):
        """
        Expose some functions
        """
        client = event['client']
        source = event['source']
        target = event['target']
        message = event['message']

        if source is None:
        	return None
        if target[1] == '#':
        	return None

        if source_nick.in_channel(self.op_channel):
        	return

        output = "<%s> %s" % (source.nick, message)
        client.tell(self.output_channel, output)
