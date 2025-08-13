# Digital Meal

**Digital Meal** is a web-based learning and teaching tool designed to foster media literacy among students.  
The overarching goal of the Digital Meal project is to provide educators with teaching materials and an interactive 
application that encourage their students' critical reflection on personal media usage.

The core idea behind Digital Meal is to:

- Instruct students on how to request and download personal data collected by digital platforms (e.g., from YouTube and TikTok).
- Provide an application that generates personalized usage reports based on the retrieved platform data.
- Offer learning and teaching materials to guide (self-)reflection and discussions about media use.

---

## Used Frameworks

Digital Meal is built using:

- Python
- Django

It is developed to be used alongside [django-ddm](https://github.com/uzh/ddm), 
a web application for collecting data donations and enriching them with questionnaire responses.

---

## Usage

> ⚠️ This repository is intended primarily for internal use.  
> It is not yet optimized for external projects or broader integrations.

---

## Project Structure

The structure of the repository is organized as follows:

- **config/**: Central project configuration, including settings, URLs, and deployment entry points (WSGI/ASGI).

- **digital_meal/**: Contains the main Digital Meal Django application with the following sub-applications and files::
  - **reports/**: Responsible for generating media usage reports.
  - **tool/**: Provides the admin interface for teachers to register and manage classes.
  - **website/**: Handles public-facing website components, including CMS (Wagtail) integration.
  - **urls.py**: Defines the main URL routes for the sub-applications.

- **templates/**: Contains overrides of base templates from used dependencies (mainly allauth and Django defaults).

- **.env.example**: Example file listing the environmental variables needed for local or production deployment.

---

## Quickstart

Follow these steps to get a local development environment up and running:

1. **Clone the repository**

```bash
git clone https://github.com/your-username/digital-meal.git
cd digital-meal
```

2. **Set up a virtual environment**

```bash
python -m venv venv
source venv/bin/activate   # On Windows use: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt

# For the wordcloud pre-processing, we also need:
python -m spacy download en_core_web_sm
python -m spacy download de_core_news_sm
```

4. **Configure environment variables**

Copy the example environment file and adjust it as needed:

```bash
cp .env.example .env
```

Edit `.env` to set your local environment variables.

5. **Apply database migrations**

```bash
python manage.py migrate
```

6. **Add necessary settings to settings.py.**

```python
DAYS_TO_DONATION_DELETION = 180  # Defines the timespan after which donations are deleted if no consent was given.
ALLOWED_REPORT_DOMAINS = ['some-domain.com']  # Is used to verify the report link domain when sending it via automated emails.
```

7. **Create a superuser (admin account)**

```bash
python manage.py createsuperuser
```

8. **Run the development server**

```bash
python manage.py runserver
```

9. **Access the application**

Open your browser and navigate to: http://127.0.0.1:8000/

---

## Contributors & Contact

Digital Meal is developed by the [Media Use and Effects division 
of the University of Zurich](https://www.ikmz.uzh.ch/en/research/divisions/media-use-and-effects.html), 
with financial support from [Citizen Science Zürich](https://www.citizenscience.uzh.ch/de.html).

Contact: [kontakt@digital-meal.ch](mailto:kontakt@digital-meal.ch). 

---

## License

This project is licensed under the [GNU General Public License v3.0 (GPL-3.0)](https://www.gnu.org/licenses/gpl-3.0.html).
