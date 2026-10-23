"""Integrated hospital workflows using existing identities and appointment services."""
import uuid
from datetime import timedelta
from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction, IntegrityError
from django.db.models import Q, F, Sum, Count
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import *
from .hospital_forms import *
from .security import roles, audit, rate_limit
from .services import BookingError, book
from .scheduling import publish_schedule, add_block, available_slots, day_bounds
from .hospital_services import partial_dispense, receive_purchase, update_admission
from .views import page, paged, integer_id, visible_appointments, clinical_appointment


@roles('doctor')
@require_http_methods(['GET','POST'])
def schedule(request):
    action = request.POST.get('action','session')
    session_form = SessionForm(request.POST if request.method == 'POST' and action == 'session' else None, auto_id='session_%s')
    block_form = BlockForm(request.POST if request.method == 'POST' and action == 'block' else None, auto_id='block_%s')
    publish_form = PublishForm(request.POST if request.method == 'POST' and action == 'publish' else None,
        initial={'first':timezone.localdate(), 'last':timezone.localdate()+timedelta(days=14)}, auto_id='publish_%s')
    form = {'session':session_form,'block':block_form,'publish':publish_form}.get(action)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                User.objects.select_for_update().get(pk=request.user.pk)
                if action in ('disable','enable'):
                    session = get_object_or_404(ScheduleSession, pk=integer_id(request.POST.get('session')), doctor=request.user)
                    if action=='disable' and Slot.objects.filter(session=session, booked=True, start__gt=timezone.now()).exists():
                        raise BookingError('Reschedule future booked visits before disabling this session.')
                    if action=='enable' and ScheduleSession.objects.filter(doctor=request.user,weekday=session.weekday,active=True,
                            start__lt=session.end,end__gt=session.start).exclude(pk=session.pk).exists():
                        raise BookingError('This session overlaps another enabled session.')
                    session.active = action=='enable'
                    session.save(update_fields=['active'])
                    if action=='disable':
                        Slot.objects.filter(session=session, booked=False).update(active=False)
                    audit(request.user, 'schedule.'+action, session.pk)
                elif form and form.is_valid():
                    if action == 'session':
                        d = form.cleaned_data
                        if ScheduleSession.objects.filter(doctor=request.user, weekday=d['weekday'], active=True,
                                start__lt=d['end'], end__gt=d['start']).exists():
                            raise BookingError('Weekly sessions may not overlap. Add separate morning/evening sessions.')
                        obj = form.save(commit=False)
                        obj.doctor = request.user
                        obj.save()
                        audit(request.user, 'schedule.session_created', obj.pk)
                    elif action == 'block':
                        add_block(request.user, **form.cleaned_data)
                    else:
                        count = publish_schedule(request.user, **form.cleaned_data)
                        messages.success(request, f'{count} available slots published; booked and existing slots were preserved.')
                else:
                    raise BookingError('Choose a supported action and correct the fields below.')
            if not form or not form.errors:
                return redirect('schedule_rules')
        except (BookingError, IntegrityError) as error:
            messages.error(request, str(error) if isinstance(error, BookingError) else 'That weekly start time already exists. Review the existing session.')
    return render(request, 'care/schedule_rules.html', {'session_form':session_form,'block_form':block_form,
        'publish_form':publish_form,'sessions':ScheduleSession.objects.filter(doctor=request.user),
        'blocks':ScheduleBlock.objects.filter(doctor=request.user, end__gt=timezone.now())[:100]})


@roles('patient','receptionist','admin')
@require_http_methods(['GET','POST'])
def registration_card(request, patient_id):
    patient = get_object_or_404(User, pk=patient_id, role='patient')
    if request.user.role == 'patient' and request.user.pk != patient.pk:
        raise PermissionDenied
    record = PatientRegistration.objects.filter(patient=patient).first()
    form = RegistrationForm(request.POST if request.method == 'POST' else None, instance=record)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            User.objects.select_for_update().get(pk=patient.pk)
            current = PatientRegistration.objects.filter(patient=patient).first()
            form = RegistrationForm(request.POST, instance=current)
            if form.is_valid():
                record = form.save(commit=False)
                record.patient = patient
                record.save()
                audit(request.user, 'registration.saved', patient.pk)
        return redirect('registration_card', patient_id=patient.pk)
    audit(request.user, 'registration.viewed', patient.pk)
    return render(request, 'care/registration_card.html', {'patient':patient,'record':record,'form':form})


@roles('doctor','receptionist','admin','patient')
@require_http_methods(['GET','POST'])
def admissions(request):
    rows = Admission.objects.select_related('patient','doctor','department','bed').order_by('-created')
    if request.user.role == 'doctor':
        rows = rows.filter(doctor=request.user)
    elif request.user.role == 'patient':
        rows = rows.filter(patient=request.user)
    beds = Bed.objects.filter(active=True, admission__isnull=True).order_by('ward','label')
    if request.method == 'POST':
        try:
            action = request.POST.get('action')
            if action == 'request' and request.user.role == 'doctor':
                patient = get_object_or_404(User, pk=integer_id(request.POST.get('patient')), role='patient', is_active=True)
                if not Appointment.objects.filter(patient=patient, slot__doctor=request.user, status__in=['confirmed','completed']).exists():
                    raise PermissionDenied
                with transaction.atomic():
                    User.objects.select_for_update().get(pk=patient.pk)
                    if Admission.objects.filter(patient=patient, status__in=['requested','admitted','discharge_ready']).exists():
                        raise BookingError('An active admission request already exists for this patient.')
                    profile = getattr(request.user, 'doctor_profile', None)
                    if not profile or not profile.department_id:
                        raise BookingError('Complete your approved department profile before requesting admission.')
                    obj = Admission.objects.create(patient=patient, doctor=request.user, department=profile.department)
                    audit(request.user, 'admission.requested', obj.pk)
            elif request.user.role in ('doctor','receptionist','admin'):
                update_admission(integer_id(request.POST.get('admission')), action, request.user,
                                 integer_id(request.POST.get('bed')) if request.POST.get('bed') else None)
            else:
                raise PermissionDenied
            messages.success(request, 'Admission workflow updated. Clinical readiness remains with the responsible doctor.')
        except (BookingError, Bed.DoesNotExist, Admission.DoesNotExist, IntegrityError) as error:
            messages.error(request, str(error) if isinstance(error, BookingError) else 'The bed or admission changed. Reload and retry.')
        return redirect('admissions')
    return render(request, 'care/admissions.html', {'rows':paged(request, rows),'beds':beds,
        'patients':User.objects.filter(role='patient', appointments__slot__doctor=request.user, appointments__status__in=['confirmed','completed']).distinct() if request.user.role=='doctor' else []})


@roles('admin')
@require_http_methods(['GET','POST'])
def bed_catalogue(request):
    form = BedForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        audit(request.user, 'bed.created', obj.pk)
        return redirect('bed_catalogue')
    return page(request, 'Bed catalogue', form, notice='Create verified ward resources only. Occupancy is managed through Admissions.', records=Bed.objects.order_by('ward','label'))


@roles('pharmacist','admin')
@require_http_methods(['GET','POST'])
def purchasing(request):
    action = request.POST.get('action','order')
    supplier_form = SupplierForm(request.POST if request.method=='POST' and action=='supplier' else None, auto_id='supplier_%s')
    order_form = PurchaseForm(request.POST if request.method=='POST' and action=='order' else None, auto_id='purchase_%s')
    receipt_form = ReceiptForm(request.POST if request.method=='POST' and action=='receipt' else None, auto_id='receipt_%s')
    form = {'supplier':supplier_form,'order':order_form,'receipt':receipt_form}.get(action)
    if request.method=='POST':
        try:
            if action == 'approve':
                if request.user.role != 'admin':
                    raise PermissionDenied
                with transaction.atomic():
                    order = get_object_or_404(PurchaseOrder.objects.select_for_update(), pk=integer_id(request.POST.get('order')))
                    if order.status != 'requested':
                        raise BookingError('Only a requested order can be approved.')
                    order.status, order.approved_by = 'approved', request.user
                    order.save(update_fields=['status','approved_by'])
                    audit(request.user, 'purchase.approved', order.pk)
                return redirect('purchasing')
            elif form and form.is_valid():
                with transaction.atomic():
                    if action == 'receipt':
                        receive_purchase(form.cleaned_data['order'].pk, form.cleaned_data['quantity'], form.cleaned_data['reference'], request.user)
                    else:
                        obj = form.save(commit=False)
                        if action == 'order':
                            obj.requested_by = request.user
                        obj.save()
                        audit(request.user, 'purchase.'+action, obj.pk)
                return redirect('purchasing')
        except (BookingError, IntegrityError) as error:
            messages.error(request, str(error) if isinstance(error, BookingError) else 'That reference or supplier already exists. Review before retrying.')
    rows = PurchaseOrder.objects.select_related('supplier','medicine','requested_by').order_by('-created')
    return render(request,'care/purchasing.html', {'supplier_form':supplier_form,'order_form':order_form,
        'receipt_form':receipt_form,'rows':paged(request,rows),'receipts':GoodsReceipt.objects.select_related('order__medicine').order_by('-created')[:30]})


@roles('pharmacist')
@require_http_methods(['GET','POST'])
def issue(request, item_id):
    item = get_object_or_404(PrescriptionItem.objects.select_related('medicine','prescription__appointment__patient'), pk=item_id)
    form = PartialIssueForm(request.POST or None, initial={'key':uuid.uuid4(),'quantity':item.remaining})
    if request.method=='POST' and form.is_valid():
        try:
            partial_dispense(item.pk, form.cleaned_data['quantity'], form.cleaned_data['key'], request.user)
            messages.success(request, 'Medicine issue saved. Remaining quantity and batch stock were updated together.')
            return redirect('prescriptions')
        except (BookingError, IntegrityError) as error:
            form.add_error(None, str(error) if isinstance(error, BookingError) else 'Submission reference is already used. Reload the prescription.')
    return page(request, 'Partial dispensing', form, notice=f'{item.medicine.name}, batch {item.medicine.batch}; prescribed {item.quantity}; remaining {item.remaining}. Verify patient and prescription before issuing.')


@roles('pharmacist','admin')
@require_http_methods(['GET','POST'])
def batch_safety(request, medicine_id):
    medicine = get_object_or_404(Medicine, pk=medicine_id)
    class SafetyForm(forms.Form):
        status = forms.ChoiceField(choices=Medicine._meta.get_field('safety_status').choices)
        reason = forms.CharField(min_length=5,max_length=120)
    form = SafetyForm(request.POST or None, initial={'status':medicine.safety_status})
    if request.method=='POST' and form.is_valid():
        with transaction.atomic():
            medicine = Medicine.objects.select_for_update().get(pk=medicine.pk)
            if form.cleaned_data['status']=='available' and request.user.role!='admin':
                form.add_error(None,'Only an administrator may authorize release to available stock.')
            else:
                medicine.safety_status = form.cleaned_data['status']
                medicine.save(update_fields=['safety_status'])
                StockMovement.objects.create(medicine=medicine,actor=request.user,quantity=0,balance=medicine.stock,reason=form.cleaned_data['reason'])
                audit(request.user,'batch.safety_changed',medicine.pk)
                return redirect('inventory')
    return page(request,'Batch quarantine / recall',form,notice=f'{medicine.name} / {medicine.batch}. Unavailable stock cannot be dispensed. Release requires administrator authorization.')


@roles('patient','doctor')
@require_http_methods(['GET','POST'])
def clinical_work(request, pk):
    appt = clinical_appointment(request.user, pk)
    can_write = request.user.role == 'doctor' and appt.status in ('confirmed','completed') and appt.slot.start <= timezone.now()
    draft = ClinicalDraft.objects.filter(appointment=appt).first() if can_write else None
    action = request.POST.get('action','draft')
    draft_form = DraftForm(request.POST if request.method=='POST' and action=='draft' else None,
        instance=draft, initial={'expected_revision':draft.revision if draft else 0})
    order_form = InvestigationForm(request.POST if request.method=='POST' and action=='order' else None)
    result_form = ResultForm(request.POST if request.method=='POST' and action=='result' else None)
    if request.method=='POST':
        if not can_write:
            raise PermissionDenied
        with transaction.atomic():
            locked = Appointment.objects.select_for_update().get(pk=appt.pk)
            if locked.status not in ('confirmed','completed'):
                raise PermissionDenied
            if action=='draft' and draft_form.is_valid():
                current = ClinicalDraft.objects.filter(appointment=appt).first()
                if draft_form.cleaned_data['expected_revision'] != (current.revision if current else 0):
                    draft_form.add_error(None,'Draft changed in another tab. Reload before saving.')
                else:
                    draft = draft_form.save(commit=False)
                    draft.appointment, draft.author = appt, request.user
                    draft.revision = (current.revision if current else 0)+1
                    draft.save()
                    audit(request.user,'clinical_draft.saved',appt.pk)
                    return redirect('clinical_work',pk=pk)
            elif action=='order' and order_form.is_valid():
                obj = order_form.save(commit=False)
                obj.appointment, obj.ordered_by = appt, request.user
                obj.save()
                audit(request.user,'investigation.ordered',obj.pk)
                return redirect('clinical_work',pk=pk)
            elif action in ('result','acknowledge'):
                obj = get_object_or_404(Investigation.objects.select_for_update(),pk=integer_id(request.POST.get('investigation')),appointment=appt)
                if action=='result' and result_form.is_valid() and obj.status=='ordered':
                    obj.result, obj.critical = result_form.cleaned_data['result'], result_form.cleaned_data['critical']
                    obj.status = 'resulted'
                    obj.save()
                    audit(request.user,'investigation.result_recorded',obj.pk)
                    return redirect('clinical_work',pk=pk)
                elif action=='acknowledge' and obj.status=='resulted':
                    obj.status, obj.acknowledged_at = 'acknowledged', timezone.now()
                    obj.save()
                    audit(request.user,'investigation.acknowledged',obj.pk)
                    return redirect('clinical_work',pk=pk)
                messages.error(request,'This result cannot be changed or acknowledged in its current state.')
            else:
                messages.error(request,'Correct the form or choose a supported action.')
    orders = list(appt.investigations.order_by('-created'))
    for order in orders:
        order.result_form = ResultForm(request.POST if request.method=='POST' and action=='result' and request.POST.get('investigation')==str(order.pk) else None,
                                      auto_id=f'result_{order.pk}_%s')
    audit(request.user,'clinical_work.viewed',appt.pk)
    return render(request,'care/clinical_work.html',{'appt':appt,'can_write':can_write,'draft':draft,
        'draft_form':draft_form,'order_form':order_form,'result_form':result_form,'orders':orders})


@roles('admin')
@require_http_methods(['GET','POST'])
def assistant_admin(request):
    form = FAQForm(request.POST if request.method=='POST' and request.POST.get('action')=='faq' else None)
    if request.method=='POST':
        if request.POST.get('action')=='faq' and form.is_valid():
            obj = form.save()
            audit(request.user,'assistant.faq_created',obj.pk)
            return redirect('assistant_admin')
        elif request.POST.get('action')=='toggle':
            obj = get_object_or_404(HospitalFAQ,pk=integer_id(request.POST.get('faq')))
            obj.approved = not obj.approved
            obj.save(update_fields=['approved','updated'])
            audit(request.user,'assistant.faq_approval_changed',obj.pk)
            return redirect('assistant_admin')
        elif request.POST.get('action')=='resolve':
            obj = get_object_or_404(AssistantEscalation,pk=integer_id(request.POST.get('escalation')))
            obj.resolved = True
            obj.save(update_fields=['resolved'])
            audit(request.user,'assistant.escalation_resolved',obj.pk)
            return redirect('assistant_admin')
    return render(request,'care/assistant_admin.html',{'form':form,'faqs':HospitalFAQ.objects.order_by('-updated')[:100],
        'escalations':AssistantEscalation.objects.select_related('patient').filter(resolved=False).order_by('created')[:100]})


@require_http_methods(['GET','POST'])
@rate_limit('assistant',40,60)
def assistant(request):
    from .forms import BookingForm
    form = AssistantForm(request.POST or None, initial={'topic':request.GET.get('topic','doctors')})
    answer = 'Choose an action. This service assistant uses hospital records; it does not diagnose or prescribe.'
    links, slots, visits, faqs = [], [], [], HospitalFAQ.objects.filter(approved=True,language=getattr(request,'language','en'))[:20]
    patient = request.user.is_authenticated and request.user.role=='patient' and request.user.approval=='approved'
    if request.method=='POST' and request.POST.get('action')=='book':
        if not patient:
            raise PermissionDenied
        booking_form = BookingForm(request.POST)
        if booking_form.is_valid():
            try:
                obj = book(request.user, integer_id(request.POST.get('slot')),booking_form.cleaned_data['mode'],booking_form.cleaned_data['reason'])
                return redirect('appointment',pk=obj.pk)
            except (BookingError,Slot.DoesNotExist) as error:
                answer = str(error) if isinstance(error,BookingError) else 'This appointment slot is no longer available.'
        else:
            answer = 'Confirm a consultation mode, visit reason and consent before booking.'
    elif request.method=='POST' and form.is_valid():
        q = form.cleaned_data['question'].casefold()
        # A deterministic safety trigger, not a diagnostic triage classifier.
        urgent = any(word in q for word in ['chest pain','cannot breathe','can\'t breathe','unconscious','heavy bleeding','emergency','छातीत दुख','श्वास','बेहोश','आपातकाल','आत्महत्या'])
        topic = form.cleaned_data['topic']
        if urgent:
            answer = 'Potential emergency: seek urgent medical help now. In India call 112 or go to the nearest emergency department. Do not wait for chat or payment.'
        elif topic=='doctors':
            slots = available_slots().filter(doctor__role='doctor',doctor__approval='approved',doctor__is_active=True,
                doctor__doctor_profile__department__active=True).select_related('doctor__doctor_profile__department')
            if q:
                slots = slots.filter(Q(doctor__name__icontains=q)|Q(doctor__doctor_profile__department__name__icontains=q))
            slots = list(slots[:12])
            answer = 'Published slots below are real availability. Your choice is rechecked under a database lock when you confirm.'
        elif topic in ('appointments','reports','billing'):
            if not patient:
                answer = 'Sign in with your patient account to access your own records.'
                links = [('Patient sign-in',reverse('login')+'?role=patient')]
            else:
                visits = visible_appointments(request.user).order_by('-slot__start')[:12]
                answer = 'These are your own appointments. Open a visit for its permitted records and billing details.'
                links = [('My medical timeline',reverse('timeline',args=[request.user.pk])),('My prescriptions',reverse('prescriptions'))]
        elif topic=='directions':
            hospital = Hospital.objects.first()
            answer = hospital.address if hospital and hospital.address else 'The hospital has not published verified directions yet.'
            links = [('Hospital contact',reverse('contact'))]
        elif topic=='medicine':
            answer = 'Follow your clinician\'s prescription. I cannot recommend a drug, change a dose or validate interactions. Contact your care team or pharmacist for medicine questions.'
        elif topic=='support':
            answer = 'Use the hospital contact page for human support. This is not an emergency messaging channel.'
            links = [('Contact hospital',reverse('contact'))]
            if patient:
                # Topic only: do not store raw potentially clinical chat text.
                if not AssistantEscalation.objects.filter(patient=request.user,resolved=False,topic='technical').exists():
                    obj = AssistantEscalation.objects.create(patient=request.user,topic='technical')
                    audit(request.user,'assistant.escalated',obj.pk)
                answer += ' Your unresolved support request is recorded for administrators.'
    history = request.session.get('assistant_service_history', [])
    if request.method == 'POST':
        history = (history + [answer])[-8:]
        request.session['assistant_service_history'] = history
    return render(request,'care/assistant.html',{'form':form,'history':history,'answer':answer,'links':links,'slots':slots,'visits':visits,'faqs':faqs,'patient_access':patient})


@roles('doctor','receptionist','pharmacist','admin')
@require_http_methods(['GET'])
def worklist(request):
    today = timezone.localdate()
    first,last = day_bounds(today)
    if request.user.role=='doctor':
        visits = Appointment.objects.filter(slot__doctor=request.user,slot__start__gte=first,slot__start__lt=last)
        metrics = [('Today\'s assigned appointments',visits.count()),('Confirmed consultations',visits.filter(status='confirmed').count()),
            ('Completed visits',visits.filter(status='completed').count()),('Critical results awaiting acknowledgment',Investigation.objects.filter(appointment__slot__doctor=request.user,critical=True,status='resulted').count())]
        links = [('Weekly schedule and leave','schedule_rules'),('Appointment calendar','availability'),('My appointments','appointments'),('Admission requests','admissions')]
    elif request.user.role=='pharmacist':
        metrics = [('Pending prescriptions',Prescription.objects.filter(dispensed=False).exclude(appointment__status='cancelled').count()),('Out of stock',Medicine.objects.filter(stock=0).count()),
            ('Quarantined / recalled batches',Medicine.objects.exclude(safety_status='available').count()),('Open purchase requests',PurchaseOrder.objects.filter(status__in=['requested','approved']).count())]
        links = [('Prescription queue','prescriptions'),('Inventory / FEFO','inventory'),('Suppliers and purchases','purchasing'),('Stock audit','movements')]
    else:
        metrics = [('Today\'s appointments',Appointment.objects.filter(slot__start__gte=first,slot__start__lt=last).count()),('Waiting tokens',QueueEntry.objects.filter(date=today,status='waiting').count()),
            ('Pending admissions',Admission.objects.filter(status='requested').count()),('Discharge desk tasks',Admission.objects.filter(status='discharge_ready').count())]
        links = [('Registration and MRN','patients'),('Queue and check-in','queue'),('Admissions and beds','admissions'),('Appointments and billing','appointments')]
    if request.GET.get('export')=='csv':
        import csv
        from django.http import HttpResponse
        response=HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition']='attachment; filename="mednova-operational-summary.csv"'
        writer=csv.writer(response)
        writer.writerow(['Date (IST)','Role','Metric','Count'])
        for label,count in metrics:
            writer.writerow([str(today),request.user.role,label,count])
        audit(request.user,'operations.summary_exported',request.user.role)
        return response
    return render(request,'care/worklist.html',{'metrics':metrics,'links':links})


@roles('patient','receptionist')
@require_http_methods(['GET','POST'])
def waiting_list(request):
    class WaitingForm(forms.Form):
        doctor = forms.ModelChoiceField(queryset=User.objects.filter(role='doctor',approval='approved',is_active=True,doctor_profile__department__active=True))
        mode = forms.ChoiceField(choices=[('in_person','In person'),('video','Video')])
        patient = forms.ModelChoiceField(queryset=User.objects.filter(role='patient',is_active=True,approval='approved'),required=False)
    form = WaitingForm(request.POST or None, initial={'doctor':request.GET.get('doctor')})
    if request.user.role=='patient':
        form.fields.pop('patient')
    records = WaitingList.objects.select_related('patient','doctor').filter(active=True)
    if request.user.role=='patient':
        records = records.filter(patient=request.user)
    if request.method=='POST':
        if request.POST.get('action')=='leave':
            obj = get_object_or_404(records,pk=integer_id(request.POST.get('entry')))
            obj.active = False
            obj.save(update_fields=['active'])
            audit(request.user,'waiting_list.left',obj.pk)
            return redirect('waiting_list')
        elif form.is_valid():
            patient = request.user if request.user.role=='patient' else form.cleaned_data['patient']
            if not patient:
                form.add_error('patient','Choose an approved patient.')
            else:
                obj,_ = WaitingList.objects.update_or_create(patient=patient,doctor=form.cleaned_data['doctor'],mode=form.cleaned_data['mode'],defaults={'active':True})
                audit(request.user,'waiting_list.joined',obj.pk)
                return redirect('waiting_list')
    return render(request,'care/waiting_list.html',{'form':form,'records':paged(request,records.order_by('-created'))})
