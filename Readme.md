# Запись значения в пользовательское поле на карточке trello

> Мы ведем в trello свои задачи. Номер карточки используется как номер задачи и записывается в комментарии в коде, в отчеты и т.д. Если выполненные карточки перенести на другую доску (Архив), ее номер переприсваивается в соответствии с нумерацией на архивной доске. Это стало для нас неприятным сюрпризом и несколько номеров задач мы не смогли восстановить. Предлагаемый скрипт позволяет избежать подобной неприятности. Он сохраняет текущий номер карточки (на рабочей доске) в пользовательское поле (Custom field)

Авторизация в организации trello настраивается в модуле `auth`. В этом каталоге нужно создать файл `__init__.py` следующего содержания:

```python
APIKY = '<<<TRELLO-API-KEY>>>'
TOKEN = '<<<ACCESS-TOKEN>>>'
ORGANISATION = '<<<organization>>>'

```

Необходимые значения api-key и token нужно получить в [trello](https://trello.com/app-key), а id организации можно получить в URL если кликнуть на имя нужной команды в подменю "КОМАНДЫ" на основной странице [trello](https://trello.com/) после авторизации. У меня он выглядит так: _https://trello.com/_**user08081543**_/home_
Параметры работы указываются в словаре `dt` в тексте скрипта.

```python
dt = {
     'boardName': "Обслуживание АРПСТН-091" - Название доски
    ,'listName':  "Запланировано"           - Название списка | None
    ,'fieldName': "task-id"                 - Название пользовательского поля
    ,'fieldType': "number"                  - Тип значения пользовательского поля
}

```

Если `listName` не указано, то будут обработаны все (открытые) карточки на доске.  
~~Кстати о типе. Все попытки присвоить значение числовому полю не увенчались. [API](https://developer.atlassian.com/cloud/trello/guides/rest-api/getting-started-with-custom-fields/) упорно возвращал ошибку _400, {"message":"Invalid custom field item value.","error":"ERROR"}_. Как только я изменил [тип значения поля](https://developer.atlassian.com/cloud/trello/rest/api-group-cards/#api-cards-idcard-customfield-idcustomfield-item-put) и, соответственно, запрос с `number` на `text`, ошибки пропали.~~