from datetime import datetime
import pooler


class Localizer(object):
    def __init__(self, cursor, uid, lang):
        pool = pooler.get_pool(cursor.dbname)

        lang_o = pool.get('res.lang')
        lang_id = lang_o.search(cursor, uid, [('code', '=', lang)])[0]
        self.lang = lang_o.simple_browse(cursor, uid, lang_id)

    def amount(self, amount, digits=2, monetary=True):
        return self.lang.format('%.{}f'.format(digits), amount, monetary=monetary)

    def date(self, date_str):
        new_format = self.lang.date_format
        return datetime.strptime(date_str, "%Y-%m-%d").strftime(new_format)

    def datetime(self, datetime_str):
        new_format = "{} {}".format(self.lang.date_format, self.lang.time_format)
        return datetime.strptime(datetime_str, "%Y-%m-%d").strftime(new_format)
