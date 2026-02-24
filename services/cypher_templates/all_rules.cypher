// all_rules.cypher
// =================
// Unified rules query: matches ALL enabled rules (case_matching, transfer,
// attribute) via graph-driven country matching.
// Uses exact case-insensitive matching for country names.

MATCH (r:Rule)
WHERE r.enabled = true
  AND (r.valid_until IS NULL OR r.valid_until >= $today)
OPTIONAL MATCH (r)-[:TRIGGERED_BY_ORIGIN]->(og:CountryGroup)<-[:BELONGS_TO]-(oc:Country)
  WHERE toLower(oc.name) = toLower($origin)
OPTIONAL MATCH (r)-[:TRIGGERED_BY_ORIGIN]->(odc:Country)
  WHERE toLower(odc.name) = toLower($origin)
WITH r, og, odc
WHERE r.origin_match_type = 'any' OR og IS NOT NULL OR odc IS NOT NULL
OPTIONAL MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rg:CountryGroup)<-[:BELONGS_TO]-(rc:Country)
  WHERE toLower(rc.name) = toLower($receiving)
OPTIONAL MATCH (r)-[:TRIGGERED_BY_RECEIVING]->(rdc:Country)
  WHERE toLower(rdc.name) = toLower($receiving)
WITH r, rg, rdc
WHERE r.receiving_match_type = 'any'
   OR r.receiving_match_type = 'not_in'
   OR rg IS NOT NULL
   OR rdc IS NOT NULL
OPTIONAL MATCH (r)-[:EXCLUDES_RECEIVING]->(eg:CountryGroup)<-[:BELONGS_TO]-(ec:Country)
  WHERE toLower(ec.name) = toLower($receiving)
WITH DISTINCT r, eg
WHERE r.receiving_match_type <> 'not_in' OR eg IS NULL
WITH DISTINCT r
WHERE (r.requires_personal_data = false OR r.requires_personal_data IS NULL OR $has_personal_data = true)
  AND (r.has_pii_required = false OR r.has_pii_required IS NULL OR $pii = true)
OPTIONAL MATCH (r)-[:HAS_PERMISSION]->(p:Permission)-[:CAN_HAVE_DUTY]->(d:Duty)
OPTIONAL MATCH (r)-[:HAS_PROHIBITION]->(pb:Prohibition)
WITH r,
     collect(DISTINCT d.module) AS required_assessments,
     collect(DISTINCT d.name) AS duty_names,
     collect(DISTINCT pb.name) AS prohibition_names
OPTIONAL MATCH (r)-[:HAS_ATTRIBUTE]->(attr:Attribute)
WITH r, required_assessments, duty_names, prohibition_names,
     collect(DISTINCT attr.name) AS linked_attributes
OPTIONAL MATCH (r)-[:HAS_DATA_CATEGORY]->(dc:DataCategory)
WITH r, required_assessments, duty_names, prohibition_names, linked_attributes,
     collect(DISTINCT dc.name) AS linked_data_categories
OPTIONAL MATCH (r)-[:HAS_PURPOSE]->(purp:Purpose)
WITH r, required_assessments, duty_names, prohibition_names, linked_attributes,
     linked_data_categories,
     collect(DISTINCT purp.name) AS linked_purposes
OPTIONAL MATCH (r)-[:HAS_PROCESS]->(proc:Process)
WITH r, required_assessments, duty_names, prohibition_names, linked_attributes,
     linked_data_categories, linked_purposes,
     collect(DISTINCT proc.name) AS linked_processes
OPTIONAL MATCH (r)-[:HAS_GDC]->(gdc:GDC)
WITH r, required_assessments, duty_names, prohibition_names, linked_attributes,
     linked_data_categories, linked_purposes, linked_processes,
     collect(DISTINCT gdc.name) AS linked_gdcs
OPTIONAL MATCH (r)-[:LINKED_TO]->(ds:DataSubject)
WITH r, required_assessments, duty_names, prohibition_names, linked_attributes,
     linked_data_categories, linked_purposes, linked_processes, linked_gdcs,
     collect(DISTINCT ds.name) AS linked_data_subjects
OPTIONAL MATCH (r)-[:LINKED_TO]->(reg:Regulator)
WITH r, required_assessments, duty_names, prohibition_names, linked_attributes,
     linked_data_categories, linked_purposes, linked_processes, linked_gdcs,
     linked_data_subjects,
     collect(DISTINCT reg.name) AS linked_regulators
OPTIONAL MATCH (r)-[:LINKED_TO]->(auth:Authority)
RETURN DISTINCT
    r.rule_id AS rule_id, r.name AS name, r.description AS description,
    r.rule_type AS rule_type,
    r.priority AS priority, r.priority_order AS priority_order,
    r.odrl_type AS odrl_type, r.outcome AS outcome,
    r.has_pii_required AS requires_pii,
    r.requires_personal_data AS requires_personal_data,
    r.origin_match_type AS origin_match_type,
    r.receiving_match_type AS receiving_match_type,
    coalesce(r.matching_mode, 'all_dimensions') AS matching_mode,
    r.valid_until AS valid_until,
    r.required_actions AS required_actions,
    r.attribute_name AS attribute_name,
    r.attribute_keywords AS attribute_keywords,
    r.attribute_patterns AS attribute_patterns,
    required_assessments,
    duty_names,
    prohibition_names,
    linked_attributes,
    linked_data_categories,
    linked_purposes,
    linked_processes,
    linked_gdcs,
    linked_data_subjects,
    linked_regulators,
    collect(DISTINCT auth.name) AS linked_authorities
ORDER BY r.priority_order
