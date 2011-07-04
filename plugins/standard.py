# coding: utf-8
import re
import random

from commands import Command

class EchoCommand(Command): 
	def __init__(self):
		pass
	
	def trig_echo(self, bot, source, target, trigger, argument):
		return argument

class HelloCommand(Command): 
	def __init__(self):
		pass
	
	def trig_hello(self, bot, source, target, trigger, argument):
		return "Hello there, %s!" % source

class PickCommand(Command): 
	def __init__(self):
		pass
	
	def trig_pick(self, bot, source, target, trigger, argument):
		choices = argument.split(" or ")
		choices = map(lambda x: x.strip(), choices)
		choices = filter(lambda choice: len(choice), choices)

		#print choices

		if choices:
			responses = ["Hm... Definitely not %s.", "%s!", "I say... %s!", "I wouldn't pick %s...", "Perhaps %s..."]
			choice = random.choice(choices)
			response = random.choice(responses)
			
			return response % choice
		else:
			return None


class TimeCommand(Command):
	def trig_time(self, bot, source, target, trigger, argument):
		import datetime
		return datetime.datetime.now().strftime("%y%m%d-%H%M%S - %H:%M:%S %a %d %b w:%V")

	def trig_date(self, bot, source, target, trigger, argument):
		return self.trig_time(bot, source, target, trigger, argument)

class WeekCommand(Command):
	def trig_week(self, bot, source, target, trigger, argument):
		import datetime
		return "Current week: %d." % (int(datetime.datetime.now().strftime("%V")))

def is_trigger(name):
	m = re.search('^trig_.+', name)
	if m:
		return True
	else:
		return False

def remove_first_five(text):
	return text[5:]

class CommandsCommand(Command):
	def trig_commands(self, bot, source, target, trigger, argument):
		triggers = []
		for command in Command.__subclasses__():
			for trigger in command.triggers:
				if trigger not in triggers:
					triggers.append(trigger)

			l = command.__dict__
			l = filter(is_trigger, l)
			l = map(remove_first_five, l)

			for trigger in l:
				if trigger not in triggers:
					triggers.append(trigger)
		
		return "Commands: %s" % ", ".join(sorted(triggers))

class HelpCommand(Command):
	def trig_help(self, bot, source, target, trigger, argument):
		"""Help command. Use it to get information about other commands."""
		trigger_found = False
		for command in Command.__subclasses__():
			fname = "trig_" + argument
			if fname in command.__dict__:
				trigger_found = True
				f = command.__dict__[fname]
				if f.__doc__:
					return "%s: %s" % (argument, f.__doc__)
		
		if trigger_found:
			return "I can offer nothing."
		else:
			return "That's not a command! Try `help <command>`"

class AAOCommand(Command):
	triggers = ['}{|', '\xe5\xe4\xf6', 'åäö']

	def on_trigger(self, bot, source, target, trigger, argument):
			if trigger == '\xe5\xe4\xf6':
				return source + u": Du använder nog Latin-1 (Testa .sayaao)"
			elif trigger == '}{|':
				return source + u": Du använder nog ISO-646 (Testa .sayaao)"
			else:
				return source + u": Du använder nog UTF-8 (Testa .sayaao)"

