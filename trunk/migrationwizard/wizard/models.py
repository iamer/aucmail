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

from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Users_info(models.Model):
    # User identification fields
    id = models.OneToOneField(User)
    username = models.CharField(maxlength=50)
    givenname = models.CharField(maxlength=50,default='')
    sn = models.CharField(maxlength=50,default='')
    password = models.CharField(maxlength=50)

    mobile = models.CharField(maxlength=50)

    # Verbose log and migration state
    state = models.CharField(maxlength=15,default='not_started')

    #Failure retry
    retry_number = models.IntegerField(default=0)

    # Contacts progress info fields
    contacts_added = models.IntegerField(default=0)
    contacts_updated = models.IntegerField(default=0)
    groups_added = models.IntegerField(default=0)
    groups_updated = models.IntegerField(default=0)
    contacts_total = models.IntegerField(default=0)

    # Mail migration progress fields
    mails_uploaded = models.IntegerField(default=0)
    mails_total = models.IntegerField(default=0)
    offending_mails_count = models.IntegerField(default=0)

    # Other user info
    nicknames = models.TextField(default='')
    migration_start_time = models.DateTimeField(null=True)
    migration_end_time = models.DateTimeField(null=True)

    mail_box_size = models.IntegerField(default=0)
    emails_bytes_uploaded = models.IntegerField(default=0)
    contacts_upload_time = models.IntegerField(default=0)
    emails_upload_time = models.IntegerField(default=0)

    mail_fwd_address = models.CharField(maxlength=255)

    feedback = models.TextField(default='')

    process_pid = models.IntegerField(default=-1)

class user_log(models.Model):
    username = models.CharField(maxlength=50)
    time_stamp = models.DateTimeField(auto_now=True)
    message = models.TextField(default='')
    type = models.TextField(default='I')

