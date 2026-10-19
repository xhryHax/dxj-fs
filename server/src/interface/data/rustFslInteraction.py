

import hashlib
import json

import aioboto3                                 # type: ignore
import aiohttp
import botocore                                 # type: ignore
import obstore
import datetime
from obstore.store import S3Store
from botocore.auth import SigV4Auth             # type: ignore
from botocore.awsrequest import AWSRequest      # type: ignore
from botocore.credentials import Credentials    # type: ignore



class RustFsInteraction:
    '''
    RustFS 异步交互类
    ~~~
    仅提供基础操作能力，无需管理任何生命周期
    '''

    _endpointUrl    : str
    _accessKey      : str
    _secretKey      : str
    _region         : str
    _session        : aioboto3.Session = aioboto3.Session()


    def __init__(self, endpointUrl:str, accessKey:str, secretKey:str, region:str) -> None:
        self._endpointUrl   = endpointUrl
        self._accessKey     = accessKey
        self._secretKey     = secretKey
        self._region        = region


    def _signRequest(self, request:AWSRequest) -> None:
        '''
        使用AWS签名V4为请求签名
        '''
        credentials = Credentials(access_key=self._accessKey, secret_key=self._secretKey,)
        signer = SigV4Auth(credentials, 's3', self._region)
        request.headers['X-Amz-Date'] = datetime.datetime.now().strftime('%Y%m%dT%H%M%SZ')
        body = request.body                                         # type: ignore
        if isinstance(body, str): body = body.encode('utf-8')
        contentHash = hashlib.sha256(body or b'').hexdigest()       # type: ignore
        request.headers['X-Amz-Content-SHA256'] = contentHash
        signer.add_auth(request)                                    # type: ignore


    def generateStore(self, bucket:str, otherDomainName:str|None=None) -> S3Store:
        '''
        生成一个 S3Store 对象以供使用

        Args:
            bucket (str): 存储桶名

        Returns:
            S3Store: 对应的 S3Store 对象
        '''
        return S3Store(
            bucket              = bucket,
            endpoint            = self._endpointUrl if otherDomainName is None else otherDomainName,
            access_key_id       = self._accessKey,
            secret_access_key   = self._secretKey,
            region              = self._region,
            allow_http          = True, # type: ignore
        )


    async def put(self, store:S3Store, targetPath:str, localPath:str) -> bool:
        '''
        上传文件到指定位置

        Args:
            store (S3Store): 存储桶名
            targetPath (str): 实际上传到的路径（包含文件名）
            localPath (str): 文件数据所在位置路径（此设备上）

        Returns:
            bool: 是否上传成功
        '''
        try:
            with open(localPath, mode='rb') as f:
                await obstore.put_async(store, targetPath, f)   # 此操作幂等
            return True
        except:
            return False


    async def delete(self, store:S3Store, targetPath:str) -> bool:
        '''
        删除指定位置的文件

        Args:
            store (S3Store): 存储桶名
            targetPath (str): 桶内文件的路径（包含文件名）

        Returns:
            bool: 是否删除成功
        '''
        try:
            await obstore.delete_async(store, targetPath)   # 此操作幂等
            return True
        except:
            return False


    async def createBucket(self, bucketName:str) -> bool:
        '''
        创建存储桶

        Args:
            bucketName (str): 存储桶名（注意，受限 S3 协议，仅限小写英文字母和连字符和数字）

        Returns:
            None: 无返回值
        '''
        try:
            async with self._session.client(service_name='s3', endpoint_url=self._endpointUrl, aws_access_key_id=self._accessKey,       # type: ignore
                                            aws_secret_access_key=self._secretKey, region_name=self._region, use_ssl=False) as client:  # type: ignore
                await client.create_bucket(Bucket=bucketName)                           # type: ignore  此操作是幂等的
            return True
        except:
            return False


    async def setBucketQuota(self, bucketName:str, quotaBytes:int) -> bool:
        '''
        设置对应存储桶的配额

        Args:
            bucketName (str): 存储桶名（注意，受限 S3 协议，仅限小写英文字母和连字符）
            quotaBytes (int): 上限字节数

        Returns:
            bool: 是否设置成功
        '''
        url = f'{self._endpointUrl}/rustfs/admin/v3/quota/{bucketName}'
        body = f'''{{"quota": {quotaBytes}}}'''
        headers = {'Content-Type': 'application/json'}
        request = AWSRequest(
            method='PUT',
            url=url,
            data=body,
            headers=headers,
        )
        self._signRequest(request)
        signedHeaders = dict(request.headers)

        async with aiohttp.ClientSession() as session:
            async with session.put(url, data=body, headers=signedHeaders) as resp:  # 此操作幂等
                return resp.status == 200


    async def getBucketQuota(self, bucketName:str) -> tuple[int, int] | None:
        '''
        获取对应存储桶的配额信息和占用信息

        Args:
            bucketName (str): 存储桶名（注意，受限 S3 协议，仅限小写英文字母和连字符）

        Returns:
            tuple[int, int]: (配额大小, 已使用大小，配额大小为 None 表示未进行配额)
            None: 获取失败
        '''
        url = f'{self._endpointUrl}/rustfs/admin/v3/quota/{bucketName}'
        request = AWSRequest(method='GET', url=url)
        self._signRequest(request)
        signedHeaders = dict(request.headers)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=signedHeaders) as resp:
                    if resp.status == 200:
                        body = await resp.read()
                        data = json.loads(body)
                        return data['quota'], data['size']
        except:
            return None


    async def deleteBucket(self, bucketName:str) -> bool:
        '''
        删除指定的桶

        Args:
            bucketName (str): 存储桶名（注意，受限 S3 协议，仅限小写英文字母和连字符）

        Returns:
            bool: 是删除成功
        '''
        try:
            async with self._session.client(service_name='s3', endpoint_url=self._endpointUrl, aws_access_key_id=self._accessKey,       # type: ignore
                                            aws_secret_access_key=self._secretKey, region_name=self._region, use_ssl=False) as client:  # type: ignore
                    await client.delete_bucket(Bucket=bucketName)                                                                       # type: ignore
                    return True
        except botocore.exceptions.ClientError as e:                # type: ignore
            error_code = e.response.get('Error', {}).get('Code')    # type: ignore
            if error_code == 'NoSuchBucket':
                return True                                         # 桶不存在，视为删除成功（幂等）
            elif error_code == 'BucketNotEmpty':
                return False
            else:
                return False
        except:
            return False


    async def getGlobalQuota(self) -> dict[str, int]:
        '''
        获取 RustFS 整体可用空间和已用空间

        Returns:
            dict[str, int]: {'totalCapacity' : 整体可用空间大小, 'totalUsed' : 已用空间大小}
        '''
        url = f'{self._endpointUrl}/rustfs/admin/v3/datausageinfo'
        request = AWSRequest(method='GET', url=url)
        self._signRequest(request)
        signedHeaders = dict(request.headers)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=signedHeaders) as resp:
                resp.raise_for_status()
                data = await resp.json()

        totalCapacity   = data.get('total_capacity', 0)
        totalUsed       = data.get('total_used_capacity', 0)
        
        return {'totalCapacity' : totalCapacity, 'totalUsed' : totalUsed}



# 使用示例
'''
async def run():
    ri = RustFsInteraction("http://192.168.178.10:9000", "rustfsadmin", "rustfsadmin",
    "us-east-1")

    # print('创建存储桶')
    # # 创建存储桶
    # print(await ri.createBucket('testbucket'))

    # print('获取配额信息')
    # # 获取桶配额
    # print(await ri.getBucketQuota('testbucket'))

    # print('进行桶配额')
    # # 进行桶配额
    # print(await ri.setBucketQuota('testbucket', 10000))

    # print('获取配额信息')
    # # 获取桶配额
    # print(await ri.getBucketQuota('testbucket'))

    # print('上传文件')
    # # 上传文件
    # await ri.put(ri.generateStore('testbucket'), '测试文件', 'C:\\Users\\LENOVO\\Desktop\\dxj\0.2\\achieve\\server\\src\\main.py')

    # print('获取配额信息')
    # # 获取桶配额
    # print(await ri.getBucketQuota('testbucket'))

    # print('删除文件')
    # # 删除文件
    # print(await ri.delete(ri.generateStore('testbucket'), '测试文件'))

    # print('获取配额信息')
    # # 获取桶配额
    # print(await ri.getBucketQuota('testbucket'))

    # print('删除桶')
    # # 删除桶
    # print(await ri.deleteBucket('testbucket'))

    await ri.getGlobalQuota()

if __name__ == '__main__':
    import asyncio
    asyncio.run(run())

'''




