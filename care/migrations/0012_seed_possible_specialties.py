from django.db import migrations

CATALOGUE = {'General Medicine': ['General Medicine',
                      'General Practice',
                      'Family Medicine',
                      'Internal Medicine',
                      'Preventive Medicine'],
 'Dentistry': ['Dentistry',
               'General Dentist',
               'Orthodontics',
               'Oral and Maxillofacial Surgery',
               'Endodontics',
               'Periodontics',
               'Prosthodontics',
               'Pediatric Dentistry',
               'Oral Medicine and Radiology'],
 'Dermatology': ['Dermatology',
                 'Clinical Dermatology',
                 'Pediatric Dermatology',
                 'Hair and Scalp Disorders',
                 'Venereology'],
 'Surgery': ['General Surgery',
             'Laparoscopic Surgery',
             'Gastrointestinal Surgery',
             'Cardiothoracic Surgery',
             'Vascular Surgery',
             'Neurosurgery',
             'Plastic and Reconstructive Surgery',
             'Surgical Oncology',
             'Pediatric Surgery',
             'Urology',
             'Orthopedic Surgery',
             'Trauma Surgery',
             'Transplant Surgery'],
 'Cardiology': ['Cardiology',
                'Interventional Cardiology',
                'Cardiothoracic Surgery',
                'Vascular Medicine',
                'Vascular Surgery'],
 'Orthopedics': ['Orthopedics',
                 'Joint Replacement',
                 'Spine Surgery',
                 'Sports Medicine',
                 'Rheumatology',
                 'Physiotherapy and Rehabilitation'],
 'Neurology': ['Neurology',
               'Neurosurgery',
               'Pediatric Neurology',
               'Neurorehabilitation'],
 'Pediatrics': ['Pediatrics',
                'Neonatology',
                'Pediatric Cardiology',
                'Pediatric Surgery',
                'Pediatric Neurology',
                'Pediatric Orthopedics'],
 'Obstetrics and Gynecology': ['Obstetrics and Gynecology',
                               'Maternal-Fetal Medicine',
                               'Reproductive Medicine and Infertility',
                               'Gynecological Surgery',
                               'Menopause Care'],
 'Ophthalmology': ['Ophthalmology',
                   'Cataract Surgery',
                   'Retina and Vitreous',
                   'Glaucoma',
                   'Cornea and External Eye Disease',
                   'Pediatric Ophthalmology'],
 'ENT / Otorhinolaryngology': ['ENT / Otorhinolaryngology',
                               'Head and Neck Surgery',
                               'Audiology',
                               'Speech and Hearing Services'],
 'Pulmonology': ['Pulmonology',
                 'Respiratory Medicine',
                 'Critical Care Medicine',
                 'Sleep Medicine'],
 'Gastroenterology': ['Gastroenterology',
                      'Hepatology',
                      'Gastrointestinal Surgery',
                      'Proctology / Colorectal Surgery'],
 'Nephrology': ['Nephrology',
                'Urology',
                'Dialysis Services',
                'Kidney Transplant Services'],
 'Endocrinology': ['Endocrinology',
                   'Diabetology',
                   'Thyroid Disorders',
                   'Metabolic Medicine'],
 'Oncology and Hematology': ['Medical Oncology',
                             'Surgical Oncology',
                             'Radiation Oncology',
                             'Hematology',
                             'Hemato-Oncology'],
 'Mental Health': ['Psychiatry',
                   'Clinical Psychology',
                   'Child and Adolescent Psychiatry',
                   'Addiction Medicine',
                   'Counseling Services'],
 'Emergency and Critical Care': ['Emergency Medicine',
                                 'Trauma and Emergency Care',
                                 'Intensive Care Medicine',
                                 'Anesthesiology',
                                 'Pain Medicine'],
 'Imaging and Diagnostics': ['Radiology',
                             'Interventional Radiology',
                             'Pathology',
                             'Laboratory Medicine',
                             'Microbiology',
                             'Biochemistry',
                             'Nuclear Medicine'],
 'Other Specialties and Rehabilitation': ['Infectious Disease',
                                          'Immunology and Allergy',
                                          'Geriatric Medicine',
                                          'Physical Medicine and '
                                          'Rehabilitation',
                                          'Occupational Medicine',
                                          'Palliative Medicine',
                                          'Clinical Genetics',
                                          'Nutrition and Dietetics',
                                          'Physiotherapy',
                                          'Speech and Language Therapy',
                                          'Rehabilitation Services']}


def seed(apps, schema_editor):
    Department=apps.get_model('care','Department')
    Specialty=apps.get_model('care','Specialty')
    def key(name):
        value=''.join(c for c in name.casefold() if c.isalnum()).replace('orthopaed','orthoped').replace('paediatr','pediatr').replace('gynaec','gynec')
        return 'entotorhinolaryngology' if value in ('ent','otorhinolaryngology','otolaryngology') else value
    existing={}
    for department in Department.objects.order_by('pk'):
        existing.setdefault(key(department.name),department)
    for name,names in CATALOGUE.items():
        department=existing.get(key(name))
        if department is None:
            department=Department.objects.create(name=name,active=False,description='Possible service catalogue entry. Hospital availability has not been verified.')
            existing[key(name)]=department
        for specialty_name in names:
            specialty,_=Specialty.objects.get_or_create(normalized_name=specialty_name.casefold(),defaults={'name':specialty_name})
            specialty.departments.add(department)


class Migration(migrations.Migration):
    dependencies=[('care','0011_reception_specialty_catalogue')]
    operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
