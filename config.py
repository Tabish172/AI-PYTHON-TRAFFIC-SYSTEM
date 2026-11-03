from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_VIDEO = ROOT / 'uploads' / 'traffic_sample.mp4'
MODEL = ROOT / 'models' / 'yolov8n.pt'
DB_PATH = ROOT / 'database' / 'traffic.db'
VEHICLES = {2: 'Car', 3: 'Motorcycle', 5: 'Bus', 7: 'Truck'}
for folder in ('uploads', 'evidence', 'reports', 'models', 'database'):
    (ROOT / folder).mkdir(exist_ok=True)
