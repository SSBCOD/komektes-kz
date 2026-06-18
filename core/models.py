from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('Volunteer', _('Ерікті')),
        ('Client', _('Клиент')),
        ('Admin', _('Әкімші')),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Client')
    phone_number = models.CharField(max_length=20, blank=True, null=True, unique=True)
    middle_name = models.CharField(max_length=150, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    total_hours = models.PositiveIntegerField(default=0)
    rank_title = models.CharField(max_length=100, blank=True, null=True)

    def get_full_name(self):
        parts = [self.last_name, self.first_name, self.middle_name]
        return ' '.join([p for p in parts if (p or '').strip()])

    def save(self, *args, **kwargs):
        if self.is_superuser:
            self.role = 'Admin'
            self.is_staff = True
        elif self.role == 'Admin':
            self.is_staff = True
            self.is_superuser = True
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

class HelpRequest(models.Model):
    CATEGORY_CHOICES = (
        ('Food', _('Азық-түлік')),
        ('Medicine', _('Дәрі-дәрмек')),
        ('Cleaning', _('Тазалау')),
        ('Financial', _('Қаржылай көмек')),
        ('Other', _('Басқа')),
    )
    STATUS_CHOICES = (
        ('Pending', _('Күтуде')),
        ('Review', _('Қаралуда')),
        ('Process', _('Өңдеуде')),
        ('Completed', _('Орындалды')),
        ('Rejected', _('Бас тартылды')),
    )
    client = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='help_requests')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    address = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.category} - {self.client.username}"

class VolunteerTask(models.Model):
    STATUS_CHOICES = (
        ('Scheduled', _('Жоспарланды')),
        ('In-Progress', _('Орындау үстінде')),
        ('Completed', _('Орындалды')),
    )
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, blank=True, default='')
    address = models.CharField(max_length=255, blank=True, default='')
    description = models.TextField(blank=True, default='')
    date = models.DateField()
    time = models.TimeField()
    duration = models.IntegerField(help_text="Duration in hours")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Scheduled')
    assigned_volunteer = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    help_request = models.OneToOneField('HelpRequest', on_delete=models.SET_NULL, null=True, blank=True, related_name='volunteer_task')

    def __str__(self):
        return self.title

class VolunteerApplication(models.Model):
    STATUS_CHOICES = (
        ('Pending', _('Күтуде')),
        ('Approved', _('Қабылданды')),
        ('Rejected', _('Бас тартылды')),
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='applications')
    skills = models.CharField(max_length=255)
    motivation_reason = models.TextField()
    has_personal_car = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"App: {self.user.username}"

class ContentPage(models.Model):
    slug = models.SlugField(max_length=50, unique=True)
    title_kk = models.CharField(max_length=200)
    title_ru = models.CharField(max_length=200, blank=True, default='')
    body_kk = models.TextField(blank=True, default='')
    body_ru = models.TextField(blank=True, default='')
    is_published = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.slug

class NewsPost(models.Model):
    title_kk = models.CharField(max_length=200)
    title_ru = models.CharField(max_length=200, blank=True, default='')
    body_kk = models.TextField(blank=True, default='')
    body_ru = models.TextField(blank=True, default='')
    cover_image = models.ImageField(upload_to='news_covers/', blank=True, null=True)
    cover_image_url = models.URLField(blank=True, default='')  # legacy URL field
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(default=timezone.now)

    def get_cover(self):
        """Returns the URL of the cover image (uploaded file takes priority over URL)."""
        if self.cover_image:
            return self.cover_image.url
        return self.cover_image_url or ''

    def __str__(self):
        return self.title_kk
