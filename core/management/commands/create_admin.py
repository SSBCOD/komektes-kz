from django.core.management.base import BaseCommand
from core.models import CustomUser

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        phone = '+77772223344'
        if not CustomUser.objects.filter(username=phone).exists():
            user = CustomUser(
                username=phone,
                phone_number=phone,
                first_name='Admin',
                last_name='Komektes',
                middle_name='',
                role='Admin',
                is_staff=True,
            )
            user.set_password('admin123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Admin created: phone=7772223344 password=admin123'))
        else:
            self.stdout.write('Admin already exists')
