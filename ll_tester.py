from plugins.ll_utils import LLUtils

class client:
	def __init__(self):
		self.users_list = {
			'one': 'one!user@domain.tld',
			'one2': 'one2!user@domain.tld',
			'two': 'two!user@sub.domain.tld',
			'two2': 'two2!user2@sub.domain.tld',
			'three': 'three!user@sub.sub.domain.tld',
			'four': 'four!user@127.0.0.1',
			'five': 'five!user@127.0.1.1',
			'six': 'six!user@127.1.1.1',
			'alfa': 'alfa!user@127.0.1.1',
		}

		self.nick_lists = {
			'#dreamhack': {
				'one': 'one!user@domain.tld',
				'one2': 'one2!user@domain.tld',
				'two': 'two!user@sub.domain.tld',
				'two2': 'two2!user2@sub.domain.tld',
				'three': 'three!user@sub.sub.domain.tld',
				'four': 'four!user@127.0.0.1',
				'five': 'five!user@127.0.1.1',
				'six': 'six!user@127.1.1.1',
				'alfa': 'alfa!user@127.0.1.1'
			}
		}


Util = LLUtils()
c = client()
print Util.create_banmask(c, 'one')