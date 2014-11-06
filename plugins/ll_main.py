# coding: utf-8
"""
ll_main

Main methods for Landlady
"""

from commands import Command
from ll_utils import LLUtils
#from utility import extract_nick
from random import randrange
import hashlib
import time
import datetime
import base64

class Landlady(Command):
    """main class"""
    def __init__(self):
        self.llu = LLUtils()
        self.settings = self.llu.Settings
        self.swarm = self.llu.Swarm()
        self.bot = None
        self.net = None
        self.client = None

        self.banlist_age = {}
        self.banlist_timestamp = {}

        if self.settings.swarm_enabled:
            from ll_swarm import Swarm
            self.swarm = Swarm()
            self.swarm.channel = self.settings.swarm['channel']

    def on_connected(self, event):
        """
        set up stuff when we're connected, we need a ref to
        the bot, swarm and stuff.
        """
        self.bot = event['bot']
        self.client = event['client']
        self.net = self.client.net
        self.bot.swarm = self.swarm

        self.swarm.bot = self.bot
        self.swarm.client = self.client

        self.llu.bot = self.bot
        self.llu.client = self.client

        # purge old bans
        delay = int(randrange(6000, 12000)/10)
        self.bot.add_timer(
                datetime.timedelta(0, delay),
                False,
                self.check_old_bans
            )


    def on_privmsg(self, event):
        """
        Expose some functions
        """
        source_nick = event['source']
        target_chan = event['target']
        message = event['message']

        if len(message) < 4:
            return
        if message.split(' ')[0][:3] == '.kb':
            argument = " ".join(message.split(' ')[1:])
            self.trigger_kb(source_nick, target_chan, argument)

    def debug_info(self, network = None):
        """trigger on debug_info signal and print debug info"""
        print "(swarm) enabled: %s" % self.swarm.enabled
        if self.swarm.enabled:
            print "(swarm) voteid: %s (%s)" % (
                    self.swarm.current_voteid, self.swarm.range)
            print "(swarm) last vote: %s s ago" % (
                    time.time() - self.swarm.last_vote_time)
            print "(swarm) channel: %s" % (
                    self.swarm.channel)
            print "(swarm) votes: %s" % (
                    self.swarm.get_current_votes())



    def trigger_kb(self, trigger_nick, trigger_channel, argument):
        """Take care of any incoming kick-ban requests"""
        if trigger_channel != self.settings.kb_settings['command_chan']:
            print "ERROR: kb-request from outside %s" % (
                    self.settings.kb_settings['command_chan'])
            return False

        (cmd, reason, targetnick, bantime) = self.llu.parse_kb_arguments(
                argument,
                trigger_nick
            )
        if not cmd:
            print "ERROR: Unknown command, %s,%s,%s." % (
                    trigger_nick,
                    trigger_channel,
                    argument
                )
            print "     : Unknown command, %s,%s,%s,%s." % (
                    cmd,
                    reason,
                    targetnick,
                    bantime
                )
            return None

        if self.settings.swarm_enabled and not self.swarm.nick_matches(targetnick):
            return False

        # Get a banmask that's unique
        banmask = self.llu.create_banmask(self.net, targetnick)
        if not banmask:
            return "Couldn't find user %s" % (targetnick)

        # Add punishfactor
        factor = self.llu.get_punish_factor(banmask, self.net.name)
        bantime = int(bantime) * int(factor)

        # Kickban the user in all channels
        for channel in self.settings.kb_settings['child_chans']:
            self.client.send('MODE %s +b %s' % (channel, banmask))
            self.client.send('KICK %s %s :%s' % (channel, targetnick, reason))
            self.bot.add_timer(
                    datetime.timedelta(0, bantime),
                    False,
                    self.client.send,
                    'MODE %s -b %s' % (channel, banmask)
                )

        self.llu.save_kickban(
                self.net.name,
                targetnick,
                banmask,
                reason,
                bantime,
                trigger_nick,
                cmd
            )
        if self.settings.swarm_enabled:
            self.llu.announce_kickban(
                    targetnick,
                    banmask,
                    reason,
                    bantime,
                    trigger_nick,
                    cmd
                )

        return None


    def trig_vote(self, bot, source, target, trigger, argument, network):
        """if someone else votes we should answer asap"""
        print "trig_vote(self,bot,%s,%s,%s,%s,network)" % (
                source,
                target,
                trigger,
                argument
            )
        if not self.settings.swarm_enabled:
            return

        if target != self.swarm.channel:
            print "ERROR: Swarm vote in none swarm channel (%s)" % target
            return False

        (incoming_vote_id, incoming_vote) = self.swarm.parse_vote(argument, source)
        if (incoming_vote_id is None) or (incoming_vote is None):
            print "ERROR: error in vote arguments"
            return False

        if incoming_vote_id not in self.swarm.votes:
            self.swarm.votes[incoming_vote_id] = {}

        self.swarm.votes[incoming_vote_id][source] = incoming_vote

        if incoming_vote_id != self.swarm.current_voteid:
            # new vote, we need to vote
            self.swarm.unvoted_id = incoming_vote_id
            self.send_vote()
        else:
            # we already voted on this
            self.swarm.range = self.swarm.get_swarm_range() # update ranges
            self.swarm.unvoted_id = None # we have no unvoted votes

    def on_join(self, event):
        """If we join the swarm.channel we need to vote"""
        nick = event['user'].nick

        # if swarm is enabled and we joined the swarm channel
        # we should start the vote-madness
        if self.settings.swarm_enabled and (nick == event['client'].net.mynick) and (event['channel'].name == self.swarm.channel):
            self.swarm.enable()
            wait_time = randrange(
                    self.swarm.min_vote_time,
                    self.swarm.min_vote_time*2
                )
            print "(swarm) joined swarm channel, voting in %s seconds" % (wait_time)
            self.bot.add_timer(
                    datetime.timedelta(0, wait_time),
                    True,
                    self.reoccuring_vote
                )

    def reoccuring_vote(self):
        """send out vote every once in a while, if we havn't voted just"""
        if (time.time() - self.swarm.last_vote_time) < self.swarm.min_vote_time:
            print "(swarm) reoccuring_vote(): throttling vote. %s < %s" % (
                    time.time() - self.swarm.last_vote_time,
                    self.swarm.min_vote_time)
            return
        self.swarm.unvoted_id = randrange(0, 65535)
        self.send_vote()


    def send_vote(self):
        """create and send vote to swarm-channel"""
        if self.swarm.unvoted_id == None:
            print "(swarm) send_vote(): unvoted_id is None. Escaping."
            return
        if not self.swarm.enabled:
            print "(swarm) send_vote(): swarm not enabled. Escaping."
            return

        self.swarm.create_vote(self.net.mynick)
        self.client.tell(self.swarm.channel,"%svote %d %d %s" % (
                self.bot.settings.trigger,
                self.swarm.current_voteid,
                self.swarm.random,
                self.swarm.vote_hash))

        self.swarm.last_vote_time = time.time()

        self.swarm.enable()


    def on_part(self, event):
        """
        if someone parts the swarm channel we need to
        update the swarm list and recalculate ranges
        """

        print "(swarm) on_part() chan: %s nick: %s" % (event['channel'].name, event['user'].nick)

        nick = event['user'].nick
        if event['channel'].name == self.swarm.channel:
            if nick != event['client'].net.mynick:
                self.swarm.disable()
            else:
                self.swarm.remove_bot(nick)

    def on_quit(self, event):
        """
        if a bot quits we seed to update the swarm list
        and recalculate ranges
        """
        print "(swarm) %s quitted" % (event['source_nick'])
        self.swarm.remove_bot(event['source_nick'])


    def trig_banned(self, bot, source, target, trigger, argument, network):
        """
        a bot banned someone, we should add this to our internal list
        so if the user rejoins we know that he/she is banned.
        """
        if not self.settings.swarm_enabled or not self.swarm.enabled:
            return

        if target != self.swarm.channel:
            return False

        arguments = argument.split(' ')
        arguments_decoded = []
        try:
            for arg in arguments:
                arguments_decoded.append(base64.b64decode(arg))
        except Exception, estr:
            print " -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  - "
            print "trig_banned(self, bot, %s, %s, %s, %s, %s)" % (
                    source,
                    target,
                    trigger,
                    argument,
                    network)
            print "EXCEPTION %s %s" % (estr.__class__.__name__, estr)
            print " -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  - "
            return

        targetnick, banmask, bantime, trigger_nick, cmd = arguments_decoded[0:5]
        if cmd in self.settings.kb_commands.keys():
            reason = self.settings.kb_commands[cmd][1]
            self.llu.save_kickban(
                self.net.name,
                targetnick,
                banmask,
                reason,
                bantime,
                trigger_nick,
                cmd)
        else:
            print " **** COMMAND (%s) not in %s" % (
                cmd,
                self.settings.kb_commands.keys())


    def check_old_bans(self):
        """
        Purge old kickbans from list
        """
        self.llu.purge_kickbans()
        delay = datetime.timedelta(0, int(float(randrange(6000, 12000)/10)))
        self.bot.add_timer(delay, False, self.check_old_bans)

