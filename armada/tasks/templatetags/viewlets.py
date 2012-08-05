from django import template
register = template.Library()

@register.simple_tag()
def task_loader(task):
    if not task:
        return ''
    else:
        if task.taskid:
            output = '''
            <div id="%s">
                <img src="/static/core/img/spinner.gif" alt="spinner" />
                <script type="text/javascript">
                    delayed_load("%s", "%s", "%s");
                </script>
            </div>
            ''' % (task.taskid, task.taskid, task.get_url(), task.taskid)
            return output
        else:
            return task.render()

