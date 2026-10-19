
from typing import Any

import redis.asyncio as aioredis



class RedislInteraction:
    '''
    Redis 异步交互类，封装连接初始化、销毁
    ~~~
    仅提供基础操作能力，生命周期管理由上层对象决定（__init__ 为实例， close 为销毁）
    '''

    client : aioredis.Redis


    def __init__(self, host:str, port:int, db:int=0, password:str|None=None, decodeResponses:bool=True) -> None:
        '''
        decodeResponses (bool, optional): 是否自动解码响应为字符串，默认为True
        '''
        self.client = aioredis.Redis(
            host=host, port=port,
            db=db, password=password, decode_responses=decodeResponses
        )


    async def initialize(self) -> bool:
        '''
        测试Redis连接是否正常

        Returns:
            bool: 连接成功返回True，否则返回False
        '''
        return await self.client.ping() # type: ignore


    async def close(self) -> None:
        '''
        关闭Redis连接

        Returns:
            None: 无返回值
    '''
        await self.client.aclose()


    async def create(self, key:str, value:Any, ex:int|None=None) -> bool:
        '''
        创建键值对，仅在键不存在时生效

        Args:
            key (str): 键名
            value (Any): 键值
            ex (int | None, optional): 过期时间（秒），默认为None表示不过期

        Returns:
            bool: 创建成功返回 True，否则返回 False
        '''
        result = await self.client.set(key, value, ex=ex, nx=True)
        return bool(result)


    async def read(self, key:str) -> Any | None:
        '''
        读取指定键的值

        Args:
            key (str): 键名

        Returns:
            Any | None: 键对应的值；如果键不存在则返回 None
        '''
        return await self.client.get(key)


    async def write(self, key:str, value:Any, ex:int|None=None) -> bool:
        '''
        覆盖写入键值对，无论键是否存在都直接写入

        Args:
            key (str): 键名
            value (Any): 键值
            ex (int | None, optional): 过期时间（秒），默认为None表示不过期

        Returns:
            bool: 写入成功返回 True，否则返回 False
        '''
        result = await self.client.set(key, value, ex=ex)
        return bool(result)


    async def update(self, key:str, value:Any, ex:int|None=None) -> bool:
        '''
        更新键值对，仅在键已存在时生效

        Args:
            key (str): 键名
            value (Any): 新值
            ex (int | None, optional): 过期时间（秒），默认为None表示不修改过期时间

        Returns:
            bool: 更新成功返回 True，否则返回 False
        '''
        result = await self.client.set(key, value, ex=ex, xx=True)
        return bool(result)


    async def scanKeys(self, pattern:str) -> list[str]:
        '''
        遍历 Redis 中所有与指定模式匹配的键名

        Args:
            pattern (str): 键名匹配模式，支持通配符，如 'session:*'

        Returns:
            list[str]: 匹配的键名列表
        '''
        keys: list[str] = []
        async for key in self.client.scan_iter(match=pattern):
            keys.append(key)
        return keys


    async def delete(self, *keys:str) -> int:
        '''
        删除一个或多个键

        Args:
            *keys (str): 一个或多个键名

        Returns:
            int: 被删除的键的数量
        '''
        return await self.client.delete(*keys)


    async def exists(self, *keys:str) -> int:
        '''
        检查一个或多个键是否存在

        Args:
            *keys (str): 一个或多个键名

        Returns:
            int: 存在的键的数量
        '''
        return await self.client.exists(*keys)


    async def expire(self, key:str, seconds:int) -> bool:
        '''
        为指定键设置过期时间

        Args:
            key (str): 键名
            seconds (int): 过期时间（秒）

        Returns:
            bool: 设置成功返回 True，否则返回 False
        '''
        return await self.client.expire(key, seconds)





# 使用示例
'''
async def testCurd():
    client = RedislInteraction(host='192.168.178.10', port=6379, db=15, password='123456', decodeResponses=True)

    testKey = 'test:curd:key'
    await client.delete(testKey)

    createResult1 = await client.create(testKey, 'value1')
    assert createResult1 is True, '创建新键应返回 True'
    createResult2 = await client.create(testKey, 'value2')
    assert createResult2 is False, '重复创建同一键应返回 False'
    print('Create 测试通过')

    readResult = await client.read(testKey)
    assert readResult == 'value1', f'读取值应为 value1，实际为 {readResult}'
    readMissing = await client.read('non:existent:key')
    assert readMissing is None, '读取不存在的键应返回 None'

    await client.close()


import asyncio

if __name__ == '__main__':

    asyncio.run(testCurd())

'''




