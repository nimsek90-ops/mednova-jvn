import base64
import hashlib
import hmac
import json
import logging
import re
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction, IntegrityError
from django.db.models import Q, Count
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode, url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods
from .models import *
from .forms import *
from .security import roles, rate_limit, limited, audit
from .services import book, change_status, dispense, BookingError

logger = logging.getLogger(__name__)


def safe_next(request, fallback="dashboard"):
    target = request.POST.get("next") or request.GET.get("next", "")
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure()):
        return target
    return reverse(fallback)


def approved_profiles():
    return DoctorProfile.objects.select_related("user", "department").filter(
        user__role="doctor", user__approval="approved", user__is_active=True,
        department__active=True,
    )


@require_http_methods(["GET"])
def home(request):
    return render(request, "care/home.html", {
        "departments": Department.objects.filter(active=True).order_by("name")[:6],
        "doctors": approved_profiles().order_by("user__name")[:3],
    })


@require_http_methods(["GET"])
def public_departments(request):
    return render(request, "care/public_departments.html", {
        "departments": Department.objects.filter(active=True).order_by("name"),
    })


@require_http_methods(["GET"])
def doctor_detail(request, pk):
    doctor = get_object_or_404(approved_profiles(), user_id=pk)
    return render(request, "care/doctor_detail.html", {
        "doc": doctor,
        "slots": Slot.objects.filter(doctor_id=pk, active=True, booked=False, start__gt=timezone.now())[:12],
    })


@require_http_methods(["GET"])
def health(request):
    from django.db import connection, DatabaseError
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        Hospital.objects.exists()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})


def integer_id(value):
    try:
        n = int(value)
        if n <= 0:
            raise ValueError()
        return n
    except (ValueError, TypeError, OverflowError):
        raise Http404()


def paged(request, qs, size=30):
    return Paginator(qs, size).get_page(request.GET.get("page", 1))


def page(request, title, form=None, **context):
    return render(request, "care/form.html", {"title": title, "form": form, **context})


def visible_appointments(user):
    qs = Appointment.objects.select_related("patient", "slot__doctor", "payment")
    if user.role == "patient":
        return qs.filter(patient=user)
    if user.role == "doctor":
        return qs.filter(slot__doctor=user)
    if user.role in ("receptionist", "admin"):
        return qs
    return qs.none()


def clinical_appointment(user, pk):
    if user.role not in ("patient", "doctor"):
        raise Http404()
    return get_object_or_404(visible_appointments(user), pk=pk)


@require_http_methods(["GET", "POST"])
@rate_limit("login-ip", 60, 900)
def sign_in(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    error = ""
    role_choices = User.ROLES
    selected_role = request.POST.get("role", "") if request.method == "POST" else request.GET.get("role", "")
    if selected_role not in dict(role_choices):
        selected_role = ""
    context = {"selected_role": selected_role, "role_choices": role_choices,
               "next": safe_next(request), "email": ""}
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()[:254]
        if limited("login-account:" + email, 12, 900):
            return render(
                request,
                "care/login.html",
                dict(context, error="Too many attempts. Please wait 15 minutes."),
                status=429,
            )
        user = authenticate(
            request, username=email, password=request.POST.get("password", "")[:256]
        )
        context["email"] = email
        if user and selected_role and user.role != selected_role:
            error = "This account does not belong to the selected workspace. Choose your assigned role."
        elif user and user.role not in dict(role_choices):
            error = "This account has no supported workspace. Contact your hospital administrator."
        elif user:
            login(request, user)
            audit(user, "session.login")
            return redirect(safe_next(request))
        if not error:
            error = "Email or password is incorrect, or the account is inactive."
    return render(request, "care/login.html", dict(context, error=error))


@require_http_methods(["GET", "POST"])
@rate_limit("register", 12, 3600)
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                u = form.save()
        except IntegrityError:
            form.add_error("email", "This email is already registered.")
        else:
            login(request, u)
            audit(u, "account.registered")
            return redirect("profile" if u.role == "doctor" else "dashboard")
    return page(request, "Create account", form, public=True)


@require_POST
def sign_out(request):
    if request.user.is_authenticated:
        audit(request.user, "session.logout")
    logout(request)
    return redirect("login")


@require_POST
def language(request):
    value = request.POST.get("language", "en")
    if value in ("en", "mr", "hi"):
        request.session["language"] = value
    return redirect(safe_next(request, "dashboard" if request.user.is_authenticated else "home"))


@require_http_methods(["GET", "POST"])
@rate_limit("password-reset", 6, 3600)
def forgot(request):
    sent = False
    error = ""
    if request.method == "POST":
        if not settings.EMAIL_HOST or not settings.DEFAULT_FROM_EMAIL:
            error = "Email reset is not configured. Contact the hospital administrator."
        else:
            email = request.POST.get("email", "").strip().lower()[:254]
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                link = settings.PUBLIC_ORIGIN.rstrip("/") + reverse(
                    "reset", args=[uid, token]
                )
                try:
                    send_mail(
                        "Reset your MedNova password",
                        f"Use this link within 30 minutes to reset your password:\n{link}\nIf you did not request this, ignore this email.",
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                    )
                except Exception:
                    logger.error(
                        "Password reset email delivery failed; check email configuration."
                    )
            sent = True
    return render(request, "care/forgot.html", {"sent": sent, "error": error})


@require_http_methods(["GET", "POST"])
@rate_limit("reset-confirm", 30, 3600)
def reset(request, uid, token):
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (
        User.DoesNotExist,
        ValueError,
        TypeError,
        OverflowError,
        UnicodeDecodeError,
    ):
        user = None
    if not user or not default_token_generator.check_token(user, token):
        return page(
            request,
            "Reset link expired",
            notice="Request a new reset link from the login page.",
            public=True,
        )
    form = SetPasswordForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        audit(user, "password.reset")
        messages.success(request, "Password updated. Sign in with your new password.")
        return redirect("login")
    return page(request, "Set a new password", form, public=True)


@roles(pending=True)
def dashboard(request):
    from .models import WellnessEntry
    u = request.user
    if u.approval != "approved":
        return render(request, "care/pending.html")
    qs = visible_appointments(u)
    future = qs.filter(
        status__in=["pending", "confirmed"], slot__start__gte=timezone.now()
    ).order_by("slot__start")
    stats = []
    if u.role in ("patient", "doctor", "receptionist", "admin"):
        stats = [
            ("Upcoming appointments", future.count()),
            ("Awaiting confirmation", qs.filter(status="pending").count()),
            ("Completed consultations", qs.filter(status="completed").count()),
        ]
    if u.role == "pharmacist":
        stats = [
            (
                "Pending prescriptions",
                Prescription.objects.filter(dispensed=False).exclude(appointment__status="cancelled").count(),
            ),
            ("Medicine batches", Medicine.objects.count()),
            ("Low stock", Medicine.objects.filter(stock__lt=10).count()),
        ]
    return render(
        request,
        "care/dashboard.html",
        {
            "appointments": future[:5],
            "next_appointment": future.first(),
            "unread_notifications": Notification.objects.filter(recipient=u, read=False).count(),
            "latest_wellness": WellnessEntry.objects.filter(patient=u).first() if u.role == 'patient' else None,
            "stats": stats,
            "pending_staff": User.objects.filter(approval="pending")
            .exclude(role="patient")
            .count(),
            "low_stock": (
                Medicine.objects.filter(stock__lt=10)[:6]
                if u.role == "pharmacist"
                else []
            ),
        },
    )


@roles(pending=True)
@require_http_methods(["GET", "POST"])
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    doc = None
    docform = None
    if request.user.role == "doctor":
        doc = DoctorProfile.objects.filter(user=request.user).first()
        docform = DoctorForm(request.POST or None, instance=doc)
    if (
        request.method == "POST"
        and form.is_valid()
        and (docform is None or docform.is_valid())
    ):
        with transaction.atomic():
            form.save()
            if docform and docform.has_changed():
                p = docform.save(False)
                p.user = request.user
                p.save()
                User.objects.filter(pk=request.user.pk).update(
                    approval="pending", review_note=""
                )
            audit(request.user, "profile.updated")
        messages.success(
            request,
            (
                "Profile saved. Changes to doctor details require admin approval."
                if docform
                else "Profile saved."
            ),
        )
        return redirect("dashboard")
    return page(
        request,
        "My profile",
        form,
        extra_form=docform,
        notice=(
            "Doctor qualifications, registration and department are reviewed before the profile becomes public."
            if docform
            else ""
        ),
    )


@roles(pending=True)
@require_http_methods(["GET", "POST"])
def password(request):
    form = PasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        if user.must_change_password:
            user.must_change_password = False
            user.save(update_fields=["must_change_password"])
        update_session_auth_hash(request, user)
        audit(user, "password.changed")
        messages.success(
            request, "Password changed. Other sessions have been invalidated."
        )
        return redirect("profile")
    return page(request, "Change password", form)


@require_http_methods(["GET"])
def doctors(request):
    profiles = DoctorProfile.objects.select_related("user", "department").filter(
        user__role="doctor", user__approval="approved", user__is_active=True, department__active=True
    )
    from django.db.models import Min
    profiles = profiles.annotate(next_slot=Min('user__slots__start', filter=Q(user__slots__active=True, user__slots__booked=False, user__slots__start__gt=timezone.now(), user__slots__start__lt=timezone.now()+timedelta(days=90))))
    query = request.GET.get("q", "").strip()[:100]
    if query:
        profiles = profiles.filter(
            Q(user__name__icontains=query) | Q(department__name__icontains=query)
        )
    department = request.GET.get("department", "")
    if department:
        profiles = profiles.filter(department_id=integer_id(department))
    if request.GET.get("available") == "1":
        profiles = profiles.filter(user__slots__active=True, user__slots__booked=False, user__slots__start__gt=timezone.now(), user__slots__start__lt=timezone.now()+timedelta(days=90)).distinct()
    return render(
        request,
        "care/doctors.html",
        {
            "doctors": paged(request, profiles.order_by("user__name", "pk")),
            "pagination": paged(request, profiles.order_by("user__name", "pk")),
            "selected_department": department,
            "available_only": request.GET.get("available") == "1",
            "q": query,
            "departments": Department.objects.filter(active=True),
        },
    )


@roles("doctor")
@require_http_methods(["GET", "POST"])
def availability(request):
    form = AvailabilityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        start = timezone.make_aware(datetime.combine(d["date"], d["start"]))
        end = timezone.make_aware(datetime.combine(d["date"], d["end"]))
        created = 0
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            while start + timedelta(minutes=12) <= end:
                if (
                    start > timezone.now()
                    and not Slot.objects.filter(
                        doctor=request.user,
                        active=True,
                        start__gt=start - timedelta(minutes=12),
                        start__lt=start + timedelta(minutes=12),
                    ).exists()
                ):
                    slot, new = Slot.objects.get_or_create(
                        doctor=request.user, start=start,
                        defaults={"consultation_type": d.get("consultation_type") or "both"},
                    )
                    if not slot.booked:
                        slot.active = True
                        slot.save(update_fields=["active"])
                        created += 1
                start += timedelta(minutes=12)
            audit(request.user, "availability.added", str(created))
        messages.success(
            request,
            f"{created} appointment slots added. Each consultation is 12 minutes.",
        )
        return redirect("availability")
    period = request.GET.get("period", "week")
    try:
        day = datetime.strptime(request.GET.get("date", str(timezone.localdate())), "%Y-%m-%d").date()
    except ValueError:
        raise Http404()
    if period == "month":
        first = day.replace(day=1)
        last = (first + timedelta(days=32)).replace(day=1)
    elif period == "day":
        first, last = day, day + timedelta(days=1)
    else:
        period = "week"
        first = day - timedelta(days=day.weekday())
        last = first + timedelta(days=7)
    first_time = timezone.make_aware(datetime.combine(first, datetime.min.time()))
    last_time = timezone.make_aware(datetime.combine(last, datetime.min.time()))
    return render(
        request,
        "care/availability.html",
        {
            "form": form,
            "period": period,
            "schedule_date": day,
            "slots": Slot.objects.filter(
                doctor=request.user, start__gte=first_time, start__lt=last_time, active=True
            ),
        },
    )


@require_POST
@roles("doctor")
def remove_slot(request, pk):
    with transaction.atomic():
        User.objects.select_for_update().get(pk=request.user.pk)
        slot = get_object_or_404(
            Slot.objects.select_for_update(), pk=pk, doctor=request.user
        )
        if slot.booked:
            messages.error(request, "A booked slot cannot be removed.")
        else:
            slot.active = False
            slot.save(update_fields=["active"])
            audit(request.user, "availability.removed", slot.pk)
    return redirect("availability")


@roles("patient", "receptionist")
@require_http_methods(["GET", "POST"])
@rate_limit("booking", 40, 60)
def booking(request, doctor_id):
    doctor = get_object_or_404(
        User, pk=doctor_id, role="doctor", approval="approved", is_active=True
    )
    if not hasattr(doctor, "doctor_profile"):
        raise Http404()
    appt = None
    if request.GET.get("reschedule"):
        try:
            import uuid

            reschedule_id = uuid.UUID(request.GET["reschedule"])
        except (ValueError, AttributeError):
            raise Http404()
        appt = get_object_or_404(
            visible_appointments(request.user),
            pk=reschedule_id,
            status__in=["pending", "confirmed"],
        )
    form = BookingForm(
        request.POST or None,
        initial={"reason": appt.reason, "mode": appt.mode} if appt else {},
    )
    slots = Slot.objects.filter(
        doctor=doctor,
        active=True,
        booked=False,
        start__gt=timezone.now(),
        start__lt=timezone.now() + timedelta(days=90),
    )
    available_dates = sorted({timezone.localdate(start) for start in slots.values_list('start', flat=True)[:3000]})[:14]
    chosen_date = request.GET.get("date", "")
    if chosen_date:
        try:
            chosen_date = datetime.strptime(chosen_date, "%Y-%m-%d").date()
        except ValueError:
            raise Http404()
        day_start = timezone.make_aware(
            datetime.combine(chosen_date, datetime.min.time())
        )
        slots = slots.filter(
            start__gte=day_start, start__lt=day_start + timedelta(days=1)
        )
    slots = list(slots[:150])
    from itertools import groupby
    slot_days = [(day, list(items)) for day, items in groupby(slots, key=lambda item: timezone.localdate(item.start))]
    if request.method == "POST" and form.is_valid():
        patient = request.user
        if request.user.role == "receptionist":
            patient = get_object_or_404(
                User,
                pk=integer_id(request.POST.get("patient", "0")),
                role="patient",
                is_active=True,
            )
        if appt:
            patient = appt.patient
        try:
            slot = get_object_or_404(
                Slot, pk=integer_id(request.POST.get("slot", "0")), doctor=doctor
            )
            obj = book(
                patient,
                slot.pk,
                form.cleaned_data["mode"],
                form.cleaned_data["reason"],
                existing=appt,
            )
            if request.user != patient:
                audit(request.user, "reception.booking", obj.pk)
            messages.success(
                request, "Appointment requested. The care team will confirm it."
            )
            return redirect("appointment", pk=obj.pk)
        except BookingError as e:
            form.add_error(None, str(e))
    return render(
        request,
        "care/booking.html",
        {
            "form": form,
            "doctor": doctor,
            "slots": slots,
            "reschedule": appt,
            "chosen_date": chosen_date,
            "available_dates": available_dates,
            "slot_days": slot_days,
            "selected_slot": request.POST.get('slot', ''),
            "patients": (
                User.objects.filter(role="patient", is_active=True).order_by("name")[
                    :300
                ]
                if request.user.role == "receptionist"
                else []
            ),
        },
    )


@roles("patient", "doctor", "receptionist", "admin")
def appointments(request):
    qs = visible_appointments(request.user)
    query = request.GET.get("q", "").strip()[:100]
    if query:
        qs = qs.filter(Q(patient__name__icontains=query) | Q(patient__email__icontains=query) | Q(slot__doctor__name__icontains=query))
    status = request.GET.get("status", "")
    if status in ("pending", "confirmed", "completed", "cancelled"):
        qs = qs.filter(status=status)
    return render(
        request,
        "care/appointments.html",
        {
            "appointments": paged(request, qs),
            "pagination": paged(request, qs),
            "status": status,
            "q": query,
        },
    )


@roles("patient", "doctor", "receptionist", "admin")
def appointment(request, pk):
    appt = get_object_or_404(visible_appointments(request.user), pk=pk)
    clinical = request.user.role in ("patient", "doctor")
    rx = (
        Prescription.objects.filter(appointment=appt)
        .prefetch_related("items__medicine")
        .first()
        if clinical
        else None
    )
    return render(
        request,
        "care/appointment.html",
        {
            "appt": appt,
            "clinical": clinical,
            "rx": rx,
            "consultation_started": appt.slot.start <= timezone.now(),
            "can_check_in": appt.status == "confirmed" and appt.mode == "in_person" and timezone.localdate(appt.slot.start) == timezone.localdate(),
            "can_confirm": appt.status == "pending" and appt.slot.start > timezone.now(),
            "reports": appt.reports.all() if clinical else [],
            "can_change": appt.status in ("pending", "confirmed")
            and appt.slot.start > timezone.now(),
            "online_payments": bool(
                settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET
            ),
        },
    )


@require_POST
@roles("patient", "doctor", "receptionist", "admin")
def appointment_action(request, pk):
    appt = get_object_or_404(visible_appointments(request.user), pk=pk)
    action = request.POST.get("action", "")
    allowed = {
        "patient": ["cancelled"],
        "doctor": ["confirmed", "cancelled", "completed"],
        "receptionist": ["confirmed", "cancelled"],
        "admin": ["confirmed", "cancelled"],
    }
    if action not in allowed[request.user.role]:
        return HttpResponseForbidden()
    if request.user.role == "patient" and appt.slot.start <= timezone.now():
        return HttpResponseForbidden(
            "Contact the hospital to amend a past appointment."
        )
    try:
        change_status(appt, request.user, action)
        messages.success(request, "Appointment updated.")
    except BookingError as e:
        messages.error(request, str(e))
    return redirect("appointment", pk=pk)


@roles("patient", "doctor")
@require_http_methods(["GET", "POST"])
@rate_limit("upload", 20, 3600)
def upload(request, pk):
    appt = clinical_appointment(request.user, pk)
    if appt.status == "cancelled":
        return HttpResponseForbidden("This appointment is cancelled.")
    form = UploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        from botocore.exceptions import BotoCoreError, ClientError
        try:
            with transaction.atomic():
                Report.objects.create(
                    appointment=appt,
                    uploaded_by=request.user,
                    title=form.cleaned_data["title"],
                    extension=form.extension,
                    file=form.cleaned_data["file"],
                )
                audit(request.user, "report.uploaded", appt.pk)
        except (OSError, BotoCoreError, ClientError):
            logger.error("Private report storage is unavailable.")
            form.add_error(None, "Report storage is unavailable. Your upload was not saved. Please try again later.")
        else:
            messages.success(request, "Report uploaded securely.")
            return redirect("appointment", pk=pk)
    return page(request, "Upload medical report", form, multipart=True)


@roles("patient", "doctor")
@rate_limit("download", 60, 60)
def download(request, pk):
    report = get_object_or_404(Report, pk=pk)
    clinical_appointment(request.user, report.appointment_id)
    audit(request.user, "report.downloaded", pk)
    try:
        if settings.PRIVATE_STORAGE_BACKEND == "s3":
            # Authorization precedes the short-lived URL. Large file bodies do
            # not pass through the function's response payload limit.
            from django.http import HttpResponseRedirect
            return HttpResponseRedirect(report.file.storage.url(
                report.file.name,
                parameters={"ResponseContentDisposition": 'attachment; filename="medical-report' + report.extension + '"'},
                expire=60,
            ))
        return FileResponse(
            report.file.open("rb"),
            as_attachment=True,
            filename="medical-report" + report.extension,
            content_type="application/octet-stream",
        )
    except FileNotFoundError:
        raise Http404("Report file is unavailable. Contact the hospital.")


@roles("doctor")
@require_http_methods(["GET", "POST"])
def prescribe(request, pk):
    appt = clinical_appointment(request.user, pk)
    if (
        appt.status not in ("confirmed", "completed")
        or appt.slot.start > timezone.now()
    ):
        return HttpResponseForbidden(
            "A prescription requires a consultation that has started."
        )
    error = ""
    if request.method == "POST":
        instructions = request.POST.get("instructions", "").strip()
        lines = []
        try:
            if not instructions or len(instructions) > 3000:
                raise ValueError("Enter instructions, up to 3000 characters.")
            for i in range(1, 6):
                mid = request.POST.get(f"medicine_{i}", "")
                if not mid:
                    continue
                med = Medicine.objects.get(pk=mid, expiry__gte=timezone.localdate())
                dose = request.POST.get(f"dose_{i}", "").strip()
                quantity = int(request.POST.get(f"quantity_{i}", "0"))
                if not dose or len(dose) > 200 or not 1 <= quantity <= 1000:
                    raise ValueError("Provide a dose and quantity for every medicine.")
                if any(m.pk == med.pk for m, _, _ in lines):
                    raise ValueError("Each medicine batch may appear only once.")
                lines.append((med, dose, quantity))
            with transaction.atomic():
                appt = Appointment.objects.select_for_update().get(pk=pk)
                if appt.status not in ("confirmed", "completed") or appt.slot.start > timezone.now():
                    raise ValueError("This consultation is no longer eligible for prescribing.")
                if Prescription.objects.filter(appointment=appt).exists():
                    raise ValueError(
                        "A prescription has already been issued. Contact the hospital for a correction."
                    )
                rx = Prescription.objects.create(
                    appointment=appt, instructions=instructions
                )
                for med, dose, quantity in lines:
                    PrescriptionItem.objects.create(
                        prescription=rx, medicine=med, dose=dose, quantity=quantity
                    )
                audit(request.user, "prescription.issued", rx.pk)
            return redirect("appointment", pk=pk)
        except (ValueError, Medicine.DoesNotExist) as e:
            error = (
                str(e) if isinstance(e, ValueError) else "Choose an available medicine."
            )
    return render(
        request,
        "care/prescribe.html",
        {
            "appt": appt,
            "error": error,
            "medicines": Medicine.objects.filter(
                expiry__gte=timezone.localdate()
            ).order_by("name"),
            "rows": range(1, 6),
        },
    )


@roles("patient", "doctor", "pharmacist")
def prescriptions(request):
    qs = Prescription.objects.select_related(
        "appointment__patient", "appointment__slot__doctor"
    ).prefetch_related("items__medicine")
    if request.user.role == "patient":
        qs = qs.filter(appointment__patient=request.user)
    if request.user.role == "doctor":
        qs = qs.filter(appointment__slot__doctor=request.user)
    return render(
        request,
        "care/prescriptions.html",
        {
            "prescriptions": paged(request, qs.order_by("-created")),
            "pagination": paged(request, qs.order_by("-created")),
        },
    )


@require_POST
@roles("pharmacist")
def dispense_rx(request, pk):
    rx = get_object_or_404(Prescription, pk=pk)
    try:
        dispense(rx, request.user)
        messages.success(request, "Prescription dispensed and stock updated.")
    except BookingError as e:
        messages.error(request, str(e))
    return redirect("prescriptions")


@roles("pharmacist", "admin")
@require_http_methods(["GET", "POST"])
def inventory(request):
    form = MedicineForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        med = form.save()
        from .models import StockMovement
        StockMovement.objects.create(medicine=med, actor=request.user, quantity=med.stock, balance=med.stock, reason="Opening stock")
        audit(request.user, "inventory.created", med.pk)
        messages.success(request, "Medicine batch added.")
        return redirect("inventory")
    return render(
        request,
        "care/inventory.html",
        {
            "form": form,
            "low_stock_count": Medicine.objects.filter(stock__lte=10).count(),
            "expired_count": Medicine.objects.filter(expiry__lt=timezone.localdate()).count(),
            "expiring_count": Medicine.objects.filter(expiry__gte=timezone.localdate(), expiry__lte=timezone.localdate()+timedelta(days=30)).count(),
            "medicines": paged(request, Medicine.objects.order_by("name", "pk")),
            "pagination": paged(request, Medicine.objects.order_by("name", "pk")),
        },
    )


@require_POST
@roles("pharmacist", "admin")
def stock(request, pk):
    try:
        change = int(request.POST.get("change", "0"))
        reason = request.POST.get("reason", "").strip()
        if (
            not reason
            or len(reason) > 120
            or not -100000 <= change <= 100000
            or change == 0
        ):
            raise ValueError()
        with transaction.atomic():
            med = get_object_or_404(Medicine.objects.select_for_update(), pk=pk)
            if med.stock + change < 0:
                raise ValueError()
            med.stock += change
            med.save(update_fields=["stock"])
            from .models import StockMovement
            StockMovement.objects.create(medicine=med, actor=request.user, quantity=change, balance=med.stock, reason=reason)
            audit(request.user, "inventory.adjusted", f"{pk}: {change}: {reason}")
        messages.success(request, "Stock updated.")
    except ValueError:
        messages.error(
            request,
            "Enter a valid adjustment and reason. Stock cannot become negative.",
        )
    return redirect("inventory")


@roles("admin")
@require_http_methods(["GET", "POST"])
def staff(request):
    if request.method == "POST":
        with transaction.atomic():
            u = get_object_or_404(
                User.objects.select_for_update(),
                pk=integer_id(request.POST.get("user", "0")),
            )
            if u.role in ("admin", "patient"):
                return HttpResponseForbidden()
            action = request.POST.get("action")
            if action not in ("approved", "denied"):
                return HttpResponseForbidden()
            if (
                action == "approved"
                and u.role == "doctor"
                and not DoctorProfile.objects.filter(
                    user=u, department__isnull=False
                ).exists()
            ):
                messages.error(
                    request,
                    "The doctor must complete their professional profile first.",
                )
            else:
                u.approval = action
                u.review_note = request.POST.get("note", "").strip()[:300]
                u.save(update_fields=["approval", "review_note"])
                audit(request.user, "staff." + action, u.pk)
                messages.success(request, "Staff review saved.")
        return redirect("staff")
    return render(
        request,
        "care/staff.html",
        {
            "staff": User.objects.exclude(role__in=["patient", "admin"])
            .select_related("doctor_profile__department")
            .order_by("approval", "name")[:300]
        },
    )


@roles("admin")
@require_http_methods(["GET", "POST"])
def departments(request):
    form = DepartmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.save()
        audit(request.user, "department.created", d.pk)
        return redirect("departments")
    return page(
        request, "Departments", form, records=Department.objects.order_by("name")
    )


@roles("admin")
@require_http_methods(["GET", "POST"])
def hospital_settings(request):
    obj = Hospital.objects.first() or Hospital()
    form = HospitalForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        audit(request.user, "hospital.updated")
        messages.success(request, "Hospital details saved.")
        return redirect("settings")
    return page(
        request,
        "Hospital settings",
        form,
        notice="Use verified hospital details. Contact buttons appear once phone numbers are saved.",
    )


@roles("admin")
def audit_log(request):
    return render(
        request,
        "care/audit.html",
        {
            "events": paged(request, AuditEvent.objects.select_related("actor")),
            "pagination": paged(request, AuditEvent.objects.select_related("actor")),
        },
    )


@roles("receptionist", "admin")
@require_http_methods(["GET", "POST"])
def payment_record(request, pk):
    appt = get_object_or_404(visible_appointments(request.user), pk=pk)
    if request.method == "POST":
        reference = request.POST.get("reference", "").strip()[:120]
        method = request.POST.get("method", "")
        if reference and method in ("cash", "bank", "refund"):
            with transaction.atomic():
                appt = Appointment.objects.select_for_update().get(pk=pk)
                p = Payment.objects.select_for_update().get(appointment=appt)
                if (
                    p.status == "unpaid"
                    and appt.status != "cancelled"
                    and method != "refund"
                ):
                    p.status = "paid"
                    p.method = method
                elif p.status == "refund_due" and method == "refund":
                    p.status = "refunded"
                else:
                    messages.error(request, "This payment cannot be changed.")
                    return redirect("appointment", pk=pk)
                p.reference = reference
                p.received_by = request.user
                p.save()
                audit(request.user, "payment.recorded", p.pk)
            messages.success(request, "Payment record saved.")
            return redirect("appointment", pk=pk)
        messages.error(request, "Enter a receipt or refund reference.")
    return render(request, "care/payment_record.html", {"appt": appt})


@roles("patient")
@require_http_methods(["GET", "POST"])
@rate_limit("payment-create", 10, 600)
def pay(request, pk):
    appt = get_object_or_404(
        visible_appointments(request.user), pk=pk, status__in=["pending", "confirmed"]
    )
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return page(
            request,
            "Online payments unavailable",
            notice="Please contact the hospital to arrange payment.",
        )
    error = ""
    if request.method == "POST":
        try:
            with transaction.atomic():
                appt = Appointment.objects.select_for_update().get(pk=pk)
                if appt.status not in ("pending", "confirmed"):
                    return redirect("appointment", pk=pk)
                payment = Payment.objects.select_for_update().get(appointment=appt)
                if payment.status != "unpaid":
                    return redirect("appointment", pk=pk)
                if not payment.order_id:
                    r = requests.post(
                        "https://api.razorpay.com/v1/orders",
                        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
                        json={
                            "amount": int(payment.amount * 100),
                            "currency": "INR",
                            "receipt": appt.short_id,
                        },
                        timeout=12,
                    )
                    r.raise_for_status()
                    data = r.json()
                    payment.order_id = data["id"]
                    payment.save(update_fields=["order_id"])
            return render(
                request,
                "care/pay.html",
                {
                    "appt": appt,
                    "payment_data": {
                        "key": settings.RAZORPAY_KEY_ID,
                        "order_id": payment.order_id,
                        "amount": int(payment.amount * 100),
                        "currency": "INR",
                        "name": "MedNova",
                        "verify_url": reverse("payment_verify", args=[pk]),
                    },
                },
            )
        except (requests.RequestException, KeyError, ValueError):
            error = "Payment service is unavailable. Please try again later."
    return render(request, "care/pay.html", {"appt": appt, "error": error})


def verify_provider_payment(payment, payment_id):
    r = requests.get(
        "https://api.razorpay.com/v1/payments/" + payment_id,
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
        timeout=12,
    )
    r.raise_for_status()
    data = r.json()
    if (
        data.get("order_id") != payment.order_id
        or data.get("amount") != int(payment.amount * 100)
        or data.get("currency") != "INR"
        or data.get("status") != "captured"
    ):
        return False
    payment.status = (
        "refund_due" if payment.appointment.status == "cancelled" else "paid"
    )
    payment.method = "razorpay"
    payment.provider_id = payment_id
    payment.save()
    return True


@require_POST
@roles("patient")
@rate_limit("payment-verify", 20, 600)
def payment_verify(request, pk):
    appt = get_object_or_404(visible_appointments(request.user), pk=pk)
    try:
        data = json.loads(request.body)
        payment_id = data.get("razorpay_payment_id", "")
        if not re.fullmatch(r"pay_[A-Za-z0-9]{1,80}", payment_id):
            raise ValueError()
        with transaction.atomic():
            payment = Payment.objects.select_for_update().get(appointment=appt)
            signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode(),
                f"{payment.order_id}|{payment_id}".encode(),
                hashlib.sha256,
            ).hexdigest()
            if not payment.order_id or not hmac.compare_digest(
                signature, str(data.get("razorpay_signature", ""))
            ):
                raise ValueError()
            if payment.status == "paid":
                return JsonResponse({"ok": True})
            if not verify_provider_payment(payment, payment_id):
                raise ValueError()
            audit(request.user, "payment.verified", payment.pk)
        return JsonResponse({"ok": True})
    except (ValueError, TypeError, AttributeError, requests.RequestException):
        return JsonResponse(
            {
                "error": "Payment is not confirmed yet. Contact the hospital if money was debited."
            },
            status=400,
        )


@csrf_exempt
@require_POST
@rate_limit("payment-webhook", 120, 60)
def webhook(request):
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        return HttpResponse(status=503)
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(), request.body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(
        expected, request.headers.get("X-Razorpay-Signature", "")
    ):
        return HttpResponse(status=403)
    try:
        data = json.loads(request.body)
        if data.get("event") != "payment.captured":
            return HttpResponse(status=200)
        entity = data["payload"]["payment"]["entity"]
        with transaction.atomic():
            p = (
                Payment.objects.select_for_update()
                .select_related("appointment")
                .filter(order_id=entity["order_id"])
                .first()
            )
            if (
                p
                and p.status == "unpaid"
                and entity["amount"] == int(p.amount * 100)
                and entity["currency"] == "INR"
                and entity["status"] == "captured"
            ):
                p.status = (
                    "refund_due" if p.appointment.status == "cancelled" else "paid"
                )
                p.method = "razorpay"
                p.provider_id = entity["id"]
                p.save()
                audit(None, "payment.webhook", p.pk)
        return HttpResponse(status=200)
    except (KeyError, ValueError, TypeError, AttributeError):
        return HttpResponse(status=400)


def call_access(request, pk):
    appt = clinical_appointment(request.user, pk)
    if appt.mode != "video" or appt.status != "confirmed":
        raise Http404()
    now = timezone.now()
    if (
        not appt.slot.start - timedelta(minutes=10)
        <= now
        <= appt.slot.start + timedelta(minutes=30)
    ):
        raise Http404(
            "The call opens 10 minutes before your appointment and closes 30 minutes after its start."
        )
    return appt


@roles("patient", "doctor")
def video(request, pk):
    appt = call_access(request, pk)
    config = {"iceServers": [], "iceTransportPolicy": "all"}
    if settings.TURN_URL and settings.TURN_SECRET:
        username = f"{int(timezone.now().timestamp())+3600}:{request.user.pk}"
        credential = base64.b64encode(
            hmac.new(
                settings.TURN_SECRET.encode(), username.encode(), hashlib.sha1
            ).digest()
        ).decode()
        config = {
            "iceServers": [
                {
                    "urls": settings.TURN_URL.split(","),
                    "username": username,
                    "credential": credential,
                }
            ],
            "iceTransportPolicy": "relay",
        }
    elif not settings.LOCAL and not settings.TESTING:
        return page(
            request,
            "Video consultations unavailable",
            notice="The hospital must connect a secure video relay before online calls can start.",
        )
    audit(request.user, "video.opened", pk)
    return render(
        request,
        "care/video.html",
        {
            "appt": appt,
            "call_data": {
                "config": config,
                "signal_url": reverse("signal", args=[pk]),
                "is_doctor": request.user.role == "doctor",
            },
            "local_only": not bool(settings.TURN_URL),
        },
    )


@roles("patient", "doctor")
@require_http_methods(["GET", "POST"])
@rate_limit("video-signals", 180, 60)
def signal(request, pk):
    appt = call_access(request, pk)
    if request.method == "POST":
        if len(request.body) > 30000:
            return JsonResponse({"error": "Payload too large"}, status=413)
        Signal.objects.filter(appointment=appt, created__lt=timezone.now() - timedelta(minutes=15)).delete()
        try:
            data = json.loads(request.body)
            kind = data["kind"]
            payload = data.get("payload", {})
            if kind not in (
                "offer",
                "answer",
                "ice",
                "leave",
                "ready",
            ) or not isinstance(payload, dict):
                raise ValueError()
            if kind == "offer" and request.user.role != "doctor":
                raise ValueError()
            if kind == "answer" and request.user.role != "patient":
                raise ValueError()
            Signal.objects.create(
                appointment=appt, sender=request.user, kind=kind, payload=payload
            )
        except (ValueError, KeyError, TypeError):
            return JsonResponse({"error": "Invalid signal"}, status=400)
        return JsonResponse({"ok": True})
    try:
        after = max(0, int(request.GET.get("after", "0")))
    except ValueError:
        return JsonResponse({"error": "Invalid cursor"}, status=400)
    qs = (
        Signal.objects.filter(
            appointment=appt,
            id__gt=after,
            created__gte=timezone.now() - timedelta(minutes=2),
        )
        .exclude(sender=request.user)
        .order_by("id")[:100]
    )
    return JsonResponse({"signals": list(qs.values("id", "kind", "payload"))})


def legal(request, kind):
    if kind not in ("privacy", "terms"):
        raise Http404()
    return render(request, "care/legal.html", {"kind": kind})


def contact(request):
    return render(request, "care/contact.html")


@roles()
@require_http_methods(["GET", "POST"])
def notifications(request):
    if request.method == "POST":
        request.user.notifications.filter(read=False).update(read=True)
        return redirect("notifications")
    pagination = paged(request, request.user.notifications.select_related("appointment"))
    return render(request, "care/notifications.html", {"notifications": pagination, "pagination": pagination})


@roles("receptionist", "admin")
@require_POST
def check_in(request, pk):
    with transaction.atomic():
        appt = get_object_or_404(Appointment.objects.select_for_update().select_related("slot"), pk=pk)
        if appt.status != "confirmed" or timezone.localdate(appt.slot.start) != timezone.localdate() or appt.mode != "in_person":
            messages.error(request, "Check-in requires a confirmed in-person appointment today.")
        elif not appt.checked_in_at:
            appt.checked_in_at = timezone.now()
            appt.save(update_fields=["checked_in_at"])
            audit(request.user, "appointment.checked_in", appt.pk)
            messages.success(request, "Patient checked in.")
        if appt.checked_in_at and appt.status == 'confirmed' and appt.mode == 'in_person' and timezone.localdate(appt.slot.start) == timezone.localdate():
            from .product import enqueue
            entry = enqueue(appt)
            messages.success(request, f"Queue token: {entry.number}")
    return redirect("appointment", pk=pk)


def error404(request, exception):
    return render(
        request,
        "care/error.html",
        {
            "code": 404,
            "explanation": "This page is unavailable or you do not have access.",
        },
        status=404,
    )


def error403(request, exception=None):
    return render(
        request,
        "care/error.html",
        {
            "code": 403,
            "explanation": "This request is not permitted. Sign in again and retry.",
        },
        status=403,
    )


def csrf_failure(request, reason=""):
    # Record only the category; never log the request, tokens or submitted fields.
    category = "cookie missing" if "cookie not set" in reason else "origin" if "Origin" in reason or "Referer" in reason else "token"
    logger.warning("Request rejected by CSRF protection (%s).", category)
    return error403(request)


def error500(request):
    # Keep the fallback independent of templates, sessions and database access.
    return HttpResponse(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>MedNova | Service unavailable</title><body>"
        "<h1>MedNova is temporarily unavailable</h1>"
        "<p>Please try again later or contact your hospital.</p></body></html>",
        status=500,
    )


@roles("receptionist", "admin")
@require_http_methods(["GET", "POST"])
def patients(request):
    form = ReceptionPatientForm(request.POST or None, initial={"role": "patient"})
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                patient = form.save()
                audit(request.user, "reception.patient_registered", patient.pk)
        except IntegrityError:
            form.add_error("email", "This email is already registered.")
        else:
            messages.success(request, "Patient registered. Share account details securely with the patient.")
            return redirect("patients")
    query = request.GET.get("q", "").strip()[:100]
    records = User.objects.filter(role="patient").order_by("name", "pk")
    if query:
        records = records.filter(Q(name__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query))
    pagination = paged(request, records)
    return render(request, "care/patients.html", {"form": form, "patients": pagination, "pagination": pagination, "q": query})


@roles("admin")
@require_http_methods(["GET", "POST"])
def users(request):
    if request.method == "POST":
        with transaction.atomic():
            target = get_object_or_404(User.objects.select_for_update(), pk=integer_id(request.POST.get("user")))
            if target.role == "admin" or target.is_superuser or target.pk == request.user.pk:
                return HttpResponseForbidden("Administrator access requires the controlled operator process.")
            action = request.POST.get("action")
            if action not in ("activate", "deactivate"):
                return HttpResponseForbidden()
            target.is_active = action == "activate"
            target.save(update_fields=["is_active"])
            audit(request.user, "account." + action, target.pk)
        return redirect("users")
    query = request.GET.get("q", "").strip()[:100]
    records = User.objects.order_by("name", "pk")
    if query:
        records = records.filter(Q(name__icontains=query) | Q(email__icontains=query))
    pagination = paged(request, records)
    return render(request, "care/users.html", {"users": pagination, "pagination": pagination, "q": query})


@roles("admin")
@require_http_methods(["GET", "POST"])
def department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)
    form = DepartmentForm(request.POST or None, instance=department)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            form.save()
            audit(request.user, "department.updated", pk)
        return redirect("departments")
    return page(request, "Edit department", form)


@roles("doctor")
@require_http_methods(["GET", "POST"])
def edit_slot(request, pk):
    with transaction.atomic():
        User.objects.select_for_update().get(pk=request.user.pk)
        slot = get_object_or_404(Slot.objects.select_for_update(), pk=pk, doctor=request.user, active=True)
        if slot.booked or slot.start <= timezone.now() or slot.appointments.exclude(status="cancelled").exists():
            return HttpResponseForbidden("Only unused future slots may be edited.")
        form = SlotEditForm(request.POST or None, instance=slot)
        if request.method == "POST" and form.is_valid():
            start = form.cleaned_data["start"]
            if Slot.objects.filter(doctor=request.user, active=True, start__gt=start-timedelta(minutes=12), start__lt=start+timedelta(minutes=12)).exclude(pk=pk).exists():
                form.add_error("start", "This time overlaps another slot.")
            else:
                try:
                    with transaction.atomic():
                        form.save()
                        audit(request.user, "availability.edited", pk)
                except IntegrityError:
                    form.add_error("start", "A slot already exists at this time. Choose another time.")
                else:
                    return redirect("availability")
    return page(request, "Edit availability", form)


@roles("admin")
def operational_report(request):
    rows = Appointment.objects.values("status").annotate(total=Count("pk")).order_by("status")
    payments = Payment.objects.values("status").annotate(total=Count("pk")).order_by("status")
    return render(request, "care/operations.html", {"appointment_totals": rows, "payment_totals": payments})


@roles("patient", "receptionist", "admin")
def receipt(request, pk):
    appt = get_object_or_404(visible_appointments(request.user), pk=pk)
    return render(request, "care/receipt.html", {"appt": appt})


@require_http_methods(["GET"])
def cleanup(request):
    if not settings.CRON_SECRET or not hmac.compare_digest(request.headers.get("Authorization", ""), "Bearer " + settings.CRON_SECRET):
        return HttpResponse(status=403)
    from django.core.management import call_command
    from io import StringIO
    call_command("cleanup_transient", stdout=StringIO())
    call_command("process_notifications", stdout=StringIO())
    return JsonResponse({"ok": True})
