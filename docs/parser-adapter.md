# ParserAdapter 接口

## 输入

解析器接收 `RecognizedDocument`。每一行包含 `text`、`location`、`page` 和 `confidence`；来源信息保存在 `RecognitionProvenance` 中，不写入公共 `ParseResult` 顶层字段。

| 入口 | 输入来源 | 用途 |
| --- | --- | --- |
| `load_text(path)` | UTF-8/UTF-8 BOM 文本 | 文本导入和回归测试 |
| `FixtureOcrProvider` | 人工整理的文字夹具 | 验证字段转换，不代表 OCR 准确率 |
| `JsonOcrProvider` | 外部引擎导出的 JSON | 验证真实 OCR 输出格式接入 |

核心调用：

```python
result = ParserAdapter().parse(request, recognized_document)
proposal = compare_parse_results(old_result, new_result, task_map)
```

## 输出

`ParserAdapter.parse` 返回固定的八个顶层字段：

```text
parse_result_id, document_id, status, fields,
course_assessment, notice, warnings, errors
```

字段证据保留原文引用、位置、页码和可用置信度。文本来源没有可解释置信度时使用 `null`。

课程权重缺失时保持 `weight=null` 并返回 `calculable=false`。同层权重不等于 1、嵌套层级超出约定或结构无法识别时也不计算。

通知出现多个不同截止时间时，`notice.deadline=null`，证据标记为需要确认，候选日期写入冲突信息。差异引擎会生成 `冲突待确认`，不会自动选择日期。

## 副作用边界

本实现不写数据库、不创建或更新任务、不修改提醒、不删除原文件，也不自动接受变更建议。调用方应在用户确认后，通过自己的业务接口应用建议。

## 合同守卫

`validate_parse_result` 和 `validate_change_proposal` 检查顶层字段、证据字段、通知字段、证据引用和正式枚举。若要升级合同，应发布新的 Schema 版本，不应直接放宽现有守卫。
