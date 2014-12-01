from sys import argv
from autoreloader.autoreloader import AutoReloader # Do not remove
class Settings(AutoReloader):                      # these two lines

	# Sample config, all options are mandatory
	server: {
			"server_address": "irc.server.com",
			#"server_password": "mypassword", # optional, omit if unused.
			"server_port": 6667,
			"nick": ["nickname_a", "nickname_b", "nickname_c"],
			"username": None,
			"realname": "PyIrkBot",
			"channels": [["#a_channel"],["#another_channel"],["#channel_with_key","secretkey"]],
			"swarm": {
				"channel": "#bot_swarm_channel",
				"secret": "H3KJ9/NS8(L6SN2HI",
				"opchans": ["#a_channel","#another_channel","#channel_with_key"]
			},
	     }

	# if we supply qauth via command line deffer joins
	# until we are mode +x
	if len(argv) == 3:
		deferred_join_all = True
		qauth = (argv[1], argv[2])
	else:
		deferred_join_all = False
		qauth = None

	trigger = "."

	recode_out_default_charset = "iso-8859-15"
	recode_fallback = "iso-8859-15"

	# Plugins that will be loaded on startup from plugins/
	# Use this directory to view all available Plugins and to add your own.
	plugins = ['plugins', 'command_catcher', 'commands', 'utility' ]
