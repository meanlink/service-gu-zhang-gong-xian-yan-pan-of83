from sqlalchemy import inspect, text
from src.config.database import Base, engine
from src import models
def migrate():
    Base.metadata.create_all(engine)
    insp = inspect(engine)
    dataset_cols = {c['name'] for c in insp.get_columns('datasets')}
    job_cols = {c['name'] for c in insp.get_columns('jobs')}
    with engine.begin() as conn:
        if 'visibility' not in dataset_cols:
            conn.execute(text("ALTER TABLE datasets ADD COLUMN visibility VARCHAR(20)"))
        if 'scope_confirmed' not in dataset_cols:
            conn.execute(text("ALTER TABLE datasets ADD COLUMN scope_confirmed BOOLEAN"))
        if 'cancel_reason' not in job_cols:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN cancel_reason VARCHAR(500)"))
        # 存量批次保持原共享读取行为，共享范围待负责人确认后生效；新批次由应用层默认私有
        conn.execute(text("UPDATE datasets SET visibility='shared' WHERE visibility IS NULL"))
        conn.execute(text("UPDATE datasets SET scope_confirmed=:confirmed WHERE scope_confirmed IS NULL"), {'confirmed': False})
        conn.execute(text("UPDATE jobs SET cancel_reason='' WHERE cancel_reason IS NULL"))
if __name__=='__main__':migrate()
