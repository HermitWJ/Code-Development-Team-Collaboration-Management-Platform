from django.db import transaction

from apps.teams.models import TeamCounter


def allocate_number(team):
    """团队内发号：行锁计数器 + 唯一键兜底，返回 (完整单号, 纯数字序号)。

    两个字段都来自这一次发号：
      story_no = STAR-1024  -> 页面展示
      no_seq   = 1024       -> commit 标题里的 --story=1024
    """
    with transaction.atomic():
        counter = TeamCounter.objects.select_for_update().get(team_id=team.id)
        counter.last_no += 1
        counter.save(update_fields=["last_no"])
        seq = counter.last_no
        return f"{team.slug}-{seq}", seq
