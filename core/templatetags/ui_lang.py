from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def t(context, kk_text, ru_text=None):
    request = context.get('request')
    lang = 'kk'
    if request is not None:
        lang = request.COOKIES.get('ui_lang', 'kk')
    if lang == 'ru' and ru_text is not None:
        return ru_text
    return kk_text


@register.simple_tag(takes_context=True)
def tc(context, choice_value):
    request = context.get('request')
    lang = 'kk'
    if request is not None:
        lang = request.COOKIES.get('ui_lang', 'kk')
    
    val = str(choice_value or '').strip()
    
    # Translation dictionary
    translations = {
        # Categories
        'Food': {'kk': 'Азық-түлік', 'ru': 'Продукты'},
        'Азық-түлік': {'kk': 'Азық-түлік', 'ru': 'Продукты'},
        'Medicine': {'kk': 'Дәрі-дәрмек', 'ru': 'Лекарства'},
        'Дәрі-дәрмек': {'kk': 'Дәрі-дәрмек', 'ru': 'Лекарства'},
        'Cleaning': {'kk': 'Қар/аула тазалау', 'ru': 'Уборка двора'},
        'Тазалау': {'kk': 'Тазалау', 'ru': 'Уборка'},
        'Қар/аула тазалау': {'kk': 'Қар/аула тазалау', 'ru': 'Уборка двора'},
        'Financial': {'kk': 'Қаржылай көмек', 'ru': 'Финансовая помощь'},
        'Қаржылай көмек': {'kk': 'Қаржылай көмек', 'ru': 'Финансовая помощь'},
        'Қаржылай': {'kk': 'Қаржылай', 'ru': 'Финансовая'},
        'Other': {'kk': 'Басқа', 'ru': 'Другое'},
        'Басқа': {'kk': 'Басқа', 'ru': 'Другое'},
        
        # Statuses
        'Pending': {'kk': 'Күтуде', 'ru': 'В ожидании'},
        'Күтуде': {'kk': 'Күтуде', 'ru': 'В ожидании'},
        'Review': {'kk': 'Қаралуда', 'ru': 'На рассмотрении'},
        'Қаралуда': {'kk': 'Қаралуда', 'ru': 'На рассмотрении'},
        'Process': {'kk': 'Жарияланды', 'ru': 'Опубликовано'},
        'Өңдеуде': {'kk': 'Өңдеуде', 'ru': 'В работе'},
        'Жарияланды': {'kk': 'Жарияланды', 'ru': 'Опубликовано'},
        'Completed': {'kk': 'Орындалды', 'ru': 'Выполнено'},
        'Орындалды': {'kk': 'Орындалды', 'ru': 'Выполнено'},
        'Аяқталды': {'kk': 'Аяқталды', 'ru': 'Завершено'},
        'Rejected': {'kk': 'Бас тартылды', 'ru': 'Отклонено'},
        'Бас тартылды': {'kk': 'Бас тартылды', 'ru': 'Отклонено'},
        'Бас тартылған': {'kk': 'Бас тартылған', 'ru': 'Отклонённые'},
        
        # Task statuses
        'Scheduled': {'kk': 'Жоспарланды', 'ru': 'Запланировано'},
        'Жоспарланды': {'kk': 'Жоспарланды', 'ru': 'Запланировано'},
        'In-Progress': {'kk': 'Орындау үстінде', 'ru': 'В процессе'},
        'Орындау үстінде': {'kk': 'Орындау үстінде', 'ru': 'В процессе'},
        
        # Volunteer experience
        'сағ': {'kk': 'сағ', 'ru': 'ч'},
        'ч': {'kk': 'сағ', 'ru': 'ч'},
    }
    
    if val in translations:
        return translations[val].get(lang, val)
    return val


