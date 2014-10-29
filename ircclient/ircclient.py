from __future__ import with_statement
import sys
import socket
import re
import time
import datetime
import errno
import random
import string
import settings
import ssl

from autoreloader.autoreloader import AutoReloader

def timestamp():
	return datetime.datetime.now().strftime("[%H:%M:%S]")

class User():
	def __init__(self, nick, user, host):
		self.nick = nick
		self.user = user
		self.host = host
		self.nickuserhost = None

		self.channel_list = []
		self.__nuh()

	def __nuh(self):
		self.nickuserhost = "%s!%s@%s" % (self.nick, self.user, self.host)

	def add_channel(self, channel):
		if channel not in self.channel_list:
			self.channel_list.append(channel)

	def remove_channel(self, channel_name):
		for channel in self.channel_list:
			if channel.name == channel_name:
				self.channel_list.remove(channel)
				channel.remove_user(nick)
				break

	def change_nick(self, new_nick):
		self.nick = new_nick
		self.__nuh()

	def in_channel(self, channel_name):
		for channel in self.channel_list:
			if channel_name == channel.name:
				return True
		return False

class Ban():
	def __init__(self, banmask, banner_nick, timestamp):
		self.banmask = banmask
		self.banner_nick = banner_nick
		self.timestamp = timestamp

class Channel():
	def __init__(self, channel_name):
		self.name = channel_name
		self.user_list = []
		self.ban_list = []

	def add_user(self, user):
		if user not in self.user_list:
			self.user_list.append(user)

	def remove_user(self, nick):
		for user in user_list:
			if user.nick == nick:
				self.user_list.remove(user)

	def add_ban(self, banmask, banner_nick, timestamp):
		b = Ban(banmask, banner_nick, timestamp)
		self.ban_list.append(b)

	def remove_ban(self, banmask):
		for ban in self.ban_list:
			if ban.banmask == banmask:
				self.ban_list.remove(ban)

	def is_banned(self, banmask):
		for ban in self.ban_list:
			if ban.banmask == banmask:
				return True
		return False

	def has_nick(self, nick):
		for user in self.user_list:
			if nick == user.nick:
				return True
		return False



class Network():
	def __init__(self, network_name, mynick=None):
		self.name = network_name
		self.mynick = mynick
		self.all_users = []
		self.all_channels = []

	def set_nick(self, nick):
		self.mynick = nick

	def user_by_nick(self, nick):
		for user in self.all_users:
			if user.nick == nick:
				return user
		raise Exception('No such user, %s' % nick)

	def channel_by_name(self, channel_name, create_if_new = True):
		for channel in self.all_channels:
			if channel.name == channel_name:
				return channel
		if create_if_new:
			c = Channel(channel_name)
			self.all_channels.append(c)
			return c
		else:
			raise Exception('No such channel, %s' % channel_name)

	def __add_user_to_channel(self, nick, channel_name):
		c = self.channel_by_name(channel_name)
		u = self.user_by_nick(nick)

		c.add_user(u)
		u.add_channel(c)

	def add_user(self, nickuserhost, channel_name = None):
		(nick, userhost) = nickuserhost.split('!')
		(user, host) = userhost.split('@')

		try:
			u = self.user_by_nick(nick)
		except Exception:
			u = User(nick, user, host)
		self.all_users.append(u)

		if channel_name:
			self.__add_user_to_channel(nick, channel_name)

	def del_user(self, nick):
		try:
			user = user_by_nick(nick)
			self.all_users.remove(user)
		except Exception:
			pass


	def nick_channels(self, nick):
		try:
			u = self.user_by_nick(nick)
			return u.channel_list
		except Exception:
			return []

	def part_nick(self, nick, channel_name):
		try:
			u = self.user_by_nick(nick)
			u.remove_channel(channel_name)
		except Exception:
			pass

	def user_change_nick(self, source_nick, new_nick):
		try:
			u = self.user_by_nick(source_nick)
		except Exception:
			return
		u.change_nick(new_nick)

	def channel_add_ban(self, channel_name, banmask, banner_nick, timestamp):
		c = self.channel_by_name(channel_name)
		c.add_ban(banmask, banner_nick, timestamp)

	def channel_remove_ban(self, channel_name, banmask):
		c = self.channel_by_name(channel_name)
		c.remove_ban(banmask)

class IRCClient(AutoReloader):
	def __init__(self, address, port, nick, username, realname, network, password):
		self.connected = False
		self.active_session = False
		# self.temp_nick_list_channel = None
		# self.temp_nick_list = None
		# self.nick_lists = {}
		# self.users_list = {}
		self.banlists = {}

		self.isupport = {}
		self.recv_buf = ''
		self.callbacks = {}
		self.throttle_errors = ['too fast, throttled','"host is trying to (re)connect too fast"']

		self.lines = []

		self.s = None


		self.nick = nick[random.randrange(0,len(nick)-1)]
		self.username = username or self.nick
		self.realname = realname
		self.network = network
		self.password = password


		self.net = Network(network)
		self.net.mynick = self.nick

		self.send_last_second = 0
		self.send_queue_history = [0]
		self.send_time = 0
		self.send_queue = []
		self.flood_protected = False

		self.command_queue = []

		self.wait_until = None

		self.irc_message_pattern = re.compile('^(:([^  ]+))?[   ]*([^  ]+)[  ]+:?([^  ]*)[   ]*:?(.*)$')
		self.message_handlers = {
			'JOIN': self.on_join,
			'KICK': self.on_kick,
			'NICK': self.on_nick,
			'PART': self.on_part,
			'QUIT': self.on_quit,
			'PING': self.on_ping,
			'PRIVMSG': self.on_privmsg,
			'NOTICE': self.on_notice,
			'ERROR': self.on_error,
			'MODE': self.on_mode,
			'353': self.on_begin_nick_list,
			'366': self.on_end_nick_list,
			'001': self.on_connected,
			'433': self.on_nick_inuse,
			'302': self.on_userhost,
			'005': self.on_isupport,
			'367': self.on_banlist,
			'368': self.on_endofbanlist,
			'352': self.on_whoreply,
		}

		self.server_address = address;
		self.server_port = port;



	def __execute_command_queue(self):
		if len(self.command_queue) > 0:
			for command in self.command_queue:
				if time.time() - command['timestamp'] > 5:
					try:
						command['command']
						self.command_queue.remove(command)
					except Exception:
						pass


	def connect(self, address, port):
		self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		self.active_session = False
		self.ping_count = 0

		try:
			if settings.Settings().networks[self.network].setdefault("ssl", False):
				self.s = ssl.wrap_socket(self.s)
		except Exception, ex:
			print timestamp() + " " + self.network + " Connection with SSL failed, " + str(ex)

		try:
			self.s.connect((address, port))
			self.connected = True
		except Exception, ex:
			print timestamp() + " " + self.network + " Connect failed, " + str(ex)
			self.connected = False

		if self.connected:
			self.s.setblocking(False)

		return self.connected

	def log_line(self, line):
		try:
			print line
		except UnicodeEncodeError:
			# FIXME use bot.settings/rebuild settings
			print line.encode(settings.Settings().recode_fallback, "replace")
		self.lines.append(line)

	def send(self, line):
		self.send_queue.append(line+"\r\n")
		self.real_send()

	def real_send(self):
		#self.log_line(timestamp() + " " + self.network + " SEND: send_queue length %s" % len(self.send_queue))
		current_second = int(time.time())

		if not self.send_queue:
			#self.log_line(timestamp() + " " + self.network + " SEND: Sendqueue empty")
			return None

		if self.send_last_second != current_second:
			if len(self.send_queue_history) >= 10:
				self.send_queue_history.pop(0)
			self.send_queue_history.append(0)

		if len(self.send_queue_history) == 0:
			self.send_queue_history.append(0)

		if self.flood_protected:
			if time.time() - self.send_time < 10:
				#self.log_line(timestamp() + " " + self.network + " SEND: too early %s" % (time.time()-self.send_time))
				return None


		if sum(self.send_queue_history) >= 4:
			self.flood_protected = True
			#self.log_line(timestamp() + " " + self.network + " SEND: flood_protected TRUE %s, current_second %d last_second %d" % (self.send_queue_history, current_second, self.send_last_second))
			return None
		else:
			#self.log_line(timestamp() + " " + self.network + " SEND: flood_protected FALSE")
			self.flood_protected = False

		data = self.send_queue.pop(0)
		self.log_line(timestamp() + " " + self.network + " SEND: (%d) %s" % (len(self.send_queue), str(data).replace("\r\n","")))

		try:
			sent =  self.s.send(data.encode(settings.Settings().recode_out_default_charset))
		except UnicodeDecodeError:
			# String is probably not unicode, print warning and just send it
			print
			print "WARNING IRCClient send called with non unicode string, fix this!"
			print
			sent = self.s.send(data)
		except UnicodeEncodeError:
			# Try fallback coding instead
			sent =  self.s.send(data.encode(settings.Settings().recode_fallback, "ignore"))

		self.send_queue_history[-1] += 1
		self.send_time = time.time()
		self.send_last_second = int(self.send_time)
		return len(data)

	def is_connected(self):
		return self.connected

	def tell(self, target, string):
		if len(string) >= 399:
			string = string[0:399]

		split = len(string) - 1

		if split >= 400:
			split = 400
			while split > 350:
				if string[split] == ' ':
					break
				split -= 1

			a = string[0:split]
			b = string[split:]

			return self.tell(target, a) + self.tell(target, b)
		else:
			return self.send("PRIVMSG " + target + " :" + string)

	def join(self, channel, password=""):
		return self.send('JOIN ' + channel + ' ' + password)

	def get_nick(self, host):
		m = re.search('^:?(\S+?)!', host)
		if m:
			return m.group(1)
		else:
			return host

	def on_begin_nick_list(self, tupels):
		# m = re.search('. (.+?) :(.*)$', tupels[5])

		# if m:
		# 	channel, nicks = m.group(1, 2)

		# 	if self.temp_nick_list_channel != channel:
		# 		self.temp_nick_list_channel = channel
		# 		self.temp_nick_list = {}

		# 	for m in re.findall('([^a-zA-Z\[\]{}]?)(.+?)(\s|$)', nicks):
		# 		# legacy #
		# 		# prefix, nick = m[0:2]
		# 		# self.temp_nick_list[nick] = {'prefix':prefix}
		# 		# legacy #
		pass


	def on_end_nick_list(self, tupels):
		#self.nick_lists[self.temp_nick_list_channel] = self.temp_nick_list
		pass

	def on_join(self, tupels):
		source, channel = [tupels[1].replace(':',''), tupels[4]]

		# if we join a channel send a WHO command to get hosts
		nick = self.get_nick(source)
		if nick == self.nick:
			self.send("WHO %s" % channel)
			self.send("MODE %s +b" % channel)
		else:
			# if channel not in self.nick_lists:
			# 	self.nick_lists[channel] = {}
			# self.nick_lists[channel][nick] = {'prefix':''}
			# self.users_list[nick] = source
			self.net.add_user(source, channel)

		if "on_join" in self.callbacks:
			self.callbacks["on_join"](self.network, source, channel)

	def on_kick(self, tupels):
		source, channel = [tupels[1], tupels[4]]
		target_nick = None

		m = re.search('^([^ ]+)', tupels[5])
		if m:
			target_nick = m.group(1)

		self.net.part_nick(target_nick, channel)
		# if channel in self.nick_lists:
		# 	if target_nick in self.nick_lists[channel]:
		# 		del(self.nick_lists[channel][target_nick])

		if "on_kick" in self.callbacks:
			self.callbacks["on_kick"](self.network, source, channel, target_nick)

	def on_nick(self, tupels):
		source, new_nick = [tupels[1], tupels[4]]

		if "on_nick_change" in self.callbacks:
			self.callbacks["on_nick_change"](self.network, source, new_nick)

		source_nick = self.get_nick(source)

		try:
			self.net.user_change_nick(source_nick, new_nick)
		except Exception:
			self.command_queue.append({'timestamp':time.time(), 'command': self.net.user_change_nick(source_nick, new_nick)})

		# if source_nick in self.users_list.keys():
		# 	self.users_list[new_nick] = self.users_list[source_nick]
		# 	del self.users_list[source_nick]

		# for nick_list in self.nick_lists.values():
		# 	if source_nick in nick_list:
		# 		nick_list[new_nick] = nick_list[source_nick]
		# 		del(nick_list[source_nick])

	def on_mode(self, tupels):
		if len(tupels) == 7:
			source, channel, mode, target = [tupels[2],tupels[4],tupels[5].split(' ',2)[0],tupels[5].split(' ',2)[1]]
		elif len(tupels) == 6:
			source, channel, mode = [tupels[2],tupels[4],tupels[5].split(' ',2)[0]]
			target = ''

		if mode == '+b':
			self.net.channel_add_ban(channel, target, source, int(time.time()))
		elif mode == '-b':
			self.net.channel_remove_ban(channel, target)


		if "on_mode" in self.callbacks:
			self.callbacks["on_mode"](source, channel, mode, target, self.net)

	def on_userhost(self, tupels):
		message = tupels[5]
		userhosts = tupels[5].split(' ')
		# for userhost in userhosts:
		# 	m = re.search('^(.+)=\+?(.+@.*)$', userhost)
		# 	if m is not None:
		# 		self.users_list[m.group(1)] = m.group(2)

		if "on_userhost" in self.callbacks:
			self.callbacks["on_userhost"]()

	def on_nick_inuse(self, tuples):
		newnick = self.nick[:6] + "".join([random.choice(string.ascii_letters + string.digits + "-") for i in xrange(3)])
		self.send("NICK " + newnick)
		self.nick = newnick
		self.net.mynick = newnick

	def on_part(self, tupels):
		source, channel, reason = [tupels[1], tupels[4], tupels[5]]

		source_nick = self.get_nick(source)
		self.net.part_nick(source_nick, channel)

		if "on_part" in self.callbacks:
			self.callbacks["on_part"](self.network, source, channel, reason)

		# if channel in self.nick_lists:
		# 	if source_nick in self.nick_lists[channel]:
		# 		del(self.nick_lists[channel][source_nick])

		# last_channel = True
		# for chan_nick_list in self.nick_lists.values():
		# 	if source_nick in chan_nick_list:
		# 		last_channel = False

		if len(self.net.nick_channels(source_nick)) == 0:
			self.net.del_user(source_nick)
			# if source_nick in self.users_list:
			# 	del(self.users_list[source_nick])

	def on_quit(self, tupels):
		source = tupels[1]
		reason = tupels[4]

		if tupels[5]:
			reason += ' ' + tupels[5]

		source_nick = self.get_nick(source)

		if "on_quit" in self.callbacks:
			self.callbacks["on_quit"](self.network, source_nick, reason)

		# for nick_list in self.nick_lists.values():
		# 	if source_nick in nick_list:
		# 		del(nick_list[source_nick])

		self.net.del_user(source_nick)
		# if source_nick in self.users_list.keys():
		# 	del self.users_list[source_nick]


	def on_ping(self, tupels):
		self.ping_count += 1
		self.send("PONG :" + tupels[4])

	def on_privmsg(self, tupels):
		source, target, message = tupels[2], tupels[4], tupels[5]

		if target[0] != '#':
			target = source

		if "on_privmsg" in self.callbacks:
			self.callbacks["on_privmsg"](self.network, source, target, message)

	def on_notice(self, tupels):
		source, target, message = tupels[2], tupels[4], tupels[5]

		if target[0] != '#':
			target = source

		if "on_notice" in self.callbacks:
			self.callbacks["on_notice"](self.network, source, target, message)

	def on_connected(self, tupels):
		self.active_session = True

		if "on_connected" in self.callbacks:
			self.callbacks["on_connected"](self.network)

	def on_isupport(self,tupels):
		message = tupels[5][:tupels[5].index(':')]
		isupport = {}
		for item in message.split(' '):
			keyval = item.split('=')
			if len(keyval) == 1:
				key = keyval[0]
				val = True
			else:
				key = keyval[0]
				val = keyval[1]

			isupport[key] = val
		self.isupport.update(isupport)

	def on_banlist(self,tupels):
		(channel, banmask, banner, timestamp) = tupels[5].split(' ')
		self.net.channel_add_ban(channel, banmask, banner, timestamp)
		# if channel not in self.banlists:
		# 	self.banlists[channel] = {}
		# self.banlists[channel][banmask] = (banner, timestamp)
		#print "** BANLIST %s %s %s ==> %s" % (banmask, banner, timestamp, self.banlists[channel][banmask])

		if "on_banlist" in self.callbacks:
			self.callbacks["on_banlist"](self.network, channel, banmask, banner, timestamp)

	def on_endofbanlist(self,tupels):
		channel = tupels[5].split(' ')[0]
		# if channel not in self.banlists:
		# 	self.banlists[channel] = {}
		# self.banlists[channel]['AGE'] = time.time()

		#print "** END OF BANLIST %s ==> %s" % (channel, self.banlists[channel])
		if "on_endofbanlist" in self.callbacks:
			self.callbacks["on_endofbanlist"](self.network, channel)

	def on_error(self, tupels):
		message = tupels[5]
		print 'the irc server informs of an error:', message

		if message in self.throttle_errors:
			self.idle_for(120)
		else:
			raise "SERVER ERROR, %s" % message

	def on_whoreply(self, tupels):
		reply = tupels[5].split(' ')

		channel = reply[0]
		user = reply[1]
		hostname = reply[2]
		server = reply[3]
		nick = reply[4]
		prefix = reply[5].replace('H','')

		#self.log_line(timestamp() + " " + self.network + " WHO: %s!%s@%s (%s)" % (nick,user,hostname,prefix))

		# if not channel in self.nick_lists:
		# 	self.nick_lists[channel] = {}
		# self.nick_lists[channel][nick] = {'prefix':prefix}
		#self.users_list[nick] = "%s!%s@%s" % (nick,user,hostname)

		self.net.add_user("%s!%s@%s" % (nick,user,hostname), channel_name=channel)

		if "on_whoreply" in self.callbacks:
			self.callbacks["on_whoreply"](self.network)

	def idle_for(self, seconds):
		self.wait_until = datetime.datetime.now() + datetime.timedelta(0, seconds)

	def tick(self):
		now = datetime.datetime.now()
		if self.wait_until and self.wait_until > now:
			self.log_line(timestamp() + " " + self.network + " TICK DEFFERED: %s > %s" % (self.wait_until, now))
			return

		if self.connected:
			# send data
			try:
				self.real_send()
			except Exception:
				pass

			try:
				self.__execute_command_queue()
			except Exception:
				pass

			try:
				retn = self.s.recv(1024)

				self.recv_buf += retn
				recv_lines = self.recv_buf.splitlines(True)
				self.recv_buf = ''
				for line in recv_lines:
					if not line.endswith("\r\n"):
						self.recv_buf = line
					else:
						line = line.rstrip("\r\n")
						#self.log_line(timestamp() + " " + self.network + " RECV: " + line)
						m = self.irc_message_pattern.match(line)
						if m:
							if m.group(3) in self.message_handlers:
								self.message_handlers[m.group(3)](m.group(0, 1, 2, 3, 4, 5))

			except ssl.SSLError, (error_code, error_message):
				if error_code != errno.EWOULDBLOCK and error_code != errno.ENOENT:
					self.connected = False
					print (error_code, error_message)
			except socket.error, (error_code, error_message):
				if error_code != errno.EWOULDBLOCK:
					self.connected = False
					print (error_code, error_message)
		else:
			self.log_line(timestamp() + " " + self.network + " TICK (not connected): %s > %s" % (self.wait_until, now))
			try:
				self.connect(self.server_address, self.server_port)
			except socket.error, (error_code, error_message):
				print "I got an error while trying to connect... Is it wrong to just return now?", (error_code, error_message)
				self.idle_for(60)
				return

			if self.connected:
				if self.password is not None:
					self.send("PASS %s" % self.password)
				self.send("USER %s * * :%s" % (self.username, self.realname))
				self.send("NICK %s" % self.nick)
