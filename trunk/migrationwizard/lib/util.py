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

from migrationwizard.wizard.models import user_log,Users_info
import migrationwizard.ocsettings as ocsettings
from django.core.mail import send_mail
import socket
import smtplib
from email.MIMEImage import MIMEImage
import email

socket.setdefaulttimeout(ocsettings.socket_default_timeout)

def addLogMessage(username,message,type='I'):
    log = user_log()
    log.username = username
    log.message = message
    log.type = type
    log.save()

def getFolders(server):
    mboxs = server.list()[1]
    folders = []
    first = True
    for box in mboxs:
       temp = box
       if(first):
           sep = temp.split(' ')[1].replace('"','')
           first = False
       temp = temp.split('\"'+sep+'\"')[1].strip().replace('\"','').replace("\'",'')
       folders.append(temp) 
    return folders

def getMessagesInFolder(server,folder):
     try:
         server.select(folder)
         r = server.search(None,"ALL")
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

def getNumberOfEMails(server):
    messages_count = 0
    folders = getFolders(server)
    for folder in folders:
        messages = getMessagesInFolder(server,folder)
        if(messages):
            messages_count += len(messages)
    return messages_count

def estimateTimeRemaining(username):
    user = Users_info.objects.get(username=username)
    if(user.state == "in_progress"):
        contacts_done = user.contacts_added + user.contacts_updated + user.groups_added + user.groups_updated
        contacts_total = user.contacts_total
    
        emails_total_bytes = user.mail_box_size
        emails_done_bytes = user.emails_bytes_uploaded
    
        if(contacts_done != 0):
            single_contact_time = user.contacts_upload_time / float(contacts_done)
        else:
            single_contact_time = 1 / float(4096)
    
        if(emails_done_bytes != 0):
            single_byte_time = user.emails_upload_time / float(emails_done_bytes)
        else:
            single_byte_time = 1 / float(4096)
    
        contacts_estimated_time = ( contacts_total - contacts_done ) * single_contact_time
        emails_estimated_time = ( emails_total_bytes - emails_done_bytes ) * single_byte_time
        estimated_time = contacts_estimated_time + emails_estimated_time
        return estimated_time
    else:
        return 0

def oc_send_mail(subject, feedback, from_email, receipient_list, fail_silently=False, auth_user=ocsettings.smtp_user, auth_password=ocsettings.smtp_password):
    send_mail(subject,feedback,from_email, receipient_list)

def send_sms(mobile,id):

    fromaddr = "<QuescomVirtualFax@Quescom.com>"
    toaddr  = "<gateway@quescom.com>"
    subject = "Migration done"
  
    msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\n\r\n" % (fromaddr, toaddr, subject)
    line = "CallerID=4808 \r\nPASSWORD=user \r\nSMS=%s \r\nYour AUCmail has been upgraded successfully. Please login at http://mail.aucegypt.edu \r\n" % str(mobile)
    msg = msg + line
    server = None
    server_ip = ''
    if(id%2):
        server_ip = ocsettings.primary_sms_server
    else:
        server_ip = ocsettings.secondry_sms_server

    try:
        server = smtplib.SMTP(server_ip)
        server.sendmail(fromaddr, toaddr, msg)
        server.quit()
    except:
        if(id%2):
            server_ip = ocsettings.secondry_sms_server
        else:
            server_ip = ocsettings.primary_sms_server
        server = smtplib.SMTP(server_ip)
        server.sendmail(fromaddr, toaddr, msg)
        server.quit()

def createhtmlmail ( from_header, to_header, subject, html, image=None, text=None):
    """Create a mime-message that will render HTML in popular
    MUAs, text in better ones"""
    import MimeWriter
    import mimetools
    import cStringIO
    
    out = cStringIO.StringIO() # output buffer for our message 
    htmlin = cStringIO.StringIO(html)
    if(text):
        txtin = cStringIO.StringIO(text)
    
    writer = MimeWriter.MimeWriter(out)
    #
    # set up some basic headers... we put subject here
    # because smtplib.sendmail expects it to be in the
    # message body
    #
    writer.addheader("Subject", subject)
    writer.addheader("From", from_header)
    writer.addheader("To", to_header)
    writer.addheader("MIME-Version", "1.0")
    #
    # start the multipart section of the message
    # multipart/alternative seems to work better
    # on some MUAs than multipart/mixed
    #
    writer.startmultipartbody("alternative")
    writer.flushheaders()
    #
    # the plain text section
    #
    if(text):
        subpart = writer.nextpart()
        subpart.addheader("Content-Transfer-Encoding", "quoted-printable")
        pout = subpart.startbody("text/plain", [("charset", 'us-ascii')])
        mimetools.encode(txtin, pout, 'quoted-printable')
        txtin.close()
    #
    # start the html subpart of the message
    #
    subpart = writer.nextpart()
    subpart.addheader("Content-Transfer-Encoding", "quoted-printable")
    #
    # returns us a file-ish object we can write to
    #
    pout = subpart.startbody("text/html", [("charset", 'us-ascii')])
    mimetools.encode(htmlin, pout, 'quoted-printable')
    htmlin.close()
    #
    # Now that we're done, close our writer and
    # return the message body
    #
    writer.lastpart()
    msg = out.getvalue()
    out.close()
    
    if(image):
      fp = open(image, 'rb')
      msgImage = MIMEImage(fp.read())
      fp.close()
      # Define the image's ID as referenced above
      email_msg = email.message_from_string(str(msg)) 
      msgImage.add_header('Content-ID', '<pop_imap>')
      email_msg.attach(msgImage)
      msg = email_msg.as_string()

    return msg

forwarding_html = """
<b class="sub-title">E-mail forwarding:</b>
<p class="normal-text">The following e-mail accounts were forwarded on the old e-mail system:</p>
<UL>
{{forwards}}
</UL>

<p class="normal-text"> If you want to keep these accounts  forwarded,you will need to create the settings for them on the new platform. To do so, please follow the instructions in the link below</p>

{{help_forward}}

"""

helper_forward_html_single = """<p class="normal-text"><FONT COLOR="#000080"><U><A HREF="http://mail-upgrade.aucegypt.edu/help/set_forwards.htm"><I><B>http://mail-upgrade.aucegypt.edu/help/set_forwards.htm</B></I></A></U></FONT></p>"""

helper_forward_html_multiple = """<p class="normal-text"><FONT COLOR="#000080"><U><A HREF="http://mail-upgrade.aucegypt.edu/help/set_forwards_using_filters.htm"><I><B>http://mail-upgrade.aucegypt.edu/help/set_forwards_using_filters.htm</B></I></A></U></FONT></p>"""

forward_address_html = """<LI><p class="normal-text"><FONT COLOR="#000080"><U><A HREF="mailto:{{mail}}"><B>{{mail}}</B></A></U></FONT></p>"""

def welcome_mail(subject, from_email, username, fullname):
    welcome_file = open(ocsettings.project_path + '/emails/welcome.html','r')
    msg = welcome_file.read()
    msg = msg.replace('{{username}}',fullname)
    from_header = 'AUCmail Admin <' + from_email + '>'
    to_header = username+'@g.'+ocsettings.auc_domain
    msg = createhtmlmail(from_header, to_header, subject, msg)
    
    server = smtplib.SMTP(ocsettings.auc_smtp)
    server.login(ocsettings.smtp_user, ocsettings.smtp_password)
    server.sendmail(from_email, username+'@g.'+ocsettings.auc_domain , str(msg))
    server.quit()

def technotes_mail(subject,  addresses, from_email, username, fullname):
    global forwarding_html
    forward_local = forwarding_html
    technical_notes = open(ocsettings.project_path + '/emails/technotes.html' , 'r')
    msg = technical_notes.read()
    msg = msg.replace('{{username}}' , fullname)

    addresses_html = ''
    for add in addresses:
        addresses_html += forward_address_html.replace('{{mail}}',add)
    forward_local = forward_local.replace('{{forwards}}',addresses_html)
    if(len(addresses) > 1):
        forward_local = forward_local.replace('{{help_forward}}',helper_forward_html_multiple)
    else:
        forward_local = forward_local.replace('{{help_forward}}',helper_forward_html_single)
    
    if(len(addresses) > 0):
        msg = msg.replace('{{forward_handling}}',forward_local)
    else:
        msg = msg.replace('{{forward_handling}}','')

    from_header = 'AUCmail Admin <' + from_email + '>'
    to_header = username+'@g.'+ocsettings.auc_domain
    msg = createhtmlmail(from_header, to_header, subject, msg, ocsettings.project_path + '/emails/pop_imap.png')
    server = smtplib.SMTP(ocsettings.auc_smtp)
    server.login(ocsettings.smtp_user, ocsettings.smtp_password)
    server.sendmail(from_email, username+'@g.'+ocsettings.auc_domain , str(msg))
    server.quit()

    # Also append this email to the old auc mail acount
    try:
        import imaplib
        user = Users_info.objects.get(username=username)
        imap_server = imaplib.IMAP4_SSL(ocsettings.auc_imap)
        imap_server.login(user.username, user.password)
        imap_server.select()
        imap_server.append(mailbox='Inbox',message=msg,flags=None,date_time=None)
    except Exception, m:
        addLogMessage("Couldn't append technotes mail to old auc mail inbox",'W')
        addLogMessage(m.message,'W')

