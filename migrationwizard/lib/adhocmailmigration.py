"""
Copyright (c) 2008, Opencraft <www.open-craft.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import htmlentitydefs
import re, string
import base64

def escapeMailText(rfc822Msg):
  def base64_encode(string):
    return base64.b64encode(string)

  return base64_encode(rfc822Msg)

def characterEscape(text):
# this pattern matches substrings of reserved and non-ASCII characters  
  pattern = re.compile(r"[&<>\"\x80-\xff]+")

# create character map
  entity_map = {}

  for i in range(256):
    entity_map[chr(i)] = "&%d;" % i

  for entity, char in htmlentitydefs.entitydefs.items():
    if entity_map.has_key(char):
        entity_map[char] = "&%s;" % entity

  def escape_entity(m, get=entity_map.get):
    return string.join(map(get, m.group()), "")

  def escape(string):
    return pattern.sub(escape_entity, string)

  return escape(text)



class MailItemEntry():

  xmlmailProperty = "<apps:mailItemProperty xmlns:apps='http://schemas.google.com/apps/2006' value='%s'/>"
  xmlmailLabel = "<apps:label xmlns:apps='http://schemas.google.com/apps/2006' labelName='%s'/>"
  allowedProperties = [ "IS_DRAFT", "IS_INBOX", "IS_SENT", "IS_STARRED", "IS_TRASH", "IS_UNREAD" ]
  
  feedHeader = """<atom:entry xmlns:atom='http://www.w3.org/2005/Atom'>
  <atom:category scheme='http://schemas.google.com/g/2005#kind'
    term='http://schemas.google.com/apps/2006#mailItem'/>"""

  feedFooter = "</atom:entry>"

  rfc822MsgContainer = """<apps:rfc822Msg xmlns:apps="http://schemas.google.com/apps/2006" encoding="base64"> %s </apps:rfc822Msg>"""

  def __init__(self, rfc822Msg=None, properties=None, labels=None):
    self.rfc822Msg = rfc822Msg
    self.properties = []
    self.labels = []

  def setRfc822Msg(self, msg):
    self.rfc822Msg = msg
    
  def addMailProperty(self, propertyname):
    self.properties.append(propertyname)
    
  def addLabel(self, label_name):
    label_name = characterEscape(label_name)
    self.labels.append(label_name)

  def __str__(self):
    self.escaped_msg = escapeMailText(self.rfc822Msg)
    self.msg_xml = self.rfc822MsgContainer % self.escaped_msg

    self.email = self.feedHeader + self.msg_xml

    self.properties_xml = ""
    for propertyname in self.properties :
      self.property_xml = self.xmlmailProperty % propertyname
      self.properties_xml = self.property_xml + self.properties_xml

    self.email = self.email + self.properties_xml

    self.labels_xml = ""
    for labelname in self.labels :
      self.label_xml = self.xmlmailLabel % labelname
      self.labels_xml = self.labels_xml + self.label_xml

    self.email = self.email + self.labels_xml

    self.email += self.feedFooter

    return self.email
