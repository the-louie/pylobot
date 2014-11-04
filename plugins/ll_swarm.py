"""
ll_swarm

peer-to-peer distribution of actions between all bots in the swarm

"""
from random import randrange
import time
import hashlib

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
        self.channel = "#dreamhack.swarm"

        self.next_vote_time = 0
        self.last_vote_time = 0

        self.reoccuring_voting_enabled = False

    def nick_matches(self, targetnick):
        md5hash = hashlib.md5()
        md5hash.update(targetnick)
        hashid = int(md5hash.hexdigest()[0:2], 16)
        if not self.range[0] <= hashid < self.range[1]:
            return False
        else:
            return True

    def get_current_votes(self):
        return self.votes[self.current_voteid]

    def update_swarm_range(self, vote):
        """
        update swarm range
        """
        lowest = min(self.range[0], vote)
        highest = max(self.range[1], vote)
        swarm_range = (lowest, highest)
        return swarm_range

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

    def parse_vote(self, argument):
        """
        parse an incomming vote and make sure it contains
        everything we need.
        """
        try:
            (vote_id_str, vote_value_str) = argument.split(' ')
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
        if nick not in self.votes[self.current_voteid].keys():
            # not a swarm bot
            return

        del self.votes[self.current_voteid][nick] # remove bot from swarm
        self.range = self.get_swarm_range() # update ranges

