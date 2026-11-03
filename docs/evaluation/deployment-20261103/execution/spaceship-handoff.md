# Domain-owner handoff: clip-iisc.site

These are the actual generated AWS records for the approved experiment ingress.
No domain purchase, hosting purchase, nameserver change or AWS access is needed.

1. Sign in to Spaceship and open **Advanced DNS Manager**.
2. Select **clip-iisc.site**, then **DNS records → Custom records**.
3. Save a screenshot or copy of the current records, especially root (`@`) A/AAAA
   records or a root redirect, so the old website destination can be restored.
4. Add the three records below. For the root record only, remove/replace any
   existing root A/AAAA, CNAME/ALIAS or redirect that conflicts with its new
   destination. Keep unrelated records. Use **300 seconds / 5 minutes** TTL if
   available; otherwise use the shortest offered TTL.

| Type selected in Spaceship | Host | Value |
|---|---|---|
| CNAME (Spaceship flattens `@` to ALIAS) | `@` | `clip-exp03-exp261103-1208550693.ap-south-1.elb.amazonaws.com` |
| CNAME | `restore` | `clip-exp03-exp261103-1208550693.ap-south-1.elb.amazonaws.com` |
| CNAME | `_124fcb804396bc7809b15f6cbbfbff11.restore` | `_0510eff1cce66333913b2d23217a51a4.wzccmgtwzk.acm-validations.aws` |

5. Select **Add / Save** for each record. Check that the validation record's
   complete name is exactly
   `_124fcb804396bc7809b15f6cbbfbff11.restore.clip-iisc.site`.
   Do not append `clip-iisc.site` twice if Spaceship adds the domain automatically.
6. Send Suraj confirmation when saved, ideally a screenshot of these three
   records. There is no need to wait for the website to load before confirming.

Values are hostnames: do not add `https://`, paths, or an IP address. A trailing
period on an absolute hostname is equivalent and may be added/removed by the UI.
Do not change nameservers, MX, SPF/DKIM/DMARC, other TXT/CNAME records, or the
existing certificate-validation record for the main domain. No `www` change is
requested. Keep the new certificate-validation record for managed renewal.

The main site's certificate is already issued. The restore certificate is pending
validation until its CNAME is visible to AWS. Saving records is a few minutes of
manual work; worldwide DNS/cache expiry and certificate issuance are not
instant or guaranteed within 30 minutes. Application compute is deliberately
stopped at this handoff, so a temporary error page does not establish DNS failure.
Suraj's agent will verify DNS, certificate status and application readiness.

Separately, the Microsoft Identity app owner must register this additional SPA
redirect before restore-app login is used:
`https://restore.clip-iisc.site/auth/callback`.
This is not a Spaceship DNS setting. Preserve the existing main-site redirect.

Official UI guidance:
- https://www.spaceship.com/knowledgebase/dns-records-types/
- https://www.spaceship.com/knowledgebase/dns-alias-record/
