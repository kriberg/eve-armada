from celery.execute import send_task
from tasks import TASK_TIMERS
from datetime import datetime

def dispatch(session, task_name, *args, **kwargs):
    task_key = '%s%s' % (task_name, args)
    cached_stamp = session.get(task_key)
    if cached_stamp:
        age = (datetime.now() - cached_stamp).total_seconds()
        if age < TASK_TIMERS[task_name]:
            return None
    result = send_task(task_name, *args, **kwargs)
    session[result.task_id] = {'task': result, 'params': kwargs}
    session[task_key] = datetime.now()
    return result.task_id

