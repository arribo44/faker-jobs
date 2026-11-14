"""
CV generation for job candidates (`JobsProvider.job_cv()`).

Generates realistic resumes/CVs for job seekers, including:
- Professional experience with dates, companies, job titles
- Education history with diplomas, institutions, years
- Technical and soft skills
- Projects and achievements
- Language proficiency
- Contact information

Formats supported:
- JSON (structured data)
- Markdown (readable format)
- Dictionary (for further processing)
"""
from __future__ import annotations

import datetime as _datetime
from typing import TYPE_CHECKING, Any, Literal, TypedDict

if TYPE_CHECKING:
    from faker_jobs import JobsProvider, CandidateRecord, OccupationRecord


# Format options for CV output
CVFormat = Literal["dict", "json", "markdown"]

# Language proficiency levels (CEFR)
LANGUAGE_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2", "Native"]

# Experience duration options
EXPERIENCE_DURATIONS = ["current", "1 month", "3 months", "6 months", "1 year", "2 years", 
                       "3 years", "4 years", "5 years", "6 years", "7 years", "8 years",
                       "9 years", "10+ years"]


class CVExperience(TypedDict):
    """A single work experience entry in a CV."""
    company: str
    job_title: str
    occupation_code: str | None
    sector: str | None
    start_date: str  # ISO format YYYY-MM
    end_date: str | None  # None if current
    duration: str
    description: list[str]
    location: str
    achievements: list[str]


class CVEducation(TypedDict):
    """A single education entry in a CV."""
    institution: str
    diploma: str
    field_of_study: str | None
    start_year: int
    end_year: int | None  # None if ongoing
    gpa: float | None
    honors: str | None


class CVSkill(TypedDict):
    """A skill entry in a CV."""
    name: str
    category: str  # "Technical", "Soft", "Language", "Tool"
    level: str  # For languages: A1-C2, for others: "Beginner", "Intermediate", "Advanced", "Expert"


class CVProject(TypedDict):
    """A project entry in a CV."""
    name: str
    description: str
    role: str
    technologies: list[str]
    start_date: str  # ISO format YYYY-MM
    end_date: str | None
    url: str | None


class CVRecord(TypedDict):
    """A complete CV/Resume record.
    
    Contains all professional information about a candidate in a structured format.
    """
    # Personal information
    name: str
    email: str
    phone: str
    address: str | None
    city: str
    country: str
    linkedin: str | None
    github: str | None
    portfolio: str | None
    
    # Professional summary
    summary: str | None
    title: str  # Current/professional title
    
    # Core sections
    experience: list[CVExperience]
    education: list[CVEducation]
    skills: list[CVSkill]
    projects: list[CVProject]
    
    # Additional sections
    languages: list[CVSkill]  # Language skills with proficiency levels
    certifications: list[str]
    interests: list[str]
    
    # Metadata
    occupation_code: str
    occupation: str
    isco_code: str | None
    isco_group: str
    sector: str
    experience_years: int
    
    # Formatting
    locale: str
    generated_date: str  # ISO format YYYY-MM-DD


class CVText(TypedDict):
    """Text representation of a CV in markdown format."""
    markdown: str
    locale: str


# Default sections to include in CV
DEFAULT_SECTIONS = ["summary", "experience", "education", "skills", "projects", "languages", "certifications"]

# Month names for date formatting
MONTH_NAMES = {
    "en": ["January", "February", "March", "April", "May", "June", 
           "July", "August", "September", "October", "November", "December"],
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin",
           "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    "de": ["Januar", "Februar", "März", "April", "Mai", "Juni",
           "Juli", "August", "September", "Oktober", "November", "Dezember"],
    "es": ["enero", "febrero", "marzo", "abril", "mayo", "junio",
           "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"],
    "it": ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
           "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"],
    "pt": ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
           "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"],
    "nl": ["januari", "februari", "maart", "april", "mei", "juni",
           "juli", "augustus", "september", "oktober", "november", "december"],
    "pl": ["styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
           "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień"],
    "sv": ["januari", "februari", "mars", "april", "maj", "juni",
           "juli", "augusti", "september", "oktober", "november", "december"],
    "cs": ["leden", "únor", "březen", "duben", "květen", "červen",
           "červenec", "srpen", "září", "říjen", "listopad", "prosinec"],
    "ro": ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
           "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"],
    "el": ["Ιανουάριος", "Φεβρουάριος", "Μάρτιος", "Απρίλιος", "Μάιος", "Ιούνιος",
           "Ιούλιος", "Αύγουστος", "Σεπτέμβριος", "Οκτώβριος", "Νοέμβριος", "Δεκέμβριος"],
    "ar": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو",
           "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
}


def _get_month_names(locale: str) -> list[str]:
    """Get month names for a given locale."""
    lang = locale.split("_")[0].lower()
    return MONTH_NAMES.get(lang, MONTH_NAMES["en"])


def _format_date(start: tuple[int, int], end: tuple[int, int] | None, locale: str) -> str:
    """Format a date range for CV."""
    months = _get_month_names(locale)
    start_year, start_month = start
    
    if end is None:
        # Current position
        end_month_name = months[start_month - 1] if start_month else ""
        end_year_str = "Present" if locale.startswith("en") else \
                      "Présent" if locale.startswith("fr") else \
                      "Aktuell" if locale.startswith("de") else \
                      "Actual" if locale.startswith("es") or locale.startswith("pt") else \
                      "Attuale" if locale.startswith("it") else \
                      "Huidig" if locale.startswith("nl") else \
                      "Obecnie" if locale.startswith("pl") else \
                      "Nu" if locale.startswith("sv") else \
                      "Nyní" if locale.startswith("cs") else \
                      "Acum" if locale.startswith("ro") else \
                      "Τρέχων" if locale.startswith("el") else \
                      "الحالي" if locale.startswith("ar") else \
                      "Present"
        return f"{months[start_month - 1]} {start_year} – {end_year_str}"
    
    end_year, end_month = end
    start_str = f"{months[start_month - 1]} {start_year}"
    end_str = f"{months[end_month - 1]} {end_year}"
    return f"{start_str} – {end_str}"


def _generate_experience(
    jobs: JobsProvider,
    occupation_code: str,
    experience_years: int,
    current_age: int,
    locale: str,
    count: int = 3
) -> list[CVExperience]:
    """Generate work experience entries."""
    experiences = []
    current_year = _datetime.date.today().year
    
    # Get occupation info
    try:
        occupation = jobs.job_occupation_record(code=occupation_code)
    except Exception:
        occupation = jobs.job_occupation_record()
    
    sector = occupation.get("sector", "")
    
    # Distribute experience years across jobs
    # Last job gets most recent years
    years_remaining = experience_years
    
    for i in range(count):
        if years_remaining <= 0 and i > 0:
            break
        
        # Determine duration for this job
        if i == 0:
            # Current/most recent job
            duration_years = min(max(1, years_remaining - (count - 1)), years_remaining)
            start_year = current_year - duration_years
            start_month = jobs.generator.random.randint(1, 12)
            end_date = None  # Current
        else:
            # Previous jobs
            duration_years = jobs.generator.random.randint(1, max(1, years_remaining))
            start_year = current_year - years_remaining
            end_year = start_year + duration_years
            start_month = jobs.generator.random.randint(1, 12)
            end_month = jobs.generator.random.randint(start_month, 12) if duration_years == 0 else jobs.generator.random.randint(1, 12)
            end_date = (end_year, end_month)
        
        # Generate company
        company_profile = jobs.job_company_profile(sector=sector)
        company = company_profile["company"]
        city = company_profile.get("city", jobs.job_location()["city"])
        
        # Generate job title (could be same occupation or related)
        if i == 0:
            job_title = occupation.get("title", occupation.get("job_title", ""))
        else:
            # Previous jobs could be in same sector
            job_title = jobs.job_occupation_title(sector=sector)
        
        # Generate description
        description = jobs.job_responsibilities().split("; ") if "; " in jobs.job_responsibilities() else [jobs.job_responsibilities()]
        
        # Generate achievements
        achievements = []
        for _ in range(jobs.generator.random.randint(2, 4)):
            skill = jobs.generator.random.choice(occupation.get("skills", ["Teamwork", "Problem solving"]))
            achievements.append(f"{jobs.generator.random.choice(['Improved', 'Developed', 'Optimized', 'Implemented', 'Led'])} {skill}")
        
        experiences.append({
            "company": company,
            "job_title": job_title,
            "occupation_code": occupation_code if i == 0 else None,
            "sector": sector,
            "start_date": f"{start_year}-{start_month:02d}",
            "end_date": f"{end_date[0]}-{end_date[1]:02d}" if end_date else None,
            "duration": _format_date((start_year, start_month), end_date, locale),
            "description": description[:3],  # Limit to 3 bullet points
            "location": city,
            "achievements": achievements
        })
        
        years_remaining -= duration_years
    
    return experiences


def _generate_education(
    jobs: JobsProvider,
    qualification: str,
    sector: str,
    locale: str,
    count: int = 2
) -> list[CVEducation]:
    """Generate education entries."""
    educations = []
    current_year = _datetime.date.today().year
    
    # Common institutions by country
    institutions = {
        "fr": ["Université Paris 1 Panthéon-Sorbonne", "Université Sorbonne Nouvelle", 
               "École Polytechnique", "HEC Paris", "ESSEC", "EDHEC", "Sciences Po",
               "Université de Lyon", "Université de Bordeaux", "IAE Paris"],
        "en": ["Harvard University", "Massachusetts Institute of Technology", 
               "Stanford University", "University of California, Berkeley",
               "Columbia University", "New York University", "University of Oxford",
               "University of Cambridge", "London School of Economics"],
        "de": ["Technische Universität München", "Ludwig-Maximilians-Universität München",
               "Ruprecht-Karls-Universität Heidelberg", "Humboldt-Universität zu Berlin",
               "Freie Universität Berlin"],
        "es": ["Universidad Complutense de Madrid", "Universidad de Barcelona",
               "Universidad Autónoma de Madrid", "IE Business School"],
        "it": ["Università di Bologna", "Politecnico di Milano", 
               "Università degli Studi di Roma La Sapienza", "Università Bocconi"],
    }
    
    lang = locale.split("_")[0]
    base_institutions = institutions.get(lang, ["University", "College", "Institute"])
    
    for i in range(count):
        institution = jobs.generator.random.choice(base_institutions)
        
        # Determine diploma level based on qualification
        if i == 0:
            # Highest degree
            diploma = qualification
            end_year = current_year - jobs.generator.random.randint(0, 5)
        else:
            # Previous degrees
            diploma = jobs.job_qualification()
            end_year = current_year - jobs.generator.random.randint(5, 15)
        
        start_year = end_year - jobs.generator.random.randint(2, 5)
        
        # Field of study based on sector
        field = sector if jobs.generator.random.random() < 0.7 else jobs.generator.random.choice([
            "Computer Science", "Business Administration", "Engineering",
            "Economics", "Finance", "Marketing", "Management"
        ])
        
        educations.append({
            "institution": institution,
            "diploma": diploma,
            "field_of_study": field,
            "start_year": start_year,
            "end_year": end_year,
            "gpa": round(jobs.generator.random.uniform(3.0, 4.0), 2) if jobs.generator.random.random() < 0.6 else None,
            "honors": "Summa Cum Laude" if jobs.generator.random.random() < 0.1 else None
        })
    
    return educations


def _generate_skills(
    jobs: JobsProvider,
    occupation: OccupationRecord,
    locale: str
) -> list[CVSkill]:
    """Generate skills list for CV."""
    skills = []
    
    # Technical skills from occupation
    for skill in occupation.get("skills", [])[:8]:
        skills.append({
            "name": skill,
            "category": "Technical",
            "level": jobs.generator.random.choice(["Intermediate", "Advanced", "Expert"])
        })
    
    # Soft skills from occupation
    for skill in occupation.get("soft_skills", [])[:5]:
        skills.append({
            "name": skill,
            "category": "Soft",
            "level": jobs.generator.random.choice(["Intermediate", "Advanced"])
        })
    
    # Knowledge as technical skills
    for knowledge in occupation.get("knowledge", [])[:5]:
        skills.append({
            "name": knowledge,
            "category": "Technical",
            "level": jobs.generator.random.choice(["Intermediate", "Advanced"])
        })
    
    # Tools (generic)
    tools = ["Microsoft Office", "Git", "Docker", "JIRA", "Slack", "Trello"]
    for tool in jobs.generator.random.sample(tools, min(3, len(tools))):
        skills.append({
            "name": tool,
            "category": "Tool",
            "level": jobs.generator.random.choice(["Intermediate", "Advanced"])
        })
    
    return skills


def _generate_languages(jobs: JobsProvider, locale: str) -> list[CVSkill]:
    """Generate language skills."""
    languages = []
    lang = locale.split("_")[0]
    
    # Native language
    native_name = {
        "fr": "French", "en": "English", "de": "German", "es": "Spanish",
        "it": "Italian", "pt": "Portuguese", "nl": "Dutch", "pl": "Polish",
        "sv": "Swedish", "cs": "Czech", "ro": "Romanian", "el": "Greek", "ar": "Arabic"
    }.get(lang, "Native Language")
    
    languages.append({
        "name": native_name,
        "category": "Language",
        "level": "Native"
    })
    
    # Additional languages
    additional_languages = ["English", "French", "Spanish", "German", "Italian", 
                            "Portuguese", "Dutch", "Russian", "Chinese", "Arabic", "Japanese"]
    additional_languages = [l for l in additional_languages if l != native_name]
    
    for lang_name in jobs.generator.random.sample(additional_languages, jobs.generator.random.randint(1, 3)):
        languages.append({
            "name": lang_name,
            "category": "Language",
            "level": jobs.generator.random.choice(LANGUAGE_LEVELS)
        })
    
    return languages


def _generate_projects(
    jobs: JobsProvider,
    experience: list[CVExperience],
    locale: str,
    count: int = 2
) -> list[CVProject]:
    """Generate project entries."""
    projects = []
    current_year = _datetime.date.today().year
    
    project_names = [
        "Customer Portal Redesign", "Mobile App Development", "Data Migration",
        "API Integration", "Performance Optimization", "Security Audit",
        "Marketing Campaign", "Product Launch", "Process Automation",
        "Website Redesign", "Cloud Migration", "Machine Learning Model"
    ]
    
    for _ in range(min(count, len(experience))):
        exp = experience[_]
        
        start_year = int(exp["start_date"].split("-")[0])
        end_year = int(exp["end_date"].split("-")[0]) if exp["end_date"] else current_year
        
        start_month = int(exp["start_date"].split("-")[1])
        end_month = int(exp["end_date"].split("-")[1]) if exp["end_date"] else jobs.generator.random.randint(1, 12)
        
        project = jobs.generator.random.choice(project_names)
        
        # Generate technologies based on experience
        technologies = []
        if "Software" in exp.get("sector", ""):
            technologies = jobs.generator.random.sample([
                "Python", "JavaScript", "React", "Django", "Flask", "PostgreSQL",
                "Docker", "Kubernetes", "AWS", "Git"
            ], jobs.generator.random.randint(2, 4))
        elif "Data" in exp.get("sector", ""):
            technologies = jobs.generator.random.sample([
                "Python", "SQL", "Pandas", "NumPy", "TensorFlow", "Tableau"
            ], jobs.generator.random.randint(2, 4))
        else:
            technologies = jobs.generator.random.sample([
                "Microsoft Office", "Salesforce", "SAP", "Excel"
            ], jobs.generator.random.randint(1, 3))
        
        projects.append({
            "name": project,
            "description": f"{exp['job_title']} project focused on {jobs.generator.random.choice(['innovation', 'efficiency', 'scalability', 'quality'])}",
            "role": exp["job_title"],
            "technologies": technologies,
            "start_date": f"{start_year}-{start_month:02d}",
            "end_date": f"{end_year}-{end_month:02d}" if end_year > start_year or end_month >= start_month else None,
            "url": f"https://example.com/projects/{project.lower().replace(' ', '-')}" if jobs.generator.random.random() < 0.3 else None
        })
    
    return projects


def _generate_certifications(jobs: JobsProvider, sector: str, count: int = 3) -> list[str]:
    """Generate certification list."""
    certifications = []
    
    sector_certs = {
        "IT": ["AWS Certified", "Google Cloud Professional", "Microsoft Certified: Azure",
               "CISSP", "PMP", "Scrum Master", "TOGAF Certified"],
        "Healthcare": ["BLS Certification", "ACLS Certification", "RN License", "CPR Certified"],
        "Finance": ["CFA", "CFP", "CPA", "FRM", "PRM"],
        "Education": ["Teaching Certification", "TEFL", "TESOL"],
        "Engineering": ["PE License", "FE Exam", "Six Sigma", "Lean Certification"],
    }
    
    sector_key = next((k for k in sector_certs if k in sector), "general")
    certs = sector_certs.get(sector_key, [
        "Project Management", "Leadership Training", "Safety Certification",
        "Quality Assurance", "Customer Service Excellence"
    ])
    
    for _ in range(jobs.generator.random.randint(1, count)):
        cert = jobs.generator.random.choice(certs)
        if cert not in certifications:
            certifications.append(cert)
    
    return certifications


def _generate_summary(jobs: JobsProvider, experience: list[CVExperience], occupation: OccupationRecord, locale: str) -> str:
    """Generate professional summary."""
    lang = locale.split("_")[0]
    
    # Summaries by language
    summaries = {
        "fr": [
            "Professionnel expérimenté avec {} ans d'expérience dans {}. Passionné par {}.",
            "{} avec une solide expérience en {}. Orienté résultats et travail d'équipe.",
            "Expert en {} avec plus de {} ans d'expérience. Capacité à gérer des projets complexes."
        ],
        "en": [
            "Experienced professional with {} years of experience in {}. Passionate about {}.",
            "{} with a strong background in {}. Results-oriented and team player.",
            "Expert in {} with over {} years of experience. Ability to manage complex projects."
        ],
        "de": [
            "Erfahrener Fachmann mit {} Jahren Erfahrung in {}. Leidenschaftlich für {}.",
            "{} mit fundierten Kenntnissen in {}. Ergebnisorientiert und teamfähig."
        ],
        "es": [
            "Profesional con {} años de experiencia en {}. Apasionado por {}.",
            "{} con una sólida experiencia en {}. Orientado a resultados y trabajo en equipo."
        ],
        "it": [
            "Professionista con {} anni di esperienza in {}. Appassionato di {}.",
            "{} con una solida esperienza in {}. Orientato ai risultati e al lavoro di squadra."
        ],
    }
    
    template = jobs.generator.random.choice(summaries.get(lang, summaries["en"]))
    
    # Get total experience
    total_exp = len(experience)
    years = sum(1 for exp in experience if exp["end_date"] is None) + jobs.generator.random.randint(0, 2)
    
    # Get sector
    sector = occupation.get("sector", "the field")
    title = occupation.get("title", "professional")
    
    # Get a skill
    skills = occupation.get("skills", ["innovation"])
    skill = jobs.generator.random.choice(skills) if skills else "the work"
    
    return template.format(years, sector, skill, title, years)


def _generate_contact_info(jobs: JobsProvider, candidate: CandidateRecord | None, locale: str) -> dict[str, Any]:
    """Generate contact information."""
    if candidate:
        return {
            "name": candidate["name"],
            "email": candidate["email"],
            "phone": candidate["phone"],
            "city": candidate["city"],
            "country": candidate["country"],
        }
    else:
        location = jobs.job_location()
        return {
            "name": jobs.generator.name(),
            "email": jobs.generator.email(),
            "phone": jobs.generator.phone_number(),
            "city": location["city"],
            "country": location["country"],
        }


def generate_cv(
    jobs: JobsProvider,
    candidate: CandidateRecord | None = None,
    sections: list[str] | None = None,
    experience_count: int = 3,
    education_count: int = 2,
    project_count: int = 2,
    output_format: CVFormat = "dict",
) -> CVRecord | CVText | dict[str, Any]:
    """
    Generate a complete CV/resume for a job candidate.
    
    Args:
        jobs: The JobsProvider instance
        candidate: Optional candidate record to base the CV on
        sections: List of sections to include (default: all)
        experience_count: Number of experience entries
        education_count: Number of education entries
        project_count: Number of project entries
        output_format: Output format - "dict" (CVRecord), "json", or "markdown"
    
    Returns:
        CVRecord, CVText, or dict depending on output_format
    """
    from faker_jobs import _generator_locale
    locale = _generator_locale(jobs.generator) or "en_US"
    
    # Get or generate candidate info
    if candidate:
        occupation_code = candidate["occupation_code"]
        occupation_title = candidate["occupation"]
        sector = candidate.get("sector", "")
        experience_years = candidate["experience_years"]
        qualification = candidate["qualification"]
        
        # Get full occupation record
        try:
            occupation = jobs.job_occupation_record(code=occupation_code)
        except Exception:
            occupation = jobs.job_occupation_record(sector=sector) if sector else jobs.job_occupation_record()
    else:
        # Generate from scratch
        occupation = jobs.job_occupation_record()
        occupation_code = occupation["code"]
        occupation_title = occupation["title"]
        sector = occupation.get("sector", "")
        experience_years = jobs.generator.random.randint(3, 15)
        qualification = jobs.job_qualification()
        
        candidate = {
            "name": "",
            "email": "",
            "phone": "",
            "city": "",
            "country": "",
            "occupation_code": occupation_code,
            "occupation": occupation_title,
            "job_title": occupation.get("job_title", occupation_title),
            "isco_code": occupation.get("isco_code"),
            "isco_group": occupation.get("isco_group", "1"),
            "sector": sector,
            "experience_years": experience_years,
            "qualification": qualification,
            "skills": [],
            "desired_salary": 0,
            "salary_currency": "EUR",
            "availability": "immediate",
        }
    
    # Generate contact info
    contact = _generate_contact_info(jobs, candidate, locale)
    
    # Generate experience
    experience = _generate_experience(
        jobs, occupation_code, experience_years, 
        current_age=jobs.generator.random.randint(25, 60), locale=locale, count=experience_count
    )
    
    # Generate education
    education = _generate_education(
        jobs, qualification, sector, locale, count=education_count
    )
    
    # Generate skills
    skills = _generate_skills(jobs, occupation, locale)
    
    # Generate languages
    languages = _generate_languages(jobs, locale)
    
    # Generate projects
    projects = _generate_projects(jobs, experience, locale, count=project_count)
    
    # Generate certifications
    certifications = _generate_certifications(jobs, sector)
    
    # Generate summary
    summary = _generate_summary(jobs, experience, occupation, locale)
    
    # Build CV record
    cv_record: CVRecord = {
        # Personal info
        "name": contact["name"],
        "email": contact["email"],
        "phone": contact["phone"],
        "address": None,  # Can be added later
        "city": contact["city"],
        "country": contact["country"],
        "linkedin": f"https://linkedin.com/in/{contact['name'].lower().replace(' ', '-')}" if jobs.generator.random.random() < 0.7 else None,
        "github": f"https://github.com/{contact['name'].lower().replace(' ', '')}" if jobs.generator.random.random() < 0.4 else None,
        "portfolio": None,
        
        # Professional summary
        "summary": summary,
        "title": occupation.get("job_title", occupation.get("title", "Professional")),
        
        # Core sections
        "experience": experience,
        "education": education,
        "skills": skills,
        "projects": projects,
        
        # Additional sections
        "languages": languages,
        "certifications": certifications,
        "interests": jobs.generator.random.sample([
            "Reading", "Hiking", "Coding", "Music", "Sports", "Travel", 
            "Photography", "Cooking", "Gaming", "Volunteering"
        ], jobs.generator.random.randint(2, 4)),
        
        # Metadata
        "occupation_code": occupation_code,
        "occupation": occupation_title,
        "isco_code": occupation.get("isco_code"),
        "isco_group": occupation.get("isco_group", "1"),
        "sector": sector,
        "experience_years": experience_years,
        
        # Formatting
        "locale": locale,
        "generated_date": _datetime.date.today().isoformat(),
    }
    
    # Handle sections filter
    if sections:
        # For now, just filter what we return (simplified)
        pass
    
    # Return based on format
    if output_format == "json":
        import json
        return json.loads(json.dumps(cv_record, ensure_ascii=False, indent=2))
    elif output_format == "markdown":
        return _cv_to_markdown(cv_record)
    else:
        return cv_record


def _cv_to_markdown(cv: CVRecord) -> CVText:
    """Convert CV record to markdown format."""
    locale = cv["locale"]
    lang = locale.split("_")[0]
    
    # Translation keys
    translations = {
        "en": {
            "name": "Name",
            "email": "Email",
            "phone": "Phone",
            "address": "Address",
            "linkedin": "LinkedIn",
            "github": "GitHub",
            "portfolio": "Portfolio",
            "title": "Title",
            "summary": "Professional Summary",
            "experience": "Work Experience",
            "education": "Education",
            "skills": "Skills",
            "projects": "Projects",
            "languages": "Languages",
            "certifications": "Certifications",
            "interests": "Interests",
            "present": "Present",
            "to": "to",
        },
        "fr": {
            "name": "Nom",
            "email": "Email",
            "phone": "Téléphone",
            "address": "Adresse",
            "linkedin": "LinkedIn",
            "github": "GitHub",
            "portfolio": "Portfolio",
            "title": "Poste",
            "summary": "Résumé Professionnel",
            "experience": "Expérience Professionnelle",
            "education": "Formation",
            "skills": "Compétences",
            "projects": "Projets",
            "languages": "Langues",
            "certifications": "Certifications",
            "interests": "Centres d'intérêt",
            "present": "Présent",
            "to": "à",
        },
        "de": {
            "name": "Name",
            "email": "E-Mail",
            "phone": "Telefon",
            "address": "Adresse",
            "linkedin": "LinkedIn",
            "github": "GitHub",
            "portfolio": "Portfolio",
            "title": "Position",
            "summary": "Berufliche Zusammenfassung",
            "experience": "Berufserfahrung",
            "education": "Ausbildung",
            "skills": "Fähigkeiten",
            "projects": "Projekte",
            "languages": "Sprachen",
            "certifications": "Zertifizierungen",
            "interests": "Interessen",
            "present": "Aktuell",
            "to": "bis",
        },
        "es": {
            "name": "Nombre",
            "email": "Correo electrónico",
            "phone": "Teléfono",
            "address": "Dirección",
            "linkedin": "LinkedIn",
            "github": "GitHub",
            "portfolio": "Portafolio",
            "summary": "Resumen Profesional",
            "experience": "Experiencia Laboral",
            "education": "Educación",
            "skills": "Habilidades",
            "projects": "Proyectos",
            "languages": "Idiomas",
            "certifications": "Certificaciones",
            "interests": "Intereses",
            "present": "Actual",
            "to": "a",
        },
        "it": {
            "name": "Nome",
            "email": "Email",
            "phone": "Telefono",
            "address": "Indirizzo",
            "linkedin": "LinkedIn",
            "github": "GitHub",
            "portfolio": "Portfolio",
            "summary": "Sintesi Professionale",
            "experience": "Esperienza Lavorativa",
            "education": "Istruzione",
            "skills": "Competenze",
            "projects": "Progetti",
            "languages": "Lingue",
            "certifications": "Certificazioni",
            "interests": "Interessi",
            "present": "Attuale",
            "to": "a",
        },
    }
    
    t = translations.get(lang, translations["en"])
    
    # Build markdown
    md = []
    md.append(f"# {cv['name']}")
    md.append(f"**{t['title']}:** {cv['title']}")
    md.append(f"**{t['email']}:** {cv['email']} | **{t['phone']}:** {cv['phone']}")
    
    if cv.get("linkedin"):
        md.append(f"**{t['linkedin']}:** {cv['linkedin']}")
    if cv.get("github"):
        md.append(f"**{t['github']}:** {cv['github']}")
    if cv.get("portfolio"):
        md.append(f"**{t['portfolio']}:** {cv['portfolio']}")
    
    md.append("")
    
    # Summary
    if cv.get("summary"):
        md.append(f"## {t['summary']}")
        md.append(cv["summary"])
        md.append("")
    
    # Experience
    if cv.get("experience"):
        md.append(f"## {t['experience']}")
        for exp in cv["experience"]:
            md.append(f"### {exp['job_title']}")
            md.append(f"**{exp['company']}** | {exp['duration']}")
            md.append(f"📍 {exp['location']}")
            
            if exp.get("description"):
                for desc in exp["description"]:
                    md.append(f"- {desc}")
            
            if exp.get("achievements"):
                md.append("**Achievements:**")
                for ach in exp["achievements"]:
                    md.append(f"- {ach}")
            
            md.append("")
        md.append("")
    
    # Education
    if cv.get("education"):
        md.append(f"## {t['education']}")
        for edu in cv["education"]:
            end_year = edu["end_year"] if edu["end_year"] else t["present"]
            md.append(f"**{edu['diploma']}** in {edu.get('field_of_study', '')}")
            md.append(f"{edu['institution']} | {edu['start_year']} – {end_year}")
            if edu.get("gpa"):
                md.append(f"GPA: {edu['gpa']}")
            if edu.get("honors"):
                md.append(f"Honors: {edu['honors']}")
            md.append("")
        md.append("")
    
    # Skills
    if cv.get("skills"):
        md.append(f"## {t['skills']}")
        
        # Group by category
        categories = {}
        for skill in cv["skills"]:
            cat = skill.get("category", "Other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(skill["name"])
        
        for cat, cat_skills in categories.items():
            md.append(f"**{cat}:** {', '.join(cat_skills)}")
        
        md.append("")
    
    # Languages
    if cv.get("languages"):
        md.append(f"## {t['languages']}")
        for lang in cv["languages"]:
            md.append(f"- **{lang['name']}:** {lang['level']}")
        md.append("")
    
    # Projects
    if cv.get("projects"):
        md.append(f"## {t['projects']}")
        for proj in cv["projects"]:
            md.append(f"### {proj['name']}")
            md.append(f"{proj['description']}")
            md.append(f"**Technologies:** {', '.join(proj['technologies'])}")
            if proj.get("start_date"):
                start = proj["start_date"]
                end = proj.get("end_date", "Present")
                md.append(f"**Duration:** {start} {t['to']} {end}")
            if proj.get("url"):
                md.append(f"**URL:** {proj['url']}")
            md.append("")
        md.append("")
    
    # Certifications
    if cv.get("certifications"):
        md.append(f"## {t['certifications']}")
        for cert in cv["certifications"]:
            md.append(f"- {cert}")
        md.append("")
    
    # Interests
    if cv.get("interests"):
        md.append(f"## {t['interests']}")
        md.append(f"{', '.join(cv['interests'])}")
        md.append("")
    
    return {
        "markdown": "\n".join(md),
        "locale": locale,
    }


def cv_to_dict(cv: CVRecord | CVText) -> dict[str, Any]:
    """Ensure CV is in dict format."""
    if isinstance(cv, dict) and "markdown" in cv:
        return cv
    return dict(cv)
