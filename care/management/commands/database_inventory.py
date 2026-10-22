"""Read-only MySQL/PostgreSQL metadata and orphan counts. Never exports application rows."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.apps import apps
from care.schema import metadata_constraints

class Command(BaseCommand):
    help = 'Export actual MySQL/PostgreSQL table definitions, constraints and orphan counts without row contents.'
    def add_arguments(self, parser):
        parser.add_argument('--output', required=True)
    def handle(self, *args, **options):
        if connection.vendor not in ('mysql','postgresql'):
            raise CommandError('This command requires an actual MySQL or PostgreSQL connection; SQLite is not substituted.')
        connection.ensure_connection()
        purposes = {m._meta.db_table: f'{m._meta.app_label}.{m.__name__}' for m in apps.get_models(include_auto_created=True)}
        report = {'engine': connection.vendor, 'database': connection.settings_dict['NAME'], 'tables': []}
        quote = connection.ops.quote_name
        with connection.cursor() as cursor:
            cursor.execute('SELECT VERSION()')
            report['server_version'] = cursor.fetchone()[0]
            if connection.vendor == 'postgresql':
                cursor.execute('SELECT tablename FROM pg_tables WHERE schemaname=current_schema() ORDER BY tablename')
                table_names = [row[0] for row in cursor.fetchall()]
            else:
                table_names = connection.introspection.table_names(cursor)
            for table in sorted(table_names):
                if connection.vendor == 'mysql':
                    cursor.execute('SELECT COLUMN_NAME,COLUMN_TYPE,IS_NULLABLE,COLUMN_DEFAULT,COLUMN_KEY,EXTRA FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION', [report['database'],table])
                    columns = [dict(zip(['name','type','nullable','default','key','extra'], row)) for row in cursor.fetchall()]
                    cursor.execute('SELECT TABLE_ROWS,ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s', [report['database'],table])
                    estimated, engine = cursor.fetchone()
                    cursor.execute(f'SHOW CREATE TABLE {quote(table)}')
                    definition = cursor.fetchone()[1]
                else:
                    cursor.execute('SELECT current_schema()')
                    report['schema'] = cursor.fetchone()[0]
                    cursor.execute("SELECT a.attname,format_type(a.atttypid,a.atttypmod),CASE WHEN a.attnotnull THEN 'NO' ELSE 'YES' END,pg_get_expr(d.adbin,d.adrelid) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=c.oid AND d.adnum=a.attnum WHERE n.nspname=current_schema() AND c.relname=%s AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum",[table])
                    columns=[dict(zip(['name','type','nullable','default'],r),key='',extra='') for r in cursor.fetchall()]
                    cursor.execute('SELECT greatest(c.reltuples,0)::bigint,c.relrowsecurity,c.relforcerowsecurity FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=current_schema() AND c.relname=%s',[table])
                    estimated,rls,force_rls=cursor.fetchone()
                    engine='PostgreSQL'; definition='Use pg_dump --schema-only for PostgreSQL DDL.'
                constraints = metadata_constraints(cursor,table)
                orphans = []
                for name, detail in constraints.items():
                    fk = detail.get('foreign_key')
                    if not fk or len(detail['columns']) != 1:
                        continue
                    child = quote(detail['columns'][0]); parent_table,parent_col=fk
                    cursor.execute(f'SELECT COUNT(*) FROM {quote(table)} AS c LEFT JOIN {quote(parent_table)} AS p ON c.{child}=p.{quote(parent_col)} WHERE c.{child} IS NOT NULL AND p.{quote(parent_col)} IS NULL')
                    orphans.append({'constraint':name,'count':cursor.fetchone()[0]})
                report['tables'].append({'rls_enabled':rls if connection.vendor=='postgresql' else None,'rls_forced':force_rls if connection.vendor=='postgresql' else None,'table':table,'purpose':purposes.get(table,'Django schema migration history' if table=='django_migrations' else 'Database table'), 'engine':engine,'approximate_rows':estimated,'columns':columns,'constraints':constraints,'create_table':definition,'orphan_counts':orphans})
        Path(options['output']).write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
        self.stdout.write(f"Actual database schema exported: {len(report['tables'])} tables. No row contents or credentials exported.")
