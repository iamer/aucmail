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

# Crqeate your views here.

from django import newforms as forms
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login , logout
from django.contrib.auth.forms import AuthenticationForm
from django import newforms as forms
from django.db import connection

import sanitychecks
import migrationwizard.ocsettings as ocsettings
from migrationwizard.wizard.models import Users_info, user_log
import migrationwizard.lib.util as util
from django.core.paginator import ObjectPaginator, InvalidPage
from migrationwizard.lib.ldap_attribs import *
from datetime import datetime, timedelta
from subprocess import call,Popen,PIPE

def signin(request):
    f = AuthenticationForm(request)
    try:
        id = request.session['member_id']
        return gotoState(request)
    except Exception, m:
        if request.method == "POST":
            username = ""
            password = ""
            if "username" in request.POST:
                username = request.POST["username"]
            if "password" in request.POST:
                password = request.POST["password"]
            username = username.replace('@aucegypt.edu','') 
            user = authenticate(username=username+"@"+ocsettings.auc_old_domain, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
    
                    request.session['member_id'] = user.id
                    if(username == 'admin'):
                        return HttpResponseRedirect('/wizard/admin/list/1/')
                    else:
                        return gotoState(request)             
            else:
               return render_to_response('login.html', {"form" : f , "message" : "* Please enter a correct username and password. Note that both fields are case-sensitive. Make sure that your password is at least 6 characters."})
    
        return render_to_response('login.html', { "form" : f} )

def gotoState(request):
    user = Users_info.objects.get(username__exact=request.user.username )
    if(user.state == 'not_started'):
        return notStartedView(request)
    elif(user.state == 'in_checks'):
        return checksView(request)
    elif(user.state == 'in_queue'):
        return inProgressView(request)
    elif(user.state == 'in_progress'):
        return inProgressView(request)
    elif(user.state == 'done'):
        return doneView(request)
    elif(user.state == 'fresh'):
        return doneView(request)
    else:
        return failedView(request)


def userWillMigrate(request):
    user = Users_info.objects.get(username=request.user.username )
    if(user.state == 'not_started'):
        user.state = 'in_checks'
        user.save()
    return gotoState(request)

def userWillStartFresh(request):
    user = Users_info.objects.get(username__exact=request.user.username )
    if(user.state == 'not_started'):
        user.state = 'fresh'
        user.save()
        unsetLocalStoreAttribute(user)
        setOnlyGmailForwordAttribute(user)
    return gotoState(request)

def checksView(request):
    user = Users_info.objects.get(username__exact=request.user.username )
    (count, size, captcha) = sanityChecks(user.username, user.password)
    return render_to_response('preparation.html', {   "large_attachments" : count , "large_mailbox" : size , "username" : request.user.username , "captcha" : captcha} )

def notStartedView(request):
    return render_to_response('choice.html', { "username" : request.user.username } )

def inProgressView(request):
    try:
        user = Users_info.objects.get(username__exact=request.user.username )
        if(user.state == 'in_progress' or user.state == 'in_queue'):
            return render_to_response('progress.html' , { "username" : request.user.username } ) 
        else:
            return HttpResponseRedirect('/wizard/')
    except:
        return HttpResponseRedirect('/wizard/')

def startMigration(request):
    user = Users_info.objects.get(username__exact=request.user.username )
    if(user.state == 'in_checks' ):
        user.state = 'in_queue'
        user.save()
    return HttpResponseRedirect('/wizard/progress/')

def doneView(request):
    return render_to_response('done.html', { "username" : request.user.username } )

def failedView(request):
    return render_to_response('progress.html' , { "username" : request.user.username } ) 


def sanityChecks(username, password):
    user = Users_info.objects.get(username__exact=username )
    auc_server = None

    login_ret_val = sanitychecks.imaplogin(ocsettings.auc_imap, username, password)

    if(login_ret_val[0] == 'OK'):
        auc_server = login_ret_val[1]
#    else:# This should be put in the logs, failure to login to AUC server through imap
#        print "Failure to login to AUC server through imap for user " + username

    # Email attachments size problem
    size = ocsettings.max_attachment_size
    message_count = sanitychecks.getNumberOfMailsLargerThan(auc_server, size)

    large_mailbox = False
    totalSize = sanitychecks.getMailBoxSize(auc_server)
    user.mail_box_size = totalSize 
    user.save()
    if(totalSize > ocsettings.gmail_mailbox_size * 1024 * 1024 * 1024):
        large_mailbox = True

    sanitychecks.imaplogout(auc_server)

    captcha = sanitychecks.captchaUnlockNeeded(username+'@'+ocsettings.auc_domain, user.password)
    return (message_count, large_mailbox, captcha)

def logout_view(request):
    try:
        logout(request)
        del request.session['member_id']
    except:
        pass
    return HttpResponseRedirect('/wizard')

def migration(request):
    if(request.user.is_authenticated()):
        return render_to_response('base.html' , {} )
    else:
        return HttpResponseRedirect('/wizard')

def resurrectDeadProcesses(request):
    inprogess_users = Users_info.objects.filter(state__exact="in_progress")
    for user in inprogess_users:
        p1 = Popen(["ps","aux"], stdout=PIPE)
        p1.wait()
        p2 = Popen(["grep", user.username ], stdin=p1.stdout, stdout=PIPE)
        p2.wait()
        p3 = call(["grep", str(user.process_pid) ], stdin=p2.stdout, stdout=PIPE)
        if(p3 == 1):
            user.state = 'failed'
            user.save()

    users = Users_info.objects.filter(state__exact="failed")
    for user in users:
        if(user.retry_number < ocsettings.max_retries_per_user):
            user.retry_number += 1
            user.process_pid = -1
            user.state = 'in_queue'
            user.save()

def addToQueue(request):
    resurrectDeadProcesses(request)
    progress_count = 0
    users = Users_info.objects.filter(state='in_progress')
    if(users):
        progress_count = len(users)

    users_info = Users_info.objects.filter(state='in_queue')
    import subprocess
    for user in users_info:
        if(progress_count < ocsettings.max_workers):
            username = user.username
            subprocess.call(["python" , ocsettings.project_path+"/runprocess.py" , username])
    #        user.state = 'in_progress'
    #        user.save()
            progress_count += 1
        else:
            break

    return HttpResponse('')
    
def getUpdate(request, last_datetime):
    sep = ":::::"
    if(last_datetime != 'None'):
        last_datetime = last_datetime.replace('_',' ')
    user = Users_info.objects.get(username__exact=request.user.username)
    contacts_currently_done = user.contacts_added + user.contacts_updated + user.groups_added + user.groups_updated
    total_contacts = user.contacts_total
    
    mails_currently_done = user.mails_uploaded
    mail_total = user.mails_total

    temp_datetime = datetime.now()
    
    all_log_entries = user_log.objects.filter(username=request.user.username, time_stamp__lte=temp_datetime)
    all_log_entries = all_log_entries.exclude(type='E')

    current_logs = None
    if(last_datetime and last_datetime != 'None'):
        current_logs = all_log_entries.exclude(time_stamp__lte=last_datetime)
    else:
        current_logs = all_log_entries

    logs = ''
    for entry in current_logs:
        logs += entry.message + '<br>'
    
    progress = 0
    if(( total_contacts + mail_total ) != 0):
        progress = ( contacts_currently_done + mails_currently_done )  * 100 / ( total_contacts + mail_total )
    elif( (( total_contacts + mail_total ) == 0 ) and user.state == 'in_progress'):
        progress = 100


    if(user.state == 'done'):
        return HttpResponse('done')

    temp_datetime = str(temp_datetime)
    temp_datetime = temp_datetime.replace(' ','_')

    est = int(util.estimateTimeRemaining(user.username ))
    d = timedelta(0, est)
    
    if(logs):
        logs = logs.replace(sep,'')

    return HttpResponse(str(progress)+sep
        +logs+sep+temp_datetime
        +sep+str(contacts_currently_done)
        +sep+str(total_contacts)
        +sep+str(mails_currently_done)
        +sep+str(mail_total)
        +sep+user.state
        +sep+str(d)
        +sep+str(user.retry_number)
        +sep+str(ocsettings.max_retries_per_user)
       )

def html_pages_link(page_number, users_name, last_page, view_name):
    html = ''
    page_number = int(page_number)
    start_page = max(1,page_number-4)
    if (last_page == 1):
      html = ''
    else:
      if (users_name == 'null'):
        if (start_page > 1):
          html += " <a id='paginator' href=/wizard/admin/"+view_name+"/1/> < first </a> "
          html += " <a id='paginator' href=/wizard/admin/"+view_name+"/"+str(page_number-1)+"/> << previous </a> "

        end_page = min(start_page + 8 , last_page)
        for i in range(start_page,end_page+1):
          if (i == page_number):
            html += str(i)
          else:
            html += " <a id='paginator' href=/wizard/admin/"+view_name+"/"+ str(i) +"/>" + str(i) +"</a> "
      
        if (end_page < last_page):
          html += " <a id='paginator' href=/wizard/admin/"+view_name+"/"+str(page_number+1)+"/> next >  </a> "
          html += " <a id='paginator' href=/wizard/admin/"+view_name+"/"+str(last_page)+"/> last >> </a> "
      else:
        if (start_page > 1):
          html += " <a id='paginator' href=/wizard/admin/"+view_name+"/1/"+users_name+"> < first </a> "
          html += " <a id='paginator' href=/wizard/admin/"+view_name+"/"+str(page_number-1)+"/"+users_name+"> << previous </a> "

        end_page = min(start_page + 8 , last_page)
        for i in range(start_page,end_page+1):
          if (i == page_number):
            html += str(i)
          else:
            html += " <a id='paginator' href=/wizard/admin/"+view_name+"/"+ str(i) +"/"+ users_name +" >" + str(i) +"</a> "
        
        if (end_page < last_page):
          html += " <a id='paginator' href=/wizard/admin/"+view_name+"/"+str(page_number+1)+"/"+users_name+"> next > </a> "
          html += " &nbsp;<a id='paginator' href=/wizard/admin/"+view_name+"/"+str(last_page)+"/"+users_name+"> last >> </a> "
    
    return html


def search_user(request, page_number=None, search_name=None):
    try:
        if(request.user.username == 'admin' ):
           view_name = "Search"
           if( request.method == "POST"):
              user_name =  request.POST
              searched_user = Users_info.objects.filter(username__icontains = user_name['search_item'])
              user_count = len(searched_user)
              paginator = ObjectPaginator(searched_user, ocsettings.no_users_per_page)
              user_list = paginator.get_page(int(page_number)-1)
              html = html_pages_link(page_number, user_name['search_item'], paginator.pages, "search") 
              return render_to_response('search.html',{ "all_users_name" : user_list,"link": html,"report_title" : view_name, "user_count" : user_count } )
           else:
              searched_user = Users_info.objects.filter(username__icontains = search_name)
              user_count = len(searched_user)
              paginator = ObjectPaginator(searched_user, ocsettings.no_users_per_page)
              html = html_pages_link(page_number, search_name, paginator.pages, "search")
              user_list = paginator.get_page(int(page_number)-1)
              return render_to_response('search.html',{ "all_users_name" : user_list,"link": html , "report_title" : view_name, "user_count" : user_count} )
        else:
            return HttpResponseRedirect('/wizard/')

    except Exception,obj:
      return HttpResponse('')

def fwd_add(request, page_number):
    try:
        if(request.user.username == 'admin' ):
            all_users = Users_info.objects.all()
            fwd_user_add = all_users.exclude(mail_fwd_address = '')
            user_count = len(fwd_user_add)
            paginator = ObjectPaginator(fwd_user_add, ocsettings.no_users_per_page)
            html = html_pages_link(page_number, 'null', paginator.pages, 'fwd_add')
            user_list = paginator.get_page(int(page_number)-1)
            view_name = "Fwd address"
            return render_to_response('view_filter.html',{ "all_users_name" : user_list, "link": html, "fwd_add":"true", "report_title" : view_name, "user_count" : user_count } )
        else:
            return HttpResponseRedirect('/wizard/')
    except:
      return HttpResponse('')

def done_state(request, page_number):
    try:
        if(request.user.username == 'admin' ):
            done_user_state = Users_info.objects.filter(state = 'done')
            paginator = ObjectPaginator(done_user_state, ocsettings.no_users_per_page)
            html = html_pages_link(page_number, 'null', paginator.pages, 'done_state')
            user_list = paginator.get_page(int(page_number)-1)
            user_count = len(done_user_state)
            view_name = "Done"
            return render_to_response('view_filter.html',{ "all_users_name" : user_list,"link": html, "report_title" : view_name, "user_count" : user_count })
        else:
            return HttpResponseRedirect('/wizard/')
    except:
      return HttpResponse('')

def failed_state(request, page_number, filter_type):
    try:
        if(request.user.username == 'admin' ):
          view_name = "Failed"
          view_name_state = ''
          shown_user = ''
          links = ''
          arg_name = ''
          get_method_state = ''
          user_count = ''
          if (request.method == 'POST'):
            filter_state = request.POST['filter-fail']
            failed_user_state_max = Users_info.objects.filter(state = 'failed',retry_number=ocsettings.max_retries_per_user)
            failed_user_state = Users_info.objects.filter(state = 'failed')
            paginator_max = ObjectPaginator(failed_user_state_max, ocsettings.no_users_per_page)
            paginator = ObjectPaginator(failed_user_state, ocsettings.no_users_per_page)
            html_max = html_pages_link(page_number, 'max_user', paginator_max.pages, 'failed_state')
            html = html_pages_link(page_number, 'all_user', paginator.pages, 'failed_state')
            user_list_max = paginator_max.get_page(int(page_number)-1)
            user_list = paginator.get_page(int(page_number)-1)
            if (filter_state == 'all-user'):
              shown_user = user_list
              user_count = len(failed_user_state)
              view_name_state = 'All users'
              links = html
              arg_name = 'all_user'
            elif (filter_state == 'max-retry-user'):
              shown_user = user_list_max
              user_count = len(failed_user_state_max)
              view_name_state = 'Max retry users'
              links = html_max
              arg_name = 'max_user'
            return render_to_response('fail.html',{ "all_users_name" : shown_user, "link": links, "report_title" : view_name, "args" : arg_name, "report_state" : view_name_state, "user_count" : user_count})
          else:
            user_list_max = ''

            failed_user_state_max = Users_info.objects.filter(state = 'failed',retry_number=ocsettings.max_retries_per_user)
            failed_user_state = Users_info.objects.filter(state = 'failed')
            paginator_max = ObjectPaginator(failed_user_state_max, ocsettings.no_users_per_page)
            paginator = ObjectPaginator(failed_user_state, ocsettings.no_users_per_page)
            html_max = html_pages_link(page_number, 'max_user', paginator_max.pages, 'failed_state')
            html = html_pages_link(page_number, 'all_user', paginator.pages, 'failed_state')
            if (filter_type == 'all_user' or filter_type == ''):
              shown_user = paginator.get_page(int(page_number)-1)
              user_count = len(failed_user_state)
              links = html
              view_name_state = 'All users'
            elif (filter_type == 'max_user'):
              user_count = len(failed_user_state_max)
              view_name_state = 'Max retry users'
              shown_user = paginator_max.get_page(int(page_number)-1)
              links = html_max
            return render_to_response('fail.html',{ "all_users_name" : shown_user, "link": links, "report_title" : view_name, "report_state" : view_name_state, "user_count" : user_count} )
        else:
            return HttpResponseRedirect('/wizard/')
    except:
      return HttpResponse('')

def not_started_state(request, page_number):
    try:
        if(request.user.username == 'admin' ):
            not_started_user_state = Users_info.objects.filter(state = 'not_started')
            user_count = len(not_started_user_state)
            paginator = ObjectPaginator(not_started_user_state, ocsettings.no_users_per_page)
            html = html_pages_link(page_number, 'null', paginator.pages, 'notstarted')
            user_list = paginator.get_page(int(page_number)-1)
            view_name = "Not started"
            return render_to_response('view_filter.html',{ "all_users_name" : user_list,"link": html ,"report_title":view_name, "user_count" : user_count} )
        else:
            return HttpResponseRedirect('/wizard/')
    except:
      return HttpResponse('')

def in_queue_state(request, page_number):
    try:
        if(request.user.username == 'admin' ):
            in_queue_user_state = Users_info.objects.filter(state = 'in_queue')
            user_count = len(in_queue_user_state)
            paginator = ObjectPaginator(in_queue_user_state, ocsettings.no_users_per_page)
            html = html_pages_link(page_number, 'null', paginator.pages, 'inqueue')
            user_list = paginator.get_page(int(page_number)-1)
            view_name = "In queue"
            return render_to_response('view_filter.html',{ "all_users_name" : user_list,"link": html, "report_title" : view_name, "user_count" : user_count } )
        else:
            return HttpResponseRedirect('/wizard/')
    except:
      return HttpResponse('')

def in_progress_state(request, page_number):
    try:
        if(request.user.username == 'admin' ):
            in_progress_user_state = Users_info.objects.filter(state = 'in_progress')
            user_count = len(in_progress_user_state)
            paginator = ObjectPaginator(in_progress_user_state, ocsettings.no_users_per_page)
            html = html_pages_link(page_number, 'null', paginator.pages, 'inprogress')
            user_list = paginator.get_page(int(page_number)-1)
            view_name = "In progress"
            return render_to_response('view_filter.html',{ "all_users_name" : user_list, "link": html, "report_title" : view_name , "user_count" : user_count} )
        else:
            return HttpResponseRedirect('/wizard/')
    except:
      return HttpResponse('')

def list_all(request, page_number=None):
    try:
        if(request.user.username == 'admin' ):
            if( request.method == "POST"):
               user_name =  request.POST
               users_list = []
               for i in  user_name:
                   users_list.append(i)
               return render_to_response('list_all.html',{ "all_users_name" : users_list }  )
            else:
               users_list = Users_info.objects.all()
               user_count = len(users_list)
               paginator = ObjectPaginator(users_list, ocsettings.no_users_per_page)
               html = html_pages_link(page_number, 'null', paginator.pages, 'list')
               if (page_number == '1'):
                 user_list = paginator.get_page(0)
               else:
                 user_list = paginator.get_page(int(page_number)-1)
               view_name = "All users"
               return render_to_response('list_all.html',{ "all_users_name" : user_list , "link": html, "report_title" : view_name, "user_count" : user_count} )
        else:
            return HttpResponseRedirect('/wizard/')
    except:
        return HttpResponse('')

def change_state(request):
    try:
        if(request.user.username == 'admin' ):
            if (request.method == "POST"):
               post = request.POST
               users_checked = []
               for i, v  in  post.iteritems():
                 if (i != "check_all"):
                  for val in v :
                    users_checked.append(i)
               view_name = "Change state"
               success_user = ''
               fail_user = ''
               message = ''
               for username in users_checked:      
                   user = Users_info.objects.get(username=username)
                   if(user.retry_number >= ocsettings.max_retries_per_user and user.state == 'failed'):
                       success_user += " "+user.username+" "
                       user.retry_number = 0
                       user.state = 'in_queue'
                       user.save()
                   else:
                     fail_user += " "+user.username+" "
               if (success_user != ''):
                 message += 'The user(s) <b>' +success_user+'</b> had been returned to the queue<br>'
               if(fail_user != ''):
                 message += "Sorry can't change the status for <b>"+fail_user+"</b><br>"
               return render_to_response('change_state.html',{"check_user" : users_checked, "report_title" : view_name, "message" : message})
        else:
            return HttpResponseRedirect('/wizard/')
    except:
       return HttpResponse('') 

def view_user(request, user_id):
    try:
        if(request.user.username == 'admin' ):
            view_name = "Change state"
            user_infos = Users_info.objects.get(id=user_id)
            success_user = ''
            fail_user = ''
            message = ''
            if (request.method == "POST"):
                if(user_infos.retry_number >= ocsettings.max_retries_per_user and user_infos.state == 'failed'):
                     success_user = user_infos.username
                     user_infos.retry_number = 0
                     user_infos.state = 'in_queue'
                     user_infos.save()
                else:
                  fail_user = user_infos.username
                if (success_user != ''):
                   message = 'The user(s) <b>' +success_user+'</b> had been returned to the queue<br>'
                elif(fail_user != ''):
                   message = "Sorry can't change the status for <b>"+fail_user+"</b><br>"
                return render_to_response('change_single_user.html',{"report_title" : view_name, "message" : message})
            else:
                user_log_message = user_log.objects.filter(username=user_infos.username)
                colored = ''
                value = ''
                value_warning = ''
                error_message = ''
                for entry in user_log_message:
                  if(entry.type == 'E'):
                    error_message += "<font id='user-log-error'>"+ entry.message.replace('\n','<br>') +"</font>"
                    value = "<font id='user-log-error'>"+ entry.message.replace('\n','<br>') +"</font>"
                  elif(entry.type == 'W'):
                    value = "<font id='user-log-warning'>"+ entry.message.replace('\n','<br>') +"</font><br>"
                  else:
                    value = "<font id='user-log-information'>"+ entry.message.replace('\n','<br>') +"</font><br>"
                  colored +=  "<br>" + value
                return render_to_response('user-details.html',{ "user_infos" : user_infos,"message" : colored , "username" : user_id, "error_message" : error_message } )
        else:
            return HttpResponseRedirect('/wizard/')
    except Exception, exc:
        return HttpResponse('')
    

def getPlaceInQueue(request):
    queued = Users_info.objects.get(username=request.user.username)
    cursor = connection.cursor()
    queued_count =  cursor.execute(" SELECT * FROM `wizard_users_info` WHERE `id_id` < %s AND `state` LIKE 'in_queue'", [queued.id_id])
#    all_queued_users =  Users_info.objects.filter(state='in_queue',id__lte=3)
    
#    for entry in all_queued_users:
#        queued_count += 1

    queue_place = queued_count + 1

    return HttpResponse(str(queue_place))

def feedback_view(request):
    if request.user.username == '' :
        return HttpResponseRedirect('/wizard/')
    if request.method == "POST":
        try:
            user = Users_info.objects.get(username = request.user.username)
            subject = request.user.username + "'s feedback"
            feedback = request.POST['feedback']
            user.feedback += feedback
            user.save()
            util.oc_send_mail(subject, feedback, ocsettings.smtp_user+'@'+ocsettings.auc_old_domain ,[ocsettings.feedback_account])
            return HttpResponse('done')
        except:
            return HttpResponse('failed')
    else:
        return render_to_response('feedback.html' , {"username" : request.user.username } )


def faq_view(request):
    return render_to_response('faqs.html', {"username" : request.user.username} )

def submit_mobile(request):
    username = request.user.username
    user = Users_info.objects.get(username=username)
    try:
        mobile = request.POST['num'] 
        if(user):
            user.mobile = mobile
            user.save()
            return HttpResponse('valid')
        else:
            return HttpResponse('invalid')
    except:
        return HttpResponse('invalid')

