"""需求类型枚举与 commit 标题模板。

格式已定稿（设计文档 v1.2）：{type}: {title} --story={no_seq}
例子：feat: 支持导出月报 --story=1024
模板只在后端这一处，前端与接口都拿拼好的成品，避免两边拼出不同结果。
"""

import re

COMMIT_TITLE_TEMPLATE = "{type}: {title} --story={no_seq}"

STORY_TYPES = [
    ("feat", "新功能"),
    ("fix", "缺陷修复"),
    ("docs", "文档"),
    ("refactor", "重构"),
    ("perf", "性能"),
    ("test", "测试"),
    ("chore", "杂务"),
]
STORY_TYPE_VALUES = [value for value, _ in STORY_TYPES]

# 标题会被粘进 git commit -m "..."，清掉会截断命令或被 shell 展开的字符
_UNSAFE_CHARS = (
    ("\\", ""),
    ('"', "'"),
    ("`", ""),
    ("$", ""),
    ("\r", " "),
    ("\n", " "),
    ("\t", " "),
)


def sanitize_title(value):
    text = (value or "").strip()
    for old, new in _UNSAFE_CHARS:
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


def build_commit_title(story_type, title, no_seq):
    return COMMIT_TITLE_TEMPLATE.format(
        type=story_type,
        title=sanitize_title(title),
        no_seq=no_seq,
    )
