from conftest import auth, event_payload, login, rubric


def create_event(client, organizer_token, code="TEST-001"):
    response = client.post("/events", headers=auth(organizer_token), json=event_payload(code))
    assert response.status_code == 201, response.text
    return response.json()


def set_event_status(client, organizer_token, event_id, status):
    response = client.patch(f"/events/{event_id}", headers=auth(organizer_token), json={"status": status})
    assert response.status_code == 200, response.text
    return response.json()


def register_participant(client, token, event_id):
    response = client.post(f"/events/{event_id}/register", headers=auth(token), json={})
    assert response.status_code == 200, response.text
    return response.json()


def create_team_and_project(client, participant_token, event_id, name, user_id):
    team = client.post(f"/events/{event_id}/teams", headers=auth(participant_token), json={"eventId": event_id, "name": name, "track": "General"})
    assert team.status_code == 201, team.text
    project = client.post(
        f"/events/{event_id}/projects",
        headers=auth(participant_token),
        json={"eventId": event_id, "teamId": team.json()["id"], "title": f"{name} Project", "problem": "Problem", "solution": "Solution", "techStack": ["Python"]},
    )
    assert project.status_code == 201, project.text
    return team.json(), project.json()


def test_auth_and_role_enforcement(client, users):
    assert client.post("/auth/login", json={"email": "organizer@example.com", "password": "wrong"}).status_code == 401
    participant = login(client, "participant1@example.com")
    assert client.post("/events", headers=auth(participant), json=event_payload()).status_code == 403


def test_duplicate_event_code_is_409(client, users):
    organizer = login(client, "organizer@example.com")
    create_event(client, organizer)
    response = client.post("/events", headers=auth(organizer), json=event_payload())
    assert response.status_code == 409


def test_invalid_rubric_rejected(client, users):
    organizer = login(client, "organizer@example.com")
    payload = event_payload("BAD-RUBRIC")
    payload["rubric"][0]["weight"] = 50
    payload["rubric"][1]["weight"] = 30
    response = client.post("/events", headers=auth(organizer), json=payload)
    assert response.status_code == 422


def test_registration_and_duplicate_registration(client, users):
    organizer = login(client, "organizer@example.com")
    event = create_event(client, organizer)
    participant = login(client, "participant1@example.com")
    assert register_participant(client, participant, event["id"])["status"] == "approved"
    duplicate = client.post(f"/events/{event['id']}/register", headers=auth(participant), json={})
    assert duplicate.status_code == 409


def test_team_capacity_and_project_minimum(client, users):
    organizer = login(client, "organizer@example.com")
    payload = event_payload("TEAM-001")
    payload["minTeamSize"] = 2
    event_response = client.post("/events", headers=auth(organizer), json=payload)
    event = event_response.json()
    participant = login(client, "participant1@example.com")
    register_participant(client, participant, event["id"])
    team = client.post(f"/events/{event['id']}/teams", headers=auth(participant), json={"eventId": event["id"], "name": "Solo", "track": "General"})
    assert team.status_code == 201
    project = client.post(f"/events/{event['id']}/projects", headers=auth(participant), json={"eventId": event["id"], "teamId": team.json()["id"], "title": "Too Early"})
    assert project.status_code == 409


def test_blind_assignment_conflict_and_identity_isolation(client, users):
    organizer = login(client, "organizer@example.com")
    event = create_event(client, organizer, "BLIND-001")
    p1 = login(client, "participant1@example.com")
    p2 = login(client, "participant2@example.com")
    register_participant(client, p1, event["id"])
    register_participant(client, p2, event["id"])
    set_event_status(client, organizer, event["id"], "submission")
    _, project1 = create_team_and_project(client, p1, event["id"], "Alpha", users["participant1@example.com"].id)
    _, project2 = create_team_and_project(client, p2, event["id"], "Beta", users["participant2@example.com"].id)
    set_event_status(client, organizer, event["id"], "judging")
    j1 = login(client, "judge1@example.com")
    j2 = login(client, "judge2@example.com")

    conflict = client.post("/conflicts", headers=auth(j1), json={"projectId": project1["id"], "reason": "Prior collaboration"})
    assert conflict.status_code == 200
    blocked = client.post("/assignments", headers=auth(organizer), json={"projectId": project1["id"], "judgeId": users["judge1@example.com"].id})
    assert blocked.status_code == 409

    for project_id in [project1["id"], project2["id"]]:
        for judge_id in [users["judge1@example.com"].id, users["judge2@example.com"].id]:
            if not (project_id == project1["id"] and judge_id == users["judge1@example.com"].id):
                response = client.post("/assignments", headers=auth(organizer), json={"projectId": project_id, "judgeId": judge_id})
                assert response.status_code == 200, response.text

    blind = client.get(f"/projects/{project1['id']}", headers=auth(j2))
    assert blind.status_code == 200
    body = blind.json()
    assert body["members"] == []
    assert body["teamName"] == ""
    assert "Participant One" not in str(body)
    assert users["judge1@example.com"].id not in str(body.get("scores"))


def test_review_state_machine_and_score_validation(client, users):
    organizer = login(client, "organizer@example.com")
    event = create_event(client, organizer, "REVIEW-001")
    p1 = login(client, "participant1@example.com")
    register_participant(client, p1, event["id"])
    set_event_status(client, organizer, event["id"], "submission")
    _, project = create_team_and_project(client, p1, event["id"], "Alpha", users["participant1@example.com"].id)
    set_event_status(client, organizer, event["id"], "judging")
    judge = login(client, "judge1@example.com")
    client.post("/assignments", headers=auth(organizer), json={"projectId": project["id"], "judgeId": users["judge1@example.com"].id})

    invalid = client.post("/reviews", headers=auth(judge), json={"projectId": project["id"], "scores": {"innovation": 11, "technical": 8}, "status": "finalized", "justifications": {"innovation": "Clear evidence.", "technical": "Working implementation."}})
    assert invalid.status_code == 422
    missing = client.post("/reviews", headers=auth(judge), json={"projectId": project["id"], "scores": {"innovation": 8}, "status": "finalized", "justifications": {"innovation": "Clear evidence.", "technical": "Working implementation."}})
    assert missing.status_code == 422
    direct_lock = client.post("/reviews", headers=auth(judge), json={"projectId": project["id"], "scores": {"innovation": 8, "technical": 8}, "status": "locked", "justifications": {"innovation": "Clear evidence.", "technical": "Working implementation."}})
    assert direct_lock.status_code == 409

    draft = client.post("/reviews", headers=auth(judge), json={"projectId": project["id"], "scores": {"innovation": 8}, "status": "draft"})
    assert draft.status_code == 200
    finalized = client.post("/reviews", headers=auth(judge), json={"projectId": project["id"], "scores": {"innovation": 8, "technical": 8}, "status": "finalized", "justifications": {"innovation": "Clear evidence.", "technical": "Working implementation."}})
    assert finalized.status_code == 200
    locked = client.post("/reviews", headers=auth(judge), json={"projectId": project["id"], "scores": {"innovation": 8, "technical": 8}, "status": "locked", "justifications": {"innovation": "Clear evidence.", "technical": "Working implementation."}})
    assert locked.status_code == 200
    after = client.post("/reviews", headers=auth(judge), json={"projectId": project["id"], "scores": {"innovation": 9, "technical": 9}, "status": "locked", "justifications": {"innovation": "Clear evidence.", "technical": "Working implementation."}})
    assert after.status_code == 409


def test_results_snapshot_and_participant_visibility(client, users):
    organizer = login(client, "organizer@example.com")
    event = create_event(client, organizer, "RESULT-001")
    p1 = login(client, "participant1@example.com")
    p2 = login(client, "participant2@example.com")
    register_participant(client, p1, event["id"])
    register_participant(client, p2, event["id"])
    set_event_status(client, organizer, event["id"], "submission")
    _, project1 = create_team_and_project(client, p1, event["id"], "Alpha", users["participant1@example.com"].id)
    _, project2 = create_team_and_project(client, p2, event["id"], "Beta", users["participant2@example.com"].id)
    set_event_status(client, organizer, event["id"], "judging")
    j1 = login(client, "judge1@example.com")
    j2 = login(client, "judge2@example.com")
    for project in [project1, project2]:
        for judge_token, judge_id in [(j1, users["judge1@example.com"].id), (j2, users["judge2@example.com"].id)]:
            assert client.post("/assignments", headers=auth(organizer), json={"projectId": project["id"], "judgeId": judge_id}).status_code == 200
            scores = {"innovation": 9 if project["id"] == project1["id"] else 6, "technical": 8 if judge_id == users["judge1@example.com"].id else 7}
            assert client.post("/reviews", headers=auth(judge_token), json={"projectId": project["id"], "scores": scores, "status": "finalized", "justifications": {"innovation": "Clear evidence.", "technical": "Working implementation."}}).status_code == 200

    calculated = client.post(f"/events/{event['id']}/results/calculate", headers=auth(organizer), json={})
    assert calculated.status_code == 200, calculated.text
    snapshot = calculated.json()["snapshotId"]
    assert snapshot
    assert all(row["projectId"] for row in calculated.json()["results"])
    published = client.post(f"/events/{event['id']}/results/publish", headers=auth(organizer))
    assert published.status_code == 200
    assert published.json()["snapshotId"] == snapshot
    participant_results = client.get(f"/events/{event['id']}/results", headers=auth(p1))
    assert participant_results.status_code == 200
    assert len(participant_results.json()) == 1
    assert participant_results.json()[0]["projectId"] == project1["id"]


def test_approval_required_registration(client, users):
    organizer = login(client, "organizer@example.com")
    payload = event_payload("APPROVAL-001")
    payload["registrationMode"] = "approval-required"
    event = client.post("/events", headers=auth(organizer), json=payload).json()
    participant = login(client, "participant1@example.com")
    registration = client.post(f"/events/{event['id']}/register", headers=auth(participant), json={})
    assert registration.status_code == 200
    assert registration.json()["status"] == "pending"
    participants = client.get(f"/events/{event['id']}/participants", headers=auth(organizer))
    assert participants.status_code == 200
    approve = client.patch(f"/events/{event['id']}/participants/{users['participant1@example.com'].id}", headers=auth(organizer), json={"status": "approved"})
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"


def test_project_update_persists_version_and_backend_failure_does_not_fake_success(client, users):
    organizer = login(client, "organizer@example.com")
    event = create_event(client, organizer, "UPDATE-001")
    participant = login(client, "participant1@example.com")
    register_participant(client, participant, event["id"])
    set_event_status(client, organizer, event["id"], "submission")
    _, project = create_team_and_project(client, participant, event["id"], "Alpha", users["participant1@example.com"].id)
    updated = client.patch(f"/projects/{project['id']}", headers=auth(participant), json={"title": "Updated Project", "summary": "Changed title"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Updated Project"
    assert updated.json()["versions"][-1]["version"] == 2
    unauthorized = client.patch(f"/projects/{project['id']}", headers=auth(login(client, "judge1@example.com")), json={"title": "Illegal"})
    assert unauthorized.status_code == 403


def test_private_event_requires_access_code(client, users):
    organizer = login(client, "organizer@example.com")
    payload = event_payload("PRIVATE-001")
    payload.update({"isPublic": False, "accessCode": "SECRET-42"})
    event = client.post("/events", headers=auth(organizer), json=payload).json()
    participant = login(client, "participant1@example.com")
    bad = client.post(f"/events/{event['id']}/register", headers=auth(participant), json={"accessCode": "WRONG"})
    assert bad.status_code == 403
    good = client.post(f"/events/{event['id']}/register", headers=auth(participant), json={"accessCode": "SECRET-42"})
    assert good.status_code == 200


def test_api_namespace_refresh_cookie_and_lifecycle_guards(client, users):
    login_response = client.post("/api/auth/login", json={"email": "organizer@example.com", "password": "password123"})
    assert login_response.status_code == 200
    assert "agamotto_refresh" in login_response.cookies
    access = login_response.json()["accessToken"]
    assert client.get("/api/auth/me", headers=auth(access)).status_code == 200
    refreshed = client.post("/api/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["accessToken"]

    event = create_event(client, access, "LIFE-001")
    participant = login(client, "participant1@example.com")
    assert client.post(f"/events/{event['id']}/register", headers=auth(participant), json={}).status_code == 200
    # Cannot skip lifecycle phases.
    assert client.patch(f"/events/{event['id']}", headers=auth(access), json={"status": "judging"}).status_code == 409
    assert client.patch(f"/events/{event['id']}", headers=auth(access), json={"status": "submission"}).status_code == 200


def test_justification_reopen_incomplete_publish_and_override(client, users):
    organizer = login(client, "organizer@example.com")
    event = create_event(client, organizer, "HARDEN-001")
    p1 = login(client, "participant1@example.com")
    register_participant(client, p1, event["id"])
    set_event_status(client, organizer, event["id"], "submission")
    _, project = create_team_and_project(client, p1, event["id"], "Hard", users["participant1@example.com"].id)
    set_event_status(client, organizer, event["id"], "judging")
    judge = login(client, "judge1@example.com")
    judge_id = users["judge1@example.com"].id
    assert client.post("/assignments", headers=auth(organizer), json={"projectId": project["id"], "judgeId": judge_id}).status_code == 200

    missing_justification = client.post("/reviews", headers=auth(judge), json={"projectId": project["id"], "scores":{"innovation":8,"technical":8}, "status":"finalized"})
    assert missing_justification.status_code == 422
    finalized = client.post("/reviews", headers=auth(judge), json={"projectId": project["id"], "scores":{"innovation":8,"technical":8}, "justifications":{"innovation":"Original evidence.","technical":"Working evidence."}, "status":"finalized"})
    assert finalized.status_code == 200

    blocked = client.post(f"/events/{event['id']}/results/calculate", headers=auth(organizer), json={})
    assert blocked.status_code == 409
    override = client.post(f"/events/{event['id']}/results/calculate", headers=auth(organizer), json={"override":True,"reason":"One assigned judge unavailable for this fixture."})
    assert override.status_code == 200
    snapshot_id = override.json()["snapshotId"]
    proof = client.get(f"/events/{event['id']}/normalization-proof/{snapshot_id}", headers=auth(organizer))
    assert proof.status_code == 200
    assert proof.json()["statistics"]

    reopen = client.post("/reviews/reopen", headers=auth(organizer), json={"projectId":project["id"],"judgeId":judge_id,"reason":"Correction requested."})
    assert reopen.status_code == 200
    audit = client.get(f"/events/{event['id']}/audit", headers=auth(organizer)).json()
    assert any(row["action"] == "REVIEW_REOPENED_BY_ORGANIZER" for row in audit)


def test_assignment_balancing_and_conflict_block_are_deterministic(client, users):
    organizer = login(client, "organizer@example.com")
    event = create_event(client, organizer, "BALANCE-001")
    p1 = login(client, "participant1@example.com")
    p2 = login(client, "participant2@example.com")
    register_participant(client, p1, event["id"])
    register_participant(client, p2, event["id"])
    set_event_status(client, organizer, event["id"], "submission")
    _, project1 = create_team_and_project(client, p1, event["id"], "One", users["participant1@example.com"].id)
    _, project2 = create_team_and_project(client, p2, event["id"], "Two", users["participant2@example.com"].id)
    set_event_status(client, organizer, event["id"], "judging")
    j1=login(client,"judge1@example.com"); j2=login(client,"judge2@example.com")
    assert client.post("/conflicts", headers=auth(j1), json={"projectId":project1["id"],"reason":"Prior relationship"}).status_code == 200
    assert client.post("/assignments", headers=auth(organizer), json={"projectId":project1["id"],"judgeId":users["judge1@example.com"].id}).status_code == 409
    auto=client.post(f"/events/{event['id']}/auto-assign", headers=auth(organizer))
    assert auto.status_code == 200
    assert auto.json()["created"] >= 2
