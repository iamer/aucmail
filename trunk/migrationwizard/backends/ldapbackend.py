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

from django.contrib.auth.models import User
import ldap
import migrationwizard.ocsettings as ocsettings
from migrationwizard.wizard.models import Users_info
from migrationwizard.lib.util import addLogMessage
import gdata
import gdata.apps
import gdata.apps.service
import sys,string,traceback

class UpdateUserData():
    """
       Used to update/create user data on Google's domain
    """
    service = None
    entry = None
    username = None
    family_name = None
    given_name = None

    def __init__(self,username,family_name=None,given_name=None):
        self.username = username
        self.family_name = family_name
        self.given_name = given_name
        self.service = self.connectToService()
        self.entry = self.retreiveOrCreateUser()

    def connectToService(self):
        try:
            service = gdata.apps.service.AppsService(email=ocsettings.admin_auc_gmail_email, domain=ocsettings.auc_domain, password=ocsettings.admin_auc_gmail_password)
            service.ProgrammaticLogin()
            return service
        except gdata.apps.service.AppsForYourDomainException, m:
            msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
            msg = str(m.message) + '\n' + msg
            msg = str(m.reason) + '\n' + msg
            addLogMessage(self.username,msg,'E')
            return None
        except Exception, m:
            msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
            msg = str(m.message) + '\n' + msg
            addLogMessage(self.username,msg,'E')
            return None
    
    def retreiveOrCreateUser(self):
        entry = None
        try:  
            entry = self.service.RetrieveUser(self.username)
        except gdata.apps.service.AppsForYourDomainException, m:
            if str(m.reason) == "EntityDoesNotExist":
                try:
                    if(self.given_name and self.family_name):
                        entry = self.service.CreateUser(self.username,self.family_name,self.given_name,'@#$%^&*123456abcd')
                    else:
                        entry = self.service.CreateUser(self.username,self.username,self.username,' @#$%^&*123456abcd')
                    return entry
                except gdata.apps.service.AppsForYourDomainException, m:
                    msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
                    msg = str(m.message) + '\n' + msg
                    msg = str(m.reason) + '\n' + msg
                    addLogMessage(self.username,msg,'E')
                    return None
                except Exception, m:
                    msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
                    msg = str(m.message) + '\n' + msg
                    addLogMessage(self.username,msg,'E')
                    return None
            else:
                msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
                msg = str(m.message) + '\n' + msg
                msg = str(m.reason) + '\n' + msg
                addLogMessage(self.username,msg,'E')
                return None

        except Exception, m:
            msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
            msg = str(m.message) + '\n' + msg
            addLogMessage(self.username,msg,'E')
            return None

        try:
            self.setGivenAndLastName()
        except Exception, m:
            msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
            msg = str(m.message) + '\n' + msg
            msg = 'Failed to set givenname and lastname. \n' + msg
            addLogMessage(self.username,msg,'W')
        return entry
     
    def syncPassword(self,password):
        if(not self.service):
            return False
     
        if(not self.entry):
             return False
        try:
            self.entry.login.password = password
    
            self.service.UpdateUser(self.username,self.entry)
        except Exception,m:
            msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
            msg = str(m.message) + '\n' + msg
            addLogMessage(self.username,msg,'E')
            return False
        return True
    
    def createNickNames(self,mailLocalAddress):
         if(not self.service):
            return False
    
         try:
            for mail in mailLocalAddress:
                nickname = mail.split('@')[0]
                if nickname != self.username:
                    self.service.CreateNickname(self.username, nickname)
         except Exception,m:
             msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
             msg = str(m.message) + '\n' + msg
             addLogMessage(self.username,msg,'E')
             return False
         return True
    
    def setGivenAndLastName(self):
        if(not self.service):
            return False
     
        if(not self.entry):
             return False
        try:
            self.entry.name.family_name = self.family_name
            self.entry.name.given_name = self.given_name
    
            self.service.UpdateUser(self.username,self.entry)
        except Exception,m:
            msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
            msg = str(m.message) + '\n' + msg
            addLogMessage(self.username,msg,'E')
            return False
        return True

    def addForwards(self,list,user):
        str = ''
        first = True
        for mail in list:
            if(first):
                str += mail 
                first = False
            else:
                str += ',' + mail
        user.mail_fwd_address = str
        user.save()

class LDAPBackend:
    """
      Authentication backend. It authenticates against AUC LDAP server
    """
    def authenticate(self, username=None, password=None):
        if( username == '' or password == ''):
            return None
        elif(username == 'admin@'+ocsettings.auc_old_domain):
            username = username.replace("@"+ocsettings.auc_old_domain,'')
            from django.contrib.auth.backends import ModelBackend
            backend = ModelBackend()
            return backend.authenticate(username,password)
        try:
            con = ldap.initialize('ldap://'+ ocsettings.ldap_server) 
            con.protocol_version = ldap.VERSION3
            udn = 'mailRoutingAddress=%s,ou=People,dc=aucegypt,dc=edu' % username
            con.simple_bind_s(udn,password)
            update_user_object = None
            res = con.search_s(udn,ldap.SCOPE_BASE,'(objectclass=*)',['*','+'])
            family_name = res[0][1]['sn'][0]
            given_name = res[0][1]['givenName'][0]
            username = username.replace("@"+ocsettings.auc_old_domain,'')
            try:
                update_user_object = UpdateUserData(username,family_name,given_name)
                user = User.objects.get(username__exact=username)
                user.set_password(password)
                user.save()

                user2 = None
                try:
                    user2 = Users_info.objects.get(username=username)
                except Users_info.DoesNotExist:
                    user2  = Users_info()
                    user2.username = username
                    user2.id_id = user.id
                    
                user2.password = password
                user2.givenname = given_name
                user2.sn = family_name
                user2.save()
                try:
                    if( not update_user_object.syncPassword(password)):
                        return None
                except gdata.apps.service.AppsForYourDomainException, m:
                    msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
                    msg = str(m.message) + '\n' + msg
                    msg = str(m.reason) + '\n' + msg
                    addLogMessage(user2.username,msg,'E')
                    return None
            except:
                user = User.objects.create_user(username,'',password)
                user.is_active = True
                user.set_password(password)
                user.save()

                user2  = Users_info()
                user2.username = username
                user2.password = password
                user2.givenname = given_name
                user2.sn = family_name
                user2.id_id = user.id

                user2.save()
                
                try:
                    if( not update_user_object.syncPassword(password)):
                        return None
                except gdata.apps.service.AppsForYourDomainException, m:
                    msg = string.join(traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1],sys.exc_info()[2]), "")
                    msg = str(m.message) + '\n' + msg
                    msg = str(m.reason) + '\n' + msg
                    addLogMessage(user2.username,msg,'E')
                    return None

                try:
                    update_user_object.createNickNames(res[0][1]['mailLocalAddress'])
                except Exception, m:
                    msg = "User does not have any aliases"
                    addLogMessage(username,msg,'W')

                try:
                    update_user_object.addForwards(res[0][1]['messageForwardingAddress'],user2)
                except Exception, m:
                    msg = "User does not have any forwarding addresses"
                    addLogMessage(username,msg,'W')
        except:
            return None
        
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

