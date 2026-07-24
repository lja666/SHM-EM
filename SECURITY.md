# Security Policy

Do not publish database passwords, API tokens, map keys, mail credentials, or
monitoring data that lacks redistribution approval. Runtime secrets are
accepted only through environment variables or untracked local configuration.

The 1.0.x release line receives security fixes. Report vulnerabilities through
the public repository's private security-advisory channel after publication,
or through the corresponding author before the repository is public.

SHM-EM 1.0.0 does not provide application-level authentication. Deployments
that expose the API beyond a trusted research network must add authentication,
TLS, and access control at the reverse proxy or infrastructure boundary.

