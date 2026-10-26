from typing import TypedDict


class PostState(TypedDict, total=False):
    page_id: str
    ideas: list[dict]          # trend scout output
    performance: dict          # analytics summary fed to the strategist
    pillar: str
    format: str
    archetype: str             # framework, relatable, contrarian, before_after, ...
    goal: str                  # the one action the post is engineered for (send/save/comment/reply)
    why_viral: str
    template: str              # visual template for carousels/documents/images
    topic: str
    facts: dict                # depth agent's fact pack
    angle: str
    hook: str                  # winning hook from the hook tournament
    hook_options: list[dict]   # [{type, text, score}]
    content: dict              # writer output
    critic: dict               # critic output
    revisions: int
    media: list[str]           # rendered file paths
    draft_id: int
    log: list[str]
