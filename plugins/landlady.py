# coding: utf-8

from commands import Command
from ll_utils import *

class Landlady(Command):
	def __init__(self):
		pass

	""" 
		Take care of any incoming kick-ban requests
	"""
	def trig_kb(self, bot, source, target, trigger, argument, network):
		(cmd,reason,targetnick,bantime) = parse_kb_arguments(argument,source)
		if not reason:
			print "UNKOWN KB: %s,%s,%s,%s,%s." % (source,target,trigger,argument,network)
			return None

		# FIXME: is it mine to take care of?

		# Get a banmask that's unique
		banmask = create_banmask(bot.clients[network], targetnick)

		# FIXME: add punishfactor

		# Kickban the user
		kickban(bot, network, banmask)

		return "%s|%s|%s" % (targetnick,banmask,reason)


	def save(self): 
		pass

	def on_load(self):
		pass

	def on_unload(self): 
		pass