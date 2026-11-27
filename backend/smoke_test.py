"""端到端烟测：覆盖状态机、鉴权、软删、富文本与看板（直接跑，无需起服务）。

用法：
    DB_ENGINE=sqlite python manage.py migrate
    DB_ENGINE=sqlite python seed_demo.py
    DB_ENGINE=sqlite python smoke_test.py

注意：脚本会重置演示库中 no_seq >= 1024 的需求单，仅用于本地演示库。
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402

from apps.stories.models import Story  # noqa: E402
from apps.teams.models import Team, TeamCounter, TeamMember  # noqa: E402

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo12345")


def login(username):
    client = APIClient()
    response = client.post(
        "/api/v1/auth/login/",
        {"username": username, "password": DEMO_PASSWORD},
        format="json",
    )
    assert response.status_code == 200, (response.status_code, response.data)
    client.credentials(HTTP_AUTHORIZATION="Token " + response.data["token"])
    return client


def move(client, base, story_id, action, version, remark=None):
    payload = {"action": action, "version": version}
    if remark is not None:
        payload["remark"] = remark
    return client.post(
        f"{base}{story_id}/transitions/", payload, format="json"
    )


def create(client, base, title, **extra):
    payload = {"type": "feat", "title": title}
    payload.update(extra)
    response = client.post(base, payload, format="json")
    assert response.status_code == 201, (response.status_code, response.data)
    return response.data


def main():
    team = Team.objects.get(slug="STAR")
    team_id = team.id
    Story.objects.filter(team=team, no_seq__gte=1024).delete()
    TeamCounter.objects.filter(team=team).update(last_no=1023)

    lisi_id = get_user_model().objects.get(username="lisi").id
    wangwu_id = get_user_model().objects.get(username="wangwu").id
    zhangsan, lisi, wangwu = login("zhangsan"), login("lisi"), login("wangwu")
    base = f"/api/v1/teams/{team_id}/stories/"
    checks = []

    response = zhangsan.get("/api/v1/teams/")
    assert response.status_code == 200 and response.data[0]["my_role"] == "owner"
    checks.append("团队列表与真实角色")

    payload = {
        "type": "feat",
        "title": "支持导出月报",
        "description": (
            '<p>运营需要按月导出项目汇总</p>'
            '<script>alert(1)</script>'
            '<img src="/media/stories/demo.png" onerror="alert(2)" alt="图">'
        ),
        "assignee_id": lisi_id,
        "priority": "high",
        # 这两个字段应被 Serializer 白名单直接丢弃
        "story_no": "STAR-9999",
        "status": "released",
    }
    response = zhangsan.post(base, payload, format="json")
    data = response.data
    assert response.status_code == 201, (response.status_code, data)
    assert data["story_no"] == "STAR-1024", data["story_no"]
    assert data["commit_title"] == "feat: 支持导出月报 --story=1024", data["commit_title"]
    assert data["status"] == "planning" and data["version"] == 1
    description = data["description"]
    assert "<p>" in description and "/media/stories/demo.png" in description
    assert "<script" not in description and "alert(1)" not in description
    assert "onerror" not in description
    story_id, version = data["id"], data["version"]
    checks.append("发号 / 白名单 / commit 标题 / 富文本服务端净化")

    response = move(zhangsan, base, story_id, "start", version)
    assert response.status_code == 201, (response.status_code, response.data)
    assert response.data["to_status"] == "developing" and response.data["version"] == 2
    version = response.data["version"]
    checks.append("开始开发直接流转（无需理由）")

    response = move(zhangsan, base, story_id, "start", version - 1)
    assert response.status_code == 409 and response.data["code"] == "VERSION_CONFLICT"
    checks.append("版本冲突统一 409")

    second = create(zhangsan, base, "修复导出月报空指针")
    second_id, second_version = second["id"], second["version"]
    response = move(zhangsan, base, second_id, "release", second_version)
    assert response.status_code == 409 and response.data["code"] == "TRANSITION_NOT_ALLOWED"
    checks.append("非法流转拦截")

    response = lisi.post(
        f"{base}{second_id}/transitions/",
        {"action": "start", "version": second_version, "role": "admin"},
        format="json",
    )
    assert response.status_code == 403 and response.data["code"] == "ROLE_NOT_ALLOWED"
    checks.append("伪造角色被拦")

    response = wangwu.get(base)
    assert response.status_code == 403 and response.data["code"] == "NOT_TEAM_MEMBER"
    checks.append("非成员被拦")

    response = zhangsan.post(base, {"type": "hack", "title": "x"}, format="json")
    assert response.status_code == 400 and response.data["code"] == "INVALID_STORY_TYPE"
    checks.append("需求类型枚举")

    response = zhangsan.post(
        base, {"type": "fix", "title": '导出"月报"含 $HOME 与 `cmd`'}, format="json"
    )
    title = response.data["commit_title"]
    assert "\n" not in title and '"' not in title and "$" not in title and "`" not in title, title
    checks.append("commit 标题特殊字符清洗")

    response = zhangsan.get(f"{base}999999/")
    assert response.status_code == 404 and response.data["code"] == "STORY_NOT_FOUND"
    response = zhangsan.post(f"{base}{story_id}/commits/", {}, format="json")
    assert response.status_code == 404
    checks.append("跨团队 404 / 无 commit 写接口")

    response = move(zhangsan, base, story_id, "submit_test", version)
    assert response.status_code == 201 and response.data["to_status"] == "pending_test", response.data
    version = response.data["version"]
    response = move(zhangsan, base, story_id, "submit_accept", version)
    assert response.status_code == 201 and response.data["to_status"] == "pending_accept", response.data
    version = response.data["version"]
    checks.append("待测试 → 待验收 直接流转")

    response = move(lisi, base, story_id, "release", version)
    assert response.status_code == 403 and response.data["code"] == "ROLE_NOT_ALLOWED"
    response = move(zhangsan, base, story_id, "accept_reject", version)
    assert response.status_code == 400 and response.data["code"] == "INVALID_PARAM"
    response = move(
        zhangsan, base, story_id, "accept_reject", version, "验收口径未满足，打回开发"
    )
    assert response.status_code == 201 and response.data["to_status"] == "developing", response.data
    version = response.data["version"]
    checks.append("验收发布限权限 / 验收打回必须写明理由")

    for action in ("submit_test", "submit_accept"):
        response = move(zhangsan, base, story_id, action, version)
        assert response.status_code == 201, (action, response.status_code, response.data)
        version = response.data["version"]
    response = move(zhangsan, base, story_id, "release", version)
    assert response.status_code == 201 and response.data["to_status"] == "released", response.data
    checks.append("验收通过 → 已发布")

    third = create(zhangsan, base, "暂停演示单")
    third_id, third_version = third["id"], third["version"]
    response = move(zhangsan, base, third_id, "suspend", third_version)
    assert response.status_code == 400 and response.data["code"] == "INVALID_PARAM"
    response = move(zhangsan, base, third_id, "suspend", third_version, "等待外部接口确认")
    assert response.status_code == 201 and response.data["to_status"] == "suspended", response.data
    checks.append("暂停 / 暂缓必须写明理由")

    response = lisi.delete(f"{base}{third_id}/")
    assert response.status_code == 403 and response.data["code"] == "ROLE_NOT_ALLOWED"
    response = zhangsan.delete(f"{base}{third_id}/")
    assert response.status_code == 204, (response.status_code, response.data)
    response = zhangsan.get(f"{base}{third_id}/")
    assert response.status_code == 404 and response.data["code"] == "STORY_NOT_FOUND"
    response = zhangsan.get(base)
    assert third_id not in [row["id"] for row in response.data["results"]]
    checks.append("删除权限 / 软删后列表与详情均不可见")

    response = zhangsan.get(f"{base}stats/")
    assert response.status_code == 200, (response.status_code, response.data)
    stats = response.data
    for key in (
        "total", "status_distribution", "priority_distribution", "member_load",
        "trend", "mine", "pending_accept", "completion_rate",
    ):
        assert key in stats, key
    assert any(row["status"] == "pending_accept" for row in stats["status_distribution"])
    assert stats["mine"]["user"]["username"] == "zhangsan"
    assert len(stats["trend"]) == 7
    checks.append("团队 + 个人指标看板接口")

    response = zhangsan.post(
        f"{base}media/",
        {
            "file": SimpleUploadedFile(
                "demo.png", b"\x89PNG\r\n\x1a\ndemo", content_type="image/png"
            )
        },
        format="multipart",
    )
    assert response.status_code == 201, (response.status_code, response.data)
    assert response.data["kind"] == "image" and response.data["url"].startswith("/media/")
    media_url = response.data["url"]
    assert zhangsan.get(media_url).status_code == 200
    response = zhangsan.post(
        f"{base}media/",
        {
            "file": SimpleUploadedFile(
                "bad.exe", b"x", content_type="application/octet-stream"
            )
        },
        format="multipart",
    )
    assert response.status_code == 400 and response.data["code"] == "INVALID_FILE_TYPE"
    checks.append("图片上传 / 扩展名白名单 / 媒体可访问")

    TeamMember.objects.update_or_create(
        team=team,
        user_id=wangwu_id,
        defaults={"role": TeamMember.ROLE_ACCEPTOR},
    )
    fourth = create(zhangsan, base, "验收负责人演示单", assignee_id=lisi_id)
    fourth_id, fourth_version = fourth["id"], fourth["version"]
    for action in ("start", "submit_test", "submit_accept"):
        response = move(zhangsan, base, fourth_id, action, fourth_version)
        assert response.status_code == 201, (action, response.status_code, response.data)
        fourth_version = response.data["version"]
    response = move(wangwu, base, fourth_id, "release", fourth_version)
    assert response.status_code == 201 and response.data["to_status"] == "released", response.data
    response = move(wangwu, base, second_id, "start", second_version)
    assert response.status_code == 403 and response.data["code"] == "ROLE_NOT_ALLOWED"
    TeamMember.objects.filter(team=team, user_id=wangwu_id).delete()
    checks.append("验收负责人可发布 / 不能越权做管理动作")

    response = zhangsan.patch(
        f"/api/v1/teams/{team_id}/members/{lisi_id}/",
        {"role": TeamMember.ROLE_ACCEPTOR},
        format="json",
    )
    assert response.status_code == 200 and response.data["role"] == "acceptor", response.data
    response = zhangsan.patch(
        f"/api/v1/teams/{team_id}/members/{lisi_id}/",
        {"role": TeamMember.ROLE_MEMBER},
        format="json",
    )
    assert response.status_code == 200, (response.status_code, response.data)
    checks.append("管理员可指派 / 取消验收负责人角色")

    response = zhangsan.patch(
        f"/api/v1/teams/{team_id}/",
        {"name": "星河项目组", "git_repo_url": "https://example.com/org/star.git"},
        format="json",
    )
    assert response.status_code == 200 and response.data["git_repo_url"].endswith("star.git"), response.data
    response = zhangsan.patch(
        f"/api/v1/teams/{team_id}/", {"git_repo_url": "javascript:alert(1)"}, format="json"
    )
    assert response.status_code == 400, (response.status_code, response.data)
    response = lisi.delete(f"/api/v1/teams/{team_id}/")
    assert response.status_code == 403, (response.status_code, response.data)
    checks.append("Git 仓库绑定 / 非法地址拦截 / 删除团队仅限创建者")

    temp = zhangsan.post(
        "/api/v1/teams/",
        {"name": "临时团队", "slug": "TMP1", "git_repo_url": "git@example.com:org/tmp.git"},
        format="json",
    )
    assert temp.status_code == 201, (temp.status_code, temp.data)
    temp_id = temp.data["id"]
    response = zhangsan.delete(f"/api/v1/teams/{temp_id}/")
    assert response.status_code == 204, (response.status_code, response.data)
    assert not Team.objects.filter(id=temp_id).exists()
    checks.append("创建团队可带仓库地址 / 创建者可删除团队")

    # 代码工程：团队 → 项目 → 需求单 → 开发分支 → 相对 main 的 commit
    code = f"/api/v1/teams/{team_id}/code/"
    project = zhangsan.post(
        code + "projects/",
        {
            "name": "烟测项目",
            "slug": "SMOKE1",
            "repo_url": "https://github.com/example/smoke-repo.git",
            "main_branch": "main",
        },
        format="json",
    )
    assert project.status_code == 201, (project.status_code, project.data)
    project_id = project.data["id"]
    response = zhangsan.get(code + "projects/")
    assert response.status_code == 200 and any(row["id"] == project_id for row in response.data)

    linked = create(
        zhangsan, base, "代码工程链路演示单",
        project_id=project_id, branch_name="feature/smoke-1",
    )
    linked_id = linked["id"]
    assert linked["branch_name"] == "feature/smoke-1" and linked["base_branch"] == "main", linked
    checks.append("项目创建 / 需求单绑定开发分支并快照 main 基线")

    commits = [
        {
            "sha": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789a",
            "title": "feat: 代码工程链路 --story=1024",
            "author": "zhangsan",
            "additions": 42,
            "deletions": 5,
            "files_changed": 3,
        },
        {
            "sha": "b2c3d4e5f60718293a4b5c6d7e8f90123456789ab0",
            "title": "test: 补充链路用例",
            "author": "lisi",
            "additions": 18,
            "deletions": 2,
            "files_changed": 2,
        },
    ]
    import_payload = {
        "project_id": project_id,
        "story_id": linked_id,
        "branch_name": "feature/smoke-1",
        "base_branch": "main",
        "commits": commits,
    }
    response = zhangsan.post(code + "commits/", import_payload, format="json")
    assert response.status_code == 201 and response.data["created"] == 2, response.data
    response = zhangsan.post(code + "commits/", import_payload, format="json")
    assert response.status_code == 201 and response.data["created"] == 0, response.data
    response = lisi.post(code + "commits/", import_payload, format="json")
    assert response.status_code == 403, (response.status_code, response.data)
    checks.append("commit 导入去重 / 仅管理员可导入")

    response = zhangsan.get(code + "commits/", {"story_id": linked_id})
    assert response.status_code == 200 and response.data["summary"]["total"] == 2, response.data
    assert response.data["summary"]["additions"] == 60
    assert response.data["summary"]["files_changed"] == 5
    response = zhangsan.get(code + f"commits/{commits[0]['sha']}/")
    assert response.status_code == 200, (response.status_code, response.data)
    assert response.data["story_brief"]["story_no"] == linked["story_no"], response.data
    assert "/commit/" in response.data["repo_links"]["commit"]
    checks.append("commit 列表总信息 / 详情与外链")

    response = zhangsan.get(f"{base}{linked_id}/")
    summary = response.data["branch_summary"]
    assert summary["branch_name"] == "feature/smoke-1" and summary["base_branch"] == "main", summary
    assert summary["total"] == 2 and summary["additions"] == 60, summary
    assert summary["author_count"] == 2, summary
    assert summary["repo_links"]["branch"].endswith("feature/smoke-1"), summary
    assert "compare/main...feature/smoke-1" in summary["repo_links"]["compare"], summary
    checks.append("需求单详情返回分支汇总与跳转链接")

    response = zhangsan.post(code + "sync-branch/", {"story_id": linked_id}, format="json")
    assert response.status_code == 400 and response.data["code"] == "LOCAL_REPO_MISSING", response.data
    response = zhangsan.delete(code + f"projects/{project_id}/")
    assert response.status_code == 204, (response.status_code, response.data)
    checks.append("本地仓库未配置时明确报错 / 项目可删除")

    # 项目隔离：需求列表 / 工作看板 / commit 列表都只返回当前项目的数据
    demo_project = zhangsan.get(code + "projects/").data[0]
    demo_project_id = demo_project["id"]
    response = zhangsan.get(base, {"project_id": demo_project_id})
    scoped_rows = response.data["results"]
    assert all(row["project"]["id"] == demo_project_id for row in scoped_rows), response.data
    response = zhangsan.get(f"{base}stats/", {"project_id": demo_project_id})
    assert response.status_code == 200 and response.data["project"]["id"] == demo_project_id, response.data
    assert response.data["total"] == len(scoped_rows), response.data
    response = zhangsan.get(code + "commits/", {"project_id": demo_project_id})
    assert response.status_code == 200 and all(
        row["project"] == demo_project_id for row in response.data["results"]
    ), response.data
    response = zhangsan.get(f"{base}stats/", {"project_id": 999999})
    assert response.status_code == 400, (response.status_code, response.data)
    checks.append("按项目隔离：需求列表 / 看板 / commit 只返回当前项目")

    print(f"演示库已重置并跑通 {len(checks)} 组检查：")
    for index, name in enumerate(checks, 1):
        print(f"  {index:>2}. {name} OK")
    print("\n后端端到端烟测全部通过")


if __name__ == "__main__":
    main()
