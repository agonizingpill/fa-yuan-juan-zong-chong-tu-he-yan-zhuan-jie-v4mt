import logging,time,json
from pathlib import Path
from .database import Session
from .models import Triage,Intake
from .triage_service import queue
from .algorithm import classify
logging.basicConfig(level=logging.INFO)
while True:
    Path('/tmp/worker-heartbeat').touch()
    try:
        item=queue.blpop('aid:triage',timeout=2)
        if not item:continue
        with Session() as db:
            row=db.get(Triage,int(item[1]))
            if not row or row.status!='queued':continue
            row.status='running';db.commit()
            try:
                case=db.get(Intake,row.intake_id)
                if case.facts_version!=row.facts_version:raise ValueError('事实版本已更新，请重新提交')
                row.predicted,row.confidence,row.metrics=classify(case.facts);row.manual_required=row.confidence<.68;row.status='done'
                Path('/artifacts').mkdir(exist_ok=True);Path(f'/artifacts/triage-{row.id}.json').write_text(json.dumps(row.metrics,ensure_ascii=False))
            except Exception as e:row.status='failed';row.error=str(e)[:200]
            db.commit()
    except Exception:logging.exception('triage loop');time.sleep(1)
