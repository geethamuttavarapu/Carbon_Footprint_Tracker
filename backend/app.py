from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, secrets, json, os, datetime, math, re, smtplib, ssl, urllib.request, urllib.error
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from email.message import EmailMessage
from xml.sax.saxutils import escape
try:
    import dns.resolver
except ImportError:
    dns = None

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, '.env'))
DB = os.path.join(BASE, 'ecotrack.db')
app = Flask(__name__)
CORS(app, supports_credentials=True, origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(',') if x.strip()])
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
SESSION_DAYS = int(os.getenv('SESSION_DAYS', '14'))
_RATE = {}

CATEGORIES = ['transportation','electricity','food','shopping','waste','cooking']
# CEA CO2 Baseline Database / Annual Report 2024-25: FY 2023-24
# Weighted-average all-India grid factor including renewable generation.
INDIA_GRID_KG_CO2_PER_KWH = 0.727
# India GHG Program indicative passenger transport factors (2014-15 technical papers).
INDIA_BUS_KG_CO2_PER_PAX_KM = 0.015161
INDIA_RAIL_KG_CO2_PER_PAX_KM = 0.00794
INDIA_MOTORCYCLE_KG_CO2_PER_KM = 0.0356
INDIA_GRID_FACTOR_YEAR = 'FY 2023-24'
EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
VERIFY_MINUTES = 15
LOCAL_TZ = ZoneInfo('Asia/Kolkata')
def local_today(): return datetime.datetime.now(LOCAL_TZ).date()

def db():
    con = sqlite3.connect(DB)
    con.execute('PRAGMA foreign_keys=ON')
    con.row_factory = sqlite3.Row
    return con

def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}

def init_db():
    con = db(); c = con.cursor()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
      password TEXT NOT NULL, email_verified INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS email_verifications (
      user_id INTEGER PRIMARY KEY, code_hash TEXT NOT NULL, expires_at TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS password_resets (
      user_id INTEGER PRIMARY KEY, code_hash TEXT NOT NULL, expires_at TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS profiles (
      user_id INTEGER PRIMARY KEY, answers TEXT NOT NULL DEFAULT '{}', footprint TEXT NOT NULL DEFAULT '{}',
      points INTEGER NOT NULL DEFAULT 0, streak INTEGER NOT NULL DEFAULT 0, last_goal_date TEXT, leaderboard_opt_in INTEGER NOT NULL DEFAULT 0, weekly_digest_opt_in INTEGER NOT NULL DEFAULT 0, daily_reminder_opt_in INTEGER NOT NULL DEFAULT 0,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS daily_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, log_date TEXT NOT NULL,
      inputs TEXT NOT NULL, footprint TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      UNIQUE(user_id, log_date), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS assessments (
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, log_date TEXT NOT NULL,
      total REAL NOT NULL, categories TEXT NOT NULL, created_at TEXT NOT NULL,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS contact_messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL,
      message TEXT NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS activity_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, action TEXT NOT NULL,
      points INTEGER NOT NULL, saved_kg REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
      FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')
    pcols={r['name'] for r in c.execute('PRAGMA table_info(profiles)').fetchall()}
    if 'leaderboard_opt_in' not in pcols: c.execute('ALTER TABLE profiles ADD COLUMN leaderboard_opt_in INTEGER NOT NULL DEFAULT 0')
    if 'weekly_digest_opt_in' not in pcols: c.execute('ALTER TABLE profiles ADD COLUMN weekly_digest_opt_in INTEGER NOT NULL DEFAULT 0')
    if 'daily_reminder_opt_in' not in pcols: c.execute('ALTER TABLE profiles ADD COLUMN daily_reminder_opt_in INTEGER NOT NULL DEFAULT 0')
    c.executescript('''
    CREATE TABLE IF NOT EXISTS challenges (id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL, target_days INTEGER NOT NULL, points INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS challenge_participation (user_id INTEGER NOT NULL, challenge_id TEXT NOT NULL, joined_at TEXT NOT NULL, completed_at TEXT, PRIMARY KEY(user_id,challenge_id), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(challenge_id) REFERENCES challenges(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS digest_sent (user_id INTEGER NOT NULL, week_start TEXT NOT NULL, sent_at TEXT NOT NULL, PRIMARY KEY(user_id,week_start), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS reminder_sent (user_id INTEGER NOT NULL, reminder_date TEXT NOT NULL, sent_at TEXT NOT NULL, PRIMARY KEY(user_id,reminder_date), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    ''')
    c.executemany('INSERT OR IGNORE INTO challenges(id,title,description,target_days,points) VALUES(?,?,?,?,?)',[('green-commute','Green Commute Week','Log a daily trip using walking, cycling, bus, train or metro on five different days.',5,100),('plant-forward','Plant-Forward Week','Complete five daily check-ins and choose a plant-forward or vegetarian meal.',5,80),('low-waste','Low-Waste Week','Complete five daily check-ins and record your waste sorting actions.',5,80)])
    cols={r['name'] for r in c.execute('PRAGMA table_info(users)').fetchall()}
    if 'email_verified' not in cols:
        c.execute('ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0')
    c.execute('CREATE INDEX IF NOT EXISTS idx_daily_user_date ON daily_logs(user_id, log_date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_activity_user_date ON activity_logs(user_id, created_at)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at)')
    con.commit(); con.close()

init_db()

def auth_user():
    h=request.headers.get('Authorization','')
    if not h.startswith('Bearer '): return None
    token=h[7:]
    con=db(); cutoff=(datetime.datetime.utcnow()-datetime.timedelta(days=SESSION_DAYS)).isoformat()
    row=con.execute('SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=? AND s.created_at>=?',(token,cutoff)).fetchone()
    if not row: con.execute('DELETE FROM sessions WHERE token=?',(token,)); con.commit()
    con.close()
    return row

def clean_num(v):
    try:
        value = float(v if v not in (None, '') else 0)
        if not math.isfinite(value): return 0
        return max(0.0, value)
    except (TypeError, ValueError, OverflowError):
        return 0

def calculate_daily(d, profile=None):
    """Transparent daily estimate in kg CO2e; factors are illustrative MVP assumptions."""
    profile = profile or {}
    travel_mode = d.get('travel_mode', 'Walking')
    km = clean_num(d.get('travel_km'))
    travel_factors = {'Car': 0.18, 'Motorcycle': INDIA_MOTORCYCLE_KG_CO2_PER_KM, 'Bus': INDIA_BUS_KG_CO2_PER_PAX_KM, 'Train': INDIA_RAIL_KG_CO2_PER_PAX_KM, 'Metro': 0.04, 'Bicycle': 0.0, 'Walking': 0.0, 'Work from home': 0.0}
    if travel_mode == 'Car':
        occupants = max(1, int(clean_num(profile.get('car_occupants', 1))))
        travel = km * travel_factors['Car'] / occupants
    else:
        travel = km * travel_factors.get(travel_mode, 0.0)
    meals = d.get('meals', 'Mixed')
    meal_factor = {'Plant-based': 1.1, 'Vegetarian': 1.35, 'Mixed': 1.8, 'Meat-heavy': 2.5}.get(meals, 1.8)
    if profile.get('diet_type') == 'Vegan' and meals == 'Mixed': meal_factor = 1.3
    household_size = max(1, int(clean_num(profile.get('household_size', 1))))
    electricity = clean_num(d.get('electricity_kwh')) * INDIA_GRID_KG_CO2_PER_KWH / household_size
    if profile.get('renewable_energy') == 'Yes': electricity *= 0.35
    shopping = 0.45 if d.get('shopping') == 'Yes' else 0.05
    waste = {'Mostly recycled': 0.05, 'Some recycled': 0.12, 'Mostly landfill': 0.22, 'Not sure': 0.12}.get(d.get('waste', 'Not sure'), 0.12)
    cooking = {'LPG': 0.18, 'Electricity': 0.12, 'PNG': 0.15, 'Other': 0.16, 'Not sure': 0.15}.get(profile.get('cooking_source', 'Not sure'), 0.15)
    categories = {
        'transportation': round(travel, 3), 'food': round(meal_factor, 3),
        'electricity': round(electricity, 3), 'shopping': round(shopping, 3),
        'waste': round(waste, 3), 'cooking': round(cooking, 3)
    }
    total = round(sum(categories.values()), 3)
    return {'daily': total, 'weekly': round(total * 7, 2), 'monthly': round(total * 30, 2), 'categories': categories, 'unit': 'kg CO2e', 'estimate': True}


def tips(fp,a):
    cats=fp['categories']; ranked=sorted(cats.items(), key=lambda x:x[1], reverse=True)
    out=[]
    for k,v in ranked[:3]:
        if k=='transportation': out.append({'title':'Move smarter','text':'Try public transport, cycling or walking for one recurring trip this week.','saving':round(v*0.25,1)})
        elif k=='housing': out.append({'title':'Tune your home','text':'Reduce AC use and prioritize efficient lighting/appliances.','saving':round(v*0.18,1)})
        elif k=='food': out.append({'title':'Plant one more plate','text':'Swap one meat-heavy meal for a plant-based option.','saving':round(v*0.12,1)})
        elif k=='travel': out.append({'title':'Fly less, plan better','text':'Batch trips and choose rail or ground travel when practical.','saving':round(v*0.25,1)})
        elif k=='shopping': out.append({'title':'Buy slower','text':'Use second-hand options and stretch the life of clothes and electronics.','saving':round(v*0.2,1)})
        else: out.append({'title':'Lighten your digital footprint','text':'Cut one hour of streaming and avoid unnecessary cloud storage.','saving':round(v*0.2,1)})
    return out

def email_domain_exists(email):
    if not EMAIL_RE.match(email): return False, 'Please enter a valid email address.'
    domain=email.rsplit('@',1)[1].lower().strip('.')
    if dns is None:
        # Syntax is still validated; DNS verification requires dnspython.
        return True, None
    try:
        dns.resolver.resolve(domain, 'MX', lifetime=3)
        return True, None
    except Exception:
        try:
            dns.resolver.resolve(domain, 'A', lifetime=3)
            return True, None
        except Exception:
            return False, 'That email domain does not appear to accept email.'

def send_verification_email(email, code):
    host=os.getenv('SMTP_HOST','').strip(); user=os.getenv('SMTP_USERNAME','').strip(); password=os.getenv('SMTP_PASSWORD','')
    from_email=os.getenv('SMTP_FROM',user).strip(); port=int(os.getenv('SMTP_PORT','587')); use_tls=os.getenv('SMTP_USE_TLS','true').lower()=='true'
    if not host or not from_email:
        if os.getenv('EMAIL_DEV_MODE','false').lower()=='true':
            print(f'[DEV EMAIL] Verification code for {email}: {code}')
            return True, None
        return False, 'Email verification is not configured. Add SMTP settings to backend/.env (see .env.example).'
    try:
        msg=EmailMessage(); msg['Subject']='Verify your Carbon Footprint Tracker account'; msg['From']=from_email; msg['To']=email
        msg.set_content(f'Your Carbon Footprint Tracker verification code is {code}. It expires in {VERIFY_MINUTES} minutes. If you did not create this account, ignore this email.')
        with smtplib.SMTP(host,port,timeout=15) as server:
            if use_tls: server.starttls(context=ssl.create_default_context())
            if user: server.login(user,password)
            server.send_message(msg)
        return True, None
    except Exception as exc:
        app.logger.exception('Unable to send verification email')
        return False, 'We could not send the verification email. Check your SMTP settings and try again.'

def create_verification(user_id,email):
    code=f'{secrets.randbelow(1000000):06d}'
    expires=(datetime.datetime.utcnow()+datetime.timedelta(minutes=VERIFY_MINUTES)).isoformat()
    con=db(); con.execute('INSERT OR REPLACE INTO email_verifications(user_id,code_hash,expires_at,attempts) VALUES(?,?,?,0)',(user_id,generate_password_hash(code),expires)); con.commit(); con.close()
    ok,err=send_verification_email(email,code)
    if not ok:
        con=db(); con.execute('DELETE FROM email_verifications WHERE user_id=?',(user_id,)); con.close()
    return ok,err

@app.post('/api/verify-email')
def verify_email():
    d=body(); email=d.get('email',''); code=d.get('code','')
    if not isinstance(email,str) or not isinstance(code,str): return jsonify(error='Enter the 6-digit verification code sent to your email.'),400
    email=email.strip().lower(); code=code.strip()
    if not EMAIL_RE.match(email) or not re.fullmatch(r'\d{6}',code): return jsonify(error='Enter the 6-digit verification code sent to your email.'),400
    con=db(); u=con.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone(); v=con.execute('SELECT * FROM email_verifications WHERE user_id=?',(u['id'],)).fetchone() if u else None
    if not u or not v: con.close(); return jsonify(error='No pending verification was found for this email.'),404
    if u['email_verified']: con.close(); return jsonify(error='This email is already verified.'),409
    if datetime.datetime.fromisoformat(v['expires_at']) < datetime.datetime.utcnow(): con.execute('DELETE FROM email_verifications WHERE user_id=?',(u['id'],)); con.commit(); con.close(); return jsonify(error='That code has expired. Request a new code.'),400
    if v['attempts']>=5: con.close(); return jsonify(error='Too many incorrect attempts. Request a new code.'),429
    if not check_password_hash(v['code_hash'],code): con.execute('UPDATE email_verifications SET attempts=attempts+1 WHERE user_id=?',(u['id'],)); con.commit(); con.close(); return jsonify(error='Incorrect verification code.'),400
    con.execute('UPDATE users SET email_verified=1 WHERE id=?',(u['id'],)); con.execute('DELETE FROM email_verifications WHERE user_id=?',(u['id'],)); token=secrets.token_urlsafe(32); con.execute('INSERT INTO sessions VALUES(?,?,?)',(token,u['id'],datetime.datetime.utcnow().isoformat())); con.commit(); con.close()
    return jsonify(token=token,user={'id':u['id'],'name':u['name'],'email':u['email']})

@app.post('/api/resend-verification')
def resend_verification():
    d=body(); email=d.get('email','')
    if not isinstance(email,str): return jsonify(error='Enter a valid email address.'),400
    email=email.strip().lower()
    con=db(); u=con.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone(); con.close()
    if not u: return jsonify(error='No account was found for that email.'),404
    if u['email_verified']: return jsonify(error='This email is already verified.'),409
    ok,err=create_verification(u['id'],email)
    if not ok:return jsonify(error=err),503
    return jsonify(ok=True,message='A new verification code has been sent.')

@app.post('/api/signup')
def signup():
    d=body(); name=d.get('name',''); email=d.get('email',''); pw=d.get('password','')
    if not all(isinstance(x,str) for x in (name,email,pw)): return jsonify(error='Enter a valid name, email and password.'),400
    name=name.strip(); email=email.strip().lower()
    if not isinstance(name,str) or not isinstance(email,str) or not isinstance(pw,str) or not name.strip() or len(name)>100 or len(pw)<8: return jsonify(error='Enter your name, a valid email address and a password of at least 8 characters.'),400
    ok,err=email_domain_exists(email)
    if not ok:return jsonify(error=err),400
    con=db()
    try:
        cur=con.execute('INSERT INTO users(name,email,password,email_verified,created_at) VALUES(?,?,?,?,?)',(name,email,generate_password_hash(pw),0,datetime.datetime.utcnow().isoformat())); uid=cur.lastrowid
        con.execute('INSERT INTO profiles(user_id,answers) VALUES(?,?)',(uid,'{}')); con.commit()
    except sqlite3.IntegrityError:
        u=con.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone(); con.close()
        if u and not u['email_verified']:
            ok,err=create_verification(u['id'],email)
            if not ok:return jsonify(error=err),503
            return jsonify(needs_verification=True,message='An account exists but the email is not verified. A new code was sent.',email=email),200
        return jsonify(error='An account with this email already exists.'),409
    con.close()
    ok,err=create_verification(uid,email)
    if not ok:
        con=db(); con.execute('DELETE FROM profiles WHERE user_id=?',(uid,)); con.execute('DELETE FROM users WHERE id=?',(uid,)); con.commit(); con.close()
        return jsonify(error=err),503
    return jsonify(needs_verification=True,message='Check your email for a 6-digit verification code.',email=email)

@app.post('/api/signin')
def signin():
    d=body(); email=d.get('email',''); password=d.get('password','')
    if not isinstance(email,str) or not isinstance(password,str): return jsonify(error='Invalid email or password.'),401
    con=db(); u=con.execute('SELECT * FROM users WHERE email=?',(email.strip().lower(),)).fetchone()
    if not u or not check_password_hash(u['password'],password): con.close(); return jsonify(error='Invalid email or password.'),401
    if not u['email_verified']:
        con.close(); return jsonify(error='Please verify your email before signing in.'),403
    token=secrets.token_urlsafe(32); con.execute('INSERT INTO sessions VALUES(?,?,?)',(token,u['id'],datetime.datetime.utcnow().isoformat())); con.commit(); con.close()
    return jsonify(token=token,user={'id':u['id'],'name':u['name'],'email':u['email']})

@app.post('/api/signout')
def signout():
    h=request.headers.get('Authorization',''); token=h[7:] if h.startswith('Bearer ') else ''
    con=db(); con.execute('DELETE FROM sessions WHERE token=?',(token,)); con.commit(); con.close(); return jsonify(ok=True)

@app.get('/api/me')
def me():
    u=auth_user()
    if not u: return jsonify(error='Unauthorized'),401
    con=db(); p=con.execute('SELECT * FROM profiles WHERE user_id=?',(u['id'],)).fetchone()
    today=local_today().isoformat()
    row=con.execute('SELECT footprint FROM daily_logs WHERE user_id=? AND log_date=?',(u['id'],today)).fetchone()
    latest=con.execute('SELECT footprint FROM daily_logs WHERE user_id=? ORDER BY log_date DESC LIMIT 1',(u['id'],)).fetchone()
    fp=json.loads(row['footprint']) if row else {}
    latest_fp=json.loads(latest['footprint']) if latest else {}
    con.close()
    return jsonify(user={'id':u['id'],'name':u['name'],'email':u['email']}, profile=json.loads(p['answers']), footprint=fp, latest_footprint=latest_fp, points=p['points'], streak=p['streak'], leaderboard_opt_in=bool(p['leaderboard_opt_in']), weekly_digest_opt_in=bool(p['weekly_digest_opt_in']), daily_reminder_opt_in=bool(p['daily_reminder_opt_in']), has_profile=all(json.loads(p['answers']).get(k) not in (None,'') for k in ['city','home_type','household_size','transport_mode','cooking_source','diet_type','renewable_energy']))

@app.put('/api/profile')
def update_profile():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    a=body()
    required=['city','home_type','household_size','transport_mode','cooking_source','diet_type','renewable_energy']
    if any(a.get(k) in (None,'') for k in required): return jsonify(error='Please complete all personal profile fields.'),400
    allowed={'home_type':['Apartment','Independent house','Shared accommodation','Other'],'transport_mode':['Car','Motorcycle','Public Transport','Bicycle','Walking'],'cooking_source':['LPG','Electricity','PNG','Other','Not sure'],'diet_type':['Vegan','Vegetarian','Flexitarian','Non-Vegetarian'],'renewable_energy':['Yes','No','Not sure']}
    if not isinstance(a.get('city'),str) or len(a.get('city','').strip())>100 or any(a.get(k) not in vals for k,vals in allowed.items()): return jsonify(error='Please check your profile answers.'),400
    try: a['household_size']=max(1,min(20,int(a['household_size'])))
    except: return jsonify(error='Household size must be a valid number.'),400
    try: a['car_occupants']=max(1,min(8,int(a.get('car_occupants') or 1)))
    except: return jsonify(error='Car occupants must be a number from 1 to 8.'),400
    con=db(); con.execute('UPDATE profiles SET answers=? WHERE user_id=?',(json.dumps(a),u['id'])); con.commit(); con.close()
    return jsonify(ok=True,profile=a)

@app.get('/api/daily')
def get_daily():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    day=request.args.get('date') or local_today().isoformat()
    try: datetime.date.fromisoformat(day)
    except (ValueError,TypeError):return jsonify(error='Invalid date.'),400
    con=db(); row=con.execute('SELECT inputs,footprint,updated_at FROM daily_logs WHERE user_id=? AND log_date=?',(u['id'],day)).fetchone(); con.close()
    return jsonify(date=day,completed=bool(row),inputs=json.loads(row['inputs']) if row else {},footprint=json.loads(row['footprint']) if row else None,updated_at=row['updated_at'] if row else None)

@app.post('/api/daily')
def save_daily():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    d=body(); day=d.get('date') or local_today().isoformat(); a=d.get('inputs') or {}
    if not isinstance(day,str) or not isinstance(a,dict):return jsonify(error='Invalid daily check-in data.'),400
    try: parsed_day=datetime.date.fromisoformat(day)
    except (ValueError,TypeError):return jsonify(error='Invalid date.'),400
    if parsed_day>local_today(): return jsonify(error='Future dates cannot be submitted.'),400
    required=['travel_mode','travel_km','meals','electricity_kwh','shopping','waste']
    if any(k not in a or a[k] in (None,'') for k in required):return jsonify(error='Please complete all daily activity questions.'),400
    allowed_daily={'travel_mode':['Car','Motorcycle','Bus','Train','Metro','Bicycle','Walking','Work from home'],'meals':['Plant-based','Vegetarian','Mixed','Meat-heavy'],'shopping':['Yes','No'],'waste':['Mostly recycled','Some recycled','Mostly landfill','Not sure']}
    if any(a.get(k) not in vals for k,vals in allowed_daily.items()):return jsonify(error='Please check your daily activity selections.'),400
    for key in ('travel_km','electricity_kwh'):
        try:
            value=float(a[key])
            if not math.isfinite(value) or value < 0: raise ValueError()
        except (TypeError,ValueError,OverflowError):
            return jsonify(error=f'{key.replace("_", " ").capitalize()} must be a valid non-negative number.'),400
    if float(a['travel_km'])>500 or float(a['electricity_kwh'])>100:return jsonify(error='Please check the travel and electricity values.'),400
    con=db(); profile_row=con.execute('SELECT answers FROM profiles WHERE user_id=?',(u['id'],)).fetchone(); profile=json.loads(profile_row['answers']) if profile_row else {}
    fp=calculate_daily(a,profile); now=datetime.datetime.utcnow().isoformat()
    con.execute("INSERT INTO daily_logs(user_id,log_date,inputs,footprint,created_at,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,log_date) DO UPDATE SET inputs=excluded.inputs,footprint=excluded.footprint,updated_at=excluded.updated_at",(u['id'],day,json.dumps(a),json.dumps(fp),now,now))
    con.execute('DELETE FROM assessments WHERE user_id=? AND log_date=?',(u['id'],day))
    con.execute('INSERT INTO assessments(user_id,log_date,total,categories,created_at) VALUES(?,?,?,?,?)',(u['id'],day,fp['daily'],json.dumps(fp['categories']),now))
    p=con.execute('SELECT points,streak,last_goal_date FROM profiles WHERE user_id=?',(u['id'],)).fetchone()
    today=local_today(); last=p['last_goal_date']; streak=p['streak']
    if day==today.isoformat() and last!=day:
        streak=streak+1 if last and (today-datetime.date.fromisoformat(last)).days==1 else 1
        con.execute('UPDATE profiles SET points=points+10,streak=?,last_goal_date=? WHERE user_id=?',(streak,day,u['id']))
        con.execute('INSERT INTO activity_logs(user_id,action,points,saved_kg,created_at) VALUES(?,?,?,?,?)',(u['id'],'Completed daily check-in',10,0,now))
    # Complete joined community challenges from qualifying, recorded days. XP is awarded once.
    joined=con.execute('SELECT cp.challenge_id,cp.joined_at,c.target_days,c.points FROM challenge_participation cp JOIN challenges c ON c.id=cp.challenge_id WHERE cp.user_id=? AND cp.completed_at IS NULL',(u['id'],)).fetchall()
    for challenge in joined:
        logs=con.execute('SELECT inputs FROM daily_logs WHERE user_id=? AND log_date>=?',(u['id'],challenge['joined_at'][:10])).fetchall()
        qualifying=0
        for log in logs:
            item=json.loads(log['inputs'])
            if challenge['challenge_id']=='green-commute' and item.get('travel_mode') in ('Walking','Bicycle','Bus','Train','Metro'): qualifying+=1
            elif challenge['challenge_id']=='plant-forward' and item.get('meals') in ('Plant-based','Vegetarian'): qualifying+=1
            elif challenge['challenge_id']=='low-waste' and item.get('waste') in ('Mostly recycled','Some recycled'): qualifying+=1
        if qualifying>=challenge['target_days']:
            con.execute('UPDATE challenge_participation SET completed_at=? WHERE user_id=? AND challenge_id=? AND completed_at IS NULL',(now,u['id'],challenge['challenge_id']))
            con.execute('UPDATE profiles SET points=points+? WHERE user_id=?',(challenge['points'],u['id']))
            con.execute('INSERT INTO activity_logs(user_id,action,points,saved_kg,created_at) VALUES(?,?,?,?,?)',(u['id'],'Completed challenge: '+challenge['challenge_id'],challenge['points'],0,now))
    con.commit(); points=con.execute('SELECT points,streak FROM profiles WHERE user_id=?',(u['id'],)).fetchone(); con.close()
    return jsonify(ok=True,date=day,footprint=fp,points=points['points'],streak=points['streak'],message='Daily check-in saved. You can edit it anytime today.')

@app.get('/api/history')
def history():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    con=db(); rows=con.execute('SELECT log_date,footprint,updated_at FROM daily_logs WHERE user_id=? ORDER BY log_date DESC LIMIT 90',(u['id'],)).fetchall(); con.close()
    items=[]
    for r in rows:
        fp=json.loads(r['footprint']); items.append({'date':r['log_date'],'total':fp.get('daily',0),'categories':fp.get('categories',{}),'updated_at':r['updated_at']})
    return jsonify(history=items)

@app.post('/api/questionnaire')
def questionnaire():
    return jsonify(error='The long questionnaire has been replaced. Save personal details in My Profile and use Daily Check-in for activities.'),410

@app.post('/api/goal')
def goal():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    d=body(); action=d.get('action','')
    if not isinstance(action,str):return jsonify(error='Unknown mission.'),400
    allowed={'Walk a short trip':40,'Choose a greener meal':30,'Power down for an hour':20}
    if action not in allowed:return jsonify(error='Unknown mission.'),400
    pts=allowed[action]; today=local_today().isoformat(); now=datetime.datetime.utcnow().isoformat()
    con=db(); exists=con.execute("SELECT 1 FROM activity_logs WHERE user_id=? AND action=? AND date(created_at,'+5 hours','+30 minutes')=?",(u['id'],action,today)).fetchone()
    if exists: con.close(); return jsonify(error='You have already completed this mission today.'),409
    con.execute('UPDATE profiles SET points=points+? WHERE user_id=?',(pts,u['id']))
    con.execute('INSERT INTO activity_logs(user_id,action,points,saved_kg,created_at) VALUES(?,?,?,?,?)',(u['id'],action,pts,0,now))
    con.commit(); points=con.execute('SELECT points FROM profiles WHERE user_id=?',(u['id'],)).fetchone()['points']; con.close()
    return jsonify(points=points)

@app.get('/api/activity')
def activity():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    con=db(); rows=con.execute('SELECT action,points,saved_kg,created_at FROM activity_logs WHERE user_id=? ORDER BY id DESC LIMIT 20',(u['id'],)).fetchall(); con.close()
    return jsonify(activity=[dict(r) for r in rows])

@app.get('/api/leaderboard')
def leaderboard():
    con=db(); rows=con.execute('SELECT name,points,streak FROM profiles p JOIN users u ON u.id=p.user_id WHERE p.leaderboard_opt_in=1 ORDER BY points DESC LIMIT 10').fetchall(); con.close(); return jsonify(leaderboard=[dict(r) for r in rows])

@app.post('/api/contact')
def contact():
    d=body()
    if not all(isinstance(d.get(k),str) and d[k].strip() for k in ('name','email','message')): return jsonify(error='Please complete all contact fields.'),400
    if len(d['name'])>100 or len(d['email'])>254 or len(d['message'])>5000 or not EMAIL_RE.match(d['email'].strip()): return jsonify(error='Please check your contact details and keep the message under 5,000 characters.'),400
    con=db(); con.execute('INSERT INTO contact_messages(name,email,message,created_at) VALUES(?,?,?,?)',(d['name'].strip(),d['email'].strip().lower(),d['message'].strip(),datetime.datetime.utcnow().isoformat())); con.commit(); con.close()
    return jsonify(ok=True,message='Thanks — your message has been saved for the project team.')

@app.get('/api/health')
def health(): return jsonify(ok=True,service='EcoTrack API')



@app.before_request
def basic_rate_limit():
    # Lightweight per-IP throttling for authentication and contact endpoints; use a reverse proxy for production-grade limits.
    if request.path in ('/api/signin','/api/signup','/api/verify-email','/api/resend-verification','/api/password-reset/request','/api/password-reset/confirm','/api/contact'):
        key=(request.remote_addr or 'unknown', request.path); now=datetime.datetime.utcnow().timestamp()
        hits=[t for t in _RATE.get(key,[]) if now-t<60]
        limit=12 if request.path=='/api/contact' else 15 if request.path=='/api/coach' else 8
        if len(hits)>=limit: return jsonify(error='Too many attempts. Please wait a minute and try again.'),429
        hits.append(now); _RATE[key]=hits



@app.post('/api/password-reset/request')
def password_reset_request():
    d=body(); email=str(d.get('email','')).strip().lower()
    if not EMAIL_RE.match(email):return jsonify(error='Enter a valid email address.'),400
    con=db(); u=con.execute('SELECT id,email_verified FROM users WHERE email=?',(email,)).fetchone()
    # Do not reveal whether an account exists.
    if not u or not u['email_verified']:
        con.close(); return jsonify(ok=True,message='If a verified account exists, a reset code has been sent.')
    code=f'{secrets.randbelow(1000000):06d}'; expires=(datetime.datetime.utcnow()+datetime.timedelta(minutes=VERIFY_MINUTES)).isoformat()
    con.execute('INSERT OR REPLACE INTO password_resets(user_id,code_hash,expires_at,attempts) VALUES(?,?,?,0)',(u['id'],generate_password_hash(code),expires)); con.commit(); con.close()
    host=os.getenv('SMTP_HOST','').strip(); sender=os.getenv('SMTP_FROM',os.getenv('SMTP_USERNAME','')).strip()
    try:
        if not host or not sender:
            if os.getenv('EMAIL_DEV_MODE','false').lower()=='true': print(f'[DEV EMAIL] Password reset code for {email}: {code}')
            else: return jsonify(error='Password reset email is not configured. Configure SMTP in backend/.env.'),503
        else:
            msg=EmailMessage(); msg['Subject']='Carbon Footprint Tracker password reset'; msg['From']=sender; msg['To']=email; msg.set_content(f'Your password reset code is {code}. It expires in {VERIFY_MINUTES} minutes. If you did not request this, ignore this email.')
            with smtplib.SMTP(host,int(os.getenv('SMTP_PORT','587')),timeout=15) as server:
                if os.getenv('SMTP_USE_TLS','true').lower()=='true':server.starttls(context=ssl.create_default_context())
                username=os.getenv('SMTP_USERNAME','').strip()
                if username:server.login(username,os.getenv('SMTP_PASSWORD',''))
                server.send_message(msg)
    except Exception:
        app.logger.exception('Password reset email failed'); return jsonify(error='Unable to send the reset email. Check SMTP settings.'),503
    return jsonify(ok=True,message='If a verified account exists, a reset code has been sent.')

@app.post('/api/password-reset/confirm')
def password_reset_confirm():
    d=body(); email=str(d.get('email','')).strip().lower(); code=str(d.get('code','')).strip(); password=d.get('password','')
    if not EMAIL_RE.match(email) or not re.fullmatch(r'\d{6}',code) or not isinstance(password,str) or len(password)<8:
        return jsonify(error='Enter your email, 6-digit code and a password of at least 8 characters.'),400
    con=db(); u=con.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone(); reset=con.execute('SELECT * FROM password_resets WHERE user_id=?',(u['id'],)).fetchone() if u else None
    if not reset:con.close();return jsonify(error='Invalid or expired reset code.'),400
    if reset['attempts']>=5 or datetime.datetime.fromisoformat(reset['expires_at'])<datetime.datetime.utcnow():con.execute('DELETE FROM password_resets WHERE user_id=?',(u['id'],));con.commit();con.close();return jsonify(error='Reset code expired. Request a new one.'),400
    if not check_password_hash(reset['code_hash'],code):con.execute('UPDATE password_resets SET attempts=attempts+1 WHERE user_id=?',(u['id'],));con.commit();con.close();return jsonify(error='Incorrect reset code.'),400
    con.execute('UPDATE users SET password=? WHERE id=?',(generate_password_hash(password),u['id']));con.execute('DELETE FROM password_resets WHERE user_id=?',(u['id'],));con.execute('DELETE FROM sessions WHERE user_id=?',(u['id'],));con.commit();con.close()
    return jsonify(ok=True,message='Password updated. Please sign in again.')

@app.get('/api/insights')
def insights():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    today=local_today(); start=today-datetime.timedelta(days=6); month_start=today.replace(day=1)
    con=db(); rows=con.execute('SELECT log_date,footprint FROM daily_logs WHERE user_id=? AND log_date>=? ORDER BY log_date',(u['id'],(today-datetime.timedelta(days=60)).isoformat())).fetchall(); con.close()
    records=[{'date':r['log_date'],'total':json.loads(r['footprint']).get('daily',0)} for r in rows]
    week=[x for x in records if x['date']>=start.isoformat() and x['date']<=today.isoformat()]
    prev_start=start-datetime.timedelta(days=7); prev=[x for x in records if prev_start.isoformat()<=x['date']<start.isoformat()]
    month=[x for x in records if x['date']>=month_start.isoformat() and x['date']<=today.isoformat()]
    def stats(items):
        vals=[x['total'] for x in items]
        return {'logged_days':len(vals),'total_kg':round(sum(vals),3),'daily_average_kg':round(sum(vals)/len(vals),3) if vals else 0}
    cur=stats(week); old=stats(prev)
    cur['change_percent']=round((cur['total_kg']-old['total_kg'])/old['total_kg']*100,1) if old['total_kg'] else None
    return jsonify(this_week=cur,previous_week=old,this_month=stats(month),records=records)

@app.get('/api/planner')
def planner():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    con=db(); rows=con.execute('SELECT footprint FROM daily_logs WHERE user_id=? ORDER BY log_date DESC LIMIT 7',(u['id'],)).fetchall(); con.close()
    cats={}
    for r in rows:
        for k,v in json.loads(r['footprint']).get('categories',{}).items(): cats[k]=cats.get(k,0)+float(v)
    ranked=sorted(cats.items(),key=lambda x:x[1],reverse=True)
    actions={
      'transportation':('Choose a lower-emission commute','Replace one short car or motorcycle journey with walking, cycling or public transport.'),
      'food':('Plan a plant-forward meal','Try one additional plant-forward meal and avoid food waste.'),
      'electricity':('Reduce electricity use','Switch off idle devices and use efficient cooling and lighting.'),
      'shopping':('Pause before purchasing','Delay non-essential purchases and consider repair, reuse or second-hand options.'),
      'waste':('Sort household waste','Separate recyclable and organic waste according to local collection rules.'),
      'cooking':('Cook efficiently','Use lids, batch cooking and an efficient appliance where practical.')}
    plan=[{'category':k,'title':actions.get(k,('Review this category','Look for one practical reduction opportunity.'))[0],'action':actions.get(k,('','Review your habits.'))[1]} for k,_ in ranked[:5]]
    if not plan: plan=[{'category':'getting-started','title':'Start with one daily log','action':'Complete your first daily check-in to create a personalised plan.'}]
    return jsonify(planner=plan,source_days=len(rows))

@app.get('/api/export')
def export_data():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    con=db(); user=con.execute('SELECT name,email,created_at FROM users WHERE id=?',(u['id'],)).fetchone(); profile=con.execute('SELECT answers,points,streak,leaderboard_opt_in,weekly_digest_opt_in,daily_reminder_opt_in FROM profiles WHERE user_id=?',(u['id'],)).fetchone(); logs=con.execute('SELECT log_date,inputs,footprint,updated_at FROM daily_logs WHERE user_id=? ORDER BY log_date',(u['id'],)).fetchall(); acts=con.execute('SELECT action,points,saved_kg,created_at FROM activity_logs WHERE user_id=? ORDER BY created_at',(u['id'],)).fetchall(); con.close()
    return jsonify(account=dict(user),profile={'answers':json.loads(profile['answers']),'points':profile['points'],'streak':profile['streak'],'leaderboard_opt_in':bool(profile['leaderboard_opt_in']),'weekly_digest_opt_in':bool(profile['weekly_digest_opt_in']),'daily_reminder_opt_in':bool(profile['daily_reminder_opt_in'])},daily_logs=[{'date':r['log_date'],'inputs':json.loads(r['inputs']),'footprint':json.loads(r['footprint']),'updated_at':r['updated_at']} for r in logs],activities=[dict(r) for r in acts])

@app.put('/api/privacy')
def privacy_settings():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    d=body(); opt=d.get('leaderboard_opt_in')
    if not isinstance(opt,bool):return jsonify(error='Choose whether to appear on the public leaderboard.'),400
    con=db(); con.execute('UPDATE profiles SET leaderboard_opt_in=? WHERE user_id=?',(1 if opt else 0,u['id'])); con.commit(); con.close()
    return jsonify(ok=True,leaderboard_opt_in=opt)

@app.delete('/api/account')
def delete_account():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    d=body()
    if d.get('confirm')!='DELETE':return jsonify(error='Type DELETE to confirm permanent account removal.'),400
    con=db(); con.execute('DELETE FROM sessions WHERE user_id=?',(u['id'],)); con.execute('DELETE FROM users WHERE id=?',(u['id'],)); con.commit(); con.close()
    return jsonify(ok=True,message='Account and associated application records deleted.')

@app.get('/api/challenges')
def get_challenges():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    con=db(); rows=con.execute('''SELECT c.id,c.title,c.description,c.target_days,c.points,p.joined_at,p.completed_at
      FROM challenges c LEFT JOIN challenge_participation p ON p.challenge_id=c.id AND p.user_id=? ORDER BY c.id''',(u['id'],)).fetchall()
    result=[]
    for row in rows:
        item=dict(row); item['progress_days']=0
        if item['joined_at']:
            logs=con.execute('SELECT inputs FROM daily_logs WHERE user_id=? AND log_date>=?',(u['id'],item['joined_at'][:10])).fetchall()
            for log in logs:
                a=json.loads(log['inputs']); cid=item['id']
                if cid=='green-commute' and a.get('travel_mode') in ('Walking','Bicycle','Bus','Train','Metro'): item['progress_days']+=1
                elif cid=='plant-forward' and a.get('meals') in ('Plant-based','Vegetarian'): item['progress_days']+=1
                elif cid=='low-waste' and a.get('waste') in ('Mostly recycled','Some recycled'): item['progress_days']+=1
        result.append(item)
    con.close()
    return jsonify(challenges=result)

@app.post('/api/challenges/<challenge_id>/join')
def join_challenge(challenge_id):
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    now=local_today().isoformat()+'T00:00:00'; con=db()
    if not con.execute('SELECT 1 FROM challenges WHERE id=?',(challenge_id,)).fetchone():con.close();return jsonify(error='Challenge not found.'),404
    con.execute('INSERT OR IGNORE INTO challenge_participation(user_id,challenge_id,joined_at) VALUES(?,?,?)',(u['id'],challenge_id,now)); con.commit(); con.close()
    return jsonify(ok=True,message='You joined the challenge.')

@app.get('/api/challenges/<challenge_id>/qr')
def challenge_qr(challenge_id):
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    con=db(); exists=con.execute('SELECT 1 FROM challenges WHERE id=?',(challenge_id,)).fetchone(); con.close()
    if not exists:return jsonify(error='Challenge not found.'),404
    try:
        import qrcode,io
        from flask import send_file
        base=os.getenv('FRONTEND_URL','http://localhost:5173').rstrip('/')
        target=f'{base}/?challenge={challenge_id}#community'
        image=qrcode.make(target); buf=io.BytesIO(); image.save(buf,format='PNG'); buf.seek(0)
        return send_file(buf,mimetype='image/png',download_name=f'{challenge_id}-qr.png')
    except ImportError:return jsonify(error='Install qrcode[pil] to generate challenge QR codes.'),503

@app.get('/api/resources')
def sustainability_resources():
    city=request.args.get('city','India').strip()[:100] or 'India'
    import urllib.parse
    topics=[('Recycling and e-waste collection','recycling and e-waste collection centres'),('Repair and reuse services','electronics repair and reuse centres'),('Public transport','public transport stations'),('Community gardens','community gardens and urban farms')]
    return jsonify(city=city,resources=[{'title':title,'description':f'Find current {title.lower()} around {city}. Confirm opening hours and accepted materials with the provider.','url':'https://www.google.com/maps/search/'+urllib.parse.quote_plus(query+' near '+city)} for title,query in topics])

@app.post('/api/coach')
def eco_coach():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    d=body(); question=str(d.get('question','')).strip()[:500]
    if not question:return jsonify(error='Ask a question first.'),400
    con=db(); rows=con.execute('SELECT footprint FROM daily_logs WHERE user_id=? ORDER BY log_date DESC LIMIT 7',(u['id'],)).fetchall(); con.close()
    totals={}
    for row in rows:
        for k,v in json.loads(row['footprint']).get('categories',{}).items():totals[k]=totals.get(k,0)+float(v)
    top=max(totals,key=totals.get) if totals else None
    suggestions={
      'transportation':'Try replacing one short solo vehicle trip with walking, cycling, bus, train or metro where practical.',
      'electricity':'Check high-use appliances, cooling settings and standby power. Compare electricity use over similar days.',
      'food':'Plan one additional plant-forward meal and store food carefully to reduce waste.',
      'shopping':'Pause non-essential purchases; repair, borrow or choose durable second-hand items.',
      'waste':'Separate recyclable, organic and residual waste according to your local municipal collection rules.',
      'cooking':'Use lids, batch cooking and an efficient appliance where practical.'}
    context={'question':question,'recent_recorded_category_totals_kg':{k:round(v,2) for k,v in totals.items()},'recorded_days':len(rows)}
    api_key=os.getenv('OPENAI_API_KEY','').strip()
    if api_key:
        try:
            instructions=('You are an eco-habits coach. Give practical, low-cost, India-relevant suggestions. '
              'Do not claim exact emissions savings, invent local services, or present estimates as certified. '
              'Use only the aggregate activity data supplied. Keep the answer under 130 words.')
            payload=json.dumps({'model':os.getenv('OPENAI_MODEL','gpt-6.2-astra'),'instructions':instructions,'input':json.dumps(context),'max_output_tokens':260}).encode()
            req=urllib.request.Request('https://api.openai.com/v1/responses',data=payload,headers={'Authorization':'Bearer '+api_key,'Content-Type':'application/json'},method='POST')
            with urllib.request.urlopen(req,timeout=25) as response: result=json.loads(response.read().decode())
            chunks=[]
            for item in result.get('output',[]):
                if item.get('type')=='message':
                    for content in item.get('content',[]):
                        if content.get('type')=='output_text' and content.get('text'):chunks.append(content['text'])
            reply=' '.join(chunks).strip()
            if reply:return jsonify(reply=reply,top_category=top,source_days=len(rows),mode='ai')
        except Exception:
            app.logger.exception('AI Eco Coach request failed; using local fallback')
    reply=(f'Your largest recorded category across your latest {len(rows)} check-ins is {top}. ' if top else 'You have not logged enough activity for a personal pattern yet. ')
    reply+=suggestions.get(top,'Start with one daily check-in, then I can suggest a practical next step.')
    reply+=' This is the built-in rule-based fallback. Add OPENAI_API_KEY to enable AI responses.'
    return jsonify(reply=reply,top_category=top,source_days=len(rows),mode='rule-based')

@app.put('/api/notifications')
def notification_preferences():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    d=body(); weekly=d.get('weekly_digest_opt_in'); daily=d.get('daily_reminder_opt_in')
    if not isinstance(weekly,bool) or not isinstance(daily,bool):return jsonify(error='Choose both email notification preferences.'),400
    con=db(); con.execute('UPDATE profiles SET weekly_digest_opt_in=?,daily_reminder_opt_in=? WHERE user_id=?',(int(weekly),int(daily),u['id'])); con.commit(); con.close()
    return jsonify(ok=True,weekly_digest_opt_in=weekly,daily_reminder_opt_in=daily)

@app.get('/api/report.pdf')
def report_pdf():
    u=auth_user()
    if not u:return jsonify(error='Unauthorized'),401
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        import io
    except ImportError:return jsonify(error='PDF export dependency is missing. Install reportlab from requirements.txt.'),503
    con=db(); rows=con.execute('SELECT log_date,footprint FROM daily_logs WHERE user_id=? ORDER BY log_date',(u['id'],)).fetchall(); name=con.execute('SELECT name FROM users WHERE id=?',(u['id'],)).fetchone()['name']; con.close()
    buf=io.BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4); styles=getSampleStyleSheet(); story=[Paragraph('Carbon Footprint Activity Report',styles['Title']),Paragraph('Account: '+escape(name),styles['Normal']),Paragraph('Estimates are illustrative and are not a certified emissions inventory.',styles['Italic']),Spacer(1,14)]
    data=[['Date','Daily estimate (kg CO2e)']]+[[r['log_date'],str(json.loads(r['footprint']).get('daily',0))] for r in rows]
    if len(data)==1:data.append(['No daily records yet','—'])
    table=Table(data,repeatRows=1); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#315b38')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.4,colors.grey),('PADDING',(0,0),(-1,-1),7)])); story.append(table); doc.build(story); buf.seek(0)
    from flask import send_file
    return send_file(buf,mimetype='application/pdf',as_attachment=True,download_name='carbon-footprint-report.pdf')


if __name__=='__main__': app.run(debug=os.getenv('FLASK_DEBUG','false').lower()=='true',host=os.getenv('HOST','127.0.0.1'),port=int(os.getenv('PORT','5000')))
