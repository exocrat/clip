/** Validate the existing Python preflight receipt before any chat submission. */
export function validateIdentityReceipt(receipt) {
  if (receipt?.infrastructure_preflight_valid !== true
      || receipt.aws_identity_verified !== true
      || receipt.https_liveness_verified !== true
      || receipt.origin_dns_to_load_balancer_verified !== true
      || receipt.session_identity?.session_identity_verified !== true
      || receipt.session_identity?.regular_account_verified !== true
      || receipt.session_identity?.test_user_id_matches !== true
      || receipt.session_identity?.session_expiry_checked !== true) {
    throw new Error('nfr05_live_target_or_session_preflight_incomplete');
  }
}
