"""向后兼容薄壳：真正的实现在 copywriting 包里。

保留这个文件是为了让旧的导入（analyze_with_ai / local_suggestions / configured）
继续可用，避免改动调用方。新代码请直接 import copywriting。
"""

from __future__ import annotations

from copywriting import CopyRequest, configured, generate_copy
from copywriting.legacy import analyze_with_ai, local_suggestions

__all__ = [
    "analyze_with_ai",
    "configured",
    "generate_copy",
    "local_suggestions",
    "CopyRequest",
]
