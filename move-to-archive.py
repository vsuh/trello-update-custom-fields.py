import json
import logging
import pprint
import sys
import requests
import trello as tl
from auth import APIKY, ORGANISATION, TOKEN
from dateutil.relativedelta import relativedelta as rd
from datetime import datetime as dt
import pytz


order = {
     'WorkDesk': '*Текучка*'
    ,'WorkList': 'Выполнено'
    ,'MonthOld': 3
    ,'DeskTarg': 'Архив'
    ,'FieldTrg': '≡'
}

def log_prepare():
    log = logging.getLogger(__file__)
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.INFO)
    f_handler = logging.FileHandler('LOG.LOG')
    f_handler.setLevel(logging.DEBUG)
    prv_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
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

def get_board(name)->list:
    """
    возвращает список описаний (словарей) доски по её имени
    name: строка или список строк - имен досок
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
    # log.debug(f"Ищем в свойствах доски `{brd['name']}` Custom field с именем `{name}`")
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
            # log.info(f"Нашли польз. поле `{ff['name']}`(id={ff['id']}) на доске `{brd['name']}`")
            log.info(f"Нашли польз. поле (id={ff['id']}) на доске `{brd['name']}`")
            return ff
    return None

def get_list(brd, name):
    lists = api.boards.get_list(brd['id'])
    for lst in lists:
        if lst['name']==name:
            return lst
    return None

def cardDate(card):
    """
    возвращает дату создания переданной карточки
    """
    creation_time = dt.fromtimestamp(int(card['id'][0:8],16))
    log.debug(f'Получили дату карточки № {card["idShort"]}: {msk.localize(creation_time).astimezone().isoformat()} из строки `{int(card["id"][0:8],16)}` (timestamp)')
    return msk.localize(creation_time).astimezone()

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

def get_CustFldLst_value(UserFieldList, idValue):
    for opt in UserFieldList['options']:
        if opt['id']==idValue:
            return opt
    return None

def create_list(trgBoard, lstName):
    return api.boards.new_list(trgBoard['id'], lstName)

def prepare_movements():
    boards = get_board(order['WorkDesk'])
    srcBoard = boards[0]
    boards = get_board(order['DeskTarg'])
    trgBoard = boards[0]
    date_edge = dt.now(msk) - rd(months=order['MonthOld'])
    log.debug(f'Отбираются карточки старше {dt.ctime(date_edge)}')
    # pp(type(srcBoard))
    srcField = get_c_field(srcBoard, order['FieldTrg'])
    # pp(srcField)
    srcList = get_list(srcBoard, order['WorkList'])
    cards = api.lists.get_card(srcList['id'])
    movements=[]
    log.debug(f"Подготавливаем список карточек для переноса")
    for next_card in cards:
        next_card_Date = cardDate(next_card)
        if next_card_Date>date_edge:
            continue
        idValue = get_custom_field_value(next_card['id'], srcField['id'])
        ValueDic = get_CustFldLst_value(srcField, idValue)
        if ValueDic is None:
            log.info(f"В карточке № {next_card['idShort']} не заполнено значение пользовательского поля: `'FieldTrg'`")
        else:
            lstName = ValueDic['value']['text']
            trgList = get_list(trgBoard, lstName)
            if trgList is None:
                trgList = create_list(trgBoard, lstName)
            movements.append({'card':next_card, 'targetFieldValue': ValueDic, 'targetList': trgList, 'targetBoard': trgBoard})
    return movements

def do_move(mv:dict):
    log.info(f"Карточка № {mv['card']['idShort']} id={mv['card']['id']} переносится на доску: `{mv['targetBoard']['name']}/{mv['targetList']['name']}`")
    ret = api.cards.update_idBoard(mv['card']['id'], mv['targetList']['idBoard'])
    # ret - новая карточка (в новой доске)
    # log.debug(f"Карточка № {mv['card']['idShort']} id={mv['card']['id']} переносится в список: `{mv['targetList']['name']}`")
    ret = api.cards.update_idList(mv['card']['id'], mv['targetList']['id'])
    # ret - новая карточка (в новом списке)

VERIFY_SSL = True
logging.captureWarnings(True)
log = log_prepare()

log.info(f"{__file__}: Перенос карточек старше {order['MonthOld']} месяцев из `{order['WorkDesk']}` на доску `{order['DeskTarg']}`")
p = pprint.PrettyPrinter(indent=4, sort_dicts=True, compact=True)
pp = p.pprint
msk = pytz.timezone('Europe/Moscow')

api = tl.TrelloApi(apikey=APIKY, token=TOKEN)
movements = prepare_movements()
log.info(f"Переносим {len(movements)} карточек из `{order['WorkDesk']}` на доску `{order['DeskTarg']}`")
for movmnt in movements:
    do_move(movmnt)

