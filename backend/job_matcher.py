"""Job matching utilities for the JobPylot backend."""

import re


def match_skills(user_skills, required_skills):
    user_skills = list(dict.fromkeys(skill.strip().casefold() for skill in user_skills))
    required_skills = list(
        dict.fromkeys(skill.strip().casefold() for skill in required_skills)
    )
    matching_skills = [
        skill for skill in user_skills if skill in required_skills
    ]
    missing_skills = [
        skill for skill in required_skills if skill not in user_skills
    ]

    if required_skills:
        match_score = len(matching_skills) / len(required_skills) * 100
    else:
        match_score = 0
    return matching_skills, missing_skills, match_score


def match_job(job_title, user_skills, required_skills):
    matching_skills, missing_skills, match_score = match_skills(
        user_skills,
        required_skills,
    )
    return {
        "matched_skills": matching_skills,
        "missing_skills": missing_skills,
        "match_score": match_score,
        "potentially_entry_level": entry_level(job_title),
    }


def meets_experience_requirement(user_experience, required_experience):
    return user_experience >= required_experience


def entry_level(job_title):
    normalized_title = job_title.strip().casefold()
    return bool(
        re.search(
            r"\b(?:intern(?:ship)?|junior|trainee|graduate\s+trainee)\b",
            normalized_title,
        )
    )


if __name__ == "__main__":
    result = match_skills(
        ["Python", "SQL", "Excel"],
        ["Python", "SQL", "Power BI"],
    )
    print(result)
