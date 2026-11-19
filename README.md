# 法援卷宗冲突核验与转介

邻里援助中心的模拟行政接待台，串联授权、当事人冲突、主题专长、材料补正、机构受理和工时回访。不提供法律意见，不判断争议实体权利，也不自动作出办案建议。

中心有6位接待员和3家合作机构。此前来访授权夹在纸质收件表里，机构承接位和回执分散在共享表格，改派常常忘记释放位置；对立双方名称带空格时还会漏查，材料补正与旧转介信无法同步。上游是模拟来访接待，本应用负责从脱敏建卷到行政转介销案，下游是合作机构接收人及中心回访人员。

## 六项业务职责

- 来访授权：化名、模拟事实和版本、授权依据；新卷默认未授权。修改事实使旧主题复核失效。撤回授权立即终止待受理或已受理转介，释放承接位，保留服务历史。
- 双方冲突：来访方与相对方关联到归一化当事人（NFKC、空格和大小写归一）；候选机构已有在途对立方时阻止转介；发信与签收均重新核验。
- 主题专长：真实 Redis worker 运行 TF-IDF + MultinomialNB，劳动/住房/消费三主题；低于68%明确退回人工，所有结果均需主管复核才可转介。
- 材料补正：按复核主题给出两项必需清单，提交脱敏文件索引后由主管通过或退回。补正重新提交会清除旧通过状态。
- 机构承接：机构专长和并发承接位约束；发信占位，撤回和销案释放；同卷只保留一条在途转介，机构受理回执需主管登记。
- 工时销案：已受理才可登记1–480分钟服务片段，累计工时大于零后主管回访销案。销案卷宗只读，保留回访满意度和总时长。

## 运行

```sh
cp .env.example .env
docker compose config --quiet
docker compose up -d --build --wait
docker compose exec backend python -m src.seed
```

前端 http://localhost:18233 ，后端 http://localhost:19233 ，API 文档 http://localhost:19233/docs 。MySQL 映射17733，Redis仅内部开放。恰好5个服务：frontend、backend、worker、db、redis，独立数据库/Redis/共享产物命名卷，全部有真实健康检查。默认子网10.221.34.0/24。MySQL应用连接采用 READ COMMITTED，容量锁内查询可看到已提交的最新转介。

| 账号 / 角色 | 密码 | 可操作职责 |
|---|---|---|
| operator / 接待员 | Aid@2026 | 建卷与授权、事实更正、双方关联、冲突核验、主题排队、材料提交、服务时长 |
| supervisor / 接待主管 | Aid@2026 | 全部接待动作，以及主题复核、材料核验、机构、转介信、受理回执、撤回、回访销案与审计 |
| viewer / 只读观察员 | Aid@2026 | 只读卷宗，全部写接口拒绝 |

JWT有效8小时。演示账户、密码和数据仅用于本地行政流程试用。

## 当日操作示例

1. 08:30 主管打开 LZ031 来访者林某，劳动报酬描述涉及青桥商行；当前只核验了脱敏身份授权页，还缺工资记录。
2. 09:00 在“双方冲突”核验友邻服务站，发现该站已承接青桥商行关联来访LZ030，改选和睦接待室。
3. 09:20 查看劳动主题复核，试发转介因缺劳动报酬记录被拒绝。
4. 09:30 接待员登记 `LZ031-工资记录-脱敏v2.pdf`；主管核验通过。若材料退回，重新提交并复核后恢复。
5. 10:00 主管发给和睦接待室，占用1位；来访者撤回授权时转介自动撤回，承接位归还，再发信会被授权规则拒绝。
6. 10:30 重新取得授权或撤回未受理信后改派；主管记录 `HM-ACK-031` 回执。未受理之前不能登记服务。
7. 14:00 接待员登记45分钟材料沟通和30分钟回执说明，主管确认75分钟工时和5分回访，销案释放位置。
8. 16:00 查看 LZ033 主题待核访客，模糊事实置信度约33%，先人工复核；更正事实后需重新提交该版本分流。LZ032 演示尚未授权的拦截。

## 算法口径

`backend/src/algorithm.py` 生成108条三主题模板合成文本，以字符2–3 gram TF-IDF和 MultinomialNB(alpha=0.5) 分类。固定seed34按主题分层留出27条，训练81条，真实计算宏F1与三乘三混淆矩阵；行是实际主题，列是预测主题，劳动/住房/消费顺序。worker把预测、最高类别概率、低置信标记、指标和样本SHA256写入关系表，并在共享artifacts卷留存指标JSON。

这些模板包含近似表述，留出分数只能证明内部可复现性，不能视为真实接待效果或法律可靠性。低置信强制人工，主管有权改判主题。没有授权不允许提交新识别；事实版本不符的任务会失败或无法复核，可重新排队恢复。

## 结构和事务

| 路径 | 职责 |
|---|---|
| backend/src/models.py、schemas.py | Intake/Consent、Party/CaseParty/ConflictCheck、Triage、Requirement/Document、Agency/Referral、ServiceLog/Closure关系约束及输入契约 |
| intake_service.py、conflict_service.py | 授权撤回、事实版本、双方归一与机构对照 |
| triage_service.py、algorithm.py、worker.py | 行政主题排队、实算和主管复核 |
| document_service.py、referral_service.py、closure_service.py | 材料补正、容量事务、机构回执和工时销案 |
| common.py、auth.py、middlewares.py | 卷宗根锁、JWT角色、动作审计、请求追踪、突发限流 |
| frontend/src/pages/ | 六个独立可操作页面，无前端框架 |
| frontend/src/components/ | case-strip跨页卷宗上下文、controls表单表格、receipt信封式机构回执 |
| frontend/src/api、stores、utils | 请求、会话和当前卷宗、格式化与可恢复保存状态 |

所有变更先锁Intake根，必要时再锁Referral与Agency。发信在机构锁内核验容量、在途对立方和材料；撤回与销案在相同锁序释放位置。数据库容量约束与服务校验同时存在。

后端`constants.py` Role、IntakeState、ReferralState、Topic与前端`constants/enums.js` roles/intakeStates/referralStates/topics共享状态值，分别用于seed、模型默认状态、机构专长校验和界面。intake状态open/referred/accepted/closed；referral状态pending/accepted/withdrawn/completed；主题labor/housing/consumer。

## 开发、数据和范围

`.env.example` 列出COMPOSE_PROJECT_NAME、三端口、COMPOSE_SUBNET、JWT_SECRET和SEED_DEMO。`.env`忽略提交。启动SEED_DEMO=true自动导入自然键缺失项；重复执行不覆盖手工修改、不重复增加机构active_count。

后端使用Python3.12、FastAPI、SQLAlchemy、PyMySQL、scikit-learn，前端Nginx托管原生ES modules。开发时在虚拟环境安装backend/requirements.txt，设置DATABASE_URL和REDIS_URL，在backend目录运行`uvicorn src.app:app --reload`；前端不需要Node构建。Google Fonts为Noto Sans SC和ZCOOL XiaoWei，离线时采用sans-serif/serif回退。

`docker compose logs -f backend worker`读取运行日志；`docker compose down -v --remove-orphans`清理本项目并删除演示数据。工作区`test-artifacts/gb-1034/`保存真实API、强制并发、权限和Chrome证据，不混入源码。

已知范围：仅模拟行政转介，不接收真实敏感身份材料，只存脱敏索引；冲突核验覆盖当前pending/accepted承接，尚无跨机构历史利益冲突目录；一卷一个来访方和一个相对方；机构回执由主管代录，没有外部机构门户；工时为人工记录，无真实支付或法律建议。数据库首次启动create_all，无历史迁移链。

MIT License，见LICENSE。
