import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from src.config.database import get_db
from src.config.settings import ARTIFACT_DIR
from src.models import Dataset, Job, Report, Delivery
from src.schemas.report import ReportInput
from src.middlewares.auth import current_user, admin_only
from src.services import reports, access
from src.services.audit import record
from src.utils.serialization import report_dict, delivery_dict
router=APIRouter()
def accessible_job_ids(db,u):
    ids=access.accessible_dataset_ids(db,u)
    if ids is None:return None
    return set(db.scalars(select(Job.id).where(Job.dataset_id.in_(ids)))) or {-1}
@router.get('/reports')
def listing(db=Depends(get_db),u=Depends(current_user)):
    job_ids=accessible_job_ids(db,u)
    q=select(Report).order_by(Report.id.desc())
    if job_ids is not None:q=q.where(Report.job_id.in_(job_ids))
    return [report_dict(r) for r in db.scalars(q)]
@router.post('/reports',status_code=201)
def create(data:ReportInput,db=Depends(get_db),u=Depends(admin_only)):
    r=reports.create(db,data); record(db,u.email,'report.schedule',{'id':r.id,'destination':r.destination}); db.commit()
    return report_dict(r)
@router.post('/reports/{id}/toggle')
def toggle(id:int,db=Depends(get_db),u=Depends(admin_only)):
    r=db.get(Report,id)
    if not r:raise HTTPException(404,'分发计划不存在')
    r.enabled=not r.enabled;record(db,u.email,'report.toggle',{'id':id,'enabled':r.enabled});db.commit()
    return report_dict(r)
@router.get('/deliveries')
def deliveries(db=Depends(get_db),u=Depends(current_user)):
    job_ids=accessible_job_ids(db,u)
    q=select(Delivery).join(Report,Delivery.report_id==Report.id).order_by(Delivery.id.desc()).limit(100)
    if job_ids is not None:q=q.where(Report.job_id.in_(job_ids))
    return [delivery_dict(d) for d in db.scalars(q)]
@router.get('/deliveries/{id}/download')
def download(id:int,format:str='csv',db=Depends(get_db),u=Depends(current_user)):
    d=db.get(Delivery,id)
    if not d:raise HTTPException(404,'归档不存在')
    report=db.get(Report,d.report_id)
    job=db.get(Job,report.job_id) if report else None
    if not job or not access.can_access_dataset(db,u,db.get(Dataset,job.dataset_id)):
        raise HTTPException(403,'未获负责人授权，无法下载该归档')
    if format not in ('csv','json'):raise HTTPException(422,'支持 CSV 或 JSON')
    filename=d.filename+('.json' if format=='json' else '')
    p=os.path.join(ARTIFACT_DIR,filename)
    if not os.path.exists(p):raise HTTPException(404,'归档文件不存在，请重新安排分发')
    return FileResponse(p,filename=filename,media_type='application/json' if format=='json' else 'text/csv; charset=utf-8')
