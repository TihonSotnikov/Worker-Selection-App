from pathlib import Path

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

ANSWERS = [
    "Меня зовут Пётр, варю уже шесть лет.",
    "Аргоном варю пять лет, в основном нержавейка.",
    "С нержавейкой тоже работал.",
    "НАКС есть, продлевал весной.",
    "Ночью не могу, только дневные смены.",
    "Живу в Южном районе, на машине минут двадцать.",
    "Хочу сто двадцать тысяч на руки.",
    "Столовая важна, остальное неважно.",
    "За пять лет сменил одно место.",
]


def test_status(client):
    data = client.get("/api/status").json()
    assert data["ml"]["roc_auc"] > 0.7
    assert data["insights"]["scenarios"][0]["delta"] < 0


def test_vacancies(client):
    vacancies = client.get("/api/vacancies").json()
    assert len(vacancies) == 6
    assert all(v["candidates_total"] > 0 for v in vacancies)
    assert client.get("/api/vacancies/999").status_code == 404


def test_shortlist(client):
    data = client.get("/api/vacancies/3/shortlist").json()
    assert 0 < len(data["shortlist"]) <= 5
    assert all(r["passes_requirements"] for r in data["shortlist"])
    first = data["shortlist"][0]
    assert first["rank"] == 1
    assert {c["key"] for c in first["comfort"]} == {"shift", "commute", "salary", "amenities", "team"}


def test_candidate_report_requires_same_profession(client):
    shortlist = client.get("/api/vacancies/3/shortlist").json()
    candidate_id = shortlist["shortlist"][0]["candidate_id"]
    report = client.get(f"/api/vacancies/3/candidates/{candidate_id}")
    assert report.status_code == 200
    assert report.json()["report"]["candidate_id"] == candidate_id
    # вакансия 1 — оператор ЧПУ, сварщик туда не подходит
    assert client.get(f"/api/vacancies/1/candidates/{candidate_id}").status_code == 404


def test_full_interview_flow(client, fake_llm):
    interview = client.post("/api/interviews", json={"vacancy_id": 3}).json()
    assert interview["status"] == "active"
    assert interview["total_questions"] == len(ANSWERS)

    for answer in ANSWERS:
        interview = client.post(f"/api/interviews/{interview['id']}/answer", json={"text": answer}).json()
    assert interview["status"] == "ready"
    assert client.post(f"/api/interviews/{interview['id']}/answer", json={"text": "ещё"}).status_code == 409

    done = client.post(f"/api/interviews/{interview['id']}/finish").json()
    assert done["status"] == "done"
    assert "Кандидат: Аргоном варю пять лет" in fake_llm.calls[0]

    report = client.get(f"/api/vacancies/3/candidates/{done['candidate_id']}").json()
    assert report["candidate"]["source"] == "interview"
    checks = {c["skill"]: c for c in report["report"]["skill_checks"]}
    assert checks["tig"]["status"] == "ok"
    assert checks["stainless"]["status"] == "missing"  # цитата не нашлась в ответах — навык не засчитан
    assert not report["report"]["passes_requirements"]
    risks = " ".join(f["text"] for f in report["report"]["risks"])
    assert "только днём" in risks  # ночная вакансия, а кандидат только днём


def test_finish_without_answers_is_rejected(client, fake_llm):
    interview = client.post("/api/interviews", json={"vacancy_id": 1}).json()
    assert client.post(f"/api/interviews/{interview['id']}/finish").status_code == 409


def test_llm_unavailable_returns_503(client, broken_llm):
    interview = client.post("/api/interviews", json={"vacancy_id": 3}).json()
    client.post(f"/api/interviews/{interview['id']}/answer", json={"text": "Варю аргоном пять лет"})
    response = client.post(f"/api/interviews/{interview['id']}/finish")
    assert response.status_code == 503
    assert client.get(f"/api/interviews/{interview['id']}").json()["error"]


def test_upload_transcript(client, fake_llm):
    content = (EXAMPLES / "candidate2.txt").read_bytes()
    response = client.post("/api/vacancies/4/upload", files={"file": ("candidate2.txt", content, "text/plain")})
    assert response.status_code == 201
    candidate_id = response.json()["candidate_id"]
    report = client.get(f"/api/vacancies/4/candidates/{candidate_id}").json()
    assert report["candidate"]["source"] == "upload"
    assert "Искитиме" in report["candidate"]["transcript"]


def test_upload_rejects_unsupported_format(client, fake_llm):
    response = client.post("/api/vacancies/4/upload", files={"file": ("cv.pdf", b"%PDF-1.4 ...", "application/pdf")})
    assert response.status_code == 400
