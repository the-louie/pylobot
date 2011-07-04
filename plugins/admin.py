# coding: utf-8
import utility
from commands import Command

class RawCommand(Command):
	def trig_raw(self, bot, source, target, trigger, argument, network):
		if utility.has_admin_privileges(source, target):
			bot.send(network, argument)

class CollectCommand(Command):
	def trig_collect(self, bot, source, target, trigger, argument):
		import gc
		obj_count = 0
		if True:
			objects = gc.get_objects()
			obj_count = len(objects)
			types = {}
			for o in objects:
				t = type(o)

				if t in types:
					types[t] += 1
				else:
					types[t] = 1

			l = []
			for key in types:
				l.append((types[key], key))

			#print sorted(l)
		gc.set_debug(gc.DEBUG_LEAK | gc.DEBUG_STATS)
		return "Collected %s objects out of %s. Garbarge are %s objects." % (gc.collect(), obj_count, len(gc.garbage))

	def trig_garbage(self, bot, source, target, trigger, argument):
		import gc

		gc.set_debug(0)

		garbage_cnt = len(gc.garbage[:])
		del(gc.garbage[:])
		collect_cnt = gc.collect(2)
		garbage_left = len(gc.garbage[:])

		return "Collected %s objects. Brought out %s units of garbage, %s units left." % (collect_cnt, garbage_cnt, garbage_left)
