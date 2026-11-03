"""Export a completed scan's tracks and a factual summary."""
import argparse
import json
from config import ROOT
from database.db import rows
from modules.analytics import data


def export(run_id):
    run = next(r for r in rows('runs') if r['id'] == run_id)
    vehicles, challans = data(run_id)
    csv_path = ROOT / 'reports' / f'{run_id}_vehicles.csv'
    vehicles.to_csv(csv_path, index=False)
    summary = dict(run=run, unique_tracking_ids=len(vehicles),
                   categories=vehicles.category.value_counts().to_dict() if not vehicles.empty else {},
                   measured_speeds=int(vehicles.speed.notna().sum()) if not vehicles.empty else 0,
                   simulated_challans=len(challans),
                   note='Tracking IDs are not a verified count of distinct physical vehicles. Uncalibrated speed is unknown.')
    path = ROOT / 'reports' / f'{run_id}_summary.json'
    path.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
    return path


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    export(parser.parse_args().run)
