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
        self.bot = None
        self.net = None
        self.client = None

        self.vote_reply_timer = 0

        self.banlist_age = {}
        self.banlist_timestamp = {}

    def on_connected(self, event):
        """
        set up stuff when we're connected, we need a ref to
        the bot, swarm and stuff.
        """
        self.bot = event['bot']
        self.client = event['client']
        self.net = self.client.net

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



    # def trigger_kb(self, trigger_nick, trigger_channel, argument, swarm_match):
    def trigger_kb(self, event):
        trigger_nick = event['source'].nick
        trigger_channel = event['target'].name
        argument = event['arguments']
        swarm_match = event['swarm_match']

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

        if swarm_match is not None and swarm_match == True:
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
        # if self.settings.swarm_enabled:
        #     self.llu.announce_kickban(
        #             targetnick,
        #             banmask,
        #             reason,
        #             bantime,
        #             trigger_nick,
        #             cmd
        #         )

        return None



    # def trig_banned(self, event):
    #     """
    #     a bot banned someone, we should add this to our internal list
    #     so if the user rejoins we know that he/she is banned.
    #     """
    #     bot = event['bot']
    #     source = event['source'].nick
    #     if event['target']:
    #         target = event['target'].name
    #     else:
    #         target = source
    #     trigger = event['trigger']
    #     arguments = event['arguments']

    #     if not self.settings.swarm_enabled or not self.swarm.enabled:
    #         return

    #     if target != self.swarm.channel:
    #         return False

    #     arguments = arguments.split(' ')
    #     arguments_decoded = []
    #     try:
    #         for arg in arguments:
    #             arguments_decoded.append(base64.b64decode(arg))
    #     except Exception, estr:
    #         print " -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  - "
    #         print "trig_banned(self, bot, %s, %s, %s, %s, %s)" % (
    #                 source,
    #                 target,
    #                 trigger,
    #                 arguments,
    #                 network)
    #         print "EXCEPTION %s %s" % (estr.__class__.__name__, estr)
    #         print " -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  -  - "
    #         return

    #     targetnick, banmask, bantime, trigger_nick, cmd = arguments_decoded[0:5]
    #     if cmd in self.settings.kb_commands.keys():
    #         reason = self.settings.kb_commands[cmd][1]
    #         self.llu.save_kickban(
    #             self.net.name,
    #             targetnick,
    #             banmask,
    #             reason,
    #             bantime,
    #             trigger_nick,
    #             cmd)
    #     else:
    #         print " **** COMMAND (%s) not in %s" % (
    #             cmd,
    #             self.settings.kb_commands.keys())


    def check_old_bans(self):
        """
        Purge old kickbans from list
        """
        self.llu.purge_kickbans()
        delay = datetime.timedelta(0, int(float(randrange(6000, 12000)/10)))
        self.bot.add_timer(delay, False, self.check_old_bans)

