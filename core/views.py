from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
from django.utils import timezone
import re
from django.db.models import Sum, F, Q
from django.urls import reverse
from datetime import datetime, timedelta
from .models import CustomUser, HelpRequest, VolunteerApplication, VolunteerTask, ContentPage, NewsPost

_KZ_MOBILE_OPERATOR_CODES = {
    '700', '701', '702', '705', '706', '707', '708',
    '747',
    '771',
    '775', '776', '777', '778',
}

_NAME_RE = re.compile(r"^[A-Za-zА-Яа-яӘәҒғҚқҢңӨөҰұҮүҺһІіЁё\- ]{2,60}$")

def _normalize_phone_number(value: str) -> str:
    digits = re.sub(r'\D+', '', (value or '').strip())
    if not digits:
        return ''
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    if len(digits) == 10:
        digits = '7' + digits
    if digits.startswith('7'):
        return f"+{digits}"
    return digits

def _is_valid_kz_mobile(phone_number: str) -> bool:
    if not phone_number:
        return False
    if not phone_number.startswith('+'):
        return False
    digits = re.sub(r'\D+', '', phone_number)
    if len(digits) != 11 or not digits.startswith('7'):
        return False
    operator_code = digits[1:4]
    return operator_code in _KZ_MOBILE_OPERATOR_CODES

@require_POST
def set_ui_language(request):
    lang = (request.POST.get('lang') or '').strip().lower()
    if lang not in {'kk', 'ru'}:
        lang = 'kk'
    next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('index')
    response = redirect(next_url)
    response.set_cookie('ui_lang', lang, max_age=60 * 60 * 24 * 365, samesite='Lax')
    return response

def index(request):
    """
    Renders the homepage.
    """
    latest_news = NewsPost.objects.filter(is_published=True).order_by('-published_at')[:3]
    return render(request, 'index.html', {'latest_news': latest_news})

def public_news(request):
    q = (request.GET.get('q') or '').strip()
    posts = NewsPost.objects.filter(is_published=True)
    if q:
        posts = posts.filter(
            Q(title_kk__icontains=q) | 
            Q(title_ru__icontains=q) | 
            Q(body_kk__icontains=q) | 
            Q(body_ru__icontains=q)
        )
    posts = posts.order_by('-published_at')
    return render(request, 'client_news.html', {'news_posts': posts, 'search_query': q})

def public_about(request):
    page = ContentPage.objects.filter(slug='about', is_published=True).first()
    return render(request, 'client_about.html', {'page': page})

def public_help(request):
    if request.user.is_authenticated and getattr(request.user, 'role', None) == 'Client':
        return redirect('/client-dashboard/?tab=askHelpSection')
    page = ContentPage.objects.filter(slug='help', is_published=True).first()
    return render(request, 'client_help.html', {'page': page})

def public_become_volunteer(request):
    if request.user.is_authenticated and getattr(request.user, 'role', None) == 'Client':
        return redirect('/client-dashboard/?tab=becomeVolunteerSection')
    page = ContentPage.objects.filter(slug='become-volunteer', is_published=True).first()
    return render(request, 'client_volunteer.html', {'page': page})

def sign_view(request):
    """
    Renders the sign-in/registration page and handles basic authentication logic.
    """
    if request.method == 'POST':
        form_type = request.POST.get('form_type')

        if form_type == 'register':
            last_name = (request.POST.get('last_name') or '').strip()
            first_name = (request.POST.get('first_name') or '').strip()
            middle_name = (request.POST.get('middle_name') or '').strip()
            phone_number = _normalize_phone_number(request.POST.get('phone_number') or '')
            password = request.POST.get('password') or ''
            password_confirm = request.POST.get('password_confirm') or ''
            if not last_name or not first_name:
                messages.error(request, _("Тегі мен аты міндетті."))
                return render(request, 'sign.html')
            if not _NAME_RE.fullmatch(last_name) or not _NAME_RE.fullmatch(first_name):
                messages.error(request, _("Тегі/аты тек әріптерден тұруы керек."))
                return render(request, 'sign.html')
            if middle_name and not _NAME_RE.fullmatch(middle_name):
                messages.error(request, _("Әкесінің аты тек әріптерден тұруы керек."))
                return render(request, 'sign.html')
            if not phone_number or not _is_valid_kz_mobile(phone_number):
                messages.error(request, _("Тек Қазақстанның ұялы нөмірі қабылданады. Мысалы: +77471234567"))
                return render(request, 'sign.html')

            if password != password_confirm:
                messages.error(request, _("Құпиясөздер сәйкес келмейді."))
                return render(request, 'sign.html')
            if len(password) < 8:
                messages.error(request, _("Құпиясөз кемінде 8 таңба болуы керек."))
                return render(request, 'sign.html')

            if CustomUser.objects.filter(username=phone_number).exists() or CustomUser.objects.filter(phone_number=phone_number).exists():
                messages.error(request, _("Бұл телефон нөмірімен пайдаланушы бұрыннан бар."))
                return render(request, 'sign.html')

            try:
                user = CustomUser.objects.create(
                    username=phone_number,
                    phone_number=phone_number,
                    first_name=first_name,
                    last_name=last_name,
                    middle_name=middle_name,
                    role='Client'
                )
                user.set_password(password)
                user.save()

                login(request, user)
                return redirect('client_dashboard')

            except Exception as e:
                messages.error(request, _("Тіркелу кезінде қате: %(error)s") % {'error': str(e)})
                return render(request, 'sign.html')

        elif form_type == 'login':
            raw_identifier = (request.POST.get('phone_number') or '').strip()
            password = request.POST.get('password') or ''

            phone_number = _normalize_phone_number(raw_identifier)
            user = None
            
            if _is_valid_kz_mobile(phone_number):
                user = authenticate(request, username=phone_number, password=password)
                if user is None:
                    user_obj = CustomUser.objects.filter(phone_number=phone_number).first()
                    if user_obj and user_obj.username != phone_number:
                        CustomUser.objects.filter(pk=user_obj.pk).update(username=phone_number, phone_number=phone_number)
                        user = authenticate(request, username=phone_number, password=password)
                if user is None:
                    user = authenticate(request, username=raw_identifier, password=password)
            else:
                user = authenticate(request, username=raw_identifier, password=password)

            if user is not None:
                login(request, user)
                
                if user.is_superuser or user.role == 'Admin':
                    return redirect('admin_dashboard')
                if user.role == 'Volunteer':
                    return redirect('volunteer_dashboard')
                elif user.role == 'Client':
                    return redirect('client_dashboard')
                else:
                    return redirect('index')
            else:
                messages.error(request, _("Телефон нөмірі немесе құпиясөз қате."))
                return render(request, 'sign.html')

    return render(request, 'sign.html')

def logout_view(request):
    logout(request)
    return redirect('index')

def _require_role(request, allowed_roles):
    if request.user.is_superuser:
        return None
    if request.user.role not in allowed_roles:
        return redirect('index')
    return None

@login_required
def volunteer_dashboard(request):
    guard = _require_role(request, {'Volunteer'})
    if guard:
        return guard
    assigned_tasks_qs = VolunteerTask.objects.filter(assigned_volunteer=request.user)
    completed_tasks_qs = assigned_tasks_qs.filter(status='Completed')
    completed_hours = completed_tasks_qs.aggregate(total=Sum('duration')).get('total') or 0
    context = {
        'upcoming_tasks': assigned_tasks_qs.exclude(status='Completed').order_by('date', 'time')[:5],
        'recent_completed_tasks': completed_tasks_qs.order_by('-date', '-time')[:5],
        'available_count': VolunteerTask.objects.filter(assigned_volunteer__isnull=True).count(),
        'completed_count': completed_tasks_qs.count(),
        'active_count': assigned_tasks_qs.exclude(status='Completed').count(),
        'completed_hours': completed_hours,
    }
    return render(request, 'dashboard.html', context)

@login_required
def volunteer_tasks(request):
    guard = _require_role(request, {'Volunteer'})
    if guard:
        return guard
    tasks = VolunteerTask.objects.filter(assigned_volunteer=request.user).order_by('date', 'time')
    context = {
        'tasks': tasks,
        'scheduled_tasks': tasks.filter(status='Scheduled'),
        'in_progress_tasks': tasks.filter(status='In-Progress'),
        'completed_tasks': tasks.filter(status='Completed'),
    }
    return render(request, 'mytasks.html', context)

@login_required
def volunteer_opportunities(request):
    guard = _require_role(request, {'Volunteer'})
    if guard:
        return guard
    context = {
        'opportunities': VolunteerTask.objects.filter(assigned_volunteer__isnull=True).exclude(status='Completed').order_by('date', 'time'),
    }
    return render(request, 'opportunities.html', context)

@login_required
def volunteer_applications(request):
    guard = _require_role(request, {'Volunteer'})
    if guard:
        return guard
    # Show the volunteer's own application(s) to become a volunteer
    applications = VolunteerApplication.objects.filter(user=request.user).order_by('-submitted_at')
    latest_application = applications.first()
    # Also show their assigned tasks summary
    tasks = VolunteerTask.objects.filter(assigned_volunteer=request.user).order_by('-date', '-time')
    context = {
        'applications': applications,
        'latest_application': latest_application,
        'tasks': tasks,
        'pending_tasks': tasks.exclude(status='Completed'),
        'completed_tasks': tasks.filter(status='Completed'),
    }
    return render(request, 'myapplications.html', context)

@login_required
@require_POST
def volunteer_claim_task(request, task_id):
    guard = _require_role(request, {'Volunteer'})
    if guard:
        return guard
    task = get_object_or_404(VolunteerTask, pk=task_id)
    if task.assigned_volunteer_id is None:
        task.assigned_volunteer = request.user
        task.status = 'In-Progress'
        task.save(update_fields=['assigned_volunteer', 'status'])
        if task.help_request_id:
            HelpRequest.objects.filter(pk=task.help_request_id).update(status='Process')
        messages.success(request, _("Тапсырма сізге тағайындалды."))
    else:
        messages.error(request, _("Бұл тапсырманы басқа ерікті алып қойған."))
    return redirect('volunteer_opportunities')

@login_required
@require_POST
def volunteer_complete_task(request, task_id):
    guard = _require_role(request, {'Volunteer'})
    if guard:
        return guard
    task = get_object_or_404(VolunteerTask, pk=task_id, assigned_volunteer=request.user)
    if task.status != 'Completed':
        task.status = 'Completed'
        task.save(update_fields=['status'])
        if task.help_request_id:
            HelpRequest.objects.filter(pk=task.help_request_id).update(status='Completed')
        CustomUser.objects.filter(pk=request.user.pk).update(total_hours=F('total_hours') + (task.duration or 0))
        messages.success(request, _("Тапсырма аяқталды деп белгіленді."))
    return redirect('volunteer_tasks')

@login_required
def edit_volunteer_profile(request):
    guard = _require_role(request, {'Volunteer', 'Admin', 'Client'})
    if guard:
        return guard
        
    if request.method == 'POST':
        first_name = (request.POST.get('first_name') or '').strip()
        last_name = (request.POST.get('last_name') or '').strip()
        middle_name = (request.POST.get('middle_name') or '').strip()
        phone_number = (request.POST.get('phone_number') or '').strip()
        city = (request.POST.get('city') or '').strip()
        
        is_kk = request.COOKIES.get('ui_lang', 'kk') == 'kk'
        
        if not first_name or not last_name:
            messages.error(request, "Аты мен тегі міндетті." if is_kk else "Имя и фамилия обязательны.")
            return redirect(request.META.get('HTTP_REFERER', 'volunteer_dashboard'))
            
        if not _NAME_RE.fullmatch(first_name) or not _NAME_RE.fullmatch(last_name):
            messages.error(request, "Аты/тегі тек әріптерден тұруы керек." if is_kk else "Имя/фамилия должны состоять только из букв.")
            return redirect(request.META.get('HTTP_REFERER', 'volunteer_dashboard'))
            
        if middle_name and not _NAME_RE.fullmatch(middle_name):
            messages.error(request, "Әкесінің аты тек әріптерден тұруы керек." if is_kk else "Отчество должно состоять только из букв.")
            return redirect(request.META.get('HTTP_REFERER', 'volunteer_dashboard'))
            
        normalized_phone = _normalize_phone_number(phone_number)
        if not normalized_phone or not _is_valid_kz_mobile(normalized_phone):
            messages.error(request, "Қазақстанның ұялы нөмірі қате. Мысалы: +77471234567" if is_kk else "Неверный мобильный номер Казахстана. Пример: +77471234567")
            return redirect(request.META.get('HTTP_REFERER', 'volunteer_dashboard'))
            
        if CustomUser.objects.filter(phone_number=normalized_phone).exclude(pk=request.user.pk).exists() or CustomUser.objects.filter(username=normalized_phone).exclude(pk=request.user.pk).exists():
            messages.error(request, "Бұл телефон нөмірі бұрыннан тіркелген." if is_kk else "Этот номер телефона уже зарегистрирован.")
            return redirect(request.META.get('HTTP_REFERER', 'volunteer_dashboard'))
            
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.middle_name = middle_name
        user.phone_number = normalized_phone
        user.username = normalized_phone
        user.city = city
        user.save()
        
        messages.success(request, "Профиль сәтті жаңартылды!" if is_kk else "Профиль успешно обновлен!")
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('volunteer_dashboard')
        return redirect(next_url)
        
    return redirect(request.META.get('HTTP_REFERER') or reverse('volunteer_dashboard'))

@login_required
def client_dashboard(request):
    guard = _require_role(request, {'Client'})
    if guard:
        return guard
    if request.method == 'POST':
        form_type = request.POST.get('form_type') or 'help_request'

        if form_type == 'help_request':
            category = request.POST.get('category')
            address = (request.POST.get('address') or '').strip()
            description = (request.POST.get('description') or '').strip()

            if category and address and description and len(address) <= 255 and len(description) <= 1000:
                HelpRequest.objects.create(
                    client=request.user,
                    category=category,
                    address=address,
                    description=description,
                    status='Pending'
                )
                messages.success(request, _("Өтініміңіз сәтті жіберілді!"))
            else:
                messages.error(request, _("Көмек өтінімінің барлық өрістерін толтырыңыз."))
            return redirect('/client-dashboard/?tab=askHelpSection')

        if form_type == 'volunteer_application':
            skills = (request.POST.get('skills') or '').strip()
            motivation_reason = (request.POST.get('motivation_reason') or '').strip()
            has_personal_car = request.POST.get('has_personal_car') == 'on'
            city = (request.POST.get('city') or '').strip()

            if not skills or not motivation_reason:
                messages.error(request, _("Дағдылар мен себепті толтырыңыз."))
                return redirect('client_dashboard')
            if len(skills) > 255 or len(motivation_reason) > 1000:
                messages.error(request, _("Өрістер тым ұзын."))
                return redirect('client_dashboard')
            if city and len(city) > 100:
                messages.error(request, _("Қала атауы тым ұзын."))
                return redirect('client_dashboard')

            existing_pending = VolunteerApplication.objects.filter(user=request.user, status='Pending').exists()
            if existing_pending:
                messages.error(request, _("Сізде қаралу үстіндегі ерікті болуға өтінім бар."))
                return redirect('client_dashboard')

            VolunteerApplication.objects.create(
                user=request.user,
                skills=skills,
                motivation_reason=motivation_reason,
                has_personal_car=has_personal_car,
                status='Pending',
            )
            if city:
                CustomUser.objects.filter(pk=request.user.pk).update(city=city)

            messages.success(request, _("Еріктінің сауалнамасы қарауға жіберілді."))
            return redirect('/client-dashboard/?tab=becomeVolunteerSection')

    help_requests = HelpRequest.objects.filter(client=request.user).order_by('-created_at')
    latest_application = VolunteerApplication.objects.filter(user=request.user).order_by('-submitted_at').first()
    
    context = {
        'help_requests': help_requests,
        'latest_application': latest_application,
        'total_requests': help_requests.count(),
        'pending_requests_count': help_requests.filter(status='Pending').count(),
        'completed_requests_count': help_requests.filter(status='Completed').count(),
        'latest_news': NewsPost.objects.filter(is_published=True).order_by('-published_at')[:3],
    }
    return render(request, 'clientdashboard.html', context)

@login_required
def admin_dashboard(request):
    guard = _require_role(request, {'Admin'})
    if guard:
        return guard
        
    context = {
        'completed_tasks': VolunteerTask.objects.filter(status='Completed').count(),
        'pending_requests': HelpRequest.objects.filter(status='Pending').count(),
        'pending_volunteers': VolunteerApplication.objects.filter(status='Pending').count(),
        'total_volunteers': CustomUser.objects.filter(role='Volunteer').count(),
        'total_requests': HelpRequest.objects.count(),
        'recent_requests': HelpRequest.objects.select_related('client').order_by('-created_at')[:5],
    }
    return render(request, 'admindash.html', context)

@login_required
def admin_clients(request):
    guard = _require_role(request, {'Admin'})
    if guard:
        return guard

    if request.method == 'POST':
        action = request.POST.get('action')
        req_id = request.POST.get('request_id')
        help_request = get_object_or_404(HelpRequest, pk=req_id)

        if action == 'accept':
            if help_request.status == 'Pending':
                help_request.status = 'Review'
            help_request.save(update_fields=['status'])
        elif action == 'reject':
            help_request.status = 'Rejected'
            help_request.save(update_fields=['status'])
        elif action == 'publish_task':
            if help_request.status == 'Pending':
                help_request.status = 'Review'
                help_request.save(update_fields=['status'])

            existing_task = getattr(help_request, 'volunteer_task', None)
            if existing_task:
                messages.info(request, _("Бұл өтінім бойынша тапсырма бұрыннан бар."))
                return redirect('admin_clients')

            date_str = (request.POST.get('task_date') or '').strip()
            time_str = (request.POST.get('task_time') or '').strip()
            duration_str = (request.POST.get('task_duration') or '').strip()

            task_date = timezone.localdate() + timedelta(days=1)
            task_time = timezone.localtime().replace(second=0, microsecond=0).time()
            task_duration = 2

            try:
                if date_str:
                    task_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                if time_str:
                    task_time = datetime.strptime(time_str, '%H:%M').time()
                if duration_str:
                    task_duration = max(1, min(24, int(duration_str)))
            except Exception:
                messages.error(request, _("Тапсырма уақыты/күні қате."))
                return redirect('admin_clients')

            title = help_request.get_category_display() if hasattr(help_request, 'get_category_display') else help_request.category
            if help_request.client and getattr(help_request.client, 'city', None):
                title = f"{title} — {help_request.client.city}"

            assigned_volunteer_id = request.POST.get('assigned_volunteer')
            assigned_volunteer = None
            task_status = 'Scheduled'
            if assigned_volunteer_id:
                assigned_volunteer = CustomUser.objects.filter(pk=assigned_volunteer_id, role='Volunteer').first()
                if assigned_volunteer:
                    task_status = 'In-Progress'

            VolunteerTask.objects.create(
                title=title,
                category=help_request.category,
                address=help_request.address,
                description=help_request.description,
                date=task_date,
                time=task_time,
                duration=task_duration,
                status=task_status,
                assigned_volunteer=assigned_volunteer,
                help_request=help_request,
            )
            help_request.status = 'Process'
            help_request.save(update_fields=['status'])
            messages.success(request, _("Тапсырма волонтёрлерге жарияланды."))

        return redirect('admin_clients')

    help_requests = HelpRequest.objects.select_related('client').order_by('-created_at')
    context = {
        'help_requests': help_requests,
        'pending_requests': help_requests.filter(status='Pending').count(),
        'pending_volunteers': VolunteerApplication.objects.filter(status='Pending').count(),
        'default_task_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
        'default_task_time': timezone.localtime().strftime('%H:%M'),
        'volunteers': CustomUser.objects.filter(role='Volunteer'),
    }
    return render(request, 'admincust.html', context)

@login_required
def admin_volunteers(request):
    guard = _require_role(request, {'Admin'})
    if guard:
        return guard

    if request.method == 'POST':
        action = request.POST.get('action')
        app_id = request.POST.get('application_id')
        application = get_object_or_404(VolunteerApplication.objects.select_related('user'), pk=app_id)

        if action == 'accept':
            application.status = 'Approved'
            application.save(update_fields=['status'])
            application.user.role = 'Volunteer'
            application.user.save(update_fields=['role'])
            messages.success(request, f"Пайдаланушы {application.user.get_full_name()} ерікті ретінде сәтті қабылданды." if request.COOKIES.get('ui_lang', 'kk') == 'kk' else f"Пользователь {application.user.get_full_name()} успешно принят в волонтеры.")
        elif action == 'reject':
            application.status = 'Rejected'
            application.save(update_fields=['status'])
            application.user.role = 'Client'
            application.user.save(update_fields=['role'])
            messages.info(request, f"Пайдаланушы {application.user.get_full_name()} өтінімі бас тартылды." if request.COOKIES.get('ui_lang', 'kk') == 'kk' else f"Заявка пользователя {application.user.get_full_name()} отклонена.")

        from django.urls import reverse
        return redirect(f"{reverse('admin_volunteers')}?selected_id={app_id}")

    applications = VolunteerApplication.objects.select_related('user').order_by('-submitted_at')
    context = {
        'applications': applications,
        'pending_volunteers': applications.filter(status='Pending').count(),
        'pending_requests': HelpRequest.objects.filter(status='Pending').count(),
    }
    return render(request, 'admin_new_volunteers.html', context)

@login_required
def admin_tasks(request):
    guard = _require_role(request, {'Admin'})
    if guard:
        return guard

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_task':
            title = (request.POST.get('title') or '').strip()
            description = (request.POST.get('description') or '').strip()
            address = (request.POST.get('address') or '').strip()
            category = (request.POST.get('category') or '').strip()
            date_str = (request.POST.get('date') or '').strip()
            time_str = (request.POST.get('time') or '').strip()
            duration_str = (request.POST.get('duration') or '2').strip()
            volunteer_id = request.POST.get('assigned_volunteer')

            if not title:
                messages.error(request, _("Тапсырма атауы міндетті."))
                return redirect('admin_tasks')

            task_date = timezone.localdate() + timedelta(days=1)
            task_time = timezone.localtime().replace(second=0, microsecond=0).time()
            task_duration = 2

            try:
                if date_str:
                    task_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                if time_str:
                    task_time = datetime.strptime(time_str, '%H:%M').time()
                if duration_str:
                    task_duration = max(1, min(24, int(duration_str)))
            except Exception:
                messages.error(request, _("Күні немесе уақыты дұрыс емес."))
                return redirect('admin_tasks')

            assigned_volunteer = None
            task_status = 'Scheduled'
            if volunteer_id:
                assigned_volunteer = CustomUser.objects.filter(pk=volunteer_id, role='Volunteer').first()
                if assigned_volunteer:
                    task_status = 'In-Progress'

            VolunteerTask.objects.create(
                title=title,
                description=description,
                address=address,
                category=category,
                date=task_date,
                time=task_time,
                duration=task_duration,
                status=task_status,
                assigned_volunteer=assigned_volunteer,
            )
            messages.success(request, _("Тапсырма сәтті жасалды."))
            return redirect('admin_tasks')

        task_id = request.POST.get('task_id')
        task = get_object_or_404(VolunteerTask, pk=task_id)

        if action == 'complete':
            task.status = 'Completed'
            task.save(update_fields=['status'])
            if task.help_request_id:
                HelpRequest.objects.filter(pk=task.help_request_id).update(status='Completed')
            if task.assigned_volunteer_id:
                CustomUser.objects.filter(pk=task.assigned_volunteer_id).update(total_hours=F('total_hours') + (task.duration or 0))
        elif action == 'assign_volunteer':
            volunteer_id = request.POST.get('volunteer_id')
            volunteer = get_object_or_404(CustomUser, pk=volunteer_id, role='Volunteer')
            task.assigned_volunteer = volunteer
            task.status = 'In-Progress'
            task.save(update_fields=['assigned_volunteer', 'status'])
            if task.help_request_id:
                HelpRequest.objects.filter(pk=task.help_request_id).update(status='Process')
            messages.success(request, _("Ерікті сәтті тағайындалды."))
        elif action == 'delete_task':
            task.delete()
            messages.success(request, _("Тапсырма жойылды."))

        return redirect('admin_tasks')

    tasks = VolunteerTask.objects.select_related('assigned_volunteer', 'help_request', 'help_request__client').order_by('-date', '-time')
    context = {
        'tasks': tasks,
        'in_progress_count': tasks.filter(status='In-Progress').count(),
        'pending_requests': HelpRequest.objects.filter(status='Pending').count(),
        'pending_volunteers': VolunteerApplication.objects.filter(status='Pending').count(),
        'volunteers': CustomUser.objects.filter(role='Volunteer'),
        'default_task_date': (timezone.localdate() + timedelta(days=1)).isoformat(),
        'default_task_time': timezone.localtime().strftime('%H:%M'),
    }
    return render(request, 'adminvolon.html', context)

@login_required
def admin_analytics(request):
    guard = _require_role(request, {'Admin'})
    if guard:
        return guard

    total_requests = HelpRequest.objects.count()
    pending_requests = HelpRequest.objects.filter(status='Pending').count()
    completed_requests = HelpRequest.objects.filter(status='Completed').count()
    rejected_requests = HelpRequest.objects.filter(status='Rejected').count()
    total_users = CustomUser.objects.count()
    total_clients = CustomUser.objects.filter(role='Client').count()
    total_volunteers = CustomUser.objects.filter(role='Volunteer').count()
    total_admins = CustomUser.objects.filter(role='Admin').count()

    def _pct(part, whole):
        if not whole:
            return 0
        return int(round((part * 100) / whole))

    context = {
        'total_users': total_users,
        'total_clients': total_clients,
        'total_volunteers': total_volunteers,
        'total_admins': total_admins,
        'total_requests': total_requests,
        'completed_requests': completed_requests,
        'rejected_requests': rejected_requests,
        'pending_requests': pending_requests,
        'pending_volunteers': VolunteerApplication.objects.filter(status='Pending').count(),
        'pending_requests_pct': _pct(pending_requests, total_requests),
        'completed_requests_pct': _pct(completed_requests, total_requests),
        'rejected_requests_pct': _pct(rejected_requests, total_requests),
        'clients_pct': _pct(total_clients, total_users),
        'volunteers_pct': _pct(total_volunteers, total_users),
        'admins_pct': _pct(total_admins, total_users),
    }
    return render(request, 'adminanalys.html', context)

def moderator_login_view(request):
    if request.user.is_authenticated and (request.user.is_superuser or getattr(request.user, 'role', None) == 'Admin'):
        return redirect('admin_dashboard')
    return render(request, 'moderator_login.html')

@login_required
def admin_users(request):
    guard = _require_role(request, {'Admin'})
    if guard:
        return guard

    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')

        if action == 'delete_user' and user_id:
            target_user = CustomUser.objects.filter(pk=user_id, is_superuser=False).first()
            if target_user:
                name = target_user.get_full_name() or target_user.username
                target_user.delete()
                is_kk = request.COOKIES.get('ui_lang', 'kk') == 'kk'
                messages.success(request, f"Пайдаланушы {name} жойылды." if is_kk else f"Пользователь {name} удалён.")
            else:
                messages.error(request, "Пайдаланушы табылмады немесе оны жою мүмкін емес." if request.COOKIES.get('ui_lang', 'kk') == 'kk' else "Пользователь не найден или его нельзя удалить.")
        return redirect('admin_users')

    users = CustomUser.objects.filter(is_superuser=False).order_by('-date_joined')
    context = {
        'all_users': users,
        'total_clients': users.filter(role='Client').count(),
        'total_volunteers': users.filter(role='Volunteer').count(),
        'pending_requests': HelpRequest.objects.filter(status='Pending').count(),
        'pending_volunteers': VolunteerApplication.objects.filter(status='Pending').count(),
    }
    return render(request, 'admin_users.html', context)

@login_required
def admin_news(request):
    guard = _require_role(request, {'Admin'})
    if guard:
        return guard

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            title_kk = (request.POST.get('title_kk') or '').strip()
            title_ru = (request.POST.get('title_ru') or '').strip()
            body_kk = (request.POST.get('body_kk') or '').strip()
            body_ru = (request.POST.get('body_ru') or '').strip()
            is_published = request.POST.get('is_published') == 'on'
            cover_file = request.FILES.get('cover_image')

            if title_kk:
                post = NewsPost(
                    title_kk=title_kk,
                    title_ru=title_ru,
                    body_kk=body_kk,
                    body_ru=body_ru,
                    is_published=is_published,
                )
                if cover_file:
                    post.cover_image = cover_file
                post.save()
                messages.success(request, _(u"Жаңалық сәтті жарияланды.") if is_published else _(u"Жаңалық жоба ретінде сақталды."))
            else:
                messages.error(request, _(u"Тақырып (KK) міндетті түрде толтырылуы керек."))
                
        elif action == 'edit':
            post_id = request.POST.get('post_id')
            post = get_object_or_404(NewsPost, pk=post_id)
            title_kk = (request.POST.get('title_kk') or '').strip()
            title_ru = (request.POST.get('title_ru') or '').strip()
            body_kk = (request.POST.get('body_kk') or '').strip()
            body_ru = (request.POST.get('body_ru') or '').strip()
            is_published = request.POST.get('is_published') == 'on'
            cover_file = request.FILES.get('cover_image')
            remove_image = request.POST.get('remove_image') == '1'

            if title_kk:
                post.title_kk = title_kk
                post.title_ru = title_ru
                post.body_kk = body_kk
                post.body_ru = body_ru
                post.is_published = is_published
                if cover_file:
                    if post.cover_image:
                        post.cover_image.delete(save=False)
                    post.cover_image = cover_file
                elif remove_image and post.cover_image:
                    post.cover_image.delete(save=False)
                    post.cover_image = None
                post.save()
                messages.success(request, _(u"Жа\u04a3\u0430\u043b\u044b\u049b \u04e9\u0437\u0433\u0435\u0440\u0442\u0456\u043b\u0434\u0456."))
            else:
                messages.error(request, _(u"\u0422\u0430\u049b\u044b\u0440\u044b\u043f (KK) \u043c\u0456\u043d\u0434\u0435\u0442\u0442\u0456 \u0442\u04af\u0440\u0434\u0435 \u0442\u043e\u043b\u0442\u044b\u0440\u044b\u043b\u0443\u044b \u043a\u0435\u0440\u0435\u043a."))

        elif action == 'delete':
            post_id = request.POST.get('post_id')
            post = get_object_or_404(NewsPost, pk=post_id)
            if post.cover_image:
                post.cover_image.delete(save=False)
            post.delete()
            messages.success(request, _(u"\u0416\u0430\u04a3\u0430\u043b\u044b\u049b \u0436\u043e\u0439\u044b\u043b\u0434\u044b."))
            
        return redirect('admin_news')

    # Handle GET request deletion
    action = request.GET.get('action')
    if action == 'delete':
        post_id = request.GET.get('id')
        if post_id:
            post = get_object_or_404(NewsPost, pk=post_id)
            post.delete()
            messages.success(request, _("Жаңалық жойылды."))
            return redirect('admin_news')

    news_posts = NewsPost.objects.order_by('-published_at')
    context = {
        'news_posts': news_posts,
        'pending_requests': HelpRequest.objects.filter(status='Pending').count(),
        'pending_volunteers': VolunteerApplication.objects.filter(status='Pending').count(),
    }
    return render(request, 'admin_news.html', context)


@login_required
def admin_contentpages(request):
    guard = _require_role(request, {'Admin'})
    if guard:
        return guard

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            slug = (request.POST.get('slug') or '').strip().lower()
            title_kk = (request.POST.get('title_kk') or '').strip()
            title_ru = (request.POST.get('title_ru') or '').strip()
            body_kk = (request.POST.get('body_kk') or '').strip()
            body_ru = (request.POST.get('body_ru') or '').strip()
            is_published = request.POST.get('is_published') == 'on'
            
            if slug and title_kk:
                ContentPage.objects.create(
                    slug=slug,
                    title_kk=title_kk,
                    title_ru=title_ru,
                    body_kk=body_kk,
                    body_ru=body_ru,
                    is_published=is_published
                )
                messages.success(request, _("Бет сәтті жасалды."))
            else:
                messages.error(request, _("Slug пен Тақырып (KK) міндетті."))
                
        elif action == 'edit':
            page_id = request.POST.get('page_id')
            page = get_object_or_404(ContentPage, pk=page_id)
            slug = (request.POST.get('slug') or '').strip().lower()
            title_kk = (request.POST.get('title_kk') or '').strip()
            title_ru = (request.POST.get('title_ru') or '').strip()
            body_kk = (request.POST.get('body_kk') or '').strip()
            body_ru = (request.POST.get('body_ru') or '').strip()
            is_published = request.POST.get('is_published') == 'on'
            
            if slug and title_kk:
                page.slug = slug
                page.title_kk = title_kk
                page.title_ru = title_ru
                page.body_kk = body_kk
                page.body_ru = body_ru
                page.is_published = is_published
                page.save()
                messages.success(request, _("Бет сәтті өзгертілді."))
            else:
                messages.error(request, _("Slug пен Тақырып (KK) міндетті."))
                
        elif action == 'delete':
            page_id = request.POST.get('page_id')
            page = get_object_or_404(ContentPage, pk=page_id)
            page.delete()
            messages.success(request, _("Бет жойылды."))
            
        return redirect('admin_contentpages')

    # Handle GET request deletion
    action = request.GET.get('action')
    if action == 'delete':
        page_id = request.GET.get('id')
        if page_id:
            page = get_object_or_404(ContentPage, pk=page_id)
            page.delete()
            messages.success(request, _("Бет жойылды."))
            return redirect('admin_contentpages')

    content_pages = ContentPage.objects.order_by('slug')
    context = {
        'content_pages': content_pages,
        'pending_requests': HelpRequest.objects.filter(status='Pending').count(),
        'pending_volunteers': VolunteerApplication.objects.filter(status='Pending').count(),
    }
    return render(request, 'admin_contentpages.html', context)


