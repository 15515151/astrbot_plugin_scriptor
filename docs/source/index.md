# Scriptor API Documentation

## 项目概述

Scriptor (灵笔司书) 是一个 AI 管家记忆系统，为家用 NAS 环境优化。

## 核心模块

### Core 模块

- [memory_manager](core/memory_manager.html) - 记忆管理
- [search_engine](core/search_engine.html) - 检索引擎
- [identity_manager](core/identity_manager.html) - 身份管理
- [group_manager](core/group_manager.html) - 群体管理
- [compactor](core/compactor.html) - 记忆压缩
- [config_pydantic](core/config_pydantic.html) - 配置管理

### Tools 模块

- [security/encryption](tools/security/encryption.html) - 加密工具
- [security/sanitizer](tools/security/sanitizer.html) - 安全工具

### Hooks 模块

- [hooks/manager](hooks/manager.html) - Hook 管理

## API 端点

### 身份认证

所有 API 端点都需要在请求头中包含 `X-API-Key` 进行身份验证。

```bash
curl -H "X-API-Key: your_api_key" https://your-server/api/status
```

### CSRF 保护

对于状态修改操作 (POST, PUT, DELETE)，需要在请求头中包含 `X-CSRF-Token`。

```bash
# 获取 CSRF Token
curl -H "X-API-Key: your_api_key" https://your-server/api/csrf/token

# 使用 Token
curl -X POST \
  -H "X-API-Key: your_api_key" \
  -H "X-CSRF-Token: your_csrf_token" \
  -H "Content-Type: application/json" \
  https://your-server/api/knowledge
```

### 端点列表

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/status | 获取系统状态 |
| GET | /api/profiles | 获取所有用户画像 |
| GET | /api/profiles/{uid} | 获取用户详情 |
| GET | /api/profiles/{uid}/memory | 获取用户记忆列表 |
| PUT | /api/profiles/{uid}/memory/{filename} | 更新用户记忆 |
| GET | /api/groups | 获取所有群体 |
| GET | /api/groups/{group_id} | 获取群体详情 |
| POST | /api/csrf/token | 获取 CSRF Token |
| POST | /api/maintenance/reindex | 触发重新索引 |
| GET | /api/knowledge | 获取知识库 |
| POST | /api/knowledge | 创建知识条目 |
| DELETE | /api/knowledge/{item_id} | 删除知识条目 |
| POST | /api/export | 导出数据 |
| GET | /api/config | 获取配置 |

## 权限系统

Scriptor 使用细粒度权限控制系统：

| 角色 | 权限 |
|------|------|
| Guest | 只能查看公开内容 |
| User | 基本操作（查看、搜索、记录） |
| Member | 群组成员 |
| Moderator | 群组版主 |
| Admin | 管理员（调试、备份、删除） |
| Owner | 群体所有者 |

## 索引

- [genindex](genindex.html)
- [modindex](modindex.html)
