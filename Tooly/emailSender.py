import smtplib
from email.mime.text import MIMEText

to = ["natutaylor@gmail.com"]
APP_PASS = "REEMPLAZAR_APP_PASSWORD"
sender = "toolyrobot@gmail.com"
password = "REEMPLAZAR_PASSWORD"




def sendEmail(msg):
    msg["Subject"] = "Message of Tooly Robot"
    msg["From"] = sender
    msg["To"] =  ','.join(to)
    smtpServer = smtplib.SMTP_SSL('smtp.gmail.com',465)
    smtpServer.login(sender,APP_PASS)
    smtpServer.sendmail(sender,to,msg.as_string())
    smtpServer.quit()
    print("email send!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")



