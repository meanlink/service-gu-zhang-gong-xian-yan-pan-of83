from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from src.config.database import get_db
from src.middlewares.auth import current_user
from src.models import Dataset, Job, Report, Audit
from src.services import access
from src.services.business import metadata
router=APIRouter()
@router.get('/meta')
def meta():return metadata()
@router.get('/overview')
def overview(db=Depends(get_db),user=Depends(current_user)):
    ids=access.accessible_dataset_ids(db,user)
    dq=select(Dataset); jq=select(Job)
    if ids is not None:
        dq=dq.where(Dataset.id.in_(ids)); jq=jq.where(Job.dataset_id.in_(ids))
    datasets=db.scalars(dq).all()
    jobs=db.scalars(jq).all()
    job_ids={j.id for j in jobs}
    reports=db.scalar(select(func.count()).select_from(Report).where(Report.job_id.in_(job_ids))) if ids is not None else db.scalar(select(func.count()).select_from(Report))
    return {'datasets':len(datasets), 'records':sum(len(d.records) for d in datasets), 'jobs':len(jobs), 'approved':sum(1 for j in jobs if j.approved), 'reports':reports}
@router.get('/audits')
def audits(db=Depends(get_db),user=Depends(current_user)):
    return [{'id':a.id,'actor':a.actor,'action':a.action,'detail':a.detail,'at':a.at} for a in db.scalars(select(Audit).order_by(Audit.id.desc()).limit(50))]
