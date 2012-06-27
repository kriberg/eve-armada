#!/usr/bin/env python 
from django.core.management import execute_manager, setup_environ
import sys
try:
    import settings # Assumed to be in the same directory. 
except ImportError:
    sys.stderr.write("""Error: Can't find the file 'settings.py' in the 
directory containing %r. It appears you've customized things.\nYou'll 
have to run django-admin.py, passing it your settings module.\n(If the 
file settings.py does indeed exist, it's causing an ImportError 
somehow.)\n""" % __file__)
    sys.exit(1)
project_directory = setup_environ(settings)
from django.db.models.loading import get_models
loaded_models = get_models()
if sys.argv and len(sys.argv) > 1:
    exec(open(sys.argv[1],'r').read())
else:
    print 'test_shell.py <module>'
