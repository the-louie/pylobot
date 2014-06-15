class landladySettings:
	# database config
	db_con = None
	db_cur = None

	# channel for contol
	cc_channel = '#dreamhack.c&c'

	settings = None
	kb_settings = {}
	kb_commands = {}
	swarm = {}
	swarm_enabled = True

	default = {
		'swarm': {
			'channel': '#dreamhack.swarm',
		},

		'kb_settings': {
				'command_chan': '#dreamhack.c&c',
				'master_chan' : '#dreamhack.op2',
				'child_chans' : '#dreamhack.trade',
				'ban_timemul' : '1,2,4,8,72,504,2016',
				'kick_tagline': 'Please read the rules at http://irc.dhcrew.se',
		},

		'kb_commands': {
				'cmd_evade': 	'3600 Please do not evade bans',
				'cmd_date': 	'600 Please join #dreamhack.date with all the other silly boys',
				'cmd_caps': 	'600 ALL CAPS MAKES YOUR EYES SQUARE',
				'cmd_flood': 	'600 Please do not flood our channel',
				'cmd_rules': 	'600 You are breaking the rules',
				'cmd_raid': 	'600 Just say "NO" to raid',
				'cmd_spam': 	'600 Please take your advertisment elsewere',
				'cmd_amsg': 	'600 Please do not use amsg while in this channel',
				'cmd_script': 	'600 Please do not use mp3-script or the like in this channel',
				'cmd_language': '600 Please mind your language',
				'cmd_trade': 	'600 Please use #dreamhack.trade for peddling junk',
				'cmd_clones':	'600 Please do not use clones or bots in our channel',
				'cmd_warez': 	'600 Please do not talk about warez',
				'cmd_away': 	'600 Please do not use awaymessages in the channel',
				'cmd_pcw': 		'600 PCW, Clanseeking and anything game related takes place in #dreamhack.game',
				'cmd_repeat': 	'600 No need to repeat yourself, no need to repeat youself',
				'cmd_begging': 	'600 Please join #dreamhack.beggers with all the other poor people',
				'cmd_tobak': 	'600 Please no controlled substances here, the police will get you',
				'cmd_drugs': 	'600 Please no drugs here',
				'cmd_ohbehave': '600 Please do not behave inappropriate here'
		}
	}
