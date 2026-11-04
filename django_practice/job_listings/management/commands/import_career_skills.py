import sys
from pathlib import Path
from django.core.management.base import BaseCommand
from job_listings.models import Career, Skill
project_root= Path(__file__).resolve().parents[4]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from backend.career_skills import career_requirements
class Command(BaseCommand):
    help = 'Import careers and their associated skills'
    def handle(self, *args, **options):
        for career_title, skill_names in career_requirements.items():
            career, created= Career.objects.get_or_create(
                title= career_title
            )
            for skill_name in skill_names:
                clean_name= skill_name.strip()
                skill = Skill.objects.filter(name__iexact=clean_name).first()
                if skill is None:
                    skill = Skill.objects.create(name=clean_name)
                career.skills.add(skill)