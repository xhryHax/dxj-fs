
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import uvicorn
from fastapi import APIRouter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interface.middleware.networkDomainMiddleware import NetworkDomainMiddleware
from interface.tools.globalTools import loadConfig
from interface.tools.networkDomainManager import networkDomainManager
import service.accountService
import service.fileLogicService
import service.fileIoService
import service.systemService



@asynccontextmanager
async def lifespan(_app:FastAPI) -> AsyncGenerator[None, None]:
    '''
    管理应用生命周期中的资源初始与释放
    ~~~
    启动阶段初始化网络域白名单管理器并触发 system-service 的启动钩子，
    退出时依次调用各微服务独立提供的销毁钩子函数并释放白名单管理器资源

    Args:
        _app: FastAPI 应用实例

    Yields:
        None: 应用运行期间挂起，退出时执行各微服务的资源销毁
    '''
    await networkDomainManager.initialize()             # 初始化网络域白名单管理器（Redis db=1）
    await service.systemService.startupHook()           # system-service 启动钩子：写入网络域配置
    yield
    await networkDomainManager.close()                  # 释放网络域白名单管理器资源
    await service.accountService.shutdownHook()         # 销毁微服务 account-service
    await service.fileLogicService.shutdownHook()       # 销毁微服务 file-logic-service
    await service.fileIoService.shutdownHook()          # 销毁微服务 file-io-service
    await service.systemService.shutdownHook()          # 销毁微服务 system-service



configObject    = loadConfig()
fsApp           = FastAPI(version='1.0', lifespan=lifespan)
globalRouter    = APIRouter(prefix='/v1')

fsApp.add_middleware(
    CORSMiddleware,
    allow_origins     = configObject.cors.allowOrigins,
    allow_credentials = configObject.cors.allowCredentials,
    allow_methods     = configObject.cors.allowMethods,
    allow_headers     = configObject.cors.allowHeaders
)
fsApp.add_middleware(NetworkDomainMiddleware)                                   # 全局网络可访问域控制中间件，对 account/file-logic/file-io/system 四个微服务统一生效
globalRouter.include_router(service.accountService.accountServiceRouter)        # 注册微服务 account-service
globalRouter.include_router(service.fileLogicService.fileLogicServiceRouter)    # 注册微服务 file-logic-service
globalRouter.include_router(service.fileIoService.fileIoServiceRouter)          # 注册微服务 file-io-service
globalRouter.include_router(service.systemService.systemServiceRouter)          # 注册微服务 system-service



fsApp.include_router(globalRouter)



if __name__ == '__main__':
    uvicorn.run('main:fsApp', host=configObject.server.host, port=configObject.server.port, reload=False)






