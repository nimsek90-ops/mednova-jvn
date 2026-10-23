from django.db import migrations
from django.db.models import F


def preserve_existing(apps, schema_editor):
    alias = schema_editor.connection.alias
    User = apps.get_model('care', 'User')
    Registration = apps.get_model('care', 'PatientRegistration')
    Item = apps.get_model('care', 'PrescriptionItem')
    for patient_id in User.objects.using(alias).filter(role='patient').values_list('pk', flat=True).iterator():
        Registration.objects.using(alias).get_or_create(patient_id=patient_id)
    # Historical completed dispensing must never become eligible for a second issue.
    Item.objects.using(alias).filter(prescription__dispensed=True).update(dispensed_quantity=F('quantity'))


class Migration(migrations.Migration):
    dependencies = [('care', '0007_prescriptionitem_issue_not_above_prescribed_and_more')]
    operations = [migrations.RunPython(preserve_existing, reverse_code=migrations.RunPython.noop)]
