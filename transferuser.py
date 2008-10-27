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

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'migrationwizard.settings'
from migrationwizard.lib import contacts
from migrationwizard.lib import emails
from migrationwizard.lib import util
import sys
import imaplib
from migrationwizard import ocsettings
import string,traceback
from migrationwizard.lib import ldif
import gdata
import gdata.apps
import gdata.apps.service

from migrationwizard.wizard.models import Users_info
from migrationwizard.lib.util import addLogMessage

from datetime import datetime

import socket
socket.setdefaulttimeout(ocsettings.socket_default_timeout)

def getUser(username):
    user = Users_info.objects.get(username__exact=username)
    return user

if(len(sys.argv) < 2 or len(sys.argv) > 2):
   print "Usage: python transferuser.py username"
   sys.exit(1)

username = None
for i,arg in enumerate(sys.argv):
    if( i == 0):
       pass
    else:
       username = arg
       break

user = None
if(username):
    user = getUser(username)

def getldf(email):
    command = ocsettings.commandpath + email

    pipe = os.popen(command,'r')
    hash = pipe.read()
    pipe.close()
    sanehash = hash[0:(len(hash) - 1)]
    ldfpath = ocsettings.lookpath + sanehash + "/" + email + "/abook.ldf"
    if os.path.exists(ldfpath):
        return ldfpath
    else:
        return None
    
try:
    # Get total number of emails to be uploaded
    auc_server = imaplib.IMAP4_SSL(ocsettings.auc_imap)
    auc_server.login(user.username,user.password)
    number = util.getNumberOfEMails(auc_server)
    user.mails_total = number
    user.migration_start_time = datetime.now() 
    user.state = "in_progress"
    user.process_pid = os.getpid()

    email2 = user.username + '@' +ocsettings.auc_old_domain
    filename = getldf(string.lower(email2))
    if(filename != None):
        try:
            file = open(filename,'r')
        except Exception,message:
            user.state = "failed"
            msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
            msg = str(message.message) + '\n' + msg
            addLogMessage(user.username,msg,'E')
            user.save()
            if(user.retry_number == ocsettings.max_retries_per_user):
                subject = user.username + " couldn't open ldf file"
                msg = user.username + " has failed to access his address book\nPlease check the logs."
                util.oc_send_mail(subject, msg, ocsettings.admin_account ,[ocsettings.admin_account])
            sys.exit(1)
            
        parser = ldif.LDIFRecordList(file)
        parser.parse()
        totalNumberOfContacts = len(parser.all_records)
        user.contacts_total = totalNumberOfContacts
        contacts_skip_count = user.contacts_added + user.contacts_updated 
        groups_skip_count = user.groups_added + user.groups_updated
    
    user.save()

    # Transfer contacts
    contacts.start(user)
    # Transfer emails
    emails.start(user)
    user.state = "done"
    user.migration_end_time = datetime.now() 
    user.save()

except gdata.apps.service.AppsForYourDomainException, m:
    user.state = 'failed'
    user.save()
    msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
    msg = str(m.message) + '\n' + msg
    msg = str(m.reason) + '\n' + msg
    addLogMessage(user.username,msg,'E')
    if(user.retry_number == ocsettings.max_retries_per_user):
        subject = user.username + "'s failure"
        msg = user.username + " has failed to migrate for "+ str(ocsettings.max_retries_per_user) +" times.\nPlease check the logs."
        util.oc_send_mail(subject, msg, ocsettings.admin_account ,[ocsettings.admin_account])
    sys.exit(1)

except socket.sslerror, m:
    if str(m.message) == "(8, 'EOF occurred in violation of protocol')" :
        user.state = 'in_queue'
    else:
        user.state = 'failed'
    user.save()
    msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
    msg = str(m.message) + '\n' + msg
    addLogMessage(user.username,msg,'E')
    if(user.retry_number == ocsettings.max_retries_per_user):
        subject = user.username + "'s failure"
        msg = user.username + " has failed to migrate for "+ str(ocsettings.max_retries_per_user) +" times.\nPlease check the logs."
        util.oc_send_mail(subject, msg, ocsettings.admin_account ,[ocsettings.admin_account])
    sys.exit(1)

except Exception,m:
    user.state = 'failed'
    user.save()
    msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
    msg = str(m.message) + '\n' + msg
    addLogMessage(user.username, msg, 'E')
    if(user.retry_number == ocsettings.max_retries_per_user):
        subject = user.username + "'s failure"
        msg = user.username + " has failed to migrate for "+ str(ocsettings.max_retries_per_user) +" times.\nPlease check the logs."
        util.oc_send_mail(subject, msg, ocsettings.admin_account ,[ocsettings.admin_account])
    sys.exit(1)

try:
    if ( user.givenname ) and ( user.sn ):
        util.welcome_mail("Welcome to AUCmail",ocsettings.admin_account, user.username, user.givenname + ' ' + user.sn)
    else:
        util.welcome_mail("Welcome to AUCmail",ocsettings.admin_account, user.username, user.username )
except Exception, m:
    msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
    msg = str(m.message) + '\n' + msg
    addLogMessage(user.username, msg, 'W')

forward_list = []
if(user.mail_fwd_address != ''):
    forward_list = user.mail_fwd_address.split(',')
    google_forward = user.username + '@' + ocsettings.gmail_forword_domain
    if google_forward in forward_list:
       forward_list.remove(google_forward)
    if '' in forward_list:
       forward_list.remove('')

try:
    util.technotes_mail("Technical instructions", forward_list, ocsettings.admin_account, user.username , user.givenname + ' ' + user.sn)
except Exception, m:
    msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
    msg = str(m.message) + '\n' + msg
    addLogMessage(user.username, msg, 'W')

if(user.mobile != ''):
    try:
        util.send_sms(user.mobile,user.id_id)
    except Exception, m:
        msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
        msg = str(m.message) + '\n' + msg
        addLogMessage(user.username, msg, 'W')

