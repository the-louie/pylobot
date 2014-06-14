# coding: utf-8

from commands import Command
from ll_utils import LLUtils
#from utility import extract_nick
from random import randrange
import hashlib
import time
import sqlite3 as sql

class Landlady(Command):
	def __init__(self):
		self.Util = LLUtils()
		self.Settings = self.Util.Settings
		#self.Swarm = self.Util.Swarm

		self.banlist_age = {}
		self.banlist_timestamp = {}
		self.bot = None

	def on_connected(self, bot, network, **kwargs):
		self.bot = bot
		self.Util.bot = bot

	"""
		Expose some information
	"""
	def trig_info(self, bot, source, target, trigger, argument, network):
		if target != self.Settings.kb_settings['command_chan']:
			print "ERROR: inforequest from outside %s" % self.Settings.kb_settings['command_chan']
			return

		if argument.split(' ')[0] != bot.clients[network].nick:
			print "INFO: inforequest for other bot %s (i'm %s)" % (argument.split(' ')[0],bot.clients[network].nick)
			return

		result = []
		# if argument.split(' ')[1] == 'swarm':
		# 	rowresult = "(swarm) enabled: %s" % self.Swarm.enabled
		# 	if self.Swarm.enabled:
		# 		rowresult += " voteid: %s swarmrange: %s" % (self.Swarm.voteid, self.Swarm.range)
		# 	result.append(rowresult)
		# 	return result

		if argument.split(' ')[1] == 'ban':
			for channel in self.Settings.kb_settings['child_chans'].split(' '):
				print "DEBUG: Checking %s" % channel
				if channel in bot.clients[network].banlists:
					real_length = len([bot.clients[network].banlists[channel] for r in bot.clients[network].banlists[channel] if r != 'AGE'])
					virt_length = 'Not implemented'
					result.append("(ban %s) real list: %s, virtual list: %s" % (channel,real_length, virt_length))
			return result


	"""
		Take care of any incoming kick-ban requests
	"""
	def trig_kb(self, bot, source, target, trigger, argument, network):
		if target != self.Settings.kb_settings['command_chan']:
			print "ERROR: kb-request from outside %s" % self.Settings.kb_settings['command_chan']
			return False

		(cmd,reason,targetnick,bantime) = self.Util.parse_kb_arguments(argument,source)
		if not cmd:
			print "ERRPR: Unknown command, %s,%s,%s,%s,%s." % (source,target,trigger,argument,network)
			return None

		# if self.Swarm.enabled:
		# 	m = hashlib.md5()
		# 	m.update(targetnick)
		# 	hashid = int(m.hexdigest()[0:2],16)
		# 	print hashid
		# 	if (self.Swarm.range[0] < hashid) or (self.Swarm.range[1] >= hashid):
		# 		return False

		# Get a banmask that's unique
		banmask = self.Util.create_banmask(bot.clients[network], targetnick)
		if not banmask:
			return "Couldn't find user %s" % (targetnick)

		print "\n"
		print " *** trig_kb banmask", banmask

		# Add punishfactor
		factor = self.Util.get_punish_factor(banmask, network)
		bantime = int(bantime) * int(factor)

		# Kickban the user
		self.Util.kickban(network, targetnick, banmask, reason, bantime, source, cmd)
		#print "%s|%s|%s" % (targetnick,banmask,reason)
		#return "%s|%s|%s" % (targetnick,banmask,reason)
		return None


	"""
		If we join the swarm.channel we need to vote
	"""
	def on_join(self, bot, userhost, channel, network, **kwargs):
		nick = self.Util.extract_nick(userhost)

		# get banlist
		if channel in self.banlist_timestamp:
			if time.time() - self.banlist_timestamp[channel] > 60:
				bot.clients[network].send('mode %s +b' % channel)
				self.banlist_timestamp[channel] = time.time()
		else:
			self.banlist_timestamp[channel] = time.time()


		# if swarm mode enabled
		# check so it's we that are joining the swarm_channel
		# if self.Swarm.enabled and (nick == bot.clients[network].nick) and (channel == self.Swarm.channel):
		# 	self.Swarm.voteid = randrange(0,65535)
		# 	self.Swarm.random = randrange(0,65535)
		# 	bot.clients[network].tell(channel,"%svote %d %d" % (bot.settings.trigger, self.Swarm.voteid, self.Swarm.random))
		# 	self.Swarm.votes = {}
		# 	self.Swarm.votes[nick] = self.Swarm.random
		# 	return

		return

	"""
		Someone else voted, of we haven't voted yet we should
	"""
	def trig_vote(self, bot, source, target, trigger, argument, network):
		# if not self.Swarm.enabled:
		# 	return

		# if target != self.Swarm.channel:
		# 	print "ERROR: Vote in none swarm_channel"
		# 	return False

		# (curr_vote_id, curr_vote) = self.Swarm.parse_vote(argument)
		# if (curr_vote_id is None) or (curr_vote is None):
		# 	print "ERROR: error in vote arguments"
		# 	return False

		# # if it's a new vote
		# if curr_vote_id != self.Swarm.voteid:
		# 	print "new vote"
		# 	self.Swarm.votes = {}
		# 	time.sleep(float(randrange(0,50)/10))
		# 	self.Swarm.random = randrange(0,65535)
		# 	while self.Swarm.random in self.Swarm.votes.values():
		# 		self.Swarm.random = randrange(0,65535)
		# 	self.Swarm.votes[bot.clients[network].nick] = self.Swarm.random
		# 	bot.clients[network].tell(target,"%svote %d %d" % (bot.settings.trigger, int(curr_vote_id), int(self.Swarm.random)))
		# else:
		# 	print "old vote"

		# self.Swarm.voteid = curr_vote_id
		# self.Swarm.votes[source] = curr_vote
		# self.Swarm.range = self.Swarm.get_swarm_range()

		return

	"""
		take care of others bans
	"""
	def on_mode(self, bot, source, channel, mode, target, network):
		client = self.bot.clients[network]
		if source == bot.clients[network].nick:
			return

		if channel in self.Settings.kb_settings['child_chans']:
			if channel not in self.banlist_timestamp or time.time()-self.banlist_timestamp[channel] > 600:
				client.banlists[channel] = {}
				client.send("MODE %s +b" % channel)
			else:
				if mode == '+b':
					self.Util.add_to_banlist(network, channel, source, target)

				elif mode == '-b' and target in client.banlists[channel]:
					self.Util.remove_from_banlist(self.bot, network, channel, target)


	"""
		Default functions
	"""
	def save(self):
		pass

	def on_load(self):
		pass

	def on_unload(self):
		pass