"""Read-only MySQL metadata and orphan counts. Never exports application rows."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.apps import apps

class Command(BaseCommand):
    help = 'Export actual MySQL tables, columns, indexes, foreign keys and orphan counts without row contents.'
    def add_arguments(self, parser):
        parser.add_argument('--output', required=True)
    def handle(self, *args, **options):
        if connection.vendor != 'mysql':
            raise CommandError('This command requires an actual MySQL connection; SQLite is not substituted.')
        connection.ensure_connection()
        purposes = {m._meta.db_table: f'{m._meta.app_label}.{m.__name__}' for m in apps.get_models(include_auto_created=True)}
        report = {'engine': connection.vendor, 'database': connection.settings_dict['NAME'], 'tables': []}
        quote = connection.ops.quote_name
        with connection.cursor() as cursor:
            cursor.execute('SELECT VERSION()')
            report['server_version'] = cursor.fetchone()[0]
            for table in sorted(connection.introspection.table_names(cursor)):
                cursor.execute('SELECT COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_DEFAULT,COLUMN_KEY,EXTRA FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION', [report['database'],table])
                columns = [dict(zip(['name','type','nullable','default','key','extra'], row)) for row in cursor.fetchall()]
                cursor.execute('SELECT TABLE_ROWS,ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s', [report['database'],table])
                estimated, engine = cursor.fetchone()
                constraints = connection.introspection.get_constraints(cursor,table)
                cursor.execute(f'SHOW CREATE TABLE {quote(table)}')
                definition = cursor.fetchone()[1]
                orphans = []
                for name, detail in constraints.items():
                    fk = detail.get('foreign_key')
                    if not fk or len(detail['columns']) != 1:
                        continue
                    child = quote(detail['columns'][0]); parent_table,parent_col=fk
                    cursor.execute(f'SELECT COUNT(*) FROM {quote(table)} AS c LEFT JOIN {quote(parent_table)} AS p ON c.{child}=p.{quote(parent_col)} WHERE c.{child} IS NOT NULL AND p.{quote(parent_col)} IS NULL')
                    orphans.append({'constraint':name,'count':cursor.fetchone()[0]})
                report['tables'].append({'table':table,'purpose':purposes.get(table,'Django schema migration history' if table=='django_migrations' else 'Database table'), 'engine':engine,'approximate_rows':estimated,'columns':columns,'constraints':constraints,'create_table':definition,'orphan_counts':orphans})
        Path(options['output']).write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
        self.stdout.write(f"Actual MySQL schema exported: {len(report['tables'])} tables. No row contents or credentials exported.")
