
from __future__ import annotations


from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from interface.tools.networkDomainManager import isIpAllowed, networkDomainManager



class NetworkDomainMiddleware(BaseHTTPMiddleware):
    '''
    网络可访问域控制中间件
    ~~~
    从 Redis 1 号数据库白名单校验请求链路上的全部 IP，不在可访问域内的请求直接返回 HTTP 403，
    属于网关公共层，独立于任何微服务
    '''

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        '''
        请求分发拦截逻辑，校验客户端真实 IP 与全部代理 IP 是否在可访问域白名单内

        真实客户端 IP 取自 X-Forwarded-For 标头中的首个地址（存在代理转发时），
        否则取 TCP 直连对端地址；请求链路上的所有代理均须在白名单内，
        任一 IP 无法识别或不在白名单时直接拒绝（fail-closed）

        Args:
            request: FastAPI 请求对象
            call_next: 下游处理函数

        Returns:
            Response: 校验通过返回下游响应，否则返回 403 JSON 响应
        '''
        if request.client is None or request.client.host == '':
            print('无法识别请求对端 IP，拒绝请求 %s', request.url.path)
            return JSONResponse(status_code=403, content={'code': 403, 'msg': '所在的 ip 不可进行访问', 'content': None})
        directIp: str = request.client.host
        xffValue: str | None = request.headers.get('X-Forwarded-For')
        ipChain: list[str] = [item.strip() for item in xffValue.split(',') if item.strip()] if xffValue is not None else []
        ipChain.append(directIp)
        clientIp: str = ipChain[0]
        allowIpList: list[str] | None = await networkDomainManager.getAllowIp()
        for ip in ipChain:
            if not isIpAllowed(ip, allowIpList):
                print('拒绝来自 %s 的访问（链路 %s），不在可访问域内', clientIp, ipChain)
                return JSONResponse(status_code=403, content={'code': 403, 'msg': '所在的 ip 不可进行访问', 'content': None})
        return await call_next(request)
