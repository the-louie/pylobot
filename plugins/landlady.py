# coding: utf-8

from commands import Command
from ll_utils import *
from utility import extract_nick
from random import randrange
import time

class Landlady(Command):
	def __init__(self):
		pass

	"""
		Take care of any incoming kick-ban requests
	"""
	def trig_kb(self, bot, source, target, trigger, argument, network):
		(cmd,reason,targetnick,bantime) = parse_kb_arguments(argument,source)
		if not cmd:
			print "UNKOWN KB: %s,%s,%s,%s,%s." % (source,target,trigger,argument,network)
			return None

		if Settings.swarm_enabled:
			m = hashlib.md5()
			m.update(targetnick)
			hashid = int(m.hexdigest()[0:2],16)
			if (Settings.swarm_range[0] < hashid) or (Settings.swarm_range[1] >= hashid):
				return False

		# Get a banmask that's unique
		banmask = create_banmask(bot.clients[network], targetnick)

		# FIXME: add punishfactor

		# Kickban the user
		kickban(bot, network, banmask)

		return "%s|%s|%s" % (targetnick,banmask,reason)


	"""
		If we join the swarm_channel we need to vote
	"""
	def on_join(self, bot, userhost, channel, network, **kwargs):
		print "ON_JOIN"
		nick = extract_nick(userhost)
		print "%s %s" % (nick,channel)
		print "%s %s" % (bot.clients[network].nick, Settings.swarm_channel)
		# check so it's we that are joining the swarm_channel
		if (nick == bot.clients[network].nick) and (channel == Settings.swarm_channel):
			Settings.swarm_voteid = randrange(0,65535)
			Settings.swarm_random = randrange(0,65535)
			bot.clients[network].tell(channel,"%svote %d %d" % (bot.settings.trigger, Settings.swarm_voteid, Settings.swarm_random))
			Settings.swarm_votes = {}
			Settings.swarm_votes[nick] = Settings.swarm_random
			return

		return

	def trig_vote(self, bot, source, target, trigger, argument, network):
		if target != Settings.swarm_channel:
			print "ERROR: Vote in none swarm_channel"
			return False

		(curr_vote_id, curr_vote) = parse_vote(argument)
		if (curr_vote_id is None) or (curr_vote is None):
			print "ERROR: error in vote arguments"
			return False


		# if it's a new vote
		if curr_vote_id != Settings.swarm_voteid:
			Settings.swarm_votes = {}
			time.sleep(float(randrange(0,50)/10))
			Settings.swarm_random = randrange(0,65535)
			while Settings.swarm_random in Settings.swarm_votes.values():
				Settings.swarm_random = randrange(0,65535)
			Settings.swarm_votes[bot.clients[network].nick] = swarm_random
			bot.clients[network].tell(target,"%svote %d %d" % (bot.settings.trigger, int(curr_vote_id), int(Settings.swarm_random)))

		Settings.swarm_voteid = curr_vote_id
		Settings.swarm_votes[source] = curr_vote
		Settings.swarm_range = get_swarm_range(Settings)

		Settings.swarm_enabled = True

		print "Settings.swarm_range", Settings.swarm_random
		print "Settings.swarm_votes", Settings.swarm_votes

		return


	"""
		Default functions
	"""
	def save(self):
		pass

	def on_load(self):
		pass

	def on_unload(self):
		pass