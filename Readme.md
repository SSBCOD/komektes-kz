🚀 Инструкция по установке проекта Komektes.kz

## Установить Python 3.13.3
Перейдите на сайт: https://www.python.org/downloads/
Скачайте версию Python 3.13.3 (нажмите кнопку Download Python 3.13.x).
Запустите скачанный файл .exe и следуйте инструкциям. Выбирайте Install Now.

⚠️ ВАЖНО: При установке обязательно поставьте галочку "Add Python to PATH" (внизу окна установщика). Без этого ничего не заработает!



python --version
python -m venv venv
venv\Scripts\Activate.ps1

❗ Если появилась ошибка "cannot be loaded because running scripts is disabled", выполните эту команду и повторите активацию:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser

## Username: admin
## Email address: (оставьте пустым, нажмите Enter)
## Password: ваш_пароль
## Password (again): ваш_пароль


python manage.py runserver


## Откройте браузер (Chrome, Edge, Firefox) и перейдите по адресу: 
http://127.0.0.1:8000/

## Как закончите работать нужно остановить сервер командой CTRL+C
deactivate

## Настройка успешно выполнена, при каждому запуске просто пишите:
venv\Scripts\Activate.ps1
python manage.py runserver
