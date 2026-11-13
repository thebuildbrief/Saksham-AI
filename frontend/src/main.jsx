import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, ArrowLeft, ArrowRight, BarChart3, BookOpen, BrainCircuit, Briefcase, Check, Code2, FileText, LoaderCircle, LogOut, Menu, Settings as SettingsIcon, ShieldCheck, Sparkles, Video, X } from 'lucide-react';
import { api, auth } from './api';
import './style.css';

const routeFor = (path) => ['coding', 'interviews', 'resumes', 'analytics', 'roadmap', 'companies', 'settings'].includes(path.split('/')[1]) ? path.split('/')[1] : 'overview';
const navItems = [
  ['overview', 'Overview', Sparkles], ['interviews', 'Mock interviews', Video], ['coding', 'Coding practice', Code2],
  ['resumes', 'Resume coach', FileText], ['roadmap', 'Roadmap', BookOpen], ['analytics', 'Progress', BarChart3],
  ['companies', 'Companies', Briefcase], ['settings', 'Settings', SettingsIcon],
];

function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('saksham_token') || '');
  const [user, setUser] = useState(null), [checking, setChecking] = useState(Boolean(sessionStorage.getItem('saksham_token')));
  const [mode, setMode] = useState(window.location.pathname === '/register' ? 'register' : 'login');
  const [tab, setTab] = useState(() => routeFor(window.location.pathname));
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [notice, setNotice] = useState(''), [mobile, setMobile] = useState(false);
  const [problems, setProblems] = useState([]), [selected, setSelected] = useState(''), [detail, setDetail] = useState(null), [language, setLanguage] = useState('python'), [code, setCode] = useState(''), [result, setResult] = useState(null);
  const [interviews, setInterviews] = useState([]), [currentInterview, setCurrentInterview] = useState(null), [role, setRole] = useState('Software Engineer'), [interviewType, setInterviewType] = useState('behavioral'), [answer, setAnswer] = useState('');
  const [resumes, setResumes] = useState([]), [resumeFeedback, setResumeFeedback] = useState('');
  const [analytics, setAnalytics] = useState(null), [roadmap, setRoadmap] = useState(null), [companies, setCompanies] = useState([]), [settings, setSettings] = useState({});

  const navigate = (page) => {
    const path = page === 'overview' ? '/dashboard' : `/${page}`;
    if (window.location.pathname !== path) window.history.pushState({}, '', path);
    setTab(page); setMobile(false); setError(''); setNotice('');
    if (page !== 'coding') { setSelected(''); setDetail(null); }
    if (page !== 'interviews') setCurrentInterview(null);
  };
  useEffect(() => {
    const sync = () => { setTab(routeFor(window.location.pathname)); setMode(window.location.pathname === '/register' ? 'register' : 'login'); };
    window.addEventListener('popstate', sync);
    return () => window.removeEventListener('popstate', sync);
  }, []);
  useEffect(() => {
    if (!token) { setChecking(false); return; }
    setChecking(true);
    auth.me(token).then(setUser).catch(() => { sessionStorage.removeItem('saksham_token'); setToken(''); setUser(null); }).finally(() => setChecking(false));
  }, [token]);
  useEffect(() => {
    if (!user) return;
    const load = async (path, setter) => { try { setter(await api(path, { token })); } catch (e) { setError(e.message); } };
    if (tab === 'coding') load('/coding/problems', (data) => setProblems(Array.isArray(data) ? data : []));
    if (tab === 'interviews') load('/interviews', setInterviews);
    if (tab === 'resumes') load('/resumes', setResumes);
    if (tab === 'analytics') load('/analytics/overview', setAnalytics);
    if (tab === 'roadmap') load('/roadmaps', setRoadmap);
    if (tab === 'companies') load('/companies', setCompanies);
    if (tab === 'settings') load('/settings', (data) => setSettings(data.settings || {}));
    if (tab === 'overview') load('/analytics/overview', setAnalytics);
  }, [user, tab, token]);
  useEffect(() => {
    if (!selected || !token) return;
    api(`/coding/problems/${selected}`, { token }).then((problem) => { setDetail(problem); setCode(problem.starter_code?.[language] || ''); setResult(null); }).catch((e) => setError(e.message));
  }, [selected, token]);

  const submitAuth = async (event) => {
    event.preventDefault(); setBusy(true); setError('');
    const form = new FormData(event.currentTarget);
    try {
      const response = mode === 'login'
        ? await auth.login(form.get('email'), form.get('password'))
        : await auth.register(form.get('name'), form.get('email'), form.get('password'));
      sessionStorage.setItem('saksham_token', response.access_token); setUser(response.user); setToken(response.access_token); navigate('overview');
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const signout = () => { sessionStorage.removeItem('saksham_token'); setToken(''); setUser(null); setMode('login'); window.history.pushState({}, '', '/login'); };
  const execute = async () => {
    setBusy(true); setError(''); setResult(null);
    try { setResult(await api('/coding/execute', { token, method: 'POST', body: JSON.stringify({ problem_id: selected, language, code, custom_input: '' }) })); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const startInterview = async (event) => {
    event.preventDefault(); setBusy(true); setError('');
    try { const data = await api('/interviews', { token, method: 'POST', body: JSON.stringify({ role, interview_type: interviewType, difficulty: 'medium' }) }); setCurrentInterview(data); setInterviews((items) => [data, ...items]); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const sendAnswer = async (event) => {
    event.preventDefault(); if (!currentInterview || !answer.trim()) return;
    setBusy(true); setError('');
    try { const data = await api(`/interviews/${currentInterview.id}/turns`, { token, method: 'POST', body: JSON.stringify({ content: answer }) }); setCurrentInterview(data); setAnswer(''); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const finishInterview = async () => {
    if (!currentInterview) return;
    setBusy(true);
    try { const data = await api(`/interviews/${currentInterview.id}/finish`, { token, method: 'POST' }); setCurrentInterview(data); setInterviews((items) => items.map((item) => item.id === data.id ? data : item)); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const evaluateInterview = async () => {
    if (!currentInterview) return;
    setBusy(true); setError('');
    try { const data = await api(`/evaluations/${currentInterview.id}`, { token, method: 'POST' }); setNotice(`Feedback saved — overall score ${data.total_score}/100. ${data.summary}`); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const uploadResume = async (event) => {
    event.preventDefault(); const formElement = event.currentTarget; const file = new FormData(formElement).get('file');
    if (!file || !file.size) return;
    setBusy(true); setError(''); setResumeFeedback('');
    try { const data = await api('/resumes', { token, method: 'POST', body: (() => { const form = new FormData(); form.append('file', file); return form; })() }); setResumes((items) => [data, ...items]); formElement.reset(); setNotice('Resume uploaded securely.'); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const analyzeResume = async (id) => {
    setBusy(true); setError('');
    try { const data = await api(`/resumes/${id}/analyze`, { token, method: 'POST' }); setResumeFeedback(data.feedback); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const downloadResume = async (resume) => {
    setBusy(true); setError('');
    try {
      const response = await fetch(`${(import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')}/api/v1/resumes/${resume.id}/download`, { headers: { Authorization: `Bearer ${token}` } });
      if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || 'Could not download resume');
      const url = URL.createObjectURL(await response.blob()); const anchor = document.createElement('a'); anchor.href = url; anchor.download = resume.filename; anchor.click(); URL.revokeObjectURL(url);
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  };
  const saveSettings = async (event) => {
    event.preventDefault(); setBusy(true); setError('');
    const form = new FormData(event.currentTarget);
    const values = { theme: form.get('theme'), language: form.get('language'), email_notifications: form.get('email_notifications') === 'on', practice_reminders: form.get('practice_reminders') === 'on', weekly_goal: Number(form.get('weekly_goal')) };
    try { const data = await api('/settings', { token, method: 'PATCH', body: JSON.stringify({ values }) }); setSettings(data.settings); setNotice('Preferences saved.'); }
    catch (e) { setError(e.message); } finally { setBusy(false); }
  };

  if (checking) return <div className="loading-screen"><LoaderCircle className="spin"/> Loading your workspace…</div>;
  if (!user) return <div className="auth-shell"><div className="auth-art"><div className="brand"><span className="brand-icon"><BrainCircuit size={22}/></span> saksham<span className="brand-ai">.ai</span></div><div className="art-copy"><div className="pill"><Sparkles size={14}/> YOUR NEXT CHAPTER STARTS HERE</div><h1>Walk into every interview <em>ready.</em></h1><p>Build confidence through focused practice, thoughtful feedback, and a little progress every day.</p><div className="art-foot"><ShieldCheck size={16}/> Your practice space, built around you</div></div><div className="orb orb-a"/><div className="orb orb-b"/></div><div className="auth-side"><form className="auth-card" onSubmit={submitAuth}><div className="mobile-brand"><BrainCircuit/> Saksham AI</div><div className="eyebrow">{mode === 'login' ? 'WELCOME BACK' : 'LET’S GET STARTED'}</div><h2>{mode === 'login' ? 'Good to see you.' : 'Create your account.'}</h2><p className="muted">{mode === 'login' ? 'Sign in and pick up where you left off.' : 'A few details and your practice journey begins.'}</p>{mode === 'register' && <label>Your name<input name="name" autoComplete="name" required placeholder="Alex Johnson"/></label>}<label>Email address<input name="email" type="email" autoComplete="email" required placeholder="you@example.com"/></label><label>Password<input name="password" type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} minLength={mode === 'register' ? 12 : 1} required placeholder="••••••••••••"/></label>{error && <div className="error">{error}</div>}<button className="primary full" disabled={busy}>{busy ? <LoaderCircle className="spin" size={18}/> : mode === 'login' ? 'Sign in' : 'Create account'} {!busy && <ArrowRight size={17}/>}</button><div className="switch">{mode === 'login' ? 'New to Saksham?' : 'Already have an account?'} <button type="button" onClick={() => { const next = mode === 'login' ? 'register' : 'login'; setMode(next); setError(''); window.history.pushState({}, '', next === 'register' ? '/register' : '/login'); }}>{mode === 'login' ? 'Create an account' : 'Sign in'}</button></div><div className="secure-note"><ShieldCheck size={15}/> Your information stays private and secure.</div></form><div className="auth-bottom">MADE FOR YOUR NEXT BIG MOMENT <span>•</span> SAKSHAM AI</div></div></div>;

  const pageTitle = navItems.find(([id]) => id === tab)?.[1] || 'Overview';
  return <div className="app"><aside className={`sidebar ${mobile ? 'show' : ''}`}><div className="brand"><span className="brand-icon"><BrainCircuit size={22}/></span> saksham<span className="brand-ai">.ai</span><button className="mobile-close" onClick={() => setMobile(false)}><X/></button></div><div className="workspace-label">WORKSPACE</div>{navItems.map(([id, label, Icon]) => <button key={id} className={`navitem ${tab === id ? 'active' : ''}`} onClick={() => navigate(id)}><Icon size={17}/>{label}</button>)}<div className="side-bottom"><div className="user-card"><div className="avatar">{user.full_name?.[0]?.toUpperCase() || 'S'}</div><div className="user-meta"><b>{user.full_name}</b><span>{user.email}</span></div><button className="icon-btn" title="Sign out" onClick={signout}><LogOut size={17}/></button></div><div className="side-caption">A calmer way to get interview ready.</div></div></aside>{mobile && <div className="scrim" onClick={() => setMobile(false)}/>}<main className="main"><header className="topbar"><button className="mobile-menu" onClick={() => setMobile(true)}><Menu/></button><span className="crumb">Workspace <b>/</b> {pageTitle}</span><div className="top-right"><span className="online"><i/> Connected</span><div className="avatar small">{user.full_name?.[0]?.toUpperCase()}</div></div></header><section className="content">{error && <div className="error banner">{error}</div>}{notice && <div className="notice banner"><Check size={15}/>{notice}</div>}
    {tab === 'overview' && <><div className="welcome"><div><div className="eyebrow">YOUR PRACTICE SPACE</div><h1>Hi, {user.full_name?.split(' ')[0] || 'there'} <span className="wave">✳</span></h1><p>Small, steady practice makes a real difference. What would you like to work on?</p></div><div className="welcome-icon"><BrainCircuit size={37}/></div></div><div className="section-head"><div><h2>Pick up a skill</h2><p className="muted">Choose a focused practice session.</p></div></div><div className="feature-grid"><button className="feature-card code-card" onClick={() => navigate('coding')}><div className="feature-icon"><Code2 size={21}/></div><div className="feature-label">TECHNICAL PRACTICE</div><h3>Coding challenges</h3><p>Work through curated problems at your own pace.</p><span className="feature-link">Explore challenges <ArrowRight size={16}/></span><div className="card-decoration">&lt;/&gt;</div></button><button className="feature-card interview-card" onClick={() => navigate('interviews')}><div className="feature-icon"><Video size={21}/></div><div className="feature-label">CONVERSATION PRACTICE</div><h3>Mock interviews</h3><p>Practice realistic questions and get constructive feedback.</p><span className="feature-link">Start an interview <ArrowRight size={16}/></span></button><button className="feature-card" onClick={() => navigate('resumes')}><div className="feature-icon"><FileText size={21}/></div><div className="feature-label">CAREER MATERIALS</div><h3>Resume coach</h3><p>Upload a resume privately and receive focused suggestions.</p><span className="feature-link">Review your resume <ArrowRight size={16}/></span></button><button className="feature-card interview-card" onClick={() => navigate('roadmap')}><div className="feature-icon"><BookOpen size={21}/></div><div className="feature-label">YOUR NEXT STEP</div><h3>Practice roadmap</h3><p>Keep a steady pace with a role-focused plan.</p><span className="feature-link">View roadmap <ArrowRight size={16}/></span></button></div><div className="lower-grid"><div className="panel"><div className="panel-title"><div><h3>Your progress</h3><p className="muted">Based on completed activity</p></div><button className="round-arrow" onClick={() => navigate('analytics')}><ArrowRight size={17}/></button></div><div className="metric-row"><Metric label="INTERVIEWS" value={analytics?.interviews ?? '—'}/><Metric label="CODE SUBMISSIONS" value={analytics?.coding_submissions ?? '—'}/><Metric label="RESUMES" value={analytics?.resumes ?? '—'}/></div></div></div></>}
    {tab === 'coding' && <><div className="practice-head"><div><div className="eyebrow">TECHNICAL PRACTICE</div><h1>Coding challenges</h1><p className="muted">Build fluency one problem at a time.</p></div><span className="count-chip">{problems.length} PROBLEMS</span></div><div className="practice-layout"><div className="problem-list panel"><div className="list-heading">PROBLEM LIBRARY</div>{problems.map((p) => <button key={p.id} className={`problem-row ${selected === p.id ? 'chosen' : ''}`} onClick={() => setSelected(p.id)}><div><b>{p.title}</b><span>{p.category || 'General'}</span></div><span className={`difficulty ${(p.difficulty || '').toLowerCase()}`}>{p.difficulty}</span></button>)}{!problems.length && <p className="empty">{error ? 'Could not load problems.' : 'Loading practice problems…'}</p>}</div><div className="editor-panel panel">{detail ? <><div className="problem-title"><div><div className="eyebrow">{detail.category || 'CHALLENGE'}</div><h2>{detail.title}</h2></div><span className={`difficulty ${(detail.difficulty || '').toLowerCase()}`}>{detail.difficulty}</span></div><div className="problem-description">{detail.description}</div><div className="editor-toolbar"><span>YOUR SOLUTION</span><select value={language} onChange={(e) => { setLanguage(e.target.value); setCode(detail.starter_code?.[e.target.value] || ''); }}><option value="python">Python</option><option value="javascript">JavaScript</option><option value="cpp">C++</option><option value="java">Java</option></select></div><textarea className="code-editor" spellCheck="false" value={code} onChange={(e) => setCode(e.target.value)} aria-label="Source code"/><div className="editor-footer"><span>Run against the challenge test cases</span><button className="primary" disabled={busy || !code.trim()} onClick={execute}>{busy ? <LoaderCircle className="spin" size={16}/> : <Code2 size={16}/>} Run code</button></div>{result && <div className={`result ${(result.status || '').toLowerCase() === 'accepted' ? 'success' : ''}`}><b>{result.status}</b><span>{result.passed_tests} of {result.total_tests} tests passed · {result.execution_time_ms} ms</span></div>}</> : <div className="select-prompt"><div className="feature-icon"><Code2/></div><h3>Choose a challenge</h3><p>Select a problem from the library to see its description and start coding.</p></div>}</div></div></>}
    {tab === 'interviews' && <><div className="practice-head"><div><div className="eyebrow">CONVERSATION PRACTICE</div><h1>Mock interviews</h1><p className="muted">Practice one thoughtful answer at a time.</p></div></div>{currentInterview ? <div className="panel interview-session"><div className="panel-title"><div><div className="eyebrow">{currentInterview.status === 'active' ? 'IN PROGRESS' : 'COMPLETED'}</div><h3>{currentInterview.title}</h3><p className="muted">{currentInterview.role} · {currentInterview.interview_type}</p></div><button className="secondary" onClick={() => setCurrentInterview(null)}><ArrowLeft size={15}/> All sessions</button></div><div className="transcript">{currentInterview.turns?.map((turn) => <div key={turn.id} className={`turn ${turn.role}`}><span>{turn.role === 'assistant' ? 'INTERVIEWER' : 'YOU'}</span><p>{turn.content}</p></div>)}</div>{currentInterview.status === 'active' ? <form className="answer-form" onSubmit={sendAnswer}><textarea value={answer} onChange={(e) => setAnswer(e.target.value)} required maxLength={12000} placeholder="Write your answer…"/><div className="editor-footer"><span>Up to 12,000 characters</span><div><button type="button" className="secondary" disabled={busy} onClick={finishInterview}>Finish</button><button className="primary" disabled={busy || !answer.trim()}>{busy ? <LoaderCircle className="spin" size={16}/> : <ArrowRight size={16}/>} Send answer</button></div></div></form> : <button className="primary" disabled={busy} onClick={evaluateInterview}>{busy ? <LoaderCircle className="spin" size={16}/> : <Sparkles size={16}/>} Get feedback</button>}</div> : <><form className="panel interview-create" onSubmit={startInterview}><div><div className="eyebrow">START PRACTICING</div><h3>Choose a focus</h3><p className="muted">Your answers and feedback are saved to your account.</p></div><label>Role<input value={role} onChange={(e) => setRole(e.target.value)} required maxLength={120}/></label><label>Interview style<select value={interviewType} onChange={(e) => setInterviewType(e.target.value)}><option value="behavioral">Behavioral</option><option value="technical">Technical</option><option value="system_design">System design</option><option value="mixed">Mixed</option></select></label><button className="primary" disabled={busy}>{busy ? <LoaderCircle className="spin" size={16}/> : <Video size={16}/>} Start interview</button></form><div className="section-head"><div><h2>Recent sessions</h2><p className="muted">Continue a session or review its transcript.</p></div></div><div className="panel session-list">{interviews.map((item) => <button key={item.id} className="session-row" onClick={() => setCurrentInterview(item)}><div className="feature-icon"><Video size={18}/></div><div><b>{item.title}</b><span>{item.role} · {item.status}</span></div><ArrowRight size={17}/></button>)}{!interviews.length && <p className="empty">Your interview sessions will appear here.</p>}</div></>}</>}
    {tab === 'resumes' && <><div className="practice-head"><div><div className="eyebrow">CAREER MATERIALS</div><h1>Resume coach</h1><p className="muted">Private uploads are stored in your account.</p></div></div><form className="panel upload-panel" onSubmit={uploadResume}><div className="feature-icon"><FileText/></div><div><h3>Upload a resume</h3><p className="muted">PDF, DOCX or text. Maximum 3 MB. Files are private to your account.</p></div><input type="file" name="file" accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain" required/><button className="primary" disabled={busy}>{busy ? <LoaderCircle className="spin" size={16}/> : <ArrowRight size={16}/>} Upload securely</button></form>{resumeFeedback && <div className="panel feedback-panel"><div className="eyebrow">RESUME FEEDBACK</div><p>{resumeFeedback}</p></div>}<div className="section-head"><div><h2>Your resumes</h2><p className="muted">Only you can view or download these files.</p></div></div><div className="panel session-list">{resumes.map((resume) => <div className="session-row" key={resume.id}><div className="feature-icon"><FileText size={18}/></div><div><b>{resume.filename}</b><span>{Math.ceil(resume.size_bytes / 1024)} KB · {new Date(resume.created_at).toLocaleDateString()}</span></div><button className="secondary" onClick={() => analyzeResume(resume.id)}>Review</button><button className="icon-btn" title="Download" onClick={() => downloadResume(resume)}><ArrowRight size={17}/></button></div>)}{!resumes.length && <p className="empty">No resumes uploaded yet.</p>}</div></>}
    {tab === 'analytics' && <><PageHead eyebrow="YOUR MOMENTUM" title="Progress" text="A clear view of the work you have put in."/>{analytics && <div className="metric-grid"><Metric label="INTERVIEWS" value={analytics.interviews}/><Metric label="CODE SUBMISSIONS" value={analytics.coding_submissions}/><Metric label="ACCEPTED SUBMISSIONS" value={analytics.accepted_submissions}/><Metric label="RESUMES" value={analytics.resumes}/><Metric label="AVERAGE INTERVIEW SCORE" value={analytics.average_interview_score ?? '—'}/></div>}</>}
    {tab === 'roadmap' && <><PageHead eyebrow="KEEP MOVING FORWARD" title={`${roadmap?.target_role || 'Your'} roadmap`} text="A small set of practical steps you can revisit any time."/>{roadmap && <div className="roadmap-list">{roadmap.items.map((item, index) => <div className="panel roadmap-item" key={item.id}><span className="step-num">{String(index + 1).padStart(2, '0')}</span><div><h3>{item.title}</h3><span>{item.category} · {item.minutes} min</span></div><Check size={17}/></div>)}</div>}</>}
    {tab === 'companies' && <><PageHead eyebrow="PRACTICE CONTEXTS" title="Company practice" text="Choose a practice focus to guide your preparation. These are general suggestions, not hiring guarantees."/><div className="company-grid">{companies.map((company) => <div className="panel company-card" key={company.id}><div className="feature-icon"><Briefcase size={19}/></div><h3>{company.name}</h3><span>{company.industry}</span><div className="tag-list">{company.practice_focus.map((focus) => <span key={focus}>{focus}</span>)}</div></div>)}</div></>}
    {tab === 'settings' && <><PageHead eyebrow="YOUR ACCOUNT" title="Preferences" text="Adjust how your practice workspace feels."/><form key={JSON.stringify(settings)} className="panel settings-form" onSubmit={saveSettings}><label>Theme<select name="theme" defaultValue={settings.theme || 'system'}><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label><label>Language<input name="language" defaultValue={settings.language || 'en'} maxLength={12}/></label><label>Weekly practice goal<input type="number" name="weekly_goal" min="1" max="30" defaultValue={settings.weekly_goal || 4}/></label><label className="check-label"><input type="checkbox" name="email_notifications" defaultChecked={Boolean(settings.email_notifications)}/> Email updates</label><label className="check-label"><input type="checkbox" name="practice_reminders" defaultChecked={Boolean(settings.practice_reminders)}/> Practice reminders</label><button className="primary" disabled={busy}>{busy ? <LoaderCircle className="spin" size={16}/> : <Check size={16}/>} Save preferences</button></form></>}
  </section></main></div>;
}

function Metric({ label, value }) { return <div className="panel metric-card"><span className="stat-value">{value ?? '—'}</span><span className="stat-name">{label}</span></div>; }
function PageHead({ eyebrow, title, text }) { return <div className="practice-head"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p className="muted">{text}</p></div></div>; }

createRoot(document.getElementById('root')).render(<React.StrictMode><App/></React.StrictMode>);
