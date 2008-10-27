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

#This is the admin for Google domain. Written in the format admin@googledomain.com
admin_auc_gmail_email = ''
admin_auc_gmail_password = ''

#The domain name written in the format googledomain.com
auc_domain = ''
#The same as the above but 2 different domains were used for development and deployment
auc_old_domain = ''

#Old AUC imap server
auc_imap = ''
#AUC LDAP server
ldap_server =  ''

#MySQL Username and password
db_user = ''
db_password = ''

gmail_mailbox_size = 7.0

#The directory on the server on which large attachments are stored
attachment_path_on_server = ''
#URL to access the attachment storage space
attachment_server_url = ''

#Project directory path on the server
project_path = ''

#Number of parallel migrations
max_workers = 20

#Google does accept for emails largers 20MB this variable is used to check for this size limit
max_attachment_size = 20000000

#Number of automatic retries. If the user fails to migrate for a value > max_retries_per_user
#the migration stops and an email is sent to the administrator.
max_retries_per_user = 15

socket_default_timeout = 90

#Used in the administration pages
no_users_per_page = 20


gmail_forword_domain = ''

#Used to send emails to the user
smtp_user = ''
smtp_password = ''

#smptp server to send mail with
auc_smtp = ''
smtp_port = 25
#Account feedback is sent to
feedback_account = ''
#Admin account where emails like welcome email and technical notes are sent from 
admin_account = ''

"""
Used to send sms to the user after successful migration.
The primary sms server is used with users having odd ID while the secondary is used 
with users having even ID to balance the load.
"""
primary_sms_server = ''
secondry_sms_server = ''

"""
The path to the gethash utility. This utility is very specific to AUC
It's used to find ldf file for a specific user

"""
commandpath = "" 
lookpath = ""

