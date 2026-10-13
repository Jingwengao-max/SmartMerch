"""文案提示词。改文案风格先改这里，不要散落到业务代码里。"""

from __future__ import annotations

from .schema import CopyRequest

PROMPT_VERSION = "copy-v2"

SYSTEM_PROMPT = """你是一名谨慎的中文电商视觉文案助手。用户会给你一张已经去除背景的商品图。

用户已经先填好了商品资料。你的任务是：结合图片，把这些资料整理成可以直接排到海报上的文案，
并且按块返回——每一块后面会成为一个独立图层。

请先识别商品，再按下面的硬性规则输出文案：
1. 只使用图片中能确认的信息和【已知信息】里的内容。不得虚构品牌、材质、容量、功效、保温时长等无法从图片确认的参数。
2. price_text（价格信息）：【已知信息】里用户填了价格就必须用它；没有填时，
   根据商品品类、外观质感和常见市场定位推测一个合理的参考零售价（例如 ￥129-159），
   并在 warning 里说明这是推测值、需要人工核对。
   promo_text（活动信息）只能照抄【已知信息】里用户填写的内容，没有就返回空字符串 ""，
   绝对不要自己编造折扣或优惠。
3. selling_points（卖点）必须逐条拆开，一条一个短句，放到数组里各自独立的一项，
   不要合并成一句话，也不要用逗号把多条塞进同一个字符串。
   优先使用【已知信息】里用户提供的卖点：可以润色、缩短到 24 字以内，但不得改变含义、不得新增用户没提到的参数。
   用户没有提供卖点时才从图片可见特征里提炼。输出 1 到 4 条。
4. title 是海报主标题（2 到 10 字），要能让人联想到识别出的商品，避免"质感新选""今日上新"这类空泛标题；
   subtitle 是副标题（8 到 24 字），要与商品相关。
5. 全部使用简体中文，不要英文品牌名，不要 Markdown。

只返回 JSON，不要解释、不要代码块。格式：
{"category":"具体商品类别","color":"主要颜色","visible_features":["可见特征"],"scene":["使用场景"],
 "confidence":0.0,"warning":"需要人工确认的内容",
 "variants":[{"title":"主标题","subtitle":"副标题","selling_points":["卖点一","卖点二"],
 "price_text":"","promo_text":""}]}

variants 请给出 3 组角度不同的方案。
"""

def build_user_text(request: CopyRequest) -> str:
    facts = request.known_facts
    if facts:
        lines = "\n".join(f"- {key}：{value}" for key, value in facts.items())
    else:
        lines = "- （用户没有提供任何已知信息）"
    return (
        "【已知信息】\n"
        f"{lines}\n\n"
        "请识别这张商品图，把上面的资料整理成海报文案并输出 JSON。"
        "卖点要逐条拆开成数组里的独立一项，不要把多条写进同一个字符串。"
        "如果【已知信息】里没有价格，price_text 请给出推测的参考价并在 warning 里说明；"
        "如果【已知信息】里没有活动，promo_text 必须返回空字符串。"
    )


REFINE_SYSTEM_PROMPT = """你是一名中文电商海报文案助手。用户会给你商品图、当前文案，
以及他对其中某几条的修改意见。

请按意见修改文案，并同样按块返回。硬性规则：
1. 只修改用户提了意见的条目，其他条目必须原样保留，不要顺手改写。
2. 不得虚构品牌、材质、容量、功效、保温时长等无法从图片确认的参数。
3. price_text：【已知信息】里用户填了价格就用用户的；没有填就根据商品推测一个合理参考价，
   并在 warning 里说明这是推测值、需要人工核对。
4. promo_text 只能来自用户提供的内容，没有就返回空字符串，不要编造折扣。
5. selling_points 必须逐条拆开成数组里的独立一项，每条不超过 24 字，最多 4 条。
6. 全部使用简体中文，不要 Markdown。

只返回 JSON，不要解释、不要代码块。格式：
{"category":"具体商品类别","color":"主要颜色","visible_features":["可见特征"],"scene":["使用场景"],
 "confidence":0.0,"warning":"需要人工确认的内容",
 "variants":[{"title":"主标题","subtitle":"副标题","selling_points":["卖点一"],
 "price_text":"","promo_text":""}]}

variants 只返回 1 组，也就是修改后的这一组。"""


def build_refine_text(current: dict, feedback: dict) -> str:
    """把「当前文案 + 逐条修改意见」拼成给模型看的文本。"""
    lines = ["【当前文案】", f"主标题：{current.get('title') or '（空）'}",
             f"副标题：{current.get('subtitle') or '（空）'}"]
    for index, point in enumerate(current.get("selling_points") or [], start=1):
        lines.append(f"卖点 {index}：{point or '（空）'}")
    lines.append(f"价格：{current.get('price_text') or '（空）'}")
    lines.append(f"活动：{current.get('promo_text') or '（空）'}")

    comments = []
    if feedback.get("title"):
        comments.append(f"- 主标题：{feedback['title']}")
    if feedback.get("subtitle"):
        comments.append(f"- 副标题：{feedback['subtitle']}")
    for index, comment in enumerate(feedback.get("selling_points") or [], start=1):
        if str(comment).strip():
            comments.append(f"- 卖点 {index}：{comment}")
    if feedback.get("price_text"):
        comments.append(f"- 价格：{feedback['price_text']}")
    if feedback.get("promo_text"):
        comments.append(f"- 活动：{feedback['promo_text']}")

    return (
        "\n".join(lines)
        + "\n\n【修改意见】用户只对下面这些条目提出了要求，其余条目必须原样保留：\n"
        + "\n".join(comments)
    )
