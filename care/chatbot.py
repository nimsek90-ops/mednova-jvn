"""Local hospital intent matching. Never sends conversation or records to a provider."""
import json
import re
from datetime import date, timedelta
from difflib import get_close_matches

from django.db import DatabaseError
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import Department, Hospital, HospitalFAQ, ScheduleSession, AssistantEscalation, Medicine
from .scheduling import available_slots, day_bounds
from .security import limited
from .views import approved_profiles, visible_appointments

SPECIALTIES = {
    'cardio': ['heart', 'cardiologist', 'cardiology', 'cardiologists'],
    'dermat': ['skin', 'dermatologist', 'dermatology'],
    'neuro': ['brain', 'neurologist', 'neurology'],
    'ortho': ['bone', 'bones', 'orthopedic', 'orthopedics', 'orthopaedic'],
    'pediatr': ['child', 'children', 'pediatrician', 'pediatrics', 'paediatrician'],
    'endocrin': ['diabetes', 'diabetic', 'endocrinologist', 'endocrinology'],
    'general': ['general medicine', 'general physician'],
    'gynec': ['gynecologist', 'gynaecologist', 'gynecology'],
    'ophthalm': ['eye', 'eyes', 'ophthalmologist'],
    'ent': ['ear', 'nose', 'throat', 'ent'],
    'urolog': ['urologist', 'urology'],
    'nephro': ['kidney', 'nephrologist', 'nephrology'],
    'pulmon': ['lung', 'lungs', 'pulmonologist', 'pulmonology'],
    'gastro': ['stomach', 'gastroenterologist', 'gastroenterology'],
    'dent': ['dental', 'dentist', 'teeth'],
    'psychiatr': ['psychiatrist', 'psychiatry'],
}


def reply(text, links=None, cards=None, suggestions=None):
    return {'text': text, 'links': links or [], 'cards': cards or [],
            'suggestions': suggestions or [], 'timestamp': timezone.now().isoformat()}


def link(label, name, *args):
    return {'label': label, 'url': reverse(name, args=args)}


def patient(request):
    u = request.user
    return u.is_authenticated and u.is_active and u.role == 'patient' and u.approval == 'approved'


def answer(request, question, context):
    q = re.sub(r'[^\w\s:-]', ' ', question.casefold())
    words = set(q.split())
    if any(x in q for x in ('chest pain', 'cannot breathe', 'can t breathe', 'unconscious', 'heavy bleeding', 'severe bleeding', 'stroke', 'emergency', 'rapidly worsening', 'swollen throat', 'suicidal', 'kill myself', 'self harm')):
        try:
            hospital = Hospital.objects.first()
        except DatabaseError:
            hospital = None
        contact = f' Published hospital ambulance contact: {hospital.ambulance}.' if hospital and hospital.ambulance else ''
        return reply('Potential emergency: seek immediate emergency care. In India call 112 or go to the nearest emergency department. Do not wait for chat. I have not contacted emergency services.' + contact)
    from .patient_assistant import run
    service_reply = run(request, question, context)
    if service_reply is not None:
        return service_reply
    if words & {'support', 'human', 'reception', 'helpdesk'}:
        text = 'Contact the hospital team using the verified contact page. This is not an emergency channel.'
        if patient(request):
            AssistantEscalation.objects.get_or_create(patient=request.user, topic='technical', resolved=False)
            text += ' Your support request is recorded; only your account and support topic are stored.'
        return reply(text, [link('Contact hospital', 'contact')])
    if words & {'stock', 'inventory'}:
        u = request.user
        if not (u.is_authenticated and u.is_active and u.approval == 'approved' and u.role in ('pharmacist', 'admin')):
            return reply('Medicine inventory is restricted to authorized pharmacy staff. Ask the hospital pharmacist about your prescription.', [link('Pharmacy information', 'pharmacy_info')])
        return reply('Open the authorized inventory for batch stock, expiry and safety status. I cannot recommend medicines or change doses.', [link('Medicine inventory', 'inventory')])
    private = words & {'appointments', 'appointment', 'reports', 'report', 'prescription', 'prescriptions', 'invoice', 'billing', 'admission', 'admissions', 'results', 'cancel', 'reschedule'}
    searching = words & {'doctor', 'doctors', 'specialist', 'specialists', 'available', 'slots', 'consult', 'book'}
    if private and (not searching or words & {'cancel', 'reschedule'} or ('my' in words and 'book' not in words)):
        if not patient(request):
            return reply('Sign in as an approved patient to access your own records.', [{'label': 'Patient sign-in', 'url': reverse('login') + '?role=patient&next=/assistant/'}])
        visits = visible_appointments(request.user).select_related('slot__doctor')
        if words & {'upcoming', 'next', 'future'}:
            visits = visits.filter(slot__start__gt=timezone.now()).exclude(status='cancelled').order_by('slot__start')
        else:
            visits = visits.order_by('-slot__start')
        visits = visits[:8]
        cards = []
        for visit in visits:
            actions = [link('Open visit, reports, billing and cancellation', 'appointment', visit.pk)]
            if visit.status in ('pending', 'confirmed'):
                actions.append({'label': 'Reschedule appointment', 'url': reverse('booking', args=[visit.slot.doctor_id]) + '?reschedule=' + str(visit.pk)})
            cards.append({'title': f'{visit.short_id} · {visit.slot.doctor.name}', 'details': [timezone.localtime(visit.slot.start).strftime('%d %b %Y, %I:%M %p %Z'), visit.get_status_display()], 'links': actions})
        links = [link('My prescriptions', 'prescriptions'), link('My admissions', 'admissions'), link('My medical timeline', 'timeline', request.user.pk)]
        return reply('Your own records are shown below. Open a visit to review reports or confirm cancellation. To reschedule, open its booking form; the existing booking rules apply.', links, cards)
    if words & {'address', 'contact', 'phone', 'directions', 'hours', 'policy', 'insurance', 'facilities'} and not (searching or 'visiting' in words):
        h = Hospital.objects.first()
        fields = [('Address', 'address'), ('Phone', 'phone'), ('Email', 'email'), ('Opening hours', 'opening_hours'), ('Cancellation policy', 'cancellation_policy')]
        facts = [f'{label}: {getattr(h, field)}' for label, field in fields if h and getattr(h, field)]
        faqs = faq_matches(request, words)
        return reply('\n'.join(facts + faqs) or 'This hospital information has not been published. Please contact reception.', [link('Verified contact information', 'contact')])
    if words & {'departments', 'department'} and not searching:
        names = list(Department.objects.filter(active=True).order_by('name').values_list('name', flat=True)[:30])
        return reply('Published departments: ' + ', '.join(names) if names else 'No departments are published.', suggestions=names[:8])
    # Match synonyms and small spelling mistakes against a bounded specialty vocabulary.
    specialty = None
    for stem, aliases in SPECIALTIES.items():
        if any(alias in q if ' ' in alias else alias in words for alias in aliases):
            specialty = stem
            break
    if not specialty:
        vocabulary = {alias: stem for stem, aliases in SPECIALTIES.items() for alias in aliases if ' ' not in alias}
        for word in words:
            close = get_close_matches(word, vocabulary, n=1, cutoff=.86)
            if close:
                specialty = vocabulary[close[0]]
                break
    if words & {'medicine', 'medication', 'dose', 'dosage', 'diagnose', 'treatment'} and not specialty and not searching:
        faqs = faq_matches(request, words)
        return reply('\n'.join(faqs) if faqs else 'I cannot diagnose, recommend prescription medicines or change a dose. Follow the instructions recorded by your clinician and contact your care team for advice.', [link('Pharmacy information', 'pharmacy_info')])
    profiles = approved_profiles().order_by('user__name', 'pk')
    if specialty:
        from django.db.models import Q
        profiles = profiles.filter(Q(department__name__icontains=specialty) | Q(qualification__icontains=specialty))
        context.clear()
        context['specialty'] = specialty
    else:
        # Name/department matching uses published records only; never an email or private identifier.
        candidates = list(profiles[:200])
        named = [p.pk for p in candidates if p.user.name.strip() and re.sub(r'[^\w\s]', ' ', p.user.name.casefold()).strip() in q]
        matched = named or [p.pk for p in candidates if any(len(w) >= 3 and w in (p.user.name + ' ' + p.department.name + ' ' + p.qualification).casefold().split() for w in words - {'doctor', 'doctors', 'medicine', 'general', 'available', 'which', 'one', 'show', 'time'})]
        if matched:
            profiles = profiles.filter(pk__in=matched)
            context.clear()
            context['profiles'] = matched
        elif words & {'one', 'ones', 'they', 'same', 'tomorrow', 'morning', 'evening', 'today', 'slots', 'video'} and context:
            if context.get('specialty'):
                profiles = profiles.filter(department__name__icontains=context['specialty'])
            elif context.get('profiles'):
                profiles = profiles.filter(pk__in=context['profiles'])
        elif not searching and not specialty and not ('visiting' in words or 'dr' in words):
            faqs = faq_matches(request, words)
            return reply('\n\n'.join(faqs) if faqs else 'I could not match that to verified hospital information. Try a doctor name, specialty, date or one of these services. For symptoms or treatment, consult a clinician; I cannot diagnose or prescribe.', [link('Human support', 'contact')], suggestions=['Find doctors', 'My appointments', 'Hospital address', 'Human support'])
        elif 'dr' in words and not matched:
            return reply('No approved doctor matched that name. Try the full name or browse the doctor directory.', [link('Doctor directory', 'doctors')])
        elif not matched and any(w.endswith(('ologist', 'ology')) for w in words):
            return reply('I could not match that specialty to published doctor records. Please choose a department from the directory.', [link('Doctor directory', 'doctors')])
        elif words & {'all', 'doctors'}:
            context.clear()
    day = None
    if 'tomorrow' in words:
        day = timezone.localdate() + timedelta(days=1)
    elif 'today' in words:
        day = timezone.localdate()
    else:
        found = re.search(r'\b\d{4}-\d{2}-\d{2}\b', question)
        if found:
            try:
                day = date.fromisoformat(found[0])
            except ValueError:
                return reply('Please enter a valid date in YYYY-MM-DD format.')
        for offset in range(7):
            candidate = timezone.localdate() + timedelta(days=offset)
            if candidate.strftime('%A').casefold() in words:
                day = candidate
                break
    profiles = list(profiles[:9])
    context.pop('service_intent', None)
    if not profiles:
        return reply('No approved registered doctor matches this specialty or name. No availability has been invented.', [link('Browse all doctors', 'doctors')])
    more = len(profiles) > 8
    profiles = profiles[:8]
    ids = [p.user_id for p in profiles]
    slots = available_slots(doctor_ids=ids).order_by('start')
    if day:
        context['day'] = day.isoformat()
    elif context.get('day') and words & {'video', 'person', 'morning', 'afternoon', 'evening', 'one', 'ones'}:
        day = date.fromisoformat(context['day'])
    if day:
        first, last = day_bounds(day)
        slots = slots.filter(start__gte=first, start__lt=last)
    mode = 'video' if 'video' in words or 'online' in words else 'in_person' if 'person' in words or 'offline' in words else None
    if mode:
        context['mode'] = mode
    else:
        mode = context.get('mode')
    if mode:
        slots = slots.filter(consultation_type__in=[mode, 'both'])
    grouped = {pk: [] for pk in ids}
    daypart = next((p for p in ('morning','afternoon','evening') if p in words), None)
    if daypart:
        context['daypart'] = daypart
        context.pop('after_minute', None)
    elif words & {'today','tomorrow'}:
        context.pop('daypart', None)
        context.pop('after_minute', None)
    else:
        daypart = context.get('daypart')
    after = re.search(r'\bafter\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b', q)
    after_minute = None
    if after:
        hour, minute, period = int(after[1]), int(after[2] or 0), after[3]
        if minute > 59 or hour > 23 or (period and not 1 <= hour <= 12):
            return reply('Please use a valid time, for example “after 5 pm”.')
        if not period and hour <= 12:
            return reply('Do you mean AM or PM? For example, “available after 5 pm”.')
        if period:
            hour = hour % 12 + (12 if period == 'pm' else 0)
        after_minute = hour * 60 + minute
        context['after_minute'] = after_minute
    elif context.get('after_minute') is not None:
        after_minute = context['after_minute']
    for slot in slots:
        local = timezone.localtime(slot.start)
        hour = local.hour
        if after_minute is not None and hour * 60 + local.minute <= after_minute:
            continue
        if daypart == 'morning' and not 6 <= hour < 12 or daypart == 'afternoon' and not 12 <= hour < 17 or daypart == 'evening' and not 17 <= hour < 22:
            continue
        if len(grouped[slot.doctor_id]) < 3:
            grouped[slot.doctor_id].append(slot)
    sessions = {}
    for session in ScheduleSession.objects.filter(doctor_id__in=ids, active=True):
        sessions.setdefault(session.doctor_id, []).append(f'{session.get_weekday_display()} {session.start:%H:%M}–{session.end:%H:%M}, {session.duration} min + {session.buffer} min buffer, {session.get_mode_display()}')
    cards = []
    for p in profiles:
        details = [p.department.name, p.qualification or 'Qualification not published', f'{p.experience} years experience · Fee ₹{p.fee}', p.location or 'Room/location not published']
        details.extend(sessions.get(p.user_id, ['Recurring visiting hours not published.']))
        links = [link('View profile', 'doctor_detail', p.user_id), link('Review and book appointment', 'booking', p.user_id)]
        for slot in grouped[p.user_id]:
            details.append(f'Available: {timezone.localtime(slot.start):%d %b %Y, %I:%M %p %Z} · {slot.duration} min + {slot.buffer} min buffer · {slot.get_consultation_type_display()}')
            links.append({'label': f'Select {timezone.localtime(slot.start):%d %b, %I:%M %p}', 'url': reverse('booking', args=[p.user_id]) + f'?date={timezone.localdate(slot.start).isoformat()}&slot={slot.pk}'})
        if not grouped[p.user_id]:
            details.append('Registered doctor; no verified slots matching this date/time/mode.')
        cards.append({'title': p.user.name, 'details': details, 'links': links})
    return reply('Live scheduling results' + (f' for {day:%d %b %Y}' if day else '') + '. Times use the hospital timezone. Slots are rechecked when you confirm on the booking form. ' + ('Showing eight doctors; use the directory for more.' if more else ''), [link('Full doctor directory', 'doctors')], cards, ['Tomorrow morning', 'Available today', 'Video consultation', 'My appointments'])


def faq_matches(request, words):
    ignored = {'the', 'is', 'what', 'are', 'how', 'i', 'a', 'of', 'to', 'my', 'in'}
    scored = []
    for faq in HospitalFAQ.objects.filter(approved=True, language=getattr(request, 'language', 'en')).order_by('-updated')[:100]:
        score = len((words - ignored) & set(re.findall(r'\w+', faq.question.casefold())))
        if score:
            scored.append((score, faq.answer))
    return [text for _, text in sorted(scored, reverse=True)[:2]]


@require_http_methods(['GET', 'POST'])
def api(request):
    try:
        who = str(request.user.pk) if request.user.is_authenticated else request.META.get('REMOTE_ADDR', 'unknown')
        if limited('chatbot:' + who, 40, 60):
            response = JsonResponse({'error': 'Too many messages. Please retry in one minute.'}, status=429)
            response['Retry-After'] = '60'
            return response
        state = request.session.get('hospital_chat', {})
        if state.get('owner') != str(request.user.pk) or timezone.now().timestamp() - state.get('updated', 0) > 1800:
            state = {}
        if request.method == 'GET':
            return JsonResponse({'history': state.get('history', []), 'greeting': reply('Hello, I’m your MedNova service assistant. Find a doctor, check live appointment times or open your own records. I cannot diagnose or prescribe.', suggestions=['Find doctors', 'Heart specialist', 'My appointments', 'Hospital address'])})
        if len(request.body) > 4096:
            return JsonResponse({'error': 'Message is too large.'}, status=400)
        try:
            payload = json.loads(request.body)
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({'error': 'Send a valid JSON message.'}, status=400)
        if not isinstance(payload, dict):
            return JsonResponse({'error': 'Send a message object.'}, status=400)
        if payload.get('action') == 'clear':
            request.session.pop('hospital_chat', None)
            request.session.pop('assistant_service_history', None)
            request.session.pop('support_draft', None)
            request.session.pop('handoff_context', None)
            return JsonResponse({'cleared': True})
        question = payload.get('message')
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 500:
            return JsonResponse({'error': 'Enter a message of 1–500 characters.'}, status=400)
        context = state.get('context', {})
        result = answer(request, question.strip(), context)
        # Keep only public service replies server-side. Private record cards and raw questions are never retained.
        public = not patient(request)
        history = (state.get('history', []) + ([result] if public else []))[-6:]
        request.session['hospital_chat'] = {'owner': str(request.user.pk), 'updated': timezone.now().timestamp(), 'context': context, 'history': history}
        response = JsonResponse(result)
        response['Cache-Control'] = 'no-store'
        return response
    except DatabaseError:
        return JsonResponse({'error': 'Hospital records are temporarily unavailable. Please retry or contact reception.'}, status=503)
