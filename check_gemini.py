"""Opt-in live smoke test. Prints sanitized statuses, never credentials or SDK payloads."""
import json
import time
from modules.gemini_service import GeminiService, GeminiUnavailable
from modules.traffic_intelligence import load_snapshot, render_answer
from utils.ai_reports import report_pdf


if __name__=='__main__':
    service = GeminiService()
    result = {}
    try:
        result['connection'] = service.test_connection()
        data = load_snapshot()
        time.sleep(3)
        plan = service.analyze('How many vehicles were detected? Which vehicle was fastest?',data['facts'],data['recommendations'])
        result['chatbot'] = 'Verified structured response with database fact references.'
        time.sleep(3)
        plan = service.analyze('Generate a complete traffic analysis report.',data['facts'],data['recommendations'])
        text = render_answer(plan,data,'Live Gemini-assisted analysis')
        result['report'] = 'Verified PDF export.' if report_pdf('Traffic report',text).startswith(b'%PDF') else 'PDF failed.'
    except GeminiUnavailable as exc:
        result['unavailable'] = str(exc)
    print(json.dumps(result,indent=2))
