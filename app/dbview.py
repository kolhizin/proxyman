import sqlalchemy
import threading
import logging

logger = logging.getLogger(__name__)

class DBView:

    def execute_(self, *args, **kwargs):
        try:
            res = self.engine_.execute(*args, **kwargs)
        except sqlalchemy.exc.DBAPIError as e: #What kind of exception
            logger.warning('Retrying query to DB due to error ({})...'.format(str(e)))
            res = self.engine_.execute(*args, **kwargs)
        return res

    def update_proxies_stats_(self):
        update_query = """
        update {schema}.proxies src
        set priority = cnt_good / cnt_total
        from (
            select proxy_id, sum(status) as cnt_good, count(*) as cnt_total
            from {schema}.log where dttm > current_timestamp::DATE - 7
            group by proxy_id
        ) stat
        where src.proxy_id=stat.proxy_id
        """.format(schema=self.schema_)
        try:
            logger.info('Running update-proxies query')
            self.engine_.execute(update_query)
        except Exception as e:
            logger.error('Failed to update proxies stats: {}'.format(str(e)))
        else:
            logger.info('Finished update-proxies query')

    def update_local_proxies_(self, mult_factor=1):
        query = """
        select proxy_id, url, kind
        from (
            select proxy_id, url, protocols, anonymous, random() * priority as rnd_priority, random() as rnd
            from {schema}.proxies
            where enabled > 0
        ) t where rnd_priority > 0 order by rnd
        """.format(schema=self.schema_)
        logger.info('Updating list of local proxies...')
        tmp = self.execute_(query).fetchall()
        logger.info('Read {} proxies from DB.'.format(len(tmp)))
        if self.update_thread_ is not None and self.update_thread_.is_alive():
            logger.warning('Can not start proxies update thread, because it is still alive!')
        else:
            logger.info('Starting proxies update thread!')
            self.update_thread_ = threading.Thread(target=DBView.update_proxies_stats_, args=[self])
            self.update_thread_.start()
        self.proxies_ = tmp * mult_factor

    def create_tables_(self):
        query = """
        CREATE TABLE IF NOT EXISTS {schema}.proxies (
            proxy_id        SERIAL PRIMARY KEY,
            url             VARCHAR(255) NOT NULL,
            protocols       VARCHAR(255) NOT NULL,
            anonymous       INTEGER,
            enabled         INTEGER,
            priority        REAL
        );
        CREATE TABLE IF NOT EXISTS {schema}.log (
            log_id          SERIAL PRIMARY KEY,
            proxy_id        BIGINT NOT NULL,
            dttm            TIMESTAMP NOT NULL,
            status          INTEGER NOT NULL,
            duration        REAL,
            err_message     VARCHAR(255)
        );
        """.format(schema=self.schema_)
        
        logger.info('Creating DB-tables for proxies...')
        try:
            self.execute_(query)
        except Exception as e:
            logger.error('Failed to create tables with exception: {}!'.format(str(e)))
            raise

    def __init__(self, conn_str, schema, mult_factor=5) -> None:
        self.conn_str_ = conn_str
        self.schema_ = schema
        self.proxies_ = []
        self.engine_ = sqlalchemy.create_engine(self.conn_str_)
        self.mult_factor_ = mult_factor
        self.update_thread_ = None
        self.create_tables_()

    def get_proxy(self):
        if not self.proxies_:
            self.update_local_proxies_(self.mult_factor_)
        if not self.proxies_:
            raise ValueError('Error: could not find suitable proxies! Probably should add new batch!')
        return self.proxies_.pop()

    def add_proxies(self, proxy_array):
        query = f"""
        insert into {self.schema_}.proxies (url, protocols, anonymous, enabled, priority)
        values (:url, :protocols, :anonymous, :enabled, :priority)
        returning proxy_id
        """
        urls = set([x[0] for x in self.execute_(f'select lower(url) from {self.schema_}.proxies').fetchall()])
        logger.debug('add_proxies: loaded {} existing urls'.format(len(urls)))
        input = [{'url': (x['url'] if type(x) is dict else x).lower(),
                  'protocols': x.get('protocols', 'http').lower() if type(x) is dict else 'http', 
                  'anonymous': int(x['anonymous']) if type(x) is dict and 'anonymous' in x else 'null', 
                  'enabled': int(x.get('enabled', 1) if type(x) is dict else 1), 
                  'priority':  x.get('priority', 1.0) if type(x) is dict else 1.0} for x in proxy_array]
        logger.debug('add_proxies: prepared {} candidates'.format(len(input)))
        input = [x for x in input if x['url'] not in urls]
        logger.debug('add_proxies: adding {} new urls'.format(len(input)))
        return [self.execute_(sqlalchemy.sql.text(query), [x]).fetchall()[0][0] for x in input] #workaround for bugs in sqlalchemy
    
    def set_proxy_status(self, proxy_id, enabled=1):
        query = f"""
        update {self.schema_}.proxies set enabled={enabled}
        where proxy_id={proxy_id}
        """
        self.execute_(query)

    def notify_result(self, proxy_id, flg_success, duration=None, message=None):
        query = f"""
        insert into {self.schema_}.log (proxy_id, dttm, status, duration, err_message)
        values ({proxy_id}, current_timestamp, {flg_success}, {duration if duration else 'NULL'}, {'"{}"'.format(message) if message else 'NULL'})
        """
        self.execute_(query)