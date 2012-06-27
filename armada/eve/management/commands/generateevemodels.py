import keyword
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, DEFAULT_DB_ALIAS
from pprint import pprint




class Command(BaseCommand):
    help = "Introspects the database and generates a django model module for the Eve database dump"
    args = "[Text file with table names from eve database dump]"
    option_list = BaseCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database to '
                'introspect.  Defaults to using the "default" database.'),
    )

    requires_model_validation = False

    db_module = 'django.db'


    def handle(self, *args, **options):
        if not len(args) == 1:
            raise CommandError("Eve database loader needs a text file with table names")

        self.eve_table_names = [l.strip() for l in open(args[0],'r').readlines()]
        self.table2model_mapping = {}
        for name in self.eve_table_names:
            if not len(name) > 1:
                continue
            self.table2model_mapping[name] = self.table2model(name[0].upper()+name[1:])
        try:
            for line in self.handle_inspection(options):
                self.stdout.write("%s\n" % line)
        except NotImplementedError:
            raise CommandError("Database inspection isn't supported for the currently selected database backend.")
    def table2model(self, n):
        n = n.replace('_', '').replace(' ', '').replace('-', '')
        if n.lower().startswith('translation'):
            n = 'Translation' + n[11:].title()
        elif n.lower().startswith('planet'):
            n = 'Planet' + n[6:].title()
        else:
            n = n[:3].title() + n[3:].title()

        if n.endswith('ies'):
            return n[:-3]+'y'
        elif n.lower().endswith('classes'):
            return n[:-2]
        elif n.endswith('s'):
            return n[:-1]
        else:
            return n

    def handle_inspection(self, options):
        connection = connections[options.get('database', DEFAULT_DB_ALIAS)]
        tables_for_fix = []

        cursor = connection.cursor()
        yield "# This is an auto-generated Django model module."
        yield "# You'll have to do the following manually to clean this up:"
        yield "#     * Rearrange models' order"
        yield "#     * Make sure each model has one field with primary_key=True"
        yield "# Feel free to rename the models, but don't rename db_table values or field names."
        yield "#"
        yield "# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'"
        yield "# into your database."
        yield ''
        yield 'from %s import models' % self.db_module
        yield ''
        for table_name in connection.introspection.get_table_list(cursor):
            if table_name not in self.eve_table_names:
                continue
            has_pk = False
            suitable_str = None
            primary_key = ''

            yield 'class %s(models.Model):' % self.table2model_mapping[table_name]
            try:
                relations = connection.introspection.get_relations(cursor, table_name)
            except NotImplementedError:
                relations = {}

            try:
                indexes = connection.introspection.get_indexes(cursor, table_name)
                # Some of the eve tables have composite keys. We need to find those and fix them as django don't like those
                for index_name in indexes:
                    if indexes[index_name]['primary_key']:
                        has_pk = True
                        primary_key = index_name
                        break
            except NotImplementedError:
                indexes = {}

            for i, row in enumerate(connection.introspection.get_table_description(cursor, table_name)):
                column_name = row[0]
                att_name = column_name.lower()
                comment_notes = [] # Holds Field notes, to be displayed in a Python comment.
                extra_params = {}  # Holds Field parameters such as 'db_column'.

                # If the column name can't be used verbatim as a Python
                # attribute, set the "db_column" for this Field.
                if ' ' in att_name or '-' in att_name or keyword.iskeyword(att_name) or column_name != att_name:
                    extra_params['db_column'] = column_name

                # Modify the field name to make it Python-compatible.
                if ' ' in att_name:
                    att_name = att_name.replace(' ', '_')
                    comment_notes.append('Field renamed to remove spaces.')

                if '-' in att_name:
                    att_name = att_name.replace('-', '_')
                    comment_notes.append('Field renamed to remove dashes.')

                if column_name != att_name:
                    comment_notes.append('Field name made lowercase.')

                if i in relations:
                    rel_to = relations[i][1]
                    rel_name = self.table2model_mapping[rel_to]
                    if rel_to == table_name:
                        field_type = 'ForeignKey(\'%s\', related_name=\'%s\'' % ('self',
                                '%s_%s_%d' % (table_name.lower(), rel_to ,i)
                                )
                    else:
                        field_type = 'ForeignKey(\'%s\', related_name=\'%s\'' % (rel_name,
                                '%s_%s_%d' % (table_name.lower(), rel_to ,i)
                                )
                    if att_name == primary_key:
                        extra_params['primary_key'] = True
                    if att_name.endswith('id') and att_name != primary_key:
                        att_name = att_name[:-2]
                        extra_params['db_column'] = column_name
                else:
                    # Calling `get_field_type` to get the field type string and any
                    # additional paramters and notes.
                    field_type, field_params, field_notes = self.get_field_type(connection, table_name, row)
                    extra_params.update(field_params)
                    comment_notes.extend(field_notes)

                    # Add primary_key and unique, if necessary.
                    if column_name in indexes:
                        if indexes[column_name]['primary_key']:
                            extra_params['primary_key'] = True
                        elif indexes[column_name]['unique']:
                            extra_params['unique'] = True

                    field_type += '('

                    # Make some educated guesses about field type, names and __str__
                    if 'CharField' in field_type:
                        wildguesses = self.table2model_mapping[table_name][3:]
                        if wildguesses.endswith('s'):
                            wildguesses = wildguesses[:-1]
                        if wildguesses.lower() in column_name and 'name' in column_name:
                            suitable_str = column_name

                if keyword.iskeyword(att_name):
                    att_name += '_field'
                    comment_notes.append('Field renamed because it was a Python reserved word.')

                # Don't output 'id = meta.AutoField(primary_key=True)', because
                # that's assumed if it doesn't exist.
                if att_name == 'id' and field_type == 'AutoField(' and 'primary_key' in extra_params and extra_params['primary_key']:
                    continue

                # Let's disregard all that and slap rename some columns!
                if att_name == primary_key:
                    extra_params['db_column'] = att_name
                    att_name = 'id'

                # In case of database upgrades, we could have hofixed the id field, but it isn't marked
                # as primary_key. Just slap the primary_key attribute on the column, regardless of what
                # postgre tells us. Fyeah!
                if column_name == 'id' and field_type == 'IntegerField(':
                    extra_params['primary_key'] = True
                    has_pk=True

                # Add 'null' and 'blank', if the 'null_ok' flag was present in the
                # table description.
                if row[6]: # If it's NULL...
                    extra_params['blank'] = True
                    if not field_type in ('TextField(', 'CharField('):
                        extra_params['null'] = True

                field_desc = '%s = models.%s' % (att_name, field_type)
                if extra_params:
                    if not field_desc.endswith('('):
                        field_desc += ', '
                    field_desc += ', '.join(['%s=%r' % (k, v) for k, v in extra_params.items()])
                field_desc += ')'
                if comment_notes:
                    field_desc += ' # ' + ' '.join(comment_notes)
                yield '    %s' % field_desc
            if not has_pk:
                tables_for_fix.append(table_name)
                yield '    id = models.IntegerField(primary_key=True) # Autogenerated substitute primary key for composite key'
            if suitable_str:
                yield '    def __unicode__(self):'
                yield '        return self.%s' % suitable_str
            for meta_line in self.get_meta(table_name):
                yield meta_line
        if len(tables_for_fix) > 0:
            yield '# The following SQL has to be run in the database to retrofit some tables with a non-composite primary key'
            yield '"""'
            for table in tables_for_fix:
                yield 'ALTER TABLE "%s" ADD COLUMN id SERIAL NOT NULL;' % table
                yield 'CREATE INDEX "%s_id_idx" ON "%s" USING btree(id);' % (table, table)
            yield '"""'

    def get_field_type(self, connection, table_name, row):
        """
        Given the database connection, the table name, and the cursor row
        description, this routine will return the given field type name, as
        well as any additional keyword parameters and notes for the field.
        """
        field_params = {}
        field_notes = []

        try:
            field_type = connection.introspection.get_field_type(row[1], row)
        except KeyError:
            field_type = 'TextField'
            field_notes.append('This field type is a guess.')

        # This is a hook for DATA_TYPES_REVERSE to return a tuple of
        # (field_type, field_params_dict).
        if type(field_type) is tuple:
            field_type, new_params = field_type
            field_params.update(new_params)

        # Add max_length for all CharFields.
        if field_type == 'CharField' and row[3]:
            field_params['max_length'] = row[3]

        if field_type == 'DecimalField':
            field_params['max_digits'] = row[4]
            field_params['decimal_places'] = row[5]

        return field_type, field_params, field_notes

    def get_meta(self, table_name):
        """
        Return a sequence comprising the lines of code necessary
        to construct the inner Meta class for the model corresponding
        to the given database table name.
        """
        return ['    class Meta:',
                '        db_table = %r' % table_name,
                '']