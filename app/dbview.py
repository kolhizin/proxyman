from msilib import schema
import sqlalchemy
import threading
import logging

logger = logging.getLogger(__name__)

class DBView:

    def execute_(self, *args, **kwargs):
        try:
            res = self.conn_.execute(*args, **kwargs)
        except sqlalchemy.exc.DBAPIError as e: #What kind of exception
            logger.warning('Lost connection to DB ({}). Retrying...'.format(str(e)))
            self.conn_ = self.engine_.connect()
            res = self.conn_.execute(*args, **kwargs)
        self.conn_.commit()
        return res

    def update_proxies_stats_(self):
        update_query = """
        merge {schema}.proxies src
        using (select proxy_id, sum(flg_success) as cnt_good, count(*) as cnt_total
            from {schema}.log where status_dt > current_timestamp::DATE - 1) AS upd
        on src.proxy_id=upd.proxy_id
        when matched update set priority = 0.5 * priority + 0.5 * cnt_good / cnt_total, last_update=current_timestamp, last_good = cnt_good, last_bad=cnt_total - cnt_good
        """.format(self.schema_)
        try:
            logger.info('Running update-proxies query')
            with self.engine_.connect() as conn:
                conn.execute(update_query)
                conn.commit()
        except Exception as e:
            logger.error('Failed to update proxies stats: {}'.format(str(e)))
        else:
            logger.info('Finished update-proxies query')

    def update_local_proxies_(self, mult_factor=1):
        query = """
        select proxy_id, url, kind
        from (
            select proxy_id, url, kind, random() * priority as rnd_priority, random() as rnd
            from {schema}.proxies
            where enabled > 0
        ) t where rnd_priority > 0 order by rnd
        """.format(schema=self.schema_)
        logger.info('Updating list of local proxies...')
        tmp = self.execute_(query).fetch_all()
        logger.info('Read {} proxies from DB.'.format(len(tmp)))
        if self.update_thread_.is_alive():
            logger.warning('Can not start proxies update thread, because it is still alive!')
        else:
            logger.info('Starting proxies update thread!')
            self.update_thread_.start()
        self.proxies_ = tmp * mult_factor

    def create_tables_(self):
        query = """
        CREATE TABLE IF NOT EXISTS {schema}.proxies (
            proxy_id        SERIAL PRIMARY KEY,
            url             VARCHAR(255) NOT NULL,
            kind            CHAR(32),
            enabled         INTEGER,
            priority        REAL,
            last_good       INTEGER,
            last_bad        INTEGER,
            last_update     TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS {schema}.log (
            proxy_id        BIGINT NOT NULL,
            status_dt       TIMESTAMP NOT NULL,
            flg_success     INTEGER NOT NULL,
            duration        REAL NOT NULL,
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
        self.conn_ = self.engine_.connect()
        self.mult_factor_ = mult_factor
        self.update_thread_ = threading.Thread(target=DBView.update_proxies_stats_, args=[self])
        self.create_tables_()

    def get_proxy(self):
        if not self.proxies_:
            self.update_local_proxies_(self.mult_factor_)
        if not self.proxies_:
            raise ValueError('Error: could not find suitable proxies! Probably should add new batch!')
        return self.proxies_.pop()

    def add_proxies(self, proxy_array):
        query = f"""
        insert into {self.schema}.proxies (url, kind, enabled, priority)
        values (:1, :2, :3, :4)
        returning proxy_id
        """
        input = [(x['url'] if type(x) is dict else x,
                    x.get('kind', 'http') if type(x) is dict else 'http', 
                    x.get('enabled', 1) if type(x) is dict else 1, 
                    x.get('priority', 1.0) if type(x) is dict else 1.0) for x in proxy_array]
        res = self.execute_(query, input).fetchall()
        return [x[0] for x in res]
    
    def set_proxy_status(self, proxy_id, enabled=1):
        query = f"""
        update {self.schema}.proxies set enabled={enabled}
        where proxy_id={proxy_id}
        """
        self.execute_(query)

    def notify_result(self, proxy_id, flg_success, duration=None, message=None):
        query = f"""
        insert into {self.schema}.log (proxy_id, status_dt, flg_success, duration, err_message)
        values ({proxy_id}, current_timestamp, {flg_success}, {duration if duration else 'NULL'}, {'"{}"'.format(message) if message else 'NULL'})
        """
        self.execute_(query)