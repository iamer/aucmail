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

import imaplib
import gdata
import gdata.service
import gdata.contacts
import gdata.contacts.service
from migrationwizard.lib.util import getFolders , getMessagesInFolder

def imaplogin(host, username, password):
    try:
        server = imaplib.IMAP4_SSL(host)
        server.login(username,password)
        return ('OK' , server)
    except server.error:
        return ('NO', server.error)

def imaplogout(server):
    try:
        server.logout()
    except:
        pass

def captchaUnlockNeeded(email, password):
    try:
        gd_client = gdata.contacts.service.ContactsService()
        gd_client.email = email
        gd_client.password = password
        gd_client.ProgrammaticLogin()
        return False 
    except gdata.service.CaptchaRequired, message:
        return True

def getNumberOfMailsLargerThan(server,size):
    messages_count = 0
    folders = getFolders(server)
    for folder in folders:
        messages = getMessagesInFolderLargerThan(server,folder,size)
        if(messages):
            messages_count += len(messages)
    return messages_count

def getMessagesInFolderLargerThan(server,folder,size):
     try:
         server.select(folder)
         r = server.search(None,"(LARGER " + str(size) + ")")
         if( r[0] == 'OK'):
            splitted = r[1][0].split(' ')
            if(len(splitted) == 1 and splitted[0] == '' ):
                return None
            else:
                return r[1][0].split(' ')
         else:
             return None
     except:
         return None

def getMailBoxSize(server):
    totalSize = 0
    folders = getFolders(server)
    for folder in folders:
        messages = getMessagesInFolder(server,folder)
        if(messages):
            for i in messages:
                sizeinfo = server.fetch(i,"(RFC822.SIZE)")
                if(sizeinfo[0] == 'OK'):
                    import re
                    value = re.search('[0-9]+\s*[(][\w\W]* ([0-9]*)',sizeinfo[1][0])
                    if(value):
                        totalSize += int(value.group(1))
    return totalSize
                    
