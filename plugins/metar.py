# coding: utf-8
# Author: Christian Svensson <blue@cmd.nu>

import urllib2
import re
from datetime import datetime, timedelta
from commands import Command

class Metar(Command):
  def __init__(self):
    self.metar = {}
    self.taf = {}
    self.metar_update_time = datetime.now()
    self.taf_update_time = datetime.now()

  def on_load(self):
    self.metar_update_time = datetime.now()
    self.taf_update_time = datetime.now()

  def on_unload(self):
    self.metar = {}
    self.taf = {}

  def trig_metar(self, bot, source, target, trigger, argument):

    if not argument or argument == "":
      return "You have to specify the airport ICAO code"

    argument = argument.upper()

    if self.metar_update_time < datetime.now():
      data = urllib2.urlopen('http://www.lfv.se/MetInfo.asp?TextFile=metar.sweden.list.txt&SubTitle=&T=METAR%A0Sweden&Frequency=30')
      self.metar = {}
      for metar in re.findall('(ES[A-Z]{2}) (.*?)=', data.read(), re.DOTALL):
        self.metar[metar[0]] = ' '.join(metar[1].split())

      self.metar_update_time = datetime.now() + timedelta(minutes=20)

    if argument in self.metar:
      return "%s: %s" % (argument, self.metar[argument])
    
    return "I am unfamiliar with the airport '" + argument + "'"

  def trig_taf(self, bot, source, target, trigger, argument):

    if not argument or argument == "":
      return "You have to specify the airport ICAO code"

    argument = argument.upper()

    if self.taf_update_time < datetime.now():
      data = urllib2.urlopen('http://www.lfv.se/MetInfo.asp?TextFile=taffc.sweden.list.txt&SubTitle=&T=TAF%A0Sweden&Frequency=120')
      self.taf = {}
      for metar in re.findall('(ES[A-Z]{2}) (.*?)=', data.read(), re.DOTALL):
        self.taf[metar[0]] = ' '.join(metar[1].split())

      self.taf_update_time = datetime.now() + timedelta(minutes=20)

    if argument in self.taf:
      return "%s: %s" % (argument, self.taf[argument])
    
    return "I am unfamiliar with the airport '" + argument + "'"


if __name__ == "__main__":
  print Metar().trig_metar(None, None, None, None, "")
  print Metar().trig_metar(None, None, None, None, " ")
  print Metar().trig_metar(None, None, None, None, "ESSA")
  print Metar().trig_metar(None, None, None, None, "ESSL")

  print Metar().trig_taf(None, None, None, None, "")
  print Metar().trig_taf(None, None, None, None, " ")
  print Metar().trig_taf(None, None, None, None, "ESSA")
  print Metar().trig_taf(None, None, None, None, "ESSL")
