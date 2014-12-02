import re
import sys
import traceback
import datetime
import time

from copy import copy
from heapq import heappush, heappop
from autoreloader.autoreloader import AutoReloader

import plugin_handler
import error_handler
from ircclient import ircclient

# Call plugins_on_load only on first import
try:
    IRCBot
except NameError:
    plugin_handler.plugins_on_load()

class PriorityQueue:
    def __init__(self):
        self.internal_array = []

    def clear(self):
        self.internal_array = []

    def push(self, item):
        heappush(self.internal_array, item)

    def pop(self):
        return heappop(self.internal_array)

    def empty(self):
        return len(self.internal_array) == 0

    def top(self):
        return self.internal_array[0]

    def delete_by_id(self, id):
        for i in range(len(self.internal_array)):
            if self.internal_array[i].id == id:
                self.internal_array[i] = self.internal_array[-1]
                self.internal_array.pop()
                heapq._siftup(self.internal_array, i)
                return True
        return False




class TimedEvent:
    def __init__(self, trigger_delta, recurring, target, id, args):
        self.trigger_delta = trigger_delta
        self.trigger_time = datetime.datetime.now() + trigger_delta
        self.recurring = recurring
        self.target = target
        self.args = args
        self.id = id

    def trigger(self):
        self.target(*self.args)

    def reset(self):
        self.trigger_time += self.trigger_delta

    def __cmp__(self, other):
        return cmp(self.trigger_time, other.trigger_time)

class IRCBot(AutoReloader):
    def __init__(self, settings):
        self.settings = settings
        self.callbacks = self.get_callbacks()
        self.client = None
        self.plugins = []
        self.timer_heap = PriorityQueue()
        self.next_timer_beat = None
        self.need_reload = {}
        self.timer_id = 0

        server_settings = self.settings.server
        print "Connecting to server at %s:%s..." % (
              server_settings['server_address'],
              server_settings['server_port'])
        self.client = ircclient.IRCClient(
                                    self,
                                    server_settings['server_address'],
                                    server_settings['server_port'],
                                    server_settings['nick'],
                                    server_settings['username'],
                                    server_settings['realname'],
                                    server_settings.setdefault('server_password'))
        self.client.callbacks = copy(self.callbacks)

    def get_callbacks(self):
        return { "on_connected": self.on_connected, "on_join": self.on_join,
             "on_nick": self.on_nick, "on_notice": self.on_notice,
             "on_part": self.on_part, "on_privmsg": self.on_privmsg,
             "on_mode": self.on_mode, "on_quit": self.on_quit, "debug_info": self.debug_info }

    def is_connected(self):
        return self.client.is_connected()

    def execute_plugins(self, trigger, event = {}):
        for plugin in plugin_handler.all_plugins():
            try:
                if plugin.__class__.__dict__.has_key(trigger):
                    event['bot'] = self
                    plugin.__class__.__dict__[trigger](plugin, event) # new object based callback
            except:
                messages = ['','EXCEPTION:']
                messages.append("%s %s" % (plugin, sys.exc_info()))
                for row in [[tb[0]+':'+str(tb[1])]+[str(z) for z in tb[2:]] for tb in traceback.extract_tb(sys.exc_info()[2])]:
                    messages.append(row)
                messages.append('')

                for message in messages:
                    error_handler.output_message(message)
                # error_handler.output_message("*** EXCEPTION ***\n%s %s Plugin '%s' threw exception\nexinfo: '%s'\n" % (
                #       datetime.datetime.now().strftime("[%H:%M:%S]"),
                #       network,
                #       plugin,
                #       sys.exc_info()

                #   ))
                # error_handler.output_message([tb[0]+':'+str(tb[1])+"\n\t"+"\n\t".join([str(z) for z in tb[2:]]) for tb in traceback.extract_tb(sys.exc_info()[2])])



    def on_connected(self, event):
        self.execute_plugins("on_connected", event)

    def on_join(self, event):
        self.execute_plugins("on_join", event)

    def on_kick(self, event):
        self.execute_plugins("on_kick", event)

    def on_nick(self, event):
        self.execute_plugins("on_nick", event)

    def on_notice(self, event):
        self.execute_plugins("on_notice", event)

    def on_part(self, event):
        self.execute_plugins("on_part", event)

    def on_privmsg(self, event):
        self.execute_plugins("on_privmsg", event)

    def on_quit(self, event):
        self.execute_plugins("on_quit", event)

    def on_mode(self, event):
        self.execute_plugins("on_mode", event)

    def debug_info(self, *argv):
        print "(net) name: %s" % self.client.server.name
        print "(net) nick: %s" % self.client.server.mynick
        print "(net) channels: %d" % len(self.client.server.all_channels)
        print "(net) known users: %d" % len(self.client.server.all_users)

        for channel in self.client.server.all_channels:
            print "(%s) users: %d" % (channel.name, len(channel.user_list))
            print "(%s) bans: %d" % (channel.name, len(channel.ban_list))
            # for ban in channel.ban_list:
            #     print "(%s)\t * %s (%s @%s)" % (channel.name, ban.banmask, ban.banner_nick, ban.timestamp)

        """trigger on debug_info signal and print debug info"""
        print "(swarm) enabled: %s" % self.client.swarm.enabled
        if self.client.swarm.enabled:
            #print "(swarm) old votes: %s" % (self.client.swarm.votes)
            print "(swarm) voteid: %s (%s)" % (
                    self.client.swarm.vote.current_voteid, self.client.swarm.vote.range)
            print "(swarm) last vote: %s s ago" % (
                    int(round(time.time() - self.client.swarm.vote.last_vote_time)))
            print "(swarm) next vote in: %s s" % (
                    int(round(self.client.swarm.vote.next_vote_time - time.time())))
            print "(swarm) channel: %s" % (
                    self.client.swarm.channel)
            print "(swarm) votes: %s" % (
                    self.client.swarm.vote.get_current_votes())
            print "(swarm) verifications: %s" % (
                    self.client.swarm.verify.sorted_vote_verifications)
            print "(swarm) verification bots: %s" % (
                    self.client.swarm.verify.vote_verifications.keys())


        self.execute_plugins("debug_info");

    # FIXME: should we do this or handle it in the
    # autojoin plugin?
    # def on_reload(self):
    #     # Check for new channels, if so join them
    #     for channel in self.settings.server['channels']:
    #         try:
    #             self.join(channel[0], channel[1])
    #         except IndexError:
    #             self.join(channel[0])
    #     # Connect to new networks
    #     net_settings = self.settings.server
    #     print "Connecting to new network %s at %s:%s..." % (network,
    #           net_settings['server_address'], net_settings['server_port'])
    #     self.client[network] = ircclient.IRCClient(net_settings['server_address'],
    #                             net_settings['server_port'],
    #                             net_settings['nick'],
    #                             net_settings['username'],
    #                             net_settings['realname'],
    #                             network)
    #     self.client[network].callbacks = copy(self.callbacks)
    #     self.networks.append(network)

    def reload(self):
        self.need_reload['main'] = True
        self.need_reload['ircbot'] = True

    def reload_plugins(self):
        plugin_handler.plugins_on_unload()
        plugin_handler.reload_plugin_modules()
        plugin_handler.plugins_on_load()

    def load_plugin(self, plugin):
        plugin_handler.load_plugin(plugin)

    def join(self, channel, password=""):
        return self.client.join(channel, password)

    def send(self, line=None):
        return self.client.send(line)

    def tell(self, target, message=None):
        return self.client.tell(target, message)

    def tick(self):
        # Do reload if necassary
        if self.need_reload.get('ircbot'):
            reload(ircclient)
            reload(plugin_handler)
            self.callbacks = self.get_callbacks()
            for client in self.client.values():
                client.callbacks = copy(self.callbacks)

            self.need_reload['ircbot'] = False

        # Call timers
        now = datetime.datetime.now()
        while not self.timer_heap.empty() and self.timer_heap.top().trigger_time <= now:
            timer = self.timer_heap.pop()
            timer.trigger()
            if timer.recurring:
                timer.reset()
                self.timer_heap.push(timer)

        self.client.tick()

        # Call timer_beat every 1 second
        if not self.next_timer_beat or self.next_timer_beat < now:
            self.next_timer_beat = now + datetime.timedelta(0, 1)
            self.execute_plugins("timer_beat", {"datetime": now })

    def add_timer(self, delta, recurring, target, *args):
        self.timer_id += 1
        timer = TimedEvent(delta, recurring, target, self.timer_id, args)

        self.timer_heap.push(timer)

        return self.timer_id

