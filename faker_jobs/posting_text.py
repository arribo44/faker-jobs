"""
The full text of a job posting (`JobsProvider.job_posting_text()`), in
French, English, German, Spanish, Italian, Portuguese, Dutch, Polish,
Swedish, Czech, Romanian, Greek or Arabic: a headline, an introduction of the company, the job, the missions, the
profile asked, the conditions and how to apply.

The wording is hand-made; every fact comes from the posting (occupation,
company, conditions, contact). Each section has a few phrasings, picked with
the provider's random generator, so that seeded runs give the same text.
Sentences avoid gender agreements and articles in front of the company
name or the job title, which the data does not give.
"""
import datetime as _datetime
import random
import unicodedata
from collections.abc import Mapping
from typing import Any

# {language: texts}. Placeholders: {company}, {city}, {country}, {sector},
# {size} (employees, formatted), {industry}, {title} (occupation name),
# {code}, {domain}, {contact_person}, {contact}, {job_id}, {date}, {portal}.
# `remote`: the line of the hybrid and full remote postings (none on site).
TEXTS: dict[str, dict[str, Any]] = {
    "fr": {
        "intro": [
            "{company} recrute pour son site de {city}.",
            "Dans le cadre de son développement, {company} renforce ses équipes à {city}.",
            "Envie de rejoindre une équipe engagée ? {company} recrute à {city}.",
        ],
        "intro_sector": [
            "{company}, entreprise de {size} salariés du secteur {sector}, recrute pour son site de {city}.",
            "Acteur du secteur {sector}, {company} ({size} salariés) renforce ses équipes à {city}.",
            "Rejoignez {company}, {size} salariés, l'un des acteurs du secteur {sector}, à {city}.",
        ],
        "industry": "Activité : {industry}.",
        "job": ["Le poste", "Description du poste", "À propos du poste"],
        "no_description": [
            "Vous exercerez le métier de {title} (fiche ROME {code}, domaine {domain}).",
            "Le poste relève du métier de {title} (fiche ROME {code}), dans le domaine {domain}.",
        ],
        "transitions": {
            "ecological": "Ce métier contribue à la transition écologique.",
            "digital": "Ce métier est au cœur de la transition numérique.",
            "demographic": "Ce métier répond aux besoins liés au vieillissement de la population.",
        },
        "missions": ["Vos missions", "Vos principales activités", "Au quotidien"],
        "missions_lead": ["Vous serez notamment chargé(e) de :", "Vos principales missions :", ""],
        "profile": ["Votre profil", "Profil recherché", "Ce que nous recherchons"],
        "qualification": "Formation : {value}",
        "experience": "Expérience : {value}",
        "knowledge": "Connaissances : {value}",
        "soft_skills": "Savoir-être : {value}",
        "regulated": "Profession réglementée : diplôme ou autorisation d'exercice obligatoire",
        "offer": ["Ce que nous offrons", "Notre offre", "Conditions du poste"],
        "contract": "Contrat : {value}",
        "salary": "Rémunération : {value}",
        "location": "Lieu de travail : {city}, {country}",
        "remote": {"hybrid": "Télétravail partiel possible (hybride)", "remote": "Poste en télétravail complet"},
        "benefits": "Avantages : {value}",
        "apply": ["Pour postuler", "Candidature", "Comment postuler ?"],
        "apply_text": [
            "Envoyez votre candidature à {contact_person}, tél. {contact}, en rappelant la référence {job_id}.",
            "Intéressé(e) ? Contactez {contact_person} au {contact}, référence de l'offre : {job_id}.",
        ],
        "posted": "Offre publiée le {date} sur {portal}.",
        "date": "{day} {month} {year}",
        "months": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
                   "septembre", "octobre", "novembre", "décembre"],
        "thousands": "\u202f",   # narrow no-break space
        "and": " et ",
        "list_separator": " ; ",
    },
    "en": {
        "intro": [
            "{company} is hiring in {city}.",
            "{company} is growing its team in {city}.",
            "Looking for your next challenge? {company} is hiring in {city}.",
        ],
        "intro_sector": [
            "{company} ({sector}, {size} employees) is hiring in {city}.",
            "With {size} employees in {sector}, {company} is growing its team in {city}.",
            "Join {company} ({sector}, {size} employees) in {city}.",
        ],
        "industry": "Industry: {industry}.",
        "job": ["About the job", "The role", "Job description"],
        "no_description": ["You will work as {title}, in the {domain} field."],
        "transitions": {
            "ecological": "This job is part of the green transition.",
            "digital": "This job is at the heart of the digital transition.",
            "demographic": "This job meets the needs of an ageing population.",
        },
        "missions": ["What you will do", "Responsibilities", "Your day-to-day"],
        "missions_lead": ["Your main responsibilities:", "You will:", ""],
        "profile": ["What we are looking for", "Requirements", "About you"],
        "qualification": "Education: {value}",
        "experience": "Experience: {value}",
        "knowledge": "Knowledge of: {value}",
        "soft_skills": "Soft skills: {value}",
        "regulated": "Regulated profession: a licence or recognised qualification is required",
        "offer": ["What we offer", "Our offer", "Terms of employment"],
        "contract": "Employment type: {value}",
        "salary": "Salary: {value}",
        "location": "Location: {city}, {country}",
        "remote": {"hybrid": "Hybrid work: part of the week from home", "remote": "Fully remote position"},
        "benefits": "Benefits: {value}",
        "apply": ["How to apply", "Apply", "Interested?"],
        "apply_text": [
            "Send your application to {contact_person}, phone {contact}, quoting reference {job_id}.",
            "Contact {contact_person} at {contact}, job reference {job_id}.",
        ],
        "posted": "Posted on {date} on {portal}.",
        "date": "{month} {day}, {year}",
        "months": ["January", "February", "March", "April", "May", "June", "July", "August",
                   "September", "October", "November", "December"],
        "thousands": ",",
        "and": " and ",
    },
    "de": {
        "intro": [
            "{company} sucht Verstärkung am Standort {city}.",
            "{company} sucht ab sofort Verstärkung für das Team in {city}.",
            "Du suchst eine neue Herausforderung? {company} stellt in {city} ein.",
        ],
        "intro_sector": [
            "{company} ({sector}, {size} Beschäftigte) sucht Verstärkung am Standort {city}.",
            "Als Unternehmen der Branche {sector} mit {size} Beschäftigten sucht {company} Verstärkung in {city}.",
            "Werde Teil von {company} ({size} Beschäftigte, Branche {sector}) in {city}.",
        ],
        "industry": "Tätigkeitsfeld: {industry}.",
        "job": ["Die Stelle", "Stellenbeschreibung", "Über die Stelle"],
        "no_description": ["Beruf: {title}, Bereich {domain}."],
        "transitions": {
            "ecological": "Dieser Beruf trägt zum ökologischen Wandel bei.",
            "digital": "Dieser Beruf steht im Mittelpunkt der digitalen Transformation.",
            "demographic": "Dieser Beruf hilft, den Herausforderungen einer alternden Gesellschaft zu begegnen.",
        },
        "missions": ["Deine Aufgaben", "Aufgaben", "Das erwartet dich"],
        "missions_lead": ["Zu deinen Aufgaben gehört:", "Du wirst:", ""],
        "profile": ["Dein Profil", "Das bringst du mit", "Anforderungen"],
        "qualification": "Ausbildung: {value}",
        "experience": "Erfahrung: {value}",
        "knowledge": "Kenntnisse: {value}",
        "soft_skills": "Persönliche Stärken: {value}",
        "regulated": "Reglementierter Beruf: Abschluss oder Berufszulassung erforderlich",
        "offer": ["Wir bieten", "Unser Angebot", "Rahmenbedingungen"],
        "contract": "Vertragsart: {value}",
        "salary": "Vergütung: {value}",
        "location": "Arbeitsort: {city}, {country}",
        "remote": {
            "hybrid": "Hybrides Arbeiten: teilweise Homeoffice möglich",
            "remote": "Vollständig remote (100 % Homeoffice)",
        },
        "benefits": "Vorteile: {value}",
        "apply": ["Bewerbung", "So bewirbst du dich", "Interesse?"],
        "apply_text": [
            "Sende deine Bewerbung unter Angabe der Referenz {job_id} an {contact_person}, Telefon {contact}.",
            "Kontakt: {contact_person}, Telefon {contact}, Referenz {job_id}.",
        ],
        "posted": "Veröffentlicht am {date} auf {portal}.",
        "date": "{day}. {month} {year}",
        "months": ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
                   "September", "Oktober", "November", "Dezember"],
        "thousands": ".",
        "and": " und ",
        "lower_soft_skills": False,   # German nouns keep their capital
    },
    "es": {
        "intro": [
            "{company} busca incorporar talento en {city}.",
            "{company} amplía su equipo en {city}.",
            "¿Buscas un nuevo reto profesional? {company} selecciona personal en {city}.",
        ],
        "intro_sector": [
            "{company}, empresa del sector {sector} con {size} empleados, busca incorporar talento en {city}.",
            "{company} ({size} empleados, sector {sector}) amplía su equipo en {city}.",
            "Únete a {company}, referente del sector {sector} con {size} empleados, en {city}.",
        ],
        "industry": "Actividad: {industry}.",
        "job": ["El puesto", "Descripción del puesto", "Sobre el puesto"],
        "no_description": ["Ocupación: {title}, en el ámbito {domain}."],
        "transitions": {
            "ecological": "Esta ocupación contribuye a la transición ecológica.",
            "digital": "Esta ocupación está en el centro de la transición digital.",
            "demographic": "Esta ocupación responde a las necesidades de una población que envejece.",
        },
        "missions": ["Funciones", "Tus responsabilidades", "Tu día a día"],
        "missions_lead": ["Entre tus funciones:", "Te encargarás de:", ""],
        "profile": ["Requisitos", "Perfil buscado", "Qué buscamos"],
        "qualification": "Formación: {value}",
        "experience": "Experiencia: {value}",
        "knowledge": "Conocimientos: {value}",
        "soft_skills": "Competencias personales: {value}",
        "regulated": "Profesión regulada: se requiere título o habilitación profesional",
        "offer": ["Qué ofrecemos", "Nuestra oferta", "Condiciones"],
        "contract": "Tipo de contrato: {value}",
        "salary": "Salario: {value}",
        "location": "Lugar de trabajo: {city}, {country}",
        "remote": {"hybrid": "Modalidad híbrida: teletrabajo parcial", "remote": "Teletrabajo 100 % (en remoto)"},
        "benefits": "Beneficios: {value}",
        "apply": ["Cómo inscribirse", "Candidaturas", "¿Te interesa?"],
        "apply_text": [
            "Envía tu candidatura a {contact_person}, tel. {contact}, indicando la referencia {job_id}.",
            "Contacta con {contact_person} en el {contact}, referencia de la oferta: {job_id}.",
        ],
        "posted": "Oferta publicada el {date} en {portal}.",
        "date": "{day} de {month} de {year}",
        "months": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                   "septiembre", "octubre", "noviembre", "diciembre"],
        "thousands": ".",
        "and": " y ",
    },
    "it": {
        "intro": [
            "{company} ricerca personale per la sede di {city}.",
            "{company} amplia il proprio team a {city}.",
            "Cerchi una nuova sfida professionale? {company} assume a {city}.",
        ],
        "intro_sector": [
            "{company}, azienda del settore {sector} con {size} dipendenti, ricerca personale per la sede di {city}.",
            "{company} ({size} dipendenti, settore {sector}) amplia il proprio team a {city}.",
            "Entra in {company}, realtà del settore {sector} con {size} dipendenti, a {city}.",
        ],
        "industry": "Attività: {industry}.",
        "job": ["La posizione", "Il ruolo", "Descrizione della posizione"],
        "no_description": ["Professione: {title}, ambito {domain}."],
        "transitions": {
            "ecological": "Questa professione contribuisce alla transizione ecologica.",
            "digital": "Questa professione è al centro della transizione digitale.",
            "demographic": "Questa professione risponde ai bisogni di una popolazione che invecchia.",
        },
        "missions": ["Mansioni", "Responsabilità", "Di cosa ti occuperai"],
        "missions_lead": ["Tra le principali attività:", "Ti occuperai di:", ""],
        "profile": ["Requisiti", "Profilo ricercato", "Cosa cerchiamo"],
        "qualification": "Titolo di studio: {value}",
        "experience": "Esperienza: {value}",
        "knowledge": "Conoscenze: {value}",
        "soft_skills": "Competenze trasversali: {value}",
        "regulated": "Professione regolamentata: titolo o abilitazione obbligatori",
        "offer": ["Cosa offriamo", "La nostra offerta", "Condizioni"],
        "contract": "Contratto: {value}",
        "salary": "Retribuzione: {value}",
        "location": "Sede di lavoro: {city}, {country}",
        "remote": {"hybrid": "Lavoro ibrido: smart working parziale", "remote": "Lavoro full remote"},
        "benefits": "Benefit: {value}",
        "apply": ["Come candidarsi", "Candidature", "Ti interessa?"],
        "apply_text": [
            "Invia la tua candidatura a {contact_person}, tel. {contact}, indicando il riferimento {job_id}.",
            "Contatta {contact_person} al numero {contact}, riferimento dell'offerta: {job_id}.",
        ],
        "posted": "Offerta pubblicata in data {date} su {portal}.",
        "date": "{day} {month} {year}",
        "months": ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
                   "settembre", "ottobre", "novembre", "dicembre"],
        "thousands": ".",
        "and": " e ",
    },
    "pt": {
        "intro": [
            "{company} está a recrutar em {city}.",
            "Para reforçar a sua equipa em {city}, {company} está a recrutar.",
            "Procura um novo desafio? {company} está a recrutar em {city}.",
        ],
        "intro_sector": [
            "{company} ({sector}, {size} colaboradores) está a recrutar em {city}.",
            "Com {size} colaboradores no setor {sector}, {company} reforça a sua equipa em {city}.",
            "Junte-se a {company} ({sector}, {size} colaboradores) em {city}.",
        ],
        "industry": "Atividade: {industry}.",
        "job": ["A função", "Descrição da função", "Sobre a função"],
        "no_description": ["Irá exercer a profissão de {title}, na área {domain}."],
        "transitions": {
            "ecological": "Esta profissão contribui para a transição ecológica.",
            "digital": "Esta profissão está no centro da transição digital.",
            "demographic": "Esta profissão responde às necessidades do envelhecimento da população.",
        },
        "missions": ["Principais responsabilidades", "O que irá fazer", "No dia a dia"],
        "missions_lead": ["As suas principais tarefas:", "Irá:", ""],
        "profile": ["Perfil", "O que procuramos", "Requisitos"],
        "qualification": "Habilitações: {value}",
        "experience": "Experiência: {value}",
        "knowledge": "Conhecimentos: {value}",
        "soft_skills": "Competências pessoais: {value}",
        "regulated": "Profissão regulamentada: diploma ou cédula profissional obrigatórios",
        "offer": ["O que oferecemos", "A nossa oferta", "Condições"],
        "contract": "Contrato: {value}",
        "salary": "Remuneração: {value}",
        "location": "Local de trabalho: {city}, {country}",
        "remote": {
            "hybrid": "Regime híbrido: teletrabalho parcial",
            "remote": "Regime de teletrabalho a 100 % (remoto)",
        },
        "benefits": "Benefícios: {value}",
        "apply": ["Como candidatar-se", "Candidaturas", "Interessado/a?"],
        "apply_text": [
            "Envie a sua candidatura a {contact_person}, tel. {contact}, com a referência {job_id}.",
            "Contacte {contact_person} através do {contact}, referência da oferta: {job_id}.",
        ],
        "posted": "Oferta publicada a {date} em {portal}.",
        "date": "{day} de {month} de {year}",
        "months": ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
                   "setembro", "outubro", "novembro", "dezembro"],
        "thousands": ".",
        "and": " e ",
    },
    "nl": {
        "intro": [
            "{company} zoekt nieuwe collega's in {city}.",
            "{company} breidt het team in {city} uit.",
            "Op zoek naar een nieuwe uitdaging? {company} zoekt versterking in {city}.",
        ],
        "intro_sector": [
            "{company} ({sector}, {size} medewerkers) zoekt nieuwe collega's in {city}.",
            "Met {size} medewerkers in {sector} breidt {company} het team in {city} uit.",
            "Kom werken bij {company} ({sector}, {size} medewerkers) in {city}.",
        ],
        "industry": "Activiteit: {industry}.",
        "job": ["De functie", "Functieomschrijving", "Over de functie"],
        "no_description": ["Je werkt als {title}, in het domein {domain}."],
        "transitions": {
            "ecological": "Dit beroep draagt bij aan de ecologische transitie.",
            "digital": "Dit beroep staat centraal in de digitale transitie.",
            "demographic": "Dit beroep speelt in op de behoeften van een vergrijzende bevolking.",
        },
        "missions": ["Wat ga je doen?", "Taken en verantwoordelijkheden", "Je dagelijkse werk"],
        "missions_lead": ["Je belangrijkste taken:", "Je gaat:", ""],
        "profile": ["Wie zoeken wij?", "Functie-eisen", "Jouw profiel"],
        "qualification": "Opleiding: {value}",
        "experience": "Ervaring: {value}",
        "knowledge": "Kennis van: {value}",
        "soft_skills": "Competenties: {value}",
        "regulated": "Gereglementeerd beroep: diploma of erkenning verplicht",
        "offer": ["Wat bieden wij?", "Ons aanbod", "Arbeidsvoorwaarden"],
        "contract": "Dienstverband: {value}",
        "salary": "Salaris: {value}",
        "location": "Standplaats: {city}, {country}",
        "remote": {
            "hybrid": "Hybride werken: deels thuiswerken mogelijk",
            "remote": "Volledig op afstand (thuiswerken)",
        },
        "benefits": "Extra's: {value}",
        "apply": ["Solliciteren", "Interesse?", "Hoe solliciteren?"],
        "apply_text": [
            "Stuur je sollicitatie naar {contact_person}, tel. {contact}, onder vermelding van referentie {job_id}.",
            "Neem contact op met {contact_person} via {contact}, vacaturenummer {job_id}.",
        ],
        "posted": "Vacature geplaatst op {date} op {portal}.",
        "date": "{day} {month} {year}",
        "months": ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus",
                   "september", "oktober", "november", "december"],
        "thousands": ".",
        "and": " en ",
    },
    "pl": {
        "intro": [
            "{company} rekrutuje w miejscowości {city}.",
            "{company} poszerza zespół w miejscowości {city}.",
            "Szukasz nowego wyzwania? {company} rekrutuje w miejscowości {city}.",
        ],
        "intro_sector": [
            "{company} (branża: {sector}, {size} pracowników) rekrutuje w miejscowości {city}.",
            "Firma {company}, zatrudniająca {size} pracowników w branży {sector}, poszerza zespół "
            "w miejscowości {city}.",
            "Dołącz do {company} (branża: {sector}, {size} pracowników) w miejscowości {city}.",
        ],
        "industry": "Działalność: {industry}.",
        "job": ["Stanowisko", "Opis stanowiska", "O stanowisku"],
        "no_description": ["Będziesz pracować w zawodzie: {title}, w obszarze: {domain}."],
        "transitions": {
            "ecological": "Ten zawód wspiera transformację ekologiczną.",
            "digital": "Ten zawód jest w centrum transformacji cyfrowej.",
            "demographic": "Ten zawód odpowiada na potrzeby starzejącego się społeczeństwa.",
        },
        "missions": ["Zakres obowiązków", "Twoje zadania", "Na co dzień"],
        "missions_lead": ["Twoje główne zadania:", "Będziesz:", ""],
        "profile": ["Wymagania", "Kogo szukamy", "Twój profil"],
        "qualification": "Wykształcenie: {value}",
        "experience": "Doświadczenie: {value}",
        "knowledge": "Wiedza: {value}",
        "soft_skills": "Umiejętności miękkie: {value}",
        "regulated": "Zawód regulowany: wymagany dyplom lub uprawnienia",
        "offer": ["Oferujemy", "Nasza oferta", "Warunki zatrudnienia"],
        "contract": "Rodzaj umowy: {value}",
        "salary": "Wynagrodzenie: {value}",
        "location": "Miejsce pracy: {city}, {country}",
        "remote": {"hybrid": "Praca hybrydowa: częściowo zdalnie", "remote": "Praca w pełni zdalna"},
        "benefits": "Benefity: {value}",
        "apply": ["Jak aplikować", "Aplikuj", "Zainteresowany/a?"],
        "apply_text": [
            "Wyślij swoją aplikację do: {contact_person}, tel. {contact}, z numerem referencyjnym {job_id}.",
            "Skontaktuj się z: {contact_person}, tel. {contact}, numer oferty: {job_id}.",
        ],
        "posted": "Ogłoszenie opublikowane {date} w serwisie {portal}.",
        "date": "{day} {month} {year}",
        # Genitive, as in dates ("13 listopada 2026").
        "months": ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia",
                   "września", "października", "listopada", "grudnia"],
        "thousands": "\u00a0",   # no-break space
        "and": " i ",
    },
    "sv": {
        "intro": [
            "{company} söker medarbetare i {city}.",
            "{company} växer och förstärker teamet i {city}.",
            "Söker du en ny utmaning? {company} rekryterar i {city}.",
        ],
        "intro_sector": [
            "{company} ({sector}, {size} anställda) söker medarbetare i {city}.",
            "Med {size} anställda inom {sector} förstärker {company} teamet i {city}.",
            "Bli en del av {company} ({sector}, {size} anställda) i {city}.",
        ],
        "industry": "Verksamhet: {industry}.",
        "job": ["Om tjänsten", "Tjänstebeskrivning", "Rollen"],
        "no_description": ["Du kommer att arbeta som {title}, inom området {domain}."],
        "transitions": {
            "ecological": "Yrket bidrar till den gröna omställningen.",
            "digital": "Yrket står i centrum för den digitala omställningen.",
            "demographic": "Yrket möter behoven hos en åldrande befolkning.",
        },
        "missions": ["Arbetsuppgifter", "Dina uppgifter", "I vardagen"],
        "missions_lead": ["Dina huvudsakliga uppgifter:", "Du kommer att:", ""],
        "profile": ["Kvalifikationer", "Vem vi söker", "Din profil"],
        "qualification": "Utbildning: {value}",
        "experience": "Erfarenhet: {value}",
        "knowledge": "Kunskaper: {value}",
        "soft_skills": "Personliga egenskaper: {value}",
        "regulated": "Reglerat yrke: examen eller legitimation krävs",
        "offer": ["Vi erbjuder", "Vårt erbjudande", "Anställningsvillkor"],
        "contract": "Anställningsform: {value}",
        "salary": "Lön: {value}",
        "location": "Arbetsort: {city}, {country}",
        "remote": {"hybrid": "Hybridarbete: delvis distansarbete", "remote": "Helt på distans"},
        "benefits": "Förmåner: {value}",
        "apply": ["Ansökan", "Så söker du", "Intresserad?"],
        "apply_text": [
            "Skicka din ansökan till {contact_person}, tel. {contact}, och ange referens {job_id}.",
            "Kontakta {contact_person} på {contact}, annonsreferens: {job_id}.",
        ],
        "posted": "Publicerad {date} på {portal}.",
        "date": "{day} {month} {year}",
        "months": ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september",
                   "oktober", "november", "december"],
        "thousands": " ",   # no-break space
        "and": " och ",
    },
    "cs": {
        "intro": [
            "{company} hledá nové kolegy do lokality {city}.",
            "{company} rozšiřuje tým v lokalitě {city}.",
            "Hledáte novou výzvu? {company} přijímá zaměstnance v lokalitě {city}.",
        ],
        "intro_sector": [
            "{company} (obor: {sector}, {size} zaměstnanců) hledá nové kolegy do lokality {city}.",
            "Společnost {company} s {size} zaměstnanci v oboru {sector} rozšiřuje tým v lokalitě {city}.",
            "Přidejte se ke {company} (obor: {sector}, {size} zaměstnanců) v lokalitě {city}.",
        ],
        "industry": "Činnost: {industry}.",
        "job": ["Pozice", "Popis pozice", "O pozici"],
        "no_description": ["Budete pracovat jako {title}, v oblasti {domain}."],
        "transitions": {
            "ecological": "Tato profese přispívá k ekologické transformaci.",
            "digital": "Tato profese je v centru digitální transformace.",
            "demographic": "Tato profese odpovídá na potřeby stárnoucí populace.",
        },
        "missions": ["Náplň práce", "Vaše úkoly", "Co vás čeká"],
        "missions_lead": ["Vaše hlavní úkoly:", "Budete:", ""],
        "profile": ["Požadavky", "Koho hledáme", "Váš profil"],
        "qualification": "Vzdělání: {value}",
        "experience": "Praxe: {value}",
        "knowledge": "Znalosti: {value}",
        "soft_skills": "Osobnostní předpoklady: {value}",
        "regulated": "Regulovaná profese: vyžaduje se diplom nebo oprávnění",
        "offer": ["Nabízíme", "Naše nabídka", "Pracovní podmínky"],
        "contract": "Typ úvazku: {value}",
        "salary": "Mzda: {value}",
        "location": "Místo výkonu práce: {city}, {country}",
        "remote": {"hybrid": "Hybridní práce: částečně home office", "remote": "Plně vzdálená práce"},
        "benefits": "Benefity: {value}",
        "apply": ["Jak se přihlásit", "Odpovědět na inzerát", "Máte zájem?"],
        "apply_text": [
            "Pošlete svůj životopis na: {contact_person}, tel. {contact}, s referenčním číslem {job_id}.",
            "Kontaktujte: {contact_person}, tel. {contact}, číslo nabídky: {job_id}.",
        ],
        "posted": "Inzerát zveřejněn {date} na {portal}.",
        "date": "{day}. {month} {year}",
        "months": ["ledna", "února", "března", "dubna", "května", "června", "července", "srpna", "září", "října",
                   "listopadu", "prosince"],
        "thousands": " ",   # no-break space
        "and": " a ",
    },
    "ro": {
        "intro": [
            "{company} angajează în {city}.",
            "{company} își extinde echipa din {city}.",
            "Cauți o nouă provocare? {company} angajează în {city}.",
        ],
        "intro_sector": [
            "{company} ({sector}, {size} angajați) angajează în {city}.",
            "Cu {size} angajați în domeniul {sector}, {company} își extinde echipa din {city}.",
            "Alătură-te {company} ({sector}, {size} angajați) în {city}.",
        ],
        "industry": "Activitate: {industry}.",
        "job": ["Postul", "Descrierea postului", "Despre post"],
        "no_description": ["Vei lucra ca {title}, în domeniul {domain}."],
        "transitions": {
            "ecological": "Această meserie contribuie la tranziția ecologică.",
            "digital": "Această meserie se află în centrul tranziției digitale.",
            "demographic": "Această meserie răspunde nevoilor unei populații îmbătrânite.",
        },
        "missions": ["Responsabilități", "Ce vei face", "Activitatea zilnică"],
        "missions_lead": ["Principalele tale sarcini:", "Vei:", ""],
        "profile": ["Cerințe", "Pe cine căutăm", "Profilul tău"],
        "qualification": "Studii: {value}",
        "experience": "Experiență: {value}",
        "knowledge": "Cunoștințe: {value}",
        "soft_skills": "Competențe personale: {value}",
        "regulated": "Profesie reglementată: diplomă sau aviz de liberă practică obligatorii",
        "offer": ["Ce oferim", "Oferta noastră", "Condiții"],
        "contract": "Tip de contract: {value}",
        "salary": "Salariu: {value}",
        "location": "Locul de muncă: {city}, {country}",
        "remote": {"hybrid": "Regim hibrid: parțial de acasă", "remote": "Lucru 100% de la distanță"},
        "benefits": "Beneficii: {value}",
        "apply": ["Cum aplici", "Aplică", "Te interesează?"],
        "apply_text": [
            "Trimite CV-ul către {contact_person}, tel. {contact}, cu referința {job_id}.",
            "Contactează-l/o pe {contact_person} la {contact}, referința anunțului: {job_id}.",
        ],
        "posted": "Anunț publicat pe {date} pe {portal}.",
        "date": "{day} {month} {year}",
        "months": ["ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie",
                   "octombrie", "noiembrie", "decembrie"],
        "thousands": ".",
        "and": " și ",
    },
    "el": {
        "intro": [
            "Η {company} προσλαμβάνει στην περιοχή {city}.",
            "Η {company} ενισχύει την ομάδα της στην περιοχή {city}.",
            "Αναζητάτε μια νέα πρόκληση; Η {company} προσλαμβάνει στην περιοχή {city}.",
        ],
        "intro_sector": [
            "Η {company} ({sector}, {size} εργαζόμενοι) προσλαμβάνει στην περιοχή {city}.",
            "Με {size} εργαζομένους στον κλάδο {sector}, η {company} ενισχύει την ομάδα της στην περιοχή {city}.",
            "Γίνετε μέλος της {company} ({sector}, {size} εργαζόμενοι) στην περιοχή {city}.",
        ],
        "industry": "Δραστηριότητα: {industry}.",
        "job": ["Η θέση", "Περιγραφή θέσης", "Σχετικά με τη θέση"],
        "no_description": ["Θα εργαστείτε ως {title}, στον τομέα {domain}."],
        "transitions": {
            "ecological": "Το επάγγελμα συμβάλλει στην πράσινη μετάβαση.",
            "digital": "Το επάγγελμα βρίσκεται στο επίκεντρο του ψηφιακού μετασχηματισμού.",
            "demographic": "Το επάγγελμα ανταποκρίνεται στις ανάγκες ενός γηράσκοντος πληθυσμού.",
        },
        "missions": ["Αρμοδιότητες", "Τι θα κάνετε", "Καθημερινά"],
        "missions_lead": ["Οι κύριες αρμοδιότητές σας:", "Θα:", ""],
        "profile": ["Απαιτούμενα προσόντα", "Ποιον αναζητούμε", "Το προφίλ σας"],
        "qualification": "Σπουδές: {value}",
        "experience": "Προϋπηρεσία: {value}",
        "knowledge": "Γνώσεις: {value}",
        "soft_skills": "Δεξιότητες: {value}",
        "regulated": "Νομοθετικά κατοχυρωμένο επάγγελμα: απαιτείται πτυχίο ή άδεια άσκησης επαγγέλματος",
        "offer": ["Προσφέρουμε", "Η προσφορά μας", "Όροι εργασίας"],
        "contract": "Σχέση εργασίας: {value}",
        "salary": "Αποδοχές: {value}",
        "location": "Τόπος εργασίας: {city}, {country}",
        "remote": {"hybrid": "Υβριδική εργασία: εν μέρει τηλεργασία", "remote": "Πλήρης τηλεργασία"},
        "benefits": "Παροχές: {value}",
        "apply": ["Αιτήσεις", "Πώς να υποβάλετε αίτηση", "Ενδιαφέρεστε;"],
        "apply_text": [
            "Στείλτε το βιογραφικό σας στον/στην {contact_person}, τηλ. {contact}, με κωδικό αγγελίας {job_id}.",
            "Επικοινωνήστε με τον/την {contact_person} στο {contact}, κωδικός αγγελίας: {job_id}.",
        ],
        "posted": "Η αγγελία δημοσιεύθηκε στις {date} στο {portal}.",
        "date": "{day} {month} {year}",
        "months": ["Ιανουαρίου", "Φεβρουαρίου", "Μαρτίου", "Απριλίου", "Μαΐου", "Ιουνίου", "Ιουλίου", "Αυγούστου",
                   "Σεπτεμβρίου", "Οκτωβρίου", "Νοεμβρίου", "Δεκεμβρίου"],
        "thousands": ".",
        "and": " και ",
    },
    "ar": {
        "intro": [
            "تعلن {company} عن توفر وظيفة شاغرة في {city}.",
            "تعزز {company} فريق عملها في {city}.",
            "هل تبحث عن تحدٍّ جديد؟ تعلن {company} عن وظيفة شاغرة في {city}.",
        ],
        "intro_sector": [
            "تعلن {company} ({sector}، {size} موظف) عن توفر وظيفة شاغرة في {city}.",
            "تعزز {company}، التي تضم {size} موظف في قطاع {sector}، فريق عملها في {city}.",
            "انضم إلى {company} ({sector}، {size} موظف) في {city}.",
        ],
        "industry": "النشاط: {industry}.",
        "job": ["الوظيفة", "الوصف الوظيفي", "عن الوظيفة"],
        "no_description": ["ستعمل في مهنة {title}، في مجال {domain}."],
        "transitions": {
            "ecological": "تسهم هذه المهنة في التحول البيئي.",
            "digital": "هذه المهنة في صميم التحول الرقمي.",
            "demographic": "تلبي هذه المهنة احتياجات مجتمع يتقدم في العمر.",
        },
        "missions": ["المهام والمسؤوليات", "ما ستقوم به", "عملك اليومي"],
        "missions_lead": ["مهامك الرئيسية:", "ستقوم بما يلي:", ""],
        "profile": ["المتطلبات", "من نبحث عنه", "ملفك المهني"],
        "qualification": "المؤهل العلمي: {value}",
        "experience": "الخبرة: {value}",
        "knowledge": "المعارف: {value}",
        "soft_skills": "المهارات الشخصية: {value}",
        "regulated": "مهنة منظمة: يشترط الحصول على شهادة أو ترخيص مزاولة المهنة",
        "offer": ["ما نقدمه", "عرضنا", "شروط العمل"],
        "contract": "نوع العقد: {value}",
        "salary": "الراتب: {value}",
        "location": "مكان العمل: {city}، {country}",
        "remote": {"hybrid": "عمل مرن: جزئيًا عن بعد", "remote": "عمل عن بعد بالكامل"},
        "benefits": "المزايا: {value}",
        "apply": ["طريقة التقديم", "التقديم", "مهتم؟"],
        "apply_text": [
            "أرسل سيرتك الذاتية إلى {contact_person}، هاتف {contact}، مع ذكر الرقم المرجعي {job_id}.",
            "تواصل مع {contact_person} على الرقم {contact}، الرقم المرجعي للوظيفة: {job_id}.",
        ],
        "posted": "نُشر الإعلان في {date} على {portal}.",
        "date": "{day} {month} {year}",
        "months": ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر",
                   "نوفمبر", "ديسمبر"],
        "thousands": ",",
        "and": " و",
        "comma": "، ",
        "list_separator": "؛ ",
        "lower_soft_skills": False,
    },
}


def _upper(text: str) -> str:
    """Upper case, without the Greek stress accents capitals drop ('Όροι' -> 'ΟΡΟΙ')."""
    upper = text.upper()
    if any("\u0370" <= char <= "\u03ff" for char in upper):
        upper = unicodedata.normalize("NFC", "".join(char for char in unicodedata.normalize("NFD", upper)
                                                     if char != "\u0301"))
    return upper


def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def _join(items: list[str], texts: Mapping[str, Any]) -> str:
    """'a, b and c'; 'a; b; c' when an item has a comma of its own."""
    if any("," in item for item in items):
        return str(texts.get("list_separator", "; ")).join(items)
    comma = str(texts.get("comma", ", "))
    return items[0] if len(items) == 1 else comma.join(items[:-1]) + texts["and"] + items[-1]


def _date(texts: Mapping[str, Any], date: _datetime.date) -> str:
    return str(texts["date"].format(day=date.day, month=texts["months"][date.month - 1], year=date.year))


def render_posting(
    posting: Mapping[str, Any], language: str, rng: random.Random, markdown: bool = False
) -> str:
    """The text of an `OccupationPosting` or a `JobPosting` in `language`
    ('fr', 'en', 'de', 'es', 'it', 'pt', 'nl', 'pl', 'sv', 'cs', 'ro', 'el', 'ar'), plain or in Markdown."""
    texts = TEXTS[language]
    occupation = posting["occupation"]
    company = posting["company"]
    location = posting["location"]
    # OccupationPosting: skills = the activities picked; JobPosting: responsibilities.
    activities = posting["skills"] if isinstance(posting["skills"], list) else posting["responsibilities"].split("; ")
    sector = posting.get("company_sector", company["sector"])
    values = {
        "company": company["company"],
        "city": location["city"],
        "country": location["country"],
        "sector": sector,
        "size": f"{posting['company_size']:,}".replace(",", texts["thousands"]),
        "industry": company["industry"],
        "title": occupation["title"],
        "code": occupation["code"],
        "domain": occupation["domain"],
        "contact_person": posting["contact_person"],
        "contact": posting["contact"],
        "job_id": posting["job_id"],
        "date": _date(texts, posting["job_posting_date"]),
        "portal": posting["job_portal"],
    }

    def pick(key: str) -> str:
        return str(rng.choice(texts[key]).format(**values))

    def line(key: str, value: object = None) -> str:
        return str(texts[key].format(value=value, **values))

    def heading(key: str) -> str:
        return f"## {pick(key)}" if markdown else _upper(pick(key))

    def bullets(items: list[str]) -> list[str]:
        return [f"- {_capitalize(item)}" for item in items]

    title = _capitalize(posting["job_title"])
    facts = " · ".join([company["company"], f"{location['city']}, {location['country']}", posting["work_type"]])
    lines = [f"# {title}" if markdown else title, f"**{facts}**" if markdown else facts, ""]

    intro = pick("intro_sector" if sector else "intro")
    if company["industry"]:
        intro += " " + line("industry")
    lines += [intro, ""]

    job = [occupation["description"] or pick("no_description")]
    job += [texts["transitions"][name] for name in occupation["transitions"]]
    lines += [heading("job"), " ".join(job), ""]

    lead = pick("missions_lead")
    lines += [heading("missions"), *([lead] if lead else []), *bullets(activities), ""]

    knowledge = rng.sample(occupation["knowledge"], min(4, len(occupation["knowledge"])))
    soft_skills = rng.sample(occupation["soft_skills"], min(3, len(occupation["soft_skills"])))
    profile = [line("qualification", posting["qualification"]), line("experience", posting["experience"])]
    if knowledge:
        profile.append(line("knowledge", _join(knowledge, texts)))
    if soft_skills:
        listed = _join(soft_skills, texts)
        profile.append(line("soft_skills", listed.lower() if texts.get("lower_soft_skills", True) else listed))
    if occupation["regulated"]:
        profile.append(texts["regulated"])
    lines += [heading("profile"), *bullets(profile), ""]

    offer = [line("contract", posting["work_type"]), line("salary", posting["salary_range"]), line("location")]
    if posting["remote"] != "on_site":
        offer.append(texts["remote"][posting["remote"]])
    if posting["benefits"]:
        offer.append(line("benefits", _join(posting["benefits"], texts)))
    lines += [heading("offer"), *bullets(offer), ""]

    lines += [heading("apply"), pick("apply_text"), line("posted")]
    return "\n".join(lines)
