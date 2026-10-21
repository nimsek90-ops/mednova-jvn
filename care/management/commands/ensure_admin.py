import os
from getpass import getpass
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.db import transaction, IntegrityError
from care.models import User, Hospital
from care.security import audit


class Command(BaseCommand):
    help = 'Provision a named administrator; never reset an existing account password.'

    def add_arguments(self, parser):
        parser.add_argument('--email', help='Login email; alternatively MEDNOVA_ADMIN_EMAIL.')
        parser.add_argument('--noinput', action='store_true', help='Read initial password from MEDNOVA_ADMIN_PASSWORD.')

    def handle(self, *args, **options):
        email = (options.get('email') or os.getenv('MEDNOVA_ADMIN_EMAIL', '')).strip().lower()
        if not email:
            if options['noinput']:
                raise CommandError('Set MEDNOVA_ADMIN_EMAIL or pass --email; no default identity is used.')
            if User.objects.filter(role='admin', is_active=True).exists():
                self.stdout.write('An administrator exists. To provision a specific identity, use --email. Nothing was changed.')
                return
            email = input('Administrator email: ').strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            raise CommandError('Enter a valid administrator email.')
        existing = User.objects.filter(email__iexact=email).first()
        if existing:
            self.verify_existing(existing)
            self.stdout.write('Administrator already exists. Its password and flags were not changed.')
            return
        password = os.getenv('MEDNOVA_ADMIN_PASSWORD', '') if options['noinput'] else getpass('New initial password (hidden): ')
        if not password:
            raise CommandError('An initial password is required; use the hidden prompt or secure environment variable.')
        if not options['noinput'] and password != getpass('Repeat password (hidden): '):
            raise CommandError('Passwords do not match.')
        candidate = User(email=email, name='Hospital administrator', role='admin')
        try:
            validate_password(password, candidate)
        except ValidationError as error:
            raise CommandError(' '.join(error.messages))
        try:
            with transaction.atomic():
                user = User.objects.create_superuser(email, password, name='Hospital administrator', is_active=True, must_change_password=True)
                Hospital.objects.get_or_create(pk=1)
                audit(user, 'admin.provisioned', user.pk)
        except IntegrityError:
            existing = User.objects.filter(email__iexact=email).first()
            if not existing:
                raise CommandError('Provisioning failed; no credentials were logged.')
            self.verify_existing(existing)
            self.stdout.write('Administrator was provisioned concurrently. No password was changed.')
            return
        self.stdout.write(self.style.SUCCESS('Administrator provisioned. Initial password replacement is required before accessing the workspace.'))

    def verify_existing(self, user):
        if not (user.role == 'admin' and user.is_staff and user.is_superuser and user.is_active and user.approval == 'approved'):
            raise CommandError('An account with this email exists but is not an active approved administrator. No privileges or credentials were changed.')
