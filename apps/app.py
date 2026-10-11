from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import csv
import io
from datetime import datetime, timedelta, date
from pathlib import Path
from copy import deepcopy
import uuid

app = Flask(__name__)

DATA_FILE = Path(__file__).parent / "data" / "tracker_data.json"

# ─────────────────────────────────────────────
# Default data structure
# ─────────────────────────────────────────────
DEFAULT_DATA = {
    "settings": {
        "start_mode": "first_log",
        "custom_start_date": None,
        "tracking_start_date": None,
        "user_name": "",
        "target_end_date": None,
    },
    "entries": {},
    "resources": [],
    "projects": [],
    "goals": {
        "long_term": [],
        "monthly_checkpoints": [],
        "quarterly_milestones": []
    },
    "achievements": [],
    "skills": {
        "Programming": {"level": "Not Started", "notes": "", "evidence": []},
        "Algorithms": {"level": "Not Started", "notes": "", "evidence": []},
        "Data Structures": {"level": "Not Started", "notes": "", "evidence": []},
        "Mathematics": {"level": "Not Started", "notes": "", "evidence": []},
        "Web Development": {"level": "Not Started", "notes": "", "evidence": []},
        "Software Engineering": {"level": "Not Started", "notes": "", "evidence": []},
        "Git / GitHub": {"level": "Not Started", "notes": "", "evidence": []},
        "Databases": {"level": "Not Started", "notes": "", "evidence": []},
        "Operating Systems": {"level": "Not Started", "notes": "", "evidence": []},
        "Networking": {"level": "Not Started", "notes": "", "evidence": []},
        "AI / ML": {"level": "Not Started", "notes": "", "evidence": []},
        "Research": {"level": "Not Started", "notes": "", "evidence": []},
        "Communication": {"level": "Not Started", "notes": "", "evidence": []},
        "Systems / Low-level": {"level": "Not Started", "notes": "", "evidence": []},
    },
    "scholarships": [],
    "quick_links": [
        {"id": "1", "name": "LeetCode", "url": "https://leetcode.com", "icon": "💻"},
        {"id": "2", "name": "GitHub", "url": "https://github.com", "icon": "🐙"},
        {"id": "3", "name": "arXiv", "url": "https://arxiv.org", "icon": "📄"},
        {"id": "4", "name": "Overleaf", "url": "https://overleaf.com", "icon": "✍️"},
    ]
}

def get_today():
    return datetime.now().strftime("%Y-%m-%d")

def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key, default_val in DEFAULT_DATA.items():
                if key not in data:
                    data[key] = deepcopy(default_val)
            old_file = Path(__file__).parent / "data" / "entries.json"
            if old_file.exists() and not data.get("entries"):
                with open(old_file, "r", encoding="utf-8") as f:
                    data["entries"] = json.load(f)
            return data
        except Exception:
            return deepcopy(DEFAULT_DATA)
    return deepcopy(DEFAULT_DATA)

def save_data(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def has_activity(entry):
    if not entry:
        return False
    return bool(
        entry.get("coding_hours") or
        entry.get("what_coded") or
        entry.get("learned") or
        entry.get("problems_solved") or
        entry.get("project_progress") or
        entry.get("writing_practice")
    )

def ensure_tracking_start(data):
    settings = data["settings"]
    entries = data["entries"]
    if settings["start_mode"] == "today":
        if not settings["tracking_start_date"]:
            settings["tracking_start_date"] = get_today()
    elif settings["start_mode"] == "custom":
        if settings.get("custom_start_date"):
            settings["tracking_start_date"] = settings["custom_start_date"]
    elif settings["start_mode"] == "first_log":
        if entries:
            first = min(entries.keys())
            settings["tracking_start_date"] = first
        else:
            settings["tracking_start_date"] = None
    if settings["tracking_start_date"] and not settings.get("target_end_date"):
        start = datetime.strptime(settings["tracking_start_date"], "%Y-%m-%d")
        settings["target_end_date"] = (start + timedelta(days=730)).strftime("%Y-%m-%d")
    return data

def calculate_stats(data):
    data = ensure_tracking_start(data)
    entries = data["entries"]
    settings = data["settings"]
    start_date = settings.get("tracking_start_date")

    if not entries or not start_date:
        return {
            "total_days": 0, "active_days": 0, "total_coding_hours": 0.0,
            "avg_hours_per_day": 0.0, "current_streak": 0, "longest_streak": 0,
            "total_problems": 0, "total_papers": 0, "tracking_start_date": start_date,
            "days_since_start": 0, "days_remaining": 730, "percent_complete": 0.0,
            "monthly_hours": 0.0, "monthly_problems": 0, "quarterly_hours": 0.0,
            "target_end_date": None, "projects_count": 0, "achievements_count": 0,
            "resources_count": 0, "completed_projects": 0,
        }

    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    today = datetime.now().date()
    days_since = max(0, (today - start).days)
    days_remaining = max(0, 730 - days_since)
    percent = min(100.0, round((days_since / 730) * 100, 1))

    total_hours = 0.0
    total_problems = 0
    total_papers = 0
    active_days = 0

    for d, e in entries.items():
        try:
            ed = datetime.strptime(d, "%Y-%m-%d").date()
        except:
            continue
        if ed < start:
            continue
        if has_activity(e):
            active_days += 1
        total_hours += float(e.get("coding_hours") or 0)
        total_problems += int(e.get("problems_solved") or 0)
        if (e.get("papers_read") or "").strip():
            total_papers += 1

    avg = round(total_hours / active_days, 2) if active_days else 0.0

    current_streak = 0
    check = today
    while True:
        ds = check.strftime("%Y-%m-%d")
        if ds in entries and has_activity(entries[ds]):
            current_streak += 1
            check -= timedelta(days=1)
        else:
            break

    longest = 0
    temp = 0
    prev = None
    for d in sorted(entries.keys()):
        try:
            ed = datetime.strptime(d, "%Y-%m-%d").date()
        except:
            continue
        if ed < start:
            continue
        if has_activity(entries[d]):
            if prev is None or (ed - prev).days == 1:
                temp += 1
            else:
                temp = 1
            longest = max(longest, temp)
            prev = ed
        else:
            temp = 0

    month_start = today.replace(day=1)
    monthly_hours = 0.0
    monthly_problems = 0
    for d, e in entries.items():
        try:
            ed = datetime.strptime(d, "%Y-%m-%d").date()
        except:
            continue
        if ed >= month_start:
            monthly_hours += float(e.get("coding_hours") or 0)
            monthly_problems += int(e.get("problems_solved") or 0)

    q_start = today - timedelta(days=90)
    quarterly_hours = 0.0
    for d, e in entries.items():
        try:
            ed = datetime.strptime(d, "%Y-%m-%d").date()
        except:
            continue
        if ed >= q_start:
            quarterly_hours += float(e.get("coding_hours") or 0)

    return {
        "total_days": days_since + 1 if start_date else 0,
        "active_days": active_days,
        "total_coding_hours": round(total_hours, 1),
        "avg_hours_per_day": avg,
        "current_streak": current_streak,
        "longest_streak": longest,
        "total_problems": total_problems,
        "total_papers": total_papers,
        "tracking_start_date": start_date,
        "days_since_start": days_since,
        "days_remaining": days_remaining,
        "percent_complete": percent,
        "monthly_hours": round(monthly_hours, 1),
        "monthly_problems": monthly_problems,
        "quarterly_hours": round(quarterly_hours, 1),
        "target_end_date": settings.get("target_end_date"),
        "projects_count": len(data.get("projects", [])),
        "achievements_count": len(data.get("achievements", [])),
        "resources_count": len(data.get("resources", [])),
        "completed_projects": len([p for p in data.get("projects", []) if p.get("status") == "Completed"]),
    }

def get_ai_recommendation(data, stats):
    entries = data["entries"]
    skills = data.get("skills", {})
    projects = data.get("projects", [])
    recent_hours = 0
    recent_problems = 0
    recent_days = 0
    for i in range(7):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        if d in entries:
            e = entries[d]
            if has_activity(e):
                recent_days += 1
            recent_hours += float(e.get("coding_hours") or 0)
            recent_problems += int(e.get("problems_solved") or 0)

    weak_skills = [name for name, s in skills.items() if s.get("level") in ("Not Started", "Learning")]
    active_projects = [p for p in projects if p.get("status") == "In Progress"]
    recommendations = []

    if stats["current_streak"] == 0 and stats["active_days"] > 0:
        recommendations.append("You broke your streak. Do a short focused session today (even 45–60 min) to restart momentum.")
    elif stats["current_streak"] >= 7:
        recommendations.append(f"Strong streak ({stats['current_streak']} days). Protect it — keep today's session realistic but consistent.")

    if recent_problems < 5 and recent_days >= 3:
        recommendations.append("Problem-solving volume is low this week. Aim for 3–5 focused problems today (arrays / hashing / two pointers).")

    if active_projects:
        p = active_projects[0]
        recommendations.append(f"Continue project «{p.get('title', 'Untitled')}». Log what you implement and any blockers.")
    elif stats["active_days"] > 14 and len(projects) < 2:
        recommendations.append("You have consistent study days but few projects. Start a small portfolio project this week.")

    if "Algorithms" in weak_skills or "Data Structures" in weak_skills:
        recommendations.append("Algorithms / Data Structures still early. Spend part of today on fundamentals + 2 easy-medium problems.")

    if recent_hours < 5 and recent_days >= 4:
        recommendations.append("Hours are moderate. Consider one deeper 90–120 min block instead of many short ones.")

    if not recommendations:
        if stats["active_days"] == 0:
            recommendations.append("No logs yet. Start with 60–90 minutes of Python fundamentals or CS50 and log it.")
        else:
            recommendations.append("Solid base. Today: 1 focused coding block + 2–3 problems + short note on what you learned.")

    return recommendations[:3]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/data")
def api_data():
    data = load_data()
    data = ensure_tracking_start(data)
    stats = calculate_stats(data)
    recommendation = get_ai_recommendation(data, stats)
    return jsonify({
        "data": data,
        "stats": stats,
        "recommendation": recommendation,
        "today": get_today()
    })

@app.route("/api/save_entry", methods=["POST"])
def save_entry():
    payload = request.json
    date = payload.get("date") or get_today()
    data = load_data()
    data["entries"][date] = {
        "coding_hours": payload.get("coding_hours", ""),
        "what_coded": payload.get("what_coded", ""),
        "learned": payload.get("learned", ""),
        "problems_solved": payload.get("problems_solved", ""),
        "problems_notes": payload.get("problems_notes", ""),
        "papers_read": payload.get("papers_read", ""),
        "writing_practice": payload.get("writing_practice", ""),
        "project_progress": payload.get("project_progress", ""),
        "notes": payload.get("notes", ""),
        "mood": payload.get("mood", ""),
        "mood_emoji": payload.get("mood_emoji", ""),
        "updated_at": datetime.now().isoformat()
    }
    data = ensure_tracking_start(data)
    save_data(data)
    stats = calculate_stats(data)
    return jsonify({"success": True, "stats": stats, "data": data})

@app.route("/api/settings", methods=["POST"])
def update_settings():
    payload = request.json
    data = load_data()
    data["settings"].update(payload)
    data = ensure_tracking_start(data)
    save_data(data)
    return jsonify({"success": True, "settings": data["settings"], "stats": calculate_stats(data)})

@app.route("/api/resource", methods=["POST", "PUT", "DELETE"])
def manage_resource():
    data = load_data()
    payload = request.json or {}
    if request.method == "POST":
        resource = {
            "id": str(uuid.uuid4())[:8],
            "title": payload.get("title", ""),
            "url": payload.get("url", ""),
            "type": payload.get("type", "URL"),
            "topic": payload.get("topic", ""),
            "tags": payload.get("tags", []),
            "status": payload.get("status", "To Read"),
            "date_added": get_today(),
            "notes": payload.get("notes", ""),
            "rating": payload.get("rating", 0),
            "linked_projects": payload.get("linked_projects", []),
            "linked_goals": payload.get("linked_goals", []),
        }
        data["resources"].append(resource)
        save_data(data)
        return jsonify({"success": True, "resource": resource})
    elif request.method == "PUT":
        rid = payload.get("id")
        for i, r in enumerate(data["resources"]):
            if r["id"] == rid:
                data["resources"][i].update(payload)
                save_data(data)
                return jsonify({"success": True, "resource": data["resources"][i]})
        return jsonify({"success": False, "error": "Not found"}), 404
    elif request.method == "DELETE":
        rid = payload.get("id")
        data["resources"] = [r for r in data["resources"] if r["id"] != rid]
        save_data(data)
        return jsonify({"success": True})

@app.route("/api/project", methods=["POST", "PUT", "DELETE"])
def manage_project():
    data = load_data()
    payload = request.json or {}
    if request.method == "POST":
        project = {
            "id": str(uuid.uuid4())[:8],
            "title": payload.get("title", ""),
            "description": payload.get("description", ""),
            "technologies": payload.get("technologies", []),
            "start_date": payload.get("start_date", get_today()),
            "deadline": payload.get("deadline", ""),
            "progress": payload.get("progress", 0),
            "status": payload.get("status", "Planning"),
            "github_url": payload.get("github_url", ""),
            "live_url": payload.get("live_url", ""),
            "notes": payload.get("notes", ""),
            "learned": payload.get("learned", ""),
            "problems": payload.get("problems", ""),
            "result": payload.get("result", ""),
            "screenshots": payload.get("screenshots", []),
        }
        data["projects"].append(project)
        save_data(data)
        return jsonify({"success": True, "project": project})
    elif request.method == "PUT":
        pid = payload.get("id")
        for i, p in enumerate(data["projects"]):
            if p["id"] == pid:
                data["projects"][i].update(payload)
                save_data(data)
                return jsonify({"success": True, "project": data["projects"][i]})
        return jsonify({"success": False}), 404
    elif request.method == "DELETE":
        pid = payload.get("id")
        data["projects"] = [p for p in data["projects"] if p["id"] != pid]
        save_data(data)
        return jsonify({"success": True})

@app.route("/api/achievement", methods=["POST", "PUT", "DELETE"])
def manage_achievement():
    data = load_data()
    payload = request.json or {}
    if request.method == "POST":
        ach = {
            "id": str(uuid.uuid4())[:8],
            "title": payload.get("title", ""),
            "date": payload.get("date", get_today()),
            "category": payload.get("category", "Project"),
            "description": payload.get("description", ""),
            "skills": payload.get("skills", []),
            "evidence_links": payload.get("evidence_links", []),
            "github_links": payload.get("github_links", []),
            "impact": payload.get("impact", ""),
            "reflection": payload.get("reflection", ""),
            "scholarship_useful": payload.get("scholarship_useful", True),
        }
        data["achievements"].append(ach)
        save_data(data)
        return jsonify({"success": True, "achievement": ach})
    elif request.method == "PUT":
        aid = payload.get("id")
        for i, a in enumerate(data["achievements"]):
            if a["id"] == aid:
                data["achievements"][i].update(payload)
                save_data(data)
                return jsonify({"success": True})
        return jsonify({"success": False}), 404
    elif request.method == "DELETE":
        aid = payload.get("id")
        data["achievements"] = [a for a in data["achievements"] if a["id"] != aid]
        save_data(data)
        return jsonify({"success": True})

@app.route("/api/skill", methods=["PUT"])
def update_skill():
    payload = request.json
    name = payload.get("name")
    data = load_data()
    if name in data["skills"]:
        data["skills"][name].update({
            "level": payload.get("level", data["skills"][name]["level"]),
            "notes": payload.get("notes", data["skills"][name].get("notes", "")),
            "evidence": payload.get("evidence", data["skills"][name].get("evidence", [])),
        })
        save_data(data)
        return jsonify({"success": True, "skill": data["skills"][name]})
    return jsonify({"success": False}), 404

@app.route("/api/scholarship", methods=["POST", "PUT", "DELETE"])
def manage_scholarship():
    data = load_data()
    payload = request.json or {}
    if request.method == "POST":
        sch = {
            "id": str(uuid.uuid4())[:8],
            "name": payload.get("name", ""),
            "country": payload.get("country", ""),
            "degree": payload.get("degree", ""),
            "deadline": payload.get("deadline", ""),
            "scholarship_deadline": payload.get("scholarship_deadline", ""),
            "status": payload.get("status", "Researching"),
            "requirements": payload.get("requirements", {
                "transcript": False, "cv": False, "personal_statement": False,
                "scholarship_essay": False, "recommendation_letters": False,
                "english_test": False, "portfolio": False, "projects": False,
                "financial_documents": False, "application_submitted": False
            }),
            "notes": payload.get("notes", ""),
            "links": payload.get("links", []),
        }
        data["scholarships"].append(sch)
        save_data(data)
        return jsonify({"success": True, "scholarship": sch})
    elif request.method == "PUT":
        sid = payload.get("id")
        for i, s in enumerate(data["scholarships"]):
            if s["id"] == sid:
                data["scholarships"][i].update(payload)
                save_data(data)
                return jsonify({"success": True})
        return jsonify({"success": False}), 404
    elif request.method == "DELETE":
        sid = payload.get("id")
        data["scholarships"] = [s for s in data["scholarships"] if s["id"] != sid]
        save_data(data)
        return jsonify({"success": True})

@app.route("/api/quick_link", methods=["POST", "PUT", "DELETE"])
def manage_quick_link():
    data = load_data()
    payload = request.json or {}
    if request.method == "POST":
        link = {
            "id": str(uuid.uuid4())[:8],
            "name": payload.get("name", ""),
            "url": payload.get("url", ""),
            "icon": payload.get("icon", "🔗"),
        }
        data["quick_links"].append(link)
        save_data(data)
        return jsonify({"success": True, "link": link})
    elif request.method == "PUT":
        if "links" in payload:
            data["quick_links"] = payload["links"]
            save_data(data)
            return jsonify({"success": True})
        lid = payload.get("id")
        for i, l in enumerate(data["quick_links"]):
            if l["id"] == lid:
                data["quick_links"][i].update(payload)
                save_data(data)
                return jsonify({"success": True})
        return jsonify({"success": False}), 404
    elif request.method == "DELETE":
        lid = payload.get("id")
        data["quick_links"] = [l for l in data["quick_links"] if l["id"] != lid]
        save_data(data)
        return jsonify({"success": True})

@app.route("/api/goals", methods=["POST", "PUT"])
def manage_goals():
    data = load_data()
    payload = request.json or {}
    if "long_term" in payload:
        data["goals"]["long_term"] = payload["long_term"]
    if "monthly_checkpoints" in payload:
        data["goals"]["monthly_checkpoints"] = payload["monthly_checkpoints"]
    if "quarterly_milestones" in payload:
        data["goals"]["quarterly_milestones"] = payload["quarterly_milestones"]
    if payload.get("generate_quarterly") and data["goals"]["long_term"] and not data["goals"]["quarterly_milestones"]:
        data["goals"]["quarterly_milestones"] = generate_quarterly_milestones(data)
    if payload.get("generate_monthly"):
        data["goals"]["monthly_checkpoints"] = generate_monthly_checkpoints(data)
    save_data(data)
    return jsonify({"success": True, "goals": data["goals"]})

def generate_quarterly_milestones(data):
    start = data["settings"].get("tracking_start_date") or get_today()
    start_dt = datetime.strptime(start, "%Y-%m-%d")
    milestones = []
    templates = [
        {"title": "Q1 – Foundations", "objectives": ["Python fundamentals", "Git basics", "First 50 problems", "1 small project", "Read 4 technical articles"]},
        {"title": "Q2 – Core CS", "objectives": ["Data Structures", "Basic Algorithms", "2 projects", "100 problems total", "Start C/C++ or systems basics"]},
        {"title": "Q3 – Depth + Projects", "objectives": ["Intermediate algorithms", "1 substantial project", "LaTeX + paper writing practice", "150+ problems", "Join research/club if possible"]},
        {"title": "Q4 – Portfolio Strength", "objectives": ["Strong portfolio project", "Demonstrated skills in 3+ areas", "200+ problems", "First research-style writeup", "English academic writing"]},
        {"title": "Q5 – Advanced Topics", "objectives": ["Advanced DS/Algo or Systems", "Open source contribution or competition", "Research exposure", "300+ problems", "Clear scholarship targets"]},
        {"title": "Q6 – Evidence Building", "objectives": ["Multiple demonstrated skills", "2–3 strong projects", "Papers/articles written", "Competition or research output", "CV + portfolio ready"]},
        {"title": "Q7 – Application Prep", "objectives": ["Finalize portfolio", "Strong letters of recommendation path", "Scholarship essays drafts", "English test if needed", "Target uni shortlist"]},
        {"title": "Q8 – Final Push", "objectives": ["Submit applications", "Polish all evidence", "Final projects/research", "Interview preparation", "Backup plans"]},
    ]
    for i, t in enumerate(templates):
        end = start_dt + timedelta(days=90 * (i + 1))
        milestones.append({
            "id": str(uuid.uuid4())[:8],
            "quarter": i + 1,
            "title": t["title"],
            "objectives": t["objectives"],
            "targets": {},
            "completed_pct": 0,
            "evidence": [],
            "deadline": end.strftime("%Y-%m-%d"),
            "status": "Upcoming" if i > 0 else "Current",
        })
    return milestones

def generate_monthly_checkpoints(data):
    stats = calculate_stats(data)
    skills = data.get("skills", {})
    weak = [n for n, s in skills.items() if s.get("level") in ("Not Started", "Learning")]
    month = datetime.now().strftime("%B %Y")
    tasks = []
    if stats["total_coding_hours"] < 40:
        tasks.append("Complete Python fundamentals / core syntax")
    if stats["total_problems"] < 30:
        tasks.append(f"Solve at least {max(20, 30 - stats['total_problems'])} problems this month")
    if len(data.get("projects", [])) < 1:
        tasks.append("Build and finish 1 small portfolio project")
    if "Git / GitHub" in weak:
        tasks.append("Learn Git properly and push all work to GitHub")
    if stats["total_papers"] < 2:
        tasks.append("Read and summarize 2 technical papers/articles")
    if not tasks:
        tasks = ["Deepen weakest skill area", "Advance main project significantly", "Solve 25+ quality problems", "Write one technical summary"]
    return [{
        "id": str(uuid.uuid4())[:8],
        "month": month,
        "tasks": tasks,
        "status": "Active",
        "completed": []
    }]

@app.route("/api/export")
def export_data():
    data = load_data()
    fmt = request.args.get("format", "json")
    if fmt == "json":
        buf = io.BytesIO()
        buf.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))
        buf.seek(0)
        return send_file(buf, mimetype="application/json", as_attachment=True,
                         download_name=f"lockin_backup_{get_today()}.json")
    elif fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["date", "coding_hours", "problems_solved", "mood", "what_coded", "learned", "papers_read", "writing_practice", "project_progress", "notes"])
        for d, e in sorted(data["entries"].items()):
            writer.writerow([
                d, e.get("coding_hours", ""), e.get("problems_solved", ""), e.get("mood", ""),
                e.get("what_coded", ""), e.get("learned", ""), e.get("papers_read", ""),
                e.get("writing_practice", ""), e.get("project_progress", ""), e.get("notes", "")
            ])
        buf = io.BytesIO()
        buf.write(output.getvalue().encode("utf-8"))
        buf.seek(0)
        return send_file(buf, mimetype="text/csv", as_attachment=True,
                         download_name=f"lockin_entries_{get_today()}.csv")
    return jsonify({"error": "Unknown format"}), 400

@app.route("/api/import", methods=["POST"])
def import_data():
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file"}), 400
    f = request.files["file"]
    try:
        content = json.load(f)
        if "entries" in content or "settings" in content:
            save_data(content)
            return jsonify({"success": True})
        return jsonify({"success": False, "error": "Invalid format"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/charts")
def chart_data():
    data = load_data()
    entries = data["entries"]
    hours_series = []
    problems_series = []
    mood_series = []
    for i in range(59, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        e = entries.get(d, {})
        hours_series.append({"date": d, "hours": float(e.get("coding_hours") or 0)})
        problems_series.append({"date": d, "count": int(e.get("problems_solved") or 0)})
        mood_series.append({"date": d, "mood": int(e.get("mood") or 0)})

    heatmap = []
    for i in range(26 * 7 - 1, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        e = entries.get(d, {})
        val = 0
        if has_activity(e):
            h = float(e.get("coding_hours") or 0)
            if h >= 3: val = 4
            elif h >= 1.5: val = 3
            elif h >= 0.5: val = 2
            else: val = 1
        heatmap.append({"date": d, "value": val})

    level_map = {"Not Started": 0, "Learning": 1, "Practicing": 2, "Comfortable": 3, "Demonstrated": 4}
    skills_radar = [{"skill": k, "value": level_map.get(v.get("level", "Not Started"), 0)} for k, v in data.get("skills", {}).items()]

    return jsonify({
        "hours": hours_series,
        "problems": problems_series,
        "mood": mood_series,
        "heatmap": heatmap,
        "skills": skills_radar
    })

if __name__ == "__main__":
    print("\n" + "="*50)
    print("  ⚡  LOCK-IN COMMAND CENTER")
    print("  2-Year CS Scholarship Tracker")
    print("="*50)
    print("\n  Open →  http://127.0.0.1:5000\n")
    print("  Data folder is inside this directory.")
    print("  Put the whole folder in Google Drive / OneDrive to sync.\n")
    app.run(debug=True, port=5000)