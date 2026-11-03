# EXP-02/05/06 run evidence

Create a fresh child directory for each coordinator run. The shared k6 run-plan
builder refuses to create parent directories or overwrite prior evidence. It
writes raw k6 output, a separate execution receipt, and read-only staged inputs
inside the new run directory. Derived reports use separate files; raw output is
never rewritten. Candidate pilots, invalid runs, timeouts and incomplete runs
remain in their original run directories.

Do not store session cookies, CSRF values, credentials, query text beyond the
reviewed case inputs, private user data, or response bodies here. The captured
k6 modules emit aggregate metric points and sanitized operation tags only.
