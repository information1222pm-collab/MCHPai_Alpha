"""Creator intelligence.

The wallet that *mints* a token carries enormous signal: serial ruggers, one-hit
wonders, and consistent builders behave very differently. We aggregate a
creator's full launch history into a :class:`CreatorProfile` and a single
``creator_score`` (0..100) that becomes a top feature for rug/survival models.
"""

from .scoring import CreatorProfile, TokenLaunch, build_creator_profile, creator_score

__all__ = ["CreatorProfile", "TokenLaunch", "build_creator_profile", "creator_score"]
