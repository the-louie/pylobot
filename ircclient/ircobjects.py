class User():
	def __init__(self, nick, user, host):
		self.nick = nick
		self.user = user
		self.host = host
		self.nickuserhost = None
		self.last_nick = None
		self.online = True

		self.channel_list = []
		self.__nuh()

	def __nuh(self):
		self.nickuserhost = "%s!%s@%s" % (self.nick, self.user, self.host)

	def __str__(self):
		return "%s!%s@%s in %d channels" % (self.nick, self.user, self.host, len(self.channel_list))

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
		self.last_nick = self.nick
		self.nick = new_nick
		self.__nuh()

	def update(self, nick, user, host):
		self.nick = nick
		self.user = user
		self.host = host
		self.__nuh()

	def in_channel(self, channel_name):
		for channel in self.channel_list:
			if channel_name == channel.name:
				return True
		return False

	def channel_flags(self, channel_name):
		for channel in self.channel_list:
			if channel_name == channel.name:
				return channel.get_flags(self.nick)
		return None

	def has_op(self, channel_name):
		return "@" in (self.channel_flags(channel_name) or "")

	def has_voice(self, channel_name):
		return "+" in (self.channel_flags(channel_name) or "")

	def quit(self):
		self.online = False

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
		self.flag_list = {}

	def add_user(self, user):
		if user not in self.user_list:
			self.user_list.append(user)

	def add_flags(self, nick, flags):
		if flags == None:
			return
		self.flag_list[nick] = flags

	def add_flag(self, nick, flag):
		if flag == None:
			return
		if nick in self.flag_list:
			self.flag_list[nick] += flag
		else:
			self.flag_list[nick] = flag

	def remove_flag(self, nick, flag):
		if flag == None:
			return
		if nick in self.flag_list:
			self.flag_list = self.flag_list.replace(flag, '')

	def get_flags(self, nick):
		if nick in self.flag_list:
			return self.flag_list[nick]
		else:
			return None

	def has_op(self, nick):
		return "@" in (self.get_flags(nick) or "")

	def has_voice(self, nick):
		return "+" in (self.get_flags(nick) or "")

	def remove_user(self, nick):
		for user in user_list:
			if user.nick == nick:
				self.user_list.remove(user)

		if nick in self.flag_list:
			del self.flag_list[nick]

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

class Server():
	def __init__(self, network_name, mynick=None):
		self.name = network_name
		self.mynick = mynick
		self.all_users = []
		self.all_channels = []
		self.isupport = {}
		self.me = None

	def set_nick(self, nick):
		self.mynick = nick

	def user_by_nick(self, nick):
		for user in self.all_users:
			if user and user.nick == nick:
				return user
		return None

	def channel_by_name(self, channel_name, create_if_new = True):
		for channel in self.all_channels:
			if channel.name == channel_name:
				return channel
		if create_if_new:
			c = Channel(channel_name)
			self.all_channels.append(c)
			return c
		else:
			return None

	def __add_user_to_channel(self, nick, channel_name, flags):
		c = self.channel_by_name(channel_name)
		if c is None:
			return False

		u = self.user_by_nick(nick)
		if u is None:
			return False

		c.add_user(u)
		c.add_flags(nick, flags)
		u.add_channel(c)

		return True

	def add_user(self, nickuserhost, channel_name = None, flags = None):
		(nick, userhost) = nickuserhost.split('!')
		(user, host) = userhost.split('@')

		u = self.user_by_nick(nick)
		if u is None:
			u = User(nick, user, host)
			self.all_users.append(u)
		else:
			u.update(nick, user, host)

		if nick == self.mynick:
			self.me = u

		if channel_name:
			self.__add_user_to_channel(nick, channel_name, flags)

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

		try:
			c = self.channel_by_name(channel_name)
			c.remove_user(nick)
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