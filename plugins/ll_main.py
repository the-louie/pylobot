# coding: utf-8

from commands import Command
from ll_utils import LLUtils
#from utility import extract_nick
from random import randrange
import hashlib
import time
import sqlite3 as sql
import datetime
import base64

class Landlady(Command):
	def __init__(self):
		self.Util = LLUtils()
		self.Settings = self.Util.Settings
		self.Swarm = self.Util.Swarm
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
		self.client = bot.clients[network]
		self.net = self.client.net
		self.bot.swarm = self.Swarm

		self.Util.bot = bot
		self.Util.client = self.client

		delay = float(randrange(6000, 12000)/10)
		self.bot.add_timer(datetime.timedelta(0, delay), False, self.check_old_bans)


	"""
		Expose some information
	"""
	def on_privmsg(self, bot, source, target, message, network, **kwargs):
		if len(message) < 4:
			return
		if message.split(' ')[0][:3] == '.kb':
			argument = " ".join(message.split(' ')[1:])
			self.trigger_kb(source, target, argument)

	def debug_info(self, network):
		print "(swarm) enabled: %s" % self.Swarm.enabled
		if self.Swarm.enabled:
			print "(swarm) voteid: %s swarmrange: %s" % (self.Swarm.voteid, self.Swarm.range)
			print "(swarm) last vote time: %s s ago" % (time.time() - self.Swarm.last_vote_time)
			print "(swarm) posponed count: %s" % (self.Swarm.posponed_vote_count)
			print "(swarm) channel: %s" % (self.Swarm.channel)
			print "(swarm) votes: %s" % (self.Swarm.votes[self.Swarm.voteid])



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
				#print "TARGET HASHID: %s (%s) my range: %d %d (exiting)" % (hashid, targetnick, self.Swarm.range[0], self.Swarm.range[1])
				return False
			#print "TARGET HASHID: %s (%s) my range: %d %d (executing)" % (hashid, targetnick, self.Swarm.range[0], self.Swarm.range[1])

		# Get a banmask that's unique
		banmask = self.Util.create_banmask(self.net, targetnick)
		if not banmask:
			return "Couldn't find user %s" % (targetnick)

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
		if self.Settings.swarm_enabled:
			self.Util.announce_kickban(targetnick, banmask, reason, bantime, trigger_nick, cmd)

		return None


	"""
		If we join the swarm.channel we need to vote
	"""
	def on_join(self, bot, userhost, channel, network, **kwargs):
		nick = self.Util.extract_nick(userhost)

		if self.Settings.swarm_enabled and (nick == self.net.mynick) and (channel == self.Swarm.channel):
			wait_time = randrange(2,5)+float(randrange(10))/10
			self.Swarm.next_vote_time = int((datetime.datetime.now()+datetime.timedelta(0,wait_time)).strftime("%s"))
			self.bot.add_timer(datetime.timedelta(0, wait_time), False, self.force_revote)
		return


	# wrapper for send_vote to force a new vote
	# to be used with timer
	def force_revote(self):
		if self.Swarm.unvoted_id != None and time.time() < self.Swarm.next_vote_time:
			print "(swarm) unvoted id already set (%s), escaping" % (self.Swarm.unvoted_id)
			return
		self.Swarm.unvoted_id = randrange(0,65535)
		self.Swarm.votes[self.Swarm.unvoted_id] = {}
		self.send_vote()

	def time_vote(self, wait_time, next_vote_time=None):
		if time.time() > self.Swarm.next_vote_time:
			# if there's a timer in the future lets skip this one.
			self.Swarm.next_vote_time = int((datetime.datetime.now()+datetime.timedelta(0,wait_time)).strftime("%s"))
			self.Swarm.vote_timer_id = self.bot.add_timer(datetime.timedelta(0, wait_time), False, self.send_vote, next_vote_time)
			self.Swarm.unvoted_id = None

	# send vote
	def send_vote(self, next_vote_time=None):
		self.Swarm.vote_timer_id = 0

		# don't vote twice on the same id
		if self.Swarm.unvoted_id == self.Swarm.voteid:
			self.Swarm.posponed_vote_count = 0
			# vote again in a while if there's no pending vote times
			wait_time = randrange(600,1200)+float(randrange(100))/10
			self.time_vote(wait_time)
			return

		# don't vote if we don't have any unvoted id to vote for
		if self.Swarm.unvoted_id == None:
			self.Swarm.posponed_vote_count = 0
			# vote again in a while  if there's no pending vote times
			wait_time = randrange(600,1200)+float(randrange(100))/10
			self.time_vote(wait_time)
			return


		last_vote_delta_time = time.time() - self.Swarm.last_vote_time
		if last_vote_delta_time < 300:
			# don't vote too often
			wait_time = randrange(600,1200)+float(randrange(100))/10
			self.time_vote(wait_time)
			return
			# make sure we didn't vote just
			self.Swarm.posponed_vote_count += 1
			if self.Swarm.posponed_vote_count <= 10:
				# if we havn't posponed votes 10 times try agin in a while
				min_wait = int(30-last_vote_delta_time)
				wait_time = randrange(min_wait,30)+float(randrange(100))/10
				self.time_vote(wait_time)

			else:
				# avoid trying too hard, let us revote in a while instead if there's no pending vote times
				self.posponed_vote_count = 0
				wait_time = randrange(600,1200)+float(randrange(100))/10
				self.time_vote(wait_time)

			return



		self.Swarm.voteid = self.Swarm.unvoted_id
		self.Swarm.random = randrange(0,65535)
		if self.Swarm.voteid not in self.Swarm.votes:
			self.Swarm.votes[self.Swarm.voteid] = {}
		self.Swarm.votes[self.Swarm.voteid][self.net.mynick] = self.Swarm.random
		self.Swarm.last_vote_time = time.time()
		self.Swarm.range = self.Swarm.get_swarm_range()
		self.client.tell(self.Swarm.channel,"%svote %d %d" % (self.bot.settings.trigger, self.Swarm.voteid, self.Swarm.random))
		#print "*\n votes: %s \n" % self.Swarm.votes[self.Swarm.voteid]
		self.Swarm.unvoted_id = None

		wait_delta = float(randrange(100))/10
		self.bot.add_timer(datetime.timedelta(0, randrange(300,900)+wait_delta), False, self.force_revote)


		return


	def on_part(self, bot, userhost, channel, network):
		nick = self.Util.extract_nick(userhost)
		if self.Settings.swarm_enabled and (nick != self.net.mynick) and (channel == self.Swarm.channel):
			if nick not in self.Swarm.votes[self.Swarm.voteid].keys(): # not a swarm bot
				return

		self.Swarm.unvoted_id = randrange(0,65535)
		self.Swarm.votes[self.Swarm.unvoted_id] = {}
		wait_delta = float(randrange(100))/30
		self.bot.add_timer(datetime.timedelta(0, randrange(0,5)+wait_delta), False, self.force_revote)

		return



	"""
		Someone else voted, of we haven't voted yet we should
	"""
	def trig_vote(self, bot, source, target, trigger, argument, network):
		print "trig_vote(self,bot,%s,%s,%s,%s,network)" % (source, target, trigger, argument)
		if not self.Settings.swarm_enabled:
			return

		if target != self.Swarm.channel:
			print "ERROR: Swarm vote in none swarm channel (%s)" % target
			return False

		(incoming_vote_id, incoming_vote) = self.Swarm.parse_vote(argument)
		if (incoming_vote_id is None) or (incoming_vote is None):
			print "ERROR: error in vote arguments"
			return False

		if incoming_vote_id not in self.Swarm.votes:
			self.Swarm.votes[incoming_vote_id] = {}

		self.Swarm.votes[incoming_vote_id][source] = incoming_vote


		if incoming_vote_id != self.Swarm.voteid: # new vote, we need to vote
			self.Swarm.unvoted_id = incoming_vote_id
			#print "overwriting unvoted_id with %s" % incoming_vote_id
			self.bot.add_timer(datetime.timedelta(0, float(randrange(50,150))/100), False, self.send_vote)
		else: # we already voted on this
			#print "adding %s vote (%s) to Swarm.votes (voteid: %s)" % (source, incoming_vote, incoming_vote_id)
			self.Swarm.range = self.Swarm.get_swarm_range()
			self.Swarm.unvoted_id = None
			#print "*\n votes: %s \n" % self.Swarm.votes[incoming_vote_id]

		return


	def trig_banned(self, bot, source, target, trigger, argument, network):
		#print "trig_banned(self, bot, %s, %s, %s, %s, %s)" % (source, target, trigger, argument, network)
		if not self.Settings.swarm_enabled:
			#print "trig_banned, swarm disabled"
			return

		if target != self.Swarm.channel:
			print "ERROR: Swarm message (banned) in none swarm channel (%s)" % target
			return False

		arguments = argument.split(' ')
		arguments_decoded = []
		try:
			for arg in arguments:
				arguments_decoded.append(base64.b64decode(arg))
		except Exception, e:
			print " -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  - "
			print "trig_banned(self, bot, %s, %s, %s, %s, %s)" % (source, target, trigger, argument, network)
			print "EXCEPTION %s %s" % (e.__class__.__name__, e)
			print " -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  - "
			return

		targetnick, banmask, bantime, trigger_nick, cmd = arguments_decoded[0:5]
		if cmd in self.Settings.kb_commands.keys():
			reason = self.Settings.kb_commands[cmd][1]
			self.Util.save_kickban(self.net.name, targetnick, banmask, reason, bantime, trigger_nick, cmd)
		else:
			print " **** COMMAND (%s) not in %s" % (cmd, self.Settings.kb_commands.keys())


	def check_old_bans(self):
		self.Util.purge_kickbans()
		delay = float(randrange(6000, 12000)/10)
		self.bot.add_timer(datetime.timedelta(0, delay), False, self.check_old_bans)

	"""
		Default functions
	"""
	def save(self):
		pass

	def on_load(self):
		pass

	def on_unload(self):
		pass