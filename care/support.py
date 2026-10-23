"""Consented persistent handoff. Team access does not grant clinical-record access."""
import uuid
from functools import wraps
from django import forms
from django.contrib import messages
from django.db import transaction, DatabaseError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import SupportCase, SupportMessage, User, Appointment, Notification
from .security import roles, audit, rate_limit

TEAM_ROLES = {
    'appointments': ('receptionist', 'admin'), 'billing': ('receptionist', 'admin'),
    'technical': ('receptionist', 'admin'), 'privacy': ('admin',),
    'reports': ('doctor',), 'clinical': ('doctor',), 'pharmacy': ('pharmacist',),
}


def database_errors(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except DatabaseError:
            response = render(request, 'care/support_unavailable.html', status=503)
            response['Retry-After'] = '60'
            return response
    return wrapped


def can_read(user, case):
    if user.role == 'patient':
        return case.patient_id == user.pk
    if user.role not in TEAM_ROLES[case.category]:
        return False
    if user.role == 'doctor':
        return case.assigned_to_id == user.pk
    return True


def cases_for(user):
    qs = SupportCase.objects.select_related('patient', 'assigned_to', 'appointment__slot__doctor')
    if user.role == 'patient':
        return qs.filter(patient=user)
    if user.role == 'admin':
        return qs  # Medical cases show routing metadata only, not text or record references.
    if user.role == 'doctor':
        return qs.filter(category__in=['reports', 'clinical'], assigned_to=user)
    categories = [k for k, roles in TEAM_ROLES.items() if user.role in roles]
    return qs.filter(category__in=categories)


class CaseForm(forms.Form):
    category = forms.ChoiceField(choices=SupportCase.CATEGORIES)
    summary = forms.CharField(max_length=2000, widget=forms.Textarea, help_text='Review the issue and remove anything you do not want the selected hospital team to receive. Do not include passwords or payment card details.')
    appointment = forms.ModelChoiceField(queryset=Appointment.objects.none(), required=False)
    consent = forms.BooleanField(label='Share this summary, my patient identity and the selected appointment reference with the selected hospital team. I understand this is not emergency or live chat.')
    request_key = forms.UUIDField(widget=forms.HiddenInput)

    def __init__(self, *args, patient, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['appointment'].queryset = Appointment.objects.filter(patient=patient).select_related('slot__doctor').order_by('-slot__start')
        self.fields['appointment'].label_from_instance = lambda a: f'{a.short_id} · {a.slot.doctor.name} · {timezone.localtime(a.slot.start):%d %b %Y %H:%M %Z}'


class ReplyForm(forms.Form):
    text = forms.CharField(max_length=2000, widget=forms.Textarea, label='Message')
    internal = forms.BooleanField(required=False, label='Internal staff note (hidden from patient)')


class RoutingForm(forms.Form):
    category = forms.ChoiceField(choices=SupportCase.CATEGORIES)
    status = forms.ChoiceField(choices=SupportCase.STATUSES)
    priority = forms.ChoiceField(choices=[('routine','Routine'),('priority','Priority')])
    assigned_to = forms.ModelChoiceField(queryset=User.objects.filter(role__in=['doctor','receptionist','pharmacist','admin'], approval='approved', is_active=True).order_by('name'), required=False)

    def clean(self):
        data = super().clean()
        assignee, category = data.get('assigned_to'), data.get('category')
        if assignee and category and assignee.role not in TEAM_ROLES[category]:
            self.add_error('assigned_to', 'Choose approved staff from the destination team.')
        if data.get('status') == 'assigned' and not assignee:
            self.add_error('assigned_to', 'Select an assignee before marking the case assigned.')
        return data


@database_errors
@roles('patient', 'doctor', 'receptionist', 'pharmacist', 'admin')
@require_http_methods(['GET'])
def queue(request):
    records = cases_for(request.user)
    selected = request.GET.get('status', '')
    if selected in dict(SupportCase.STATUSES):
        records = records.filter(status=selected)
    return render(request, 'care/support_queue.html', {'cases': records[:100], 'statuses': SupportCase.STATUSES, 'selected': selected})


@database_errors
@roles('patient')
@rate_limit('support_create', 10, 60)
@require_http_methods(['GET','POST'])
def create(request):
    draft = request.session.get('support_draft', {})
    if timezone.now().timestamp() - draft.get('updated', 0) > 1800:
        draft = {}
    initial = {'category': draft.get('category', 'technical'), 'summary': draft.get('summary', ''), 'request_key': draft.get('request_key', str(uuid.uuid4())), 'appointment': draft.get('appointment')}
    form = CaseForm(request.POST if request.method == 'POST' else None, patient=request.user, initial=initial)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        with transaction.atomic():
            # Lock identity so double-clicks and concurrent retries cannot create duplicate cases.
            User.objects.select_for_update().get(pk=request.user.pk)
            existing = SupportCase.objects.filter(request_key=data['request_key']).first()
            if existing:
                if existing.patient_id != request.user.pk:
                    form.add_error(None, 'That submission reference is unavailable. Start a new support request.')
                else:
                    return redirect('support_case', pk=existing.pk)
            else:
                appt = data['appointment']
                assignee = appt.slot.doctor if appt and data['category'] in ('clinical','reports') and appt.slot.doctor.role == 'doctor' and appt.slot.doctor.is_active and appt.slot.doctor.approval == 'approved' else None
                case = SupportCase.objects.create(patient=request.user, category=data['category'], summary=data['summary'],
                    appointment=appt, assigned_to=assignee, status='assigned' if assignee else 'open',
                    priority='priority' if data['category'] in ('clinical','privacy') else 'routine',
                    request_key=data['request_key'], consented_at=timezone.now())
                audit(request.user, 'support.created', case.pk)
                SupportMessage.objects.create(case=case, author=request.user, text='Patient reviewed and consented to the support summary.')
                request.session.pop('support_draft', None)
                request.session.pop('handoff_context', None)
                messages.success(request, 'Support case saved. This is a hospital portal queue, not a live transfer. No external message was sent.')
                return redirect('support_case', pk=case.pk)
    return render(request, 'care/support_create.html', {'form': form})


@database_errors
@roles('patient', 'doctor', 'receptionist', 'pharmacist', 'admin')
@rate_limit('support_updates', 30, 60)
@require_http_methods(['GET','POST'])
def detail(request, pk):
    case = get_object_or_404(cases_for(request.user), pk=pk)
    readable = can_read(request.user, case)
    staff = request.user.role != 'patient'
    reply = ReplyForm(request.POST if request.method=='POST' and request.POST.get('action')=='reply' else None, auto_id='reply_%s')
    if not staff:
        reply.fields.pop('internal')
    route = RoutingForm(request.POST if request.method=='POST' and request.POST.get('action')=='route' else None,
        initial={'category':case.category,'status':case.status,'priority':case.priority,'assigned_to':case.assigned_to_id}, auto_id='route_%s')
    route.fields['assigned_to'].queryset = route.fields['assigned_to'].queryset.filter(role__in=TEAM_ROLES[case.category])
    if staff and request.user.role != 'admin':
        route.fields['category'].disabled = True
        route.fields['assigned_to'].disabled = True
    if request.method=='POST':
        with transaction.atomic():
            case = get_object_or_404(cases_for(request.user).select_for_update(of=('self',)), pk=pk)
            readable = can_read(request.user, case)
            action = request.POST.get('action')
            if action=='reply' and readable and reply.is_valid():
                internal = reply.cleaned_data.get('internal', False) if staff else False
                SupportMessage.objects.create(case=case, author=request.user, text=reply.cleaned_data['text'], internal=internal)
                if not staff and case.status in ('waiting_for_patient','resolved','closed'):
                    case.status='open'
                case.save(update_fields=['status','updated'])
                if staff and not internal:
                    Notification.objects.create(recipient=case.patient, message='Your hospital support case has a new portal reply.')
                audit(request.user, 'support.internal_note' if internal else 'support.reply', case.pk)
                return redirect('support_case', pk=case.pk)
            elif action=='route' and staff and (readable or request.user.role=='admin') and route.is_valid():
                data = route.cleaned_data
                groups = {'appointments':'operations','billing':'operations','technical':'operations',
                          'reports':'clinical','clinical':'clinical','pharmacy':'pharmacy','privacy':'privacy'}
                # Only administrators may move a case into a different team or assign another worker.
                if groups[data['category']] != groups[case.category]:
                    route.add_error('category', 'This would share the existing conversation with a different access group. Ask the patient to consent to a new case for that team.')
                elif request.user.role != 'admin' and (data['category'] != case.category or (data['assigned_to'] and data['assigned_to'].pk != request.user.pk)):
                    route.add_error(None, 'Only administrators can reassign another worker or change the destination team.')
                else:
                    previous = f'{case.category}/{case.status}'
                    for field in ('category','status','priority','assigned_to'):
                        setattr(case, field, data[field])
                    case.save()
                    # An audit message contains routing metadata only, never the summary.
                    SupportMessage.objects.create(case=case, author=request.user, text=f'Routing/status changed: {previous} → {case.category}/{case.status}.', internal=True)
                    audit(request.user, 'support.routed', case.pk)
                    Notification.objects.create(recipient=case.patient, message='Your hospital support case status has been updated.')
                    return redirect('support_case', pk=case.pk)
            else:
                messages.error(request, 'This support action is not permitted or contains invalid fields.')
    visible_messages = case.messages.select_related('author')
    if not staff:
        visible_messages = visible_messages.filter(internal=False)
    if readable:
        audit(request.user, 'support.viewed', case.pk)
    return render(request, 'care/support_detail.html', {'case':case, 'readable':readable, 'staff':staff,
        'case_messages':list(reversed(list(visible_messages.order_by('-created','-pk')[:100]))) if readable else [], 'reply_form':reply, 'route_form':route})
