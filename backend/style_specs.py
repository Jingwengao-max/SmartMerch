"""每个风格的文案条目与图层映射。

新增风格时：
1. 在 models/ 放版式模型；
2. 在这里登记 fields（条目、区域、字号、层级）；
3. 在 learned_layout.MODEL_FILES 与前端 styles 里登记。
"""

from __future__ import annotations

STYLE_SPECS: dict[str, dict] = {
    "editorial": {
        "label": "杂志",
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
                "singleLine": True, "minFont": 16,
                "maxChars": 10, "hint": "4 至 10 字，使用完整短句，不换行",
                "layouts": {
                    1: [["leftDetail", 32, 10, 1]],
                    2: [["leftDetail", 30, 10, 1], ["rightDetail", 28, 10, 1]],
                    3: [
                        ["leftCallout", 30, 10, 1],
                        ["leftDetail", 30, 10, 1],
                        ["rightDetail", 28, 10, 1],
                    ],
                },
                "align": "center", "verticalAlign": "middle",
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
        "label": "简约",
        "templateId": "learned-style2-v1",
        "variantOverrides": {
            # 版式 1：主标题三行大字铺满标题框、压在商品下层；口号/介绍加半透明浮窗。
            0: {
                "layout": {
                    "productScale": 1.08,
                    "productShrink": 0.94,
                    # 为上方三行主标题保留固定安全区。
                    "productMinTop": 0.30,
                },
                "background": {
                    "haze": {
                        "from": 0.5, "to": 0.8, "color": "accent",
                        "opacity": 0.14, "blur": 80,
                    },
                },
                "name": {
                    # 方案 1 的标题固定在上方安全区，按文字原顺序三行排列。
                    # 不使用自动铺满，避免标题被商品遮挡后看起来像断字、乱序。
                    "lines": 3, "fillBox": False, "zIndex": 3,
                    "font": [420, 100], "flowFit": True,
                    "maxBlockHeight": 752,
                    "fixedTitleLines": True, "justifyLines": True,
                    "lineHeightRatio": 1.08, "twoLineHeightRatio": 1.18,
                    "fontFamily": "hei", "weight": 900,
                    "align": "left", "verticalAlign": "top",
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
                "maxChars": 9, "hint": "1 至 9 字中文商品名，不得使用标点或换行",
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
    "retro": {
        "label": "复古",
        "templateId": "retro-food-poster-v1",
        "productNameField": "subtitle",
        "fields": [
            {
                "key": "subtitle", "id": "cn-title", "role": "title",
                "label": "中文商品名", "kind": "text", "regions": ["cnTitle"],
                "color": "dark", "font": [44, 28], "weight": 700, "zIndex": 4,
                "align": "center", "verticalAlign": "middle", "maxChars": 12,
                "hint": "4 至 12 字中文商品名，只使用中文",
            },
            {
                "key": "title", "id": "hero-title", "role": "heroTitle",
                "label": "英文主标题", "kind": "text", "regions": ["heroTitle"],
                "color": "paper", "font": [116, 50], "weight": 900, "zIndex": 4,
                "align": "center", "verticalAlign": "middle",
                "generated": False, "maxChars": 36, "autoLines": 2,
            },
            {
                "key": "slogan", "id": "slogan", "role": "slogan",
                "label": "中文口号", "kind": "text", "regions": ["slogan"],
                "color": "accent", "font": [50, 30], "weight": 700, "zIndex": 4,
                "align": "center", "verticalAlign": "middle", "maxChars": 18, "autoLines": 2,
                "hint": "8 至 18 字，突出味道、质感或使用感受",
            },
            {
                "key": "feature", "id": "feature", "role": "label",
                "label": "核心卖点", "kind": "text", "regions": ["feature"],
                "color": "dark", "font": [46, 30], "weight": 800, "zIndex": 5,
                "align": "center", "verticalAlign": "middle",
                "panel": {"fill": "paper", "opacity": 0.96, "radius": 30, "pad": [20, 10, 20, 10]},
                "maxChars": 18, "hint": "8 至 18 字，只写一条最重要、最有辨识度的卖点",
            },
            {
                "key": "footer", "id": "footer", "role": "footer",
                "label": "底部说明", "kind": "text", "regions": ["footer"],
                "color": "dark", "font": [28, 18], "weight": 700, "zIndex": 4,
                "align": "center", "verticalAlign": "middle", "maxChars": 48, "autoLines": 2,
                "hint": "12 至 48 字，可填写品牌说明或品质宣言",
            },
        ],
        "defaults": {
            "subtitle": "商品名称", "title": "NEW ARRIVAL",
            "slogan": "好味层层展开", "feature": "真材实料、风味浓郁",            "footer": "QUALITY INGREDIENTS · MADE WITH CARE",
        },
    },
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
