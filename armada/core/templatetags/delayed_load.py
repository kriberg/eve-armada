from django import template
register = template.Library()

@register.simple_tag()
def delayed_load(url, taskid):
    output = '''
    <div id="%s">
        <img src="/static/core/img/spinner.gif" alt="spinner" />
        <script type="text/javascript">
            delayed_load("%s", "%s", "%s");
        </script>
    </div>
    ''' % (taskid, taskid, url, taskid)
    return output

