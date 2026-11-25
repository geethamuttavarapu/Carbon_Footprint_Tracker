"""Send one daily check-in reminder to opted-in users who have not logged today."""
import datetime
import os
import smtplib
import ssl
from email.message import EmailMessage

import app


def send_reminders():
    host = os.getenv('SMTP_HOST', '').strip()
    sender = os.getenv('SMTP_FROM', os.getenv('SMTP_USERNAME', '')).strip()
    if not host or not sender:
        raise RuntimeError('Configure SMTP_HOST and SMTP_FROM in backend/.env before scheduling reminders.')
    today = app.local_today().isoformat()
    con = app.db()
    users = con.execute('''SELECT u.id,u.name,u.email FROM users u JOIN profiles p ON p.user_id=u.id
        WHERE p.daily_reminder_opt_in=1 AND u.email_verified=1
        AND NOT EXISTS (SELECT 1 FROM daily_logs d WHERE d.user_id=u.id AND d.log_date=?)''', (today,)).fetchall()
    sent = 0
    for user in users:
        if con.execute('SELECT 1 FROM reminder_sent WHERE user_id=? AND reminder_date=?', (user['id'], today)).fetchone():
            continue
        msg = EmailMessage()
        msg['Subject'] = 'A gentle reminder to log your daily footprint'
        msg['From'] = sender
        msg['To'] = user['email']
        msg.set_content(f"Hello {user['name']},\n\nYou have not saved today's Carbon Footprint check-in yet. If you have a moment, record your activities to keep your personal trend up to date.\n\nYou can turn off reminders in Profile > Account & Privacy.\n")
        with smtplib.SMTP(host, int(os.getenv('SMTP_PORT', '587')), timeout=20) as server:
            if os.getenv('SMTP_USE_TLS', 'true').lower() == 'true':
                server.starttls(context=ssl.create_default_context())
            username = os.getenv('SMTP_USERNAME', '').strip()
            if username:
                server.login(username, os.getenv('SMTP_PASSWORD', ''))
            server.send_message(msg)
        con.execute('INSERT INTO reminder_sent(user_id,reminder_date,sent_at) VALUES(?,?,?)',
                    (user['id'], today, datetime.datetime.utcnow().isoformat()))
        con.commit()
        sent += 1
    con.close()
    print(f'Sent {sent} daily reminder(s).')


if __name__ == '__main__':
    send_reminders()
