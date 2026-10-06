"""
generate_laravel_personalized_emails.py

Builds laravel_personalized_emails.csv from laravel-jobs.csv using
hand-verified company research (each fact below was checked against the
company's own website or independent sources - see the research notes in
this file's git history / conversation for sources). No emails are sent by
this script and laravel-jobs.csv is never modified.

Every email uses the same body: no company-specific fact, just a short
self-introduction grounded in Ahmed's actual CV (CV_AHMED_BEN_BETTAIEB.pdf)
- his real stack, current role and project background - followed by a
direct statement of interest. The RESEARCH dict below is still kept for
reference (Website / ResearchSummary / ResearchStatus columns in the
output CSV) even though it's no longer injected into the email body.
"""

import csv
import sys

CSV_PATH = "laravel-jobs.csv"
OUT_PATH = "laravel_personalized_emails.csv"

FIELDS = ["Company", "Email", "Website", "ResearchSummary", "Subject", "Body", "ResearchStatus"]

SUBJECT = "Spontaneous Application - Full-Stack Developer (Laravel)"

# company (lowercase) -> (website, fact sentence, template kind)
# template kind: "agency"  -> company builds software/products for clients
#                "product" -> company builds/runs its own product or platform
#
# Facts describe only what the company does - its market, services, products
# or tech stack. Founding dates, headcount, years of experience and other
# history/scale trivia are deliberately left out.
RESEARCH = {
    "nehos groupe": (
        "https://www.nehos-groupe.com",
        "Nehos Groupe is an AI agency building enterprise RAG systems and full-stack Next.js/React applications for companies across France, Europe and Tunisia.",
        "agency",
    ),
    "appinov": (
        "https://appinov.io",
        "Appinov is a web and mobile development agency working across Tunisia, France and Canada, building custom software and e-commerce platforms with a stack spanning React, Node.js, PHP and Symfony.",
        "agency",
    ),
    "classquiz": (
        "https://classquiz.tn",
        "Class Quiz is a Tunisian edtech platform delivering curriculum-aligned interactive exercises to primary school students through its mobile and web apps.",
        "product",
    ),
    "logient": (
        "https://www.logient.com",
        "Logient is a digital transformation and AI consulting firm delivering application development, cloud migration and enterprise platform integrations across the Microsoft, Salesforce and SAP ecosystems.",
        "agency",
    ),
    "diool / diool labs": (
        "https://www.diool.com",
        "Diool (Diool Labs) is a pan-African fintech providing trade finance, supply chain finance and B2B Buy Now Pay Later solutions to businesses across Zambia, Cameroon, Cote d'Ivoire and Senegal.",
        "product",
    ),
    "its tunisie": (
        "https://itserv.tn",
        "IT SERV is a Tunisian digital services company delivering e-government platforms, telecom billing/BSS systems and digital-health solutions to clients across multiple countries.",
        "agency",
    ),
    "informatech tunisie": (
        "",
        "InformaTech Tunisie is a Teboulba-based software company whose engineers work with ReactJS, Laravel and React Native on client web and mobile projects.",
        "agency",
    ),
    "iovision": (
        "https://www.iovision.io",
        "IOVISION is a Sfax-based offshore software studio building AI-powered web and mobile products - including Finispia (ethical fintech), MooMe (dairy-farm management) and Stile (AI fashion shopping).",
        "product",
    ),
    "khallasli": (
        "https://www.khallasli.com",
        "Khallasli is a Sousse-based Tunisian fintech aggregating digital financial services - bill payments, mobile recharges, prepaid card top-ups and merchant payments - through a web platform, its Digitis mobile app, kiosks and a partner API.",
        "product",
    ),
    "proxym group": (
        "https://www.proxym-group.com",
        "Proxym Group builds the Bankerise and Insurise digital platforms for banks and insurers, plus Smart Gov e-government solutions, through its Proxym-IT web, mobile and information-systems teams.",
        "agency",
    ),
    "2y2s tunisia": (
        "https://2y2s.net",
        "2Y2S is a Tunisian edtech company behind EducaKids, a school-management platform handling online enrollment, academic tracking and parent communication for kindergartens and educational institutions.",
        "product",
    ),
    "club privilèges": (
        "https://clubprivileges.app",
        "Club Privilèges runs a loyalty-rewards app connecting members in Tunisia with discounts at partner retail locations via in-app QR-code scanning.",
        "product",
    ),
    "welyne": (
        "https://www.welyne.com",
        "Welyne is a Paris/Tunis/Dubai product studio building AI agents, computer vision and full-stack web & mobile applications, including its Welyne ONE retail kiosk and WeeFizz body-scanning technology.",
        "agency",
    ),
    "vaerdia": (
        "",
        "",
        "unverified",
    ),
    "millisave software": (
        "https://www.millisave.com",
        "Millisave builds a modular procurement-to-CRM business platform - covering source-to-pay, sales pipelines and an AI forecasting module - to unify supplier and customer operations for its clients.",
        "product",
    ),
    "ecg assurances": (
        "https://www.ecg-pereire-assurances.com",
        "ECG Pereire Assurances is an independent insurance brokerage serving clients across Tunisia, Morocco and Senegal, negotiating coverage with a wide network of insurance partners.",
        "agency",
    ),
    "web media tunisie": (
        "https://www.webmedia-tunisie.com",
        "Web Media is a Tunisian digital agency delivering websites and e-commerce projects, building on WordPress/WooCommerce, custom web applications and AI-driven chatbot integrations.",
        "agency",
    ),
    "media web services (mws)": (
        "https://www.mws-services.com",
        "Media Web Services (MWS) is a Tunisian web agency delivering custom platforms and e-commerce sites, working across WordPress, React, Laravel, PrestaShop, Shopify and WooCommerce.",
        "agency",
    ),
    "velorex digital": (
        "https://www.velorex-digital.com",
        "Velorex Digital is a Hammamet/Nabeul-based web agency building projects with a stack spanning Laravel, PHP, MySQL, React, Next.js and Tailwind CSS.",
        "agency",
    ),
    "itgust": (
        "https://www.itgust-group.com",
        "ITGust is a Tunis-based web & AI agency building websites, mobile apps and custom AI agents with a stack centered on React, Node.js and major cloud platforms (AWS, Azure, GCP).",
        "agency",
    ),
    # --- laravel-jobs-new.csv (companies where Tunisian Laravel/PHP devs work) ---
    "elyos digital": (
        "https://www.elyosdigital.com",
        "Elyos Digital is a Monastir-based web agency working across Tunisia and France, delivering websites, mobile apps, web design and digital-transformation projects for its clients.",
        "agency",
    ),
    "anypli": (
        "https://anypli.com",
        "Anypli is a Monastir-based web and mobile development agency building iOS/Android apps, web platforms and digital marketing solutions for national and international brands in healthcare, transportation and communication.",
        "agency",
    ),
    "maisonduweb": (
        "https://mdw.engineering",
        "",
        "unverified",
    ),
    "pixel pro agency": (
        "https://pixelpro-agency.com",
        "Pixel Pro is a Sfax-based web agency delivering custom web development, mobile solutions, branding, audiovisual production and 3D work for its clients.",
        "agency",
    ),
    "sascode": (
        "https://sascode.io",
        "Sascode is a Tunis-based software studio building websites, business platforms, mobile apps and dashboards, including management systems for hospitality, retail, delivery and food-and-beverage POS.",
        "product",
    ),
    "tac-tic": (
        "https://www.tac-tic.net",
        "TAC-TIC is an Ariana-based software engineering company delivering web and mobile development, digital transformation, IT networks and telecom consulting.",
        "agency",
    ),
    "i-techrity": (
        "https://i-techrity.tn",
        "i-Techrity is a Tunisian ICT4D civic-tech startup building transparency and civic-engagement platforms such as Pinvestigate and Atide, and websites for 360 Tunisian municipalities.",
        "product",
    ),
    "next consult": (
        "https://next.tn",
        "NEXT Consult is a Tunis-based technology consulting firm specializing in web and mobile application development, web marketing and digital transformation.",
        "agency",
    ),
    "medianet": (
        "https://www.medianet-group.com",
        "Medianet is a Tunis-based digital agency delivering web and mobile development, e-commerce platforms, AI automation and digital marketing for clients in banking, insurance, tourism and government across Africa, Europe and North America.",
        "agency",
    ),
    "civitas technologies": (
        "https://civitas.tn",
        "CIVITAS builds a customer-service platform for government institutions - a mobile app and online portal that let citizens track permit and licence applications in real time while giving administrations configurable workflow tools.",
        "product",
    ),
    "xenius consulting": (
        "https://xeniusconsulting.com",
        "Xenius Consulting builds digital-transformation platforms, mainly for the insurance sector with Isinsur, alongside education products (Xensoft, Ulearn) and custom web and mobile development.",
        "product",
    ),
    "laser informatique & solutions": (
        "https://www.laserinformatique.com",
        "Laser Informatique & Solutions is a Tunis-based software company building management software for financial services, pharmaceuticals, automotive dealers and leasing, and offering nearshore development and web solutions.",
        "product",
    ),
    "lookiimobile tunisie": (
        "https://lookiimobile.com",
        "Lookiimobile builds digital security and collaboration products - including MyCena Desk Center, Personal Fortress and Business Fortress - with a development team in Tunis.",
        "product",
    ),
    "webify technology": (
        "https://webifyia.com",
        "Webify Technology is a Sousse-based digital agency specializing in web and mobile app development, UI/UX design, AI integration and CMS/ERP solutions.",
        "agency",
    ),
    "octasoft": (
        "https://octasoft.com.tn",
        "OCTASOFT is a software company specializing in e-tourism, building web, desktop and mobile applications for travel agencies, hotels and spas, including its OSTravel booking and back-office platform.",
        "product",
    ),
    "piximind": (
        "https://www.piximind.com",
        "PixiMind is a Tunisian nearshore digital center building web, mobile, e-commerce and AI solutions for clients in e-commerce, insurance, healthcare and telecom, with a stack spanning React, Angular, Laravel, Next.js and Flutter.",
        "agency",
    ),
    "wind consulting": (
        "https://www.wind-consulting-tunisia.com",
        "Wind Consulting is a Mahdia-based software company supporting clients' digital transformation through consulting, digital solutions, IoT and development outsourcing.",
        "agency",
    ),
    "creo": (
        "https://www.creo.tn",
        "Creo is a Sousse-based digital consulting firm helping companies analyze their performance and implement digital-transformation and change-management projects.",
        "agency",
    ),
    "itgate group": (
        "https://itgate-group.com",
        "ITGate Group is a Sousse-based digital agency delivering website creation, mobile app development, graphic design, SEO, community management and embedded-systems work.",
        "agency",
    ),
    "provesta soft": (
        "https://www.provestasoft.com",
        "Provesta Software builds custom web, mobile and desktop applications and ERP/CRM systems, alongside AI, business-intelligence and SEO services.",
        "agency",
    ),
    "satoripop": (
        "https://www.satoripop.com",
        "Satoripop builds custom applications, AI-powered tools and industry platforms for retail, banking, insurance, hospitality and government, with cloud, data-integration and modernization services.",
        "agency",
    ),
    "sofonn solutions": (
        "https://sofonn.com",
        "Sofonn builds digital solutions for the maritime industry, including the Marine IQ and Marine LOG platforms for fleet management, crew oversight and regulatory compliance.",
        "product",
    ),
    "netadvisor": (
        "https://netadvisor.tn",
        "NetAdvisor is a Sfax-based digital agency delivering web and mobile development, UI/UX design and digital marketing, working with Node.js, Django, Laravel, Angular and Python.",
        "agency",
    ),
    "hypergroup": (
        "https://www.hypergroup.com.tn",
        "Hyper Group is a Sfax-based group of specialized companies delivering web-solution development, digital communication and graphic design for clients across North Africa.",
        "agency",
    ),
    "barthauer software tunisia": (
        "https://www.barthauer.de",
        "Barthauer develops IT solutions for infrastructure and water management - chiefly BaSYS, a database-driven infrastructure management system - with a development subsidiary in Sousse.",
        "product",
    ),
    "iec telecom": (
        "https://www.iec-telecom.com",
        "IEC Telecom provides satellite communications and managed connectivity for land and maritime operations, combining satellite and terrestrial networks with managed IT services and digital solutions.",
        "product",
    ),
    "your team in tunisia": (
        "https://www.yourteamintunisia.com",
        "Your Team In Tunisia provides Employer of Record services that let European companies hire and manage Tunisian employees without setting up a local subsidiary.",
        "agency",
    ),
    "novatis": (
        "https://www.novatis.tn",
        "Novatis is a Tunisian web agency specializing in custom Laravel development, building business-rule-driven web platforms, e-commerce, SEO and AI automation.",
        "agency",
    ),
    "1waydev": (
        "https://www.1waydev.com",
        "1WayDev is a Tunis-based nearshore agency building custom business web applications, websites and e-commerce stores with Laravel, React and Next.js, plus SEO and paid-advertising services.",
        "agency",
    ),
    "witify": (
        "https://witify.io",
        "Witify is a Montreal-based custom software company building management and automation software, system modernization and web and mobile applications.",
        "agency",
    ),
    "mawadonline": (
        "https://mawadonline.com",
        "MawadOnline is a UAE e-commerce marketplace for construction materials and equipment, connecting suppliers with construction professionals across the Emirates.",
        "product",
    ),
    "aquil'app": (
        "https://aquilapp.fr",
        "AquilApp is a Nantes-based web and mobile agency building bespoke web applications, mobile apps and e-commerce platforms, and offering CTO consulting.",
        "agency",
    ),
}

# Self-introduction grounded in CV_AHMED_BEN_BETTAIEB.pdf - no company facts,
# just Ahmed's real background, then a direct statement of interest. Used for
# every row, regardless of ResearchStatus.
BODY = """\
Dear Hiring Team at {company},

My name is Ahmed Ben Bettaieb, a Full-Stack Software Engineer with 3+ years of experience building web applications with Laravel, React, and Node.js. I currently build multi-tenant SaaS platforms using Laravel, Livewire, FilamentPHP and PostgreSQL, and I've also worked on e-commerce, real estate and payment-integration projects using MySQL, MongoDB and REST APIs. My focus spans the full stack, from secure, maintainable backend architecture to responsive React/Next.js interfaces, and I deploy and maintain applications with Docker, Nginx and CI/CD pipelines on Linux servers.

I'm interested in contributing to your team, and I've attached my CV for your consideration.

Best regards,

Ahmed Ben Bettaieb
"""


def read_recipients(csv_path):
    """Read (company, email) pairs from laravel-jobs.csv. Does not modify the file."""
    recipients = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for row in reader:
            if len(row) < 2:
                continue
            company = row[0].strip()
            email = row[1].strip()
            if email:
                recipients.append((company, email))
    return recipients


def build_row(company, email):
    key = company.strip().lower()
    website, fact, kind = RESEARCH.get(key, ("", "", "unverified"))

    status = "Verified" if kind in ("agency", "product") and fact else "Unverified"
    summary = fact if status == "Verified" else "Research unavailable"
    body = BODY.format(company=company)

    return {
        "Company": company,
        "Email": email,
        "Website": website,
        "ResearchSummary": summary,
        "Subject": SUBJECT,
        "Body": body,
        "ResearchStatus": status,
    }


def generate(csv_path=CSV_PATH, out_path=OUT_PATH):
    recipients = read_recipients(csv_path)
    if not recipients:
        print(f"No recipients found in '{csv_path}'. Nothing to do.")
        return

    rows_out = [build_row(company, email) for company, email in recipients]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows_out)

    verified = sum(1 for r in rows_out if r["ResearchStatus"] == "Verified")
    unverified = len(rows_out) - verified
    print(f"Generated {len(rows_out)} personalized emails -> '{out_path}'.")
    print(f"Verified: {verified}  Unverified: {unverified}")


if __name__ == "__main__":
    # Optional: python generate_laravel_personalized_emails.py <input.csv> <output.csv>
    generate(*sys.argv[1:3])
