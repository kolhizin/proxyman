import sanic
import sanic.response

from sanic import Sanic
from sanic.response import json

app = sanic.Sanic("proxy-manager-app")

@app.get('/proxy')
async def get_proxy(request):
    """
    Return random proxy satisifying criteria.
    """
    return sanic.response.json({'result': 'ok', 'data': {'kind': 'http', 'url': 'http://127.0.0.1:80/', 'proxy_id': 321}}, status=200)

@app.post('/result')
async def notify_proxy_result(request):
    """
    Notify results of requests using specified proxy.
    """
    return sanic.response.json({'result': 'ok', 'data': {}}, status=200)

@app.post('/proxy')
async def add_proxy(request):
    """
    Add new proxy to manager.
    """
    return sanic.response.json({'result': 'ok', 'data': {}}, status=200)

@app.update('/proxy')
async def update_proxy(request):
    """
    Update proxy status in manager. Can not change proxy params -- should add new.
    """
    return sanic.response.json({'result': 'ok', 'data': {}}, status=200)

if __name__ == '__main__':
    app.run()