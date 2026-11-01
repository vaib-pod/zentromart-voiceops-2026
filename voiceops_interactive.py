
"""ZentroMart VoiceOps: dark AI voice assistant + verified PDF order receipts.
Run from the project root:
    python -m streamlit run voiceops_interactive.py
Requires vendor/Capstone_Project_Dataset_FTTT_2026, .env with Groq and Gnani
keys for live voice. Receipt documents are synthetic; not GST tax invoices.
"""
from __future__ import annotations
import base64
import os
import re
import tempfile
import uuid
from html import escape
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
from src.core import Agent
from src.receipt_generator import build_receipt_pdf, receipt_filename, money
from src.voice_receipts import route_message, verified_receipt_for_session
st.set_page_config(
    page_title='ZentroMart / VoiceOps',
    page_icon='✦',
    layout='wide',
    initial_sidebar_state='expanded',
)
@st.cache_data(show_spinner=False)
def background_image_uri() -> str:
    p=ROOT/'assets'/'voiceops_background.png'
    if not p.is_file():
        return ''
    return 'data:image/png;base64,'+base64.b64encode(p.read_bytes()).decode('ascii')
bg=background_image_uri()
bg_rule=(f'linear-gradient(180deg,rgba(6,7,24,.34),rgba(6,7,24,.84) 70%), url("{bg}")'
         if bg else 'linear-gradient(135deg,#080919,#141144 65%,#0A2758)')
BOT_IMAGE_BASE64 = (
    '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'
)
bot_uri = "data:image/webp;base64," + BOT_IMAGE_BASE64
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=Oxanium:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');
:root { --navy:#080a1e; --panel:#11142e; --stroke:rgba(158,179,255,.18);
 --white:#ffffff; --fade:rgba(255,255,255,.70); --blue:#4a72ff; --violet:#6324cb; }
html, body, .stApp { font-family:'Inter',sans-serif; color:white!important; }
.stApp { background:#08091e!important; }
[data-testid="stAppViewContainer"] { background-image: BG_RULE!important;
 background-repeat:no-repeat!important; background-position:center top!important;
 background-size:cover!important; background-attachment:fixed!important; }
[data-testid="stHeader"] {background:transparent!important;}
[data-testid="stToolbar"], [data-testid="stDecoration"] {display:none!important;}
.stHeadingAnchor, [data-testid="stHeaderActionElements"],
[data-testid="stMarkdownContainer"] :is(h1,h2,h3) > a[href^="#"],
[data-testid="stMarkdownContainer"] :is(h1,h2,h3) > a[aria-label*="link" i] { display:none!important; }
.block-container {max-width:1240px;padding:2.6rem 2.7rem 5rem;}
h1,h2,h3,h4,p,span,label {color:#fff;}
h1,h2,h3 {font-family:'Oxanium','Inter',sans-serif;}
p {line-height:1.6;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#0d102a,#090c20)!important;
 border-right:1px solid rgba(142,163,245,.2);}
[data-testid="stSidebar"] * {color:#fff!important;}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top:26px;}
.brand {font-family:'Oxanium',sans-serif;font-size:26px;font-weight:800;line-height:1.07;
 letter-spacing:.04em;padding:0 1px 7px;}
.brand-note {font-size:10px;color:rgba(255,255,255,.58)!important;
 letter-spacing:.19em;font-weight:700;padding-bottom:12px;}
.side-rule {height:1px;background:linear-gradient(90deg,rgba(143,160,255,.45),transparent);margin:17px 0;}
.side-label {font:700 10px 'Oxanium',sans-serif;letter-spacing:.19em;margin:17px 0 9px;color:#e8ecff;}
.demo-profile {display:flex;align-items:center;gap:11px;padding:13px;border:1px solid rgba(149,173,255,.22);
 background:rgba(27,33,77,.47);border-radius:15px;margin:8px 0 13px;}
.profile-avatar {width:39px;height:39px;min-width:39px;border-radius:12px;
 display:flex;align-items:center;justify-content:center;font:800 18px 'Oxanium',sans-serif;
 background:linear-gradient(130deg,#5630cc,#2e91d5);color:white;}
.profile-main {font-size:13px;font-weight:700;color:white;}
.profile-sub {font-size:10px;color:rgba(255,255,255,.57)!important;margin-top:2px;}
[data-testid="stSidebar"] [role="radiogroup"] label {border:1px solid rgba(140,158,233,.16);
 border-radius:12px;padding:8px 11px;margin:4px 0;background:rgba(16,21,49,.64);}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {border-color:rgba(123,146,255,.58);
 background:linear-gradient(90deg,rgba(74,67,188,.4),rgba(29,54,108,.22));}
.hero {position:relative;overflow:hidden;padding:27px 35px 28px;border-radius:23px;
 background:linear-gradient(110deg,rgba(10,9,35,.86),rgba(8,15,38,.72));
 border:1px solid rgba(137,154,250,.22);box-shadow:0 20px 64px rgba(0,0,0,.24);
 margin-bottom:18px;isolation:isolate;}
.hero::before {content:'';position:absolute;z-index:-1;right:-150px;top:-230px;
 width:510px;height:510px;border:1px solid rgba(87,64,222,.42);border-radius:50%;
 box-shadow:0 0 0 38px rgba(75,49,206,.05),0 0 0 96px rgba(42,70,181,.06);}
.hero::after {content:'';position:absolute;z-index:-1;right:-20px;bottom:-110px;width:550px;height:230px;
 background:radial-gradient(ellipse,rgba(21,142,220,.24),transparent 70%);}
.status-pill {display:inline-block;border:1px solid rgba(155,176,255,.28);
 background:rgba(49,58,143,.3);padding:9px 14px;border-radius:999px;
 font:700 11px 'Oxanium',sans-serif;letter-spacing:.13em;color:white;}
.hero h1 {font:800 clamp(46px,6.1vw,82px)/.98 'Oxanium',sans-serif;
 letter-spacing:-.055em;margin:13px 0 11px;color:#fff;}
.hero p {font-size:13px;color:rgba(255,255,255,.79);max-width:690px;margin:0;}
.kpi-row {display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:15px 0 18px;}
.kpi {padding:13px 15px;background:rgba(10,15,43,.76);border:1px solid rgba(134,161,248,.16);
 border-radius:13px;backdrop-filter:blur(10px);}
.kpi strong {display:block;font:700 12px 'Oxanium',sans-serif;color:white;margin-bottom:5px;}
.kpi span {display:block;font-size:11px;color:rgba(255,255,255,.65);}
.section-heading {font:700 22px 'Oxanium',sans-serif;letter-spacing:-.02em;margin:8px 0 6px;color:white;}
.muted {font-size:12px;color:rgba(255,255,255,.7);}
.bot-perch {position:relative;z-index:1;height:112px;margin:0 26px -8px 0;
 display:flex;justify-content:flex-end;pointer-events:none;}
.bot-crop {position:relative;width:168px;height:112px;flex:0 0 168px;
 overflow:hidden;margin-left:auto;}
.bot-figure {position:absolute;top:0;right:0;width:168px;
 filter:drop-shadow(0 12px 16px rgba(0,0,0,.28));}
.bot-figure img {display:block;width:100%;height:auto;margin:0;}
.bot-eye-cover {position:absolute;z-index:2;top:29.5%;width:8%;height:5.3%;
 opacity:0;background:#002733;border-radius:999px;
 animation:mascot-blink 2s ease-in-out infinite;pointer-events:none;}
.bot-eye-cover::after {content:'';position:absolute;left:8%;right:8%;top:76%;height:2px;
 border-radius:99px;background:#3be7c2;box-shadow:0 0 7px #27dbc0;}
.bot-eye-cover.left {left:36.8%;}
.bot-eye-cover.right {left:56.5%;}

@keyframes mascot-blink {0%,39%,45%,100%{opacity:0;}41%,43%{opacity:1;}}
@media (prefers-reduced-motion:reduce){.bot-eye-cover{animation:none!important;}}
[data-testid="stVerticalBlockBorderWrapper"]:has(.conversation-shell-marker) {
 background:linear-gradient(155deg,rgba(14,20,54,.96),rgba(7,12,36,.96))!important;
 border:1px solid rgba(137,164,255,.30)!important;border-radius:22px!important;
 box-shadow:0 21px 62px rgba(0,0,0,.32)!important;
 overflow:visible!important;}
.conversation-shell-marker {height:1px;margin:0;padding:0;}
.chat-topline {display:flex;align-items:center;justify-content:space-between;gap:12px;
 padding:0 0 10px;border-bottom:1px solid rgba(146,161,241,.18);margin-bottom:10px;}
.chat-topline strong {font:700 19px 'Oxanium',sans-serif;color:#fff;}
.chat-topline span {font-size:10px;color:rgba(255,255,255,.59);}
.chat-live {display:flex;align-items:center;gap:7px;font-size:10px;font-weight:600;
 color:#d9e8ff;white-space:nowrap;}
.chat-live b {width:7px;height:7px;background:#42dfb0;box-shadow:0 0 9px rgba(66,223,176,.75);
 border-radius:50%;display:inline-block;}
[data-testid="stChatMessage"] {background:rgba(20,26,61,.9);border:1px solid rgba(143,155,227,.17);
 border-radius:15px;padding:12px 15px;margin-bottom:9px;}
[data-testid="stChatInput"] {background:rgba(13,16,42,.96);border-radius:14px;
 border:1px solid rgba(142,160,249,.30);}
[data-testid="stChatInput"] textarea {color:white!important;}
[data-testid="stAudioInput"], [data-testid="stFileUploader"] {border-radius:12px;}
[data-testid="stAudioInput"] button, [data-testid="stAudioInput"] * {color:#fff!important;}
[data-testid="stAudio"] {background:rgba(16,20,48,.8);border-radius:12px;}
[data-testid="stVerticalBlockBorderWrapper"]:has(.conversation-shell-marker)
 [data-testid="stVerticalBlockBorderWrapper"] {border:none!important;box-shadow:none!important;}
 div.stButton > button[kind="primary"], div.stDownloadButton > button {background:
 linear-gradient(105deg,#6547e9,#2878ec)!important;color:white!important;
 border:1px solid rgba(192,193,255,.23)!important;border-radius:11px;font-weight:700;
 box-shadow:0 7px 20px rgba(58,50,200,.19);}
 div.stButton > button[kind="secondary"] {background:rgba(48,53,119,.35)!important;
 color:white!important;border:1px solid rgba(145,166,255,.3)!important;border-radius:11px;}
button:hover {border-color:rgba(155,184,255,.72)!important;}
[data-baseweb="input"] > div,[data-baseweb="select"] > div {background:rgba(13,17,45,.95)!important;
 border:1px solid rgba(140,156,235,.28)!important;border-radius:10px!important;}
[data-baseweb="input"] input,input,textarea {color:white!important;}
[data-testid="stWidgetLabel"] p,[data-testid="stMarkdownContainer"] p {color:white;}
[data-testid="stAlert"] {background:rgba(23,28,65,.9)!important;border-radius:12px;}
[data-testid="stMetricValue"] {color:white;}
hr {border-color:rgba(140,153,240,.19)!important;}
.receipt-glass {border:1px solid rgba(140,163,250,.2);border-radius:15px;
 background:rgba(12,17,47,.75);padding:17px 22px;margin:12px 0;}
.receipt-glass strong {font:700 15px 'Oxanium',sans-serif;}
.receipt-glass p {font-size:12px;color:rgba(255,255,255,.72);margin:6px 0 0;}
.item-tag {border:1px solid rgba(111,141,254,.33);background:rgba(55,62,139,.27);
 color:white;padding:9px 12px;border-radius:9px;display:block;margin:5px 0;font-size:12px;}
.profile-details {padding:20px;border:1px solid rgba(151,172,244,.24);
 background:rgba(11,17,47,.87);border-radius:17px;}
@media (max-width:900px){.block-container{padding:1.6rem 1rem 4rem;}
 .hero{padding:25px 21px}.hero h1{font-size:50px;}.kpi-row{grid-template-columns:1fr;}
 .bot-perch{height:91px;margin-right:8px}
 .bot-crop{width:136px;height:91px;flex-basis:136px}
 .bot-figure{width:136px;}
 .chat-topline strong{font-size:16px;}}
</style>'''.replace('BG_RULE',bg_rule),unsafe_allow_html=True)
if 'agent' not in st.session_state:
    try:
        st.session_state.agent=Agent()
    except Exception as exc:
        st.error('Unable to load ZentroMart dataset. Check vendor/Capstone_Project_Dataset_FTTT_2026 and restart.')
        st.caption(f'Diagnostic: {type(exc).__name__}')
        st.stop()
    st.session_state.session_id=str(uuid.uuid4())
    st.session_state.messages=[]
    st.session_state.recording_counter=0
    st.session_state.notice=''
    st.session_state.autoplay=False
    st.session_state.receipt_pending=False
if 'receipt_pending' not in st.session_state:
    st.session_state.receipt_pending=False
def current_order_session():
    return st.session_state.agent.sessions.get(st.session_state.session_id)
def reset_chat():
    st.session_state.agent=Agent()
    st.session_state.session_id=str(uuid.uuid4())
    st.session_state.messages=[]
    st.session_state.recording_counter+=1
    st.session_state.notice=''
    st.session_state.autoplay=False
    st.session_state.receipt_pending=False
def speak(answer: str):
    if not st.session_state.get('speak_replies',True):
        return None
    key=os.getenv('GNANI_API_KEY')
    if not key:
        st.warning('Add GNANI_API_KEY in .env to generate spoken replies. Text chat remains available.')
        return None
    try:
        from gnani.tts import GnaniTTSClient
        with st.spinner('Generating voice response...'):
            return GnaniTTSClient(api_key=key).synthesize(answer,voice='Pranav',model='timbre-v2.5')
    except Exception as exc:
        st.warning(f'Audio unavailable ({type(exc).__name__}); the text reply is available.')
        return None
def process_message(message: str) -> None:
    with st.spinner('Thinking with ZentroMart AI...'):
        turn=route_message(
            st.session_state.agent, st.session_state.session_id, message,
            receipt_pending=st.session_state.receipt_pending,
        )
    if not turn.user_display:
        st.warning('No speech detected. Please try again.')
        return
    st.session_state.receipt_pending=turn.pending
    st.session_state.messages.append(dict(role='user',text=turn.user_display))
    audio=speak(turn.answer)
    st.session_state.messages.append(dict(
        role='assistant',text=turn.answer,decision=turn.decision,audio=audio,
        receipt_pdf=turn.receipt_pdf,receipt_order_id=turn.receipt_order_id,
        receipt_filename=turn.receipt_name,
    ))
    st.session_state.autoplay=bool(audio)
with st.sidebar:
    st.markdown('<div class="brand">ZENTROMART<br/>VOICEOPS</div>',unsafe_allow_html=True)
    st.markdown('<div class="brand-note">✦  CUSTOMER VOICE SUPPORT</div>',unsafe_allow_html=True)
    st.markdown('<div class="side-rule"></div>',unsafe_allow_html=True)
    display_name=st.session_state.get('display_name','Guest User')
    initial=escape(display_name[:1].upper() or 'G')
    st.markdown(f'''<div class="demo-profile"><div class="profile-avatar">{initial}</div>
     <div><div class="profile-main">{escape(display_name)}</div>
     <div class="profile-sub">Demo session · Not signed in</div></div></div>''',unsafe_allow_html=True)
    st.markdown('<div class="side-label">DASHBOARD</div>',unsafe_allow_html=True)
    page=st.radio('Choose a page',['Voice Assistant','Order Receipts','Profile'],
                  key='nav_page',label_visibility='collapsed')
    st.markdown('<div class="side-rule"></div>',unsafe_allow_html=True)
    st.markdown('<div class="side-label">VOICE SETTINGS</div>',unsafe_allow_html=True)
    language=st.selectbox('Speech recognition language',['en-IN','hi-IN'],
                         format_func=lambda x:'English (India)' if x=='en-IN' else 'Hindi (India)')
    st.toggle('Spoken AI replies',value=True,key='speak_replies')
    st.markdown('<div class="side-label">CONVERSATION</div>',unsafe_allow_html=True)
    st.button('↻  New conversation',use_container_width=True,on_click=reset_chat)
    st.caption('Verification is required for order data. Demo tickets and real handovers are disabled.')
    st.markdown('<div class="side-rule"></div>',unsafe_allow_html=True)
    gnani_ok=bool(os.getenv('GNANI_API_KEY'))
    groq_ok=bool(os.getenv('GROQ_API_KEY') or os.getenv('LLM_API_KEY'))
    st.markdown('<div class="side-label">KEY CONFIGURATION</div>',unsafe_allow_html=True)
    st.caption(('● Gnani key present' if gnani_ok else '○ Gnani key missing')+'  ·  '+
               ('● Groq key present' if groq_ok else '○ Groq key missing'))
    st.caption('Key presence does not mean the APIs are connected.')
st.markdown('''<div class="hero">
 <div class="status-pill">✦ &nbsp; ZENTROMART CUSTOMER VOICE SUPPORT</div>
 <h1>BEYOND<br/>THE CHAT.</h1>
 <p>Speak naturally, get policy-grounded answers, and securely download your order receipts.</p>
</div>''',unsafe_allow_html=True)
st.markdown('''<div class="kpi-row">
 <div class="kpi"><strong>01 / LISTEN</strong><span>Speech to text with Gnani</span></div>
 <div class="kpi"><strong>02 / UNDERSTAND</strong><span>Policy-aware Groq + RAG support</span></div>
 <div class="kpi"><strong>03 / ACT</strong><span>Verified PDF receipts and voice replies</span></div>
</div>''',unsafe_allow_html=True)
if page=='Voice Assistant':
    st.markdown('<div class="section-heading">YOUR CONVERSATION</div>',unsafe_allow_html=True)
    st.markdown('<p class="muted">Ask about returns, refunds, deliveries, cancellations, or request a receipt.</p>',
                unsafe_allow_html=True)
    st.markdown(f'''<div class="bot-perch" aria-label="Smiling ZentroMart assistant mascot">
      <div class="bot-crop"><div class="bot-figure">
        <img src="{bot_uri}" alt="Friendly light-blue robot mascot"/>
        <span class="bot-eye-cover left"></span><span class="bot-eye-cover right"></span>
      </div></div></div>''',unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown('''<div class="conversation-shell-marker"></div>
        <div class="chat-topline"><div><strong>✦ &nbsp; ZentroMart Assistant</strong>
        <div><span>Voice + text support · Context-aware conversation</span></div></div>
        <div class="chat-live"><b></b> LOCAL SESSION</div></div>''',unsafe_allow_html=True)

        with st.container(height=360,border=False):
            if not st.session_state.messages:
                st.info('Welcome! Ask “What is the electronics return policy?” or say “Download my invoice.”')
            for i,item in enumerate(st.session_state.messages):
                with st.chat_message(item['role']):
                    st.markdown(item['text'])
                    if item.get('decision'):
                        st.caption('ROUTING / '+str(item['decision']).upper())
                    if (item.get('receipt_pdf') and
                            verified_receipt_for_session(st.session_state.agent,
                                                         st.session_state.session_id,
                                                         item.get('receipt_order_id'))):
                        st.download_button(
                            '↓ Download receipt (PDF)',data=item['receipt_pdf'],
                            file_name=item['receipt_filename'],mime='application/pdf',
                            type='primary',key=f'voice_receipt_{i}',use_container_width=True,
                        )
                    if item.get('audio'):
                        autoplay=(i==len(st.session_state.messages)-1 and st.session_state.autoplay)
                        st.audio(item['audio'],format='audio/wav',autoplay=autoplay)
        st.session_state.autoplay=False
        st.markdown('<div class="side-label">TALK TO THE ASSISTANT</div>',unsafe_allow_html=True)
        recording=st.audio_input('Record your question',sample_rate=16000,
                       key=f'recording_{st.session_state.recording_counter}')
        if st.button('✦  Send voice message',type='primary',disabled=recording is None,
                     use_container_width=True):
            if not os.getenv('GNANI_API_KEY'):
                st.error('Add GNANI_API_KEY to .env to use voice transcription.')
            else:
                path=None
                try:
                    payload=recording.getvalue()
                    if not payload:
                        st.warning('Recording is empty.')
                    else:
                        with tempfile.NamedTemporaryFile(suffix='.wav',delete=False) as tmp:
                            tmp.write(payload)
                            path=Path(tmp.name)
                        from gnani.stt import GnaniSTTClient
                        with st.spinner('Transcribing speech with Gnani...'):
                            transcript=GnaniSTTClient(api_key=os.environ['GNANI_API_KEY']).transcribe(
                                str(path),language_code=language).get('transcript','')
                        process_message(transcript)
                        st.session_state.recording_counter+=1
                        st.rerun()
                except Exception as exc:
                    st.error(f'Voice processing failed ({type(exc).__name__}). Check terminal logs.')
                finally:
                    if path is not None:
                        path.unlink(missing_ok=True)
        typed_message=st.chat_input('Ask ZentroMart anything…')
        if typed_message:
            try:
                process_message(typed_message)
                st.rerun()
            except Exception as exc:
                st.error(f'Assistant unavailable ({type(exc).__name__}). Check terminal logs.')
elif page=='Order Receipts':
    st.markdown('<div class="section-heading">YOUR ORDER. YOUR RECEIPT.</div>',unsafe_allow_html=True)
    st.markdown('<p class="muted">Find an order, verify ownership, and download a PDF receipt. '
                'No customer information is shown before verification.</p>',unsafe_allow_html=True)
    st.markdown('''<div class="receipt-glass"><strong>SECURE DOWNLOAD / 3 STEPS</strong>
        <p>01 — Enter your 8-digit order ID &nbsp;&nbsp; / &nbsp;&nbsp;
        02 — Verify with phone suffix or delivery PIN &nbsp;&nbsp; / &nbsp;&nbsp;
        03 — Download your PDF receipt</p></div>''',unsafe_allow_html=True)
    s=current_order_session()
    oid_default=s.order_id if s and s.order_id else ''
    input_col,button_col=st.columns([3,1],vertical_alignment='bottom')
    with input_col:
        oid_input=st.text_input('8-digit Order ID',value=oid_default,
                                max_chars=8,placeholder='e.g. 69520867',key='receipt_oid')
    with button_col:
        lookup_clicked=st.button('Find order',type='primary',use_container_width=True)
    if lookup_clicked:
        if not re.fullmatch(r'\d{8}',oid_input.strip()):
            st.error('Enter a valid 8-digit order ID.')
        elif s and s.verified and s.order_id==oid_input.strip():
            st.session_state.notice='This order has already been verified in your session.'
            st.rerun()
        else:
            response=st.session_state.agent.respond(
                f'I need help with my order {oid_input.strip()}',
                session_id=st.session_state.session_id,allow_ticket=False)
            st.session_state.notice=response['answer']
            st.rerun()
    s=current_order_session()
    if st.session_state.notice:
        st.info(st.session_state.notice)
    if s and s.order_id and not s.verified:
        if s.attempts>=2 or s.phase=='verification_blocked':
            st.error('Verification attempts exhausted. Start a new conversation or contact support.')
        else:
            st.markdown('<div class="section-heading">VERIFY OWNERSHIP</div>',unsafe_allow_html=True)
            st.caption(f'Order {s.order_id}: enter the registered phone’s last 4 digits '
                       'OR the 6-digit delivery PIN. This value is not displayed or sent to the LLM.')
            with st.form('verify_receipt',clear_on_submit=True):
                proof=st.text_input('Verification code',type='password',max_chars=6,
                    placeholder='4 or 6 digits')
                submitted=st.form_submit_button('Verify order',type='primary')
                if submitted:
                    if not re.fullmatch(r'(?:\d{4}|\d{6})',proof.strip()):
                        st.error('Use exactly 4 or 6 digits.')
                    else:
                        response=st.session_state.agent.respond(
                            proof.strip(),session_id=st.session_state.session_id,
                            allow_ticket=False)
                        st.session_state.notice=response['answer']
                        proof_session=current_order_session()
                        if proof_session and getattr(proof_session,'history',None):
                            last=proof_session.history[-1]
                            if isinstance(last,dict) and 'customer' in last:
                                last['customer']='[verification details redacted]'
                        st.rerun()
    s=current_order_session()
    if s and s.verified and s.safe_order.get('verified') is True and s.safe_order.get('found') is True \
       and str(s.safe_order.get('order_id'))==s.order_id:
        verified=s.safe_order
        st.success('Order verified. Your PDF receipt is ready.')
        st.markdown('<div class="section-heading">ORDER SUMMARY</div>',unsafe_allow_html=True)
        a,b,c=st.columns(3)
        a.metric('Order ID',s.order_id)
        b.metric('Items',str(len(verified.get('items') or [])))
        c.metric('Order total',money(verified.get('total_inr')))
        st.caption('Items in this verified order:')
        items=verified.get('items',[])
        query=st.text_input('Find an item within this order (optional)',
                            placeholder='Search by product name or SKU',key='verified_item_search')
        filtered=[item for item in items if
                  query.casefold() in str(item.get('title','')).casefold() or
                  query.casefold() in str(item.get('sku','')).casefold()]
        if not filtered:
            st.info('No matching items in this verified order.')
        for item in filtered:
            title=escape(str(item.get('title') or 'Item'))
            sku=escape(str(item.get('sku') or '-'))
            qty=escape(str(item.get('qty') or '0'))
            line=f'{title} &nbsp; · &nbsp; {sku} &nbsp; · &nbsp; Qty {qty}'
            st.markdown(f'<div class="item-tag">{line}</div>',unsafe_allow_html=True)
        st.caption('Item search only filters this verified order. The PDF contains the full order.')
        try:
            receipt_pdf=build_receipt_pdf(verified)
            st.download_button('↓  Download order receipt (PDF)',data=receipt_pdf,
                file_name=receipt_filename(s.order_id),mime='application/pdf',
                type='primary',use_container_width=True)
        except (ValueError,PermissionError) as exc:
            st.error(f'Could not generate receipt: {type(exc).__name__}')
        st.info('This is an educational order receipt, not an official GST tax invoice.')
    elif not (s and s.order_id):
        st.caption('Enter your order ID above to begin. No order details are available before verification.')
elif page=='Profile':
    st.markdown('<div class="section-heading">PROFILE / DEMO</div>',unsafe_allow_html=True)
    st.markdown('<p class="muted">Customize how your local demo session appears. This is not an authenticated customer account.</p>',unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown('### Your local profile')
        st.text_input('Display name',value=st.session_state.get('display_name','Guest User'),key='profile_name_input')
        if st.button('Save display name',type='primary'):
            name=st.session_state.profile_name_input.strip()[:40]
            if name:
                st.session_state.display_name=name
                st.rerun()
            else:
                st.warning('Enter a name first.')
        st.divider()
        st.caption('Conversation data and verification belong to this browser session. A display name does not prove customer identity.')
        st.caption('The synthetic dataset is for demonstration and testing only.')
