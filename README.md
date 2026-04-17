# CursorTranslate

> 为 Cursor 设置页提供中文翻译与用量展示的轻量 Python 工具。

CursorTranslate 会读取 Cursor 本地用户数据中的认证信息，生成前端翻译脚本并注入到 Cursor 的 `workbench.html` 中，同时同步更新 `product.json` 中的校验值，用于避免修改核心文件后出现安装损坏提示。

## Features

- 翻译 Cursor 设置页中的常见英文文本
- 自动读取本地 `state.vscdb` 中的登录信息
- 获取账号总用量与高级请求用量
- 在设置页插入用量卡片
- 自动备份 `workbench.html` 与 `product.json`
- 支持重复执行，已注入时仅更新脚本和校验值
- 支持一键恢复为原始状态

## Project Structure

| 文件 | 说明 |
| --- | --- |
| `CursorTranslate.py` | 主脚本 |
| `cursor_translate_dic.txt` | 翻译词典文件 |
| `QiDong_Cursor_ZhongWen.bat` | Windows 辅助启动脚本 |
| `README.md` | 项目说明文档 |

## How It Works

执行流程如下：

1. 从 Cursor 本地数据库 `state.vscdb` 读取 `accessToken` 和邮箱
2. 调用 Cursor 接口获取用量摘要和高级请求数据
3. 读取本地翻译词典 `cursor_translate_dic.txt`
4. 生成 `cursor_hanhua.js`
5. 备份并修改 Cursor 的 `workbench.html`
6. 注入脚本引用
7. 重新计算 `workbench.html` 的 SHA256 并写回 `product.json`

## Requirements

- Python 3
- 本地已安装并登录 Cursor
- 对 Cursor 安装目录具有读写权限
- 网络可访问以下接口：
  - `https://www.cursor.com/api/usage-summary`
  - `https://api2.cursor.sh/auth/usage`

项目仅使用 Python 标准库，不依赖第三方包。

## Configuration

脚本内置了默认路径配置。

### Cursor 安装目录

- Windows: `%LocalAppData%\Programs\cursor`
- Linux: `/usr/share/cursor`
- 其他系统: `/usr/share/cursor`

### Cursor 用户数据目录

- Windows: `%AppData%\Cursor`
- Linux: `~/.cursor`
- 其他系统: `~/.cursor`

如果你的实际安装路径不同，运行时可通过 `--cursorDir="实际路径"` 指定，无需修改脚本常量。

## Quick Start

### Help

默认不带参数运行时，只会显示帮助信息，不会直接执行：

```bash
python CursorTranslate.py
```

### Apply

```bash
python CursorTranslate.py --apply
```

### Restore

```bash
python CursorTranslate.py --restore
```

恢复时会：

- 还原 `workbench.html`
- 恢复 `product.json` 的备份
- 删除生成的 `cursor_hanhua.js`

## Usage Examples

### Windows

#### 1. 使用默认命令执行

```powershell
python .\CursorTranslate.py --apply
```

恢复：

```powershell
python .\CursorTranslate.py --restore
```

#### 2. 如果你的 Cursor 安装目录不是默认值

可以直接通过命令行指定安装目录，例如：

```powershell
python .\CursorTranslate.py --apply --cursorDir="D:\Tools\cursor"
```

默认 Windows 安装目录为 `%LocalAppData%\Programs\cursor`。

#### 3. 使用 bat 辅助脚本

如果你保留了 `QiDong_Cursor_ZhongWen.bat`，也可以在 Windows 下结合它做启动前处理。

### Linux

#### 1. 直接执行

```bash
python3 ./CursorTranslate.py --apply
```

恢复：

```bash
python3 ./CursorTranslate.py --restore
```

#### 2. 如果 Cursor 安装在默认位置

默认会使用：

- 安装目录：`/usr/share/cursor`
- 用户目录：`~/.cursor`

如果脚本需要写入系统目录，可能需要使用有权限的方式运行，例如先确认文件权限、再以合适权限执行。

#### 3. 自定义安装目录示例

如果你的 Cursor 安装路径不同，可以直接在命令行指定：

```bash
python3 ./CursorTranslate.py --apply --cursorDir="/your/cursor/path"
```

## Translation Dictionary

默认词典文件为：

- `cursor_translate_dic.txt`

词典每行使用 `=>` 分隔原文和译文，例如：

```text
Settings => 设置
General => 常规
Account => 账户
```

也支持带引号的写法：

```text
"Settings" => "设置"
```

以下内容会被忽略：

- 空行
- 以 `#` 开头的行
- 以 `//` 开头的行

## Frontend Behavior After Injection

生成的 JS 脚本会在 Cursor 设置页中执行以下逻辑：

- 使用词典和正则模式翻译文本节点
- 翻译 `title`、`aria-label`、`placeholder` 等属性
- 跳过编辑器区域、输入框、代码块等不适合翻译的位置
- 监听 DOM 变化并增量处理新节点
- 在账号相关区域附近插入用量卡片

当前用量数据字段已经统一为英文 key，例如：

- `total_used`
- `total_limit`
- `remaining`
- `premium_used`
- `premium_limit`
- `total_percent_used`
- `api_percent_used`
- `billing_cycle_start`
- `billing_cycle_end`
- `updated_at`
- `plan_type`
- `is_valid`
- `model_details`

## Backup and Restore

脚本会自动生成以下备份：

- `workbench.html.bak`
- `product.json.bak`

如果需要恢复，执行：

```bash
python CursorTranslate.py --restore
```

## FAQ

### 提示找不到 `workbench.html`

说明当前 Cursor 安装目录不正确，或者 Cursor 安装位置不是默认路径。

可以优先检查：

- Windows 默认路径是否为 `%LocalAppData%\Programs\cursor`
- 你是否需要通过 `--cursorDir="实际路径"` 指定自定义安装目录

### 提示找不到翻译词典文件

请确认项目目录下存在：

- `cursor_translate_dic.txt`

并且文件名与 [CursorTranslate.py](file:///home/ericwyn/dev/python/Cursor_chinese/CursorTranslate.py) 中的 `TRANSLATION_DICTIONARY_NAME` 一致。

### 用量获取失败

可能原因：

- 当前未登录 Cursor
- 本地数据库里没有有效 token
- 网络访问 Cursor 接口失败
- token 已失效

这种情况下脚本仍然可以继续做汉化，但用量数据会为空。

### Cursor 提示安装损坏

正常情况下脚本会自动更新 `product.json` 中的校验值。

如果之前已经手动修改导致异常，可以尝试：

```bash
python CursorTranslate.py --restore
python CursorTranslate.py --apply
```

如果你的安装目录不是默认值，也可以带上 `--cursorDir`：

```bash
python CursorTranslate.py --restore --cursorDir="实际路径"
python CursorTranslate.py --apply --cursorDir="实际路径"
```

### 更新 Cursor 后汉化失效

Cursor 更新后可能覆盖 `workbench.html`，重新执行一次：

```bash
python CursorTranslate.py --apply
```

即可重新注入。

## Security Notes

- 脚本不会上传本地数据库文件
- 认证信息从本地 Cursor 数据目录读取
- 使用的是 Cursor 自身接口
- 修改前会自动备份关键文件

但本项目本质上仍然会修改 Cursor 安装目录下的文件，请自行评估风险，并在可控环境下使用。

## Development

可以使用以下命令检查脚本语法：

```bash
python -m py_compile CursorTranslate.py
```