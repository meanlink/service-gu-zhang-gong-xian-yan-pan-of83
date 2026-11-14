import time, json, logging
from pathlib import Path
from sqlalchemy import select
from redis import Redis
from src.config.database import Session
from src.config.settings import REDIS_URL
from src.models import Job, Dataset, Report
from src.services.business import analyze
from src.services.reports import deliver
from src.services.access import creator_has_access
from src.services.audit import record
logging.basicConfig(level=logging.INFO)
def execute(job_id):
    with Session() as db:
        j=db.get(Job,job_id)
        if not j or j.status!='queued':return
        if not creator_has_access(db,j):
            j.status='cancelled';j.cancel_reason='批次授权已撤销，任务未执行';j.finished_at=time.time()
            record(db,'worker','job.cancelled',{'id':j.id,'reason':j.cancel_reason});db.commit();return
        j.status='running'; db.commit()
        dataset_id,params=j.dataset_id,dict(j.params)
    try:
        with Session() as db:
            records=list(db.get(Dataset,dataset_id).records)
        result=analyze(records,params)
        json.dumps(result,allow_nan=False)
        finalize(job_id,result=result)
    except Exception as e:
        logging.exception('Analysis failed')
        finalize(job_id,error=str(e)[:990])
def finalize(job_id,result=None,error=None):
    """仅在任务仍处于 running 且创建者仍获授权时写入结果；与撤权并发时取消优先，结果不落库。"""
    with Session() as db:
        j=db.get(Job,job_id,with_for_update=True)
        if not j or j.status!='running':return # 已被撤权取消，丢弃计算结果
        if error is None and not creator_has_access(db,j):
            j.status='cancelled';j.cancel_reason='批次授权已撤销，计算结果未写入';j.finished_at=time.time()
            record(db,'worker','job.cancelled',{'id':j.id,'reason':j.cancel_reason})
        elif error is None:
            j.result=result;j.status='completed';j.finished_at=time.time()
            record(db,'worker','job.completed',{'id':j.id})
        else:
            j.status='failed';j.error=error;j.finished_at=time.time()
            record(db,'worker','job.failed',{'id':j.id,'error':j.error})
        db.commit()
def tick():
    with Session() as db:
        queued=list(db.scalars(select(Job.id).where(Job.status=='queued').limit(3)))
    for job_id in queued:execute(job_id)
    with Session() as db:
        for r in db.scalars(select(Report).where(Report.enabled==True,Report.next_run<=time.time())):
            d=deliver(db,r)
            if d:record(db,'worker','report.delivered',{'id':r.id,'delivery':d.id})
        db.commit()
def main():
    r=Redis.from_url(REDIS_URL,socket_timeout=3)
    # This Compose stack has a single worker. A crash must not strand its jobs.
    # 仅恢复 running 任务；已取消任务保持取消，重启或再次授权都不会复活。
    with Session() as db:
        for j in db.scalars(select(Job).where(Job.status=='running')):
            j.status='queued';record(db,'worker','job.recovered',{'id':j.id})
        db.commit()
    while True:
        Path('/tmp/heartbeat').touch()
        try:
            item=r.blpop('analysis:queue',timeout=1)
            if item:execute(int(item[1]))
            tick()
        except Exception:
            logging.exception('Worker retry');time.sleep(2)
if __name__=='__main__':main()
