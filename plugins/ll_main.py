# coding: utf-8

from commands import Command
from ll_utils import LLUtils
#from utility import extract_nick
from random import randrange
import hashlib
import time
import sqlite3 as sql
import datetime

class Landlady(Command):
	def __init__(self):
		self.Util = LLUtils()
		self.Settings = self.Util.Settings
		#self.Swarm = self.Util.Swarm
		self.bot = None
		self.net = None
		self.client = None

		self.banlist_age = {}
		self.banlist_timestamp = {}

		if self.Settings.swarm_enabled:
			from ll_swarm import Swarm
			self.Swarm = Swarm()
			self.Swarm.channel = self.Settings.swarm['channel']

	def on_connected(self, bot, network, **kwargs):
		self.bot = bot
		self.Util.bot = bot
		self.client = bot.clients[network]
		self.net = self.client.net

	"""
		Expose some information
	"""
	def on_privmsg(self, bot, source, target, message, network, **kwargs):
		if len(message) < 4:
			return
		if message.split(' ')[0][:3] == '.kb':
			argument = " ".join(message.split(' ')[1:])
			self.trigger_kb(source, target, argument)

	def trigger_info(self, net, source, target, trigger, argument):
		if target != self.Settings.kb_settings['command_chan']:
			print "ERROR: inforequest from outside %s" % self.Settings.kb_settings['command_chan']
			return

		if argument.split(' ')[0] != self.net.mynick:
			print "INFO: inforequest for other bot %s (i'm %s)" % (argument.split(' ')[0],self.net.mynick)
			return

		result = []
		# if argument.split(' ')[1] == 'swarm':
		# 	rowresult = "(swarm) enabled: %s" % self.Swarm.enabled
		# 	if self.Swarm.enabled:
		# 		rowresult += " voteid: %s swarmrange: %s" % (self.Swarm.voteid, self.Swarm.range)
		# 	result.append(rowresult)
		# 	return result

		# if argument.split(' ')[1] == 'ban':
		# 	for channel in self.Settings.kb_settings['child_chans'].split(' '):
		# 		print "DEBUG: Checking %s" % channel
		# 		if channel in bot.clients[network].banlists:
		# 			real_length = len([bot.clients[network].banlists[channel] for r in bot.clients[network].banlists[channel] if r != 'AGE'])
		# 			virt_length = 'Not implemented'
		# 			result.append("(ban %s) real list: %s, virtual list: %s" % (channel,real_length, virt_length))
		# 	return result


	"""
		Take care of any incoming kick-ban requests
	"""
	def trigger_kb(self, trigger_nick, trigger_channel, argument):
		if trigger_channel != self.Settings.kb_settings['command_chan']:
			print "ERROR: kb-request from outside %s" % self.Settings.kb_settings['command_chan']
			return False

		(cmd,reason,targetnick,bantime) = self.Util.parse_kb_arguments(argument,trigger_nick)
		if not cmd:
			print "ERROR: Unknown command, %s,%s,%s." % (trigger_nick,trigger_channel,argument)
			print "     : Unknown command, %s,%s,%s,%s." % (cmd,reason,targetnick,bantime)
			return None

		if self.Settings.swarm_enabled:
			m = hashlib.md5()
			m.update(targetnick)
			hashid = int(m.hexdigest()[0:2],16)
			if not self.Swarm.range[0] <= hashid < self.Swarm.range[1]:
				print "TARGET HASHID: %s (%s) my range: %d %d (exiting)" % (hashid, targetnick, self.Swarm.range[0], self.Swarm.range[1])
				return False
			print "TARGET HASHID: %s (%s) my range: %d %d (executing)" % (hashid, targetnick, self.Swarm.range[0], self.Swarm.range[1])

		# Get a banmask that's unique
		banmask = self.Util.create_banmask(self.net, targetnick)
		if not banmask:
			return "Couldn't find user %s" % (targetnick)

		print "\n"
		print " *** trig_kb banmask", banmask

		# Add punishfactor
		factor = self.Util.get_punish_factor(banmask, self.net.name)
		bantime = int(bantime) * int(factor)

		# Kickban the user in all channels
		for channel in self.Settings.kb_settings['child_chans']:
			self.client.send('MODE %s +b %s' % (channel, banmask))
			self.client.send('KICK %s %s :%s' % (channel, targetnick, reason))
			self.bot.add_timer(datetime.timedelta(0, bantime), False, self.client.send, 'MODE %s -b %s' % (channel, banmask))
			#self.bot.add_timer(datetime.timedelta(0, duration), False, self.remove_from_banlist, network, channel, banmask)

		self.Util.save_kickban(self.net.name, targetnick, banmask, reason, bantime, trigger_nick, cmd)
		#print "%s|%s|%s" % (targetnick,banmask,reason)
		#return "%s|%s|%s" % (targetnick,banmask,reason)
		return None


	"""
		If we join the swarm.channel we need to vote
	"""
	def on_join(self, bot, userhost, channel, network, **kwargs):
		nick = self.Util.extract_nick(userhost)

		# if swarm mode enabled
		# check so it's we that are joining the swarm channel
		if self.Settings.swarm_enabled and (nick == self.net.mynick) and (channel == self.Swarm.channel):
			self.Swarm.voteid = randrange(0,65535)
			self.Swarm.random = randrange(0,65535)
			self.client.tell(channel,"%svote %d %d" % (bot.settings.trigger, self.Swarm.voteid, self.Swarm.random))
			self.Swarm.votes = {}
			self.Swarm.votes[nick] = self.Swarm.random
			return

		return

	"""
		Someone else voted, of we haven't voted yet we should
	"""
	def trig_vote(self, bot, source, target, trigger, argument, network):
		if not self.Settings.swarm_enabled:
			return

		if target != self.Swarm.channel:
			print "ERROR: Swarm vote in none swarm channel (%s)" % target
			return False

		(curr_vote_id, curr_vote) = self.Swarm.parse_vote(argument)
		if (curr_vote_id is None) or (curr_vote is None):
			print "ERROR: error in vote arguments"
			return False

		# if it's a new vote
		if curr_vote_id != self.Swarm.voteid:
			print "new vote"
			self.Swarm.votes = {}
			time.sleep(float(randrange(0,50))/10)
			self.Swarm.random = randrange(0,65535)
			while self.Swarm.random in self.Swarm.votes.values():
				self.Swarm.random = randrange(0,65535)
			self.Swarm.votes[bot.clients[network].nick] = self.Swarm.random
			bot.clients[network].tell(target,"%svote %d %d" % (bot.settings.trigger, int(curr_vote_id), int(self.Swarm.random)))
		else:
			print "old vote"

		self.Swarm.voteid = curr_vote_id
		self.Swarm.votes[source] = curr_vote
		self.Swarm.range = self.Swarm.get_swarm_range()

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