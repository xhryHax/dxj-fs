
from __future__ import annotations

import json
import time
from typing import Any

from interface.data.redisInteraction import RedislInteraction
from interface.tools.globalTools import ConfigObject, loadConfig



NETWORK_DOMAIN_REDIS_DB   : int = 1
ALLOW_IP_KEY              : str = 'allowIp'



def isIpAllowed(clientIp: str, rules: list[str] | None) -> bool:
    '''
    判断客户端 IP 是否命中可访问域白名单规则

    Args:
        clientIp: 客户端 IP 地址
        rules: 白名单规则列表，为 None 时表示读取失败或未初始化，拒绝

    Returns:
        bool: 命中放行规则返回 True，否则返回 False
    '''
    if rules is None:
        return False
    for rule in rules:
        if not isinstance(rule, str):
            continue
        if rule == '' or rule == '*':
            return True
        if rule.endswith('*'):
            if clientIp.startswith(rule[:-1]):
                return True
        elif clientIp == rule:
            return True
    return False



def isValidNetworkDomain(value: str) -> bool:
    '''
    校验网络域表达式是否合法

    Args:
        value: 网络域表达式，支持空串、星号、IPv4 精确地址与网段通配

    Returns:
        bool: 表达式合法返回 True，否则返回 False
    '''
    if value == '' or value == '*':
        return True
    if value.endswith('*'):
        prefix: str = value[:-1]
        if not prefix.endswith('.'):
            return False
        segments: list[str] = prefix[:-1].split('.')
    else:
        segments = value.split('.')
    if not 1 <= len(segments) <= 4:
        return False
    for segment in segments:
        if not segment.isdigit() or not 0 <= int(segment) <= 255:
            return False
    return True



class NetworkDomainManager:
    '''
    网络域白名单管理单例
    ~~~
    负责 Redis 1 号数据库连接、白名单缓存与惰性刷新、配置同步与白名单读写，
    作为公共层独立于任何微服务，供中间件与 system-service 单向依赖
    '''

    def __init__(self) -> None:
        configObject: ConfigObject = loadConfig()
        self._updateInterval: int = configObject.networkDomain.update
        self._redis: RedislInteraction | None = None
        self._allowIpList: list[str] | None = None
        self._lastRefreshTime: float = 0.0


    async def initialize(self) -> None:
        '''
        初始化 Redis 1 号数据库连接并加载一次白名单缓存

        供应用启动阶段调用，Redis 不可用时记录警告并以放行模式继续运行

        Returns:
            None: 无返回值
        '''
        configObject: ConfigObject = loadConfig()
        self._redis = RedislInteraction(
            host=configObject.redis.host,
            port=configObject.redis.port,
            db=NETWORK_DOMAIN_REDIS_DB,
            password=configObject.redis.pw
        )
        try:
            await self._redis.initialize()
            await self._refresh()
        except Exception:
            print('网络域白名单初始化失败，中间件将以放行模式运行')


    async def close(self) -> None:
        '''
        关闭 Redis 1 号数据库连接

        供应用退出阶段调用

        Returns:
            None: 无返回值
        '''
        if self._redis is not None:
            await self._redis.close()
            self._redis = None


    async def _refresh(self) -> None:
        '''
        从 Redis 1 号数据库重新拉取白名单并更新缓存

        Returns:
            None: 无返回值
        '''
        if self._redis is None:
            return
        rawValue: str | None = await self._redis.read(ALLOW_IP_KEY)
        if rawValue is None:
            self._allowIpList = None
        else:
            try:
                parsed: Any = json.loads(rawValue)
                if not isinstance(parsed, list):
                    self._allowIpList = None
                else:
                    self._allowIpList = [str(item) for item in parsed]
            except json.JSONDecodeError:
                self._allowIpList = None
        self._lastRefreshTime = time.monotonic()


    async def getAllowIp(self) -> list[str] | None:
        '''
        惰性获取当前白名单列表，缓存过期时自动从 Redis 刷新

        Returns:
            list[str] | None: 白名单列表；Redis 无此键或读取失败时返回 None
        '''
        if self._redis is None:
            return self._allowIpList
        now: float = time.monotonic()
        if self._lastRefreshTime == 0.0 or now - self._lastRefreshTime >= self._updateInterval:
            try:
                await self._refresh()
            except Exception:
                print('刷新网络域白名单失败，保留上次缓存结果')
        return self._allowIpList


    async def setAllowIp(self, allowIp: list[str]) -> bool:
        '''
        将白名单整体覆盖写入 Redis 并同步更新本地缓存

        Args:
            allowIp: 新的白名单列表

        Returns:
            bool: 写入成功返回 True，否则返回 False
        '''
        if self._redis is None:
            return False
        serialized: str = json.dumps(allowIp, ensure_ascii=False)
        written: bool = await self._redis.write(ALLOW_IP_KEY, serialized)
        if written:
            self._allowIpList = allowIp
            self._lastRefreshTime = time.monotonic()
        return written


    async def syncFromConfig(self) -> bool:
        '''
        将 serviceConfig.json 中 NetworkDomain.allowIp 覆盖写入 Redis

        供 system-service 启动时调用

        Returns:
            bool: 写入成功返回 True，否则返回 False
        '''
        configObject: ConfigObject = loadConfig()
        return await self.setAllowIp(configObject.networkDomain.allowIp)


    async def addAllowIp(self, value: str) -> list[str] | None:
        '''
        向白名单追加一个网络域并返回最新列表

        Args:
            value: 待追加的网络域表达式

        Returns:
            list[str] | None: 最新白名单列表；写入失败返回 None
        '''
        if self._redis is None:
            return None
        currentList: list[str] | None = await self.getAllowIp()
        mergedList: list[str] = list(currentList) if currentList is not None else []
        if value not in mergedList:
            mergedList.append(value)
            written: bool = await self.setAllowIp(mergedList)
            if not written:
                return None
        return mergedList


    async def deleteAllowIp(self, value: str) -> list[str] | None:
        '''
        从白名单移除一个网络域并返回最新列表

        Args:
            value: 待移除的网络域表达式

        Returns:
            list[str] | None: 最新白名单列表；写入失败返回 None
        '''
        if self._redis is None:
            return None
        currentList: list[str] | None = await self.getAllowIp()
        mergedList: list[str] = list(currentList) if currentList is not None else []
        if value in mergedList:
            mergedList.remove(value)
            written: bool = await self.setAllowIp(mergedList)
            if not written:
                return None
        return mergedList



networkDomainManager: NetworkDomainManager = NetworkDomainManager()
