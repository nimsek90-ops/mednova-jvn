"""Real HTTP upgrade acceptance; guarded local synthetic fixture databases only."""
import os
import re
import uuid
from datetime import date, timedelta
import requests
from http_acceptance import ORIGIN, PASSWORD, get, sign


def post(session, path, data):
    # POST-only actions have no GET page. Use a real same-origin form for CSRF.
    page = get(session, '/assistant/')
    token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page.text)[1]
    response = session.post(ORIGIN+path, data={**data,'csrfmiddlewaretoken':token},
        headers={'Origin':ORIGIN,'Referer':page.url}, timeout=15)
    response.raise_for_status()
    return response


def main():
    mysql = os.getenv('MEDNOVA_HTTP_MYSQL') == '1' and os.getenv('MYSQL_DATABASE') == 'mednova_local'
    postgres = os.getenv('MEDNOVA_HTTP_POSTGRES') == '1' and os.getenv('PGDATABASE') == 'mednova_pg_rehearsal'
    if os.getenv('APP_ENV') != 'local' or os.getenv('MEDNOVA_DEMO') != '1' or not (mysql or postgres):
        raise SystemExit('Refusing mutations outside designated local synthetic acceptance targets.')
    suffix = uuid.uuid4().hex[:10]
    admin,doctor,reception,pharmacy = [sign(email) for email in ['admin@example.test','doctor@example.test','reception@example.test','pharmacy@example.test']]
    patient = requests.Session()
    response=post(patient,'/register/',{'name':'SYNTHETIC Upgrade QA '+suffix,'email':'synthetic-upgrade-'+suffix+'@example.test',
        'role':'patient','password1':PASSWORD,'password2':PASSWORD,'consent':'on'})
    assert response.url.endswith('/dashboard/')
    registration = get(reception,'/patients/?q=synthetic-upgrade-'+suffix)
    patient_id=re.search(r'/patients/(\d+)/registration/',registration.text)[1]
    card=get(patient,f'/patients/{patient_id}/registration/')
    assert 'MN-' in card.text
    assert patient.get(ORIGIN+'/purchasing/',timeout=10).status_code==403
    print('PASS 1: new synthetic registration has a persisted MRN; patient cannot access pharmacy purchasing')
    day=date.today()+timedelta(days=15+int(suffix[:2],16)%50)
    response=post(doctor,'/schedule/rules/',{'action':'session','weekday':day.weekday(),'start':'21:00','end':'21:40',
        'duration':15,'buffer':5,'mode':'both','visit_type':'follow_up','capacity':2})
    assert '15 min + 5 min buffer' in get(doctor,'/schedule/rules/').text
    post(doctor,'/schedule/rules/',{'action':'publish','first':str(day),'last':str(day)})
    directory=get(patient,'/doctors/?q=Test+Doctor')
    doctor_id=re.search(r'href="/doctors/(\d+)/">Test Doctor</a>',directory.text)[1]
    booking=get(patient,f'/book/{doctor_id}/?date={day}')
    slot=re.search(r'name="slot" value="(\d+)"',booking.text)[1]
    assert '15 min + 5 min buffer' in booking.text
    response=post(patient,'/assistant/',{'action':'book','slot':slot,'mode':'in_person','reason':'SYNTHETIC upgrade QA','consent':'on'})
    assert re.search(r'/appointments/[0-9a-f-]+/$',response.url)
    appointment_path=response.url.removeprefix(ORIGIN)
    post(doctor,appointment_path+'action/',{'action':'confirmed'})
    assert 'Confirmed' in get(patient,appointment_path).text
    assert reception.get(ORIGIN+appointment_path+'clinical-work/',timeout=10).status_code==403
    print('PASS 2: recurring duration/buffer slots flow through assistant booking into the shared appointment; clinical reception access denied')
    post(admin,'/admin/beds/',{'label':'SYNTHETIC-QA-'+suffix,'ward':'SYNTHETIC TRAINING','room_type':'Training only'})
    post(doctor,'/admissions/',{'action':'request','patient':patient_id})
    admissions=get(reception,'/admissions/')
    match=re.search(r'<tr><td>SYNTHETIC Upgrade QA '+suffix+r'.*?</tr>',admissions.text,re.S)
    assert match
    admission=re.search(r'name="admission" value="(\d+)"',match[0])[1]
    bed=re.search(r'<option value="(\d+)">[^<]*SYNTHETIC-QA-'+suffix,admissions.text)[1]
    post(reception,'/admissions/',{'action':'allocate','admission':admission,'bed':bed})
    assert 'Admitted' in get(patient,'/admissions/').text
    print('PASS 3: responsible-doctor admission request, reception bed allocation and patient-owned admission view')
    medicine_name='SYNTHETIC STOCK '+suffix
    post(pharmacy,'/inventory/',{'name':medicine_name,'batch':'QA-'+suffix,'expiry':str(day+timedelta(days=90)),
        'stock':10,'price':'5.00','purchase_price':'2.00','reorder_level':3})
    post(pharmacy,'/purchasing/',{'action':'supplier','name':'SYNTHETIC SUPPLIER '+suffix,'contact':'Synthetic training only'})
    purchasing=get(pharmacy,'/purchasing/')
    supplier=re.search(r'<option value="(\d+)">SYNTHETIC SUPPLIER '+suffix,purchasing.text)[1]
    medicine=re.search(r'<option value="(\d+)">'+medicine_name,purchasing.text)[1]
    post(pharmacy,'/purchasing/',{'action':'order','supplier':supplier,'medicine':medicine,'quantity':3})
    listing=get(admin,'/purchasing/')
    row=re.search(r'<tr><td>#\d+</td><td>SYNTHETIC SUPPLIER '+suffix+r'.*?</tr>',listing.text,re.S)[0]
    order=re.search(r'name="order" value="(\d+)"',row)[1]
    post(admin,'/purchasing/',{'action':'approve','order':order})
    post(pharmacy,'/purchasing/',{'action':'receipt','order':order,'quantity':3,'reference':'SYNTHETIC-GRN-'+suffix,'verified':'on'})
    assert 'SYNTHETIC-GRN-'+suffix in get(pharmacy,'/purchasing/').text
    post(pharmacy,f'/inventory/{medicine}/safety/',{'status':'quarantined','reason':'Synthetic quarantine acceptance'})
    assert re.search(r'<option value="quarantined" selected', get(pharmacy,f'/inventory/{medicine}/safety/').text)
    print('PASS 4: supplier, purchase request, admin approval, verified GRN and batch quarantine persist via actual HTTP')
    post(patient,'/waiting-list/',{'doctor':doctor_id,'mode':'in_person'})
    post(patient,appointment_path+'action/',{'action':'cancelled','cancellation_reason':'Synthetic QA cancellation'})
    assert 'may now be available' in get(patient,'/notifications/').text
    print('PASS 5: waiting-list notification follows cancellation of the shared appointment')
    assert get(admin,'/admin/data/schema/?table=care_dispensingevent').status_code==200
    response=post(requests.Session(),'/assistant/',{'topic':'doctors','question':'emergency cannot breathe'})
    assert '112' in response.text
    print('PASS 6: actual new-table metadata and public emergency escalation; no model provider required')


if __name__=='__main__':
    main()
