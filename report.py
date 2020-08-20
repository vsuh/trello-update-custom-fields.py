#!venv/Scripts/python.exe
"""
Скрипт создает файл с отчетом по карточкам за определенный период
"""
import trello as tl
import pprint
import logging
import argparse
from auth import APIKY, TOKEN, ORGANISATION

api = tl.TrelloApi(apikey=APIKY, token=TOKEN)
MAXERRS = 5
p = pprint.PrettyPrinter(indent=4, sort_dicts=True, compact=True)
pp = p.pprint
log = logging.getLogger(__name__)
parser = argparse.ArgumentParser(add_help=True , description='Формирование отчета по карточкам trello')
REPFILE = "report.csv"
period = 'cw'

def init():
    c_handler = logging.StreamHandler()
    c_handler.setLevel(logging.DEBUG)
    c_format = logging.Formatter('%(asctime)s | %(name)s - %(levelname)s - %(message)s')
    c_handler.setFormatter(c_format)
    log.addHandler(c_handler)
    log.setLevel(logging.DEBUG)
    parser.add_argument('--period', dest='period', metavar='cw|pw|cm|pm|cy|py')
    args = parser.parse_args()
    if not args.period:
        raise SystemExit("Требуется параметр")
    else:
        period = args.period

def set_period_by_name(period, dateBeg, dateEnd):
    if period == 'cw':

def report():
    dateBeg = None
    dateEnd = None
    set_period_by_name(period, dateBeg, dateEnd)
    pass

init()
report()