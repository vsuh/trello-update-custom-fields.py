# see https://bitbucket.org/btubbs/trollop/src/default/
import pprint

import trollop
import pytz
import logging
import sys 
from datetime import datetime as dt, timedelta as td
pp = pprint.PrettyPrinter(indent=4)

class MyBoard:
    """описание доски с именем brdName """

    def __init__(self, brdName, logger=None):
        """Конструктор
        dsk - доска по имени brdName
        log - логгер
        cds - словарь карточек { 'num': card_data }
        """
        self.__apiKey = '3b5478b4ee39b92fea4ec7a9e1013dc6'
        self.__token = '05d7ea49830212591558f45d39b146831dfa775b84a8c7bd1512f58266c3823b'
        self.conn = trollop.TrelloConnection(self.__apiKey, self.__token)
        self.mosc = self.conn.get_organization('user08081583')
        self.dsk = None
        if logger is None:
            logger = logging.getLogger(__name__)
        self.log = logger
        self.config_log()
        for brd in self.mosc.boards:
            if brd.name == brdName:
                self.dsk = brd
                break
        if self.dsk is None:
            raise RuntimeError(f"Не нашли доску с именем '{brdName}' в аккаунте '{self.mosc.displayname}'")
        self.cds = {}
        
    def config_log(self):
        logging.basicConfig(format='%(asctime)-15s %(levelname)-8s {%(funcName)s} %(message)s'
            , level=logging.WARNING, datefmt='%d-%m-%y %H:%M:%S')
        # self.log = logging.getLogger(__name__)
        # self.log.addHandler(logging.StreamHandler(sys.stdout))

    def set_period(self, type=None, beg=None, end=None):
        if beg is None:
            self.beg = self.get_edge(type=type, edge='beg')
        else:
            self.beg = self.get_edge(edge='beg', date=beg)
        if end is None:
            self.end = self.get_edge(type=type, edge='end')
        else:
            self.end = self.get_edge(edge='end', date=end)

    def get_edge(self, edge, type='d', date=None):
        """
        возвращает дату+время границы периода
        edge - 'beg'|'end'
        type - 'd' - day |'w' - week |'m' - month |'y' - year
        date -  date in period, today if None
        """
        msk = pytz.timezone('Europe/Moscow')
        if type == 'd':
            if date is None:
                today = dt.today()
            else:
                today = date
            beg = dt(today.year, today.month, today.day,0,0,0,0)
            if edge == 'beg':
                return msk.localize(beg)
            if edge == 'end':
                end = dt(beg.year, beg.month, beg.day, 23, 59, 59, 999)
                return msk.localize(end)
        if type == 'y':
            if date is None:
                today = dt.today()
            else:
                today = date
            beg = dt(today.year, 1, 1, 0, 0, 0, 0)
            if edge == 'beg':
                return msk.localize(beg)
            if edge == 'end':
                end = dt(1+beg.year , 1, 1, 0, 0, 0, 0)
                end = end - td(days=1)
                end = dt(end.year, end.month, end.day, 23, 59, 59, 999)
                return msk.localize(end)
        if type == 'm':
            if date is None:
                today = dt.today()
            else:
                today = date
            beg = dt(today.year, today.month, 1, 0, 0, 0, 0)
            if edge == 'beg':
                return msk.localize(beg)
            if edge == 'end':
                end = dt(beg.year if beg.month<12 else 1+beg.year, beg.month+1 if beg.month<12 else 1, 1, 0, 0, 0, 0)
                end = end - td(days=1)
                end = dt(end.year, end.month, end.day, 23, 59, 59, 999)
                return msk.localize(end)
        if type == 'w':
            if date is None:
                today = dt.today()
            else:
                today = date
            weekday = dt.weekday(today) 
            ubdil = weekday + 7
            beg = today - td(days=ubdil)
            beg = dt(beg.year, beg.month, beg.day, 0, 0, 0, 0)
            if edge == 'beg':
                return msk.localize(beg)
            if edge == 'end':
                end = beg + td(days=6)
                end = dt(end.year, end.month, end.day, 23, 59, 59, 999)
                return msk.localize(end)
        return None

    def get_data_period(self, periodBeg=None, periodEnd=None, type='w'):
        """Получить данные за период. Если период не указан, за последнюю неделю
        """
        self.set_period(type=type, beg=periodBeg, end=periodEnd)
        self.log.debug(f'Получен период с {self.beg} по {self.end}')
        mm = []
        for list in self.dsk.lists:
            if list.name == 'План':
                continue
            for card in list.cards:
                cdt = self.cardDate(card)
                if cdt < self.beg or cdt > self.end:
                    continue
                crd_object = {'date': cdt
                        , 'name': card.name
                        , 'desc': card.desc
                        , 'link': card.url
                        , 'list': card.list.name
                        }
                mm.append((card._data['idShort'], crd_object))
        self.cds = dict(mm)

    def output(self):
        print('div id="ss-card-list"')
        for i in sorted(self.cds):
            v = self.cds.get(i)
            print(f"""<div class='ss-crd-line' id='line-num-{i}' url="v['link']">
                <div class='ss-crd-date'>{v['date'].strftime('%d-%m-%Y')}</div>
                <div class='ss-crd-name'>{v['name']} <ll class='ss-crd-list-name'>({v['list']})</ll></div>
                <div class='ss-crd-desc'>{v['desc']}</div>
                </div>""")
        print('</div')

    def prepare_rep(self):
        pass


    def rep(self, list):
        for i in list.cards:
            cdt = self.cardDate(i)
            print(cdt.strftime('%d-%m-%y'), i._data['idShort'], i.name, i.desc if len(i.desc)<45 else i.desc[:90]+'...')
    
    def cardDate(self, card):
        creation_time = dt.fromtimestamp(int(card._id[0:8],16))
        msk = pytz.timezone('Europe/Moscow')
        return msk.localize(creation_time)

if __name__ == "__main__":
    pass
