import re
#from utility import extract_nick
from ll_settings import landladySettings as DefaultSettings
import sys
import sqlite3
import copy
import time
import datetime

class Settings():
	def __init__(self):
		self.kb_commands = {}
		self.kb_settings = {}
		#self.swarm = {}
		self.general = {}
		pass



class LLUtils():
	def __init__(self):
		self.Settings = Settings()
		#self.Swarm = Swarm()

		self.bot = None
		self.dbcon = None
		self.dbcur = None
		self.db_connect()


	'''

		Connect to db and if needed populate it with
		the default values from ll_settings.py

	'''
	def db_real_connect(self):
		if (self.dbcon) and (self.dbcur):
			print "INFO: Already connected to db."
			return True

		# connect to db
		try:
			self.dbcon = sqlite3.connect('data/landlady.db')
			self.dbcur = self.dbcon.cursor()
		except Exception, e:
			print "ERROR: Couldn't open database, %s" % e
			sys.exit(1)


	def db_connect(self):
		self.db_real_connect()

		# on first run we might have to create the banmemory table
		try:
			self.dbcur.execute("CREATE TABLE IF NOT EXISTS landlady_banmem (timestamp INT, network TEXT, targetnick TEXT, targethost TEXT, command TEXT, sourcenick TEXT, duration INT)")
		except Exception, e:
			print "ERROR: couln't create table, %s" % e

		# on first run we might have to create the settings table
		try:
			self.dbcur.execute("CREATE TABLE IF NOT EXISTS landlady_config (section TEXT, key TEXT, value TEXT)")
		except Exception, e:
			print "ERROR: couln't create table, %s" % e

		# load the data from the db, and if there's default values missing add them in
		for section in DefaultSettings.default.keys():
			print "INFO: Loading %s" % section
			try:
				self.dbcur.execute('SELECT key, value FROM landlady_config WHERE section = ?', [section])
			except Exception, e:
				print "ERROR: Fetching config, %s" % (e)
				sys.exit(1)

			loaded_vals = []
			rows = self.dbcur.fetchall()
			if len(rows) == 0:
				print "WARNING: No settings found for %s, using default" % section
			for row in rows:
				loaded_vals.append(row[0])
				DefaultSettings.default[section][row[0]] = row[1]

			for key in DefaultSettings.default[section].keys():
				if key not in loaded_vals:
					print "INFO: Updating %s with %s=%s" % (section,key,DefaultSettings.default[section][key])
					try:
						self.dbcur.execute('INSERT INTO landlady_config (section, key, value) VALUES (?,?,?)', [section, key, DefaultSettings.default[section][key]])
					except Exception, e:
						print "ERROR: Couln't update database, %s" % e

			self.dbcon.commit()


		for key in DefaultSettings.default['kb_commands'].keys():
			mess = DefaultSettings.default['kb_commands'][key].split(' ',1)[1]
			time = DefaultSettings.default['kb_commands'][key].split(' ',1)[0]
			self.Settings.kb_commands[key] = (time,mess)
			print "DEBUG: kb_commands loading %s '%s' -> (%s,%s)." % (key,DefaultSettings.default['kb_commands'][key],DefaultSettings.default['kb_commands'][key][1],DefaultSettings.default['kb_commands'][key][0])

		for key in DefaultSettings.default['kb_settings'].keys():
			self.Settings.kb_settings[key] = copy.copy(DefaultSettings.default['kb_settings'][key])
			print "DEBUG: kb_settings, %s = %s" % (key,DefaultSettings.default['kb_settings'][key])
		self.Settings.kb_settings['ban_timemul'] = DefaultSettings.default['kb_settings']['ban_timemul'].split(',')
		self.Settings.kb_settings['child_chans'] = DefaultSettings.default['kb_settings']['child_chans'].split(' ')


		self.Settings.swarm = copy.deepcopy(DefaultSettings.default['swarm'])
		self.Settings.swarm_enabled = copy.deepcopy(DefaultSettings.swarm_enabled)
		#self.Swarm.channel = DefaultSettings.default['swarm']['channel']


	'''


		Take the arguments for a kb kb_command
		and parse them.

		If it's not a valid command it returns
		a lot of None


	'''
	def parse_kb_arguments(self, argument, source):
		cmd = reason = targetnick = bantime = bantime_int = None

		try:
			(cmd, targetnick) = argument.split(' ')
		except ValueError:
			pass
		except Exception:
			print "\n1 %s\n" % argument
			return (None,None,None,None)

		if not cmd:
			try:
				(cmd, targetnick, bantime) = argument.split(' ')
			except Exception:
				print "\n2 %s\n" % argument
				return (None,None,None,None)

		if not cmd in self.Settings.kb_commands:
			print "ERROR: Command (%s) not found" % cmd
			return (None,None,None,None)

		try:
			bantime_int = int(bantime)
		except TypeError:
			bantime_int = None
		except ValueError:
			bantime_int = None

		if not bantime_int:
			bantime_int = int(self.Settings.kb_commands[cmd][0])

		reason = "%s (%d) /%s" % (self.Settings.kb_commands[cmd][1], bantime_int, source.split('!')[0])

		return (cmd,reason,targetnick,bantime_int)


	def is_numeric(self, host):
		hostbits = host.split('.')
		numeric = True
		if len(hostbits) == 4:
			for bit in hostbits:
				numeric &= bit.isdigit()
				if not numeric:
					break

		return numeric



	'''


		Ban someone

		The functions handels the creation of the banmask so
		it's unique to the user and the accuall commands to
		the irc-server


	'''
	def match_banmask(self, net, targetnick, banmask, channel_name):
		matches = []

		# escape banmask to re
		banmask = banmask.replace('.','\.')
		banmask = banmask.replace('-','\-')
		banmask = banmask.replace('[','\[')
		banmask = banmask.replace(']','\]')
		banmask = banmask.replace('{','\{')
		banmask = banmask.replace('}','\}')
		banmask = banmask.replace('*','.*')

		try:
			channel = net.channel_by_name(channel_name)
		except Exception, e:
			print "ERROR: %s" % e
			return 99

		for user in channel.user_list:
			if user.nick == targetnick:
				continue

			try:
				m = re.search(banmask, user.nickuserhost)
				if m:
					matches.append(user.nick)
			except Exception, e:
				print "ERROR when regexing: %s %s" % (e.__class__.__name__, e)
				print "\t%s, %s" % (banmask, user.nickuserhost)

		return matches

	def create_banmask(self, net, targetnick):
		print "create_banmask(net, %s)" % targetnick
		try:
			u = net.user_by_nick(targetnick)
		except Exception, e:
			# FIXME: get correct banmask adhoc
			print "ERROR: %s" % e
			return None

		user = u.user
		host = u.host

		# FIXME: clean up below and remove redundant code
		# need to add method for numeric ip's also!

		if self.is_numeric(host):
			hits = 0
			for channel in self.Settings.kb_settings['child_chans']:
				banmask = '*!*@%s.*' % '.'.join(host.split('.')[:-1])
				hits += len(self.match_banmask(net, targetnick, banmask, channel))
			if hits == 0:
				return banmask

			hits = 0
			for channel in self.Settings.kb_settings['child_chans']:
				banmask = '*!*%s*@%s.*' % (user, '.'.join(host.split('.')[:-1]))
				hits += len(self.match_banmask(net, targetnick, banmask, channel))
			if hits == 0:
				return banmask

			banmask = '*!%s@%s' % (user, host)
			return banmask

		else:
			# try a wide mask first
			hits = 0
			for channel in self.Settings.kb_settings['child_chans']:
				if len(host.split('.')) == 2:
					banmask = '*!*@%s' % host
				else:
					banmask = '*!*@*.%s' % '.'.join(host.split('.')[1:])
				hits += len(self.match_banmask(net, targetnick, banmask, channel))
			if hits == 0:
				return banmask

			# try a wide mask second
			hits = 0
			for channel in self.Settings.kb_settings['child_chans']:
				if len(host.split('.')) == 2:
					banmask = '*!*%s@%s' % (user,host)
				else:
					banmask = '*!*@*.%s' % '.'.join(host.split('.')[1:])
				hits += len(self.match_banmask(net, targetnick, banmask, channel))
			if hits == 0:
				return banmask

			# narrow it down a bit
			hits = 0
			for channel in self.Settings.kb_settings['child_chans']:
				if len(host.split('.')) == 2:
					banmask = '*!*@%s' % host
				else:
					banmask = '*!*@*.%s' % '.'.join(host.split('.')[1:])
				hits += len(self.match_banmask(net, targetnick, banmask, channel))
			if hits == 0:
				return banmask

			# narrow it down a bit more
			hits = 0
			for channel in self.Settings.kb_settings['child_chans']:
				banmask = '*!*@%s' % (host)
				hits += len(self.match_banmask(net, targetnick, banmask, channel))
			if hits == 0:
				return banmask

			# if everything else failed use this
			banmask = '*!*%s*@%s' % (user,host)

		return banmask

	def get_punish_factor(self, banmask, network):
		self.dbcur.execute("SELECT count(*) FROM landlady_banmem WHERE targethost = ? AND network = ?", (banmask, network))
		try:
			count = int(self.dbcur.fetchone()[0])
		except Exception, e:
			print "ERROR: Couldn't get ban count: %s" % e
			return 1

		if count >= len(self.Settings.kb_settings['ban_timemul']):
			count = len(self.Settings.kb_settings['ban_timemul'])-1

		return self.Settings.kb_settings['ban_timemul'][count]



	def save_kickban(self, network, targetnick, banmask, reason, duration, sourcenick, command):

		# save kb to memory
		self.dbcur.execute("""INSERT INTO landlady_banmem (
				timestamp,
				network,
				targetnick,
				targethost,
				command,
				sourcenick,
				duration)
			VALUES (
				datetime('now'),?,?,?,?,?,?)""",
			(network, targetnick, banmask, command, sourcenick, duration)
		)
		self.dbcon.commit()

		# kick and ban user in all channels
		# for channel in self.Settings.kb_settings['child_chans']:
		# 	client.send('MODE %s +b %s' % (channel, banmask))
		# 	client.send('KICK %s %s :%s' % (channel, targetnick, reason))
		# 	self.add_to_banlist(network, channel, sourcenick, banmask)
		# 	self.bot.add_timer(datetime.timedelta(0, duration), False, self.unban, network, channel, banmask)
		# 	self.bot.add_timer(datetime.timedelta(0, duration), False, self.remove_from_banlist, network, channel, banmask)

	def unban(self, network, channel, banmask):
		client = self.bot.clients[network]
		print "DEBUG: Unbanning %s in %s" % (banmask, channel)
		client.send('MODE %s -b %s' % (channel, banmask))

	def add_to_banlist(self, network, channel, sourcenick, banmask):
		bl = self.bot.clients[network].banlists
		if channel in bl:
			self.bot.clients[network].banlists[channel][banmask] = (sourcenick,time.time())

	def remove_from_banlist(self, network, channel, banmask):
		bl = self.bot.clients[network].banlists
		if channel in bl:
			if banmask in bl[channel]:
				del(self.bot.clients[network].banlists[channel][banmask])

	def extract_nick(self, host):
		m = re.search('^:?(.+)!', host)
		if m:
			return str(m.group(1))
		else:
			return host


