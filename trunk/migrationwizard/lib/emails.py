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

import getpass, imaplib
from email.message import Message
import email,mimetypes
import sys
from migrationwizard import ocsettings
import adhocmailmigration
import gdata , gdata.apps , gdata.apps.service
import util
from util import addLogMessage
from ldap_attribs import *

import os
import socket
socket.setdefaulttimeout(ocsettings.socket_default_timeout)

import time
import string
import traceback

ReplaceString = """

This message contained an attachment that was stripped out. 

You can access it through URL:
%(file_url)s

"""

offending_folder = "Managed"
user_object = None

service = gdata.apps.service.AppsService(email=ocsettings.admin_auc_gmail_email , domain=ocsettings.auc_domain, password=ocsettings.admin_auc_gmail_password)
service.ProgrammaticLogin()

emails_skip_count = 0
skipped_emails = 0

def sanitise(msg):
    ct = msg.get_content_type()
    fn = msg.get_filename()
    if not fn:
        fn = msg.get_param("name")
    if fn and msg['Content-Transfer-Encoding'] == 'base64':
        dir = ocsettings.attachment_path_on_server + '/' + user_object.username
        addLogMessage(user_object.username , "Stripping attachment " + fn , 'I')
        try:
            os.mkdir( dir )
        except OSError:
            pass
        finally:
            fn = fn.replace(' ','_')
            file_location = dir + '/' + fn
            fp = open(file_location, 'wb')
            fp.write(msg.get_payload(decode=True))
            fp.close()
            params = msg.get_params()[1:] 
            params = ', '.join([ '='.join(p) for p in params ])
            file_url = ocsettings.attachment_server_url + '/' + user_object.username + "/" + fn
            replace = ReplaceString % dict(file_url=file_url)
            msg.set_payload(replace)
            for k, v in msg.get_params()[1:]:
                msg.del_param(k)
            msg.set_type('text/plain')
            del msg['Content-Transfer-Encoding']
            del msg['Content-Disposition']
    else:
        if msg.is_multipart():
            payload = [ sanitise(x) for x in msg.get_payload() ]
            msg.set_payload(payload)
    return msg

    
def getFolders(server,sep):
    mboxs = server.list()[1]
    folders = []
    for box in mboxs:
        temp = box
        temp = temp.split('\"'+sep+'\"')[1].strip().replace('\"','').replace("\'",'')
        folders.append(temp) 
    return folders

def getMessagesInFolder(server,folder):
    try:
        server.select(folder)
        r = server.search(None,"ALL")
        if( r[0] == 'OK'):
#            print 'messages found in folder ' +  folder
            splitted = r[1][0].split(' ')
            if(len(splitted) == 1 and splitted[0] == '' ):
                return None
            else:
                return r[1][0].split(' ')
        else:
            return None
    except:
        return None

def getMessageSubject(server,num):
    try:
        data = server.fetch(num,"(BODY[HEADER.FIELDS (SUBJECT)])")
        return data[1][0][1].strip()
    except:
        return "no subject"
    return "no subject"

def getMessageFrom(server,num,folder):
    try:
        server.select(folder)
        typ, data = server.fetch(num,"(BODY[HEADER.FIELDS (FROM)])")
        return data[0][1].split(": ")[1]
    except:
        return "no_from"
    return "no_from"

def getMessageTo(server,num,folder):
    try:
        server.select(folder)
        typ, data = server.fetch(num,"(BODY[HEADER.FIELDS (TO)])")
        return data[0][1].split(": ")[1]
    except:
        return "no_to"
    return "no_to"

def getMsgSize(server, num):
    sizeinfo = server.fetch(num,"(RFC822.SIZE)")
    if(sizeinfo[0] == 'OK'):
        import re
        value = re.search('[0-9]+\s*[(][\w\W]* ([0-9]*)',sizeinfo[1][0])
        if(value):
            return int(value.group(1))
    return None          

def getMsg(server,num,folder):
    server.select(folder)
    typ, data = server.fetch(num, '(RFC822)')
    return data

def cleanToFromSubject(data,toAddr,fromAddr,subject):
    try:
        cleanTo = ''
        cleanFrom = ''
        cleanSubject = ''

        try:
            ltIndex = toAddr.index("<")
            gtIndex = toAddr.index(">")
            slicedAddr = toAddr[ ltIndex+1 : gtIndex ]
            slicedName = toAddr[ 0 : ltIndex ]

            if " " in slicedAddr:
                spaceIndex = slicedAddr.index(" ")
                cleanTo = slicedAddr[ 0 : spaceIndex ]
                cleanTo = slicedName + "<" + cleanTo + ">"
                data = data.replace(toAddr.strip(),cleanTo)
        except ValueError,e:
            if(e.message == 'substring not found'):
	        data = data.replace(toAddr.strip(),toAddr.strip().replace(" ",''))
                #pass
        try:
            ltIndex = fromAddr.index("<")
            gtIndex = fromAddr.index(">")
            slicedAddr = fromAddr[ ltIndex+1 : gtIndex ]
            slicedName = fromAddr[ 0 : ltIndex ]

            if " " in fromAddr:
                spaceIndex = slicedAddr.index(" ")
                cleanFrom = slicedAddr[ 0 : spaceIndex ]
                cleanFrom = slicedName + "<" + cleanFrom + ">"
                data = data.replace(fromAddr.strip(),cleanFrom)
        except ValueError,e:
            if(e.message == 'substring not found'):
	        data = data.replace(fromAddr.strip(),fromAddr.strip().replace(" ",''))
                #pass

        return data
    except Exception, m:
        addLogMessage(user_object.username, "Could not clean message " + subject , 'W')
   
def sendMessage(server,folder,msg):
    data = getMsg(server,msg,folder)
    toAddr = getMessageTo(server,msg,folder)
    fromAddr = getMessageFrom(server,msg,folder)
    subject = getMessageSubject(server,msg)
    size = getMsgSize(server,msg)
    msg_string = ''

    if( size > ocsettings.max_attachment_size):
        msg_string = str(sanitise(email.message_from_string(data[0][1])))
        offending = True
        user_object.offending_mails_count += 1
        user_object.save()
    else:
        msg_string = data[0][1]
        offending = False 
    
    emailfeed = adhocmailmigration.MailItemEntry()
    emailfeed.setRfc822Msg(msg_string)
    if(folder == "Inbox" or folder == "inbox"):
        emailfeed.addMailProperty("IS_INBOX")
    elif (folder == "Drafts" or folder == "draft" or folder == "drafts"):
        emailfeed.addMailProperty("IS_DRAFT")
    elif (folder == "Trash"):
        emailfeed.addMailProperty("IS_TRASH")
    elif(folder == "Sent" or folder == "sent"):
        emailfeed.addMailProperty("IS_SENT")
    else:
        emailfeed.addLabel(folder)
    if offending :
       emailfeed.addLabel(offending_folder)
    try :
        response = service.Post(str(emailfeed), "/a/feeds/migration/2.0/%s/%s/mail" % ( ocsettings.auc_domain , user_object.username) )
    except gdata.service.RequestError, m:
        if m[0]['body'] == 'Invalid RFC 822 Message: Illegal whitespace in address':
            msg_string = cleanToFromSubject(msg_string,toAddr,fromAddr,subject)
    	    emailfeed.setRfc822Msg(msg_string)
	    service.Post(str(emailfeed), "/a/feeds/migration/2.0/%s/%s/mail" % ( ocsettings.auc_domain , user_object.username ))
    except socket.sslerror, m:
        msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
        if "(8, 'EOF occurred in violation of protocol')" in msg :
            user_object.state = 'in_queue'
            msg = 'sslerror EOF error, not incrementing retry count' + '\n' + msg
        else:
            user_object.state = 'failed'
        user_object.save()
        msg = str(m.message) + '\n' + msg
        addLogMessage(user_object.username,msg,'E')
        if(user_object.state == 'failed' and user_object.retry_number == ocsettings.max_retries_per_user):
            subject = user_object.username + "'s failure"
            msg = user_object.username + " has failed to migrate for "+ str(ocsettings.max_retries_per_user) +" times.\nPlease check the logs."
            util.oc_send_mail(subject, msg, ocsettings.admin_account ,[ocsettings.admin_account])
        sys.exit(1)
    except socket.error, m:
        msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
        if "(104, 'Connection reset by peer')" in msg :
            user_object.state = 'in_queue'
            msg = "socket 'Connection reset by peer' error, not incrementing retry count" + '\n' + msg
        elif "(32, 'Broken pipe')" in msg :
            user_object.state = 'in_queue'
            msg = "socket 'Broken pipe' error, not incrementing retry count" + '\n' + msg
        else:
            user_object.state = 'failed'
        user_object.save()
        msg = str(m.message) + '\n' + msg
        addLogMessage(user_object.username,msg,'E')
        if(user_object.state == 'failed' and user_object.retry_number == ocsettings.max_retries_per_user):
            subject = user_object.username + "'s failure"
            msg = user_object.username + " has failed to migrate for "+ str(ocsettings.max_retries_per_user) +" times.\nPlease check the logs."
            util.oc_send_mail(subject, msg, ocsettings.admin_account ,[ocsettings.admin_account])
        sys.exit(1)

    user_object.mails_uploaded += 1
    user_object.emails_bytes_uploaded += size
    user_object.save()
    try:
        addLogMessage(user_object.username, 'Added Message: "' + subject + '" of size ' + str(size) )
    except:
        try:
            addLogMessage(user_object.username, "Added Message of size " + str(size) )
        except:
            pass



def updateFolder(folder,auc_server,sep,gmail_sep):
    global service, emails_skip_count,skipped_emails
  
    messages = getMessagesInFolder(auc_server,folder)
    if(messages):
        for msg in messages:
            if(skipped_emails < emails_skip_count):
                skipped_emails += 1
                continue
            start_time = time.time()
            sendMessage(auc_server,folder,msg)
            end_time = time.time()
            user_object.emails_upload_time += (end_time - start_time)
            user_object.save()


def getUnseenMessages(server,folder):
    try:
        server.select(folder)
        r = server.search(None,"UNSEEN")
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

def handleUnseenMessages(server):
    folder = "Inbox"
    server.select(folder)
    messages = getUnseenMessages(server,folder)
    if(messages):
        for msg in messages:
            sendMessage(server,folder,msg)

def transferEmails(auc_server):
    folders = getFolders(auc_server,"/")

    if 'Inbox' in folders:
        folders.remove('Inbox')
        folders.append('Inbox')
    elif 'inbox' in folders:
        folders.remove('inbox')
        folders.append('inbox')

    for folder in folders:
        addLogMessage(user_object.username,"Updating folder " + folder)
        updateFolder(folder,auc_server,'/','/')

    handleUnseenMessages(auc_server)


def start(user):
    global user_object, emails_skip_count, skipped_emails
    user_object = user
    #email = user.username + ocsettings.auc_old_domain
    auc_server = imaplib.IMAP4_SSL(ocsettings.auc_imap)
    auc_server.login(user.username,user.password)
    emails_skip_count = user.mails_uploaded
    skipped_emails = 0
    setInitialForwordAttribute(user_object)
    transferEmails(auc_server)
    unsetLocalStoreAttribute(user_object)
    setOnlyGmailForwordAttribute(user_object)
