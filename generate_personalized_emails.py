"""
generate_personalized_emails.py

Builds personalized_emails.csv from cleaned_emails.csv using hand-verified
company research. No emails are sent.

Every company-specific claim in a "Verified" email comes from the web-research
phase; companies that could not be confidently identified ("Unverified") get a
safe generic email with no company-specific claims.

Personalization approach:
  * Each verified company is classified into a type (SaaS, e-commerce,
    software, consulting, hospitality, education, engineering, real-estate,
    telecom, generic, recruiter, job board) using only the verified fact that
    is already present in the dataset (no guessing).
  * The company fact (hook) is kept verbatim and a connector sentence ties that
    fact to the candidate's actual, CV-supported experience. The connector is
    chosen by company type, so the reason for contacting is logically connected
    to what the company actually does.
  * Recruitment / staffing agencies and job boards are identified ONLY where
    the existing verified fact explicitly says so. They receive a different
    opening ("reaching out to see whether you are currently handling...")
    instead of "opportunities at <Company>".
  * Recruiters and job boards never claim interest in "opportunities at" the
    agency.

The script regenerates personalized_emails.csv and then runs a validation pass
that checks safety, coverage and variety.
"""

import argparse
import csv
import re
import statistics
from collections import Counter, defaultdict

CSV_PATH = "cleaned_emails.csv"
OUT_PATH = "personalized_emails.csv"

FIELDS = ["Company", "Email", "Website", "ResearchSummary", "Subject", "Body", "ResearchStatus"]

SUBJECT = "Spontaneous Application - Full-Stack Software Engineer"

# company (lowercase) -> ("Verified"|"Unverified", hook sentence or None)
# The hooks are hand-verified facts from the research phase. They are used
# verbatim in the generated emails - never edited or expanded here.
RESEARCH = {
    "adecco tunisie": ("Verified", "As part of the Adecco Group, the global leader in talent and staffing, your teams help candidates and companies across more than 60 countries connect every day."),
    "klymber": ("Verified", "Your Paris-based firm recruits senior IT engineers, especially in infrastructure, cloud and cybersecurity, for large accounts and startups across France."),
    "numeryx": ("Verified", "Numeryx delivers IT services and its own software products, including the Business Suite BPM platform and the SASYX next-generation firewall, with teams in France, Tunisia and West Africa."),
    "solinum": ("Verified", "Solinum's digital consulting teams build web and mobile solutions across Java, React, Node.js and mobile frameworks such as Flutter and React Native."),
    "acti security": ("Verified", "ACTI has designed, supplied and maintained security systems such as fire detection, video surveillance and access control in Tunisia and Morocco since 1993."),
    "heptasys": ("Verified", "Heptasys is a French IT consulting firm focused on Cloud, DevOps, Kubernetes and QA/testing, and it also runs an IT staffing unit."),
    "consulting datamed": ("Verified", "Datamed Consulting supports clients through project management, IT infrastructure, digital development and data projects, from requirements through integration and testing."),
    "riskover": ("Verified", "RisKover helps banks, insurers and asset managers implement regulatory risk frameworks such as Basel, ALM and IFRS9, with reporting covering COREP, LCR/NSFR and IRRBB using specialized risk software."),
    "proxwel": ("Verified", "Proxwel provides technology consulting, system integration and nearshoring across ITSM, OSS/BSS, Big Data analytics and IoT, with teams in France, Tunisia and Dubai."),
    "ooredoo": ("Verified", "Ooredoo Tunisie runs mobile, fixed broadband and digital services across 4G/5G networks, fibre and eSIM, backed by the My Ooredoo self-service app."),
    "datasense group": ("Verified", "Datasense Group supports organizations with SI architecture, application development, API management and Agile transformation, including certified training."),
    "jefferson frank": ("Verified", "Jefferson Frank is the AWS-specialist recruitment brand of Tenth Revolution Group, placing cloud, DevOps and data talent across the AWS ecosystem."),
    "addinn": ("Verified", "ADDINN Group is a digital transformation consultancy with offices in Paris, Tunis and Brazzaville, delivering strategy consulting and custom digital products."),
    "consultim it": ("Verified", "CONSULTIM-IT focuses on the Microsoft ecosystem - Microsoft 365, SharePoint, Teams, Azure, Dynamics 365 and Power BI - from its base in Sousse, Tunisia."),
    "value": ("Verified", "Value helps clients define and execute digital and data roadmaps, with strong expertise in data & analytics and generative AI."),
    "noverka conseil": ("Verified", "Noverka Conseil is a Montreal IT consulting and placement firm whose activities now continue under the Quebec-based we+ consultants group."),
    "streamwide": ("Verified", "STREAMWIDE builds mission-critical communication software - push-to-talk, secure messaging and geolocation apps used by public safety, defence and transport organizations such as the French Red Cross."),
    "keythinkers": ("Verified", "KEYTHINKERS is a Paris-based AI agency that audits data/AI architectures and builds AI agents, RAG systems and automation workflows."),
    "deltalink": ("Verified", "DeltaLink is an IT recruitment firm based in Rabat offering IT recruitment, outsourcing, consulting and training."),
    "dracoss": ("Verified", "Dracoss is a Tunisian startup selling anti-scale water filters for showers and faucets, with its own e-commerce site."),
    "adactim": ("Verified", "Adactim is a Microsoft-focused managed services provider covering cloud, infrastructure, cybersecurity and ERP through a nearshore center in Tunisia."),
    "aiventu": ("Verified", "Aiventu is a Microsoft consulting partner delivering Dynamics 365, Power Platform and Microsoft 365 implementations across Africa, Europe and the Middle East."),
    "apeiron tech": ("Verified", "Apeiron Tech is a French-Tunisian software studio delivering custom ERP, mobile apps, e-commerce, AI and Web3 solutions from Paris and Sousse."),
    "audasoft": ("Verified", "Audasoft is a Tunisian software company with 10+ years of experience delivering web, mobile, cloud and AI/LLM solutions using React, Vue.js, Angular and the major public clouds."),
    "avantages soft": ("Verified", "Avantages Soft builds ERP business-management software covering accounting, HR, payment and production management from its base in Ariana, Tunisia."),
    "chifco": ("Verified", "Chifco develops IoT, machine learning, big data and business intelligence solutions, including home automation and fleet management, for clients in Tunisia, France and beyond."),
    "connect network": ("Unverified", None),
    "cynoia": ("Verified", "Cynoia is an all-in-one collaboration platform for African businesses that combines project management, chat, video calls, calendar and files in a single tool."),
    "digibrain agency": ("Verified", "Digibrain Agency is a Tunisian digital agency offering marketing and web & mobile development, with clients such as LG Business Solutions."),
    "diginov": ("Verified", "Diginov is a Sousse-based IT consulting company delivering web and mobile development, UX/UI design and digital transformation services."),
    "farkito": ("Verified", "Farkito is a Tunisian FoodTech startup with a multi-platform app connecting restaurants and hotels with their customers."),
    "firstdown": ("Verified", "Firstdown is a French AI & data consulting firm helping SMEs deploy concrete AI use cases and industrialize their data, from strategy to production."),
    "industryx0": ("Verified", "IndustryX0 builds CIPA, an operational intelligence platform for industrial operations, accelerating Industry 4.0 adoption across Africa and the Mediterranean."),
    "pure technology": ("Verified", "Pure Technology is a Pune-based AI product development and IT staffing company delivering production-grade AI solutions for enterprise and growth-stage teams."),
    "smart touch tunisie": ("Unverified", None),
    "tas tunisia": ("Verified", "TAS delivers hybrid ERP solutions combining Sage, Divalto and Wavesoft with custom modules, serving more than 250 clients in Tunisia and Africa since 2013."),
    "tech expert": ("Verified", "Tech Expert designs and industrializes business-critical digital systems in Tunis, across products, digital factories and AI."),
    "aymax": ("Verified", "Aymax is a digital services firm specializing in SAP consulting, application development and AI integration, present in France, Tunisia, Egypt, Belgium and Switzerland."),
    "smb technologie": ("Verified", "SMB Technologie is a Tunis-based IT company offering analytics, AI, mobile, web and cybersecurity solutions."),
    "discovery": ("Verified", "Discovery Intech has more than 30 years of ERP integration experience with Sage X3, SAP S/4HANA, QAD and Microsoft Dynamics 365, plus AI, Industry 4.0 and MES services across 26 countries."),
    "sfm technologies": ("Verified", "SFM Technologies is a Tunis-based firm delivering strategy consulting and engineering missions in telecommunications for regulators, operators and international donors."),
    "moneycore": ("Verified", "Moneycore is a French consulting firm specializing in electronic banking, payment methods and cybersecurity, running offshore service centers."),
    "devoteam": ("Verified", "Devoteam is an AI-driven technology consulting leader with 11,000+ experts, guiding digital transformation through cloud, data, cybersecurity and AI in partnership with AWS, Google Cloud, Microsoft and ServiceNow."),
    "ey": ("Verified", "EY is one of the Big Four professional services networks, providing assurance, consulting, tax and transaction services in Tunisia and across North Africa."),
    "umantrust": ("Verified", "Umantrust is a Paris-based consulting firm built around cybersecurity, data, cloud and DevOps advisory and implementation."),
    "edonec": ("Verified", "eDonec is a Tunis-based IT services company building web and mobile applications, including a platform that engages parents in children's development at kindergarten and at home."),
    "cbtw": ("Verified", "CBTW delivers software engineering, AI & data platforms, cloud and cybersecurity services with 2,500+ experts across 21 countries, serving banking, telecom, retail and manufacturing."),
    "alphalyr": ("Verified", "Alphalyr is a Paris-based SaaS and data platform that turns retail, e-commerce and supply chain data into AI-powered decisions for brands."),
    "f2k computing": ("Verified", "F2K Computing is a Massy-based IT consultancy offering consulting, infrastructure & architecture, software development and certification services."),
    "synorys": ("Verified", "Synorys is a French engineering and IT consulting firm covering telecommunications networks, multimedia and IT systems for banking, insurance, public services, aeronautics and defence."),
    "yellowsys": ("Verified", "Yellowsys is a Paris-based data consulting firm helping enterprises with BI, data integration, data visualization and its agentic AI platform YellowMind."),
    "acteol": ("Verified", "Acteol builds a hospitality CRM that unifies bookings, EPoS and loyalty data into a single customer view to drive automated campaigns, with a significant development office in Tunisia."),
    "staffing tunisia": ("Verified", "Staffing Tunisia is a Tunisian recruitment and HR agency offering full-process recruitment, interim staffing, RPO and HR outsourcing from Sfax, Tunis and Sousse."),
    "primatec": ("Verified", "Primatec Engineering specializes in the test, validation and development of automotive ECUs, offering test-automation solutions for international manufacturers from Sfax."),
    "pepolls": ("Verified", "Pepolls is a Tunis-based startup building a poll-based social network that gives users control of their personal data."),
    "creado agency": ("Verified", "Creado is a Tunisian creative agency covering communication consulting, web and mobile design, digital marketing and audiovisual production."),
    "tt consulting": ("Verified", "TT Consulting provides professional training, consulting and candidate profiling, with coding and career-reinvention programs."),
    "atlassian": ("Verified", "Atlassian builds collaboration and DevOps products including Jira, Confluence, Trello and Bitbucket, used by millions of teams worldwide."),
    "metam": ("Verified", "Metam is a digital transformation partner for the built environment, combining data & AI, custom development, cloud, RPA and ERP for AEC clients."),
    "omicrone": ("Verified", "Omicrone is a French consulting firm focused on financial services, IT and agile transformation across finance, asset management, risk and IT."),
    "achmitech": ("Verified", "Achmitech is a Moroccan technology company delivering consulting, software development, cloud, cybersecurity and AI, operating in Morocco and France."),
    "trsb": ("Verified", "TRSB is a digital transformation partner with 500+ experts across 13 agencies in France, Portugal and Canada, delivering consulting, engineering and managed services."),
    "ia tech": ("Verified", "IA Tech engineers embedded software and IoT solutions for energy efficiency and telecom/IT integration, serving Tunisia, France, the UAE and Africa."),
    "sofrecom": ("Verified", "Sofrecom Tunisie is an Orange Group subsidiary delivering IT development, services integration and digital transformation, contributing to Tunisia's e-government, e-health and e-banking initiatives."),
    "beprimetech": ("Verified", "BePrimeTech builds BeSmartTravel, a SaaS platform for hotels and travel companies to manage bookings, payments and operations, using Angular, Java and microservices."),
    "biforyou": ("Verified", "BI4YOU delivers business intelligence, AI, data analytics and e-governance platforms for public and private clients across Africa, Europe and the Middle East."),
    "actia engineering": ("Verified", "ACTIA Engineering is the R&D center of the ACTIA Group, with more than 1,000 engineers developing software and electronics for embedded systems in mobility, energy and aerospace."),
    "polytechnique": ("Verified", "The Ecole Polytechnique de Tunisie is a top Tunisian engineering school affiliated with the University of Carthage, offering a multidisciplinary engineering curriculum and multiple research laboratories."),
    "kio technologie": ("Verified", "KIO Technologie is an IT services company with offices in Paris and Sousse focused on web and mobile development, CRM, SEO and graphic design."),
    "it explorer": ("Verified", "IT-Explorer is a French portage salarial company that manages payroll, benefits and administration for independent IT consultants."),
    "serma international": ("Verified", "SERMA International is the nearshore subsidiary of the French SERMA Group, providing software development, FPGA/ASIC design and testing, and obsolescence management."),
    "talan": ("Verified", "Talan is an international consulting and technology group with 4,600+ employees in 35 countries, accelerating digital transformation through data, AI and blockchain."),
    "expensya": ("Verified", "Expensya is an intelligent expense-management SaaS used by more than 5,000 companies, now part of Medius, with a major engineering hub in Tunisia."),
    "gfi tunisie": ("Verified", "GFI Tunisie, formerly Cynapsys, is a digital services company with more than 240 employees focused on IoT, cybersecurity, e-commerce and interoperability."),
    "teamsyst": ("Verified", "TEAMSYST is a Tunisian digital services company offering web and mobile development, big data, IT recruitment, ERP and QA services."),
    "al bawsala": ("Verified", "Al Bawsala is a Tunisian NGO promoting democratic governance, transparency and citizen participation through open data and legislative monitoring."),
    "vneuron": ("Verified", "Vneuron provides AML and counter-terrorist financing compliance software used by more than 250 financial institutions in 45+ countries."),
    "peritis": ("Verified", "Peritis is a French data & AI services company and a top Elastic partner, focused on the Elastic Stack for search, observability and security."),
    "cpl jobs": ("Verified", "CPL Jobs Tunisia is part of Cpl Resources plc, a European recruitment and HR outsourcing leader founded in Ireland in 1989."),
    "epiconsulting": ("Verified", "Epiconsulting is a Paris-based IT engineering company covering systems & network administration, cybersecurity, cloud, databases and full-stack development."),
    "drakkapp": ("Verified", "Drakkapp designs custom AI solutions and process automation for banks and financial institutions, with a focus on regulatory compliance."),
    "sofali": ("Verified", "Sofali is a French consulting and integration company specialized in business intelligence, data analytics and decision-support solutions, with offices in Paris and Casablanca."),
    "proxiad": ("Verified", "Proxiad is a French IT services and consulting firm delivering software engineering and business intelligence, with more than 440 people across Europe."),
    "openbee": ("Verified", "Open Bee is a French software company whose document-management and e-invoicing platform is used by 250,000+ users and holds ISO 27001 certification."),
    "perfectsoft": ("Verified", "PerfectSoft is a Sfax-based software company specializing in real-time web and mobile development with a strong open-source footprint."),
    "ai2 education": ("Verified", "AI2 Education is a Paris-based higher-education institution offering Bachelor and Master programs in AI and Data Science, plus an AI2 Lab linking students with companies."),
    "infotel": ("Verified", "Infotel is an international French technology group delivering software, cloud, data and cybersecurity services primarily for banking, insurance and industry."),
    "we are sander": ("Verified", "Sander is a Brussels-based recruitment and HR-tech startup recruiting in Finance, IT, HR and Legal."),
    "syslearn": ("Verified", "Syslearn is a French digital services company providing mobile/web development, AI, data science, DevOps and cybersecurity services across banking, energy, automotive and more."),
    "optimal decision": ("Verified", "Optimal Decision is a Tunisian business intelligence consulting firm and the Tableau partner for the Maghreb, delivering decision-support dashboards."),
    "winsearch": ("Verified", "Winsearch is a French recruitment firm specializing in engineers and executives for industry, technology and healthcare."),
    "spark it": ("Verified", "Spark-it is a French digital services company in web, CRM, ERP, BI and Big Data, serving France, the UK and Benelux with delivery centers in France and Tunisia."),
    "infinity management": ("Verified", "Infinity Management Groupe accompanies companies in organizational, digital and human transformation across Tunisia, France, Senegal and Spain."),
    "upsourcing": ("Verified", "Upsourcing is a Paris-based headhunting firm specializing in IT, tech and digital roles, from developers to CTO, data and DevOps leaders."),
    "technica engineering": ("Verified", "Technica Engineering is a German automotive engineering company and pioneer of Automotive Ethernet, designing E/E systems, hardware and software for connected vehicles."),
    "inqure health": ("Verified", "InQure Health develops branded Ayurvedic-inspired health and OTC products, operating through affiliates across India, APAC and the MENA region."),
    "streamlink": ("Verified", "Streamlink is a certified SAP partner providing BI, Big Data and digital transformation services from Levallois-Perret and Tunis."),
    "smartpoint": ("Verified", "Smartpoint is a Paris-based data-focused digital services company providing data engineering, BI, data science and QA/test automation."),
    "waialys group": ("Verified", "WAIALYS Group is an IT consulting firm active in France and Tunisia delivering web/mobile development, DevOps, EdTech and Industry 4.0 expertise."),
    "autobiz": ("Verified", "Autobiz is the European leader in used-car valuation and trade-in solutions, using big data and AI across more than 20 countries."),
    "newaccess": ("Verified", "Newaccess is a Swiss software company, now part of FNZ Group, providing front-to-back digital banking and wealth management solutions."),
    "advisus ndc": ("Verified", "Advisus NDC is a Tunisian HR consulting and recruitment firm offering recruitment, HR advisory and training."),
    "be softilys": ("Verified", "Be Softilys is a Tunisian software publisher focused on digital transformation, data governance, GDPR compliance and sensitive-data management, using Java and Angular."),
    "binitns": ("Verified", "Binitns, formerly MISC, is a Tunisian IT and BPO consulting firm advising European clients on cloud, data management, security and infrastructure."),
    "lansrod": ("Verified", "Lansrod is a French Big Data and data science consultancy, part of the Audensiel group, delivering engineering projects for large enterprises."),
    "poulina group": ("Verified", "Poulina Group is a Tunisian conglomerate founded in 1967, active in agrifood, building materials, packaging and retail through roughly 100 subsidiaries."),
    "tuniteam": ("Verified", "Tuniteam is a Sfax-based company building iOS, Android and web solutions for European clients, plus QA services."),
    "finlogic": ("Verified", "Finlogic is a FINTRAC-registered money services business providing cross-border payments and FX solutions with same-day delivery."),
    "symolia": ("Verified", "Symolia Group is an independent French IT consulting group active in France, Morocco and Tunisia, specializing in payment systems, digital/cloud and finance solutions."),
    "tritux": ("Verified", "Tritux is a Tunisian-French software publisher and IT services company delivering software engineering and outsourcing for telecom, banking and government clients."),
    "inted group": ("Verified", "Inted Group is a Paris-based group of universities and schools focused on student mobility and employability through work-study and initial training programs."),
    "cweave": ("Verified", "Cweave, also known as ComWeave, modernizes legacy APIs with pre-built connectors, delivering real-time data to web and mobile applications."),
    "dataklu": ("Unverified", None),
    "sync-s": ("Verified", "Sync Solutions is a Swiss Romande IT partner providing Microsoft 365, email and Teams hosting, IP telephony, connectivity and cybersecurity services."),
    "sintegra consulting": ("Verified", "Sintegra Consulting is an IT recruitment platform helping African engineers land permanent roles with French digital services companies, with more than 2,000 recruitments."),
    "ozeol": ("Verified", "Ozeol is a global B2B company helping businesses clear surplus and end-of-line inventory, with a team of 700+ across 8 international offices."),
    "dso services": ("Verified", "DSO Services is a Sfax-based engineering and IT services company of the IMBA group, covering software engineering, Big Data and IT infrastructure."),
    "kytl": ("Verified", "Kytl is a French cybersecurity company offering managed SOC services, security audits, penetration testing and training."),
    "symdrik": ("Verified", "Symdrik is a Paris-based digital and mobile expertise center providing open-source web and mobile development, with references including Accor Hotels and Macif."),
    "africashore": ("Verified", "Africashore connects IT freelancers based in Africa with companies across Europe, the US, Canada and the UAE for remote assignments."),
    "madar consulting": ("Verified", "Madar Consulting builds big data solutions on its proprietary MADAR platform, using Hadoop, Spark and Kafka, with offices in Tunisia, France and the USA."),
    "koders": ("Verified", "Koders is a Grenoble-based IT consulting firm specializing in development projects and providing technical resources."),
    "st2i": ("Verified", "ST2I is a Tunisian IT integrator and subsidiary of the STUDI group, specializing in information systems, GIS and geomatics since 1992."),
    "coachess": ("Unverified", None),
    "xtech": ("Verified", "Xtech is a Tunis-based custom software company developing web and mobile applications with agile methodologies for clients including HomeTouch and Pearson."),
    "sawayou": ("Unverified", None),
    "xperpool": ("Unverified", None),
    "hexagone digitale": ("Verified", "Hexagone Digitale is a digital transformation consulting firm with offices in Paris, Lyon, Casablanca and Tunis, covering IT sourcing, agile consulting and architecture."),
    "next mondays": ("Verified", "Next Mondays is a Marseille-based platform connecting tech freelancers with companies in France across IT, mobile, data, QA and embedded systems."),
    "akka": ("Verified", "AKKA, now known as Akkodis and part of the Adecco Group, is an engineering and technology consulting company focused on R&D for automotive and aerospace."),
    "eninsy": ("Verified", "Eninsy is a global IT provider of Terminal Management Systems for oil and gas, with projects deployed on more than 100 terminals across 49 countries."),
    "meydan hotels": ("Verified", "Meydan Hotels is a luxury Dubai hotel next to Meydan Racecourse, managed by Kerzner International, offering 284 rooms and suites with racetrack views."),
    "adecco": ("Verified", "Adecco is one of the world's largest HR services and staffing companies, providing temporary staffing, permanent placement and talent development in more than 60 countries."),
    "medihrc": ("Unverified", None),
    "tectra": ("Verified", "Tectra is a leading Moroccan temporary staffing and recruitment company with more than 30 agencies and 45,000+ temporary employees."),
    "abc recruitment": ("Verified", "ABC Recruitment is a UAE recruitment company established in 1978, offering executive search, manpower outsourcing and HR consulting across oil & gas, banking, construction and healthcare."),
    "baytik": ("Verified", "Baytik is a Dubai-based real estate and travel company offering property sales, vacation rentals and property management in Business Bay."),
    "spec energy": ("Verified", "SPEC Energy is a global EPC engineering company providing procurement, fabrication and construction for new energy, refinery and petrochemical projects, with major operations in Dubai."),
    "millenium hotels": ("Verified", "Millennium Hotels and Resorts is a global hotel brand operating more than 145 hotels across 80 locations worldwide."),
    "al ansari": ("Verified", "Al Ansari Exchange is the UAE's leading exchange company with more than 280 branches, offering foreign exchange, money transfers, prepaid cards and corporate payments."),
    "al ghurair": ("Verified", "Al Ghurair is one of the Middle East's largest diversified family groups, active in foods, real estate and mobility with over 28,000 employees."),
    "arabian cement company": ("Verified", "Arabian Cement Company is one of Egypt's leading cement producers, with a fully integrated plant and around 5 million tonnes of annual production capacity."),
    "inaya": ("Verified", "Inaya, a member of the Belhasa Group, is a UAE facilities management company providing maintenance, cleaning, MEP and soft services across Dubai and Abu Dhabi."),
    "infini concepts": ("Verified", "Infini Concepts is a Dubai-based hospitality group that creates, develops and operates restaurant and nightlife concepts for the global F&B industry."),
    "jannah hotels": ("Verified", "Jannah Hotels & Resorts is a UAE luxury Halal hotel group operating hotels and apartments in Abu Dhabi, Dubai and Ras Al Khaimah."),
    "nabooda auto": ("Verified", "Al Nabooda Automobiles is the exclusive Audi, Porsche and Volkswagen distributor in Dubai and the Northern Emirates since 1976."),
    "springfield re": ("Verified", "Springfield Properties is a RERA-licensed Dubai real estate agency active in sales, leasing, off-plan investment and property management."),
    "terra solis dubai": ("Verified", "Terra Solis Dubai, Tomorrowland's luxury desert resort in the Arabian dunes, is known for its music events, poolside parties and premium accommodation."),
    "vivandi": ("Verified", "Vivandi is a Dubai-based distributor and retailer of premium hair care, beauty and wellness products, with exclusive partnerships with international brands."),
    "woodlem dubai": ("Verified", "Woodlem Park School Dubai is a KHDA-approved CBSE-curriculum Indian school in Al Qusais offering education from Pre-KG to Grade 12."),
    "emiratalent": ("Verified", "EmiraTalent is a UAE recruitment and staffing consultancy specializing in Emiratisation and Emirati talent hiring."),
    "meritshot": ("Verified", "Meritshot is a Noida-based career-transformation edtech platform offering job-linked programs in data science, cybersecurity, full-stack development and more."),
    "alwadifa consulting": ("Unverified", None),
    "best profil": ("Verified", "Best Profil is a Moroccan recruitment and temporary staffing agency established in 1996, with a network of agencies across the country."),
    "emploi.ma": ("Verified", "Emploi.ma is a Moroccan online job board connecting job seekers with employers, part of a group operating in 37 African countries."),
    "jobplus": ("Verified", "JobPlus is a Casablanca-based recruitment and interim staffing firm founded in 2015."),
    "lci rh": ("Unverified", None),
    "rekrute": ("Verified", "ReKrute is Morocco's leading online recruitment portal, providing e-recruitment, CV databases and HR technology across Morocco and French-speaking Africa."),
    "rh value": ("Verified", "RH Value is a Casablanca-based HR consulting firm offering recruitment, training, payroll and HR process design, including SIRH support."),
    "career hub international": ("Verified", "Career Hub International is an Abu Dhabi-based HR consultancy and staffing firm known for sourcing teachers, engineers, nurses and executives."),
    "prime group": ("Verified", "Prime Group is a Dubai-headquartered quality, compliance and growth solutions provider active in testing, certification, inspection and auditing."),
    "michael page": ("Verified", "Michael Page is a global recruitment consultancy and part of PageGroup, operating in the Middle East for more than 20 years."),
    "coral boutique villa": ("Verified", "Coral Boutique Villa is a 5-star boutique hotel in Al Barsha, Dubai, with 30 fully furnished 4-bedroom villas, a pool and conference facilities."),
    "melf": ("Unverified", None),
    "kingston stanley": ("Verified", "Kingston Stanley is a Dubai-based recruitment agency founded in 2011, specializing in digital, marketing, tech and corporate services hiring."),
    "accor": ("Verified", "Accor is a world-leading hospitality group with more than 5,800 hotels and 45+ brands, including Sofitel and Novotel, and the ALL loyalty program."),
    "jac": ("Verified", "JAC Motors is a Chinese automotive manufacturer distributed in the UAE by Al Habtoor Motors, offering passenger vehicles, SUVs, pickups and electric vehicles."),
    "eyewa": ("Verified", "Eyewa is the Middle East's leading online eyewear destination, selling glasses and contact lenses online and through more than 260 retail stores."),
    "speedaf": ("Verified", "Speedaf is a cross-border logistics provider offering door-to-door shipping, fulfillment and real-time tracking across emerging markets."),
    "citruss": ("Unverified", None),
    "habtoor hospitality": ("Verified", "Habtoor Hospitality is the Middle East's longest established hospitality group, operating hotels and resorts, dining venues and lifestyle destinations in the UAE."),
    "gates hospitality": ("Verified", "Gates Hospitality is an award-winning Dubai hospitality company that creates restaurants and lifestyle concepts, growing from a single venue to several across the UAE."),
    "psi": ("Verified", "Property Shop Investment (PSI) is one of the UAE's leading real estate brokerage firms, based in Abu Dhabi and serving developers such as Aldar and Emaar."),
    "able": ("Verified", "ABLE is a Dubai-based pediatric therapy center providing Applied Behaviour Analysis, occupational therapy and speech-language services for children with special needs."),
    "al khaleej palace deira": ("Unverified", None),
    "al imousa": ("Verified", "Ali Mousa & Sons is a UAE conglomerate founded in 1978, operating across contracting, MEP, joinery, metals, prefab and real estate development."),
    "avenue hotel dubai": ("Verified", "Avenue Hotel Dubai is a 4-star boutique business hotel in Deira with 133 rooms and suites, restaurants and a rooftop pool."),
    "erc": ("Verified", "Emirates Reem Investments (ERC) is a Dubai FMCG and beverages company producing water and consumer goods under brands such as Jeema."),
    "hi al barsha": ("Unverified", None),
    "it road": ("Verified", "IT Road Consulting is a Casablanca-headquartered IT consulting group with offices in Paris and Tunis, covering IT audit, architecture, cybersecurity and AI."),
    "prestige luxury": ("Verified", "Prestige Luxury is a Dubai real estate brokerage established in 2007, specializing in premium residential and commercial property."),
    "slhr uae": ("Verified", "SLHR is an Ajman-based HR consultancy offering talent acquisition, visa processing, payroll and HR support across the UAE."),
    "tafaseel": ("Verified", "Tafaseel is the UAE's largest home-grown BPO, delivering customer support, technical assistance, digital transformation and HR outsourcing."),
    "vplace gulf jobs": ("Unverified", None),
    "carino": ("Verified", "Carino is a UAE trading company in building and construction materials that now trades as Gratis Building & Construction Materials."),
    "charterhouse": ("Verified", "Charterhouse is a Dubai executive search and recruitment firm, part of the global Charterhouse Partnership network."),
    "delta oil gas jobs": ("Verified", "Delta International Petroleum Services is an Abu Dhabi oil, gas and petrochemical manpower provider, serving ADNOC operating companies since 1992."),
    "neurotech egypt": ("Verified", "NeuroTech is an Egyptian educational platform offering practical Arabic-language AI and data science courses, with accredited certificates and job-placement support."),
    "ratls contracting": ("Verified", "RATLS Contracting is a UAE main contractor offering design-build for industrial, commercial, residential and hospitality projects, serving clients such as Flydubai and Nakheel."),
    "accelhr": ("Verified", "Accel HR is an HR outsourcing provider offering HRIS, payroll and benefits administration, partnering with Ultimate Software and Lawson."),
    "brite consult": ("Verified", "Brite Consult is an HR consultancy offering recruitment, advisory, psychometric assessments and learning & development for MENA clients."),
    "inertia egypt": ("Verified", "Inertia is an Egyptian real estate developer with residential and commercial projects across Cairo, the North Coast and the Red Sea."),
    "latinum hr": ("Verified", "Latinum HR is a global human capital and recruitment partner with bases in Pune and Dubai, recruiting for employers such as Amazon, Infosys and Vodafone."),
    "nai school": ("Verified", "North American International School in Mizhar, Dubai, is a K-12 international school delivering a US-American curriculum."),
    "hr source": ("Verified", "HR Source Consulting is a MENA-region HR solutions consultancy serving the IT, media, sales & marketing and exhibitions industries."),
    "pact employment": ("Verified", "PACT Employment Services is a UAE recruitment agency offering contract staffing, HR outsourcing and payroll solutions."),
    "ajmal": ("Verified", "Ajmal Perfumes is one of the UAE's best-known fragrance houses, producing oriental and oud perfumes with a global retail presence."),
    "babylon difc": ("Verified", "Babylon DIFC is an upscale restaurant in Dubai's financial district, with its presence centered on its Instagram page."),
    "ns search": ("Verified", "NS Search is a Dubai headhunting boutique that places talent in marketing communications and across industries in the MENA region and Europe."),
    "ineos": ("Verified", "Ineos is a Moroccan IT integrator and consultancy specializing in network, cloud and cybersecurity, supporting digital transformation for companies in Morocco and West Africa."),
    "bacme": ("Unverified", None),
    "aksal": ("Verified", "Groupe AKSAL is a leading Moroccan retail and luxury group representing international brands such as Zara and Gucci and developing malls such as Morocco Mall."),
    "anglo arabian healthcare": ("Verified", "Anglo Arabian Healthcare is a UAE integrated healthcare provider operating hospitals, medical centres and pharmacies under brands such as HealthBay."),
    "crit maroc": ("Verified", "Crit Maroc is the Moroccan subsidiary of the CRIT Group, a global temporary work and recruitment leader active since 2003 in 12 Moroccan cities."),
    "global jobs": ("Verified", "Global Jobs is a Casablanca-based HR consulting and recruitment firm offering recruitment, training and international job placement."),
    "hr skills": ("Verified", "HR Skills Maroc is a Casablanca-based recruitment and HR training firm delivering talent sourcing and skills development programs."),
    "hsk hospitality": ("Verified", "HSK Hospitality is a Dubai-based hospitality group operating multi-cuisine casual dining restaurants in the UAE."),
    "marocadres": ("Verified", "Marocadres is a Casablanca online recruitment platform connecting job seekers with employers, including Moroccan professionals abroad."),
    "taleem": ("Verified", "Taaleem is a UAE education group operating early childhood, primary and secondary schools in Dubai with British, American and IB curricula."),
    "candidzone": ("Verified", "Candidzone is a Qatar-based HR and manpower consulting firm founded in 2012, delivering recruitment, staffing, EOR and payroll across the GCC."),
    "rh pro plus": ("Verified", "RH Pro Plus is a Tunisia-based HR consulting firm specializing in recruitment, training and skills assessments, with presence in francophone Africa."),
    "movenpick": ("Verified", "Movenpick Hotels & Resorts is a Swiss-founded luxury hotel chain now owned by Accor, operating more than 80 properties across the Middle East, Africa, Europe and Asia."),
    "armada group": ("Verified", "Armada Group is a Kuwait-headquartered fashion retail conglomerate operating more than 19 international and in-house brands across 250+ stores."),
    "derby group": ("Verified", "Derby Group is a Dubai-based business group offering BPO and staffing across banking and insurance, and is a trusted recruitment partner of top UAE banks."),
    "anapec": ("Verified", "ANAPEC is Morocco's national employment agency, created in 2000, which intermediates between job seekers and employers through a nationwide network."),
    "ardt": ("Verified", "AR Design & Technology (ARDT) is a Dubai-area digital services firm offering software development, web and app development, and digital marketing."),
    "it people gulf": ("Verified", "IT People is a Dubai-based IT consulting and staffing firm providing placement, managed services and build-operate-transfer across the GCC."),
    "casa mia uae": ("Verified", "Casamia is a Dubai luxury building-materials showroom curating high-end tiles, kitchens, furniture and lighting from premium European brands."),
    "eim": ("Unverified", None),
    "opuslab edtech": ("Verified", "Opus Lab is a state-recognized Tunisian digital skills school offering certified courses in web development, data science, design and programming."),
}

# ---------------------------------------------------------------------------
# Company typing.
#
# Recruiters / staffing agencies / job boards are marked ONLY where the
# existing verified fact in RESEARCH explicitly says so (recruitment, staffing,
# placement, headhunting, hiring, job board, talent acquisition...). Nothing is
# inferred from a company name alone.
# ---------------------------------------------------------------------------

RECRUITERS = frozenset({
    "abc recruitment", "advisus ndc", "adecco", "adecco tunisie", "africashore",
    "anapec", "best profil", "brite consult", "candidzone", "career hub international",
    "charterhouse", "cpl jobs", "crit maroc", "delta oil gas jobs", "deltalink",
    "derby group", "emiratalent", "global jobs", "hr skills", "it people gulf",
    "jefferson frank", "jobplus", "kingston stanley", "klymber", "latinum hr",
    "michael page", "next mondays", "noverka conseil", "ns search", "pact employment",
    "rh pro plus", "rh value", "sintegra consulting", "slhr uae", "staffing tunisia",
    "tectra", "upsourcing", "we are sander", "winsearch",
})

JOB_BOARDS = frozenset({
    "emploi.ma", "marocadres", "rekrute",
})

# Direct-employer categories (everything else falls back to "generic").
CATEGORY = {
    # saas / product platforms
    "acteol": "saas", "alphalyr": "saas", "autobiz": "saas", "beprimetech": "saas",
    "cynoia": "saas", "expensya": "saas", "farkito": "saas", "industryx0": "saas",
    "openbee": "saas", "pepolls": "saas",
    # e-commerce
    "dracoss": "ecommerce", "eyewa": "ecommerce",
    # software companies / publishers
    "apeiron tech": "software", "atlassian": "software", "audasoft": "software",
    "avantages soft": "software", "be softilys": "software", "cweave": "software",
    "edonec": "software", "eninsy": "software", "newaccess": "software",
    "perfectsoft": "software", "streamwide": "software", "tas tunisia": "software",
    "vneuron": "software",
    # real estate
    "baytik": "realestate", "inertia egypt": "realestate", "prestige luxury": "realestate",
    "psi": "realestate", "springfield re": "realestate",
    # hospitality (hotels / restaurants / hospitality groups)
    "accor": "hospitality", "avenue hotel dubai": "hospitality", "babylon difc": "hospitality",
    "coral boutique villa": "hospitality", "gates hospitality": "hospitality",
    "habtoor hospitality": "hospitality", "hsk hospitality": "hospitality",
    "infini concepts": "hospitality", "jannah hotels": "hospitality",
    "meydan hotels": "hospitality", "millenium hotels": "hospitality",
    "movenpick": "hospitality", "terra solis dubai": "hospitality",
    # education / training
    "ai2 education": "education", "inted group": "education", "meritshot": "education",
    "nai school": "education", "neurotech egypt": "education", "opuslab edtech": "education",
    "polytechnique": "education", "taleem": "education", "woodlem dubai": "education",
    # engineering / embedded / industrial R&D
    "actia engineering": "engineering", "ia tech": "engineering", "primatec": "engineering",
    "spec energy": "engineering", "technica engineering": "engineering",
    # telecom operators
    "ooredoo": "telecom",
    # everything else that is a consulting / IT services firm
    "achmitech": "consulting", "acti security": "generic", "addinn": "consulting",
    "adactim": "consulting", "aiventu": "consulting", "akka": "consulting",
    "al bawsala": "generic", "al ansari": "generic", "al ghurair": "generic",
    "al imousa": "generic", "anglo arabian healthcare": "generic",
    "arabian cement company": "generic", "ardt": "consulting",
    "armada group": "generic", "able": "generic", "accelhr": "generic",
    "ajmal": "generic", "aksal": "generic", "aymax": "consulting",
    "biforyou": "consulting", "binitns": "consulting", "casa mia uae": "generic",
    "carino": "generic", "cbtw": "consulting", "chifco": "consulting",
    "consultim it": "consulting", "consulting datamed": "consulting",
    "creado agency": "consulting", "datasense group": "consulting",
    "devoteam": "consulting", "digibrain agency": "consulting", "diginov": "consulting",
    "discovery": "consulting", "drakkapp": "consulting", "dso services": "consulting",
    "erc": "generic", "epiconsulting": "consulting", "ey": "consulting",
    "f2k computing": "consulting", "finlogic": "generic", "firstdown": "consulting",
    "gfi tunisie": "consulting", "heptasys": "consulting", "hexagone digitale": "consulting",
    "hr source": "generic", "inaya": "generic", "ineos": "consulting",
    "infinity management": "consulting", "infotel": "consulting",
    "inqure health": "generic", "it explorer": "consulting", "it road": "consulting",
    "jac": "generic", "keythinkers": "consulting", "kio technologie": "consulting",
    "koders": "consulting", "kytl": "consulting", "lansrod": "consulting",
    "madar consulting": "consulting", "metam": "consulting", "moneycore": "consulting",
    "nabooda auto": "generic", "numeryx": "consulting", "omicrone": "consulting",
    "ozeol": "generic", "peritis": "consulting", "poulina group": "generic",
    "prime group": "generic", "proxiad": "consulting", "proxwel": "consulting",
    "pure technology": "consulting", "ratls contracting": "generic",
    "riskover": "consulting", "serma international": "consulting",
    "sfm technologies": "consulting", "smb technologie": "consulting",
    "smartpoint": "consulting", "sofrecom": "consulting",
    "sofali": "consulting", "solinum": "consulting", "spark it": "consulting",
    "speedaf": "generic", "st2i": "consulting", "streamlink": "consulting",
    "sync-s": "consulting", "symdrik": "consulting", "symolia": "consulting",
    "synorys": "consulting", "syslearn": "consulting", "tafaseel": "generic",
    "talan": "consulting", "tech expert": "consulting", "teamsyst": "consulting",
    "trsb": "consulting", "tt consulting": "consulting", "tritux": "consulting",
    "tuniteam": "consulting", "umantrust": "consulting", "value": "consulting",
    "vivandi": "generic", "waialys group": "consulting", "xtech": "consulting",
    "yellowsys": "consulting",
}

# ---------------------------------------------------------------------------
# Sentence components. Every connector only references the candidate's real,
# CV-supported experience (Laravel/React/Node.js, MySQL/PostgreSQL, SaaS,
# e-commerce, payment integrations, dashboards, real-estate platform,
# restaurant/supplier platforms, e-learning, Docker/Linux/CI-CD). Nothing is
# fabricated.
# ---------------------------------------------------------------------------

DIRECT_OPENING = ("I am writing to express my interest in full-stack software engineering "
                  "opportunities at {company}.")
RECRUITER_OPENING = ("I am reaching out to see whether you are currently handling any "
                     "full-stack software engineering opportunities that could match my "
                     "background.")
JOBBOARD_OPENING = ("I am reaching out to see whether your platform is currently listing "
                    "any full-stack software engineering roles that could match my "
                    "background.")

DIRECT_VALUE = "I bring three-plus years of full-stack web development to that kind of work."
RECRUITER_VALUE = "I would be glad to be considered for any full-stack role you are currently recruiting for."
JOBBOARD_VALUE = "I bring three-plus years of full-stack development with Laravel, React, Node.js and PostgreSQL/MySQL."

CTA = ("I would be happy to share my CV and discuss whether my background could fit any "
       "current or upcoming opportunities.")

CONNECTORS = {
    "saas": ("That caught my attention because my recent work has centered on Laravel-based "
             "SaaS products - multi-tenant dashboards, marketplaces and third-party "
             "integrations - where maintainable architecture matters as much as the "
             "features."),
    "ecommerce": ("That caught my attention because I have built e-commerce experiences "
                  "first-hand - online stores, product catalogs and Stripe payment "
                  "integrations - where the journey from checkout to dashboard needs to "
                  "be seamless."),
    "software": ("That caught my attention because my own work focuses on building and "
                 "maintaining web applications where clean architecture, security and "
                 "long-term maintainability come first."),
    "software_erp": ("That caught my attention because my own work centers on "
                     "business-management applications - restaurant and supplier "
                     "platforms, real-estate systems - where reliable workflows and "
                     "maintainable code matter most."),
    "consulting": ("That caught my attention because I work across that same breadth - "
                   "Laravel and React for web applications, Node.js for services, MySQL "
                   "and PostgreSQL for data - and I enjoy applying that to client "
                   "projects."),
    "consulting_data": ("That caught my attention because my experience is in building "
                        "data-driven dashboards and applications - reporting views, "
                        "analytics back-ends and the APIs that feed them - which fits "
                        "well with data-focused delivery."),
    "consulting_cloud": ("That caught my attention because I work across the full stack "
                         "and use the surrounding tooling - Docker, Linux and CI/CD "
                         "pipelines - so I fit naturally into cloud- and DevOps-oriented "
                         "teams."),
    "generic": ("That caught my attention because my experience is building the custom "
                "web applications businesses rely on - from customer-facing platforms to "
                "internal dashboards and integrations - and I would enjoy applying that "
                "to your context."),
    "hospitality": ("That caught my attention because I recently built a "
                    "restaurant-management platform and a supplier marketplace, so I have "
                    "direct experience with the software the hospitality sector depends "
                    "on day to day."),
    "education": ("That caught my attention because I have worked on e-learning platforms "
                  "before, both building and improving them, and I know how much reliable "
                  "software matters to learners and institutions."),
    "engineering": ("That caught my attention because even in engineering-led companies, "
                    "software increasingly shapes the products and operations that set "
                    "them apart, and I enjoy bringing a full-stack perspective to those "
                    "challenges."),
    "realestate": ("That caught my attention because I recently built a real-estate "
                   "platform covering property listings and buying, renting and selling "
                   "workflows, so that space genuinely feels familiar to me."),
    "telecom": ("That caught my attention because a telecom operator's customer experience "
                "now depends heavily on digital self-service, and building those "
                "customer-facing applications and dashboards is exactly the kind of work "
                "I do."),
    "recruiter": ("That caught my attention because I am a full-stack software engineer "
                  "specialising in Laravel, React, Node.js and PostgreSQL/MySQL, actively "
                  "looking for my next role."),
    "jobboard": ("That caught my attention because I am a full-stack software engineer "
                 "specialising in Laravel, React, Node.js and PostgreSQL/MySQL, and a "
                 "portal like yours is a natural first step."),
}

ERP_WORDS = ("erp", "sage", "sap", "dynamics")
DATA_WORDS = ("data", " bi", "analytics", "reporting", "intelligence", "machine learning",
              "hadoop", "spark", "kafka", "big data")
CLOUD_WORDS = ("cloud", "devops", "kubernetes", "infrastructure", "cybersecurity",
               "security", "azure", "aws", "docker")


def classify_company(company):
    """Return the category used to pick the email template for a company."""
    key = (company or "").strip().lower()
    if key in RECRUITERS:
        return "recruiter"
    if key in JOB_BOARDS:
        return "jobboard"
    return CATEGORY.get(key, "generic")


def pick_connector(category, hook):
    """Pick the connector sentence for a company type.

    Within the consulting / software categories the connector is refined by
    keywords present in the verified hook, so the connection always reflects
    the specific activity the company was verified to be involved in.
    """
    if category in ("recruiter", "jobboard"):
        return CONNECTORS[category]
    if category == "software":
        text = (hook or "").lower()
        if any(word in text for word in ERP_WORDS):
            return CONNECTORS["software_erp"]
        return CONNECTORS["software"]
    if category == "consulting":
        text = (hook or "").lower()
        if any(word in text for word in DATA_WORDS):
            return CONNECTORS["consulting_data"]
        if any(word in text for word in CLOUD_WORDS):
            return CONNECTORS["consulting_cloud"]
        return CONNECTORS["consulting"]
    return CONNECTORS.get(category, CONNECTORS["generic"])


FALLBACK_BODY = """\
Dear Hiring Team at {company},

I am reaching out to express my interest in potential Full-Stack Software Engineering opportunities at {company}.

I am a Software Engineer with professional experience in Laravel, PHP, JavaScript, React, Node.js, and database-driven web applications.

Please find my CV attached for your consideration. I would be happy to discuss how my experience could contribute to your team.

Best regards,

Ahmed Ben Bettaieb
"""


def load_companies():
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        return [row for row in csv.DictReader(f) if (row.get("Email") or "").strip()]


def normalize_hook(hook):
    hook = (hook or "").strip()
    if hook and not hook.endswith("."):
        hook += "."
    return hook


def build_verified_body(company, hook, category):
    hook = normalize_hook(hook)
    connector = pick_connector(category, hook)

    if category == "recruiter":
        opening = RECRUITER_OPENING
        value = RECRUITER_VALUE
    elif category == "jobboard":
        opening = JOBBOARD_OPENING
        value = JOBBOARD_VALUE
    else:
        opening = DIRECT_OPENING.format(company=company)
        value = DIRECT_VALUE

    return (
        f"Dear Hiring Team at {company},\n\n"
        f"{opening}\n\n"
        f"{hook} {connector}\n\n"
        f"{value} {CTA}\n\n"
        f"Best regards,\n\n"
        f"Ahmed Ben Bettaieb"
    )


def build_row(company, email, status, hook):
    if status == "Unverified" or not hook:
        body = FALLBACK_BODY.format(company=company or "your company")
        research = "Research unavailable"
        category = None
    else:
        company_name = company or "the company"
        category = classify_company(company)
        body = build_verified_body(company_name, hook, category)
        research = hook
    return {
        "Company": company,
        "Email": email,
        "Website": "",
        "ResearchSummary": research,
        "Subject": SUBJECT,
        "Body": body,
        "ResearchStatus": status,
        "_category": category,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate personalized_emails.csv")
    parser.add_argument("--validate-only", action="store_true",
                        help="Validate the existing personalized_emails.csv without regenerating it.")
    parser.add_argument("--no-validate", action="store_true",
                        help="Generate without running the validation pass.")
    args = parser.parse_args()

    if args.validate_only:
        rows = load_personalized_rows()
        if not rows:
            return
        report = run_validation(rows)
        print_validation_report(report)
        return

    companies = load_companies()
    rows = []
    for row in companies:
        company = (row.get("Company") or "").strip()
        email = (row.get("Email") or "").strip()
        status, hook = RESEARCH.get(company.strip().lower(), ("Unverified", None))
        built = build_row(company, email, status, hook)
        rows.append(built)

    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow({field: r[field] for field in FIELDS})

    verified = sum(1 for r in rows if r["ResearchStatus"] == "Verified")
    unverified = sum(1 for r in rows if r["ResearchStatus"] != "Verified")
    print(f"Wrote {len(rows)} rows to {OUT_PATH}")
    print(f"Verified: {verified} | Unverified (generic email): {unverified}")
    print()

    if not args.no_validate:
        report = run_validation(rows)
        print_validation_report(report)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# Phrases that would reveal the email was machine-generated.
AI_SELF_GENERATION_PHRASES = [
    "ai-generated", "generated by ai", "generated using", "generated with",
    "written with ai", "written by ai", "using ai", "by an ai", "an ai model",
    "ai to write", "artificial intelligence", "automated email", "automated message",
    "email was automated", "machine-generated", "lm model",
]

# Phrases that look like fabricated experience/role claims.
# Uses word boundary-aware matching so "architecture" doesn't false-match "architect".
FABRICATED_CLAIM_RE = re.compile(
    r"(?:i have worked at|i led |i lead |team lead|lead developer|lead engineer"
    r"|worked directly with|my client|years of experience at|principal"
    r"|senior-level|i built this company|i founded|i am a team lead|managed a team"
    r"|i am an architect|as an architect)", re.IGNORECASE
)

# External-contact / payment solicitation language that must never appear.
FORBIDDEN_COMMERCIAL_PHRASES = [
    "call me at", "my phone", "phone number", "whatsapp", "bank account",
    "bank transfer", "pay me", "payment from you", "send money", "wire transfer",
    "deposit payment", "click here", "sign up", "apply now", "invite you to",
    "including my contact number", "my mobile",
]

HARD_WORD_MIN = 60
HARD_WORD_MAX = 135


def load_personalized_rows():
    if not __import__("pathlib").Path(OUT_PATH).exists():
        print(f"[ERROR] '{OUT_PATH}' not found.")
        return []
    with open(OUT_PATH, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _words(text):
    return len((text or "").split())


def structure_key(company, hook, body):
    """Normalized skeleton of an email: company names and the company-specific
    fact are replaced by placeholders, so only the template structure remains."""
    key = body or ""
    obs = normalize_hook(hook) if hook else ""
    if obs:
        key = key.replace(obs, " <OBS> ")
    if company:
        key = key.replace(company, " <CO> ")
    key = re.sub(r"\s+", " ", key).strip()
    return key


def run_validation(rows):
    failures = []
    notes = []

    total = len(rows)
    if total != 222:
        failures.append(f"Unexpected number of rows: {total} (expected 222).")

    # 1. No empty bodies / emails
    empty_emails = [r.get("Company") or "?" for r in rows if not (r.get("Email") or "").strip()]
    empty_bodies = [r.get("Company") or "?" for r in rows if not (r.get("Body") or "").strip()]
    if empty_emails:
        failures.append(f"Empty Email for: {', '.join(empty_emails)}")
    if empty_bodies:
        failures.append(f"Empty Body for: {', '.join(empty_bodies)}")

    verified = [r for r in rows if (r.get("ResearchStatus") or "").strip() == "Verified"]
    unverified = [r for r in rows if (r.get("ResearchStatus") or "").strip() != "Verified"]

    # 3/4. Forbidden phrases
    for r in rows:
        body = (r.get("Body") or "").lower()
        for phrase in AI_SELF_GENERATION_PHRASES:
            if phrase in body:
                failures.append(f"AI self-generation phrase '{phrase}' in {r.get('Company')}.")
                break
        for phrase in FORBIDDEN_COMMERCIAL_PHRASES:
            if phrase in body:
                failures.append(f"Forbidden commercial phrase '{phrase}' in {r.get('Company')}.")
                break
        if r["ResearchStatus"] == "Verified":
            match = FABRICATED_CLAIM_RE.search(body)
            if match:
                failures.append(f"Fabricated-claim phrase '{match.group(0).strip()}' in {r.get('Company')}.")

    # 6. Unverified companies use the fallback
    for r in unverified:
        company = r.get("Company") or ("your company" if not (r.get("Company") or "").strip() else "")
        expected = FALLBACK_BODY.format(company=company or "your company")
        if (r.get("Body") or "").strip() != expected.strip():
            failures.append(f"Unverified company '{r.get('Company')}' does not use the generic fallback.")
        if (r.get("ResearchSummary") or "") != "Research unavailable":
            failures.append(f"Unverified company '{r.get('Company')}' has unexpected research summary.")

    # 7. Recruiter wording applied only to recruiters / job boards
    recruiter_rows = []
    for i, r in enumerate(rows):
        if r["ResearchStatus"] != "Verified":
            continue
        body = r.get("Body") or ""
        cat = classify_company(r.get("Company"))
        is_agency = cat in ("recruiter", "jobboard")
        uses_recruiter_wording = "reaching out to see whether" in body
        uses_direct_opening = "express my interest in full-stack" in body
        if is_agency and not uses_recruiter_wording:
            failures.append(f"Recruiter/job board '{r.get('Company')}' missing recruiter wording.")
        if not is_agency:
            if uses_recruiter_wording:
                failures.append(f"Recruiter wording incorrectly applied to '{r.get('Company')}'.")
            if not uses_direct_opening:
                failures.append(f"Direct employer '{r.get('Company')}' missing direct opening.")
        if is_agency:
            recruiter_rows.append(r)

    # 8. Company-specific information actually appears in the email
    for r in verified:
        hook = normalize_hook(r.get("ResearchSummary"))
        body = r.get("Body") or ""
        if hook and hook not in body:
            failures.append(f"Company fact missing from email body: '{r.get('Company')}'.")
        if not (r.get("Company") or "").strip() in body:
            failures.append(f"Company name missing from email body: '{r.get('Company')}'.")

    # 9. Unique structural skeletons (company names + facts stripped)
    skeletons = Counter()
    for r in rows:
        skeletons[structure_key(r.get("Company"), r.get("ResearchSummary"), r.get("Body"))] += 1

    # 10. Duplicate companies/contacts stay consistent
    groups = defaultdict(set)
    for r in rows:
        key = (r.get("Company") or "").strip().lower()
        if key:
            groups[key].add((
                (r.get("Body") or "").strip(),
                (r.get("ResearchStatus") or "").strip(),
                (r.get("Subject") or "").strip(),
                (r.get("ResearchSummary") or "").strip(),
            ))
    dup_conflicts = [k for k, v in groups.items() if len(v) > 1]
    if dup_conflicts:
        failures.append(f"Inconsistent duplicate companies: {', '.join(sorted(dup_conflicts))}")

    # 11. Word counts
    all_counts = [_words(r.get("Body")) for r in rows]
    verified_counts = [_words(r.get("Body")) for r in verified]
    fallback_counts = [_words(r.get("Body")) for r in unverified]
    for r in rows:
        n = _words(r.get("Body"))
        if n < HARD_WORD_MIN or n > HARD_WORD_MAX:
            failures.append(f"Out-of-range word count ({n}) for '{r.get('Company')}'.")
    out_of_band = [r for r in verified if not (80 <= _words(r.get("Body")) <= 123)]
    if out_of_band:
        band_list = ", ".join(f"{r.get('Company')}={_words(r.get('Body'))}" for r in out_of_band[:6])
        notes.append(f"Verified rows outside 80-123 words: {len(out_of_band)} ({band_list}{'...' if len(out_of_band) > 6 else ''})")

    report = {
        "total": total,
        "verified": len(verified),
        "unverified": len(unverified),
        "recruiters": len(recruiter_rows),
        "unique_structures": len(skeletons),
        "structures": skeletons.most_common(),
        "word_counts": all_counts,
        "verified_counts": verified_counts,
        "fallback_counts": fallback_counts,
        "failures": failures,
        "notes": notes,
        "rows": rows,
    }
    return report


def print_validation_report(report):
    print("=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)
    print(f"Total rows:            {report['total']}")
    print(f"Verified:              {report['verified']}")
    print(f"Unverified (fallback): {report['unverified']}")
    print(f"Recruiter / job board: {report['recruiters']}")
    print(f"Unique email structures (names + facts stripped): {report['unique_structures']}")

    all_w = report["word_counts"]
    ver_w = report["verified_counts"]
    print(f"Word counts (all rows): min={min(all_w)} max={max(all_w)} avg={statistics.mean(all_w):.1f} "
          f"median={statistics.median(all_w):.0f}")
    if ver_w:
        print(f"Word counts (verified only): min={min(ver_w)} max={max(ver_w)} "
              f"avg={statistics.mean(ver_w):.1f}")

    print()
    print("Unique structure skeletons (how many rows share each):")
    for skeleton, count in report["structures"]:
        print(f"  {count:>4} x  {skeleton[:110]!r}")

    print()
    print("Validation failures:")
    if report["failures"]:
        for f_ in report["failures"]:
            print(f"  [FAIL] {f_}")
    else:
        print("  none")
    for n in report["notes"]:
        print(f"  [NOTE] {n}")
    print(f"Validation failures count: {len(report['failures'])}")
    print()

    print("Sample emails (one per company type):")
    for r in report["rows"]:
        if r.get("Company") == "Adecco Tunisie":
            _print_sample(r)
        elif r.get("Company") == "Numeryx":
            _print_sample(r)
        elif r.get("Company") == "Expensya":
            _print_sample(r)
        elif r.get("Company") == "Eyewa":
            _print_sample(r)
        elif r.get("Company") == "Movenpick":
            _print_sample(r)
    print()

    any_fail = len(report["failures"]) == 0
    print("VALIDATION " + ("PASSED" if any_fail else "FAILED"))


def _print_sample(row):
    print("-" * 60)
    print(f"{row.get('Company')} | {row.get('Email')} | {row.get('ResearchStatus')}")
    print(f"Subject: {row.get('Subject')}")
    print("Body:")
    print(row.get("Body"))
    print(f"[{_words(row.get('Body'))} words]")


if __name__ == "__main__":
    main()