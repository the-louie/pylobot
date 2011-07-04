# coding: utf-8
import random

import utility
from commands import Command

class InsultCommand(Command):
	def __init__(self): 
		pass 

	def trig_insult(self, bot, source, target, trigger, argument):
		t = argument.strip()
		if not t:
			t = source

		insult = random.sample(self.insults, 1)[0]
		try:
			return insult.replace('%s', t)
		except:
			return "We all know %s sucks, but so does the insult I tried to use." % t

	def trig_addinsult(self, bot, source, target, trigger, argument):
		if not "%s" in argument:
			return "Trying to add an improper insult, booo!"
		elif argument in self.insults:
			return "That insult already exists!"
		self.insults.append(argument)
		self.save()
		return "Added insult: %s" % argument.replace('%s', source)

	def save(self):
		utility.save_data("insults", self.insults)

	def on_load(self):
		self.insults = utility.load_data("insults", [])

	def on_unload(self): 
		self.insults = None
