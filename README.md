# 云存储协作平台

以「组（Group）」为核心组织单位的多租户网盘 / 文件共享系统。用户注册登录后加入或创建组，在组内共享文件空间，并通过**公开页**与**指定页**对外分发内容；组管理员负责审批入组申请与页面控制，系统管理员负责全局运维与网络访问域管理。

- `server/` —— FastAPI 异步后端，以「微服务」切分为 account / file-logic / file-io / system 四个模块
- `user/` —— Vue 3 + Vite 单页应用（纯 Web，非小程序；无第三方 UI 库）

---

## 快速开始

### 1. 准备依赖服务

后端运行依赖三个外部服务，需提前启动并可达：

| 服务 | 用途 |
| --- | --- |
| MySQL | 存储账户、组、文件等元数据 |
| Redis | 存储登录会话、上传进度（业务 db=0，网络域白名单 db=1） |
| RustFS（S3 兼容对象存储） | 存储文件实体 |

1. 建库并初始化表结构，执行 `server/doc/Untitled.sql`（8 张表 + 外键约束）。
2. 启动 RustFS，并确保配置中的 bucket 可用。

### 2. 配置后端

编辑唯一配置文件 `server/config/serviceConfig.json`，按实际环境填写 MySQL / Redis / RustFS 地址、CORS 允许的来源，以及 `NetworkDomain.allowIp` 网络访问域白名单（支持 `192.168.178.*` 通配写法）。默认服务端口为 `1114`。

> 注意：网络域中间件是 **fail-closed** 的，白名单未覆盖的来源会被直接拒绝，本地联调时请记得把自己所在的网段加入白名单。

### 3. 启动后端

必须在 `server/` 目录下启动（配置文件使用相对路径读取，同时 `src/` 需在模块搜索路径上）：

```bash
cd server
python src/main.py        # 监听 0.0.0.0:1114
```

主要依赖（项目未附带 `requirements.txt`，需自行安装）：

```
fastapi  uvicorn  sqlmodel  sqlalchemy  aiomysql
redis  obstore  aioboto3  botocore  aiohttp  aiosmtplib
```

> Python 需 3.14+（代码使用了 `uuid.uuid7()`）。

### 4. 启动前端

```bash
cd user
npm install
npm run dev       # 开发服务器
npm run build     # 构建产物输出到 dist/
```

前端通过 Vite 代理转发 `/v1` 与 `/v1/io`，使 HttpOnly Cookie 与下载直链保持同源。开发时在 `user/.env` 中调整：

```ini
VITE_API_BASE_URL=/v1
VITE_API_PROXY_TARGET=http://localhost:1114
VITE_RUSTFS_GATEWAY=http://xyhraics.top
```

Node 需 20.19+ / 22.12+（Vite 8 要求）。

---

## 核心点

### 后端架构

路由统一挂载在 `/v1` 前缀下，四个模块职责清晰：

| 模块 | 职责 |
| --- | --- |
| `account-service` | 注册登录、改名改密、组列表、入组申请与审批、退组 |
| `file-logic-service` | 文件元数据与列表、回收站、存储配额、重命名改标签、公开页与指定页管理 |
| `file-io-service` | 分片上传（预上传 / 分片 PUT / 合并）、下载签名链接 |
| `system-service` | 管理员登录、在线用户、全局组与配额管理、任命组管理员、网络访问域白名单 |

分层结构为 `service`（接口层）→ `interface/work`（业务层）→ `interface/data`（数据层：MySQL / Redis / RustFS），全部为异步实现，通过 `lifespan` 钩子统一初始化与释放资源。

### 鉴权：Redis Session + HttpOnly Cookie

不使用 JWT，也不使用 `Authorization` 头。登录成功后生成随机 token 写入 Redis（`session:{token}`，TTL 3600），并通过 `httponly` Cookie 下发；前端 axios 以 `withCredentials: true` 携带，本地仅在 localStorage 缓存非敏感的用户资料。响应体可携带续签 token，实现滑动续期。

### 文件分片上传与断点续传

上传走三步：预上传获取 `uploadInfoId` → 按 `Content-Range` 随机写临时分片文件 → 合并后推送至 RustFS。Redis 记录已接收分片与进度，因此支持断点续传与进度查询。

### 下载使用预签名 URL

下载不经过应用层中转，由 RustFS 生成预签名链接，签名后替换对外域名再返回，客户端直连对象存储获取文件。

### 网络可访问域白名单

自定义中间件解析 `X-Forwarded-For` 全链路与直连 IP，逐条按通配规则校验，任一不通过即返回 403。白名单存于 Redis 并带惰性刷新，可在系统管理页动态增删。

### 其他

- 密码使用 PBKDF2-HMAC-SHA256 加盐存储，比对采用 `hmac.compare_digest` 常量时间比较
- 全局 ID 由 `uuid.uuid7()` 转 62 进制并加 `dxj` 前缀，固定 30 位
- 统一响应体 `{ code, msg, content }`，错误码分层：1xxx 参数 / 2xxx 权限 / 3xxx 业务 / 5xxx 风控
- 前端设计系统见 `user/doc/DESIGN.md`；完整接口定义见 `server/doc/API设计.md`

---

## 文档

| 文档 | 说明 |
| --- | --- |
| `server/doc/API设计.md` | 后端接口设计与错误码（前后端各一份，内容一致） |
| `server/doc/Untitled.sql` | 数据库建表脚本 |
| `server/doc/代码编写规范.txt` | 后端编码规范 |
| `user/doc/DESIGN.md` | 前端设计系统与视觉规范 |
| `user/doc/开发文档.md` | 前端功能需求清单 |
