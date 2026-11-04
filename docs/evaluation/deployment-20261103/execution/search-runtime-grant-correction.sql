-- Restore only existing Search-domain runtime privileges omitted at final-database binding.
GRANT USAGE ON SCHEMA "search" TO "clip_test_marketplace_app";
GRANT DELETE ON TABLE "search"."saved_listings" TO "clip_test_marketplace_app";
GRANT INSERT ON TABLE "search"."saved_listings" TO "clip_test_marketplace_app";
GRANT SELECT ON TABLE "search"."saved_listings" TO "clip_test_marketplace_app";
GRANT INSERT ON TABLE "search"."wanted_command_results" TO "clip_test_marketplace_app";
GRANT SELECT ON TABLE "search"."wanted_command_results" TO "clip_test_marketplace_app";
GRANT UPDATE ON TABLE "search"."wanted_command_results" TO "clip_test_marketplace_app";
GRANT INSERT ON TABLE "search"."wanted_requests" TO "clip_test_marketplace_app";
GRANT SELECT ON TABLE "search"."wanted_requests" TO "clip_test_marketplace_app";
GRANT UPDATE ON TABLE "search"."wanted_requests" TO "clip_test_marketplace_app";
