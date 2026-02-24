// precedent_cases.cypher
// ======================
// Search for precedent cases matching origin/receiving country pair.
// Used in Phase 3 of the evaluation pipeline.

MATCH (dt:DataTransferCase)-[:FROM_COUNTRY]->(oc:Country),
      (dt)-[:TO_COUNTRY]->(rc:Country)
WHERE toLower(oc.name) = toLower($origin)
  AND toLower(rc.name) = toLower($receiving)
OPTIONAL MATCH (dt)-[:HAS_PURPOSE]->(p:Purpose)
OPTIONAL MATCH (dt)-[:HAS_PROCESS]->(proc:Process)
OPTIONAL MATCH (dt)-[:HAS_PERSONAL_DATA]->(pd:PersonalData)
RETURN dt.case_id AS case_id,
       dt.status AS status,
       dt.pia_status AS pia_status,
       dt.tia_status AS tia_status,
       dt.hrpr_status AS hrpr_status,
       dt.description AS description,
       collect(DISTINCT p.name) AS purposes,
       collect(DISTINCT proc.name) AS processes_l1,
       collect(DISTINCT proc.level) AS processes_levels,
       collect(DISTINCT pd.name) AS personal_data
ORDER BY dt.created_at DESC
LIMIT 20
