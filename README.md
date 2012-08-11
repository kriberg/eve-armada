eve-armada
==========

## About

EVE Armada is a website to explore the eve universe and your characters,
corporations and alliances.

## Installation

To setup armada, you will need the following:
* git
* virtualenv
* python 2.7
* pip
* postgresql (with devel package)
* rabbitmq

Install the respective packages, create a database named armada and make sure
your user has access to that.

### Virtualenv
Setup a virtualenv to run armada:

<pre>
mkdir eve-armada
cd eve-armada
virtualenv env
</pre>

### Clone eve-aramada from github.

<pre>
git clone git://github.com/kriberg/eve-armada.git
</pre>

### Install requirements
Activate the virtualenv and install eve-armada python requirements.

<pre>
source env/bin/activate
pip install -r requirements.txt
</pre>

### local\_settings.py
Setup your local\_settings.py with your database configuration, celery broker
configuration, media root, smtp settings etc.

### Install eve SDE
Grab one of the postgresql eve SDE conversions from <http://zofu.no-ip.de/> and
import it into the database you created. The reloaddb script is only intended
for development environments, as it will scratch your entire database when run.
Import the dump will probably take quite a while. The script will also create
the file ``eve_table_names.txt``, which will be used to generate models for the
SDE tables.

<pre>
cd data
wget http://zofu.no-ip.de/inf12/inf12-pgsql-v1-unquoted-compatible.sql.bz2
bunzip2 inf12-pgsql-v1-unquoted-compatible.sql.bz2
./reloaddb.sh inf12-pgsql-v1-unquoted-compatible.sql
cd ..
</pre>

### Generate SDE models
After loading the eve static data export, we generate the django models for the
dump and put those in eve/ccpmodels.py.

<pre>
cd armada
python manage.py generateevemodels ../data/eve_table_names.txt > eve/ccpmodels.py
</pre>

### Fix compound keys
The SDE uses compound primary keys for some tables, which django in turn
doesn't support.  For these, we will need to add single-column primary keys.
The generateevemodels management command will detect these tables and add some
sql, for you to run, at the end of eve/ccpmodels.py.  Copypaste that into a
psql prompt to create the needed columns.

### Syncdb
Run syncdb to create the remaining tables.

<pre>
python manage.py syncdb
</pre>

### Starting the dev servers
If everything is in order, you should now be able to start the dev server and
the celery demon and the python-smtpd loopback in separate terminals

<pre>
python manage.py runserver
python manage.py celeryd -l info
python -m smtpd -n -c DebuggingServer localhost:1025
</pre>

Point your browser to http://localhost:8000/ and register a new user, add api
keys and add some pilots
