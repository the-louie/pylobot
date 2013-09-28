# coding: utf-8
import re
import sys
from plugins import Plugin
import favorites
import commands
import utility
import traceback
import settings

import error_handler

class CommandCatcherPlugin(Plugin):
	hooks = ['on_privmsg']

	def __init__(self):
		pass

	def on_command(self, bot, source, target, trigger, arguments, network):
		meth_name = 'trig_' + trigger.lower()
		pairs = []

		for command_class in commands.Command.__subclasses__():
			import __builtin__
			meth = None
			try:
				meth = command_class.instance.__getattribute__(meth_name)
				pairs.append([command_class.instance, meth])
			except:
				pass

		for command in commands.get_commands_by_trigger(trigger):
			pairs.append([command, command.on_trigger])

		for pair in pairs:
			command, method = pair

			if command.can_trigger(source, trigger):
				m = re.search('^(.+)!', source)
				if m:
					if target == source:
						target = m.group(1)
					source = m.group(1)

				try:
					# FIXME this is rather ugly, for compatiblity with pynik
					if method.im_func.func_code.co_argcount == 7:
						ret = utility.timeout(method, 10, (bot, source, target, trigger, arguments), {'network': network})
					elif method.im_func.func_code.co_argcount == 6:
						ret = utility.timeout(method, 10, (bot, source, target, trigger, arguments))
					else:
						raise NotImplementedError("Trigger '%s' argument count missmatch, was %s." % (
								trigger, method.im_func.func_code.co_argcount))
					return ret
				except utility.TimeoutException:
					return "Command '%s' took too long to execute." % trigger
				except MemoryError:
					return "Command '%s' used to much memory." % trigger
				except:
					error_handler.output_message("Error triggered by '%s' with command '%s', exinfo: '%s', traceback: '%s'" % (
							source, trigger, sys.exc_info(), traceback.extract_tb(sys.exc_info()[2])))

					# try:
					# 	bot.tell(bot.settings.admin_network, bot.settings.admin_channel,
					# 		 "%s triggered an error by typing '%s %s': %s, tb: %s." % (
					# 			source, trigger, arguments,
					# 			sys.exc_info(), traceback.extract_tb(sys.exc_info()[2])[::-1]))
					# except:
					# 	error_handler.output_message("%s %s Unable to send exception to admin channel, exinfo: '%s', traceback: '%s'" % (
					# 		datetime.datetime.now().strftime("[%H:%M:%S]"), network,
					# 		sys.exc_info(), traceback.extract_tb(sys.exc_info()[2])))

					return "Oops. Error logged."
			else:
				return "Bwaha. You can't trigger that!"

		if not len(pairs):
			if trigger in favorites.FavoriteCommands.instance.favorites.keys():
				return favorites.FavoriteCommands.instance.trig_fav(bot, source, target, 'fav', trigger + ' ' + arguments)

	def on_privmsg(self, bot, source, target, message, network, **kwargs):
		m = re.match(r'^(\S)((\S+)\s?(.*?))$', message)
		if m and m.group(1) == bot.settings.trigger:
			body = m.group(2)
			if body[0] == '(':
				trigger = "lisp"
				arguments = body
			else:
				trigger = m.group(3)
				arguments = m.group(4)

			ret = self.on_command(bot, source, target, trigger, arguments, network)
			if ret:
				if type(ret) is not list:
					ret = [ret]

				for ret_str in ret:
						m = re.search('^(.+)!', source)
						if m:
							if target == source:
								target = m.group(1)

						bot.tell(network, target, ret_str)


	def on_load(self):
		pass

	def on_unload(self):
		pass
