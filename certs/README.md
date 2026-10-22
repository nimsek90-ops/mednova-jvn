# Public database CA certificates

Only approved provider public CA certificates belong here: `mysql-ca.pem` or `postgres-ca.pem`. These exact files are allowed through Git and deployment packaging so verified TLS can use them. Never place client private keys, passwords or other secrets here. No provider certificate has been supplied; hosted TLS connectivity remains unverified. Set PGSSLROOTCERT to the deployed public certificate path after selecting the target.
