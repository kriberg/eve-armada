from celery.execute import send_task
from tasks import TASK_TIMERS
from datetime import datetime

def dispatch(session, task_name, context, *args, **kwargs):
    cached_stamp = session.get(task_name)
    if cached_stamp:
        age = (datetime.now() - cached_stamp).total_seconds()
        if age < TASK_TIMERS[task_name]:
            return None
    result = send_task(task_name, *args, **kwargs)
    session[result.task_id] = {'result': result,
            'task_name': task_name,
            'context': context}
    session[task_name] = datetime.now()
    return result.task_id

