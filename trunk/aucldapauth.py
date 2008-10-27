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

from migrationwizard import ocsettings
from mod_python import apache
import os,os.path,sys,getpass,ldap

def authenhandler(req):
    """
      Handles the authentication for the attachment storage space. Currently the authentication
      is specific for AUC LDAP server
    """
    reqdir = os.path.dirname(req.uri)
    reqfile = os.path.basename(req.uri)
    reqdir = reqdir.replace("/aucldapprotected/","")
    pw = req.get_basic_auth_pw()
    user = req.user
    if reqdir == "/aucldapprotected" :
    	return apache.HTTP_FORBIDDEN	
    if reqdir != user :
    	return apache.HTTP_UNAUTHORIZED
    l = ldap.open(ocsettings.ldap_server)
    login_dn = "mailRoutingAddress=%s@aucegypt.edu,ou=People,dc=aucegypt,dc=edu"% user
    try :
    	l.simple_bind_s(login_dn, pw)
    except ldap.INVALID_CREDENTIALS, message:
     	return apache.HTTP_UNAUTHORIZED
    status = handler(req)
    if status == "Success":
      return apache.DONE
    else:
      return apache.HTTP_NOT_FOUND

def handler(req):
    reqfile = os.path.basename(req.uri)
    user = req.user
    fullpath = ocsettings.attachment_path_on_server+"/"+user+"/"+reqfile
    if os.path.exists(fullpath):
        req.headers_out["Content-type"] = "application/force-download"
        req.headers_out["Content-Disposition"] = "attachment; filename=%s" % reqfile
        f = open(fullpath)
        req.write(f.read())
        f.close()
        return "Success"
    else:
        return "404"

