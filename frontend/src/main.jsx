import React,{useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {LineChart,Line,XAxis,YAxis,Tooltip,ResponsiveContainer,BarChart,Bar,CartesianGrid} from 'recharts';
import './styles.css';

const API=(import.meta.env.VITE_API_URL||'http://127.0.0.1:5000')+'/api';
const localDate=()=>{const d=new Date();return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
const localDateFromUtc=value=>{const d=new Date(value.endsWith('Z')?value:value+'Z');return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
const profileFields=[
{id:'city',label:'Where do you currently live?',type:'text',placeholder:'City'},
{id:'home_type',label:'What type of home do you live in?',options:['Apartment','Independent house','Shared accommodation','Other']},
{id:'household_size',label:'How many people live in your household?',type:'number'},
{id:'car_occupants',label:'If you use a car, how many people usually share the trip?',type:'number',optional:true},
{id:'transport_mode',label:'What is your usual main transport?',options:['Car','Motorcycle','Public Transport','Bicycle','Walking']},
{id:'cooking_source',label:'What do you mainly use for cooking?',options:['LPG','Electricity','PNG','Other','Not sure']},
{id:'diet_type',label:'What best describes your usual diet?',options:['Vegan','Vegetarian','Flexitarian','Non-Vegetarian']},
{id:'renewable_energy',label:'Do you use solar or other renewable electricity?',options:['Yes','No','Not sure']}
];

const faq=[
['What is a carbon footprint?','It is an estimate of the greenhouse-gas emissions associated with your lifestyle choices, expressed as carbon-dioxide equivalent (CO₂e).'],
['How does daily tracking work?','Set up your personal profile once, then record a short daily check-in for travel, food, electricity, shopping and waste.'],
['What areas do you measure?','Daily estimates include travel, food, electricity, shopping, waste and cooking. Your personal profile helps tailor the estimate.'],
['Is my result exact?','No. It is an estimate. The MVP uses transparent factors and assumptions so you can understand the direction of your impact.'],
['Can I change my answers?','Yes. Edit your permanent lifestyle details in My Profile and update your Daily Check-in at any time.'],
['How do rewards work?','Complete check-ins and daily eco-actions to earn XP, protect your streak and unlock badges.'],
['Do you sell my personal data?','No. This project is designed around data minimisation. Your account and questionnaire data are stored in the project database for your dashboard.'],
['Can I delete my data?','Yes. Open My Profile and use the permanent account deletion control. Export your records first if you want to keep a copy.']
];

function getToken(){return localStorage.getItem('eco_token')}
async function api(path,opts={}){const r=await fetch(API+path,{headers:{'Content-Type':'application/json',...(getToken()?{Authorization:'Bearer '+getToken()}:{})},...opts});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.error||'Something went wrong');return d}

class PageErrorBoundary extends React.Component{
 constructor(props){super(props);this.state={hasError:false}}
 static getDerivedStateFromError(){return {hasError:true}}
 render(){
  if(this.state.hasError)return <main className="simple-page page-error"><span className="eyebrow">PAGE RECOVERY</span><h1>This page hit a small snag.</h1><p className="lead">Your other pages and saved data are still here. Try opening this page again.</p><button className="primary big" onClick={()=>this.setState({hasError:false})}>Try this page again →</button></main>;
  return this.props.children;
 }
}

function App(){
 const [route,setRoute]=useState(location.hash.slice(1)||'home');const [me,setMe]=useState(null);const [boot,setBoot]=useState(true);const [transition,setTransition]=useState(false);const transitionTimer=useRef(null);
useEffect(() => {
  let cancelled = false;

  document.documentElement.classList.toggle(
    'dark-theme',
    localStorage.getItem('eco_theme') === 'dark'
  );

  api('/me')
    .then(data => {
      if (!cancelled) setMe(data);
    })
    .catch(() => {})
    .finally(() => {
      if (!cancelled) setBoot(false);
    });

  const syncRoute = () => {
    setRoute(location.hash.slice(1) || 'home');
  };

  window.addEventListener('hashchange', syncRoute);
  window.addEventListener('popstate', syncRoute);

  return () => {
    cancelled = true;
    window.removeEventListener('hashchange', syncRoute);
    window.removeEventListener('popstate', syncRoute);

    if (transitionTimer.current) {
      window.clearTimeout(transitionTimer.current);
    }
  };
}, []);
 const nav=r=>{
  if(r===route)return;
  setTransition(true);setRoute(r);
  if(location.hash!==`#${r}`)window.history.pushState(null,'',`#${r}`);
  window.scrollTo({top:0,behavior:'instant'});
  if(transitionTimer.current)window.clearTimeout(transitionTimer.current);
  transitionTimer.current=window.setTimeout(()=>setTransition(false),850);
 };
 const signout=async()=>{try{await api('/signout',{method:'POST'})}catch{}localStorage.removeItem('eco_token');setMe(null);nav('home')};
 if(boot)return <FootprintLoader full/>;
 const page=route==='home'?<Home me={me} nav={nav}/>:route==='auth'?<Auth onAuth={u=>{setMe(u);nav('dashboard')}}/>:route==='form'?<Protected me={me} nav={nav}><Form nav={nav}/></Protected>:route==='dashboard'?<Protected me={me} nav={nav}><Dashboard nav={nav}/></Protected>:route==='achievements'?<Protected me={me}><Achievements/></Protected>:route==='profile'?<Protected me={me}><Profile/></Protected>:route==='insights'?<Protected me={me}><Insights/></Protected>:route==='community'?<Protected me={me}><Community/></Protected>:route==='contact'?<Contact/>:route==='faq'?<FAQ/>:route==='terms'?<Legal title="Terms & conditions"><p>These terms describe use of the Carbon Footprint Tracker MVP. The calculator is provided for educational and behavioural guidance and is not a certified emissions audit.</p><h3>Use of the service</h3><p>You agree to provide information that is reasonably accurate, keep your login details private, and use the service lawfully.</p><h3>Estimates</h3><p>Results are estimates based on the project's calculation factors and should not be treated as financial, legal, medical or environmental compliance advice.</p><h3>Availability</h3><p>This is a student/MVP project. Features may change as the product evolves.</p></Legal>:route==='privacy'?<Legal title="Privacy & data protection"><p>We collect the information you provide to create an account, calculate your footprint and personalise your dashboard.</p><h3>What we store</h3><p>Account details, questionnaire answers, footprint estimates and reward activity are stored in the project's application database.</p><h3>Your choices</h3><p>You can export your records, opt out of the public leaderboard and email notifications, or permanently delete your account from My Profile. Deletion removes linked application records from the active SQLite database.</p><h3>Security</h3><p>Passwords are hashed by the backend and sessions use randomly generated tokens. No system can guarantee absolute security, so avoid entering information you do not want stored.</p></Legal>:route==='cookies'?<CookieSettings/>:<Home me={me} nav={nav}/>;
 return <><Header me={me} nav={nav} signout={signout}/><div className="page-stage" key={route}><PageErrorBoundary key={route}><div className="page-enter">{page}</div></PageErrorBoundary></div>{transition&&<div className="bee-flight" aria-hidden="true"><span>🐝</span></div>}<Footer nav={nav}/></>;
}


function LoadFailure({message}){return <main className="simple-page"><span className="eyebrow">COULD NOT LOAD THIS PAGE</span><h1>Something went wrong.</h1><p className="lead">{message||'Please check your connection and try again.'}</p><button className="primary big" onClick={()=>location.reload()}>Try again →</button></main>}
function FootprintLoader({full=false}){return <div className={full?'loader full':'loader'}><div className="loader-scene"><span className="foot foot1">●</span><span className="foot foot2">●</span><span className="foot foot3">●</span><span className="foot foot4">●</span></div><div className="loader-word">Walking to your next view<span>...</span></div></div>}
function Header({me,nav,signout}){return <header className="top"><button className="brand" onClick={()=>nav('home')}><span className="brand-mark">☘</span><span><b>Carbon Footprint</b><small>TRACK • REDUCE • REWARD</small></span></button><nav>{me?<><button onClick={()=>nav('dashboard')}>Dashboard</button><button onClick={()=>nav('form')}>Daily Check-in</button><button onClick={()=>nav('achievements')}>Rewards</button><button onClick={()=>nav('profile')}>Profile</button><button onClick={()=>nav('insights')}>Insights</button><button onClick={()=>nav('community')}>Community</button></>:<><button onClick={()=>nav('home')}>Home</button><button onClick={()=>nav('faq')}>FAQs</button><button onClick={()=>nav('contact')}>Contact</button></>}</nav><div className="header-actions">{me?<><span className="xp">✦ {me.points||0} XP</span><button className="outline" onClick={signout}>Sign out</button></>:<button className="primary small" onClick={()=>nav('auth')}>Sign in / Sign up</button>}</div></header>}

function Home({me,nav}){return <main><section className="wwf-hero"><div className="hero-copy"><div className="eyebrow">YOUR PERSONAL ENVIRONMENTAL FOOTPRINT</div><h1>How big is <em>your</em><br/>footprint?</h1><p>Set up your lifestyle once, then log a few simple daily activities to understand and reduce your carbon footprint.</p><div className="hero-cta"><button className="primary big" onClick={()=>nav(me?(me.has_profile?'form':'profile'):'auth')}>Start tracking <span>→</span></button><button className="under" onClick={()=>nav('faq')}>How it works</button></div><div className="hero-note"><span>◒</span> One-time profile · quick daily check-in</div></div><div className="wildlife-art"><div className="sun"></div><div className="hill hill1"></div><div className="hill hill2"></div><div className="tree tree1">♣</div><div className="tree tree2">♣</div><div className="bird">⌁</div><div className="bear">🐻</div><div className="art-card"><b>SMALL STEPS</b><span>BIG IMPACT</span></div></div></section><section className="intro-band"><div><span className="eyebrow">A SIMPLE JOURNEY</span><h2>Measure. Understand. Change.</h2></div><p>A simple daily routine helps you understand your own recorded trends. Results are indicative estimates and depend on the assumptions shown in the methodology notes.</p></section><section className="home-cards"><InfoCard n="01" title="Set up your profile" text="Share a few details about your home and usual lifestyle once."/><InfoCard n="02" title="Track each day" text="Log travel, meals, electricity, shopping and waste in a short check-in."/><InfoCard n="03" title="See your progress" text="Understand your trends, build sustainable habits and earn rewards."/></section><section className="promise"><div className="leaf-burst">✦</div><div><span className="eyebrow">BUILT TO MOTIVATE</span><h2>Your footprint is a starting point, not a judgement.</h2><p>The goal is to make the next action clearer — not to make perfect living feel impossible.</p></div></section></main>}
function InfoCard({n,title,text}){return <article className="info-card"><span>{n}</span><h3>{title}</h3><p>{text}</p><i>↗</i></article>}

function Auth({onAuth}){
 const [mode,setMode]=useState('signin'),[f,setF]=useState({name:'',email:'',password:''}),[err,setErr]=useState(''),[busy,setBusy]=useState(false),[verify,setVerify]=useState(false),[code,setCode]=useState(''),[resetStage,setResetStage]=useState(false);
 const submit=async e=>{e.preventDefault();setErr('');setBusy(true);try{
   if(mode==='forgot'){await api('/password-reset/request',{method:'POST',body:JSON.stringify({email:f.email})});setResetStage(true);setVerify(true);setErr('If a verified account exists, a reset code has been sent.');return;}
   if(mode==='signin'){
     const d=await api('/signin',{method:'POST',body:JSON.stringify({email:f.email,password:f.password})});localStorage.setItem('eco_token',d.token);onAuth(d.user);return;
   }
   const d=await api('/signup',{method:'POST',body:JSON.stringify(f)});setVerify(true);
 }catch(x){setErr(x.message)}finally{setBusy(false)}};
 const verifyCode=async e=>{e.preventDefault();setErr('');setBusy(true);try{if(resetStage){await api('/password-reset/confirm',{method:'POST',body:JSON.stringify({email:f.email,code,password:f.password})});setResetStage(false);setVerify(false);setMode('signin');setErr('Password updated. Please sign in with your new password.');return;}const d=await api('/verify-email',{method:'POST',body:JSON.stringify({email:f.email,code})});localStorage.setItem('eco_token',d.token);onAuth(d.user)}catch(x){setErr(x.message)}finally{setBusy(false)}};
 const resend=async()=>{setErr('');setBusy(true);try{if(resetStage){await api('/password-reset/request',{method:'POST',body:JSON.stringify({email:f.email})});setErr('A fresh password reset code was requested.')}else{await api('/resend-verification',{method:'POST',body:JSON.stringify({email:f.email})});setErr('A fresh verification code was sent. Check your inbox and spam folder.')}}catch(x){setErr(x.message)}finally{setBusy(false)}};
 return <main className="auth-page"><div className="auth-visual"><span className="eyebrow">WELCOME</span><h1>Make your footprint<br/><em>count.</em></h1><div className="walking-mini">●　 ●　 ●</div><p>Save your answers, see your progress and turn greener habits into a game.</p></div><form className="auth-form" onSubmit={verify?verifyCode:submit}><div className="seg"><button type="button" className={mode==='signin'?'active':''} onClick={()=>{setMode('signin');setVerify(false);setResetStage(false);setErr('')}}>Sign in</button><button type="button" className={mode==='signup'?'active':''} onClick={()=>{setMode('signup');setVerify(false);setResetStage(false);setErr('')}}>Create account</button></div>{verify||resetStage?<><h2>{resetStage?'Reset your password':'Verify your email'}</h2><p className="muted">We sent a 6-digit code to <b>{f.email}</b>. Enter it below to prove you can access this mailbox.</p><Field label="Verification code"><input required inputMode="numeric" pattern="[0-9]{6}" maxLength="6" value={code} onChange={e=>setCode(e.target.value.replace(/\D/g,'').slice(0,6))}/></Field>{resetStage&&<Field label="New password"><input required minLength="8" type="password" value={f.password} onChange={e=>setF({...f,password:e.target.value})}/></Field>}{err&&<div className={err.startsWith('A fresh')||err.startsWith('Password updated')?'success':'error'}>{err}</div>}<button type="submit" className="primary big full" disabled={busy}>{busy?'Verifying…':'Verify email →'}</button><button type="button" className="outline full" onClick={resend} disabled={busy}>Resend code</button></>:<><h2>{mode==='signin'?'Welcome back':mode==='forgot'?'Reset your password':'Create your account'}</h2>{mode==='signup'&&<Field label="Full name"><input required value={f.name} onChange={e=>setF({...f,name:e.target.value})} /></Field>}<Field label="Email"><input required type="email" value={f.email} onChange={e=>setF({...f,email:e.target.value})}/></Field>{mode!=='forgot'&&<Field label="Password"><input required minLength="8" type="password" value={f.password} onChange={e=>setF({...f,password:e.target.value})}/></Field>}{err&&<div className="error">{err}</div>}{mode==='signin'&&<button type="button" className="under" onClick={()=>{setMode('forgot');setErr('')}}>Forgot password?</button>}<button type="submit" className="primary big full" disabled={busy}>{busy?(mode==='signin'?'Signing in…':mode==='forgot'?'Sending reset code…':'Creating account…'):(mode==='signin'?'Sign in':mode==='forgot'?'Send reset code':'Create account')} →</button><small className="muted">New accounts must verify their email. We never treat an email address as valid just because it has the right format.</small></>}</form></main>}
function Field({label,children}){return <label className="field"><span>{label}</span>{children}</label>}

function Form({nav}){
 const [values,setValues]=useState({travel_mode:'Walking',travel_km:0,meals:'Mixed',electricity_kwh:0,shopping:'No',waste:'Some recycled'});
 const [saved,setSaved]=useState(false),[loading,setLoading]=useState(false),[error,setError]=useState(''),[footprint,setFootprint]=useState(null),[existing,setExisting]=useState(false);
 useEffect(()=>{api('/daily').then(d=>{if(d.completed){setValues(d.inputs);setExisting(true);setFootprint(d.footprint)}}).catch(()=>{})},[]);
 const update=(k,v)=>setValues(x=>({...x,[k]:v}));
 const submit=async e=>{e.preventDefault();setLoading(true);setError('');try{const d=await api('/daily',{method:'POST',body:JSON.stringify({inputs:values})});setFootprint(d.footprint);setSaved(true);setExisting(true)}catch(err){setError(err.message)}finally{setLoading(false)}};
 if(saved&&footprint)return <main className="result-page daily-result"><div className="result-orbit">🌱</div><span className="eyebrow">TODAY'S CHECK-IN SAVED</span><h1>{footprint.daily} <small>kg CO₂e</small></h1><p>Your daily estimate is saved. You can edit today's answers whenever you need.</p><div className="result-actions"><button className="outline light-outline" onClick={()=>setSaved(false)}>Edit today's entries</button><button className="primary big" onClick={()=>nav('dashboard')}>View dashboard →</button></div></main>;
 return <main className="quiz-page daily-form"><div className="quiz-top"><div><span className="eyebrow">DAILY ACTIVITY TRACKER</span><h1>{existing?'Update today’s check-in':'Your day, in a few steps'}</h1><p className="muted">Only enter what happened today. Your personal profile is saved separately.</p></div><div className="quiz-percent">6 items</div></div><form className="daily-grid" onSubmit={submit}>
 <section className="daily-question"><span className="q-number">01</span><div><h2>What was your main way of travelling today?</h2><div className="answer-grid compact">{['Car','Motorcycle','Bus','Train','Metro','Bicycle','Walking','Work from home'].map(x=><button type="button" key={x} className={values.travel_mode===x?'answer selected':'answer'} onClick={()=>update('travel_mode',x)}>{x}</button>)}</div></div></section>
 <section className="daily-question"><span className="q-number">02</span><div><h2>How far did you travel using this mode?</h2><div className="inline-input"><input type="number" min="0" max="500" step="0.5" value={values.travel_km} onChange={e=>update('travel_km',e.target.value)}/><span>km</span></div></div></section>
 <section className="daily-question"><span className="q-number">03</span><div><h2>What best describes your meals today?</h2><div className="answer-grid compact">{['Plant-based','Vegetarian','Mixed','Meat-heavy'].map(x=><button type="button" key={x} className={values.meals===x?'answer selected':'answer'} onClick={()=>update('meals',x)}>{x}</button>)}</div></div></section>
 <section className="daily-question"><span className="q-number">04</span><div><h2>Approximately how much electricity did your household use today?</h2><p className="muted">Enter your household estimate in kWh. The estimate is shared across household members.</p><div className="inline-input"><input type="number" min="0" max="100" step="0.1" value={values.electricity_kwh} onChange={e=>update('electricity_kwh',e.target.value)}/><span>kWh</span></div></div></section>
 <section className="daily-question"><span className="q-number">05</span><div><h2>Did you buy anything new today?</h2><div className="answer-grid compact">{['No','Yes'].map(x=><button type="button" key={x} className={values.shopping===x?'answer selected':'answer'} onClick={()=>update('shopping',x)}>{x}</button>)}</div></div></section>
 <section className="daily-question"><span className="q-number">06</span><div><h2>How did you manage your waste today?</h2><div className="answer-grid compact">{['Mostly recycled','Some recycled','Mostly landfill','Not sure'].map(x=><button type="button" key={x} className={values.waste===x?'answer selected':'answer'} onClick={()=>update('waste',x)}>{x}</button>)}</div></div></section>
 {error&&<p className="form-error">{error}</p>}<div className="quiz-actions daily-submit"><span className="muted">You can edit this entry later today.</span><button className="primary big" disabled={loading}>{loading?'Saving…':existing?'Update check-in':'Save daily check-in'} →</button></div>
 </form></main>
}

function Dashboard({nav}){
 const [data,setData]=useState(null),[activity,setActivity]=useState([]),[history,setHistory]=useState([]),[today,setToday]=useState(null),[loadError,setLoadError]=useState('');
 const refresh=()=>Promise.all([api('/me'),api('/activity'),api('/history'),api('/daily')]).then(([m,a,h,d])=>{setData(m);setActivity(a.activity);setHistory(h.history);setToday(d)});
 useEffect(()=>{refresh().catch(e=>setLoadError(e.message))},[]);
 if(!data)return loadError?<LoadFailure message={loadError}/>:<FootprintLoader full/>;
 if(!data.has_profile)return <main className="dashboard"><section className="panel onboarding-card"><span className="eyebrow">WELCOME TO ECOTRACK</span><h1>Let's set up your personal profile.</h1><p>Add a few details once. You can edit them anytime, and we'll use them to make your daily estimates more relevant.</p><button className="primary big" onClick={()=>nav('profile')}>Set up my profile →</button></section></main>;
 const fp=today?.footprint||{daily:0,weekly:0,monthly:0,categories:{}};
 const cats=Object.entries(fp.categories||{}).map(([name,value])=>({name:name[0].toUpperCase()+name.slice(1),value}));
 const trend=history.slice(0,7).reverse().map(x=>({day:new Date(x.date+'T12:00:00').toLocaleDateString(undefined,{weekday:'short'}),v:x.total}));
 const total=history.reduce((n,x)=>n+x.total,0); const todayKey=localDate(); const weekStart=new Date(); weekStart.setDate(weekStart.getDate()-6); const weekKey=`${weekStart.getFullYear()}-${String(weekStart.getMonth()+1).padStart(2,'0')}-${String(weekStart.getDate()).padStart(2,'0')}`; const week=history.filter(x=>x.date>=weekKey&&x.date<=todayKey).reduce((n,x)=>n+x.total,0); const month=history.filter(x=>x.date.slice(0,7)===todayKey.slice(0,7)).reduce((n,x)=>n+x.total,0);
 return <main className="dashboard"><div className="dash-title"><div><span className="eyebrow">YOUR DAILY FOOTPRINT</span><h1>Hello, {data.user.name.split(' ')[0]}.</h1><p>Small daily entries make your progress meaningful.</p></div><button className="primary" onClick={()=>nav('form')}>{today?.completed?'Edit today’s check-in':'Complete today’s check-in'} →</button></div>
 <div className="checkin-banner"><div><b>{today?.completed?'Today’s check-in is complete':'Your daily check-in is waiting'}</b><p>{today?.completed?'Your entry is saved. You can update it anytime today.':'Record a few activities to calculate today’s footprint.'}</p></div><button className="outline" onClick={()=>nav('form')}>{today?.completed?'Edit entry':'Start check-in'}</button></div>
 <div className="metric-grid"><Metric title="Today" value={fp.daily} unit="kg CO₂e"/><Metric title="Last 7 logged days" value={week} unit="kg CO₂e"/><Metric title="This month" value={month} unit="kg CO₂e"/><Metric title="Eco XP" value={data.points||0} unit="points"/></div>
 <div className="dash-columns"><section className="panel"><div className="panel-head"><span className="eyebrow">REAL RECORDED ENTRIES</span><h2>Your recent footprint</h2></div>{trend.length?<ResponsiveContainer width="100%" height={290}><LineChart data={trend}><CartesianGrid strokeDasharray="4 4" opacity={.15}/><XAxis dataKey="day"/><YAxis/><Tooltip/><Line type="monotone" dataKey="v" stroke="#315b38" strokeWidth={4}/></LineChart></ResponsiveContainer>:<p className="muted">Your trend will appear after you save daily check-ins.</p>}</section><section className="panel green-panel"><span className="eyebrow">YOUR NEXT STEP</span><h2>{cats.sort((a,b)=>b.value-a.value)[0]?.name||'Daily habits'} is your biggest signal.</h2><p>Start with one small action. Consistency matters more than perfection.</p><button className="primary" onClick={()=>nav('achievements')}>Open today's missions</button><button className="outline" onClick={()=>nav('insights')}>View insights & reports →</button><div className="streak">🔥 {data.streak||0} day streak</div></section></div>
 <div className="dash-columns"><section className="panel"><div className="panel-head"><span className="eyebrow">TODAY'S BREAKDOWN</span><h2>Where your footprint comes from</h2></div>{cats.length?<ResponsiveContainer width="100%" height={300}><BarChart data={cats}><CartesianGrid strokeDasharray="4 4" opacity={.15}/><XAxis dataKey="name" angle={-18} textAnchor="end" height={65}/><YAxis/><Tooltip/><Bar dataKey="value" fill="#77a95a" radius={[10,10,0,0]}/></BarChart></ResponsiveContainer>:<p className="muted">Complete today's check-in to see your breakdown.</p>}</section><section className="panel"><div className="panel-head"><span className="eyebrow">RECENT ACTIVITY</span><h2>Your green log</h2></div>{activity.slice(0,7).map((x,i)=><div className="activity" key={i}><span>✓</span><div><b>{x.action}</b><small>{new Date(x.created_at).toLocaleString()}</small></div><strong>+{x.points} XP</strong></div>)}{!activity.length&&<p className="muted">Your first activity will appear here.</p>}</section></div>
 <section className="panel history-panel"><div className="panel-head"><span className="eyebrow">ASSESSMENT HISTORY</span><h2>Recent daily records</h2></div>{history.slice(0,10).map(x=><div className="history-row" key={x.date}><span>{new Date(x.date+'T12:00:00').toLocaleDateString(undefined,{day:'numeric',month:'short',year:'numeric'})}</span><b>{x.total.toFixed(2)} kg CO₂e</b></div>)}{!history.length&&<p className="muted">No daily records yet.</p>}</section></main>
}

function Insights(){
 const [d,setD]=useState(null),[planner,setPlanner]=useState([]),[err,setErr]=useState(''),[reduction,setReduction]=useState(15);
 useEffect(()=>{Promise.all([api('/insights'),api('/planner')]).then(([a,b])=>{setD(a);setPlanner(b.planner)}).catch(e=>setErr(e.message))},[]);
 const download=async path=>{try{const r=await fetch(API+path,{headers:{Authorization:'Bearer '+getToken()}});if(!r.ok)throw new Error('Could not create report');const blob=await r.blob();const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=path.includes('pdf')?'carbon-footprint-report.pdf':'carbon-footprint-data.json';a.click();URL.revokeObjectURL(url)}catch(e){setErr(e.message)}};
 if(!d)return err?<LoadFailure message={err}/>:<FootprintLoader full/>;
 const logged=new Set(d.records.map(x=>x.date));const today=new Date();const first=new Date(today.getFullYear(),today.getMonth(),1);const days=new Date(today.getFullYear(),today.getMonth()+1,0).getDate();const offset=first.getDay();
 return <main className="simple-page insights-page"><span className="eyebrow">YOUR PROGRESS, IN CONTEXT</span><h1>Insights & reports.</h1><p className="lead">Comparisons use recorded check-ins only. Missing days are not counted as zero.</p>{err&&<p className="form-error">{err}</p>}
 <div className="metric-grid"><Metric title="This week" value={d.this_week.total_kg} unit={`kg CO₂e · ${d.this_week.logged_days} logged days`}/><Metric title="Previous week" value={d.previous_week.total_kg} unit={`kg CO₂e · ${d.previous_week.logged_days} logged days`}/><Metric title="This month" value={d.this_month.total_kg} unit={`kg CO₂e · ${d.this_month.logged_days} logged days`}/><Metric title="Weekly change" value={d.this_week.change_percent===null?'—':`${d.this_week.change_percent}%`} unit="vs previous week"/></div>
 <section className="panel"><div className="panel-head"><span className="eyebrow">CHECK-IN CALENDAR</span><h2>{today.toLocaleDateString(undefined,{month:'long',year:'numeric'})}</h2></div><div className="calendar-grid">{['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map(x=><b key={x}>{x}</b>)}{Array.from({length:offset},(_,i)=><span key={'blank'+i}/>)}{Array.from({length:days},(_,i)=>{const day=String(i+1).padStart(2,'0'),key=`${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${day}`;return <span key={key} className={logged.has(key)?'calendar-day logged':'calendar-day'} title={logged.has(key)?'Check-in recorded':'No check-in'}>{i+1}{logged.has(key)?' ✓':''}</span>})}</div><p className="muted">Green-marked dates have a saved daily entry.</p></section>
 <section className="panel"><span className="eyebrow">WHAT-IF SIMULATOR</span><h2>Explore a reduction target</h2><p className="muted">A scenario based on your recorded weekly total; it is a planning estimate, not a guaranteed saving.</p><label className="field"><span>Target reduction: {reduction}%</span><input type="range" min="0" max="50" step="5" value={reduction} onChange={e=>setReduction(Number(e.target.value))}/></label><div className="metric-grid"><Metric title="Current logged week" value={d.this_week.total_kg} unit="kg CO₂e"/><Metric title="Scenario total" value={d.this_week.total_kg*(1-reduction/100)} unit="kg CO₂e"/><Metric title="Potential difference" value={d.this_week.total_kg*reduction/100} unit="kg CO₂e"/></div></section>
 <section className="panel"><div className="panel-head"><span className="eyebrow">PERSONALISED REDUCTION PLANNER</span><h2>Start with your biggest categories</h2></div><div className="planner-list">{planner.map((x,i)=><article key={x.category}><span>{String(i+1).padStart(2,'0')}</span><div><b>{x.title}</b><p>{x.action}</p><small>{x.category}</small></div></article>)}</div></section>
 <section className="panel"><span className="eyebrow">TAKE YOUR DATA WITH YOU</span><h2>Download your records</h2><p className="muted">JSON contains your account profile, daily inputs, estimates and reward activity. PDF contains a simple daily-estimate report.</p><div className="hero-cta"><button className="primary" onClick={()=>download('/export')}>Export my data (JSON) ↓</button><button className="outline" onClick={()=>download('/report.pdf')}>Download PDF report ↓</button></div></section>
 </main>
}

function Metric({title,value,unit}){const n=Number(value);const shown=typeof value==='string'&&!Number.isFinite(n)?value:(Number.isFinite(n)?n.toFixed(1):'—');return <div className="metric"><span>{title}</span><strong>{shown}</strong><em>{unit}</em><small>personal estimate</small></div>}

function Achievements(){const [data,setData]=useState(null),[lb,setLb]=useState([]),[loadError,setLoadError]=useState('');useEffect(() => {
  let cancelled = false;

  async function loadAchievements() {
    try {
      const [m, l] = await Promise.all([
        api('/me'),
        api('/leaderboard')
      ]);

      if (cancelled) return;

      setData(m);
      setLb(l.leaderboard || []);
    } catch (e) {
      if (!cancelled) {
        setLoadError(e.message);
      }
    }
  }

  loadAchievements();

  return () => {
    cancelled = true;
  };
}, []);if(!data)return loadError?<LoadFailure message={loadError}/>:<FootprintLoader full/>;const badges=[['🌱','First Sprout','Complete your first footprint check-in',true],['🚲','Green Commuter','Build low-carbon travel habits',data.points>=75],['⚡','Streak Spark','Keep a 3-day streak',data.streak>=3],['🥗','Plant Plate','Choose a plant-forward action',data.points>=125],['🏆','Eco Champion','Reach 500 XP',data.points>=500],['🌍','Planet Pal','Complete 7 missions',data.points>=700]];return <main className="ach-page"><section className="reward-hero"><div><span className="eyebrow">YOUR GREEN ARCADE</span><h1>Good choices deserve<br/><em>confetti.</em></h1><p>Every little action can move your score. Collect XP, keep your streak alive and unlock your badge cabinet.</p></div><div className="xp-orb"><b>{data.points||0}</b><span>XP</span><strong>🔥 {data.streak||0} days</strong></div></section><section className="panel mission-panel"><div className="panel-head"><span className="eyebrow">TODAY'S MISSIONS</span><h2>Pick a power-up</h2></div><div className="missions"><Mission emoji="🚶" title="Walk a short trip" xp={40}/><Mission emoji="🥬" title="Choose a greener meal" xp={30}/><Mission emoji="💡" title="Power down for an hour" xp={20}/></div></section><div className="reward-columns"><section className="panel"><div className="panel-head"><span className="eyebrow">BADGE CABINET</span><h2>Collect them all</h2></div><div className="badges">{badges.map(b=><div className={b[3]?'badge unlocked':'badge'} key={b[1]}><div className="badge-icon">{b[0]}</div><b>{b[1]}</b><small>{b[2]}</small><span>{b[3]?'UNLOCKED':'LOCKED'}</span></div>)}</div></section><section className="panel"><div className="panel-head"><span className="eyebrow">LEADERBOARD</span><h2>Friendly competition</h2></div>{lb.map((x,i)=><div className="leader" key={i}><span>{i+1}</span><b>{x.name}</b><small>🔥 {x.streak}d</small><strong>{x.points} XP</strong></div>)}</section></div></main>}
function Mission({ emoji, title, xp }) {
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function checkMission() {
      try {
        const data = await api('/activity');

        if (!cancelled) {
          setDone(
            data.activity.some(
              a =>
                a.action === title &&
                localDateFromUtc(a.created_at) === localDate()
            )
          );
        }
      } catch {
        // Activity status can be checked again when the page is reopened.
      }
    }

    checkMission();

    return () => {
      cancelled = true;
    };
  }, [title]);

  const click = async () => {
    if (done || busy) return;

    setBusy(true);
    setError('');

    try {
      await api('/goal', {
        method: 'POST',
        body: JSON.stringify({ action: title })
      });

      setDone(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      className={done ? 'mission done' : 'mission'}
      onClick={click}
      disabled={busy || done}
    >
      <span className="mission-emoji">{done ? '✓' : emoji}</span>

      <div>
        <b>{title}</b>
        <small>
          {error ||
            (done
              ? 'Completed — nice work!'
              : busy
              ? 'Saving…'
              : 'I completed this action (self-reported)')}
        </small>
      </div>

      <strong>{done ? '✓' : `+${xp}`}</strong>
    </button>
  );
}
function Profile(){
 const [m,setM]=useState(null),[form,setForm]=useState({}),[editing,setEditing]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
useEffect(() => {
  let cancelled = false;

  async function loadProfile() {
    try {
      const x = await api('/me');
      if (cancelled) return;

      setM(x);
      setForm({
        city: '',
        home_type: 'Apartment',
        household_size: 1,
        car_occupants: 1,
        transport_mode: 'Walking',
        cooking_source: 'LPG',
        diet_type: 'Vegetarian',
        renewable_energy: 'Not sure',
        ...(x.profile || {})
      });
    } catch (e) {
      if (!cancelled) setError(e.message);
    }
  }

  loadProfile();
  return () => { cancelled = true; };
}, []);
 const update=(k,v)=>setForm(x=>({...x,[k]:v}));
 const save=async e=>{e.preventDefault();setBusy(true);setError('');setMessage('');try{const d=await api('/profile',{method:'PUT',body:JSON.stringify(form)});setForm(d.profile);setM(x=>({...x,profile:d.profile,has_profile:true}));setEditing(false);setMessage('Your personal profile has been updated. Future daily estimates will use these details.')}catch(err){setError(err.message)}finally{setBusy(false)}};
 if(!m)return error?<LoadFailure message={error}/>:<FootprintLoader full/>;
 return <main className="profile-page"><div className="profile-banner"><div className="avatar">{m.user.name[0]}</div><div><span className="eyebrow">YOUR ECO PROFILE</span><h1>{m.user.name}</h1><p>{m.user.email}</p></div></div><div className="profile-columns"><section className="panel"><span className="eyebrow">PROGRESS</span><div className="profile-metrics"><Metric title="XP" value={m.points} unit="points"/><Metric title="Streak" value={m.streak} unit="days"/></div></section><section className="panel profile-editor"><div className="profile-section-head"><div><span className="eyebrow">LIFESTYLE INFORMATION</span><h2>Personal profile</h2><p className="muted">Complete once and edit whenever your routine changes.</p></div><button className="outline" onClick={()=>setEditing(!editing)}>{editing?'Cancel':'Edit profile'}</button></div>
 {message&&<p className="success-message">{message}</p>}{error&&<p className="form-error">{error}</p>}
 {editing||!m.has_profile?<form onSubmit={save} className="profile-form">{profileFields.map(f=><Field key={f.id} label={f.label}>{f.options?<select value={form[f.id]||''} onChange={e=>update(f.id,e.target.value)} required><option value="">Select an option</option>{f.options.map(o=><option key={o}>{o}</option>)}</select>:<input type={f.type||'text'} min={f.type==='number'?1:undefined} max={f.id==='car_occupants'?8:f.type==='number'?20:undefined} placeholder={f.placeholder||''} value={form[f.id]??''} onChange={e=>update(f.id,e.target.value)} required={!f.optional}/>}</Field>)}<button className="primary big" disabled={busy}>{busy?'Saving…':'Save personal profile'} →</button></form>:<div className="answers">{profileFields.map(f=><div key={f.id}><span>{f.label}</span><b>{String(form[f.id]??'Not provided')}</b></div>)}</div>}
 </section><section className="panel account-controls"><span className="eyebrow">ACCOUNT & PRIVACY</span><h2>Your data controls</h2><p className="muted">Leaderboard participation is optional. Export your data from Insights before deleting your account.</p><PrivacyControls/><EmailNotificationsControl/><ThemeControl/><DeleteAccount/></section></div></main>
}

function PrivacyControls(){const [on,setOn]=useState(false),[msg,setMsg]=useState('');useEffect(() => {
  let cancelled = false;

  api('/me')
    .then(x => {
      if (!cancelled) setOn(!!x.leaderboard_opt_in);
    })
    .catch(() => {});

  return () => { cancelled = true; };
}, []);const save=async v=>{setOn(v);try{await api('/privacy',{method:'PUT',body:JSON.stringify({leaderboard_opt_in:v})});setMsg('Privacy preference saved.')}catch(e){setMsg(e.message)}};return <div className="control-row"><div><b>Appear on public leaderboard</b><p className="muted">Your name and XP are visible only if you opt in.</p></div><button className="outline" onClick={()=>save(!on)}>{on?'Opt out':'Opt in'}</button>{msg&&<small>{msg}</small>}</div>}
function EmailNotificationsControl(){const [weekly,setWeekly]=useState(false),[daily,setDaily]=useState(false),[msg,setMsg]=useState('');useEffect(() => {
  let cancelled = false;

  api('/me')
    .then(x => {
      if (cancelled) return;
      setWeekly(!!x.weekly_digest_opt_in);
      setDaily(!!x.daily_reminder_opt_in);
    })
    .catch(() => {});

  return () => { cancelled = true; };
}, []);const save=async(w,d)=>{try{const x=await api('/notifications',{method:'PUT',body:JSON.stringify({weekly_digest_opt_in:w,daily_reminder_opt_in:d})});setWeekly(x.weekly_digest_opt_in);setDaily(x.daily_reminder_opt_in);setMsg('Preferences saved. Email requires SMTP and the scheduled backend jobs.')}catch(e){setMsg(e.message)}};return <div className="notification-controls"><div className="control-row"><div><b>Daily check-in reminder</b><p className="muted">Receive a reminder if you have not logged today.</p></div><button className="outline" onClick={()=>save(!daily,weekly)}>{daily?'Turn off':'Turn on'}</button></div><div className="control-row"><div><b>Weekly email summary</b><p className="muted">Receive a recap of your saved activity and estimates.</p></div><button className="outline" onClick={()=>save(daily,!weekly)}>{weekly?'Turn off':'Turn on'}</button></div>{msg&&<small>{msg}</small>}</div>}

function Community() {
  const [items, setItems] = useState([]);
  const [resources, setResources] = useState([]);
  const [city, setCity] = useState('');
  const [qr, setQr] = useState('');
  const [message, setMessage] = useState('');
  const [question, setQuestion] = useState('');
  const [reply, setReply] = useState('');
  const [busy, setBusy] = useState(false);

  const load = async () => {
    try {
      const [challenges, profile] = await Promise.all([
        api('/challenges'),
        api('/me')
      ]);

      setItems(challenges.challenges || []);
      setCity(profile.profile?.city || 'India');
    } catch (e) {
      setMessage(e.message);
    }
  };

  useEffect(() => {
    let cancelled = false;

    async function loadCommunity() {
      try {
        const [challenges, profile] = await Promise.all([
          api('/challenges'),
          api('/me')
        ]);

        if (cancelled) return;

        setItems(challenges.challenges || []);
        setCity(profile.profile?.city || 'India');
      } catch (e) {
        if (!cancelled) setMessage(e.message);
      }
    }

    loadCommunity();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadResources() {
      if (!city) return;

      try {
        const data = await api(
          '/resources?city=' + encodeURIComponent(city)
        );

        if (!cancelled) {
          setResources(data.resources || []);
        }
      } catch {
        if (!cancelled) setResources([]);
      }
    }

    loadResources();

    return () => {
      cancelled = true;
    };
  }, [city]);

  const join = async id => {
    try {
      await api('/challenges/' + id + '/join', {
        method: 'POST'
      });

      setMessage(
        'You joined the challenge. Save qualifying daily check-ins to make progress.'
      );

      await load();
    } catch (e) {
      setMessage(e.message);
    }
  };

  const showQr = async id => {
    try {
      const response = await fetch(
        API + '/challenges/' + id + '/qr',
        {
          headers: {
            Authorization: 'Bearer ' + getToken()
          }
        }
      );

      if (!response.ok) {
        throw new Error('Could not create QR code.');
      }

      const blob = await response.blob();
      setQr(URL.createObjectURL(blob));
    } catch (e) {
      setMessage(e.message);
    }
  };

  const ask = async e => {
    e.preventDefault();

    setBusy(true);
    setReply('');

    try {
      const data = await api('/coach', {
        method: 'POST',
        body: JSON.stringify({ question })
      });

      setReply(data.reply);
    } catch (e) {
      setReply(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="simple-page community-page">
      <span className="eyebrow">TAKE ACTION TOGETHER</span>
      <h1>Community & local action.</h1>

      <p className="lead">
        Join self-reported challenges, get practical habit ideas and find
        local sustainability services. Challenge progress is based on your
        saved check-ins.
      </p>

      {message && <p className="success-message">{message}</p>}

      <section className="panel">
        <span className="eyebrow">COMMUNITY CHALLENGES</span>
        <h2>Small actions, shared momentum.</h2>

        <div className="community-grid">
          {items.map(x => (
            <article className="challenge-card" key={x.id}>
              <h3>{x.title}</h3>
              <p>{x.description}</p>

              <div className="challenge-progress">
                <b>
                  {x.progress_days || 0} / {x.target_days} qualifying days
                </b>
                <span>{x.points} XP</span>
              </div>

              <div className="challenge-actions">
                {x.completed_at ? (
                  <strong>Completed ✓</strong>
                ) : x.joined_at ? (
                  <strong>Joined · keep logging</strong>
                ) : (
                  <button
                    className="primary"
                    onClick={() => join(x.id)}
                  >
                    Join challenge
                  </button>
                )}

                <button
                  className="outline"
                  onClick={() => showQr(x.id)}
                >
                  Get QR code
                </button>
              </div>
            </article>
          ))}
        </div>

        {qr && (
          <div className="qr-panel">
            <img
              src={qr}
              alt="QR code linking to the selected community challenge"
            />

            <button
              className="outline"
              onClick={() => {
                URL.revokeObjectURL(qr);
                setQr('');
              }}
            >
              Close QR
            </button>
          </div>
        )}

        <p className="muted">
          Challenge actions are self-reported and verified only against
          your saved questionnaire entries, not by sensors or third parties.
        </p>
      </section>

      <section className="panel">
        <span className="eyebrow">ECO COACH</span>
        <h2>Need a practical next step?</h2>

        <p className="muted">
          This built-in coach uses simple rules and your recent logged
          categories. It is not a generative AI service.
        </p>

        <form className="coach-form" onSubmit={ask}>
          <input
            value={question}
            onChange={e => setQuestion(e.target.value)}
            placeholder="e.g. How can I reduce my footprint?"
            maxLength="500"
            required
          />

          <button className="primary" disabled={busy}>
            {busy ? 'Thinking…' : 'Ask Eco Coach'}
          </button>
        </form>

        {reply && <p className="coach-reply">{reply}</p>}
      </section>

      <section className="panel">
        <span className="eyebrow">LOCAL SUSTAINABILITY DIRECTORY</span>
        <h2>Explore around {city || 'your city'}.</h2>

        <p className="muted">
          These links open live map searches. Check provider details,
          opening hours and accepted materials before visiting.
        </p>

        <div className="resource-grid">
          {resources.map(x => (
            <a
              className="resource-card"
              href={x.url}
              target="_blank"
              rel="noreferrer"
              key={x.title}
            >
              <b>{x.title} ↗</b>
              <p>{x.description}</p>
            </a>
          ))}
        </div>
      </section>
    </main>
  );
}

function ThemeControl(){const [dark,setDark]=useState(localStorage.getItem('eco_theme')==='dark');useEffect(()=>{document.documentElement.classList.toggle('dark-theme',dark);localStorage.setItem('eco_theme',dark?'dark':'light')},[dark]);return <div className="control-row"><div><b>Appearance</b><p className="muted">Switch between light and dark themes.</p></div><button className="outline" onClick={()=>setDark(!dark)}>{dark?'Use light mode':'Use dark mode'}</button></div>}
function DeleteAccount(){const [confirm,setConfirm]=useState(''),[msg,setMsg]=useState('');const remove=async()=>{if(confirm!=='DELETE'){setMsg('Type DELETE exactly to confirm.');return}if(!window.confirm('This permanently deletes your account and all associated records. Continue?'))return;try{await api('/account',{method:'DELETE',body:JSON.stringify({confirm})});localStorage.removeItem('eco_token');location.hash='home';location.reload()}catch(e){setMsg(e.message)}};return <div className="delete-zone"><b>Delete account permanently</b><p className="muted">This removes your profile, daily history, reward activity and account. This cannot be undone.</p><input aria-label="Type DELETE to confirm" placeholder="Type DELETE" value={confirm} onChange={e=>setConfirm(e.target.value)}/><button className="danger-button" onClick={remove}>Delete my account</button>{msg&&<small>{msg}</small>}</div>}

function Contact(){const [f,setF]=useState({name:'',email:'',message:''}),[done,setDone]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false);const submit=async e=>{e.preventDefault();setBusy(true);setError('');try{await api('/contact',{method:'POST',body:JSON.stringify(f)});setDone(true)}catch(e){setError(e.message)}finally{setBusy(false)}};return <main className="simple-page contact-layout"><div><span className="eyebrow">CONTACT US</span><h1>Have a question?<br/><em>Let's talk.</em></h1><p>Tell us what you would improve, what confused you, or what green feature you want next.</p><div className="contact-details"><span>✉ Use the contact form to reach the project team</span><span>⌂ Student project · India</span><span>Messages are saved in the project database</span></div></div><form className="panel contact-form" onSubmit={submit}>{error&&<p className="form-error">{error}</p>}{done?<div className="success"><div>✓</div><h2>Message received.</h2><p>Thanks — your note has been saved for the project team. Email delivery is available only when SMTP is configured.</p></div>:<><Field label="Name"><input required value={f.name} onChange={e=>setF({...f,name:e.target.value})}/></Field><Field label="Email"><input required type="email" value={f.email} onChange={e=>setF({...f,email:e.target.value})}/></Field><Field label="Message"><textarea required rows="7" value={f.message} onChange={e=>setF({...f,message:e.target.value})}/></Field><button className="primary big" disabled={busy}>{busy?'Saving…':'Send message →'}</button></>}</form></main>}
function FAQ(){return <main className="simple-page"><span className="eyebrow">FAQS</span><h1>Questions, answered.</h1><p className="lead">A quick guide to the calculator, your data and the rewards system.</p><div className="faq-list">{faq.map(([q,a])=><details key={q}><summary>{q}<span>+</span></summary><p>{a}</p></details>)}</div></main>}
function Legal({title,children}){return <main className="legal-page"><span className="eyebrow">CARBON FOOTPRINT TRACKER</span><h1>{title}</h1><p className="legal-date">Last updated: 23 November 2026</p><article className="legal-copy">{children}<h3>Questions</h3><p>If you need clarification, please use the Contact us page.</p></article></main>}
function CookieSettings(){return <main className="simple-page"><span className="eyebrow">COOKIE SETTINGS</span><h1>Your privacy, your choice.</h1><p className="lead">This project does not currently run third-party analytics or advertising trackers.</p><section className="cookie-card"><div><h3>Essential browser storage</h3><p>Authentication uses a sign-in token stored in this browser. Theme preference is stored locally. These are required for the current application experience.</p></div><strong>Required</strong></section><section className="cookie-card"><div><h3>Optional analytics</h3><p>No analytics service is connected, so no analytics preference is being collected.</p></div><strong>Not active</strong></section></main>}
function Protected({me,children,nav}){if(!me){return <main className="simple-page"><span className="eyebrow">MEMBERS AREA</span><h1>Please sign in first.</h1><button className="primary big" onClick={()=>nav('auth')}>Sign in →</button></main>}return children}
function Footer({nav}){return <footer><div><button className="brand footer-brand" onClick={()=>nav('home')}><span className="brand-mark">☘</span><span><b>Carbon Footprint</b><small>TRACK • REDUCE • REWARD</small></span></button><p>Understand your footprint. Make small changes. Build momentum.</p></div><div className="footer-links"><button onClick={()=>nav('faq')}>FAQs</button><button onClick={()=>nav('contact')}>Contact us</button><button onClick={()=>nav('terms')}>Terms & conditions</button><button onClick={()=>nav('privacy')}>Privacy & data protection</button><button onClick={()=>nav('cookies')}>Cookie Settings</button></div><small>© {new Date().getFullYear()} Carbon Footprint Tracker</small></footer>}

createRoot(document.getElementById('root')).render(<App/>);
