"""Command-line scanning using the same pipeline as the dashboard."""
import argparse
import json
from config import DEFAULT_VIDEO
from modules.speed_estimation import Calibration
from utils.video_processor import VideoProcessor

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--video', default=str(DEFAULT_VIDEO))
    parser.add_argument('--max-frames', type=int, default=0)
    args = parser.parse_args()
    scan = VideoProcessor(args.video, Calibration())
    try:
        while not scan.closed:
            scan.step(1)
            if scan.frame_index % 100 == 0:
                print(f'{scan.frame_index}/{scan.total}: {len(scan.tracks.tracks)} tracks', flush=True)
            if args.max_frames and scan.frame_index >= args.max_frames:
                scan.close('Stopped - preview')
    finally:
        scan.close()
    print(json.dumps(dict(run_id=scan.run_id,status=scan.status,frames=scan.frame_index,
                         tracks=len(scan.tracks.tracks),output=str(scan.output),error=scan.error),indent=2))
    if scan.error:
        raise SystemExit(1)
