# -*- coding: utf-8 -*-
"""
翻译模块 - 负责 Cursor 设置页的中文化功能
"""

import hashlib
import json
import os
import platform
import re
import shutil
import sys

CURRENT_PLATFORM = platform.system().lower()

# 路径配置（区分 win/mac/linux）
if CURRENT_PLATFORM == 'windows':
    DEFAULT_CURSOR_INSTALL_PATH = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "Programs", "cursor"
    )
elif CURRENT_PLATFORM == 'darwin':  # macOS
    DEFAULT_CURSOR_INSTALL_PATH = "/Applications/Cursor.app/Contents/Resources/app"
elif CURRENT_PLATFORM == 'linux':
    DEFAULT_CURSOR_INSTALL_PATH = "/usr/share/cursor"
else:
    DEFAULT_CURSOR_INSTALL_PATH = "/usr/share/cursor"

# macOS 的安装路径已经包含 resources/app，所以只需 out/... 部分
if CURRENT_PLATFORM == 'darwin':
    WORKBENCH_RELATIVE_DIR = os.path.join("out", "vs", "code", "electron-sandbox", "workbench")
else:
    WORKBENCH_RELATIVE_DIR = os.path.join("resources", "app", "out", "vs", "code", "electron-sandbox", "workbench")
WORKBENCH_HTML_NAME = "workbench.html"
TRANSLATION_JS_NAME = "cursor_hanhua.js"
TRANSLATION_DICTIONARY_NAME = "cursor_translate_dic.txt"
INJECTION_MARKER = "<!-- CURSOR_HANHUA_INJECTION -->"
BACKUP_SUFFIX = ".bak"

# 默认翻译词典路径
DEFAULT_DICTIONARY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), TRANSLATION_DICTIONARY_NAME)


def get_workbench_dir(cursor_install_path):
    """获取 workbench 目录完整路径"""
    return os.path.join(cursor_install_path, WORKBENCH_RELATIVE_DIR)


def get_workbench_html_path(cursor_install_path):
    """获取 workbench.html 完整路径"""
    return os.path.join(get_workbench_dir(cursor_install_path), WORKBENCH_HTML_NAME)


def get_translation_js_path(cursor_install_path):
    """获取翻译 JS 文件完整路径"""
    return os.path.join(get_workbench_dir(cursor_install_path), TRANSLATION_JS_NAME)


def get_workbench_backup_path(cursor_install_path):
    """获取 workbench.html 备份文件路径"""
    return get_workbench_html_path(cursor_install_path) + BACKUP_SUFFIX


def get_product_json_path(cursor_install_path):
    """获取 product.json 完整路径"""
    if CURRENT_PLATFORM == 'darwin':
        return os.path.join(cursor_install_path, "product.json")
    else:
        return os.path.join(cursor_install_path, "resources", "app", "product.json")


def get_product_backup_path(cursor_install_path):
    """获取 product.json 备份路径"""
    return get_product_json_path(cursor_install_path) + BACKUP_SUFFIX


def auto_detect_cursor_install_path():
    """自动检测 Cursor 安装路径"""
    default_path = DEFAULT_CURSOR_INSTALL_PATH
    if os.path.exists(default_path):
        # macOS 的 app 路径结构不同
        if CURRENT_PLATFORM == 'darwin':
            if os.path.exists(os.path.join(default_path, "out", "vs", "code", "electron-sandbox", "workbench")):
                return default_path
        else:
            if os.path.exists(os.path.join(default_path, "resources", "app")):
                return default_path

    # 尝试其他常见路径
    if CURRENT_PLATFORM == 'darwin':
        common_paths = [
            "/Applications/Cursor.app/Contents/Resources/app",
            os.path.expanduser("~/Applications/Cursor.app/Contents/Resources/app"),
        ]
    elif CURRENT_PLATFORM == 'windows':
        common_paths = [
            os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "Cursor", "resources", "app"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)"), "Cursor", "resources", "app"),
        ]
    else:  # linux
        common_paths = [
            "/usr/share/cursor",
            "/opt/cursor",
            "/usr/local/share/cursor",
        ]

    for path in common_paths:
        if os.path.exists(path):
            if CURRENT_PLATFORM == 'darwin':
                if os.path.exists(os.path.join(path, "out", "vs", "code", "electron-sandbox", "workbench")):
                    return path
            else:
                if os.path.exists(os.path.join(path, "resources", "app")):
                    return path

    return None


def auto_detect_cursor_user_data_path():
    """自动检测 Cursor 用户数据路径"""
    if CURRENT_PLATFORM == 'windows':
        default_path = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            "Cursor"
        )
    elif CURRENT_PLATFORM == 'darwin':  # macOS
        default_path = os.path.expanduser("~/Library/Application Support/Cursor")
    elif CURRENT_PLATFORM == 'linux':
        default_path = os.path.expanduser("~/.cursor")
    else:
        default_path = os.path.expanduser("~/.cursor")

    if os.path.exists(default_path):
        return default_path

    # 尝试其他常见路径
    common_paths = [
        os.path.expanduser("~/.cursor"),
    ]

    if CURRENT_PLATFORM == 'windows':
        common_paths.extend([
            os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Cursor"),
        ])

    for path in common_paths:
        if os.path.exists(path):
            return path

    return None


def read_translation_dictionary(dictionary_path=None):
    """读取翻译词典文件，返回 {原文: 译文} 字典"""
    if dictionary_path is None:
        dictionary_path = DEFAULT_DICTIONARY_PATH

    if not os.path.exists(dictionary_path):
        print(f"[错误] 未找到翻译词典文件: {dictionary_path}")
        sys.exit(1)

    translation_map = {}
    with open(dictionary_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue
            parts = line.split('=>', 1)
            if len(parts) != 2:
                continue
            source_text = parts[0].strip().strip('"')
            target_text = parts[1].strip().strip('"')
            if source_text and target_text:
                translation_map[source_text] = target_text

    return translation_map


def generate_translation_js(translation_dictionary):
    """生成翻译注入脚本"""
    dict_json = json.dumps(translation_dictionary, ensure_ascii=False, indent=2)

    js_code = f'''
(function() {{
    'use strict';

    const translationDict = {dict_json};

    function translateText(text) {{
        if (!text || typeof text !== 'string') return text;
        const trimmed = text.trim();
        if (translationDict[trimmed]) {{
            return text.replace(trimmed, translationDict[trimmed]);
        }}
        return text;
    }}

    function translateAttribute(element, attrName) {{
        const value = element.getAttribute(attrName);
        if (value) {{
            const translated = translateText(value);
            if (translated !== value) {{
                element.setAttribute(attrName, translated);
            }}
        }}
    }}

    function shouldSkipNode(node) {{
        if (!node.parentElement) return true;
        const tag = node.parentElement.tagName.toLowerCase();
        if (['script', 'style', 'code', 'pre', 'textarea', 'input'].includes(tag)) return true;
        const role = node.parentElement.getAttribute('role');
        if (role === 'textbox' || role === 'code') return true;
        return false;
    }}

    function translateTextNode(node) {{
        if (shouldSkipNode(node)) return;
        const original = node.textContent;
        if (!original || !original.trim()) return;
        const translated = translateText(original);
        if (translated !== original) {{
            node.textContent = translated;
        }}
    }}

    function translateElement(element) {{
        translateAttribute(element, 'title');
        translateAttribute(element, 'aria-label');
        translateAttribute(element, 'placeholder');
        translateAttribute(element, 'data-placeholder');
    }}

    let pendingNodes = [];
    let isTranslationScheduled = false;

    function translateTree(root) {{
        const walker = document.createTreeWalker(
            root,
            NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT,
            null,
            false
        );

        let node;
        while (node = walker.nextNode()) {{
            if (node.nodeType === Node.ELEMENT_NODE) {{
                translateElement(node);
            }} else if (node.nodeType === Node.TEXT_NODE && !shouldSkipNode(node)) {{
                translateTextNode(node);
            }}
        }}
    }}

    function enqueueNode(node) {{
        pendingNodes.push(node);
        if (!isTranslationScheduled) {{
            isTranslationScheduled = true;
            requestAnimationFrame(processPendingNodes);
        }}
    }}

    function processPendingNodes() {{
        const nodesToProcess = pendingNodes.splice(0, pendingNodes.length);
        isTranslationScheduled = false;
        for (const node of nodesToProcess) {{
            try {{
                translateTree(node);
            }} catch (error) {{}}
        }}
    }}

    function handleMutations(mutations) {{
        for (const mutation of mutations) {{
            if (mutation.type === 'childList') {{
                for (const node of mutation.addedNodes) {{
                    if (node.nodeType === Node.ELEMENT_NODE || node.nodeType === Node.TEXT_NODE) {{
                        enqueueNode(node);
                    }}
                }}
            }} else if (mutation.type === 'characterData' && mutation.target.nodeType === Node.TEXT_NODE) {{
                enqueueNode(mutation.target);
            }}
        }}
    }}

    translateTree(document.body);

    const observer = new MutationObserver(handleMutations);
    observer.observe(document.body, {{
        childList: true,
        subtree: true,
        characterData: true
    }});
}})();
'''
    return js_code


def write_translation_js(cursor_install_path, translation_dictionary):
    """写入翻译 JS 文件"""
    js_content = generate_translation_js(translation_dictionary)
    js_path = get_translation_js_path(cursor_install_path)

    os.makedirs(os.path.dirname(js_path), exist_ok=True)
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(js_content)

    print(f"[写入] 翻译脚本: {js_path}")


def has_translation_injection(cursor_install_path):
    """检测 workbench.html 中是否包含翻译脚本引用（兼容多种变体）"""
    html_path = get_workbench_html_path(cursor_install_path)
    if not os.path.exists(html_path):
        return False

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检测多种变体（包括 ./ 前缀）
    markers = [
        INJECTION_MARKER,
        f'src="{TRANSLATION_JS_NAME}"',
        f"src='{TRANSLATION_JS_NAME}'",
        f'src={TRANSLATION_JS_NAME}',
        f'src="./{TRANSLATION_JS_NAME}"',
        f"src='./{TRANSLATION_JS_NAME}'",
    ]

    # 使用正则表达式匹配 ./ 前缀变体
    pattern = r'src=["\']?\./' + re.escape(TRANSLATION_JS_NAME) + r'["\']?'
    if re.search(pattern, content):
        return True

    return any(marker in content for marker in markers)


def inject_translation_html(cursor_install_path):
    """将翻译脚本引用注入到 workbench.html"""
    html_path = get_workbench_html_path(cursor_install_path)

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    injection = f'{INJECTION_MARKER}\n<script src="{TRANSLATION_JS_NAME}"></script>\n'

    if '</body>' in content:
        content = content.replace('</body>', injection + '</body>')
    else:
        content += '\n' + injection

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[注入] 已将翻译脚本引用注入到 workbench.html")


def remove_translation_html(cursor_install_path):
    """从 workbench.html 移除翻译脚本引用"""
    html_path = get_workbench_html_path(cursor_install_path)
    if not os.path.exists(html_path):
        return

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 移除多种变体（包括 ./ 前缀）
    patterns = [
        r'<!-- CURSOR_HANHUA_INJECTION -->\s*\n?',
        r'<script src="cursor_hanhua\.js"></script>\s*\n?',
        r"<script src='cursor_hanhua\.js'></script>\s*\n?",
        r'<script src=cursor_hanhua\.js></script>\s*\n?',
        r'<script src=["\']?\./cursor_hanhua\.js["\']?"></script>\s*\n?',
    ]

    for pattern in patterns:
        content = re.sub(pattern, '', content)

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"[移除] 已从 workbench.html 移除翻译脚本引用")


def create_backup(cursor_install_path):
    """创建 workbench.html 备份"""
    html_path = get_workbench_html_path(cursor_install_path)
    backup_path = get_workbench_backup_path(cursor_install_path)

    if os.path.exists(html_path) and not os.path.exists(backup_path):
        shutil.copy2(html_path, backup_path)
        print(f"[备份] {html_path} -> {backup_path}")


def calculate_checksum(file_path):
    """计算文件的 SHA256 校验值"""
    with open(file_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def update_checksum(cursor_install_path):
    """更新 product.json 中的校验值"""
    html_path = get_workbench_html_path(cursor_install_path)
    product_json_path = get_product_json_path(cursor_install_path)

    if not os.path.exists(html_path) or not os.path.exists(product_json_path):
        return False

    # 计算 workbench.html 的 SHA256
    html_hash = calculate_checksum(html_path)

    # 读取 product.json
    with open(product_json_path, 'r', encoding='utf-8') as f:
        product_data = json.load(f)

    # 更新 checksums
    if 'checksums' not in product_data:
        product_data['checksums'] = {}

    product_data['checksums'][f'vs/code/electron-sandbox/workbench/{WORKBENCH_HTML_NAME}'] = html_hash

    # 写回 product.json
    with open(product_json_path, 'w', encoding='utf-8') as f:
        json.dump(product_data, f, indent=2, ensure_ascii=False)

    print(f"[校验] 已更新 product.json 中的校验值")
    return True


def install_translation(cursor_install_path, dictionary_path=None):
    """安装翻译功能"""
    print("\n[翻译] 开始安装翻译...")

    # 检查 workbench.html 是否存在
    html_path = get_workbench_html_path(cursor_install_path)
    if not os.path.exists(html_path):
        print(f"[错误] 未找到 workbench.html: {html_path}")
        print("[提示] 请检查 Cursor 安装路径是否正确")
        return False

    # 读取翻译词典
    print("[翻译] 读取翻译词典...")
    translation_dict = read_translation_dictionary(dictionary_path)
    print(f"[翻译] 已加载 {len(translation_dict)} 条翻译")

    # 创建备份
    print("[翻译] 创建备份...")
    create_backup(cursor_install_path)

    # 写入翻译脚本
    write_translation_js(cursor_install_path, translation_dict)

    # 注入 HTML 引用（如果尚未注入）
    if not has_translation_injection(cursor_install_path):
        inject_translation_html(cursor_install_path)
    else:
        print("[翻译] 检测到已注入，跳过注入步骤")

    # 更新校验值
    update_checksum(cursor_install_path)

    print("[翻译] 翻译安装成功！请重启 Cursor 以查看效果。")
    return True


def uninstall_translation(cursor_install_path):
    """卸载翻译功能（幂等）"""
    print("\n[翻译] 开始卸载翻译...")

    # 检查 workbench.html 是否存在
    html_path = get_workbench_html_path(cursor_install_path)
    if not os.path.exists(html_path):
        print("[翻译] 未找到 workbench.html，跳过卸载")
        return True

    # 移除 HTML 引用
    if has_translation_injection(cursor_install_path):
        remove_translation_html(cursor_install_path)
    else:
        print("[翻译] 未检测到翻译脚本引用，跳过移除步骤")

    # 删除翻译 JS 文件
    js_path = get_translation_js_path(cursor_install_path)
    if os.path.exists(js_path):
        os.remove(js_path)
        print(f"[删除] 已删除 {js_path}")
    else:
        print(f"[翻译] 翻译脚本不存在，跳过删除")

    # 更新校验值
    update_checksum(cursor_install_path)

    print("[翻译] 翻译卸载完成！")
    return True


def restore_backup(cursor_install_path):
    """恢复备份文件"""
    html_path = get_workbench_html_path(cursor_install_path)
    backup_path = get_workbench_backup_path(cursor_install_path)

    if os.path.exists(backup_path):
        shutil.copy2(backup_path, html_path)
        os.remove(backup_path)
        print(f"[恢复] workbench.html 已从备份恢复")
        return True

    print("[警告] 未找到备份文件")
    return False
