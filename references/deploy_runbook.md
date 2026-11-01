# 发布手册（双站）

> 本文中的仓库名、项目名、域名都是**示例值**，实际值取自你的 `lesson-studio.json`：
> `deploy.edgeone_project`、`deploy.edgeone_area`、`deploy.git_remote_contains`、`site_url`、`alt_url`。

## 发布拓扑

```
<site_dir>/            ← 唯一发布源
   ├── git push ─────→ Git 托管（GitHub）→ Vercel 等自动构建（海外备份）
   └── edgeone CLI ──→ EdgeOne Pages（正式站，自定义域名）
```

## 命令

```bash
cd <项目根目录>

# 1) 提交并推送（触发远端构建）
git add -A && git commit -m "Day N: <中英主题>" && git push

# 2) 部署正式站
cd <site_dir>
export PAGES_SOURCE=skills          # Windows: set PAGES_SOURCE=skills
edgeone pages deploy -n <edgeone_project> -a <edgeone_area> --skip-ai-gateway-sync
```

## 验证（必须逐项）

```bash
# 各域名 + 状态码 + 字节数
for d in <主域名> <备用域名>; do
  for p in "" dayN.html; do
    printf "%-28s " "$d/$p"
    curl -s -o /dev/null -w "%{http_code} %{size_download}B\n" -A "Mozilla/5.0" "https://$d/$p" --max-time 25
  done
done

# 与本地比对
stat -c%s <site_dir>/dayN.html      # macOS: stat -f%z
```

合格标准：全部 200，且**线上字节数 == 本地字节数**。字节数不一致通常是换行被转换，见下方排查表。

## 关键约束

| 项 | 规则 |
|---|---|
| Git 提交身份 | 与远端项目的协作账号一致；Vercel 会以"作者无权限"拦截陌生邮箱的提交 |
| 构建根目录 | 站点在子目录时，构建配置的 Root Directory 要指向 `<site_dir>`，不是仓库根 |
| EdgeOne 加速区域 | 未备案域名只能用「全球（不含中国大陆）」；备案后才可切中国站 |
| 对外链接 | 只用**永久自定义域名**。`*.edgeone.cool` 带鉴权且约 3 小时过期；`*.vercel.app` 在中国大陆常被 DNS 污染 |
| 证书 | 自定义域名绑定后自动签发与续期，留意到期前是否续上 |

## 故障排查

| 症状 | 原因 | 处理 |
|---|---|---|
| EdgeOne 部署报未登录 | CLI 会话过期 | `edgeone login` 后重试 |
| 线上 401 | 用的是 `*.edgeone.cool` 临时链接 | 换永久域名 |
| `*.vercel.app` 打不开（000） | 大陆 DNS 污染 | 属预期；只作备份，不作验证目标 |
| 页面 404 | 构建 Root Directory 没设 / 部署目录选错 | 检查项目设置 |
| 构建卡在 Building | 同上，或提交身份被拦 | 查 Deployments 状态；核对提交邮箱 |
| `git push` 502 / 超时 | 本机代理抖动或端口变化 | 探测可用端口后 `git -c http.proxy=<port> -c https.proxy=<port> push origin main` |
| 字节数不一致 | Windows 换行转换 | 写盘用 `write_bytes()`；仓库加 `* -text` |
| 新增页覆盖老数据 | 存储前缀没换 | 用 `clone_lesson.py`，不要手改前缀 |
| 导出图尺寸不对 | 模板 Canvas 参数被改 | 回退模板，不要"顺手优化"导出逻辑 |

## 回滚

```bash
cd <项目根目录>
git log --oneline -5
git revert <commit>                 # 生成反向提交，远端自动重新构建
git checkout <commit> -- <site_dir>/dayN.html   # 只恢复某一页
```

EdgeOne 侧：控制台「部署记录」可回滚到任一历史部署。

## 发布后收尾

1. 更新进度记录（最新课程、下一课、已用主题划掉）
2. 更新项目状态文档（如为里程碑）
3. 归档 `linkedin/dayN/`（海报、分享卡、poster.json、帖子草稿）
4. 汇报：主题、各站结果与链接、回归结果（含降级说明）、物料路径、遗留问题
