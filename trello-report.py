#!venv/Scripts/python.exe
"""
Скрипт создает файл с отчетом по карточкам за определенный период
"""
import trello as tl
import pprint
import logging
import argparse
import pytz
import re
from datetime import datetime as dt, timedelta as td
from dateutil.relativedelta import relativedelta as rd
import requests
import json


from auth import APIKY, TOKEN, ORGANISATION

api = tl.TrelloApi(apikey=APIKY, token=TOKEN)
MAXERRS = 5
p = pprint.PrettyPrinter(indent=4, sort_dicts=True, compact=True)
pp = p.pprint
log = logging.getLogger(__name__)
parser = argparse.ArgumentParser(add_help=True
    , description='Формирование отчета по карточкам trello'
    , formatter_class=argparse.RawDescriptionHelpFormatter)
VERIFY_SSL = True
REPFILE = "report.tsv"
rigth_names = ['d', 'cd', 'pd', 'w', 'cw', 'pw', 'm', 'cm', 'pm', 'y', 'cy', 'py']
margins = {'name':None, 'past':None, 'beg':None, 'end':None, 'date': None}
cust_fields_names = ['id', 'Автор', '≡', 'created']
cf_options = None

def init():
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.INFO)
    c_format = logging.Formatter('%(asctime)s | %(name)s - %(levelname)s - %(message)s', datefmt='%d-%m-%y %H:%M:%S')
    c_handler.setFormatter(c_format)
    log.addHandler(c_handler)
    # log.setLevel(logging.DEBUG)
    parser.add_argument('--period', dest='period')
    parser.add_argument('--past', dest='past', default=1, type=int)
    parser.add_argument('--date', dest='date', help="date as DD-MM-YY")
    parser.usage = f'python {__file__} [OPTIONS]'
    
    parser.epilog = '''
PERIOD: d | w | m | y  тип периода: день, неделя, месяц или год
DATE: date дата, входящая в период в формате DD-MM-YY
PAST: nn количество периодов от текущего назад

ПРИМЕР:

    %(prog)s --period m --past 4
            список карточек за месяц, отстоящий на 4 месяца от текущего

    %(prog)s --period w --date 14-10-20
            список карточек с 12 по 18 октября 2020 г.
 
    см. примеры в README.md
    '''
    args = parser.parse_args()
    if not (args.period or args.date):
        raise SystemExit("Требуется параметр period или date (см. --help)")
    
    if args.period and not args.period in rigth_names:
        raise KeyError(f'Допускается период из списка {rigth_names}')
    
    margins['name'] = args.period if args.period else 'd'
    margins['past'] = args.past
    margins['date'] = dt.strptime(args.date,'%d-%m-%y') if args.date else None

def set_period_by_name():
    if margins['date'] is None:
        today = dt.today()
    else:
        today = margins['date']

    msk = pytz.timezone('Europe/Moscow')
    mode = margins['name'][-1]
    shift = 0
    if margins['past']:
        shift = margins['past']
    if margins['name'][0] == 'p':
        shift = 1
    if margins['name'][0] == 'c' or margins['date']:
        shift = 0

    log.debug(f'Вид периода:`{mode}`, смещение:-{shift}')
    if mode == 'd':
        beg = dt(today.year, today.month, today.day,0,0,0,0)
        if not shift == 0:
            beg -= rd(days=shift)
        margins['beg'] = msk.localize(beg)
        margins['end'] = msk.localize(dt(beg.year, beg.month, beg.day, 23, 59, 59, 999))
    if mode == 'w':
        weekday = dt.weekday(today) 
        if weekday>0:
            beg = today - rd(days=weekday)
        else:
            beg = today
        if shift>0:
            beg = beg - rd(weeks=shift)
        beg = dt(beg.year, beg.month, beg.day, 0, 0, 0, 0)
        margins['beg'] =  msk.localize(beg)
        end = beg + rd(days=6)
        end = dt(end.year, end.month, end.day, 23, 59, 59, 999)
        margins['end'] =  msk.localize(end)
    if mode == 'm':
        beg = dt(today.year, today.month, 1, 0, 0, 0, 0)
        if shift>0:
            beg = beg - rd(months=shift)
        margins['beg'] = msk.localize(beg)
        margins['end'] = msk.localize( beg + rd(months=1) - rd(seconds=1) )
    if mode == 'y':
        beg = dt(today.year-shift, 1, 1, 0, 0, 0, 0)
        margins['beg'] = msk.localize( beg )
        margins['end'] = msk.localize( beg + rd(years=1) - rd(seconds=1) )
    log.debug(f"вычисленный период: c {margins['beg'].strftime('%d-%m-%y')} по {margins['end'].strftime('%d-%m-%y %H:%M:%S')}")

def get_board_by_name(name):
    """
    возвращает описание (словарь) доски по её имени
    """
    log.debug(f"Ищем доску с именем `{name}`")
    for brd in api.organizations.get_board(idOrg_or_name=ORGANISATION, filter='open'):
        if name.upper() == brd['name'].upper():
            log.info(f"Нашли доску `{brd['name']}`(id={brd['id']})")
            return brd
    return None

def cardDate(card):
        creation_time = dt.fromtimestamp(int(card['id'][0:8],16))
        msk = pytz.timezone('Europe/Moscow')
        log.debug(f'Получили дату карточки № {card["idShort"]}: {creation_time.strftime("%d-%m-%y %H:%M:%S")} из строки {int(card["id"][0:8],16)}')
        return msk.localize(creation_time)

def get_c_field(brd, name):
    """
    возвращает описание (словарь) пользовательского поля по его имени
    """
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
            log.debug(f"На доске `{brd['name']}` нашли польз. поле `{ff['name']}`(id={ff['id']}) ")
            return ff
    return None

def get_custom_fields(board):
    """
    возвращает словарь словарей с идентификаторами custom fields из доски board
    """

    ret = {}
    for cf_name in cust_fields_names:
        cf = get_c_field(board, cf_name)
        ret.update({cf_name: {
             'brd': board['name']
            ,'br_id': board['id']
            ,'id': cf['id']
            }
        })
    return ret


def get_custom_field_value(card_id,custom_field_id):
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

def get_cf_options_of_board(board_id, idValue):
    global cf_options
    url = f'https://api.trello.com/1/boards/{board_id}/customFields?key={APIKY}&token={TOKEN}'
    payload = {'token':TOKEN,'key':APIKY}
    headers = {
    "Accept": "application/json"
    }
    if not cf_options:
        request = requests.get(url, json=payload, headers=headers, verify=VERIFY_SSL)
        cf_options = json.loads(request.content)
    for i in cf_options:
        if i['type'] == 'list':
            for opt in i['options']:
                if opt['id'] == idValue:
                    return opt['value']

    return None
def get_list_of_card(listId):
    return "План"

def string_value(value, board):
    if type(value) == str:
        value = get_cf_options_of_board(board['id'], value)
    if value is None:
        return None
    for (typ, val) in value.items(): pass
    if typ == 'checkbox':
        return val
    if typ == 'date':
        return val
    if typ == 'list':
        return 'list item'
    if typ == 'number':
        return val
    if typ == 'text':
        return val
    return 'unknown type of c-field'



def get_cards_in_period():
    """
    возвращает список карточек удовлетворяющих условию
    """
    boards = ['*Текучка*']
    # boards = ['*Текучка*', 'Архив']
    cards = []
    for name in boards:
        brd = get_board_by_name(name)
        custom_fields = get_custom_fields(brd)

        for crd in api.boards.get_card_filter(board_id=brd['id'], filter='open'):
            crddate = cardDate(crd)
            if crddate > margins['end'] or crddate < margins['beg']:
                continue
            log.debug(f'Обрабатывается карточка № {crd["idShort"]}: {crd["name"][:30]} (id=`{crd["id"]}`)')
            card = {
                 'date': crddate
                ,'name': crd['name']
                ,'desc': crd['desc'] if len(crd['desc'])<194 else crd['desc'][:190]+'...'
                ,'bord': brd['name']
                ,'link': crd['shortUrl']
                ,'list': api.cards.get_list(crd['id'])['name']
            }
            for cf_name, dict_cf in custom_fields.items():
                cf_value = get_custom_field_value(crd['id'], dict_cf['id'])
                value_to_add_to_dict = { cf_name: string_value(cf_value, brd) }
                card.update( value_to_add_to_dict )
            cards.append(card)
        return cards

def report():
    set_period_by_name()
    cards_list = get_cards_in_period()
    log.info(f'Формируется отчет из {len(cards_list)} карточек')
    # pp(cards_list)
    print('Дата', 'Список', "Задача", "Описание", "Доска", "Номер", "Автор", "Раздел", "Ссылка", sep='\t')
    for card in sorted(cards_list, key=lambda x: x['date']):
        _name = re.sub("^\s+|\t|\n|\r|\s+$", '', card['name'])
        _desc = re.sub("^\s+|\t|\n|\r|\s+$", '', card['desc'])
        print(card['date'].strftime("%d-%m-%y %H:%M:%S"), card['list'], _name, _desc, card['bord'], card['id'], card['Автор'], card['≡'], card['link'], sep='\t')
    

init()
report()


# ==============================================
