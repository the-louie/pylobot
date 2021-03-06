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
import sqlite3

from autoreloader.autoreloader import AutoReloader

from ircobjects import User,Ban, Channel, Server
from swarm import Swarm

import irclog
import logging
import logging.handlers
logger = logging.getLogger('landlady')


def timestamp():
    return datetime.datetime.now().strftime("[%H:%M:%S]")

class IRCClient(AutoReloader):
    def __init__(self, bot, address, port, nick, username, realname, password):
        # connect to db
        try:
            self.dbcon = sqlite3.connect('data/landlady.db')
            self.dbcur = self.dbcon.cursor()
            self.dbcur.execute("CREATE TABLE IF NOT EXISTS nick_log (nick TEXT, usecount INT, last_used timestamp)")
            self.dbcon.commit()
        except Exception, e:
            logger.error("ERROR: Couldn't open database, %s" % e)
            sys.exit(1)

        # setup irc loghandler
        logging.handlers.IRCHandler = irclog.IRCHandler
        ircHandler = logging.handlers.IRCHandler(self.send)
        ircHandler.setLevel(logging.ERROR)
        logger.addHandler(ircHandler)
        self.log_chan = bot.settings.server["log_channel"]

        self.connected = False
        self.active_session = False

        self.recv_buf = ''
        self.callbacks = {}
        self.throttle_errors = ['too fast, throttled','"host is trying to (re)connect too fast"']

        self.s = None

        self.availible_bot_nicks = nick
        self.nick_blacklist = []
        self.nick = self.__get_nick__()

        self.server_address = address
        self.server_port = port
        self.username = username or self.nick
        self.realname = realname
        self.password = password

        self.server = Server("server")
        self.server.mynick = self.nick

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

        self.swarm = Swarm(bot, self)
        self.swarm_enabled = True

        self.deferred_join_all = bot.settings.deferred_join_all
        self.deferred_join_swarm = bot.settings.deferred_join_swarm



    def __execute_command_queue(self):
        if len(self.command_queue) > 0:
            for command in self.command_queue:
                if time.time() - command['timestamp'] > 5:
                    try:
                        command['command']
                        self.command_queue.remove(command)
                    except Exception:
                        pass

    def __get_nick__(self):
        self.dbcur.execute("SELECT nick FROM nick_log ORDER BY usecount, last_used")
        rows = self.dbcur.fetchall()
        nicks = []
        for r in rows:
            if r[0] not in self.nick_blacklist:
                nicks.append(rows[0])

        if len(nicks) > 0:
            return nicks[0][0]
        else:
            return self.availible_bot_nicks[random.randrange(0,len(self.availible_bot_nicks)-1)]

    def __remember_nick__(self):
        self.dbcur.execute("SELECT count(*) as c from nick_log WHERE nick like ?", (self.server.mynick,))
        rows = self.dbcur.fetchall()
        if rows[0][0] == 0:
            self.dbcur.execute("INSERT INTO nick_log (nick, usecount, last_used) VALUES (?, 1, CURRENT_TIMESTAMP)", (self.server.mynick,))
        else:
            self.dbcur.execute("UPDATE nick_log SET usecount=usecount+1, last_used=CURRENT_TIMESTAMP WHERE nick LIKE ?", (self.server.mynick,))

        self.dbcon.commit()

    def connect(self, address, port):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.active_session = False
        self.ping_count = 0

        # FIXME: SSL CODE COMMENTED HERE; HALP!
        # try:
        #     if settings.Settings().networks[self.network_name].setdefault("ssl", False):
        #         self.s = ssl.wrap_socket(self.s)
        # except Exception, ex:
        #     print timestamp() + " " + self.network_name + " Connection with SSL failed, " + str(ex)

        try:
            self.s.connect((address, port))
            self.connected = True
        except Exception, ex:
            logger.error(timestamp() + " " + " Connect failed, " + str(ex))
            self.connected = False

        if self.connected:
            self.s.setblocking(False)

        return self.connected


    def log_send(self, line):
        self.send("PRIVMSG " + self.log_chan + " :" + line)

    def send(self, line):
        self.send_queue.append(line+"\r\n")
        return self.real_send()

    def real_send(self):
        current_second = int(time.time())

        if not self.send_queue:
            return None

        if len(self.send_queue) > 30:
            logger.error("Send queue > 30, discarding message.")
            return None

        if self.send_last_second != current_second:
            if len(self.send_queue_history) >= 11:
                self.send_queue_history.pop(0)
            self.send_queue_history.append(0)

        if len(self.send_queue_history) == 0:
            self.send_queue_history.append(0)

        if self.flood_protected:
            if time.time() - self.send_time < 11:
                return None


        if sum(self.send_queue_history) >= 3:
            self.flood_protected = True
            return None
        else:
            self.flood_protected = False

        data = self.send_queue.pop(0)
        logger.info("SEND: (sq:%d) %s", len(self.send_queue), str(data).replace("\r\n",""))

        try:
            sent =  self.s.send(data.encode(settings.Settings().recode_out_default_charset))
        except UnicodeDecodeError:
            # String is probably not unicode, print warning and just send it
            logger.warn("WARNING IRCClient send called with non unicode string, fix this!")
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
        pass


    def on_end_nick_list(self, tupels):
        pass

    def on_join(self, tupels):
        source, channel = [tupels[1].replace(':',''), tupels[4]]

        nick = self.get_nick(source)

        # add user to network
        self.server.add_user(source, channel)

        # if we join a channel send a WHO command to get hosts
        if nick == self.nick:
            self.send("WHO %s" % channel)
            self.send("MODE %s +b" % channel)
            if self.swarm_enabled and channel==self.swarm.channel:
                self.swarm.swarmchan_join()

        chan_obj = self.server.channel_by_name(channel)
        user_obj = self.server.user_by_nick(nick)

        event = {
            'client': self,
            'channel': chan_obj,
            'user': user_obj,
            'swarm_match': self.swarm.nick_matches(nick)
        }

        if "on_join" in self.callbacks:
            self.callbacks["on_join"](event)

    def on_kick(self, tupels):
        source, channel = [tupels[1], tupels[4]]
        target_nick = None

        m = re.search('^([^ ]+)', tupels[5])
        if m:
            target_nick = m.group(1)

        self.server.part_nick(target_nick, channel)


        event = {
            'client': self,
            'channel': self.server.channel_by_name(channel),
            'source_user': self.server.user_by_nick(source),
            'target_user': self.server.user_by_nick(target_nick),
            'reason': '',
            'swarm_match': self.swarm.nick_matches(target_nick)
        }

        if "on_kick" in self.callbacks:
            self.callbacks["on_kick"](event)

    def on_nick(self, tupels):
        source, new_nick = [tupels[1], tupels[4]]

        source_nick = self.get_nick(source)

        try:
            self.server.user_change_nick(source_nick, new_nick)
        except Exception:
            pass

        event = {
            'client': self,
            'user': self.server.user_by_nick(new_nick),
            'swarm_match': self.swarm.nick_matches(new_nick)
        }

        if "on_nick" in self.callbacks:
            self.callbacks["on_nick"](event)


    def on_mode(self, tupels):
        if len(tupels) == 7:
            source, channel, mode, target = [tupels[2],tupels[4],tupels[5].split(' ',2)[0],tupels[5].split(' ',2)[1]]
        elif len(tupels) == 6:
            source, channel, mode = [tupels[2],tupels[4],tupels[5].split(' ',2)[0]]
            if len(tupels[5].split(' ',2)) == 2:
                target = tupels[5].split(' ',2)[1]
            else:
                target = ''

        if channel[0] != '#':
            target = channel
            channel = ""


        source_nick = self.get_nick(source)

        if channel != "":
            if mode == '+b':
                self.server.channel_add_ban(channel, target, source, int(time.time()))
            elif mode == '-b':
                self.server.channel_remove_ban(channel, target)
            elif mode == '+v':
                try:
                    c = self.server.channel_by_name(channel)
                    c.add_flag(target, '+')
                except Exception:
                    pass
            elif mode == '-v':
                try:
                    c = self.server.channel_by_name(channel)
                    c.remove_flag(target, '+')
                except Exception:
                    pass
            elif mode == '+o':
                try:
                    c = self.server.channel_by_name(channel)
                    c.add_flag(target, '@')
                except Exception:
                    pass
            elif mode == '-o':
                try:
                    c = self.server.channel_by_name(channel)
                    c.remove_flag(target, '@')
                except Exception:
                    pass

        event = {
            'client': self,
            'channel': self.server.channel_by_name(channel),
            'source_user': self.server.user_by_nick(source_nick),
            'target_user': self.server.user_by_nick(target),
            'mode': mode,
            'swarm_match': self.swarm.nick_matches(target)
        }

        if "on_mode" in self.callbacks:
            self.callbacks["on_mode"](event)

    def on_userhost(self, tupels):
        message = tupels[5]
        userhosts = tupels[5].split(' ')

        if "on_userhost" in self.callbacks:
            self.callbacks["on_userhost"]()

    def on_nick_inuse(self, tuples):
        oldnick = self.server.mynick
        self.nick_blacklist.append(oldnick)
        newnick = self.__get_nick__()
        #newnick = self.availible_bot_nicks[random.randrange(0,len(self.availible_bot_nicks)-1)]
        self.send("NICK " + newnick)
        self.nick = newnick
        self.server.mynick = newnick

        event = {
            'client': self,
            'nick': oldnick,
            'swarm_match': None
        }

        if "on_nick_inuse" in self.callbacks:
            self.callbacks["on_nick_inuse"](event)

    def on_part(self, tupels):
        source, channel_name, reason = [tupels[1], tupels[4], tupels[5]]

        source_nick = self.get_nick(source)
        self.server.part_nick(source_nick, channel_name)

        if len(self.server.nick_channels(source_nick)) == 0:
            self.server.del_user(source_nick)

        try:
            user_obj = self.server.user_by_nick(source_nick)
        except:
            user_obj = None

        if channel_name == self.swarm.channel:
            if source_nick == self.server.mynick:
                # we left the swarmchan, disable the swarm
                self.swarm.disable()
            else:
                # someone else left the swarmchan, remove them
                # if they were a bot
                self.swarm.swarmchan_part(source_nick)


        event = {
            'client': self,
            'user': user_obj,
            'nick': source_nick,
            'channel': self.server.channel_by_name(channel_name),
            'reason': reason,
            'swarm_match': self.swarm.nick_matches(source_nick)
        }

        if "on_part" in self.callbacks:
            self.callbacks["on_part"](event)


    def on_quit(self, tupels):
        source = tupels[1]
        reason = tupels[4]

        if tupels[5]:
            reason += ' ' + tupels[5]

        source_nick = self.get_nick(source)
        self.swarm.vote.remove_bot(source_nick)

        event = {
            'user': self.server.user_by_nick(source_nick),
            'nick': source_nick,
            'reason': reason,
            'swarm_match': self.swarm.nick_matches(source_nick)
        }

        if "on_quit" in self.callbacks:
            self.callbacks["on_quit"](event)

        self.server.del_user(source_nick)

    def on_ping(self, tupels):
        self.ping_count += 1
        self.send("PONG :" + tupels[4])


    def on_privmsg(self, tupels):
        source, target, message = tupels[2], tupels[4], tupels[5]
        source_nick = self.get_nick(source)

        source_nick = self.get_nick(source)
        source_obj = self.server.user_by_nick(source_nick)
        if source_obj is None: # havn't seen this user before, might be a message from someone not in any channel
            source_obj = self.server.add_user(source)

        if target[0] == '#': # target is a channel, it's a public message
            target_obj = self.server.channel_by_name(target)
        else: # it's a private message, target is me!
            target_obj = None



        # if source is not None:
        #     source_nick = self.get_nick(source)
        #     source_user = self.server.user_by_nick(source_nick)

        #     if target[0] == '#':
        #         if source_user is None:
        #             source_user = self.server.add_user(source, target)
        #         target_obj = self.server.channel_by_name(target)
        #     else:
        #         target_obj = None



        # else:
        #     source_user = None


        if target == self.swarm.channel and message.split(' ')[0] == '.vote':
            self.swarm.incoming_vote(source_obj, target, message.split(' ')[1:])
        if target == self.swarm.channel and message.split(' ')[0] == '.verify':
            self.swarm.incoming_verification(source_obj, target, message.split(' ')[1:])
        if target == self.swarm.channel and message.split(' ')[0] == '.verifail':
            self.swarm.incoming_verification(source_obj, target, message.split(' ')[1:])

        event = {
            "client": self,
            "source": source_obj,
            "target": target_obj,
            "message": message,
            'swarm_match': self.swarm.nick_matches(source_nick)
        }

        if "on_privmsg" in self.callbacks:
            self.callbacks["on_privmsg"](event)

    def on_notice(self, tupels):
        source, target, message = tupels[2], tupels[4], tupels[5]

        source_nick = None
        if source is not None:
            source_nick = self.get_nick(source)

            if target[0] == '#':
                target = self.server.channel_by_name(target)
            else:
                target = None

            source_user = self.server.user_by_nick(source_nick)
        else:
            source_user = None

        event = {
            "client": self,
            "user": source_user,
            "target": target,
            "message": message,
            'swarm_match': self.swarm.nick_matches(source_nick)
        }

        if "on_notice" in self.callbacks:
            self.callbacks["on_notice"](event)

    def on_connected(self, tupels):
        self.active_session = True

        self.send('WHO %s' % (self.server.mynick))

        self.__remember_nick__()

        self.swarm.on_connected()

        event = {
            "client": self,
            "server": self.server,
            "swarm_match": None
        }

        if "on_connected" in self.callbacks:
            self.callbacks["on_connected"](event)

    def on_isupport(self,tupels):
        # http://www.irc.org/tech_docs/005.html
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

        self.server.isupport.update(isupport)

    def on_banlist(self,tupels):
        (channel, banmask, banner, timestamp) = tupels[5].split(' ')
        self.server.channel_add_ban(channel, banmask, banner, timestamp)

    def on_endofbanlist(self,tupels):
        channel_name = tupels[5].split(' ')[0]

        event = {
            "client": self,
            "channel": self.server.channel_by_name(channel_name),
            "swarm_match": None
        }

        if "on_endofbanlist" in self.callbacks:
            self.callbacks["on_endofbanlist"](event)

    def on_error(self, tupels):
        message = tupels[5]
        logger.error('the irc server informs of an error: %s', message)

        if message in self.throttle_errors:
            self.idle_for(120)
        else:
            raise Exception("SERVER ERROR: " + message)

    def on_whoreply(self, tupels):
        reply = tupels[5].split(' ')

        channel = reply[0]
        user = reply[1]
        hostname = reply[2]
        server = reply[3]
        nick = reply[4]
        prefix = reply[5].replace('H','')

        if nick == self.server.mynick:
            self.server.add_user("%s!%s@%s" % (nick,user,hostname))
            self.me = self.server.user_by_nick(self.nick)

        self.server.add_user("%s!%s@%s" % (nick,user,hostname), channel, prefix)


    def idle_for(self, seconds):
        self.wait_until = datetime.datetime.now() + datetime.timedelta(0, seconds)

    def tick(self):
        now = datetime.datetime.now()
        if self.wait_until and self.wait_until > now:
            logger.debug("TICK DEFERED: %s > %s", self.wait_until, now)
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
                        m = self.irc_message_pattern.match(line)
                        if m:
                            if m.group(3) in self.message_handlers:
                                self.message_handlers[m.group(3)](m.group(0, 1, 2, 3, 4, 5))

            except ssl.SSLError, (error_code, error_message):
                if error_code != errno.EWOULDBLOCK and error_code != errno.ENOENT:
                    self.connected = False
                    logger.error("%s %s", error_code, error_message)
            except socket.error, (error_code, error_message):
                if error_code != errno.EWOULDBLOCK:
                    self.connected = False
                    logger.error("%s %s", error_code, error_message)
        else:
            logger.info("TICK (not connected): %s > %s", self.wait_until, now)
            try:
                self.connect(self.server_address, self.server_port)
            except socket.error, (error_code, error_message):
                logger.error("I got an error while trying to connect... Is it wrong to just return now? %s %s", (error_code, error_message))
                self.idle_for(60)
                return

            if self.connected:
                if self.password is not None:
                    self.send("PASS %s" % self.password)
                self.send("USER %s * * :%s" % (self.username, self.realname))
                self.send("NICK %s" % self.nick)
