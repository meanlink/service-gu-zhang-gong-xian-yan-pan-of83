import time
from sqlalchemy import select, update
from src.models import Dataset, DatasetGrant, Job, User
def accessible_dataset_ids(db, user):
    """返回该账号可读取的批次 id 集合；负责人返回 None 表示不受限。"""
    if user.role == 'admin':
        return None
    granted = select(DatasetGrant.dataset_id).where(DatasetGrant.user_id == user.id)
    rows = db.scalars(select(Dataset.id).where((Dataset.visibility == 'shared') | (Dataset.id.in_(granted))))
    return set(rows)
def can_access_dataset(db, user, dataset):
    if dataset is None:
        return False
    if user.role == 'admin' or dataset.visibility == 'shared':
        return True
    return db.scalar(select(DatasetGrant.id).where(DatasetGrant.dataset_id == dataset.id, DatasetGrant.user_id == user.id)) is not None
def creator_has_access(db, job):
    """worker 写入结果前的最终校验：任务创建者当前是否仍获授权读取该批次。"""
    user = db.get(User, job.created_by)
    if user is None:
        return False
    dataset = db.get(Dataset, job.dataset_id)
    return can_access_dataset(db, user, dataset)
def cancel_unfinished(db, dataset_id, user_id, reason):
    """撤权即时生效：条件更新取消该账号在此批次上未完成的分析，返回实际取消的任务 id。
    与 worker 写入并发时以行锁串行化：已完成任务不被覆盖，已取消任务不被复活。"""
    ids = list(db.scalars(select(Job.id).where(Job.dataset_id == dataset_id, Job.created_by == user_id, Job.status.in_(['queued', 'running']))))
    cancelled = []
    for job_id in ids:
        res = db.execute(update(Job).where(Job.id == job_id, Job.status.in_(['queued', 'running'])).values(status='cancelled', cancel_reason=reason, finished_at=time.time()))
        if res.rowcount:
            cancelled.append(job_id)
    return cancelled
def grant(db, dataset, user, actor):
    existing = db.scalar(select(DatasetGrant).where(DatasetGrant.dataset_id == dataset.id, DatasetGrant.user_id == user.id))
    if existing:
        return existing
    g = DatasetGrant(dataset_id=dataset.id, user_id=user.id, granted_by=actor, created_at=time.time())
    db.add(g)
    db.flush()
    return g
