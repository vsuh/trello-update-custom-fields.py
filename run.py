#!venv/Scripts/python.exe
"""
Скрипт присваивает дополнительному полю карточки (Custom field) значение `idShort` 
чтобы при переносе карточки на другую доску номер задачи не потерялся
"""
import trello as tl
import pprint
import logging
from auth import APIKY, TOKEN, ORGANISATION

dt = {
     'boardName':     "*Текучка*"
    ,'listName':      None
    ,'fieldName':     "id"
    ,'fieldType':     "number"
}


api = tl.TrelloApi(apikey=APIKY, token=TOKEN)
MAXERRS = 5

p = pprint.PrettyPrinter(indent=4, sort_dicts=True, compact=True)
pp = p.pprint

log = logging.getLogger(__name__)
c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)
c_format = logging.Formatter('%(asctime)s | %(name)s - %(levelname)s - %(message)s')
c_handler.setFormatter(c_format)
log.addHandler(c_handler)
log.setLevel(logging.DEBUG)

def get_board(name):
    log.debug(f"Ищем доску с именем `{name}`")
    for brd in api.organizations.get_board(idOrg_or_name=ORGANISATION, filter='open'):
        if name.upper() == brd['name'].upper():
            log.info(f"Нашли доску `{brd['name']}`(id={brd['id']})")
            return brd
    return None

def get_c_field(brd, name):
    import requests
    import json
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
    params=query
    )
    log.debug(f"Получаем все польз. поля на доске `{brd['name']}`")
    flds = json.loads(response.text)
    for ff in flds:
        if ff['name'].upper() == name.upper():
            log.info(f"Нашли поле `{ff['name']}`(id={ff['id']}) на доске `{brd['name']}`")
            return ff
    return None

def get_lists(brd, name):
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
    log.debug(f"получаем все карточки из списка `{lst['name']}`(id={lst['id']})")
    return api.lists.get_card_filter(filter='open', idList=lst['id'])

def update_custom_field(card_id,custom_field_id,value_type,value):
    import requests
    url = f'https://api.trello.com/1/card/{card_id}/customField/{custom_field_id}/item?key={APIKY}&token={TOKEN}'
    
    payload = {'token':TOKEN,'key':APIKY,'value':{value_type: value}}
    request = requests.put(url,json=payload) 
    return request


fld = get_c_field(get_board(dt['boardName']), dt['fieldName'])

lts = get_lists(get_board(dt['boardName']), dt['listName'])
ers = 0
for lst in lts:
    crds = get_all_cards(lst)
    for crd in crds:
        rp = update_custom_field(crd['id'], fld['id'],dt['fieldType'], str(crd['idShort']))
        if rp.status_code < 400:
            log.debug(f"{lst['name'].upper()} RC: {rp.status_code} {rp.content}")
        else:
            ers += 1
            log.error(f"{lst['name'].upper()} RC:({ers}) {rp.status_code} {rp.content} {rp.request.body}")
        if ers > MAXERRS:
            log.error('Выполнение прервали после 5 ошибок')
            break
if ers:
    log.error("Завершено с ошибками")

