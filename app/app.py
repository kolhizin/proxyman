from argparse import ArgumentError
import sanic
import sanic.response
import dbview
import traceback
import logging
import sys

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%dT%H-%M-%S')

app = sanic.Sanic("proxy-manager-app")
dbv = dbview.DBView('connstr', 'schema') #TBD

@app.get('/proxy')
async def get_proxy(request):
    """
    Return random proxy satisifying criteria.
    """
    try:
        proxy_id, url, kind = dbv.get_proxy()
    except Exception as e:
        logging.error('Failed to get proxy: {}'.format(str(e)))
        logging.error('Traceback: {}'.format(traceback.format_exc()))
        return sanic.response.json({'result': 'error', 'message': str(e)}, status=500)    
    return sanic.response.json({'result': 'ok', 'data': {'kind': kind, 'url': url, 'proxy_id': proxy_id}}, status=200)

@app.post('/result')
async def notify_proxy_result(request):
    """
    Notify results of requests using specified proxy.
    """
    try:
        proxy_id = request.args['proxy_id']
        flg_success = int(request.args['flg_success'])
        if flg_success not in (0, 1):
            raise ArgumentError('Argument flg_success should be either 0 or 1, but got {}'.format(flg_success))
        dbv.notify_result(proxy_id, flg_success, duration=request.json.get('duration'), message=request.json.get('message'))
    except Exception as e:
        logging.error('Failed to notify result: {}'.format(str(e)))
        logging.error('Traceback: {}'.format(traceback.format_exc()))
        return sanic.response.json({'result': 'error', 'message': str(e)}, status=500)    
    return sanic.response.json({'result': 'ok'}, status=200)

@app.post('/proxy')
async def add_proxy(request):
    """
    Add new proxy to manager.
    """
    try:
        input = request.json
        if type(input) is dict:
            input = [input]
        if not all([type(x) is dict and 'url' in x for x in input]):
            raise ArgumentError('Argument to POST /proxy should be dict or list of dicts containing at list `url` key')
        res = dbv.add_proxies(input)
    except Exception as e:
        logging.error('Failed to add proxies: {}'.format(str(e)))
        logging.error('Traceback: {}'.format(traceback.format_exc()))
        return sanic.response.json({'result': 'error', 'message': str(e)}, status=500)     
    return sanic.response.json({'result': 'ok', 'data':{'proxy_id': res}}, status=200)

@app.update('/proxy')
async def update_proxy(request):
    """
    Update proxy status in manager. Can not change proxy params -- should add new.
    """
    try:
        proxy_id = request.args['proxy_id']
        enabled = int(request.args['enabled'])
        if enabled not in (0, 1):
            raise ArgumentError('Argument enabled should be either 0 or 1, but got {}'.format(enabled))
        dbv.set_proxy_status(proxy_id, enabled=enabled)
    except Exception as e:
        logging.error('Failed to update proxy: {}'.format(str(e)))
        logging.error('Traceback: {}'.format(traceback.format_exc()))
        return sanic.response.json({'result': 'error', 'message': str(e)}, status=500)    
    return sanic.response.json({'result': 'ok'}, status=200)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)