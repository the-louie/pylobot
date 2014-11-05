"""
ll_swarm

peer-to-peer distribution of actions between all bots in the swarm

"""
from random import randrange
import time
import hashlib
import datetime

MIN_VOTE_TIME = 300

class Swarm():
    """
    handle swarm messages and stuff

    The following functions handles voting and also decides
    if a action is to be taken depending on a keyword
    """
    def __init__(self):
        self.min_vote_time = MIN_VOTE_TIME

        self.range = (65535, 0)
        self.votes = {}
        self.enabled = False

        self.random = 0
        self.current_voteid = None
        self.unvoted_id = None
        self.vote_hash = ""

        self.channel = "#dreamhack.swarm"
        self.secret = 'O=DVHk!D4"48h/g)f4R/sjF#p5FB4976hT#fBGsd8'
        self.opchans = ['#dreamhack','#dreamhack.info','#dreamhack.trade']

        self.next_vote_time = 0
        self.last_vote_time = 0

        self.reoccuring_voting_enabled = False

        self.bot = None
        self.client = None

        self.swarm_op_timer = None

    def nick_matches(self, targetnick):
        md5hash = hashlib.md5()
        md5hash.update(targetnick)
        hashid = int(md5hash.hexdigest()[0:2], 16)
        if not self.range[0] <= hashid < self.range[1]:
            return False
        else:
            return True

    def enable(self):
        """
        enable swarm functions
        """
        print "(swarm) enable"
        self.enabled = True

        # make sure the swarm is opped periodically
        if self.swarm_op_timer == None:
            delay = int(randrange(600, 1200)/10)
            self.swarm_op_timer = self.bot.add_timer(
                    datetime.timedelta(0, delay),
                    True,
                    self.op_bots
                )

    def disable(self):
        """
        disable swarm functions
        """
        print "(swarm) disable"
        self.enabled = False

    def get_current_votes(self):
        if self.current_voteid in self.votes:
            return self.votes[self.current_voteid]
        else:
            return {}

    def get_swarm_members(self):
        if self.current_voteid in self.votes:
            return self.votes[self.current_voteid].keys()
        else:
            return []

    def update_swarm_range(self, vote):
        """
        update swarm range
        """
        lowest = min(self.range[0], vote)
        highest = max(self.range[1], vote)
        swarm_range = (lowest, highest)
        return swarm_range

    def create_vote_hash(self, voteid, random, nick):
        md5hash = hashlib.md5()
        md5hash.update(self.secret + str(voteid) + str(random) + str(nick) + self.secret)
        return md5hash.hexdigest()

    def create_vote(self, mynick):
        """
        Setup a new vote
        """
        self.current_voteid = self.unvoted_id
        self.random = randrange(0, 65535)
        if self.current_voteid not in self.votes:
            self.votes[self.current_voteid] = {}
        self.votes[self.current_voteid][mynick] = self.random
        self.last_vote_time = time.time()
        self.range = self.get_swarm_range()
        self.unvoted_id = None
        self.vote_hash = self.create_vote_hash(self.current_voteid, self.random, mynick)

    def parse_vote(self, argument, sourcenick):
        """
        parse an incomming vote and make sure it contains
        everything we need.
        """
        try:
            (vote_id_str, vote_value_str, vote_hash_str) = argument.split(' ')
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

        calc_hash = self.create_vote_hash(vote_id, vote_value, sourcenick)
        if calc_hash != vote_hash_str:
            print "(swarm) vote hash missmatch '%s' '%s'" % (calc_hash, vote_hash)
            return (None, None)

        return (vote_id, vote_value)


    def get_swarm_range(self):
        """
        calculate ranges
        """
        sorted_swarm_votes = sorted(self.votes[self.current_voteid].values())
        #print self.votes
        my_index = sorted_swarm_votes.index(self.random)

        buckets = [0]
        bucket_size = 256.0/(len(sorted_swarm_votes))
        curr_bucket = bucket_size
        for tmp in range(0, 255):
            if tmp > curr_bucket:
                buckets.append(tmp)
                curr_bucket = curr_bucket + bucket_size

        buckets.append(255)
        swarm_range = (buckets[my_index], buckets[my_index+1])

        if swarm_range[1] == 255:
            swarm_range = (swarm_range[0], 256)

        return swarm_range

    def remove_bot(self, nick):
        """
        remove a bot and recalculate ranges
        """
        if self.current_voteid not in self.votes:
            # no votes yet
            return

        if nick not in self.votes[self.current_voteid].keys():
            # not a swarm bot
            return

        del self.votes[self.current_voteid][nick] # remove bot from swarm
        self.range = self.get_swarm_range() # update ranges

    def op_bots(self):
        """
        op all members of the swarm where appropriate
        """
        print "(swarm) op_bots()"
        if not self.enabled:
            print "(swarm) not enabled"
            return

        for channel_name in self.opchans:
            channel = self.client.net.channel_by_name(channel_name)
            for botnick in self.get_swarm_members():
                if channel.has_nick(botnick):
                    self.client.send("MODE %s +o %s" % (channel_name, botnick))


    # def sync_channels(self):
    #     print "(fenrus) sync_channels"
    #     delay = float(randrange(3000, 12000)/10)
    #     self.bot.add_timer(datetime.timedelta(0, delay), False, self.sync_channels)

    #     # don't sync too often
    #     if time.time() - self.last_sync_time < 300:
    #         return
    #     self.last_sync_time = time.time()

    #     try:
    #         master_channel = self.net.channel_by_name(self.master_channel)
    #         master_users = master_channel.user_list
    #     except Exception, e:
    #         print "(fenrus) ERROR: %s" % e
    #         return

    #     for master_user in master_users:
    #         if self.Settings.swarm_enabled and not self.swarm.nick_matches(master_user.nick):
    #             continue

    #         for slave_channel_name in self.slave_channels:
    #             slave_channel = self.net.channel_by_name(slave_channel_name)
    #             if not slave_channel.has_nick(master_user.nick):
    #                 # print "(fenrus) %s not in %s" % (master_user.nick, slave_channel_name)
    #                 continue
    #             # print "(fenrus) master_user.channel_flags(%s): %s" % (slave_channel_name, master_user.channel_flags(slave_channel_name))
    #             flags = master_user.channel_flags(slave_channel_name)
    #             if not flags or ("+" not in flags and "@" not in flags):
    #                 #print "(fenrus) *** voice *** %s in %s" % (master_user.nick, slave_channel_name)
    #                 self.client.send('MODE %s +v %s' % (slave_channel_name, master_user.nick))
    #             # else:
    #             #   print "(fenrus) no action, %s has %s in %s" % (master_user.nick, flags, slave_channel_name)





