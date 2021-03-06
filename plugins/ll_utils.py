import re
#from utility import extract_nick
from ll_settings import landladySettings as DefaultSettings
import sys
import sqlite3
import copy
import time
import datetime
import base64
import logging
logger = logging.getLogger('landlady')

#from ll_swarm import Swarm

class Settings():
    def __init__(self):
        self.kb_commands = {}
        self.kb_settings = {}
        self.swarm = {}
        self.general = {}
        self.fenrus = {}

class LLUtils():
    def __init__(self):
        self.Settings = Settings()
        #self.Swarm = Swarm

        self.bot = None
        self.client = None
        self.dbcon = None
        self.dbcur = None
        self.db_connect()


    '''

        Connect to db and if needed populate it with
        the default values from ll_settings.py

    '''
    def db_real_connect(self):
        if (self.dbcon) and (self.dbcur):
            logger.error("Already connected to db.")
            return True

        # connect to db
        try:
            self.dbcon = sqlite3.connect('data/landlady.db')
            self.dbcur = self.dbcon.cursor()
        except Exception, e:
            logger.error("Couldn't open database, %s", e)
            sys.exit(1)


    def db_connect(self):
        self.db_real_connect()

        # on first run we might have to create the banmemory table
        try:
            self.dbcur.execute("CREATE TABLE IF NOT EXISTS landlady_banmem (timestamp INT,  targetnick TEXT, targethost TEXT, command TEXT, sourcenick TEXT, duration INT)")
        except Exception, e:
            logger.error("couln't create table, %s", e)

        # on first run we might have to create the settings table
        try:
            self.dbcur.execute("CREATE TABLE IF NOT EXISTS landlady_config (section TEXT, key TEXT, value TEXT)")
        except Exception, e:
            logger.error("ERROR: couln't create table, %s", e)

        # load the data from the db, and if there's default values missing add them in
        for section in DefaultSettings.default.keys():
            logger.debug("INFO: Loading %s", section)
            try:
                self.dbcur.execute('SELECT key, value FROM landlady_config WHERE section = ?', [section])
            except Exception, e:
                logger.error("ERROR: Fetching config, %s", e)
                sys.exit(1)

            loaded_vals = []
            rows = self.dbcur.fetchall()
            if len(rows) == 0:
                logger.warn("WARNING: No settings found for %s, using default", section)
            for row in rows:
                loaded_vals.append(row[0])
                DefaultSettings.default[section][row[0]] = row[1]

            for key in DefaultSettings.default[section].keys():
                if key not in loaded_vals:
                    logger.debug("Updating %s with %s=%s", section,key,DefaultSettings.default[section][key])
                    try:
                        self.dbcur.execute('INSERT INTO landlady_config (section, key, value) VALUES (?,?,?)', [section, key, DefaultSettings.default[section][key]])
                    except Exception, e:
                        logger.error("Couln't update database, %s", e)

            self.dbcon.commit()


        for key in DefaultSettings.default['kb_commands'].keys():
            mess = DefaultSettings.default['kb_commands'][key].split(' ',1)[1]
            time = DefaultSettings.default['kb_commands'][key].split(' ',1)[0]
            self.Settings.kb_commands[key] = (time,mess)
            logger.debug("kb_commands loading %s '%s' -> (%s,%s).", key,DefaultSettings.default['kb_commands'][key],DefaultSettings.default['kb_commands'][key][1],DefaultSettings.default['kb_commands'][key][0])

        for key in DefaultSettings.default['kb_settings'].keys():
            self.Settings.kb_settings[key] = copy.copy(DefaultSettings.default['kb_settings'][key])
            logger.debug("kb_settings, %s = %s", key,DefaultSettings.default['kb_settings'][key])

        self.Settings.kb_settings['ban_timemul'] = DefaultSettings.default['kb_settings']['ban_timemul'].split(',')
        self.Settings.kb_settings['child_chans'] = DefaultSettings.default['kb_settings']['child_chans'].split(' ')

        # self.Settings.swarm = copy.deepcopy(DefaultSettings.default['swarm'])
        # self.Settings.swarm_enabled = copy.deepcopy(DefaultSettings.swarm_enabled)
        # self.Swarm.channel = DefaultSettings.default['swarm']['channel']


    '''


        Take the arguments for a kb kb_command
        and parse them.

        If it's not a valid command it returns
        a lot of None


    '''
    def parse_kb_arguments(self, user, userlist, cmd, targetnick, bantime_int, source):
        reason = bantime_int = trigger_nick = None
        trigger_nick = source.split('!')[0]

        if not cmd in self.Settings.kb_commands:
            logger.error("Command (%s) not found", cmd)
            return None

        if not bantime_int:
            bantime_int = int(self.Settings.kb_commands[cmd][0])



        hostlist = {}
        for user in userlist:
            if user.nick not in hostlist:
                hostlist[user.nick] = user.nickuserhost

        banmask = self.create_banmask(user, hostlist, targetnick)
        if not banmask:
            logger.error("Couldn't find user %s", targetnick)
            return None

        factor = int(self.get_punish_factor(banmask))
        bantime = bantime_int * factor

        reason = "%s (%d) /%s" % (self.Settings.kb_commands[cmd][1], bantime, trigger_nick)

        self.save_kickban(
                targetnick,
                banmask,
                reason,
                bantime,
                trigger_nick,
                cmd
            )


        logger.debug("(kb) cmd: %s, reason: %s, targetnick: %s, factor: %s, bantime: %s", cmd, reason, targetnick, factor, bantime_int)

        return {
                'reason': reason,
                'bantime': bantime_int,
                'banmask': banmask
            }


    def is_numeric(self, host):
        hostbits = host.split('.')
        numeric = True
        if len(hostbits) == 4:
            for bit in hostbits:
                numeric &= bit.isdigit()
                if not numeric:
                    break
        else:
            numeric = False

        return numeric



    '''
        Ban someone

        The functions handels the creation of the banmask so
        it's unique to the user and the accuall commands to
        the irc-server
    '''
    def match_banmask(self, userlist, targetnick, banmask):
        matches = []

        # escape banmask to re
        banmask = banmask.replace('.','\.')
        banmask = banmask.replace('-','\-')
        banmask = banmask.replace('[','\[')
        banmask = banmask.replace(']','\]')
        banmask = banmask.replace('{','\{')
        banmask = banmask.replace('}','\}')
        banmask = banmask.replace('*','.*')

        for usernick in userlist.keys():
            userhost = usernick + "!" + userlist[usernick]

            if usernick == targetnick:
                continue

            try:
                m = re.match(banmask, userhost)
                if m:
                    matches.append(usernick)
            except Exception, e:
                logger.error("ERROR when regexing: %s %s", e.__class__.__name__, e)
                logger.error("\t%s, %s", banmask, userhost)

        return matches

    def create_banmask(self, targetnick, user, host, hostlist):
        if self.is_numeric_ip(host):
            hits = 0
            banmask = '*!*@%s' % '.'.join(host.split('.')[:3])+'.*'
            matches = self.match_banmask(hostlist, targetnick, banmask)
            hits += len(matches)
            if hits == 0:
                return banmask

            hits = 0
            banmask = '*!*@%s' % host
            hits += len(self.match_banmask(hostlist, targetnick, banmask))
            if hits == 0:
                return banmask

            hits = 0
            banmask = '*!*%s*@%s' % (user, host)
            hits += len(self.match_banmask(hostlist, targetnick, banmask))
            if hits == 0:
                return banmask

            banmask = '*!%s@%s' % (user, host)
            return banmask

        else:
            # try a wide mask first
            hits = 0
            if len(host.split('.')) == 2:
                banmask = '*!*@%s' % host
            else:
                banmask = '*!*@*.%s' % '.'.join(host.split('.')[1:])
            hits += len(self.match_banmask(hostlist, targetnick, banmask))
            if hits == 0:
                return banmask

            # try a wide mask second
            hits = 0
            if len(host.split('.')) == 2:
                banmask = '*!*@%s' % (host)
            else:
                banmask = '*!*%s@*.%s' % (user, '.'.join(host.split('.')[1:]))
            hits += len(self.match_banmask(hostlist, targetnick, banmask))
            if hits == 0:
                return banmask

            # narrow it down a bit
            hits = 0
            if len(host.split('.')) == 2:
                banmask = '*!*@%s' % host
            else:
                banmask = '*!*%s@*.%s' % (user, '.'.join(host.split('.')[1:]))
            hits += len(self.match_banmask(hostlist, targetnick, banmask))
            if hits == 0:
                return banmask

            # narrow it down a bit more
            hits = 0
            banmask = '*!*@%s' % (host)
            hits += len(self.match_banmask(hostlist, targetnick, banmask))
            if hits == 0:
                return banmask

            # if everything else failed use this
            banmask = '*!*%s*@%s' % (user,host)

        return banmask

    def get_punish_factor(self, banmask):
        logger.debug("get_punish_factor(self, %s)", banmask)
        self.dbcur.execute("SELECT count(*) FROM landlady_banmem WHERE targethost = ?", (banmask,))
        try:
            count = int(self.dbcur.fetchone()[0])
        except Exception, e:
            logger.error("ERROR: Couldn't get ban count: %s", e)
            return 1

        if count >= len(self.Settings.kb_settings['ban_timemul']):
            count = len(self.Settings.kb_settings['ban_timemul'])-1

        return self.Settings.kb_settings['ban_timemul'][count]



    def save_kickban(self, targetnick, banmask, reason, duration, sourcenick, command):
        # save kb to memory
        self.dbcur.execute("""INSERT INTO landlady_banmem (
                timestamp,
                targetnick,
                targethost,
                command,
                sourcenick,
                duration)
            VALUES (
                datetime('now'),?,?,?,?,?)""",
            (targetnick, banmask, command, sourcenick, duration)
        )
        self.dbcon.commit()

    def purge_kickbans(self):
        result = self.dbcur.execute("""SELECT targethost FROM
                landlady_banmem
            WHERE
                datetime(timestamp, '+'||duration||' seconds') < datetime('now');
            """)

        unbanlist = []
        for row in result:
            unbanlist.append(row[0])

        for channel in self.Settings.kb_settings['child_chans']:
            c = self.client.server.channel_by_name(channel)
            for banmask in unbanlist:
                if c.is_banned(banmask):
                    c.remove_ban(banmask)
                    self.unban(channel, banmask)
                self.dbcur.execute("DELETE FROM landlady_banmem WHERE targethost LIKE ?", (banmask,))

            self.dbcon.commit()



    def announce_kickban(self, targetnick, banmask, reason, bantime, trigger_nick, cmd):
        result = []
        result.append(base64.b64encode(str(targetnick)))
        result.append(base64.b64encode(str(banmask)))
        result.append(base64.b64encode(str(bantime)))
        result.append(base64.b64encode(str(trigger_nick)))
        result.append(base64.b64encode(str(cmd)))
        self.client.tell(self.Settings.swarm['channel'], '.banned '+" ".join(result))

    def unban(self, channel, banmask):
        self.client.send('MODE %s -b %s' % (channel, banmask))

    def add_to_banlist(self, channel, sourcenick, banmask):
        bl = self.bot.client.banlists
        if channel in bl:
            self.bot.clients.banlists[channel][banmask] = (sourcenick,time.time())

    def remove_from_banlist(self, channel, banmask):
        bl = self.bot.client.banlists
        if channel in bl:
            if banmask in bl[channel]:
                del(self.bot.client.banlists[channel][banmask])

    def extract_nick(self, host):
        m = re.search('^:?(.+)!', host)
        if m:
            return str(m.group(1))
        else:
            return host


