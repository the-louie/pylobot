import re
from utility import extract_nick
from ll_settings import landladySettings as Settings

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

def kickban(client, targetnick, banmask, reason, duration):
	client = bot.clients[network]

	for channel in Settings.kb_channels:
		client.send('MODE %s +b %s' % (channel, banmask))
		client.send('KICK %s %s :%s' % (channel, targetnick, reason))
		bot.add_timer(datetime.timedelta(0, duration), False, client.send, 'MODE %s -b %s' % (channel, banmask))
