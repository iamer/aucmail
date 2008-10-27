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

import gdata
import sys
import os
import getopt
import getpass
import atom
import gdata.contacts
import gdata.contacts.service
import gdata.service
import ldif
import traceback
from migrationwizard import ocsettings
import migrationwizard.lib.util as util

from migrationwizard.wizard.models import Users_info
from util import addLogMessage
import string
import socket
socket.setdefaulttimeout(ocsettings.socket_default_timeout)
import atom
atom.XML_STRING_ENCODING = None 
import time

gd_client = None
localuser = None

contacts_skip_count = 0
skipped_contacts = 0

groups_skip_count = 0
skipped_groups = 0

#Login to service
def gmailLogin(email, password):
    try:
        gd_client = gdata.contacts.service.ContactsService()
        gd_client.email = email
        gd_client.password = password
        gd_client.ProgrammaticLogin()
        return gd_client
    except Exception,message:
        localuser.state = "failed"
        msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
        msg = str(message.message) + "\n" + msg
        addLogMessage(localuser.username,msg,'E')
        localuser.save()
        if(localuser.retry_number == ocsettings.max_retries_per_user):
            subject = localuser.username + "'s failure"
            msg = localuser.username + " has failed to migrate for "+ str(ocsettings.max_retries_per_user) +" times.\nPlease check the logs."
            util.oc_send_mail(subject, msg, ocsettings.admin_account ,[ocsettings.admin_account])
        sys.exit(1)

#Create contacts
def createContact(contact_name, contact_email , contact_mobile=None , contact_home=None):
    global gd_client
    new_contact = gdata.contacts.ContactEntry(title=atom.Title(text=contact_name))

    if(contact_mobile and ('' in contact_mobile)):
        contact_mobile.remove('')
        if(len(contact_mobile)):
            contact_mobile = None
    
    if(contact_home and ('' in contact_home)):
        contact_home.remove('')
        if(len(contact_home)):
            contact_home = None
    
    if(not contact_email ):
        if('@' in contact_name):
            contact_email = [contact_name]

    try:
        for i,email in enumerate(contact_email):
            primary = 'false'
            if(i==0):
                primary='true'
            new_contact.email.append(gdata.contacts.Email(address=email,primary=primary, rel=gdata.contacts.REL_WORK))
    except Exception, m:
        pass

    if(contact_mobile != None):
        for number in contact_mobile:
            new_contact.phone_number.append(gdata.contacts.PhoneNumber(rel=gdata.contacts.REL_OTHER,text=number))
            
    if(contact_home != None):
        for number in contact_home:
            new_contact.phone_number.append(gdata.contacts.PhoneNumber(rel=gdata.contacts.REL_HOME,text=number))

    contact_entry = gd_client.CreateContact(new_contact)
    return contact_entry

#Create groups
def createGroup(group_name):
	global gd_client
	new_group = gdata.contacts.GroupEntry(title=atom.Title(text=group_name))
	group_entry = gd_client.CreateGroup(new_group)
	return group_entry

def addContactToGroup(contact_entry, group_entry):
	global gd_client
	contact_entry.group_membership_info.append(gdata.contacts.GroupMembershipInfo(href=group_entry.id.text)) 
	contact_entry = gd_client.UpdateContact(contact_entry.GetEditLink().href, contact_entry)
	if(contact_entry):
		return True
	else:
		return False

def readLDFFile(file):
	parser = ldif.LDIFRecordList(file)
	parser.parse()
	return parser

def contactHasNumber(contact_entry, number):
    found = False
    for phone_number in contact_entry.phone_number:
        if(number == phone_number.text):
            found = True
    return found

def findGroup(group_name):
	global gd_client
	group_entry = None
	feed = gd_client.GetGroupsFeed()
	for i, entry in enumerate(feed.entry):
		if( group_name == entry.title.text):
			group_entry = entry
			break
	return group_entry

def addNumberToContact(contact_entry,number,rel=gdata.contacts.REL_OTHER):
    if(not contactHasNumber(contact_entry, number)):
        contact_entry.phone_number.append(gdata.contacts.PhoneNumber(rel=rel,text=number))
        contact_entry = gd_client.UpdateContact(contact_entry.GetEditLink().href, contact_entry)
    return contact_entry

def addNumbersToContact(contact_entry,numberList,rel=gdata.contacts.REL_OTHER):
    for number in numberList:
        contact_entry = addNumberToContact(contact_entry,number,rel)
    return contact_entry

def isMember(contact_entry,group_entry):
    isAMember = False
    for group in contact_entry.group_membership_info:
        if(group.href == group_entry.id.text):
            isAMember = True
            break
    return isAMember

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

def transferContacts(parser):
    global skipped_contacts, contacts_skip_count , skipped_groups , groups_skip_count
    try:
        mailLists = []
        for i,item in enumerate(parser.all_records):

            start_time = time.time()
    	    contact_name = None
    	    contact_email = None
    	    contact_mobile = None
    	    contact_home = None
    	    group_name = None
            contact_entry = None
            itemDict = item[1]
            if 'member' in itemDict.keys():
                addLogMessage(localuser.username,"Contact number: " + str(i) + " is a group. Will be added later")
                addLogMessage(localuser.username,"Group cn: " + itemDict['cn'][0])
                mailLists.append(itemDict)
            else:
                if( skipped_contacts < contacts_skip_count):
                    skipped_contacts += 1
                    continue 
                if 'mail' in itemDict.keys():
                	contact_email = itemDict['mail']
                if 'cn' in itemDict.keys():
                 	contact_name = itemDict['cn'][0]
                if 'mobile' in itemDict.keys():
                    contact_mobile = itemDict['mobile']
                if 'telephonenumber' in itemDict.keys():
                	contact_home = itemDict['telephonenumber']
 
                try:
                    addLogMessage(localuser.username,"Creating contact : " + contact_name)
                    contact_entry = createContact(contact_name, contact_email , contact_mobile , contact_home)
                    localuser.contacts_added += 1
                    end_time = time.time()
                    localuser.contacts_upload_time += (end_time - start_time)
                    localuser.save()
                except gdata.service.RequestError, message:
                    addLogMessage(localuser.username,"Contact : " + contact_name + " already exists. Updating info...",'W')
                    try:
                        contact_entry = atom.CreateClassFromXMLString(target_class=gdata.contacts.ContactEntry,xml_string=message[0]['body'])
                        if(contact_mobile != None):
                            addNumbersToContact(contact_entry,contact_mobile,gdata.contacts.REL_OTHER)
                        if(contact_home != None):
                            addNumbersToContact(contact_entry,contact_home,gdata.contacts.REL_OTHER)
                        localuser.contacts_updated += 1
                        end_time = time.time()
                        localuser.contacts_upload_time += (end_time - start_time)
                        localuser.save()
                    except SyntaxError:
   		                pass
                    except Exception,message:
              #      localuser.log += traceback.print_exc(file=sys.stdout)
                        addLogMessage(localuser.username,str(message.message))

        for itemDict in mailLists:
            if( skipped_groups < groups_skip_count):
                skipped_groups += 1
                continue 

            start_time = time.time()
            if 'cn' in itemDict.keys():
                group_name = itemDict['cn'][0]
                group_entry = findGroup(group_name)
                if( group_entry == None):
                    addLogMessage(localuser.username,"Adding group " + group_name)
                    localuser.groups_added += 1
                    end_time = time.time()
                    localuser.contacts_upload_time += (end_time - start_time)
                    localuser.save()
                    group_entry = createGroup(group_name)
                    membersList = itemDict['member']
        
                    for member in membersList:
                        member_name = ''
                        member_email = '' 
                        if 'cn' in member:
                    	    temp = member.split(',')
                            member_name = temp[0]
                            member_name = member_name.replace('cn=','')
                            member_email = temp[1]
                            member_email = member_email.replace('mail=','')
                        else:
                            member_email = member.replace('mail=','')
                            member_name = member_email

                        contact_entry = None
                        try:
                            contact_entry = createContact(member_name, [member_email])
                        except gdata.service.RequestError, message:
                            contact_entry = atom.CreateClassFromXMLString(target_class=gdata.contacts.ContactEntry,xml_string=message[0]['body'])
                        except Exception,message:
                            msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
                            msg = str(message.message) + '\n' + msg
                            addLogMessage(localuser.username,msg,'E')
                        finally:
                            if(contact_entry and  not isMember(contact_entry,group_entry)):
                                addContactToGroup(contact_entry, group_entry)
                else:
                    addLogMessage(localuser.username,"Updating group " + group_name, 'W')
                    localuser.groups_updated += 1
                    end_time = time.time()
                    localuser.contacts_upload_time += (end_time - start_time)
                    localuser.save()
                    
                    membersList = itemDict['member']
        
                    for member in membersList:
                    	temp = member.split(',')
                        member_name = temp[0]
                        member_name = member_name.replace('cn=','')
                        member_email = temp[1]
                        member_email = member_email.replace('mail=','')
                        contact_entry = None
                        try:
                            contact_entry = createContact(member_name, [member_email])
                        except gdata.service.RequestError, message:
                            contact_entry = atom.CreateClassFromXMLString(target_class=gdata.contacts.ContactEntry,xml_string=message[0]['body'])
                        except Exception, message:
                            msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
                            msg = str(message.message) + '\n' + msg
                            addLogMessage(localuser.username,msg,'E')
                        finally:
                            if(contact_entry and not isMember(contact_entry,group_entry)):
                                addContactToGroup(contact_entry, group_entry)

    except Exception, message:
        localuser.state = "failed"
        msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
        msg = str(message.message) + '\n' + msg
        addLogMessage(localuser.username,msg,'E')
        localuser.save()
        if(localuser.retry_number == ocsettings.max_retries_per_user):
            subject = localuser.username + "'s failure"
            msg = localuser.username + " has failed to migrate for "+ str(ocsettings.max_retries_per_user) +" times.\nPlease check the logs."
            util.oc_send_mail(subject, msg, ocsettings.admin_account ,[ocsettings.admin_account])
        sys.exit(1)
        #traceback.print_exc(file=sys.stdout)


def start(user):
    global gd_client, localuser , contacts_skip_count , groups_skip_count
    localuser = user
    
    email = localuser.username + '@' +ocsettings.auc_domain
    email2 = localuser.username + '@' +ocsettings.auc_old_domain
    password = localuser.password

    #Get LDF file name to read from this method is specific to AUC
    filename = getldf(string.lower(email2))
    if(filename != None):
        gd_client = gmailLogin(email,password)
        try:
            file = open(filename,'r')
        except Exception,message:
            localuser.state = "failed"
            msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
            msg = str(message.message) + '\n' + msg
            addLogMessage(localuser.username,msg,'E')
            localuser.save()
            if(localuser.retry_number == ocsettings.max_retries_per_user):
                subject = localuser.username + " couldn't open ldf file"
                msg = localuser.username + " has failed to access his address book\nPlease check the logs."
                util.oc_send_mail(subject, msg, ocsettings.admin_account ,[ocsettings.admin_account])
            sys.exit(1)
            
        parser = ldif.LDIFRecordList(file)
        parser.parse()
        totalNumberOfContacts = len(parser.all_records)
        localuser.contacts_total = totalNumberOfContacts
        contacts_skip_count = localuser.contacts_added + localuser.contacts_updated 
        groups_skip_count = localuser.groups_added + localuser.groups_updated
        localuser.save()
        transferContacts(parser)

