from argparse import ArgumentError
import fastapi
import fastapi.responses
import uvicorn
import typing
import dbview
import traceback
import logging
import sys
import argparse
import yaml
import proxies

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')

logging.info('Starting app...')

app = fastapi.FastAPI()

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", default="/etc/config.yaml", help="path to config file")
parser.add_argument("-s", "--secret", default="/run/secrets/config.secret", help="path to secret file")
args = parser.parse_args()

with open(args.config, 'r') as f:
    config = yaml.load(f, yaml.FullLoader)

logging.info('Read config: {}'.format(config))

with open(args.secret, 'r') as f:
    secret = yaml.load(f, yaml.FullLoader)

logging.info('Configuring db-connection...')
dbv = dbview.DBView(config['db']['connection-string'].format(secret['db-password']), config['db']['schema']) #TBD
logging.info('Configured db-connection')
logging.info('Refresing proxies list...')
dbv.add_proxies([{'url': url, 'protocols': protocols, 'anonymous': anonymous} for url, protocols, anonymous in proxies.gather_proxies()])
logging.info('Refreshed proxies')

@app.get('/proxy')
async def get_proxy():
    """
    Return random proxy satisifying criteria.
    """
    try:
        proxy_id, url, kind = dbv.get_proxy()
    except Exception as e:
        logging.error('Failed to get proxy: {}'.format(str(e)))
        logging.error('Traceback: {}'.format(traceback.format_exc()))
        return fastapi.responses.JSONResponse(content={'result': 'error', 'message': str(e)}, status_code=500)
    return fastapi.responses.JSONResponse(content={'result': 'ok', 'data': {'kind': kind, 'url': url, 'proxy_id': proxy_id}}, status_code=200)

@app.post('/result')
async def notify_proxy_result(proxy_id: int, status: int, payload: typing.Dict[typing.AnyStr, typing.Any] = {}):
    """
    Notify results of requests using specified proxy.
    """
    try:
        logging.debug('Adding result: {}'.format(payload))
        if status not in (0, 1):
            raise ArgumentError('Argument status should be either 0 or 1, but got {}'.format(status))
        dbv.notify_result(proxy_id, status, duration=payload.get('duration'), message=payload.get('message'))
    except Exception as e:
        logging.error('Failed to notify result: {}'.format(str(e)))
        logging.error('Traceback: {}'.format(traceback.format_exc()))
        return fastapi.responses.JSONResponse(content={'result': 'error', 'message': str(e)}, status_code=500)    
    return fastapi.responses.JSONResponse(content={'result': 'ok'}, status_code=200)

@app.post('/proxy')
async def add_proxy(payload: typing.List[typing.Any]):
    """
    Add new proxy to manager.
    """
    try:
        if not all([type(x) is dict and 'url' in x for x in payload]):
            raise ArgumentError('Argument to POST /proxy should be dict or list of dicts containing at list `url` key')        
        res = dbv.add_proxies(payload)
    except Exception as e:
        logging.error('Failed to add proxies: {}'.format(str(e)))
        logging.error('Traceback: {}'.format(traceback.format_exc()))
        return fastapi.responses.JSONResponse(content={'result': 'error', 'message': str(e)}, status_code=500)     
    return fastapi.responses.JSONResponse(content={'result': 'ok', 'data':{'proxy_id': res}}, status_code=200)

@app.patch('/proxy')
async def update_proxy(proxy_id: int, enabled: int):
    """
    Update proxy status in manager. Can not change proxy params -- should add new.
    """
    try:
        if enabled not in (0, 1):
            raise ArgumentError('Argument enabled should be either 0 or 1, but got {}'.format(enabled))
        dbv.set_proxy_status(proxy_id, enabled=enabled)
    except Exception as e:
        logging.error('Failed to update proxy: {}'.format(str(e)))
        logging.error('Traceback: {}'.format(traceback.format_exc()))
        return fastapi.responses.JSONResponse(content={'result': 'error', 'message': str(e)}, status_code=500)    
    return fastapi.responses.JSONResponse(content={'result': 'ok'}, status_code=200)

if __name__ == '__main__':
    uvicorn.run("app:app", host="0.0.0.0", port=8000, log_level="info")