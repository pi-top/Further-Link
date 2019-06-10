from urllib import request, parse

from support import logger
from support.base.beanret import BeanRet


def http(url, data, method="GET"):
    pass


def get(url):
    logger.info(url)
    response = request.urlopen(url)
    result = response.read().decode(encoding='utf-8')
    logger.info(result)
    if result != None:
        beanret = BeanRet()
        beanret.toObj(result)
        return beanret


def post(url, data=None):
    try:
        logger.info(url)
        postdata = parse.urlencode(data).encode('utf-8')
        req = request.Request(url, data=postdata, method="POST")
        response = request.urlopen(req)
        result = response.read().decode(encoding='utf-8')
        logger.info(result)
        beanret = BeanRet().toObj(result)
        return beanret
    except:
        return BeanRet(success=False)
