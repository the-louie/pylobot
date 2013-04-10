# coding: utf-8
# Author: Christian Svensson <blue@cmd.nu>

# Note: first %s = team, second %s = time via log_svn_time_format
# def _get_svn_url(settings, svn):
#   event = svn.cat ("https://cmd.nu/svn/trunk/test").strip()
#   return "https://cmd.nu/svn/trunk/" + event + "%s_%s.txt"
#
# log_svn_url = _get_svn_url
# log_svn_channels = [ '#mychannel' ]
# log_svn_username = "user"
# log_svn_password = "password"
# log_svn_time_format = "%Y%m%d"
# log_svn_teams = [ "access", "team" ]

import pysvn
import os
from tempfile import NamedTemporaryFile
from datetime import datetime
from commands import Command
from settings import Settings

class Logger(Command):
  hooks = [ "on_privmsg" ]
  def __init__(self):
    self.svn = pysvn.Client()
    self.svn.callback_get_login = self._get_login
    self.svn.callback_ssl_server_trust_prompt = self._ssl_trust
    self.logs = {}

  def _get_login(self, realm, username, may_save):
    return True, Settings().log_svn_username, \
      Settings().log_svn_password, False

  def _ssl_trust(self, trust_dict):
    return True, 1, True

  def on_load(self):
    pass

  def on_unload(self):
    pass

  def on_privmsg(self, bot, source, target, message, network, **kwargs):
    if not target in self.logs:
      return None

    # Log it!
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source = source.split('!')[0].rjust(16)
    self.logs[target]["log"].append(time + " " + source + "> " + message)
    return None

  def trig_logstart(self, bot, source, target, trigger, argument):
    if target in self.logs:
      return "I'm already logging this channel"

    if not target in Settings().log_svn_channels:
      return "Nah, I don't like this channel that much"

    if not argument or argument == "":
      return "You have to specify the group name as argument"

    team = argument.lower()

    if not team in Settings().log_svn_teams:
      return "Nobody told me there is a '" + team + "' group :("

    time = datetime.now().strftime(Settings().log_svn_time_format)

    self.logs[target] = { "team" : team, "time": time, "log": [] }
    return "Logging ..."

  def trig_logstop(self, bot, source, target, trigger, argument):
    if not target in self.logs:
      return "Sorry, nobody told me to record this channel :("

    l = self.logs[target]
    tmp = NamedTemporaryFile(delete=False)
    tmp.write("\n".join(l["log"]))
    tmp.close()

    url = Settings().log_svn_url(self.svn) % (l["team"], l["time"])
    try:
      self.svn.import_ (tmp.name, url,
	  'IRC auto logger: ' + l["team"] + ' @ ' + l["time"])

      os.unlink(tmp.name)
    except pysvn._pysvn.ClientError as e:
      return "Oops! I failed to upload the log (" + tmp.name + \
	"), error is: " + str(e)

    del self.logs[target]
    return "Log uploaded to " + url

if __name__ == "__main__":
  l = Logger()
  print l.trig_logstart(None, None, "#dhtech", None, "")
  print l.trig_logstart(None, None, "#dhtecasdh", None, "access")
  print l.trig_logstart(None, None, "#dhtech", None, "access123")
  print l.trig_logstart(None, None, "#dhtech", None, "access")
  print l.trig_logstart(None, None, "#dhtech", None, "access")
  print l.on_privmsg(None, "blueCmd", "#dhtech", "Tja lol", None)
  print l.on_privmsg(None, "soundguuf", "#dhtech", "Hej hej hej hej", None)
  print l.trig_logstop(None, None, "#dhtech", None, "")
  print l.trig_logstop(None, None, "#dhtech", None, "")
  print l.trig_logstart(None, None, "#dhtech", None, "access")
  print l.on_privmsg(None, "blueCmd", "#dhtech", "Tja lol", None)
  print l.on_privmsg(None, "blueCmd", "#dhtech", "Tja lol", None)
  print l.on_privmsg(None, "soundguuf", "#dhtech", "Hej hej hej hej", None)
  print l.trig_logstop(None, None, "#dhtech", None, "")
