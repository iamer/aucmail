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

import ldap
from util import addLogMessage
import migrationwizard.ocsettings as ocsettings

def ldapConnection(user_object):
    username = user_object.username+"@"+ocsettings.auc_old_domain
    password = user_object.password
    con = ldap.initialize('ldap://'+ ocsettings.ldap_server) 
    con.protocol_version = ldap.VERSION3
    udn = 'mailRoutingAddress=%s,ou=People,dc=aucegypt,dc=edu' % username
    con.simple_bind_s(udn,password)
    return con,udn

def setInitialForwordAttribute(user_object):
    l,login_dn = ldapConnection(user_object)
    addresses = user_object.mail_fwd_address.split(',')
    fwd = user_object.username+'@'+ocsettings.gmail_forword_domain
    if fwd not in addresses:
        mod_attrs = [( ldap.MOD_ADD, 'messageForwardingAddress', fwd )]
	try:
            l.modify_s(login_dn, mod_attrs)
	except ldap.TYPE_OR_VALUE_EXISTS:
	    addresses.append(fwd)
	    if '' in addresses:
	        addresses.remove('')
   	    user_object.mail_fwd_address = ",".join(addresses)
	    user_object.save()
    else:
        addLogMessage(user_object.username, fwd + ' is already in the forwarding list' , 'W')

def unsetInitialForwordAttribute(user_object):
    l,login_dn = ldapConnection(user_object)
    addresses = user_object.mail_fwd_address.split(',')
    fwd = user_object.username+'@'+ocsettings.gmail_forword_domain
    mod_attrs = [( ldap.MOD_DELETE, 'messageForwardingAddress', fwd )]
    try:
        l.modify_s(login_dn, mod_attrs)
    except ldap.NO_SUCH_ATTRIBUTE:
        pass
    
    if fwd in addresses:
        addresses.remove(fwd)
    user_object.mail_fwd_address = ",".join(addresses)
    user_object.save()

def unsetLocalStoreAttribute(user_object):
    l,login_dn = ldapConnection(user_object)
    mod_attrs = [( ldap.MOD_REPLACE, 'messageLocalDeliveryOption', 'FALSE' )]
    l.modify_s(login_dn, mod_attrs)

def setOnlyGmailForwordAttribute(user_object):
    l,login_dn = ldapConnection(user_object)
    try:
        mod_attrs = [( ldap.MOD_DELETE, 'messageForwardingAddress', None )]
        l.modify_s(login_dn, mod_attrs)
    except ldap.NO_SUCH_ATTRIBUTE:
        pass

    mod_attrs = [( ldap.MOD_ADD, 'messageForwardingAddress', user_object.username+'@'+ocsettings.gmail_forword_domain )]
    l.modify_s(login_dn, mod_attrs)

