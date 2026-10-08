# FnDepot 源：qnap8528 驱动

自动跟随上游 [iamiao/8528](https://github.com/iamiao/8528) 发布的新版本，生成符合 FnDepot 第三方应用源
规范（schema_version = 2）的 `fnpack.json`，供飞牛 fnOS 第三方应用商店添加使用。

## 添加到飞牛第三方商店

在飞牛应用商店的「第三方源 / 添加源」中填入下面任意一种地址：

- GitHub 仓库地址：`https://github.com/KITblue/qnap8528fpk`
- JSON 直链：`https://raw.githubusercontent.com/KITblue/qnap8528fpk/main/fnpack.json`
- 国内加速直链：`https://cdn.jsdelivr.net/gh/KITblue/qnap8528fpk@main/fnpack.json`

添加后即可在商店中看到并安装 `qnap8528 驱动`，新版本发布后源内版本列表会自动更新。

## 本仓库内容

| 路径 | 说明 |
| --- | --- |
| `fnpack.json` | FnDepot 源索引（机器生成，勿手改） |
| `scripts/gen_fnpack.py` | 生成脚本：拉取上游 Release、解析版本与架构、计算 sha256 |
| `.github/workflows/sync.yml` | 每天 03:17 UTC（北京时间 11:17）自动重跑生成脚本并提交变化 |

安装包不落库，`download_url` 直接指向上游 Release 资产地址，因此仓库体积始终很小。

## 手动更新

```bash
python scripts/gen_fnpack.py          # 重新生成 fnpack.json
python scripts/gen_fnpack.py --check  # 只检查上游是否有新版本（有则退出码 10）
```

也可以在 GitHub 仓库的 Actions 页面手动触发 `Sync FnDepot source`。

## 上游信息

- 项目：https://github.com/iamiao/8528
- 应用名：`qnap8528-kmod`（FPK manifest 内 appname，须与源索引键名一致）
- 平台：x86
