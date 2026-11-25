"""Send opted-in weekly summaries. Schedule once a week with cron/Task Scheduler."""
import datetime
import os
import smtplib
import ssl
from email.message import EmailMessage

import app


def send_digest():
    host = os.getenv('SMTP_HOST', '').strip()
    sender = os.getenv('SMTP_FROM', os.getenv('SMTP_USERNAME', '')).strip()
    if not host or not sender:
        raise RuntimeError('Configure SMTP_HOST and SMTP_FROM in backend/.env before scheduling digests.')

    today = app.local_today()
    week_start = (today - datetime.timedelta(days=7)).isoformat()
    week_end = today.isoformat()
    con = app.db()
    recipients = con.execute('''SELECT u.id,u.name,u.email FROM users u JOIN profiles p ON p.user_id=u.id
        WHERE p.weekly_digest_opt_in=1 AND u.email_verified=1''').fetchall()
    sent = 0
    for user in recipients:
        already = con.execute('SELECT 1 FROM digest_sent WHERE user_id=? AND week_start=?', (user['id'], week_start)).fetchone()
        if already:
            continue
        rows = con.execute('SELECT footprint FROM daily_logs WHERE user_id=? AND log_date>? AND log_date<=?',
                           (user['id'], week_start, week_end)).fetchall()
        vals = [float(__import__('json').loads(r['footprint']).get('daily', 0)) for r in rows]
        total = sum(vals)
        average = total / len(vals) if vals else 0
        msg = EmailMessage()
        msg['Subject'] = 'Your Carbon Footprint weekly summary'
        msg['From'] = sender
        msg['To'] = user['email']
        msg.set_content(
            f"Hello {user['name']},\n\n"
            f"Your last 7-day tracking summary ({week_start} to {week_end}):\n"
            f"Recorded check-ins: {len(vals)}\n"
            f"Recorded total: {total:.2f} kg CO2e (indicative estimate)\n"
            f"Average per recorded day: {average:.2f} kg CO2e\n\n"
            "Only days with saved check-ins are included. These figures are indicative, not a certified inventory.\n"
            "You can turn off weekly summaries in Profile > Account & Privacy.\n"
        )
        with smtplib.SMTP(host, int(os.getenv('SMTP_PORT', '587')), timeout=20) as server:
            if os.getenv('SMTP_USE_TLS', 'true').lower() == 'true':
                server.starttls(context=ssl.create_default_context())
            username = os.getenv('SMTP_USERNAME', '').strip()
            if username:
                server.login(username, os.getenv('SMTP_PASSWORD', ''))
            server.send_message(msg)
        con.execute('INSERT INTO digest_sent(user_id,week_start,sent_at) VALUES(?,?,?)',
                    (user['id'], week_start, datetime.datetime.utcnow().isoformat()))
        con.commit()
        sent += 1
    con.close()
    print(f'Sent {sent} weekly digest(s).')


if __name__ == '__main__':
    send_digest()
