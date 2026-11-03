import uuid
from pathlib import Path
import cv2
import pandas as pd
import plotly.express as px
import streamlit as st
from config import ROOT, DEFAULT_VIDEO
from database.db import rows, connect
from modules.analytics import data
from modules.speed_estimation import Calibration
from utils.video_processor import VideoProcessor
from utils.pdf_generator import challan_pdf

st.set_page_config(page_title='Traffic Intelligence', page_icon='🚦', layout='wide')
from utils.app_theme import apply_theme
apply_theme()
st.sidebar.title('TRAFFIC / AI')
st.sidebar.caption('Traffic intelligence command center')
pages = ['Dashboard', 'Live Video Surveillance', 'Upload Traffic Video', 'Vehicle Detection',
         'Speed Monitoring', 'Challan Management', 'Analytics & Reports', 'AI Intelligence Center', 'History Management', 'Settings', 'About Project']
page = st.sidebar.radio('Workspace', pages)
st.sidebar.caption('Local video analysis • Demo fines only')
st.title(page)
st.caption('VEHICLE INTELLIGENCE / CALIBRATED SPEED ESTIMATES / EVIDENCE')
if 'source' not in st.session_state:
    st.session_state.source = str(DEFAULT_VIDEO)


def scan_panel():
    st.info('Your supplied WhatsApp video is ready as the default source. Surveillance replays uploaded footage; it is not a live camera feed.')
    upload = st.file_uploader('Choose traffic footage', type=['mp4','avi','mov'])
    if upload is not None:
        import hashlib
        content = upload.getbuffer()
        path = ROOT / 'uploads' / (hashlib.sha256(content).hexdigest()[:20] + Path(upload.name).suffix.lower())
        if not path.exists():
            path.write_bytes(content)
        st.session_state.source = str(path)
    if st.button('Use supplied WhatsApp video'):
        st.session_state.source = str(DEFAULT_VIDEO)
    source = Path(st.session_state.source)
    if not source.is_file():
        st.error('Source video missing. Upload a video above.')
        return
    with st.expander('Original footage and calibration preview'):
        st.video(str(source))
    a, b, c = st.columns(3)
    confidence = a.slider('Detection confidence', .1, .9, .35, .05)
    resolution = b.selectbox('Inference resolution', [640, 960, 1280])
    limit = c.number_input('Speed limit (km/h)', 1, 300, 80)
    with st.expander('Road calibration — required for speed and demo fines', expanded=True):
        st.caption('Use a fixed camera. Place two cross-sections across the same road; enter their measured ground distance along vehicle travel. The bottom center of each box must cross both. Do not guess distance from this video.')
        axis = st.selectbox('Travel axis', ['y','x'], format_func=lambda x: 'Vertical / horizontal reference lines' if x == 'y' else 'Horizontal / vertical reference lines')
        line_a, line_b = st.slider('Reference line positions (fraction of image)', 0.0, 1.0, (0.4,0.7), .01)
        distance = st.number_input('Measured road distance between lines (meters)', 0.0, 1000.0, 0.0, .5)
        confirmed = st.checkbox('I measured this road distance and verified both lines cross the same traffic path')
        cap = cv2.VideoCapture(str(source))
        ok, preview = cap.read()
        cap.release()
        if ok:
            h,w = preview.shape[:2]
            for name, value in [('A',line_a), ('B',line_b)]:
                p,q = ((0,int(value*h)),(w,int(value*h))) if axis=='y' else ((int(value*w),0),(int(value*w),h))
                cv2.line(preview,p,q,(255,180,40),3)
                cv2.putText(preview,name,(max(10,p[0]),max(25,p[1])),cv2.FONT_HERSHEY_SIMPLEX,1,(255,180,40),2)
            st.image(preview, channels='BGR', caption='Calibration preview', width=760)
        if not distance or not confirmed:
            st.warning('Detection-only mode: speed remains unknown and no fines are generated.')
    ocr = st.checkbox('Attempt number plate OCR for violations (downloads OCR models on first use)')
    fine = st.number_input('DEMO fine amount (INR)', 0, 100000, 2000, 100)
    device = st.selectbox('Compute device', ['cpu','0'], format_func=lambda x: 'CPU' if x=='cpu' else 'CUDA GPU 0 (requires compatible PyTorch)')
    running = st.session_state.get('processor')
    col1,col2 = st.columns(2)
    if col1.button('Start new scan', type='primary', disabled=running is not None and not running.closed):
        try:
            with st.spinner('Loading detector and opening video… First use downloads the model.'):
                st.session_state.processor = VideoProcessor(source, Calibration(line_a,line_b,distance if confirmed else 0,axis), confidence,resolution,limit,fine,ocr,device)
        except Exception as exc:
            st.error(f'Could not start scan: {exc}. Check dependencies, model access and video format, then retry.')
    if col2.button('Stop scan'):
        processor = st.session_state.get('processor')
        if processor and not processor.closed:
            processor.close()

    @st.fragment(run_every=1)
    def scan_progress():
        processor = st.session_state.get('processor')
        if not processor:
            return
        if not processor.closed:
            processor.step(3)
        st.subheader(processor.status)
        st.progress(min(processor.frame_index/max(processor.total,1),1.0))
        st.caption(f'Frame {processor.frame_index:,} / {processor.total:,} • {len(processor.tracks.tracks)} unique tracks • {len(processor.issued)} demo violations')
        if processor.latest is not None:
            st.image(processor.latest, channels='BGR', caption='Yellow: speed pending • Green: within limit • Red: above limit')
        if processor.warning:
            st.warning(processor.warning)
        if processor.error:
            st.error(processor.error)
        if processor.closed:
            if not processor.tracks.tracks:
                st.info('No vehicles detected. Try a lower confidence or a higher resolution.')
            if processor.output.exists():
                st.download_button('Download annotated video', processor.output.read_bytes(), processor.output.name, 'video/mp4')
                st.caption('MP4 uses MPEG-4 video. Use VLC if your browser cannot play this codec.')
    scan_progress()


def dashboard(analytics=False):
    runs = rows('runs')
    if not runs:
        st.info('No scans yet. Open Upload Traffic Video to scan your supplied footage.')
        return
    selected = st.selectbox('Scan', list(reversed(runs)), format_func=lambda r: f"{r['started'][:19]} UTC · {Path(r['source']).name} · {r['status']}")
    output = ROOT / 'reports' / f"{selected['id']}_annotated.mp4"
    if output.is_file() and selected['status'] != 'Running':
        st.download_button('Download annotated scan', output.read_bytes(), output.name, 'video/mp4')
    vehicles, fines = data(selected['id'])
    if vehicles.empty:
        st.info('No vehicle tracks recorded for this scan yet.')
        return
    columns = st.columns(4)
    columns[0].metric('Unique vehicle tracks', len(vehicles))
    columns[1].metric('Estimated mean km/h', f"{vehicles.speed.mean():.1f}" if vehicles.speed.notna().any() else 'Uncalibrated / pending')
    columns[2].metric('Overspeeding', len(fines))
    columns[3].metric('Demo fines • INR', f'{fines.fine.sum():,.0f}' if not fines.empty else '0')
    columns = st.columns(4)
    for col, category in zip(columns, ['Car','Motorcycle','Bus','Truck']):
        col.metric(category, int((vehicles.category==category).sum()))
    st.caption('Counts represent tracking IDs; occlusion or camera cuts can split one physical vehicle into multiple tracks. Unknown speeds are excluded from speed statistics.')
    left,right = st.columns(2)
    left.plotly_chart(px.pie(vehicles,names='category',title='Vehicle mix'), width='stretch')
    if vehicles.speed.notna().any():
        right.plotly_chart(px.histogram(vehicles.dropna(subset=['speed']),x='speed',title='Estimated speed distribution'), width='stretch')
    else:
        right.info('Calibrate and scan vehicles crossing both lines to see speed analytics.')
    if analytics:
        arrivals = vehicles.assign(second=vehicles.first_seen.astype(int)).groupby('second').size().rename('new_tracks').reset_index()
        st.plotly_chart(px.bar(arrivals,x='second',y='new_tracks',title='New vehicle tracks over video time'),width='stretch')
        known = int(vehicles.speed.notna().sum())
        st.plotly_chart(px.pie(names=['Within limit','Overspeeding','Unknown speed'],values=[known-len(fines),len(fines),len(vehicles)-known],title='Speed status'),width='stretch')
        st.dataframe(vehicles.sort_values('speed',ascending=False).head(10),hide_index=True)
    st.dataframe(vehicles,hide_index=True,width='stretch')
    st.download_button('Export vehicles CSV', vehicles.to_csv(index=False),'vehicles.csv','text/csv')


def challans():
    st.warning('SIMULATION ONLY. Amounts are configurable demo values, not government fines. Registration candidates require manual verification.')
    records = pd.DataFrame(rows('challans'))
    if records.empty:
        st.info('No simulated challans. A calibrated scan and a speed exceeding the configured limit are required.')
        return
    query = st.text_input('Search registration or challan ID')
    categories = st.multiselect('Vehicle type', records.category.unique(),default=list(records.category.unique()))
    statuses = st.multiselect('Status', records.status.unique(),default=list(records.status.unique()))
    days = st.multiselect('Processing date (UTC)', sorted(records.created.str[:10].unique()),default=sorted(records.created.str[:10].unique()))
    filtered = records[records.category.isin(categories) & records.status.isin(statuses) & records.created.str[:10].isin(days)]
    if query:
        filtered = filtered[filtered.registration.str.contains(query,case=False,regex=False) | filtered.id.str.contains(query,case=False,regex=False)]
    st.dataframe(filtered,hide_index=True)
    st.download_button('Export challans CSV',filtered.to_csv(index=False),'demo_challans.csv','text/csv')
    if not filtered.empty:
        selected = st.selectbox('View evidence / PDF',filtered.id)
        record = filtered[filtered.id==selected].iloc[0].to_dict()
        if Path(record['evidence']).is_file():
            st.image(record['evidence'])
        st.download_button('Download demo challan PDF',challan_pdf(record),f'{selected}.pdf','application/pdf')
        status = st.selectbox('Set demo status',['Demo - unpaid','Demo - paid','Demo - dismissed'])
        if st.button('Save demo status'):
            with connect() as db:
                db.execute('UPDATE challans SET status=? WHERE id=?',(status,selected))
            st.rerun()


try:
    if page == 'AI Intelligence Center':
        from modules.ai_center import render_center
        render_center()
    elif page == 'History Management':
        from modules.history_ui import render_history
        render_history()
    elif page in ['Upload Traffic Video','Live Video Surveillance','Speed Monitoring']:
        scan_panel()
    elif page in ['Dashboard','Vehicle Detection','Analytics & Reports']:
        dashboard(page=='Analytics & Reports')
    elif page == 'Challan Management':
        challans()
    elif page == 'Settings':
        st.subheader('Dashboard background')
        background = st.file_uploader('Choose your traffic background image',type=['jpg','jpeg','png','webp','avif'],key='background_upload')
        if background is not None and st.button('Apply background image'):
            from utils.app_theme import save_background
            save_background(background)
            st.rerun()
        st.subheader('Scan configuration')
        st.write('Set confidence, resolution, speed limit, compute device, OCR, demo amount and road calibration on the Upload Traffic Video page before starting a scan. Each scan saves its settings independently.')
        st.code(f'Database: {ROOT / "database/traffic.db"}\nEvidence: {ROOT / "evidence"}\nReports: {ROOT / "reports"}')
    else:
        st.write('Python • Streamlit • Ultralytics YOLOv8 nano • ByteTrack • OpenCV • EasyOCR • SQLite')
        st.write('Speeds use interpolated crossing times between two road reference lines and a user-measured real distance. No pixel displacement is presented as km/h. Fixed camera geometry, visible road contact points, constant frame rate footage and correct calibration are required. Moving cameras, edits and variable frame rates can invalidate estimates.')
        st.write('OCR is best effort using rectangular plate candidates and Indian registration patterns. No registration numbers are invented. This application does not issue official challans or identify vehicle owners.')
except Exception as exc:
    st.error(f'Operation failed: {exc}. Correct the input or check local file permissions and retry.')
