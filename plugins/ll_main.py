# coding: utf-8

from commands import Command
from ll_utils import LLUtils
from utility import extract_nick
from random import randrange
import hashlib
import time
import sqlite3 as sql

class Landlady(Command):
	def __init__(self):
		self.Util = LLUtils()
		self.Settings = self.Util.Settings

		self.banlist_age = {}
		self.bot = None

	def on_connected(self, bot, network, **kwargs):
		self.bot = bot
		self.Util.bot = bot

	"""
		Expose some information
	"""
	def trig_info(self, bot, source, target, trigger, argument, network):
		if target != self.Settings.kb_settings['master_chan']:
			print "ERROR: inforequest from outside %s" % self.Settings.kb_settings['master_chan']
			return

		if argument.split(' ')[0] != bot.clients[network].nick:
			print "INFO: inforequest for other bot %s (i'm %s)" % (argument.split(' ')[0],bot.clients[network].nick)
			return

		result = []
		if argument.split(' ')[1] == 'swarm':
			rowresult = "(swarm) enabled: %s" % self.Settings.swarm['enabled']
			if self.Settings.swarm['enabled']:
				rowresult += " voteid: %s swarmrange: %s" % (self.Settings.swarm['voteid'], self.Settings.swarm['range'])
			result.append(rowresult)
			return result

		if argument.split(' ')[1] == 'ban':
			for channel in self.Settings.kb_settings['child_chans'].split(' '):
				print "Checking %s" % channel
				if channel in bot.clients[network].banlists:
					real_length = len([bot.clients[network].banlists[channel] for r in bot.clients[network].banlists[channel] if r != 'AGE'])
					virt_length = 'Not implemented'
					result.append("(ban %s) real list: %s, virtual list: %s" % (channel,real_length, virt_length))
			return result


	"""
		Take care of any incoming kick-ban requests
	"""
	def trig_kb(self, bot, source, target, trigger, argument, network):
		if target != self.Settings.kb_settings['master_chan']:
			print "ERROR: kb-request from outside %s" % self.Settings.kb_settings['master_chan']
			return False

		(cmd,reason,targetnick,bantime) = self.Util.parse_kb_arguments(argument,source)
		if not cmd:
			print "UNKOWN KB: %s,%s,%s,%s,%s." % (source,target,trigger,argument,network)
			return None

		if self.Settings.swarm['enabled']:
			m = hashlib.md5()
			m.update(targetnick)
			hashid = int(m.hexdigest()[0:2],16)
			print hashid
			if (self.Settings.swarm['range'][0] < hashid) or (self.Settings.swarm['range'][1] >= hashid):
				return False

		# Get a banmask that's unique
		banmask = self.Util.create_banmask(bot.clients[network], targetnick)

		# Add punishfactor
		factor = self.Util.get_punish_factor(banmask, network)
		bantime = bantime * factor

		# Kickban the user
		#self.Util.kickban(bot, network, targetnick, banmask, reason, bantime, source, cmd)

		return "%s|%s|%s" % (targetnick,banmask,reason)


	"""
		If we join the swarm.channel we need to vote
	"""
	def on_join(self, bot, userhost, channel, network, **kwargs):
		nick = extract_nick(userhost)
		bot.clients[network].send('mode %s +b' % channel)

		# if swarm mode enabled
		# check so it's we that are joining the swarm_channel
		if self.Settings.swarm['enabled'] and (nick == bot.clients[network].nick) and (channel == self.Settings.swarm['channel']):
			self.Settings.swarm['voteid'] = randrange(0,65535)
			self.Settings.swarm['random'] = randrange(0,65535)
			bot.clients[network].tell(channel,"%svote %d %d" % (bot.settings.trigger, self.Settings.swarm['voteid'], self.Settings.swarm['random']))
			self.Settings.swarm['votes'] = {}
			self.Settings.swarm['votes'][nick] = self.Settings.swarm['random']
			return

		return

	"""
		Someone else voted, of we haven't voted yet we should
	"""
	def trig_vote(self, bot, source, target, trigger, argument, network):
		if not self.Settings.swarm['enabled']:
			return

		if target != self.Settings.swarm['channel']:
			print "ERROR: Vote in none swarm_channel"
			return False

		(curr_vote_id, curr_vote) = self.Util.parse_vote(argument)
		if (curr_vote_id is None) or (curr_vote is None):
			print "ERROR: error in vote arguments"
			return False

		# if it's a new vote
		if curr_vote_id != self.Settings.swarm['voteid']:
			print "new vote"
			self.Settings.swarm['votes'] = {}
			time.sleep(float(randrange(0,50)/10))
			self.Settings.swarm['random'] = randrange(0,65535)
			while self.Settings.swarm['random'] in self.Settings.swarm['votes'].values():
				self.Settings.swarm['random'] = randrange(0,65535)
			self.Settings.swarm['votes'][bot.clients[network].nick] = self.Settings.swarm['random']
			bot.clients[network].tell(target,"%svote %d %d" % (bot.settings.trigger, int(curr_vote_id), int(self.Settings.swarm['random'])))
		else:
			print "old vote"

		self.Settings.swarm['voteid'] = curr_vote_id
		self.Settings.swarm['votes'][source] = curr_vote
		self.Settings.swarm['range'] = self.Util.get_swarm_range()

		self.Settings.swarm['enabled'] = True

		return

	"""
		take care of others bans
	"""
	def on_mode(self, bot, source, channel, mode, target, network):
		client = self.bot.clients[network]

		if channel in self.Settings.kb_settings['child_chans']:
			if channel not in self.banlist_age or time.time()-self.banlist_age[channel] > 300:
				client.banlists[channel] = {}
				client.send("MODE %s +b" % channel)
			else:
				if mode == '+b':
					self.Util.add_to_banlist(self.bot, network, channel, source, target)

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