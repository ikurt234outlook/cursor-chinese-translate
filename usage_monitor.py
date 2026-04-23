# -*- coding: utf-8 -*-
"""
用量监控模块 - 负责获取和显示 Cursor 用量数据
"""

import datetime
import json
import os
import platform
import re
import sqlite3
import sys
import urllib.request

CURRENT_PLATFORM = platform.system().lower()

# 路径配置（区分 win/mac/linux）
if CURRENT_PLATFORM == 'windows':
    DEFAULT_CURSOR_USER_DATA_PATH = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "Cursor"
    )
elif CURRENT_PLATFORM == 'darwin':  # macOS
    DEFAULT_CURSOR_USER_DATA_PATH = os.path.expanduser("~/Library/Application Support/Cursor")
elif CURRENT_PLATFORM == 'linux':
    DEFAULT_CURSOR_USER_DATA_PATH = os.path.expanduser("~/.cursor")
else:
    DEFAULT_CURSOR_USER_DATA_PATH = os.path.expanduser("~/.cursor")

STATE_DB_RELATIVE_PATH = os.path.join("User", "globalStorage", "state.vscdb")
ACCESS_TOKEN_KEY = "cursorAuth/accessToken"
EMAIL_KEY = "cursorAuth/cachedEmail"

API_USAGE = "https://api2.cursor.sh/auth/usage"
API_USAGE_SUMMARY = "https://www.cursor.com/api/usage-summary"

# macOS 的安装路径已经包含 resources/app，所以只需 out/... 部分
if CURRENT_PLATFORM == 'darwin':
    WORKBENCH_RELATIVE_DIR = os.path.join("out", "vs", "code", "electron-sandbox", "workbench")
else:
    WORKBENCH_RELATIVE_DIR = os.path.join("resources", "app", "out", "vs", "code", "electron-sandbox", "workbench")
WORKBENCH_HTML_NAME = "workbench.html"
USAGE_JS_NAME = "cursor_usage.js"
USAGE_INJECTION_MARKER = "<!-- CURSOR_USAGE_INJECTION -->"


def get_workbench_dir(cursor_install_path):
    """获取 workbench 目录完整路径"""
    return os.path.join(cursor_install_path, WORKBENCH_RELATIVE_DIR)


def get_workbench_html_path(cursor_install_path):
    """获取 workbench.html 完整路径"""
    return os.path.join(get_workbench_dir(cursor_install_path), WORKBENCH_HTML_NAME)


def get_usage_js_path(cursor_install_path):
    """获取用量监控 JS 文件完整路径"""
    return os.path.join(get_workbench_dir(cursor_install_path), USAGE_JS_NAME)


def auto_detect_cursor_user_data_path():
    """自动检测 Cursor 用户数据路径"""
    default_path = DEFAULT_CURSOR_USER_DATA_PATH
    if os.path.exists(default_path):
        return default_path

    # 尝试其他常见路径
    if CURRENT_PLATFORM == 'darwin':
        common_paths = [
            os.path.expanduser("~/Library/Application Support/Cursor"),
            os.path.expanduser("~/.cursor"),
        ]
    elif CURRENT_PLATFORM == 'windows':
        common_paths = [
            os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Cursor"),
            os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Cursor"),
        ]
    else:  # linux
        common_paths = [
            os.path.expanduser("~/.cursor"),
        ]

    for path in common_paths:
        if os.path.exists(path):
            return path

    return None


def create_empty_usage_data():
    """创建空的用量数据结构"""
    return {
        "total_used": 0,
        "total_limit": 2000,
        "remaining": 2000,
        "premium_used": 0,
        "premium_limit": 500,
        "total_percent_used": 0,
        "api_percent_used": 0,
        "billing_cycle_start": "",
        "billing_cycle_end": "",
        "updated_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "plan_type": "pro",
        "is_valid": False,
        "model_details": {}
    }


def read_access_token(cursor_user_data_path=None):
    """从 Cursor 本地 state.vscdb 数据库读取访问令牌和用户邮箱"""
    if cursor_user_data_path is None:
        cursor_user_data_path = auto_detect_cursor_user_data_path()

    if cursor_user_data_path is None:
        print("[警告] 未找到 Cursor 用户数据目录")
        return None, None

    database_path = os.path.join(cursor_user_data_path, STATE_DB_RELATIVE_PATH)
    if not os.path.exists(database_path):
        print(f"[警告] 未找到 Cursor 数据库: {database_path}")
        return None, None

    try:
        connection = sqlite3.connect(database_path)
        cursor_obj = connection.cursor()

        # 读取 access token
        cursor_obj.execute("SELECT value FROM ItemTable WHERE key = ?", (ACCESS_TOKEN_KEY,))
        token_row = cursor_obj.fetchone()
        access_token = token_row[0] if token_row else None

        # 读取邮箱
        cursor_obj.execute("SELECT value FROM ItemTable WHERE key = ?", (EMAIL_KEY,))
        email_row = cursor_obj.fetchone()
        email = email_row[0] if email_row else None

        connection.close()
        return access_token, email

    except Exception as e:
        print(f"[错误] 读取数据库失败: {e}")
        return None, None


def fetch_api_usage(access_token):
    """从 API 获取用量数据"""
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        req = urllib.request.Request(API_USAGE, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except Exception as e:
        print(f"[警告] 获取 API 用量失败: {e}")
        return None


def fetch_usage_summary(access_token):
    """从 API 获取用量摘要"""
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        req = urllib.request.Request(API_USAGE_SUMMARY, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except Exception as e:
        print(f"[警告] 获取用量摘要失败: {e}")
        return None


def merge_usage_data(access_token):
    """合并多个 API 的用量数据"""
    usage_data = create_empty_usage_data()

    # 获取 API 用量
    api_usage = fetch_api_usage(access_token)
    if api_usage:
        usage_data.update({
            "total_used": api_usage.get("totalUsage", 0),
            "total_limit": api_usage.get("totalLimit", 2000),
            "remaining": api_usage.get("remaining", 2000),
            "premium_used": api_usage.get("premiumUsage", 0),
            "premium_limit": api_usage.get("premiumLimit", 500),
            "total_percent_used": api_usage.get("totalPercentUsed", 0),
            "api_percent_used": api_usage.get("apiPercentUsed", 0),
            "billing_cycle_start": api_usage.get("billingCycleStart", ""),
            "billing_cycle_end": api_usage.get("billingCycleEnd", ""),
            "plan_type": api_usage.get("planType", "pro"),
            "is_valid": True,
            "model_details": api_usage.get("modelDetails", {})
        })

    # 获取用量摘要
    usage_summary = fetch_usage_summary(access_token)
    if usage_summary:
        usage_data.update({
            "total_used": usage_summary.get("totalUsage", usage_data["total_used"]),
            "total_limit": usage_summary.get("totalLimit", usage_data["total_limit"]),
            "remaining": usage_summary.get("remaining", usage_data["remaining"]),
        })

    usage_data["updated_at"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return usage_data


def generate_usage_js(usage_data):
    """生成用量监控注入脚本"""
    usage_json = json.dumps(usage_data, ensure_ascii=False)

    js_code = f'''
(function() {{
    'use strict';

    const usageData = {usage_json};

    const usageContainerSelectors = [
        '[class*="account"]',
        '[class*="user"]',
        '[class*="profile"]',
        '[data-testid*="account"]',
        '[data-testid*="user"]'
    ];

    function formatCompactNumber(num) {{
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
        return num.toString();
    }}

    function buildModelDetailsHtml() {{
        if (!usageData.model_details) return '';

        let html = '';
        for (const [modelName, detail] of Object.entries(usageData.model_details)) {{
            html += '<div style="margin-top:4px;opacity:.85">' +
                modelName + '：' + detail.requests + ' / ' + detail.max_requests +
                '，Token ' + formatCompactNumber(detail.tokens || 0) +
                '</div>';
        }}
        return html;
    }}

    function buildUsageCardHtml() {{
        return '' +
            '<div style="font-weight:600;margin-bottom:8px">用量监控</div>' +
            '<div>总用量：' + (usageData.total_used || 0) + ' / ' + (usageData.total_limit || 0) + '</div>' +
            '<div>高级请求：' + (usageData.premium_used || 0) + ' / ' + (usageData.premium_limit || 0) + '</div>' +
            '<div>剩余次数：' + (usageData.remaining || 0) + '</div>' +
            '<div>总使用率：' + (usageData.total_percent_used || 0) + '%</div>' +
            '<div>API 使用率：' + (usageData.api_percent_used || 0) + '%</div>' +
            '<div>计费周期：' + (usageData.billing_cycle_start || '-') + ' 至 ' + (usageData.billing_cycle_end || '-') + '</div>' +
            '<div>计划类型：' + (usageData.plan_type || '-') + '</div>' +
            '<div>更新时间：' + (usageData.updated_at || '-') + '</div>' +
            buildModelDetailsHtml();
    }}

    function createUsageCardElement() {{
        const card = document.createElement('div');
        card.id = 'cursor-usage-card';
        card.style.cssText = [
            'margin-top:12px',
            'padding:12px',
            'border:1px solid var(--vscode-widget-border)',
            'border-radius:8px',
            'background:var(--vscode-editorWidget-background)',
            'color:var(--vscode-foreground)',
            'font-size:12px',
            'line-height:1.6'
        ].join(';');
        card.innerHTML = buildUsageCardHtml();
        return card;
    }}

    function findUsageContainer() {{
        for (const selector of usageContainerSelectors) {{
            const container = document.querySelector(selector);
            if (container) {{
                return container;
            }}
        }}
        return null;
    }}

    function renderUsageCard() {{
        const existingCard = document.getElementById('cursor-usage-card');
        if (existingCard && existingCard.parentElement) {{
            existingCard.replaceWith(createUsageCardElement());
            return;
        }}

        const container = findUsageContainer();
        if (!container) return;

        container.appendChild(createUsageCardElement());
    }}

    renderUsageCard();

    const observer = new MutationObserver(() => {{
        renderUsageCard();
    }});
    observer.observe(document.body, {{
        childList: true,
        subtree: true
    }});
}})();
'''
    return js_code


def write_usage_js(cursor_install_path, usage_data):
    """写入用量监控 JS 文件"""
    js_content = generate_usage_js(usage_data)
    js_path = get_usage_js_path(cursor_install_path)

    os.makedirs(os.path.dirname(js_path), exist_ok=True)
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_content)

    print(f"[写入] 用量监控脚本: {js_path}")


def has_usage_injection(cursor_install_path):
    """检测 workbench.html 中是否包含用量监控脚本引用（兼容多种变体）"""
    html_path = get_workbench_html_path(cursor_install_path)
    if not os.path.exists(html_path):
        return False

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检测多种变体（包括 ./ 前缀）
    markers = [
        USAGE_INJECTION_MARKER,
        f'src="{USAGE_JS_NAME}"',
        f"src='{USAGE_JS_NAME}'",
        f'src={USAGE_JS_NAME}',
        f'src="./{USAGE_JS_NAME}"',
        f"src='./{USAGE_JS_NAME}'",
    ]

    # 使用正则表达式匹配 ./ 前缀变体
    pattern = r'src=["\']?\./' + re.escape(USAGE_JS_NAME) + r'["\']?'
    if re.search(pattern, content):
        return True

    return any(marker in content for marker in markers)


def inject_usage_html(cursor_install_path):
    """将用量监控脚本引用注入到 workbench.html"""
    html_path = get_workbench_html_path(cursor_install_path)

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    injection = f'{USAGE_INJECTION_MARKER}\n<script src="{USAGE_JS_NAME}"></script>\n'

    if '</body>' in content:
        content = content.replace('</body>', injection + '</body>')
    else:
        content += '\n' + injection

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[注入] 已将用量监控脚本引用注入到 workbench.html")


def remove_usage_html(cursor_install_path):
    """从 workbench.html 移除用量监控脚本引用"""
    html_path = get_workbench_html_path(cursor_install_path)
    if not os.path.exists(html_path):
        return

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 移除多种变体（包括 ./ 前缀）
    patterns = [
        r'<!-- CURSOR_USAGE_INJECTION -->\s*\n?',
        r'<script src="cursor_usage\.js"></script>\s*\n?',
        r"<script src='cursor_usage\.js'></script>\s*\n?",
        r'<script src=cursor_usage\.js></script>\s*\n?',
        r'<script src=["\']?\./cursor_usage\.js["\']?"></script>\s*\n?',
    ]

    for pattern in patterns:
        content = re.sub(pattern, '', content)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[移除] 已从 workbench.html 移除用量监控脚本引用")


def get_usage(cursor_user_data_path=None):
    """获取用量数据"""
    print("\n[用量] 读取认证信息...")
    access_token, email = read_access_token(cursor_user_data_path)

    if access_token:
        print(f"[用量] 已找到令牌，邮箱: {email or '未知'}")
        print("[用量] 获取用量数据...")
        usage_data = merge_usage_data(access_token)
        return usage_data
    else:
        print("[用量] 未找到认证令牌，跳过用量获取")
        return create_empty_usage_data()


def print_usage_summary(usage_data):
    """打印用量摘要"""
    if usage_data and usage_data.get("is_valid"):
        print(f"[用量] 总用量: {usage_data['total_used']} / {usage_data['total_limit']} 次")
        print(f"[用量] 高级请求: {usage_data['premium_used']} / {usage_data['premium_limit']} 次")
        print(f"[用量] 剩余: {usage_data['remaining']} 次")
        if usage_data.get('billing_cycle_start'):
            print(f"[用量] 计费周期: {usage_data['billing_cycle_start']} 至 {usage_data['billing_cycle_end']}")
    else:
        print("[用量] 获取用量数据失败")


def install_usage_monitor(cursor_install_path, cursor_user_data_path=None):
    """安装用量监控功能"""
    print("\n[用量] 开始安装用量监控...")

    # 检查 workbench.html 是否存在
    html_path = get_workbench_html_path(cursor_install_path)
    if not os.path.exists(html_path):
        print(f"[错误] 未找到 workbench.html: {html_path}")
        print("[提示] 请检查 Cursor 安装路径是否正确")
        return False

    # 获取用量数据
    usage_data = get_usage(cursor_user_data_path)

    # 打印用量摘要
    print_usage_summary(usage_data)

    # 写入用量监控脚本
    write_usage_js(cursor_install_path, usage_data)

    # 注入 HTML 引用（如果尚未注入）
    if not has_usage_injection(cursor_install_path):
        inject_usage_html(cursor_install_path)
    else:
        print("[用量] 检测到已注入，跳过注入步骤")

    print("[用量] 用量监控安装成功！请重启 Cursor 以查看效果。")
    return True


def uninstall_usage_monitor(cursor_install_path):
    """卸载用量监控功能（幂等）"""
    print("\n[用量] 开始卸载用量监控...")

    # 检查 workbench.html 是否存在
    html_path = get_workbench_html_path(cursor_install_path)
    if not os.path.exists(html_path):
        print("[用量] 未找到 workbench.html，跳过卸载")
        return True

    # 移除 HTML 引用
    if has_usage_injection(cursor_install_path):
        remove_usage_html(cursor_install_path)
    else:
        print("[用量] 未检测到用量监控脚本引用，跳过移除步骤")

    # 删除用量监控 JS 文件
    js_path = get_usage_js_path(cursor_install_path)
    if os.path.exists(js_path):
        os.remove(js_path)
        print(f"[删除] 已删除 {js_path}")
    else:
        print(f"[用量] 用量监控脚本不存在，跳过删除")

    print("[用量] 用量监控卸载完成！")
    return True
