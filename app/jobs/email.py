from flask_mail import Message
from app import mail
from flask import render_template


def send_email(user,subject,template,**kwargs):
    template ="email/"+template
    msg= Message()
    msg.body = render_template(template+".txt",firstname=user.first_name,lastname=user.last_name,**kwargs)
    msg.html = render_template(template+".html",firstname=user.first_name,lastname=user.last_name,**kwargs)
    msg.recipients=[user.email]
    msg.subject=subject
    mail.send(msg)
    
    
    