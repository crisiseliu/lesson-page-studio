#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""技能内共用的配置读取（纯标准库，不引入第三方依赖）。

配置文件名固定为 lesson-studio.json，查找顺序：
    1) 脚本 --config 显式指定
    2) 当前工作目录
    3) 技能根目录（scripts/ 的上一级）

命令行参数一律优先于配置文件；配置文件优先于脚本内置默认值。
"""
import json
import sys
from pathlib import Path

FILENAME = "lesson-studio.json"


def find_config(explicit: str | None = None) -> Path | None:
    if explicit:
        return Path(explicit)
    for cand in (Path.cwd() / FILENAME, Path(__file__).resolve().parent.parent / FILENAME):
        if cand.exists():
            return cand
    return None


def load(explicit: str | None = None) -> dict:
    p = find_config(explicit)
    if p is None or not p.exists():
        if explicit:
            print(f"ERROR: 指定的配置文件不存在: {p}", file=sys.stderr)
            sys.exit(4)
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: 配置文件不是合法 JSON（{p}）：{exc}", file=sys.stderr)
        sys.exit(4)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def pick(cli_value, cfg: dict, key: str, default=None):
    """优先级：命令行 > 配置文件 > 内置默认。"""
    if cli_value is not None:
        return cli_value
    if key in cfg and cfg[key] not in (None, ""):
        return cfg[key]
    return default


def deep(cfg: dict, *keys, default=None):
    """读嵌套配置：deep(cfg, "deploy", "edgeone_project")。"""
    cur = cfg
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return default if cur in (None, "") else cur
