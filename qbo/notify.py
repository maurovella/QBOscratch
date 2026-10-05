"""Aviso por mail a los familiares cuando el robot no recibe respuesta.

La cuenta, la contrasena y los destinatarios salen de variables de entorno,
no del codigo:

    QBO_SMTP_USER       cuenta de Gmail que envia
    QBO_SMTP_PASSWORD   app password de esa cuenta
    QBO_ALERT_TO        destinatarios separados por coma

Si falta alguna, sendEmail() avisa por pantalla y no manda nada.
"""
import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 465


def settings():
    sender = os.environ.get("QBO_SMTP_USER", "").strip()
    password = os.environ.get("QBO_SMTP_PASSWORD", "")
    to = [addr.strip() for addr in os.environ.get("QBO_ALERT_TO", "").split(",") if addr.strip()]
    return sender, password, to


def sendEmail(msg):
    sender, password, to = settings()
    if not (sender and password and to):
        print("email NO enviado: faltan QBO_SMTP_USER, QBO_SMTP_PASSWORD o QBO_ALERT_TO")
        return False
    msg["Subject"] = "Message of Tooly Robot"
    msg["From"] = sender
    msg["To"] =  ','.join(to)
    smtpServer = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
    smtpServer.login(sender, password)
    smtpServer.sendmail(sender,to,msg.as_string())
    smtpServer.quit()
    print("email send!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    return True
