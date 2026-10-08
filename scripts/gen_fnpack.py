#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动追踪 iamiao/8528 的上游 Release，生成符合 FnDepot V2 规范的 fnpack.json。

用法：
    python scripts/gen_fnpack.py            # 生成 / 更新 fnpack.json
    python scripts/gen_fnpack.py --check    # 只检查是否有变化（有变化退出码 10）

要点：
  * 版本号取自 FPK 文件名（qnap8528-kmod_1.24.3_x86.fpk -> 1.24.3）
  * download_url 直接指向上游 Release 资产地址（绝对 URL，规范允许）
  * sha256 优先取 GitHub 资产 digest，缺失时下载后本地计算；size 取资产大小
  * 无变化时不改写文件，避免产生空提交
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "fnpack.json"

UPSTREAM = "iamiao/8528"
APP_NAME = "qnap8528-kmod"          # 必须与 FPK manifest 里的 appname 一致
ICON_URL = "https://cdn.jsdelivr.net/gh/iamiao/8528@master/fnos/ICON_256.PNG"
UA = {"User-Agent": "fnpack-sync", "Accept": "application/vnd.github+json"}
ALLOWED_CATEGORIES = {
    "影音娱乐", "系统工具", "编程开发", "AI赋能", "生活服务",
    "智能智控", "教育学习", "游戏地带", "硬件驱动",
}

APP_META = {
    "display_name": "qnap8528 驱动",
    "desc": "QNAP IT8528 EC 内核驱动，支持风扇控制、温度传感器、LED、按键与 VPD 读取。",
    "platform": ["x86"],
    "categories": ["硬件驱动"],
    "run_as": "root",
    "install_type": "",
    "is_docker": False,
    "service_port": "",
    "maintainer": "iamiao",
    "maintainer_url": "https://github.com/iamiao/8528",
    "bug_report_url": "https://github.com/iamiao/8528/issues",
    "readme_url": "https://github.com/iamiao/8528/blob/master/README.md",
    "icon_url": ICON_URL,
}


def log(msg: str) -> None:
    print(f"[gen_fnpack] {msg}", flush=True)


def http_get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_releases(upstream: str) -> list[dict]:
    url = f"https://api.github.com/repos/{upstream}/releases?per_page=100"
    return json.loads(http_get(url, timeout=60).decode("utf-8")) or []


def parse_version(name: str) -> str | None:
    m = re.search(r"[_-]v?(\d+\.\d+(?:\.\d+)*)[_-]", name)
    return m.group(1) if m else None


def parse_arch(name: str) -> str:
    low = name.lower()
    if "arm" in low or "aarch64" in low:
        return "arm"
    if "x86" in low or "amd64" in low or "x64" in low:
        return "x86"
    return "all"


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(upstream: str) -> dict:
    releases: dict[str, dict] = {}

    for rel in fetch_releases(upstream):
        stamp = (rel.get("published_at") or "")[:19]
        for asset in rel.get("assets") or []:
            name = asset.get("name") or ""
            if not name.lower().endswith(".fpk"):
                continue
            version = parse_version(name)
            if not version:
                log(f"跳过（解析不出版本号）: {name}")
                continue
            arch = parse_arch(name)
            url = asset["browser_download_url"]

            digest = (asset.get("digest") or "").split(":")[-1]
            if not re.fullmatch(r"[0-9a-f]{64}", digest or ""):
                data = http_get(url, timeout=300)
                digest = sha256_of(data)
                size = len(data)
                log(f"已下载校验 {name} size={size} sha256={digest[:12]}…")
            else:
                size = int(asset.get("size") or 0)
                log(f"使用上游 digest {name} size={size}")

            node = releases.setdefault(version, {"changelog": "", "packages": {}})
            node["packages"][arch] = {
                "download_url": url,
                "sha256": digest,
                "size": size,
            }
            node["changelog"] = f"qnap8528 驱动 {version}"
            if stamp:
                node["updated_at"] = stamp.replace("T", "T") + "+00:00"

    def ver_key(v: str) -> list[int]:
        return [int(x) if x.isdigit() else 0 for x in re.split(r"[.\-+]", v)[:3]]

    ordered = {v: releases[v] for v in sorted(releases, key=ver_key)}
    return {
        "schema_version": "2",
        "source_info": {
            "name": "qnap8528 驱动源",
            "author": "ike",
            "homepage": f"https://github.com/{upstream}",
            "description": "自动跟随 iamiao/8528 上游 Release 的 FnDepot 外部源。",
        },
        "apps": {APP_NAME: {**APP_META, "releases": ordered}},
    }


def validate(doc: dict) -> None:
    assert doc["schema_version"] == "2"
    assert doc["source_info"].get("name") and doc["source_info"].get("author")
    for app_name, app in doc["apps"].items():
        assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", app_name), f"非法应用名 {app_name}"
        for field in ("display_name", "desc", "platform", "categories", "icon_url",
                      "run_as", "install_type", "is_docker", "releases"):
            assert field in app, f"{app_name} 缺字段 {field}"
        assert set(app["platform"]) <= {"all", "x86", "arm"}
        assert app["categories"] and set(app["categories"]) <= ALLOWED_CATEGORIES
        assert app["run_as"] in ("package", "root")
        assert isinstance(app["is_docker"], bool)
        assert app["releases"], "至少要有一个版本"
        for ver, rel in app["releases"].items():
            assert rel["packages"], f"{ver} 没有安装包"
            for arch, pkg in rel["packages"].items():
                assert arch in ("all", "x86", "arm"), f"非法架构 {arch}"
                assert str(pkg.get("download_url", "")).startswith(("http://", "https://"))
                assert re.fullmatch(r"[0-9a-f]{64}", pkg.get("sha256", ""))
                assert isinstance(pkg.get("size"), int) and pkg["size"] > 0
    log("规范自检通过")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", default=UPSTREAM)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    doc = build(args.upstream)
    validate(doc)
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"

    if args.check:
        old = OUT_JSON.read_text(encoding="utf-8") if OUT_JSON.exists() else ""
        if old != text:
            log("检测到上游有新版本")
            return 10
        log("无变化")
        return 0

    if OUT_JSON.exists() and OUT_JSON.read_text(encoding="utf-8") == text:
        log("fnpack.json 无变化")
        return 0

    OUT_JSON.write_text(text, encoding="utf-8")
    log(f"已写入 {OUT_JSON.name}，含 {len(doc['apps'][APP_NAME]['releases'])} 个版本")
    return 0


if __name__ == "__main__":
    sys.exit(main())
