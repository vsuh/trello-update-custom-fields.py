#!venv/Scripts/python.exe
"""
Скрипт присваивает дополнительному полю карточки (Custom field) значение `idShort` 
чтобы при переносе карточки на другую доску номер задачи не потерялся
"""
import json
import logging
import pprint
import sys
import requests
import trello as tl
from auth import APIKY, ORGANISATION, TOKEN

# ✔ TODO: протокол писать еще и в файл
# ✔ TODO: добавить функцию форматирования строки лога
# ✔ TODO: обеспечить обработку списка досок (или всех, если не указано)
# TODO: новая задача: перекладывать карточки из списка "Выполнено" в Архив

VERIFY_SSL = True
logging.captureWarnings(True)
tasks = [
    {    'taskName': 'Дата создания'
    ,'boardName':     ["Архив", "*Текучка*"]
    ,'listName':      None
    ,'fieldName':     "created"
    ,'fieldType':     "date"
    ,'chngTempl':     "cardDate"
  }
  ,
# {    'taskName': 'Номер карточки'
#     ,'boardName':     ["*Текучка*"]
#     ,'listName':      None
#     ,'fieldName':     "id"
#     ,'fieldType':     "number"
#     ,'chngTempl':     "cardId"
#   }
]


api = tl.TrelloApi(apikey=APIKY, token=TOKEN)
MAXERRS = 5

p = pprint.PrettyPrinter(indent=4, sort_dicts=True, compact=True)
pp = p.pprint

def log_prepare():
    log = logging.getLogger(__file__)
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.INFO)
    f_handler = logging.FileHandler('LOG.LOG')
    f_handler.setLevel(logging.DEBUG)
    prv_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        # lvl = args[1]
        record = prv_factory(*args, **kwargs)
        record.levelname = record.levelname.rjust(8)
        return record

    logging.setLogRecordFactory(record_factory)

    c_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    f_format = logging.Formatter('%(asctime)s | %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)
    log.addHandler(c_handler)
    log.addHandler(f_handler)
    log.setLevel(logging.DEBUG)
    return log

def get_board(name):
    """
    возвращает описание (словарь) доски по её имени
    """
    log.debug(f"Ищем доску с именем `{name}` (или все)")
    boards = api.organizations.get_board(idOrg_or_name=ORGANISATION, filter='open')
    if name is None:
        return boards
    list_of_boards_found = []
    name = [name] if type(name) == str else name
    up_names = list(map(lambda x: x.upper(), name))
    for brd in boards:
        for nm in up_names:
            if nm == brd['name'].upper():
                log.info(f"Нашли доску `{brd['name']}`(id={brd['id']})")
                list_of_boards_found.append(brd)

    return list_of_boards_found
    

def get_c_field(brd, name):
    """
    возвращает описание (словарь) пользовательского поля по его имени
    """
    import json

    import requests
    log.debug(f"Ищем в свойствах доски `{brd['name']}` Custom field с именем `{name}`")
    id = brd['id']
    url = f'https://api.trello.com/1/boards/{id}/customFields'

    headers = {
    "Accept": "application/json"
    }

    query = {
    'key': APIKY,
    'token': TOKEN
    }

    response = requests.request(
    "GET",
    url,
    headers=headers,
    params=query,
    verify=VERIFY_SSL
    )
    log.debug(f"Получаем все польз. поля на доске `{brd['name']}`")
    flds = json.loads(response.text)
    for ff in flds:
        if ff['name'].upper() == name.upper():
            log.info(f"Нашли польз. поле `{ff['name']}`(id={ff['id']}) на доске `{brd['name']}`")
            return ff
    return None

def get_lists(brd, name):
    """
    возвращает описание (словарь) списка по его имени. Если имя не указано (Null), возвращается массив описаний всех списков
    """
    log.debug(f"Получаем списки на доске `{brd['name']}` с именем `{name if not name is None else '<>'}` (или все)")
    lists = api.boards.get_list_filter(filter='open', board_id=brd['id'])
    if name is None:
        log.info(f"Возвращаем все листы с доски `{brd['name']}`")
        return lists
    for lst in lists:
        if lst['name'].upper() == name.upper():
            log.info(f"Нашли лист `{lst['name']}`(id={lst['id']}) на доске `{brd['name']}`")
            return [lst]
    return None

def get_all_cards(lst):
    """
    возвращает коллекцию (список) незакрытых карточек из списка `lst`
    """
    log.debug(f"Получаем все карточки из списка `{lst['name']}`(id={lst['id']})")
    return api.lists.get_card_filter(filter='open', idList=lst['id'])

def cardId(card) -> str:
    return str(card['idShort'])

def cardDate(card):
    """
    возвращает дату создания переданной карточки
    """
    from datetime import datetime as dt

    import pytz

    creation_time = dt.fromtimestamp(int(card['id'][0:8],16))
    msk = pytz.timezone('Europe/Moscow')
    log.debug(f'Получили дату карточки № {card["idShort"]}: {msk.localize(creation_time).astimezone().isoformat()} из строки {int(card["id"][0:8],16)}')
    return msk.localize(creation_time).astimezone().isoformat()

def get_custom_field_value(card_id, custom_field_id):
    """
    получает значение custom field из карточки
    """
    url = f'https://api.trello.com/1/cards/{card_id}/?fields={custom_field_id}&customFieldItems=true&key={APIKY}&token={TOKEN}'
    payload = {'token':TOKEN,'key':APIKY}
    headers = {
    "Accept": "application/json"
    }

    request = requests.get(url, json=payload, headers=headers, verify=VERIFY_SSL) 
    if request.ok:
        cf_items = json.loads(request.content)
        for cf_field in cf_items['customFieldItems']:
            if cf_field['idCustomField'] == custom_field_id:
                try:
                    return cf_field['value']
                except KeyError:
                    # получить значение опции по idValue
                    return cf_field['idValue']
    else:
        return None

def update_custom_field(card_id,custom_field_id,value_type,value):
    import requests
    url = f'https://api.trello.com/1/card/{card_id}/customField/{custom_field_id}/item?key={APIKY}&token={TOKEN}'
    
    payload = {'token':TOKEN,'key':APIKY,'value':{value_type: value}}
    request = requests.put(url,json=payload,verify=VERIFY_SSL) 
    return request

log = log_prepare()
log.info(f'*** Установка значений полей в карточках *** {sys.argv[0]}')
ers = 0
for task in tasks:
    log.info(f'Начинается обработка `{task["taskName"]}`')
    boards = get_board(task['boardName'])
    log.debug(f'Получили список досок из {len(boards)} эл.')
    for board in boards:
        log.debug(f'Обрабатывается доска `{board["name"]}`')
        list_of_lists = get_lists(board, task['listName'])
        log.info(f'Нашли {len(list_of_lists)} списков на доске {board["name"]}')
        custom_fileld_desc = get_c_field(board, task['fieldName'])
        for list in list_of_lists:
            crds = get_all_cards(list)
            log.info(f'Нашли {len(crds)} карточек в списке `{list["name"]}`')
            for card in crds:
                old_value = get_custom_field_value(card['id'], custom_fileld_desc['id'])
                log.debug(f'Получили предыдущее значение поля "{old_value}"')
                if task['chngTempl'] == 'cardDate':
                    if not old_value is None:
                        log.debug(f'тогда пропускаем')
                        continue
                    new_value = cardDate(card)
                if task['chngTempl'] == 'cardId':
                    if not (old_value is None and board['name'] == '*Текучка*'):
                        log.debug(f'тогда пропускаем')
                        continue
                    new_value = cardId(card)
                log.info(f'Изменение польз.поля "{task["fieldName"]}" карточки {card["id"]} на значение "{new_value}"')
                result = update_custom_field(card['id'], custom_fileld_desc['id'], task['fieldType'], new_value)
                if result.status_code < 400:
                    log.debug(f"{list['name'].upper()} RC: {result.status_code} {result.content}")
                else:
                    ers += 1
                    log.error(f"{list['name'].upper()} RC:({ers}) {result.status_code} {result.content} {result.request.body}")
                if ers > MAXERRS:
                    log.error('Прервали перебор карточек прервали после 5 ошибок')
                    break
            if ers > MAXERRS:
                log.error('Прервали перебор списков после 5 ошибок')
                break
    if ers:
        log.error("Завершено с ошибками")
    else:
        log.info("Завершено без ошибок")

