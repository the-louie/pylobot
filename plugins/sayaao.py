# coding: utf-8
from commands import Command
class SayAAOCommand(Command):
	
	def trig_sayaao(self, bot, source, target, trigger, argument, network):
		bot.tell(network, target, u"Detta är UTF-8 åäöÅÄÖ.".encode("UTF-8"))
		bot.tell(network, target, u"och detta är ISO-8859-1 åäöÅÄÖ.".encode("ISO-8859-1"))
		return None
