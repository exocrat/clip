# Regional RDS trust roots

These three **public CA certificates** are the self-signed roots from AWS's
[ap-south-1 bundle](https://truststore.pki.rds.amazonaws.com/ap-south-1/ap-south-1-bundle.pem).
They contain no private keys. `manifest.json` pins the HTTPS source, complete bundle
SHA-256, per-file/DER fingerprints, subjects and validity dates. Only roots are
installed, following [AWS guidance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.SSL.html).

The ordinary API Dockerfile copies one certificate per `.crt` into Debian's local
CA directory and runs `update-ca-certificates` before dropping to user10001.
Existing public system roots remain available. The image explicitly sets
SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt because the bundled libpq OpenSSL
default is a wheel-build path, not Debian's system store. This selects the installed
system file for sslrootcert=system; it does not weaken certificate/hostname checks. The optional Hybrid image inherits
this trust store only when rebuilt from the corrected ordinary API image.
There is no build-time CA download, DB configuration change, runtime root-store
write or insecure TLS fallback. Identity still requires verify-full/system roots.

To update: download the fixed official HTTPS URL using certificate/hostname
verification; review bundle changes and each root's self-signature, CA/key usage,
region, expiry and fingerprint. Replace the individual PEM-encoded `.crt` files
and manifest together, rebuild/retest both relevant image variants/platforms and
obtain shared-owner review. Never add a server/intermediate certificate, synthetic
fixture root or a private key. An upstream CA change is a source review, not an
automatic refresh or deployment. Fresh live RDS verification remains separately
gated; local trust-store tests do not establish a deployed image's configuration.
