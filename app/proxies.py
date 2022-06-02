import requests

def parse_proxynova_com(html):
    s1 = lxml.etree.fromstring(html, parser=lxml.etree.HTMLParser(recover=True))
    s2 = [x for x in s1.findall('.//table')[0].findall('.//tr')[1:] if  len(x.getchildren()) > 2]
    addrs = [re.sub('[^0-9\.]+', '', ''.join(x.getchildren()[0].itertext()).strip().replace('.write', '')) for x in s2]
    ports = [''.join(x.getchildren()[1].itertext()).strip() for x in s2]
    types = [''.join(x.getchildren()[-1].itertext()).strip() for x in s2]
    proto = ['null' for x in s2]
    return list(zip(addrs, ports, proto, types))

def parse_freeproxy_cz(html):
    s1 = lxml.etree.fromstring(html, parser=lxml.etree.HTMLParser(recover=True))
    s2 = [x for x in s1.findall('.//table')[1].findall('.//tr')[1:] if  len(x.getchildren()) > 2]
    addrs = [base64.b64decode(''.join(x.getchildren()[0].itertext()).strip().replace('document.write(Base64.decode("', '').replace('"))', '')).decode('utf-8') for x in s2]
    ports = [''.join(x.getchildren()[1].itertext()).strip() for x in s2]
    proto = [''.join(x.getchildren()[2].itertext()).strip() for x in s2]
    types = [''.join(x.getchildren()[6].itertext()).strip() for x in s2]
    return list(zip(addrs, ports, proto, types))

def parse_hidemy_name(html):
    s1 = lxml.etree.fromstring(html, parser=lxml.etree.HTMLParser(recover=True))
    s2 = [x for x in s1.findall('.//table')[0].findall('.//tr')[1:] if  len(x.getchildren()) > 2]
    addrs = [''.join(x.getchildren()[0].itertext()).strip() for x in s2]
    ports = [''.join(x.getchildren()[1].itertext()).strip() for x in s2]
    proto = [''.join(x.getchildren()[4].itertext()).strip() for x in s2]
    types = [''.join(x.getchildren()[5].itertext()).strip() for x in s2]
    return list(zip(addrs, ports, proto, types))

def get_proxies_hidemy_name():
    url_template = 'https://hidemy.name/ru/proxy-list/?anon=234&start={}#list'
    headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36' }
    res = []
    offset = 0
    while True:
        try:
            response = requests.get(url_template.format(offset), headers=headers)
            if response.status_code != 200:
                break
            tmp = parse_hidemy_name(response.text)
            if tmp is None or len(tmp) == 0:
                break
        except:
            break
        offset += 64
        res += tmp
        
    return [('{}:{}'.format(x[0], x[1]), x[2].lower(), 'высокая' in x[3].lower()) for x in res]

def gather_proxies():
    proxies = []
    proxies += get_proxies_hidemy_name()
    return proxies