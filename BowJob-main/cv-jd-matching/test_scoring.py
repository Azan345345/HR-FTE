"""
Test script to verify scoring consistency and changes.
Run: python test_scoring.py
"""

import json
import copy
from improvement_engine import CVImprovementEngine
import os

# Initialize engine
api_key = os.getenv("OPENAI_API_KEY", "test-key")
engine = CVImprovementEngine(api_key=api_key)

# Sample JD
JOB_DESCRIPTION = """
Senior Software Engineer

Requirements:
- 5+ years of experience in software development
- Strong proficiency in Python, JavaScript, React
- Experience with AWS, Docker, Kubernetes
- Knowledge of CI/CD pipelines
- Experience with PostgreSQL, MongoDB databases
- Agile/Scrum methodology experience
- Bachelor's degree in Computer Science or related field

Nice to have:
- GraphQL experience
- Machine Learning knowledge
- Team leadership experience
"""

# Base CV
BASE_CV = {
    "contact_info": {
        "full_name": "John Doe",
        "email": "john@email.com",
        "phone": "+1-555-1234"
    },
    "title": "Software Developer",
    "professional_summary": "Experienced software developer with 6 years of experience.",
    "work_experience": [
        {
            "job_title": "Software Developer",
            "company": "Tech Corp",
            "start_date": "2018-01-01",
            "end_date": "2024-01-01",
            "description": [
                "Developed web applications using JavaScript and React",
                "Worked with databases and APIs"
            ]
        }
    ],
    "education": [
        {
            "degree": "Bachelor of Science in Computer Science",
            "institution": "State University",
            "end_date": "2017"
        }
    ],
    "skills": [
        "JavaScript",
        "React",
        "Python"
    ],
    "projects": None,
    "certifications": None,
    "total_years_of_experience": 6
}


def test_consistency():
    """Test that same inputs produce same scores."""
    print("\n" + "="*60)
    print("TEST 1: CONSISTENCY (same inputs should produce same scores)")
    print("="*60)

    scores = []
    for i in range(3):
        score = engine.calculate_match_score(BASE_CV, JOB_DESCRIPTION)
        scores.append(score["current_match_score"])
        print(f"Run {i+1}: Score = {score['current_match_score']}, Rating = {score['rating']}")

    if len(set(scores)) == 1:
        print("✅ PASS: All scores are identical")
    else:
        print(f"❌ FAIL: Scores vary: {scores}")

    return scores[0]


def test_adding_skills():
    """Test that adding skills increases the score."""
    print("\n" + "="*60)
    print("TEST 2: ADDING SKILLS (should increase score)")
    print("="*60)

    cv = copy.deepcopy(BASE_CV)
    base_score = engine.calculate_match_score(cv, JOB_DESCRIPTION)
    print(f"Base CV (3 skills): {base_score['current_match_score']} | Skills: {base_score['breakdown']['skills_score']}")

    # Add more JD-relevant skills
    cv["skills"].extend(["AWS", "Docker", "Kubernetes", "PostgreSQL", "MongoDB"])
    score_after_skills = engine.calculate_match_score(cv, JOB_DESCRIPTION)
    print(f"After +5 skills (8 total): {score_after_skills['current_match_score']} | Skills: {score_after_skills['breakdown']['skills_score']}")

    diff = score_after_skills['current_match_score'] - base_score['current_match_score']
    if diff > 0:
        print(f"✅ PASS: Score increased by {diff} points")
    else:
        print(f"❌ FAIL: Score did not increase (diff: {diff})")

    return base_score['current_match_score'], score_after_skills['current_match_score']


def test_adding_projects():
    """Test that adding projects increases the score."""
    print("\n" + "="*60)
    print("TEST 3: ADDING PROJECTS (should increase score)")
    print("="*60)

    cv = copy.deepcopy(BASE_CV)
    base_score = engine.calculate_match_score(cv, JOB_DESCRIPTION)
    print(f"Base CV (0 projects): {base_score['current_match_score']} | Projects: {base_score['breakdown']['projects_score']}")

    # Add 1 project
    cv["projects"] = [{"name": "E-commerce Platform", "description": "Built with React and Node.js"}]
    score_1_project = engine.calculate_match_score(cv, JOB_DESCRIPTION)
    print(f"After +1 project: {score_1_project['current_match_score']} | Projects: {score_1_project['breakdown']['projects_score']}")

    # Add 2 more projects (3 total)
    cv["projects"].extend([
        {"name": "CI/CD Pipeline", "description": "Automated deployment with Docker"},
        {"name": "Data Analytics Dashboard", "description": "Built with Python and PostgreSQL"}
    ])
    score_3_projects = engine.calculate_match_score(cv, JOB_DESCRIPTION)
    print(f"After +3 projects: {score_3_projects['current_match_score']} | Projects: {score_3_projects['breakdown']['projects_score']}")

    diff1 = score_1_project['current_match_score'] - base_score['current_match_score']
    diff2 = score_3_projects['current_match_score'] - score_1_project['current_match_score']

    if diff1 > 0 and diff2 > 0:
        print(f"✅ PASS: Score increased correctly (+{diff1}, then +{diff2})")
    else:
        print(f"❌ FAIL: Score progression not correct (diff1: {diff1}, diff2: {diff2})")


def test_experience_years():
    """Test experience scoring."""
    print("\n" + "="*60)
    print("TEST 4: EXPERIENCE YEARS (should scale with years)")
    print("="*60)

    for years in [2, 5, 8, 15]:
        cv = copy.deepcopy(BASE_CV)
        cv["total_years_of_experience"] = years
        score = engine.calculate_match_score(cv, JOB_DESCRIPTION)
        print(f"{years} years: Score = {score['current_match_score']} | Exp: {score['breakdown']['experience_score']}")


def test_education():
    """Test education scoring."""
    print("\n" + "="*60)
    print("TEST 5: EDUCATION (degree vs no degree)")
    print("="*60)

    cv_with_degree = copy.deepcopy(BASE_CV)
    cv_no_degree = copy.deepcopy(BASE_CV)
    cv_no_degree["education"] = []

    score_with = engine.calculate_match_score(cv_with_degree, JOB_DESCRIPTION)
    score_without = engine.calculate_match_score(cv_no_degree, JOB_DESCRIPTION)

    print(f"With degree: {score_with['current_match_score']} | Edu: {score_with['breakdown']['education_score']}")
    print(f"No degree: {score_without['current_match_score']} | Edu: {score_without['breakdown']['education_score']}")

    if score_with['current_match_score'] > score_without['current_match_score']:
        print("✅ PASS: Degree adds value")
    else:
        print("❌ FAIL: Degree not adding value")


def test_full_improvement_cycle():
    """Test a full cycle of improvements."""
    print("\n" + "="*60)
    print("TEST 6: FULL IMPROVEMENT CYCLE")
    print("="*60)

    cv = copy.deepcopy(BASE_CV)

    # Step 1: Initial score
    score1 = engine.calculate_match_score(cv, JOB_DESCRIPTION)
    print(f"Step 1 - Initial: {score1['current_match_score']} ({score1['rating']})")
    print(f"         Breakdown: {score1['breakdown']}")

    # Step 2: Add skills
    cv["skills"].extend(["AWS", "Docker", "CI/CD", "PostgreSQL", "Agile"])
    score2 = engine.calculate_match_score(cv, JOB_DESCRIPTION)
    print(f"Step 2 - +5 Skills: {score2['current_match_score']} ({score2['rating']}) [+{score2['current_match_score'] - score1['current_match_score']}]")

    # Step 3: Add projects
    cv["projects"] = [
        {"name": "Cloud Migration", "description": "Migrated infrastructure to AWS using Docker and Kubernetes"},
        {"name": "API Gateway", "description": "Built RESTful APIs with Python and PostgreSQL"},
        {"name": "React Dashboard", "description": "Real-time dashboard with React and GraphQL"}
    ]
    score3 = engine.calculate_match_score(cv, JOB_DESCRIPTION)
    print(f"Step 3 - +3 Projects: {score3['current_match_score']} ({score3['rating']}) [+{score3['current_match_score'] - score2['current_match_score']}]")

    # Step 4: Add more experience-related keywords in work desc
    cv["work_experience"][0]["description"].extend([
        "Led team of 5 developers using Agile/Scrum methodology",
        "Implemented CI/CD pipelines with Docker and Kubernetes",
        "Managed PostgreSQL and MongoDB databases"
    ])
    score4 = engine.calculate_match_score(cv, JOB_DESCRIPTION)
    print(f"Step 4 - Enhanced Desc: {score4['current_match_score']} ({score4['rating']}) [+{score4['current_match_score'] - score3['current_match_score']}]")

    total_improvement = score4['current_match_score'] - score1['current_match_score']
    print(f"\n📈 Total improvement: {score1['current_match_score']} → {score4['current_match_score']} (+{total_improvement} points)")


def test_score_details():
    """Show detailed score breakdown."""
    print("\n" + "="*60)
    print("TEST 7: DETAILED BREAKDOWN")
    print("="*60)

    score = engine.calculate_match_score(BASE_CV, JOB_DESCRIPTION)
    print(f"Score: {score['current_match_score']}")
    print(f"Rating: {score['rating']}")
    print(f"\nBreakdown:")
    for k, v in score['breakdown'].items():
        print(f"  {k}: {v}")
    print(f"\nDetails:")
    for k, v in score['details'].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    print("\n" + "#"*60)
    print("# CV SCORING CONSISTENCY TESTS")
    print("#"*60)

    test_consistency()
    test_adding_skills()
    test_adding_projects()
    test_experience_years()
    test_education()
    test_full_improvement_cycle()
    test_score_details()

    print("\n" + "#"*60)
    print("# TESTS COMPLETE")
    print("#"*60 + "\n")
