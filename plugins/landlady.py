# coding: utf-8

from commands import Command
from ll_utils import *
from utility import extract_nick
from random import randrange
import time
import sqlite3 as sql

class Landlady(Command):
	def __init__(self):
		db_connect()
		pass

	"""
		Take care of any incoming kick-ban requests
	"""
	def trig_kb(self, bot, source, target, trigger, argument, network):
		if target != Settings.default.kb_commands['master_chan']:
			print "ERROR: kb-request from outside %s" % Settings.default.kb_commands['master_chan']
			return False

		(cmd,reason,targetnick,bantime) = parse_kb_arguments(argument,source)
		if not cmd:
			print "UNKOWN KB: %s,%s,%s,%s,%s." % (source,target,trigger,argument,network)
			return None

		if Settings.swarm['enabled']:
			m = hashlib.md5()
			m.update(targetnick)
			hashid = int(m.hexdigest()[0:2],16)
			if (Settings.swarm.range[0] < hashid) or (Settings.swarm.range[1] >= hashid):
				return False

		# Get a banmask that's unique
		banmask = create_banmask(bot.clients[network], targetnick)

		# Add punishfactor
		factor = get_punish_factor(banmask)
		bantime = bantime * factor

		# Kickban the user
		kickban(bot, network, targetnick, banmask, reason, bantime, source, cmd)

		return "%s|%s|%s" % (targetnick,banmask,reason)


	"""
		If we join the swarm.channel we need to vote
	"""
	def on_join(self, bot, userhost, channel, network, **kwargs):
		print "ON_JOIN"
		nick = extract_nick(userhost)
		print "%s %s" % (nick,channel)
		print "%s %s" % (bot.clients[network].nick, Settings.swarm['channel'])
		# check so it's we that are joining the swarm_channel
		if (nick == bot.clients[network].nick) and (channel == Settings.swarm['channel']):
			Settings.swarm['voteid'] = randrange(0,65535)
			Settings.swarm['random'] = randrange(0,65535)
			bot.clients[network].tell(channel,"%svote %d %d" % (bot.settings.trigger, Settings.swarm['voteid'], Settings.swarm['random']))
			Settings.swarm.votes = {}
			Settings.swarm.votes[nick] = Settings.swarm['random']
			return

		return

	def trig_vote(self, bot, source, target, trigger, argument, network):
		if target != Settings.swarm['channel']:
			print "ERROR: Vote in none swarm_channel"
			return False

		(curr_vote_id, curr_vote) = parse_vote(argument)
		if (curr_vote_id is None) or (curr_vote is None):
			print "ERROR: error in vote arguments"
			return False


		# if it's a new vote
		if curr_vote_id != Settings.swarm['voteid']:
			Settings.swarm.votes = {}
			time.sleep(float(randrange(0,50)/10))
			Settings.swarm['random'] = randrange(0,65535)
			while Settings.swarm['random'] in Settings.swarm_votes.values():
				Settings.swarm['random'] = randrange(0,65535)
			Settings.swarm_votes[bot.clients[network].nick] = Settings.swarm['random']
			bot.clients[network].tell(target,"%svote %d %d" % (bot.settings.trigger, int(curr_vote_id), int(Settings.swarm['random'])))

		Settings.swarm['voteid'] = curr_vote_id
		Settings.swarm_votes[source] = curr_vote
		Settings.swarm_range = get_swarm_range(Settings)

		Settings.swarm['enabled'] = True

		print "Settings.swarm_range", Settings.swarm['random']
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