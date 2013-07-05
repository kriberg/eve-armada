from subprocess import call
import sys
import keyword
from tempfile import NamedTemporaryFile
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, DEFAULT_DB_ALIAS, transaction
from armada.settings import DATABASES
from armada.eve.management.commands import start_task, end_task, fail_task

INITIAL_SQLS = ('data/eve_typeattributes_view.sql',
        'data/eve_invtypes_view.sql')

CAPSULER_API_DATA_TABLES = ('capsuler_userpilotproperty',
        'capsuler_userpilotskill',
        'capsuler_userpilotcertificate',
        'capsuler_userpilotaugmentor',
        'capsuler_asset',
        'corporation_corporationasset')


class Command(BaseCommand):
    help = "Upgrades current database with a new SDE dump"
    args = "[Database dump file]"
    option_list = BaseCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to '
                'introspect.  Defaults to using the "default" database.'),
    )

    requires_model_validation = False

    db_module = 'django.db'

    def handle(self, *args, **options):
        if not len(args) == 1:
            raise CommandError("Please supply a database dump")
        dumpfile = args[0]
        dbalias = options.get('database', DEFAULT_DB_ALIAS)

        connection = connections[dbalias]
        cursor = connection.cursor()
        cursor.execute("select tablename from pg_tables where schemaname='public'")
        table_names = [row[0] for row in cursor.fetchall()]
        if len(table_names) == 0:
            print 'Your database is empty, do you want to initialize it with this dumpfile?'
            choice = raw_input('(y/n): ')
            if choice == 'y':
                self.import_dumpfile(dbalias, dumpfile)
            else:
                sys.exit(0)
            with transaction.atomic():
                sde_table_names = self.get_database_tables(cursor)
                self.initiate_custom_tables(sde_table_names, cursor)
                self.update_sde_table(sde_table_names, dumpfile, cursor)
            print 'Installation complete!'
        else:
            print 'Did you take a backup of your database?'
            choice = raw_input('(y/n): ')
            if not choice == 'y':
                print 'Do it now!'
                sys.exit(1)
            with transaction.atomic():
                database_table_names = self.get_database_tables(cursor)
                start_task('Checking eve_sde_table')
                if not 'eve_sde_table' in database_table_names:
                    with open('data/eve_sde_table.sql', 'r') as f:
                        sql = f.read()
                        try:
                            cursor.execute(sql)
                        except:
                            pass
                end_task()
                sde_table_names = self.get_sde_tables(cursor)
                non_sde_tables = filter(lambda x: not x in sde_table_names,
                        database_table_names)
                create_constraints = self.generate_create_constraints(non_sde_tables,
                        cursor)
                drop_constraints = self.generate_drop_constraints(database_table_names,
                        cursor)

            with transaction.atomic():
                start_task('Dropping constraints')
                for sql in drop_constraints:
                    cursor.execute(sql)
                end_task()
            with transaction.atomic():
                start_task('Deleting API fetched data')
                for table_name in CAPSULER_API_DATA_TABLES:
                    if table_name in non_sde_tables:
                        sql = 'DELETE FROM %s' % table_name
                        cursor.execute(sql)
                end_task()
                start_task('Dropping SDE tables')
                self.drop_tables(sde_table_names, cursor)
                end_task()
            start_task('Importing new SDE dump')
            logfile = self.import_dumpfile(dbalias, dumpfile)
            end_task()
            print '  Imported "%s" to database "%s", logfile "%s".' % (dumpfile,
                DATABASES[dbalias]['NAME'], logfile)
            with transaction.atomic():
                post_import_tables = self.get_database_tables(cursor)
                new_sde_tables = filter(lambda x: not x in non_sde_tables,
                        post_import_tables)
                start_task('Updating SDE table names')
                self.update_sde_table(new_sde_tables, dumpfile, cursor)
                end_task()
                start_task('Re-creating constraints')
                broken_constraints = []
                for sql in create_constraints:
                    try:
                        cursor.execute(sql)
                    except:
                        broken_constraints.append(sql)
                if len(broken_constraints) > 0:
                    scriptfile = NamedTemporaryFile(suffix='.sql',
                            prefix='armada_constraints_',
                            delete=False)
                    with scriptfile as f:
                        f.write("\n".join(create_constraints))

                    fail_task('Error while re-enabling %d constraints. This usually \
                            happens because data in the CCP SDE has changed primary keys. \
                            Writing script to generate the broken constraints to "%s". Try \
                            to run it manually and fix the broken data by hand' %
                            (len(broken_constraints), scriptfile.name))
                    sys.exit(1)
                end_task()

                start_task('Creating missing armada tables')
                new_tables = self.initiate_custom_tables(database_table_names, cursor)
                end_task()
                if len(new_tables) > 0:
                    for name in new_tables:
                        print '\t%s added.' % name
            print 'Upgrade complete!'

    def get_database_tables(self, cursor):
        cursor.execute("select tablename from pg_tables where \
                schemaname='public' order by tablename")
        return [row[0] for row in cursor.fetchall()]

    def get_sde_tables(self, cursor):
        cursor.execute('select max(batch) from eve_sde_table')
        batch = cursor.fetchone()[0]
        cursor.execute('select name from eve_sde_table where batch=%s',
                (batch,))
        return [row[0] for row in cursor.fetchall()]

    def update_sde_table(self, sde_table_names, dumpfile, cursor):
        cursor.execute('select max(batch) from eve_sde_table')
        batch = cursor.fetchone()
        if len(batch) == 0:
            batch = 0
        else:
            batch = int(batch[0]) + 1
        for name in sde_table_names:
            cursor.execute('insert into eve_sde_table (batch, name, updated, \
                    dumpfile) values (%s, %s, now(), %s)',
                    (batch, name, dumpfile))

    def disable_tables(self, table_names, cursor):
        for table_name in table_names:
            disable_sql = 'ALTER TABLE %s DISABLE TRIGGER USER' % table_name
            print disable_sql
            cursor.execute(disable_sql)

    def generate_create_constraints(self, table_names, cursor):
        sql = """SELECT 'ALTER TABLE '||nspname||'.'||relname||' ADD CONSTRAINT '||conname||' '||
            pg_get_constraintdef(pg_constraint.oid)||';'
            FROM pg_constraint
            INNER JOIN pg_class ON conrelid=pg_class.oid
            INNER JOIN pg_namespace ON pg_namespace.oid=pg_class.relnamespace
            WHERE nspname='public' AND relname IN %s
            ORDER BY CASE WHEN contype='f' THEN 0 ELSE 1 END DESC,contype DESC,
            nspname DESC,relname DESC,conname DESC;"""
        cursor.execute(sql, (tuple(table_names),))
        return [r[0] for r in cursor.fetchall()]

    def generate_drop_constraints(self, table_names, cursor):
        sql = """SELECT 'ALTER TABLE '||nspname||'.'||relname||' DROP CONSTRAINT '||conname||';'
            FROM pg_constraint
            INNER JOIN pg_class ON conrelid=pg_class.oid
            INNER JOIN pg_namespace ON pg_namespace.oid=pg_class.relnamespace
            WHERE nspname='public' AND relname IN %s
            ORDER BY CASE WHEN contype='f' THEN 0 ELSE 1 END,contype,nspname,relname,conname"""
        cursor.execute(sql, (tuple(table_names),))
        return [r[0] for r in cursor.fetchall()]

    def initiate_custom_tables(self, dbtables, cursor):
        new_files = []
        for sqlfile in INITIAL_SQLS:
            table_name = sqlfile.replace('data/','').replace('.sql','')
            if table_name in dbtables:
                continue
            with open(sqlfile, 'r') as f:
                sql = f.read()
                try:
                    cursor.execute(sql)
                    new_files.append(sqlfile)
                except:
                    pass
        return new_files

    def drop_tables(self, table_names, cursor):
        for table in table_names:
            sql = 'DROP TABLE %s CASCADE;' % table
            cursor.execute(sql)

    def import_dumpfile(self, dbalias, dumpfile):
        #TODO: fix this to handle username/password
        log = NamedTemporaryFile(prefix='sde_import_', suffix='.log',
                delete=False)
        with log:
            opcode = call(['psql -f %s %s' % (dumpfile,
                DATABASES[dbalias]['NAME']),],
                    stdout=log,
                    stderr=log,
                    shell=True)
        if opcode != 0:
            print """Looks like something went wrong, did you jump instead of
                    bridge?! Check the import log at "%s".""" % log.name
            sys.exit(opcode)
        return log.name

