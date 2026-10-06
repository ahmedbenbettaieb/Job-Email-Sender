# Job Sender

A tool to find, research, and send personalized job application emails to companies. This repo contains scripts to generate personalized emails from CSV files and send them via SMTP.

## How to Find Companies to Contact

To find relevant companies (especially for Laravel/tech roles in Tunisia or elsewhere):

1. **Job boards** - Search on platforms like LinkedIn, Indeed, WeWorkRemotely, Jobgether, Hired, Wellfound (AngelList), Glassdoor, Rekrute (Tunisia), Emploitic, etc. Look for companies hiring Laravel/PHP/Full-stack roles.

2. **Company directories** - Browse tech company lists (e.g. StartupTunisia, Digital Tunisia, local tech hubs, incubators, Clutch, BuiltIn, StackShare, or chamber of commerce directories).

3. **Google search** - Use targeted queries like:
   - "Laravel" "Tunisie" "contact"
   - "developpeur Laravel" "Tunis" "email"
   - "software company" "Tunisia" site:tn
   - "agency" "Laravel" "contact@*.tn"

4. **GitHub/Portfolios** - Find companies from open-source contributors, Laravel packages, or local tech meetups.

5. **Social media** - Check LinkedIn posts, Twitter/X, Facebook groups (e.g. Tunisian Developers), Discord/Slack communities.

6. **Look for career/contact pages** - Once you find a company, get their official contact email (often contact@, hr@, jobs@, careers@) and website.

7. **Verify emails** - Prefer generic/company emails over personal ones. Avoid scraping personal emails.
## CSV Format

### Jobs CSV (laravel-jobs.csv or similar)
Columns:
- Company - Company name
- Email - Primary contact email
- Email 2 - Optional secondary email
- City - Location (optional)

See example_jobs.csv and example_laravel_jobs.csv for format.

### Personalized Emails CSV
Generated files include research summary, subject, body. See example_personalized_emails.csv and example_laravel_personalized_emails.csv for format.

## Usage

1. Copy example CSVs and fill with your real data: cp example_jobs.csv laravel-jobs.csv
2. Generate personalized emails using the appropriate script
3. Review generated CSVs before sending
4. Send emails using the sender script (configure SMTP in .env)

## Security Notes

- **Never commit** real CSVs with personal/company data - this repo is configured to ignore all *.csv except examples.
- **Never commit** resumes/CVs (*.pdf, CV_*) or .env files.
- Always review generated emails before sending to avoid mistakes.
