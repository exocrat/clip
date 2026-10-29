-- Review candidate ONLY: fixed-target read-only catalog inventory, no reset.
-- Separate live-window/one-master-read approval is required before execution.
-- Output stays private. Contains no credential/hash columns or application rows.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '5s';
SET LOCAL lock_timeout = '3s';

-- Abort before collecting metadata from any other database/login/transaction.
SELECT 1 / CASE WHEN current_database() = 'clip_test'
    AND current_user = 'clip_test_admin' AND session_user = 'clip_test_admin'
    AND current_setting('transaction_read_only') = 'on'
    AND current_setting('transaction_isolation') = 'repeatable read'
    AND (SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid())
    THEN 1 ELSE 0 END AS fixed_target_guard;
SELECT ssl AS transport_tls FROM pg_stat_ssl WHERE pid = pg_backend_pid();

SELECT n.nspname AS project_schema, pg_get_userbyid(n.nspowner) AS owner,
       n.nspacl::text AS schema_acl
FROM pg_namespace n
WHERE n.nspname IN ('identity','listings','search','conversations') ORDER BY 1;

SELECT n.nspname AS object_schema,c.relname,c.relkind,
       pg_get_userbyid(c.relowner) AS owner,c.relacl::text AS object_acl,
       c.relrowsecurity,c.relforcerowsecurity
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname IN ('identity','listings','search','conversations')
   OR c.oid=to_regclass('public.schema_migrations') ORDER BY 1,2;

SELECT rolname AS project_role,oid,rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,
       rolinherit,rolreplication,rolbypassrls,rolconnlimit
FROM pg_roles WHERE starts_with(rolname,'clip_test_') ORDER BY rolname;

SELECT datname AS target_database,pg_get_userbyid(datdba) AS owner,datacl::text
FROM pg_database WHERE datname=current_database();
SELECT rolname AS database_role,
       has_database_privilege(oid,current_database(),'CONNECT') AS connect_privilege,
       has_database_privilege(oid,current_database(),'CREATE') AS create_privilege,
       has_database_privilege(oid,current_database(),'TEMPORARY') AS temporary_privilege
FROM pg_roles WHERE rolname IN
 ('clip_test_identity_app','clip_test_marketplace_app','clip_test_listings_app')
ORDER BY 1;

SELECT member.rolname AS member_role,parent.rolname AS granted_role,m.admin_option
FROM pg_auth_members m JOIN pg_roles member ON member.oid=m.member
JOIN pg_roles parent ON parent.oid=m.roleid
WHERE starts_with(member.rolname,'clip_test_') ORDER BY 1,2;

SELECT r.rolname AS logging_role,s.setdatabase,setting AS logging_setting
FROM pg_db_role_setting s JOIN pg_roles r ON r.oid=s.setrole
CROSS JOIN LATERAL unnest(s.setconfig) setting
WHERE starts_with(r.rolname,'clip_test_') AND split_part(setting,'=',1) IN
 ('log_statement','log_min_duration_statement','log_min_duration_sample',
  'log_transaction_sample_rate','log_min_error_statement',
  'log_parameter_max_length_on_error','pgaudit.log','auto_explain.log_min_duration')
ORDER BY 1,2,3;

SELECT r.rolname AS runtime_role,n.nspname AS access_schema,
       has_schema_privilege(r.oid,n.oid,'USAGE') AS usage,
       has_schema_privilege(r.oid,n.oid,'CREATE') AS create_privilege
FROM pg_roles r CROSS JOIN pg_namespace n
WHERE r.rolname IN ('clip_test_identity_app','clip_test_marketplace_app',
                   'clip_test_listings_app')
  AND n.nspname IN ('identity','listings','search','conversations','public')
ORDER BY 1,2;

SELECT r.rolname AS privilege_role,n.nspname,c.relname,p.privilege,
       has_table_privilege(r.oid,c.oid,p.privilege) AS allowed
FROM pg_roles r CROSS JOIN pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
CROSS JOIN (VALUES ('SELECT'),('INSERT'),('UPDATE'),('DELETE'),('TRUNCATE'),
                   ('REFERENCES'),('TRIGGER'),('MAINTAIN')) p(privilege)
WHERE r.rolname IN ('clip_test_identity_app','clip_test_marketplace_app',
                   'clip_test_listings_app') AND c.relkind IN ('r','p','v','m')
  AND (n.nspname IN ('identity','listings','search','conversations')
       OR c.oid=to_regclass('public.schema_migrations')) ORDER BY 1,2,3,4;

SELECT n.nspname AS routine_schema,p.oid::regprocedure::text AS signature,
       pg_get_userbyid(p.proowner) AS owner,p.prosecdef,p.proacl::text AS function_acl,
       p.prokind,CASE WHEN p.prokind IN ('f','p') THEN
       encode(sha256(convert_to(pg_get_functiondef(p.oid),'UTF8')),'hex') END
       AS definition_sha256
FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname IN ('identity','listings','search','conversations') ORDER BY 1,2;

SELECT r.rolname AS routine_role,p.oid::regprocedure::text AS signature,
       has_function_privilege(r.oid,p.oid,'EXECUTE') AS execute_privilege
FROM pg_roles r CROSS JOIN pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE r.rolname IN ('clip_test_identity_app','clip_test_marketplace_app',
                   'clip_test_listings_app')
 AND n.nspname IN ('identity','listings','search','conversations') ORDER BY 1,2;
SELECT r.rolname AS sequence_role,n.nspname,c.relname,
       has_sequence_privilege(r.oid,c.oid,'USAGE') AS usage,
       has_sequence_privilege(r.oid,c.oid,'SELECT') AS select_privilege,
       has_sequence_privilege(r.oid,c.oid,'UPDATE') AS update_privilege
FROM pg_roles r CROSS JOIN pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE c.relkind='S' AND r.rolname IN
 ('clip_test_identity_app','clip_test_marketplace_app','clip_test_listings_app')
 AND n.nspname IN ('identity','listings','search','conversations') ORDER BY 1,2,3;

SELECT pg_get_userbyid(d.defaclrole) AS default_acl_owner,
       n.nspname AS default_acl_schema,d.defaclobjtype,d.defaclacl::text
FROM pg_default_acl d LEFT JOIN pg_namespace n ON n.oid=d.defaclnamespace
ORDER BY 1,2,3;

SELECT extname AS extension_name,extversion,n.nspname AS extension_schema
FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace ORDER BY 1;
SELECT evtname AS event_trigger,evtevent,evtenabled,
       pg_get_userbyid(evtowner) AS owner,evtfoid::regprocedure::text
FROM pg_event_trigger ORDER BY 1;

-- Explicitly flag external foreign keys, including constraints whose identified
-- object schema can be NULL in the general dependency graph below.
SELECT n.nspname AS external_fk_schema,c.relname AS external_table,
       con.conname,target.oid::regclass::text AS referenced_relation
FROM pg_constraint con JOIN pg_class c ON c.oid=con.conrelid
JOIN pg_namespace n ON n.oid=c.relnamespace
JOIN pg_class target ON target.oid=con.confrelid
JOIN pg_namespace tn ON tn.oid=target.relnamespace
WHERE con.contype='f' AND tn.nspname IN
 ('identity','listings','search','conversations')
 AND n.nspname NOT IN ('identity','listings','search','conversations') ORDER BY 1,2,3;

-- Conservative REVIEW graph, not a DROP authorization or complete SQL-source
-- dependency analyzer. Follow internal owners too: an external view's rewrite
-- rule can cause PostgreSQL to drop its owner view. Unknown/extension/partition
-- cases require explicit review; NULL schema is never automatically safe.
WITH RECURSIVE edges(parent_class,parent_object,child_class,child_object) AS (
 SELECT refclassid,refobjid,classid,objid FROM pg_depend
 UNION
 SELECT classid,objid,refclassid,refobjid FROM pg_depend WHERE deptype IN ('i','e')
), roots(classid,objid) AS (
 SELECT 'pg_namespace'::regclass::oid,oid FROM pg_namespace
 WHERE nspname IN ('identity','listings','search','conversations')
 UNION
 SELECT 'pg_class'::regclass::oid,to_regclass('public.schema_migrations')::oid
 WHERE to_regclass('public.schema_migrations') IS NOT NULL
), closure(classid,objid) AS (
 SELECT * FROM roots
 UNION
 SELECT e.child_class,e.child_object FROM closure c
 JOIN edges e ON e.parent_class=c.classid AND e.parent_object=c.objid
)
SELECT c.classid::regclass::text AS object_catalog,c.objid,
       info.type AS object_type,info.schema AS object_schema,info.identity
FROM closure c CROSS JOIN LATERAL pg_identify_object(c.classid,c.objid,0) info
ORDER BY 1,2;

SELECT count(*) AS other_client_sessions FROM pg_stat_activity
WHERE datname=current_database() AND pid<>pg_backend_pid()
  AND backend_type='client backend';
ROLLBACK;
