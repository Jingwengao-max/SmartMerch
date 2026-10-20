"""每个风格的文案条目与图层映射。

新增风格时：
1. 在 models/ 放版式模型；
2. 在这里登记 fields（条目、区域、字号、层级）；
3. 在 learned_layout.MODEL_FILES 与前端 styles 里登记。
"""

from __future__ import annotations

STYLE_SPECS: dict[str, dict] = {
    "editorial": {
        "label": "杂志编辑",
        "templateId": "learned-bakery-editorial-v1",
        "productNameField": "title",
        "fields": [
            {
                "key": "title", "id": "hero-title", "role": "heroTitle",
                "label": "英文标题", "kind": "text", "regions": ["heroTitle"],
                "color": "accent", "font": [132, 74], "compactFont": [104, 56],
                "weight": 700, "zIndex": 3,
                "generated": False, "maxChars": 60,
            },
            {
                "key": "subtitle", "id": "cn-title", "role": "title",
                "label": "中文商品名", "kind": "text", "regions": ["cnTitle"],
                "color": "accent", "font": [82, 62], "compactFont": [70, 52],
                "weight": 700, "zIndex": 3,
                "maxChars": 12, "hint": "4 至 12 字中文商品名，只使用中文",
            },
            {
                "key": "launchText", "id": "launch", "role": "label",
                "label": "右上标签", "kind": "text", "regions": ["launch"],
                "color": "dark", "font": 38, "weight": 700, "zIndex": 3,
                "align": "center", "verticalAlign": "middle",
                "maxChars": 6, "hint": "2 至 6 字右上标签",
            },
            {
                "key": "badgeText", "id": "badge", "role": "badge",
                "label": "徽章", "kind": "text", "regions": ["badge"],
                "color": "#ffffff", "font": 60, "weight": 700, "zIndex": 5,
                "align": "center", "verticalAlign": "middle",
                "maxChars": 8, "hint": "2 至 8 字符徽章文字",
            },
            {
                "key": "footer", "id": "footer-brand", "role": "footer",
                "label": "品牌口号", "kind": "text", "regions": ["footer"],
                "color": "dark", "font": 64, "weight": 700, "zIndex": 3,
                "align": "center", "verticalAlign": "middle", "pad": [70, 0, 70, 0],
                "maxChars": 24, "hint": "8 至 24 字底部品牌口号",
            },
            {
                "key": "sellingPoints", "label": "卖点", "kind": "list",
                "role": "sellingPoint",
                "maxItems": 3, "color": "dark", "weight": 700, "zIndex": 4,
                "maxChars": 28, "hint": "10 至 28 字",
                "layouts": {
                    1: [["leftDetail", 32, 12, 4]],
                    2: [["leftDetail", 30, 9, 4], ["rightDetail", 30, 5, 4]],
                    3: [
                        ["leftCallout", 30, 9, 4],
                        ["leftDetail", 30, 9, 4],
                        ["rightDetail", 30, 5, 4],
                    ],
                },
            },
        ],
        "defaults": {
            "title": "NEW PRODUCT",
            "subtitle": "匠心新品 好味登场",
            "launchText": "新品上市",
            "badgeText": "NEW!",
            "footer": "品牌口号待补充",
        },
    },
    "style2": {
        "label": "风格二",
        "templateId": "learned-style2-v1",
        "variantOverrides": {
            # 版式 1：主标题三行大字铺满标题框、压在商品下层；口号/介绍加半透明浮窗。
            0: {
                "layout": {"productScale": 1.08, "productShrink": 0.94},
                "background": {
                    "haze": {
                        "from": 0.5, "to": 0.8, "color": "accent",
                        "opacity": 0.14, "blur": 80,
                    },
                },
                "name": {
                    "lines": 3, "fillBox": True, "zIndex": 1,
                    "fontFamily": "hei", "weight": 900, "fontScale": 0.9,
                    "emboss": {"offset": 6, "opacity": 0.45, "gray": 0.55},
                },
                "sellingPoints": {
                    "color": "accent", "symmetric": True, "align": "center",
                    "verticalAlign": "middle",
                    "shadow": {"offset": 3, "opacity": 0.3, "darken": 0.22},
                    "glow": {"pad": 10, "opacity": 0.26, "blur": 20, "lighten": 0.18},
                },
                "slogan": {
                    "zIndex": 4, "font": [64, 24], "expand": [32, 0, 32, 0],
                    "panel": {
                        "fill": "#ffffff", "opacity": 0.42,
                        "radius": 20, "pad": [22, 16, 22, 16],
                        "icon": True,
                    },
                },
                "intro": {
                    "zIndex": 4, "font": [38, 26], "offset": [52, -24],
                    "panel": {
                        "fill": "#ffffff", "opacity": 0.42,
                        "radius": 20, "pad": [22, 16, 22, 16],
                        "icon": True,
                    },
                },
            },
        },
        "productNameField": "name",
        "fields": [
            {
                "key": "name", "id": "product-name", "role": "name",
                "label": "商品名", "kind": "text", "regions": ["name"],
                "color": "accent", "font": [96, 52], "weight": 700, "zIndex": 3,
                "maxChars": 12, "hint": "4 至 12 字中文商品名",
            },
            {
                "key": "slogan", "id": "slogan", "role": "slogan",
                "label": "口号", "kind": "text", "regions": ["slogan"],
                "color": "dark", "font": [56, 24], "weight": 700, "zIndex": 3,
                "maxChars": 20, "lines": 2, "stripPunctuation": True,
                "hint": "必须是对偶句：两句、字数尽量一致、不使用逗号或句号",
            },
            {
                "key": "intro", "id": "intro", "role": "intro",
                "label": "介绍", "kind": "text", "regions": ["intro"],
                "color": "dark", "font": [32, 22], "weight": 400, "zIndex": 3,
                "wrap": 10, "maxLines": 7,
                "maxChars": 60, "hint": "20 至 60 字商品介绍",
            },
            {
                "key": "sellingPoints", "label": "卖点", "kind": "list",
                "role": "sellingPoint",
                "maxItems": 3, "color": "dark", "weight": 700, "zIndex": 4,
                "maxChars": 8, "hint": "4 至 8 字",
                "layouts": {
                    1: [["point1", 34, 9, 2]],
                    2: [["point1", 34, 9, 2], ["point2", 34, 9, 2]],
                    3: [["point1", 34, 9, 2], ["point2", 34, 9, 2], ["point3", 34, 9, 2]],
                },
            },
            {
                "key": "sellingPointsEn", "id": "selling-points-en", "role": "sellingPointEn",
                "label": "英文卖点", "kind": "list", "maxItems": 3,
                "maxChars": 28, "zIndex": 4, "color": "accent-dark", "weight": 400,
                "attachTo": "sellingPoints", "font": 30, "minFont": 16, "gap": 4, "align": "center",
                "spread": 30,
                "hint": "与三条卖点一一对应的简洁英文翻译，不要新增信息",
            },
        ],
        "defaults": {
            "name": "商品名称",
            "slogan": "一句品牌口号",
            "intro": "在这里补充一段商品介绍。",
        },
    },
}

# 极简版式沿用杂志编辑的条目结构，只是版式区域与装饰不同。
STYLE_SPECS["minimal"] = {
    "label": "极简",
    "templateId": "learned-minimal-v1",
    "productNameField": "title",
    "fields": STYLE_SPECS["editorial"]["fields"],
    "defaults": STYLE_SPECS["editorial"]["defaults"],
}


def get_style_spec(style: str, variant_index: int | None = None) -> dict:
    spec = STYLE_SPECS.get(style)
    if not spec:
        raise ValueError(f"未知风格：{style}")
    if variant_index is None:
        return spec
    overrides = (spec.get("variantOverrides") or {}).get(variant_index)
    if not overrides:
        return spec
    field_keys = {field["key"] for field in spec["fields"]}
    fields = [
        {**field, **(overrides.get(field["key"]) or {})}
        for field in spec["fields"]
    ]
    top_level = {key: value for key, value in overrides.items() if key not in field_keys}
    return {**spec, **top_level, "fields": fields}
