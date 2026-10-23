"""Possible-service catalogue, not a statement of hospital capability or doctor credentials."""
CATALOGUE = {
 'General Medicine': ['General Medicine','General Practice','Family Medicine','Internal Medicine','Preventive Medicine'],
 'Dentistry': ['Dentistry','General Dentist','Orthodontics','Oral and Maxillofacial Surgery','Endodontics','Periodontics','Prosthodontics','Pediatric Dentistry','Oral Medicine and Radiology'],
 'Dermatology': ['Dermatology','Clinical Dermatology','Pediatric Dermatology','Hair and Scalp Disorders','Venereology'],
 'Surgery': ['General Surgery','Laparoscopic Surgery','Gastrointestinal Surgery','Cardiothoracic Surgery','Vascular Surgery','Neurosurgery','Plastic and Reconstructive Surgery','Surgical Oncology','Pediatric Surgery','Urology','Orthopedic Surgery','Trauma Surgery','Transplant Surgery'],
 'Cardiology': ['Cardiology','Interventional Cardiology','Cardiothoracic Surgery','Vascular Medicine','Vascular Surgery'],
 'Orthopedics': ['Orthopedics','Joint Replacement','Spine Surgery','Sports Medicine','Rheumatology','Physiotherapy and Rehabilitation'],
 'Neurology': ['Neurology','Neurosurgery','Pediatric Neurology','Neurorehabilitation'],
 'Pediatrics': ['Pediatrics','Neonatology','Pediatric Cardiology','Pediatric Surgery','Pediatric Neurology','Pediatric Orthopedics'],
 'Obstetrics and Gynecology': ['Obstetrics and Gynecology','Maternal-Fetal Medicine','Reproductive Medicine and Infertility','Gynecological Surgery','Menopause Care'],
 'Ophthalmology': ['Ophthalmology','Cataract Surgery','Retina and Vitreous','Glaucoma','Cornea and External Eye Disease','Pediatric Ophthalmology'],
 'ENT / Otorhinolaryngology': ['ENT / Otorhinolaryngology','Head and Neck Surgery','Audiology','Speech and Hearing Services'],
 'Pulmonology': ['Pulmonology','Respiratory Medicine','Critical Care Medicine','Sleep Medicine'],
 'Gastroenterology': ['Gastroenterology','Hepatology','Gastrointestinal Surgery','Proctology / Colorectal Surgery'],
 'Nephrology': ['Nephrology','Urology','Dialysis Services','Kidney Transplant Services'],
 'Endocrinology': ['Endocrinology','Diabetology','Thyroid Disorders','Metabolic Medicine'],
 'Oncology and Hematology': ['Medical Oncology','Surgical Oncology','Radiation Oncology','Hematology','Hemato-Oncology'],
 'Mental Health': ['Psychiatry','Clinical Psychology','Child and Adolescent Psychiatry','Addiction Medicine','Counseling Services'],
 'Emergency and Critical Care': ['Emergency Medicine','Trauma and Emergency Care','Intensive Care Medicine','Anesthesiology','Pain Medicine'],
 'Imaging and Diagnostics': ['Radiology','Interventional Radiology','Pathology','Laboratory Medicine','Microbiology','Biochemistry','Nuclear Medicine'],
 'Other Specialties and Rehabilitation': ['Infectious Disease','Immunology and Allergy','Geriatric Medicine','Physical Medicine and Rehabilitation','Occupational Medicine','Palliative Medicine','Clinical Genetics','Nutrition and Dietetics','Physiotherapy','Speech and Language Therapy','Rehabilitation Services'],
}


def install_catalogue(Department, Specialty):
    for department_name, names in CATALOGUE.items():
        department = Department.objects.filter(name__iexact=department_name).first()
        if department is None:
            department = Department.objects.create(name=department_name, active=False,
                description='Possible service catalogue entry. Hospital service availability has not been verified.')
        for name in names:
            specialty, _ = Specialty.objects.get_or_create(normalized_name=name.casefold(), defaults={'name':name})
            specialty.departments.add(department)
