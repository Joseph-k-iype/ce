"""
Create sample SQLite database with compliance policies for testing.
"""
import sqlite3
from datetime import datetime

# Create database
conn = sqlite3.connect('sample_data/compliance_policies.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS compliance_policies (
    policy_id TEXT PRIMARY KEY,
    policy_name TEXT NOT NULL,
    regulation TEXT NOT NULL,
    jurisdiction TEXT,
    requirement_type TEXT,
    data_category TEXT,
    mandatory BOOLEAN,
    penalty_amount INTEGER,
    effective_date TEXT,
    description TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS regulatory_authorities (
    authority_id TEXT PRIMARY KEY,
    authority_name TEXT NOT NULL,
    country TEXT,
    region TEXT,
    contact_email TEXT,
    website TEXT,
    enforcement_powers TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS data_transfer_mechanisms (
    mechanism_id TEXT PRIMARY KEY,
    mechanism_name TEXT NOT NULL,
    from_region TEXT,
    to_region TEXT,
    valid_until TEXT,
    requires_approval BOOLEAN,
    compliance_standard TEXT
)
''')

# Insert compliance policies
policies = [
    ('POL_GDPR_001', 'GDPR Consent Requirement', 'GDPR', 'European Union', 'Consent', 'All Personal Data', True, 20000000, '2018-05-25', 'Obtain explicit consent before processing personal data'),
    ('POL_GDPR_002', 'GDPR Data Portability', 'GDPR', 'European Union', 'Data Rights', 'All Personal Data', True, 10000000, '2018-05-25', 'Provide data in machine-readable format upon request'),
    ('POL_GDPR_003', 'GDPR Right to Erasure', 'GDPR', 'European Union', 'Data Rights', 'All Personal Data', True, 10000000, '2018-05-25', 'Delete personal data upon valid request'),
    ('POL_GDPR_004', 'GDPR Breach Notification', 'GDPR', 'European Union', 'Security', 'All Personal Data', True, 10000000, '2018-05-25', 'Notify authorities within 72 hours of data breach'),
    ('POL_CCPA_001', 'CCPA Consumer Rights', 'CCPA', 'California', 'Data Rights', 'All Personal Data', True, 7500, '2020-01-01', 'Disclose data collection and allow opt-out'),
    ('POL_CCPA_002', 'CCPA Do Not Sell', 'CCPA', 'California', 'Data Sales', 'All Personal Data', True, 7500, '2020-01-01', 'Provide opt-out mechanism for data sales'),
    ('POL_HIPAA_001', 'HIPAA Protected Health Info', 'HIPAA', 'United States', 'Privacy', 'Health Data', True, 50000, '1996-08-21', 'Protect patient health information confidentiality'),
    ('POL_HIPAA_002', 'HIPAA Security Rule', 'HIPAA', 'United States', 'Security', 'Health Data', True, 50000, '2003-04-21', 'Implement administrative, physical, and technical safeguards'),
    ('POL_PIPEDA_001', 'PIPEDA Consent Principle', 'PIPEDA', 'Canada', 'Consent', 'All Personal Data', True, 100000, '2001-01-01', 'Obtain meaningful consent for data collection'),
    ('POL_LGPD_001', 'LGPD Data Processing', 'LGPD', 'Brazil', 'Processing', 'All Personal Data', True, 50000000, '2020-09-18', 'Process data only for specified legitimate purposes'),
    ('POL_DPA_001', 'UK DPA Data Protection', 'Data Protection Act', 'United Kingdom', 'Privacy', 'All Personal Data', True, 17500000, '2018-05-25', 'Comply with data protection principles'),
    ('POL_COPPA_001', 'COPPA Children Privacy', 'COPPA', 'United States', 'Children Data', 'Children Data', True, 43792, '2000-04-21', 'Obtain parental consent for children under 13'),
]

cursor.executemany('''
INSERT OR REPLACE INTO compliance_policies
(policy_id, policy_name, regulation, jurisdiction, requirement_type, data_category, mandatory, penalty_amount, effective_date, description)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', policies)

# Insert regulatory authorities
authorities = [
    ('AUTH_ICO', 'Information Commissioner\'s Office', 'United Kingdom', 'Europe', 'icocasework@ico.org.uk', 'https://ico.org.uk', 'Fines, Enforcement Notices, Prosecutions'),
    ('AUTH_CNIL', 'Commission Nationale Informatique et Libertés', 'France', 'Europe', 'contact@cnil.fr', 'https://www.cnil.fr', 'Sanctions, Warnings, Orders'),
    ('AUTH_AEPD', 'Agencia Española de Protección de Datos', 'Spain', 'Europe', 'info@aepd.es', 'https://www.aepd.es', 'Fines, Warnings, Orders'),
    ('AUTH_BFDI', 'Federal Commissioner for Data Protection', 'Germany', 'Europe', 'poststelle@bfdi.bund.de', 'https://www.bfdi.bund.de', 'Fines, Audits, Orders'),
    ('AUTH_OPC', 'Office of the Privacy Commissioner', 'Canada', 'North America', 'info@priv.gc.ca', 'https://www.priv.gc.ca', 'Investigations, Compliance Orders'),
    ('AUTH_FTC', 'Federal Trade Commission', 'United States', 'North America', 'privacy@ftc.gov', 'https://www.ftc.gov', 'Penalties, Injunctions, Consumer Redress'),
    ('AUTH_ANPD', 'Autoridade Nacional de Proteção de Dados', 'Brazil', 'South America', 'contato@anpd.gov.br', 'https://www.gov.br/anpd', 'Fines, Warnings, Data Processing Bans'),
]

cursor.executemany('''
INSERT OR REPLACE INTO regulatory_authorities
(authority_id, authority_name, country, region, contact_email, website, enforcement_powers)
VALUES (?, ?, ?, ?, ?, ?, ?)
''', authorities)

# Insert data transfer mechanisms
mechanisms = [
    ('MECH_SCC', 'Standard Contractual Clauses', 'European Union', 'Global', '2024-12-31', False, 'EU Commission Approved'),
    ('MECH_BCR', 'Binding Corporate Rules', 'European Union', 'Global', None, True, 'DPA Approved'),
    ('MECH_ADEQ', 'Adequacy Decision', 'European Union', 'Adequate Countries', None, False, 'EU Commission Decision'),
    ('MECH_DPF', 'Data Privacy Framework', 'European Union', 'United States', '2025-12-31', False, 'Self-Certification'),
    ('MECH_CONSENT', 'Explicit Consent', 'Global', 'Global', None, False, 'GDPR Article 49'),
]

cursor.executemany('''
INSERT OR REPLACE INTO data_transfer_mechanisms
(mechanism_id, mechanism_name, from_region, to_region, valid_until, requires_approval, compliance_standard)
VALUES (?, ?, ?, ?, ?, ?, ?)
''', mechanisms)

conn.commit()
conn.close()

print("✅ SQLite database created successfully!")
print("📊 Created tables:")
print("   - compliance_policies (12 records)")
print("   - regulatory_authorities (7 records)")
print("   - data_transfer_mechanisms (5 records)")
print("\n📁 Location: sample_data/compliance_policies.db")
