import re
from utility import extract_nick
from ll_settings import landladySettings as Settings
import sys
import sqlite3
import copy

'''

	Connect to db and if needed populate it with
	the default values from ll_settings.py

'''
def db_connect():
	if (Settings.db_con) and (Settings.db_cur):
		print "INFO: Already connected to db."
		return True

	# connect to db
	try:
		dbcon = sqlite3.connect('data/landlady.db')
		dbcur = dbcon.cursor()
	except Exception, e:
		print "ERROR: Couldn't open database, %s" % e
		sys.exit(1)

	# on first run we might have to create the banmemory table
	try:
		dbcur.execute("CREATE TABLE IF NOT EXISTS landlady_banmem (timestamp INT, network TEXT, targetnick TEXT, targethost TEXT, command TEXT, sourcenick TEXT, duration INT)")
	except Exception, e:
		print "ERROR: couln't create table, %s" % e

	# on first run we might have to create the settings table
	try:
		dbcur.execute("CREATE TABLE IF NOT EXISTS landlady_config (section TEXT, key TEXT, value TEXT)")
	except Exception, e:
		print "ERROR: couln't create table, %s" % e

	# load the data from the db, and if there's default values missing add them in
	for section in Settings.default.keys():
		print "Loading %s" % section
		try:
			dbcur.execute('SELECT key, value FROM landlady_config WHERE section = ?', [section])
		except Exception, e:
			print "ERROR: Fetching config, %s" % (e)
			sys.exit(1)

		loaded_vals = []
		rows = dbcur.fetchall()
		if len(rows) == 0:
			print "WARNING: No settings found for %s, using default" % section
		for row in rows:
			loaded_vals.append(row[0])
			Settings.default[section][row[0]] = row[1]

		for key in Settings.default[section].keys():
			if key not in loaded_vals:
				print "INFO: Updating %s with %s=%s" % (section,key,Settings.default[section][key])
				try:
					dbcur.execute('INSERT INTO landlady_config (section, key, value) VALUES (?,?,?)', [section, key, Settings.default[section][key]])
				except Exception, e:
					print "ERROR: Couln't update database, %s" % e

		dbcon.commit()


	for key in Settings.default['kb_commands'].keys():
		Settings.default['kb_commands'][key] = (Settings.default['kb_commands'][key].split(' ',2)[1],Settings.default['kb_commands'][key].split(' ',2)[0])
		print "DEBUG: kb_commands loading %s '%s' -> (%s,%s)." % (key,Settings.default['kb_commands'][key],Settings.default['kb_commands'][key][1],Settings.default['kb_commands'][key][0])

	for key in Settings.default['kb_settings'].keys():
		Settings.default['kb_settings'][key] = copy.copy(Settings.default['kb_settings'][key])
		print "DEBUG: kb_settings, %s = %s" % (key,Settings.default['kb_settings'][key])
	Settings.kb_settings['ban_timemul'] = Settings.default['kb_settings']['ban_timemul'].split(',')


	Settings.swarm = copy.deepcopy(Settings.default['swarm'])

	#
	# take care of special variables
	# FIXME: This shouldn't be among settings.
	#
	Settings.swarm['range'] = (65535,0)
	Settings.swarm['votes'] = {}
	Settings.swarm['enabled'] = False
	Settings.swarm['id'] = 0
	Settings.swarm['random'] = 0
	Settings.swarm['voteid'] = -1



	Settings.db_con = dbcon
	Settings.db_cur = dbcur






'''
	Take the arguments for a kb kb_command
	and parse them.

	If it's not a valid command it returns
	a lot of None
'''

def parse_kb_arguments(argument,source):
	cmd = reason = targetnick = bantime = bantime_int = None

	try:
		(cmd, targetnick) = argument.split(' ')
	except ValueError:
		pass
	except Exception:
		return (None,None,None,None)

	if not cmd:
		try:
			(cmd, targetnick, bantime) = argument.split(' ')
		except Exception:
			return (None,None,None,None)

	if not cmd in Settings.kb_commands:
		return (None,None,None,None)

	try:
		bantime_int = int(bantime)
	except TypeError:
		bantime_int = None

	if not bantime_int:
		bantime_int = int(Settings.kb_commands[cmd][1])

	reason = "%s (%d) /%s" % (Settings.kb_commands[cmd][0], bantime_int, source)

	return (cmd,reason,targetnick,bantime_int)





'''

	Ban someone

	The functions handels the creation of the banmask so
	it's unique to the user and the accuall commands to
	the irc-server

'''
def match_banmask(client, targetnick, banmask, channel):
	matches = []
	print "** testing %s in %s" % (banmask, channel)
	banmask = banmask.replace('*','.*?')
	for user in client.users_list:
		if not channel in client.nick_lists.keys():
			print "\t unkown channel"
			continue
		if not extract_nick(user) in client.nick_lists[channel]:
			print "\t ignore user not in %s" % channel
			continue
		if extract_nick(user) == targetnick:
			print "\t ignore target user"
			continue
		try:
			m = re.search(banmask,user)
			if m:
				print "'%s' -> '%s' OK", (banmask, user)
				matches.append(user)
		except Exception, e:
			print "ERROR when regexing: %s" % e

	print "\t found %s matches" % len(matches)
	return matches

def create_banmask(client, targetnick):
	if targetnick not in client.users_list:
		# FIXME: get correct banmask adhoc
		print "ERROR: Unknown user :("
		return None

	targethost = client.users_list[targetnick]

	m = re.search('^(.+)@(.+)', targethost)
	if not m:
		print "ERROR: regex failed for %s" % targethost
		return targethost

	user = m.group(1)
	host = m.group(2)

	print "user: %s  host: %s" % (user,host)

	# FIXME: clean up below and remove redundant code

	# try a wide mask first
	hits = 0
	for channel in Settings.kb_channels:
		banmask = '*!*@*.%s' % '.'.join(host.split('.')[1:])
		hits += len(match_banmask(client, targetnick, banmask, channel))
	if hits == 0:
		return banmask

	# narrow it down a bit
	hits = 0
	for channel in Settings.kb_channels:
		banmask = '*!*%s@*.%s' % (user,'.'.join(host.split('.')[1:]))
		hits += len(match_banmask(client, targetnick, banmask, channel))
	if hits == 0:
		return banmask

	# narrow it down a bit more
	hits = 0
	for channel in Settings.kb_channels:
		banmask = '*!*@%s' % (host)
		hits += len(match_banmask(client, targetnick, banmask, channel))
	if hits == 0:
		return banmask

	# if everything else failed use this
	banmask = '*!*%s*@%s' % (user,host)

	return banmask

def get_punish_factor(banmask):
	Settings.db_cur.execute("SELECT count(*) FROM landlady_banmem WHERE targethost = ? AND network = ", (banmask, network))
	try:
		count = int(Settings.db_cur.fetchone()[0])
	except Exception, e:
		print "ERROR: Couldn't get ban count: %s"
		return 1

	if count >= len(Settings.kb_settings['ban_timemul']):
		count = len(Settings.kb_settings['ban_timemul'])-1

	return Settings.kb_settings['ban_timemul'][count]



def kickban(bot, network, targetnick, banmask, reason, duration, sourcenick, command):
	client = bot.clients[network]

	# save kb to memory
	Settings.db_cur.execute("INSERT INTO landlady_banmem (timestamp, network targetnick, targethost, command, sourcenick, duration) VALUES (strftime('%s',?,?,?,?,?,?))", (network, targetnick, banmask, command, sourcenick, duration))
	Settings.db_con.commit()

	# kick and ban user in all channels
	for channel in Settings.kb_settings['child_chans']:
		client.send('MODE %s +b %s' % (channel, banmask))
		client.send('KICK %s %s :%s' % (channel, targetnick, reason))
		bot.add_timer(datetime.timedelta(0, duration), False, client.send, 'MODE %s -b %s' % (channel, banmask))








'''

	handle swarm messages and stuff

	The following functions handles voting and also decides
	if a action is to be taken depending on a keyword

'''
def update_swarn_range(swarm_range, vote):
	swarm_range = (min(Settings.swarm_range[0], vote), max(Settings.swarm_range[1], vote))

	return swarm_range


def parse_vote(argument):
	try:
		(vote_id_str, vote_value_str) = argument.split(' ')
	except Exception:
		return (None, None)

	try:
		vote_id = int(vote_id_str)
	except Exception:
		return (None, None)

	try:
		vote_value = int(vote_value_str)
	except Exception:
		return (None, None)

	return (vote_id, vote_value)


def get_swarm_range(Settings):
	sorted_swarm_votes = sorted(Settings.swarm_votes.values())
	my_index = sorted_swarm_votes.index(Settings.swarm_random)
	client_count = len(Settings.swarm_votes)

	buckets = [0]
	bucket_size = 256.0/(len(sorted_swarm_votes))
	curr_bucket = bucket_size
	for tmp in range(0,255):
	  if tmp > curr_bucket:
		buckets.append(tmp)
		curr_bucket = curr_bucket + bucket_size

	buckets.append(255)
	swarm_range = (buckets[my_index],buckets[my_index+1])

	return swarm_range
