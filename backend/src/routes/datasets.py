from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.config.database import get_db
from src.models import Dataset, DatasetGrant, Job, User
from src.schemas.dataset import DatasetInput, GrantInput, ScopeInput
from src.middlewares.auth import current_user, can_write, admin_only
from src.services import datasets, access
from src.services.audit import record
from src.utils.serialization import dataset_dict, grant_dict
router=APIRouter(prefix='/datasets')
def get_dataset_or_404(db,id):
    d=db.get(Dataset,id)
    if not d:raise HTTPException(404,'数据批次不存在')
    return d
@router.get('')
def listing(db=Depends(get_db),u=Depends(current_user)):
    ids=access.accessible_dataset_ids(db,u)
    q=select(Dataset).order_by(Dataset.id.desc())
    if ids is not None:q=q.where(Dataset.id.in_(ids))
    return [dataset_dict(d) for d in db.scalars(q)]
@router.post('',status_code=201)
def create(data:DatasetInput,db=Depends(get_db),u=Depends(can_write)):
    d=datasets.create(db,data)
    if u.role!='admin':access.grant(db,d,u,u.email) # 新批次默认私有，创建者自动获得授权
    record(db,u.email,'dataset.create',{'id':d.id,'rows':len(d.records),'visibility':d.visibility})
    db.commit(); return dataset_dict(d)
@router.get('/{id}')
def detail(id:int,db=Depends(get_db),u=Depends(current_user)):
    d=get_dataset_or_404(db,id)
    if not access.can_access_dataset(db,u,d):raise HTTPException(403,'未获负责人授权，无法读取该批次')
    return {**dataset_dict(d),'records':d.records}
@router.get('/{id}/grants')
def grants(id:int,db=Depends(get_db),u=Depends(admin_only)):
    d=get_dataset_or_404(db,id)
    users={x.id:x for x in db.scalars(select(User))}
    items=[grant_dict(g,users.get(g.user_id)) for g in db.scalars(select(DatasetGrant).where(DatasetGrant.dataset_id==d.id).order_by(DatasetGrant.id))]
    cancelled=[{'id':j.id,'name':j.name,'created_by':j.created_by,'cancel_reason':j.cancel_reason,'finished_at':j.finished_at} for j in db.scalars(select(Job).where(Job.dataset_id==d.id,Job.status=='cancelled').order_by(Job.id.desc()))]
    return {'dataset':dataset_dict(d),'grants':items,'cancelled_jobs':cancelled}
@router.post('/{id}/grants',status_code=201)
def grant_create(id:int,data:GrantInput,db=Depends(get_db),u=Depends(admin_only)):
    d=get_dataset_or_404(db,id)
    target=db.get(User,data.user_id)
    if not target:raise HTTPException(404,'账号不存在')
    if target.role=='admin':raise HTTPException(422,'负责人默认拥有全部批次权限，无需授权')
    if db.scalar(select(DatasetGrant.id).where(DatasetGrant.dataset_id==d.id,DatasetGrant.user_id==target.id)):
        raise HTTPException(409,'该账号已获该批次授权')
    g=access.grant(db,d,target,u.email)
    record(db,u.email,'dataset.grant',{'dataset':d.id,'user':target.email})
    db.commit(); return grant_dict(g,target)
@router.delete('/{id}/grants/{user_id}')
def grant_revoke(id:int,user_id:int,db=Depends(get_db),u=Depends(admin_only)):
    d=get_dataset_or_404(db,id)
    g=db.scalar(select(DatasetGrant).where(DatasetGrant.dataset_id==d.id,DatasetGrant.user_id==user_id))
    if not g:raise HTTPException(404,'该账号没有该批次授权')
    target=db.get(User,user_id)
    db.delete(g)
    reason=f'批次「{d.name}」授权被负责人 {u.email} 撤销'
    cancelled=access.cancel_unfinished(db,d.id,user_id,reason)
    record(db,u.email,'dataset.revoke',{'dataset':d.id,'user':target.email if target else user_id,'cancelled_jobs':cancelled})
    db.commit(); return {'revoked':user_id,'cancelled_jobs':cancelled}
@router.post('/{id}/scope')
def set_scope(id:int,data:ScopeInput,db=Depends(get_db),u=Depends(admin_only)):
    d=get_dataset_or_404(db,id)
    previous=d.visibility
    d.visibility=data.visibility; d.scope_confirmed=True
    cancelled=[]
    if d.visibility=='private':
        # 转为私有相当于对未授权账号撤权：取消其未完成的分析
        granted={g.user_id for g in db.scalars(select(DatasetGrant).where(DatasetGrant.dataset_id==d.id))}
        reason=f'批次「{d.name}」共享范围被负责人 {u.email} 确认为私有，账号未获授权'
        creators={j.created_by for j in db.scalars(select(Job).where(Job.dataset_id==d.id,Job.status.in_(['queued','running'])))}
        for uid in creators:
            if uid in granted:continue
            creator=db.get(User,uid)
            if creator and creator.role!='admin':cancelled+=access.cancel_unfinished(db,d.id,uid,reason)
    record(db,u.email,'dataset.scope',{'dataset':d.id,'from':previous,'to':d.visibility,'confirmed':True,'cancelled_jobs':cancelled})
    db.commit(); return dataset_dict(d)
