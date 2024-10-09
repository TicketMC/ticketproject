
from jinja2 import Template
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

smtp_server = "sandbox.smtp.mailtrap.io"
smtp_port = 2525
sender_email = "d8d29e3e3b9e62"
sender_password = "b903ebb76033be"

"""server = smtplib.SMTP(smtp_server, smtp_port)
server.starttls()
server.login(sender_email, sender_password)"""

server = smtplib.SMTP(smtp_server, smtp_port)
server.ehlo()
server.starttls()
server.ehlo()
server.login(sender_email, sender_password)

def send_email_admin(person: str, myemail: str, subject: str, message: str, finalms: str):
  with open("email.html", "r") as file:
    template_str = file.read()

  jinja_template = Template(template_str)
  
  email_data = {
      "greeting": f"Hola {person}!",
      "message": message,
      "finalms": finalms
  }
  email_content = jinja_template.render(email_data)
  msg = MIMEMultipart()
  msg["From"] = "ticketmc.sena@gmail.com"
  msg["To"] = myemail
  msg["Subject"] = subject
  msg.attach(MIMEText(email_content, "html"))

  server.sendmail(sender_email, myemail, msg.as_string())
  server.quit()
  
def send_email_user(person: str, myemail: str, subject: str, message: str, finalms: str):
  with open("email.html", "r") as file:
    template_str = file.read()

  jinja_template = Template(template_str)
  
  email_data = {
      "greeting": f"Hola {person}!",
      "message": message,
      "finalms": finalms
  }
  email_content = jinja_template.render(email_data)
  msg = MIMEMultipart()
  msg["From"] = "ticketmc.sena@gmail.com"
  msg["To"] = myemail
  msg["Subject"] = subject
  msg.attach(MIMEText(email_content, "html"))

  server.sendmail(sender_email, myemail, msg.as_string())
  server.quit()

