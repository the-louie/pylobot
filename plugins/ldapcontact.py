# coding: utf-8
# Author: Christian Svensson <blue@cmd.nu>
#
# ldap_url = "ldaps://ldap.se"
# ldap_base = "ou=blah"
# ldap_channels = [ '#mychannel' ]

import re
import sys
import ldap
from commands import Command
from settings import Settings

class LdapcontactCommand(Command):
  def __init__(self):
    self.non_decimal = re.compile(r'[^\d+]+')
    self.international = re.compile(r'^0')

  def on_load(self):
    pass

  def on_unload(self):
    pass

  def _format_phone(self, nr):
    if nr == None:
      return ""
    nr = self.non_decimal.sub('', nr)
    nr = self.international.sub('+46', nr)

    if nr.startswith("+46") and len(nr) == 12:
      return nr[0:3] + " " + nr[3:5] + "-" + nr[5:8] + " " + nr[8:10] + " " \
          + nr[10:12]
    return nr

  def _safe_get(self, entry, key):
    return entry[1][key][0] if key in entry[1] else None

  def trig_contact(self, bot, source, target, trigger, argument):
    if not target in Settings().ldap_channels:
      return "Nah, I don't like this channel that much"

    if not argument or argument == "":
      return "You have to specify the username as argument"

    uid = argument.lower()
    con = ldap.initialize(Settings().ldap_url)
    sr = con.search_st(Settings().ldap_base, ldap.SCOPE_SUBTREE, \
        "uid=" + uid, timeout=1)
    if not sr:
      return "Couldn't find that user, sorry :("
    for entry in sr:
      name = entry[1]['sn'][0] + ", " + entry[1]['givenName'][0]
      email = self._safe_get(entry, 'gosaMailForwardingAddress')
      home =  self._safe_get(entry, 'homePhone')
      work =  self._safe_get(entry, 'telephoneNumber')
      name = name.decode('utf-8')

      txt = name.encode('utf-8') + " " + uid + " " + \
        (email if email else "") + " " + self._format_phone(home)
      if work:
        txt = txt + " (" + self._format_phone(work) + ")"

      return txt

if __name__ == "__main__":
  l = LdapcontactCommand()
  print l.trig_contact(None, None, "#dhtech", None, "")
  print l.trig_contact(None, None, "#dhtecasdh", None, "access")
  print l.trig_contact(None, None, "#dhtech", None, "access123")
  print l.trig_contact(None, None, "#dhtech", None, "bluecmd")
