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
    def __init__(self, bot, client):
        self.bot = bot
        self.client = client

        self.min_vote_time = MIN_VOTE_TIME

        self.range = (65535, 0)
        self.votes = {}
        self.enabled = False

        self.random = 0
        self.current_voteid = None
        self.unvoted_id = None
        self.vote_hash = ""

        self.channel = self.bot.settings.server['swarm']['channel'] #"#dreamhack.swarm"
        self.secret = self.bot.settings.server['swarm']['secret'] # 'O=DVHk!D4"48h/g)f4R/sjF#p5FB4976hT#fBGsd8'
        self.opchans = self.bot.settings.server['swarm']['opchans'] # ['#dreamhack','#dreamhack.info','#dreamhack.trade']

        self.next_vote_time = 0
        self.last_vote_time = 0

        self.vote_reply_timer = 0

        self.reoccuring_voting_enabled = False

        self.swarm_op_timer = None

    def nick_matches(self, targetnick):
        #print "(swarm) nick_matches(self, %s)" % (targetnick)
        if not self.enabled:
            print "(swarm) not enabled, exiting"
            return None
        if targetnick is None:
            print "(swarm) target nick is None, exiting"
            return True

        md5hash = hashlib.md5()
        md5hash.update(targetnick)
        hashid = int(md5hash.hexdigest()[0:2], 16)
        #print "(swarm) hashid is %d, my range is %d-%d" % (hashid, self.range[0], self.range[1])
        if not self.range[0] <= hashid < self.range[1]:
            #print "(swarm) *** FALSE ***"
            return False
        else:
            #print "(swarm) *** TRUE ***"
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
        timebit = int(round(int(datetime.datetime.now().strftime("%s"))/300))
        #timebit = 0 # FIXME: this should not be 0 but the above line
        instring = self.secret + str(voteid) + str(random) + str(nick) + str(timebit)
        outstring = hashlib.sha512(instring + hashlib.sha512(instring).digest()).hexdigest()
        return outstring

    def create_vote(self, mynick):
        """
        Setup a new vote
        """
        self.current_voteid = self.unvoted_id
        self.random = randrange(0, 65535)
        if self.current_voteid not in self.votes:
            self.votes[self.current_voteid] = {}
        self.votes[self.current_voteid][mynick] = self.random
        self.range = self.get_swarm_range()
        self.unvoted_id = None
        self.vote_hash = self.create_vote_hash(self.current_voteid, self.random, mynick)

    def parse_vote(self, arguments, sourcenick):
        """
        parse an incomming vote and make sure it contains
        everything we need.
        """
        try:
            (vote_id_str, vote_value_str, vote_hash_str) = arguments
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
            print "(swarm) vote hash missmatch:\n\tcalc: %s\n\tinco: %s\n" % (calc_hash, vote_hash_str)
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
            channel = self.client.server.channel_by_name(channel_name)
            #print "(swarm) * checking %s" % channel_name
            if not channel.has_op(self.client.nick): # only check channels we have op in
                #print "(swarm) * Not op in %s" % channel_name
                continue
            for botnick in self.get_swarm_members():
                #print "(swarm) * checking %s" % botnick
                if botnick == self.client.nick: # don't try to op myself
                    #print "(swarm) * it's ME! eject eject eject"
                    continue
                if channel.has_nick(botnick) and (not channel.has_op(botnick) and not channel.has_voice(botnick)):
                    self.client.send("MODE %s +o %s" % (channel_name, botnick))
                #print "(swarm) %s in_channel: %s, has_op: %s, has_voice: %s" % (botnick, channel.has_nick(botnick), channel.has_op(botnick), channel.has_voice(botnick))


    def incoming_vote(self, source, target, arguments):
        """if someone else votes we should answer asap"""

        print "(swarm) trig_vote(self,%s,%s,%s)" % (
                source,
                target,
                " ".join(arguments)
            )

        if not self.enabled:
            return

        if target != self.channel:
            print "ERROR: Swarm vote in none swarm channel (%s)" % target
            return False

        (incoming_vote_id, incoming_vote) = self.parse_vote(arguments, source)
        if (incoming_vote_id is None) or (incoming_vote is None):
            print "ERROR: error in vote arguments"
            return False

        if incoming_vote_id not in self.votes:
            self.votes[incoming_vote_id] = {}

        if incoming_vote in self.votes[incoming_vote_id].values():
            print "ERROR: save vote value twice"
            return False

        self.votes[incoming_vote_id][source] = incoming_vote

        if not self.vote_reply_timer and incoming_vote_id != self.current_voteid:
            # new vote, we need to vote
            self.vote_reply_timer = True
            self.unvoted_id = incoming_vote_id
            wait_time = randrange(0,5)
            self.bot.add_timer(
                    datetime.timedelta(0, wait_time),
                    False,
                    self.delayed_vote
                )

        elif self.vote_reply_timer:
            # already a timer running
            print "(swarm) triggered vote but vote_reply_timer is %s" % (self.vote_reply_timer)
        else:
            # we already voted on this
            self.range = self.get_swarm_range() # update ranges
            self.unvoted_id = None # we have no unvoted votes


    def delayed_vote(self):
        self.vote_reply_timer = False
        self.send_vote()


    def swarmchan_join(self):
        # if swarm is enabled and we joined the swarm channel
        # we should start the vote-madness
        self.enable()
        wait_time = randrange(
                int(self.min_vote_time/10),
                int(self.min_vote_time/2)
            )
        print "(swarm) joined swarm channel, voting in %s seconds" % (wait_time)
        self.next_vote_time = time.time() + wait_time
        self.bot.add_timer(
                datetime.timedelta(0, wait_time),
                False,
                self.reoccuring_vote
            )

    def swarmchan_part(self, nick):
        """
        if someone parts the swarm channel we need to
        update the swarm list and recalculate ranges
        """
        print "(swarm) on_part() chan: %s nick: %s" % (event['channel'].name, event['user'].nick)
        if nick in self.get_swarm_members():
            self.remove_bot(nick)

    def reoccuring_vote(self):
        """send out vote every once in a while, if we havn't voted just"""
        if (time.time() - self.last_vote_time) < self.min_vote_time:
            print "(swarm) reoccuring_vote(): throttling vote. %s < %s" % (
                    time.time() - self.last_vote_time,
                    self.min_vote_time)
            return
        if not self.enabled:
            print "(swarm) reoccuring_vote() when swarm is disabled, bailing."
            return

        self.unvoted_id = randrange(0, 65535)
        self.send_vote()

        # bootstrap the next vote to get better control instead of using the
        # built in reoccuring timer. main reason is that we want the first
        # vote to come faster than MIN_VOTE_TIME.
        wait_time = randrange(
                self.min_vote_time,
                self.min_vote_time*2
            )
        print "(swarm) just voted, voting in %s seconds" % (wait_time)
        self.next_vote_time = time.time() + wait_time
        self.bot.add_timer(
                datetime.timedelta(0, wait_time),
                False,
                self.reoccuring_vote
            )


    def send_vote(self):
        """create and send vote to swarm-channel"""
        if self.unvoted_id == None:
            print "(swarm) send_vote(): unvoted_id is None. Escaping."
            return
        if not self.enabled:
            print "(swarm) send_vote(): swarm not enabled. Escaping."
            return

        self.create_vote(self.client.server.mynick)
        self.client.tell(self.channel,"%svote %d %d %s" % (
                self.bot.settings.trigger,
                self.current_voteid,
                self.random,
                self.vote_hash))

        self.last_vote_time = time.time()
