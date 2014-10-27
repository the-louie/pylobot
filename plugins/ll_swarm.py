
'''


	handle swarm messages and stuff

	The following functions handles voting and also decides
	if a action is to be taken depending on a keyword


'''
class Swarm():
	def __init__(self):
		self.range = (65535,0)
		self.votes = {}
		self.enabled = True
		self.id = 0
		self.random = 0
		self.voteid = None
		self.unvoted_id = None
		self.channel = "#dreamhack.swarm"
		self.last_vote_time = 0
		self.posponed_vote_count = 0

	def update_swarm_range(self, vote):
		swarm_range = (min(self.range[0], vote), max(self.range[1], vote))

		return swarm_range


	def parse_vote(self, argument):
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
		sorted_swarm_votes = sorted(self.votes[self.voteid].values())
		#print self.votes
		my_index = sorted_swarm_votes.index(self.random)
		client_count = len(self.votes[self.voteid].keys())

		buckets = [0]
		bucket_size = 256.0/(len(sorted_swarm_votes))
		curr_bucket = bucket_size
		for tmp in range(0,255):
		  if tmp > curr_bucket:
			buckets.append(tmp)
			curr_bucket = curr_bucket + bucket_size

		buckets.append(255)
		swarm_range = (buckets[my_index],buckets[my_index+1])

		if swarm_range[1] == 255:
			swarm_range = (swarm_range[0], 256)

		return swarm_range


