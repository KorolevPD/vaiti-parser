from pprint import pprint as pp

from app.models import Vacancy
from app.storage import get

v = get(Vacancy, 1)
if v:
    pp(v[0].model_dump_json())
