"""Read-only patient service tools and patient-reviewed handoff preparation."""
import re
import uuid
from decimal import Decimal
from django.conf import settings
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from .models import Appointment, Report, Investigation, Prescription, Payment, Admission, QueueEntry, SupportCase, Hospital
from .security import audit


def prepare_handoff(request, question, category='technical', appointment=None):
    from .chatbot import patient, reply, link
    if not patient(request):
        return reply('Sign in as a patient to prepare a private support case. You can also contact the hospital directly.',
            [{'label':'Patient sign-in','url':reverse('login')+'?role=patient&next=/assistant/'}, link('Hospital contact','contact')])
    previous = request.session.get('handoff_context', {})
    if timezone.now().timestamp() - previous.get('updated', 0) < 1800 and category=='technical' and previous.get('issue'):
        question, category, appointment = previous['issue'], previous['category'], previous.get('appointment')
    if re.search(r'password|api.?key|secret|token|card number|cvv', question, re.I):
        question = '[Credential or payment details omitted. Please describe the service problem without secrets.]'
    if appointment:
        appt = Appointment.objects.filter(pk=appointment, patient=request.user).select_related('slot__doctor').first()
    else:
        appt = None
    summary = f'Patient-reported issue (not independently verified): {question[:500]}\nMessage time: {timezone.localtime():%d %b %Y %H:%M %Z}.\nRequested team: {dict(SupportCase.CATEGORIES).get(category, "Portal support")}.'
    if appt:
        summary += f'\nVerified linked appointment: {appt.short_id}; {appt.slot.doctor.name}; {timezone.localtime(appt.slot.start):%d %b %Y %H:%M %Z}; status: {appt.get_status_display()}.'
    old = request.session.get('support_draft', {})
    request.session['support_draft'] = {'category':category, 'summary':summary, 'appointment':str(appt.pk) if appt else None,
        'request_key':old.get('request_key', str(uuid.uuid4())), 'updated':timezone.now().timestamp()}
    request.session['handoff_context'] = {'issue':question[:500], 'category':category, 'appointment':str(appt.pk) if appt else None, 'updated':timezone.now().timestamp()}
    return reply('This needs the hospital team’s review. I have prepared your issue summary, but no case has been created or message sent. Review, edit and confirm what to share. Once saved, staff can review the details without asking you to repeat them.',
        [link('Review summary and create support case','support_create'), link('My support cases','support_queue')])


def intents(question):
    q = question.casefold()
    q = re.sub(r'\bap+oin?t?ments?\b', 'appointment', q)
    result = []
    terms = {
        'reports': ('report','test result','blood result','scan result'),
        'prescriptions': ('prescription','presciption','prescribed','my medicine','medication'),
        'billing': ('bill','invoice','outstanding','payment','refund','receipt'),
        'admissions': ('my admission','my discharge','my bed','admission status'),
        'queue': ('waiting','waited','queue','delayed visit'),
        'preparation': ('bring','prepar','required document','check in','check-in','visit instruction','video requirement'),
        'tickets': ('my case','case status','my ticket','ticket status','support status'),
    }
    for intent, phrases in terms.items():
        if any(p in q for p in phrases):
            # Public hospital policies and opening hours are answered from approved content, not patient records.
            if intent in ('billing','prescriptions','reports') and ('insurance' in q or 'hours' in q or 'timings' in q or 'services offered' in q):
                continue
            result.append(intent)
    if ('appointment' in q or 'my visit' in q or 'follow-up' in q or 'follow up' in q) and not any(p in q for p in ('book','available','can i see','consult a')):
        if not result or any(p in q for p in (' and ', 'also', 'reschedule','cancel')):
            result.append('appointments')
    return list(dict.fromkeys(result))[:4]


def run(request, question, context):
    from .chatbot import patient, reply, link, faq_matches
    q = question.casefold()
    if any(p in q for p in ('privacy complaint','security concern','report abuse','safeguard','not my report','incorrectly linked')):
        return prepare_handoff(request, question, 'clinical' if any(p in q for p in ('abuse','safeguard')) else 'privacy', context.get('appointment'))
    found = intents(question)
    if not found and 'doctor' not in q and context.get('service_intent') in ('reports','prescriptions','billing','appointments','queue') and re.search(r'\b(it|that|those|still|latest)\b', q):
        found = [context['service_intent']]
    human = any(p in q for p in ('real person','human','support','complaint','privacy','incorrectly linked','not my report','reaction','side effect','abuse','safeguard','diagnosis','diagnose','change dose','stop treatment'))
    issue = any(p in q for p in ('cannot','can t','can’t',"can't",'missing','pending for','long time','unavailable','didn t cancel',"didn't cancel",'didn’t cancel','dispute','wrong','not received','not my','reaction','side effect'))
    if found == ['tickets']:
        human = False
    if human and not found:
        category = 'privacy' if any(p in q for p in ('privacy','not my','security')) else 'clinical' if any(p in q for p in ('reaction','side effect','abuse','safeguard','diagnosis','diagnose','change dose','stop treatment')) else 'technical'
        return prepare_handoff(request, question, category, context.get('appointment'))
    if not found:
        return None
    public_only = found == ['preparation']
    if not patient(request) and not public_only:
        return reply('Sign in securely as a patient so I can check only your own records.', [{'label':'Patient sign-in','url':reverse('login')+'?role=patient&next=/assistant/'}])
    context['service_intent'] = found[0]
    cards, text, actions, references_seen = [], [], [], set()
    latest_ref = None
    for intent in found:
        if intent == 'reports':
            reports = Report.objects.filter(appointment__patient=request.user).select_related('appointment__slot__doctor').order_by('-created')[:8]
            orders = Investigation.objects.filter(appointment__patient=request.user).select_related('appointment').order_by('-created')[:8]
            text.append('These are your uploaded reports and recorded investigation statuses. No completion date or diagnosis is inferred. A file upload and an investigation result are separate records.')
            for report in reports:
                latest_ref = str(report.appointment_id)
                references_seen.add(latest_ref)
                cards.append({'title':report.title,'details':[f'Report file uploaded: {timezone.localtime(report.created):%d %b %Y %H:%M %Z}', f'Visit {report.appointment.short_id} · {report.appointment.slot.doctor.name}'], 'links':[link('Secure report download','download',report.pk),link('Open related visit','appointment',report.appointment_id)]})
            for order in orders:
                latest_ref = str(order.appointment_id)
                references_seen.add(latest_ref)
                cards.append({'title':order.name,'details':[order.get_category_display(), 'Recorded status: '+order.get_status_display(), f'Ordered {timezone.localtime(order.created):%d %b %Y %H:%M %Z}', 'Expected completion time is not stored.' if order.status=='ordered' else 'Open the authorized clinical page for the recorded result.'], 'links':[link('View investigation securely','clinical_work',order.appointment_id)]})
            if not reports and not orders:
                text.append('No report uploads or investigations are linked to your account. This does not establish whether a test was performed elsewhere.')
            if issue:
                text.append('For download problems, sign in again and retry the secure download. If it still fails or the report is missing, review a support summary for the assigned clinician; reception cannot read your medical report through this queue.')
        elif intent == 'prescriptions':
            records = Prescription.objects.filter(appointment__patient=request.user).select_related('appointment__slot__doctor').prefetch_related('items__medicine').order_by('-created')[:5]
            text.append('These instructions were recorded by your clinician. I cannot prescribe, change doses or recommend stopping treatment.')
            for rx in records:
                latest_ref = str(rx.appointment_id)
                references_seen.add(latest_ref)
                details = [rx.appointment.slot.doctor.name, 'Fully dispensed' if rx.dispensed else 'Not marked fully dispensed', 'Recorded instructions: '+rx.instructions]
                for item in rx.items.all():
                    details.append(f'{item.medicine.name} · Recorded dose: {item.dose} · {item.route} {item.frequency} {item.duration_text} · Dispensed {item.dispensed_quantity}/{item.quantity}')
                cards.append({'title':f'Prescription · {rx.appointment.short_id}', 'details':details, 'links':[link('Open recorded prescription','appointment',rx.appointment_id)]})
            if not records:
                text.append('No prescription is linked to your patient account.')
            actions.append(link('Pharmacy services and contact','pharmacy_info'))
        elif intent == 'billing':
            payments = Payment.objects.filter(appointment__patient=request.user).select_related('appointment__slot__doctor')
            total = payments.filter(status='unpaid').exclude(appointment__status='cancelled').aggregate(value=Sum('amount'))['value'] or Decimal('0')
            text.append(f'Outstanding recorded consultation charges for non-cancelled visits: ₹{total:.2f}. This is not a total for hospital services that are not recorded in this module. Refunds and payment processing require the authorized billing workflow.')
            for payment in payments.order_by('-updated')[:8]:
                latest_ref = str(payment.appointment_id)
                references_seen.add(latest_ref)
                links = [link('Payment record / receipt','receipt',payment.appointment_id)]
                if payment.status=='unpaid' and payment.appointment.status!='cancelled' and settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
                    links.append(link('Review secure online payment','pay',payment.appointment_id))
                cards.append({'title':f'Billing · {payment.appointment.short_id}', 'details':[f'₹{payment.amount}', 'Recorded status: '+payment.get_status_display()], 'links':links})
            if not payments.exists():
                text.append('No billing record is linked to your account.')
        elif intent == 'appointments':
            visits = Appointment.objects.filter(patient=request.user).select_related('slot__doctor__doctor_profile__department')
            if 'next' in q or 'upcoming' in q:
                visits = visits.filter(slot__start__gt=timezone.now()).exclude(status='cancelled').order_by('slot__start')
            else:
                visits = visits.order_by('-slot__start')
            # Appointment references are matched only inside this patient's queryset.
            references = re.findall(r'\b[a-fA-F0-9]{8}\b', question)
            if references:
                own = list(visits[:100])
                visits = [v for v in own if v.short_id.casefold() in [s.casefold() for s in references]]
            else:
                visits = list(visits[:8])
            text.append('Your appointment records are below. Booking changes need your confirmation; no appointment has been changed by this message.')
            if len(visits)==1:
                context['appointment'] = str(visits[0].pk)
                context['profiles'] = [visits[0].slot.doctor.doctor_profile.pk]
                latest_ref = str(visits[0].pk)
            for visit in visits:
                references_seen.add(str(visit.pk))
                profile = visit.slot.doctor.doctor_profile
                details = [visit.slot.doctor.name, profile.department.name, timezone.localtime(visit.slot.start).strftime('%d %b %Y, %I:%M %p %Z'), visit.get_status_display(), profile.location or 'Visit location/room not published.']
                links = [link('Open visit / confirm cancellation','appointment',visit.pk)]
                if visit.status in ('pending','confirmed') and visit.slot.start > timezone.now():
                    links.append({'label':'Review reschedule options','url':reverse('booking',args=[visit.slot.doctor_id])+'?reschedule='+str(visit.pk)})
                if visit.mode=='video' and visit.status=='confirmed':
                    links.append(link('Video consultation entry and device check','video',visit.pk))
                if visit.status=='cancelled':
                    details.append('Recorded cancellation reason: '+(visit.cancellation_reason or 'No reason is recorded. I cannot establish who cancelled or why from this field.'))
                links.append(link('Request a follow-up with this doctor','booking',visit.slot.doctor_id))
                cards.append({'title':'Appointment · '+visit.short_id,'details':details,'links':links})
            if not visits:
                text.append('No matching appointment belongs to your account.')
            h = Hospital.objects.first()
            if h and ('cancel' in q or 'reschedule' in q):
                text.append(f'Configured cancellation notice: {h.cancellation_notice_minutes} minutes. '+(h.cancellation_policy or 'No additional cancellation policy is published.'))
        elif intent == 'queue':
            entries = QueueEntry.objects.filter(appointment__patient=request.user, date=timezone.localdate()).select_related('appointment')[:8]
            text.append('Your recorded check-in queue status is below. A reliable waiting-time estimate is not stored; contact reception for a delay.')
            for entry in entries:
                latest_ref = str(entry.appointment_id)
                references_seen.add(latest_ref)
                cards.append({'title':f'Your token {entry.number}','details':[str(entry.date),entry.get_status_display()],'links':[link('Open my visit','appointment',entry.appointment_id)]})
            if not entries:
                text.append('No check-in queue token is recorded for you today.')
        elif intent == 'admissions':
            records = Admission.objects.filter(patient=request.user).select_related('department','doctor','bed').order_by('-created')[:8]
            for record in records:
                cards.append({'title':record.department.name,'details':[record.get_status_display(),record.doctor.name,str(record.bed) if record.bed else record.last_bed or 'Bed not assigned.'],'links':[link('My admissions','admissions')]})
            text.append('Your recorded admission statuses are shown.' if records else 'No admission is recorded for your account.')
        elif intent == 'preparation':
            facts = faq_matches(request, set(re.findall(r'\w+',q)))
            text.append('\n'.join(facts) if facts else 'Appointment preparation, required documents and department-specific instructions have not been published in the approved knowledge base. Ask your care team before changing food, fluids or medication.')
            if 'video' in q:
                text.append('The existing video consultation page provides device checks and patient consent. Open the confirmed video visit to review its entry requirements; this chat cannot verify your camera or connection.')
            actions.extend([link('Hospital contact','contact'),link('My appointments','appointments')])
        elif intent == 'tickets':
            cases = SupportCase.objects.filter(patient=request.user).order_by('-updated')[:8]
            text.append('These are the support cases actually saved for your patient account. Replies are in the portal; this is not a live transfer.')
            for case in cases:
                cards.append({'title':case.reference,'details':[case.get_category_display(),case.get_status_display(),f'Updated {timezone.localtime(case.updated):%d %b %Y %H:%M %Z}'],'links':[link('Read case and reply','support_case',case.pk)]})
            if not cases:
                text.append('No support case has been created yet.')
            actions.append(link('My support cases','support_queue'))
        if patient(request):
            audit(request.user, 'assistant.'+intent+'_viewed', request.user.pk)
    if issue or human:
        category = 'privacy' if any(p in q for p in ('not my','privacy','security','incorrectly linked')) else 'reports' if 'reports' in found else 'pharmacy' if 'prescriptions' in found else 'billing' if 'billing' in found else 'appointments' if 'appointments' in found or 'queue' in found else 'technical'
        verified_ref = next(iter(references_seen)) if len(references_seen)==1 else None
        previous = request.session.get('handoff_context', {})
        if previous.get('category') == category and previous.get('issue') and previous['issue'] != question and timezone.now().timestamp()-previous.get('updated',0)<1800:
            question = previous['issue'][:240] + '\nFollow-up: ' + question[:240]
        handoff = prepare_handoff(request, question, category, verified_ref)
        text.append(handoff['text'])
        actions.extend(handoff['links'])
    return reply('\n\n'.join(text), actions, cards, ['My appointments','My reports','Prescription help','Billing help','My case status'])
