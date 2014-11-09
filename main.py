# coding: latin-1
import time
import datetime
import os
import sys

import select
import tty
import termios

try:
	import settings
except ImportError:
	print "---> Please copy settings.sample.py to settings.py and customize it. <---"
	sys.exit(0)

import ircbot

bot = ircbot.IRCBot(settings.Settings())
bot.add_timer(datetime.timedelta(0, 600), True, bot.send, "PING :iamabanana")

# Add paths for debugger
sys.path += [os.path.join(sys.path[0], "ircclient"), os.path.join(sys.path[0], "plugins")]

def isData():
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])


# do magic with the terminal to allow for non blocking input until we use curses
old_term_settings = termios.tcgetattr(sys.stdin)
tty.setcbreak(sys.stdin.fileno())
new_term_settings = termios.tcgetattr(sys.stdin.fileno())
new_term_settings[3] = (new_term_settings[3] & ~termios.ICANON & ~termios.ECHO)
termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, new_term_settings)

def Tick():
	cli_string = ""
	while True:
		try:
			if bot.need_reload.has_key('main') and bot.need_reload['main']:
				reload(ircbot)
				reload(settings)
				print "Collected %s objects out of %s. Garbarge are %s objects." % (gc.collect(2),
					len(gc.get_objects()), len(gc.garbage))
				bot.need_reload['main'] = False
				bot.on_reload()

			bot.tick()

			time.sleep(0.1)

			if isData():
				c = sys.stdin.read(1)
				if ord(c) != 10:
					sys.stdout.write(c)
					cli_string += c
				else:
					print ""
					if cli_string == "":
						cli_string = "debug_info"
					command = cli_string.split(' ')[0]
					params = cli_string.split(' ')[1:]
					if command in bot.callbacks:
						try:
							bot.callbacks[command](*params)
						except Exception, e:
							print "Exception: " + e.__class__.__name__
							print e
							print
					elif command == 'help':
						for key in bot.callbacks.keys():
							if key[:6] == 'debug_':
								sys.stdout.write(key + "\n")
					elif command == 'exit':
						sys.exit(0)

					cli_string = ""



		# except KeyboardInterrupt:
		# 	print ""
		# 	print "Entering debug mode, use c(ontinue) to exit. Don't stay here to long."
		# 	print "This is " + bot.settings.networks.values()[0]["nick"]
		# 	bot.callbacks["debug_info"]()
		# 	#pdb.set_trace()
		except:
			raise

# Run bot with debugger
Tick()
termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_term_settings)

