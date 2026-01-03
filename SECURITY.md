# Security Policy

## Overview

AIcineDB Backend implements comprehensive security measures to protect user data and prevent common vulnerabilities. This document outlines our security practices and how to report security issues.

## Security Features

### 🔐 Authentication & Authorization

- **JWT Token Validation**: All protected endpoints validate JWT tokens from Supabase Auth
- **Role-Based Access Control (RBAC)**: Support for user, creator, admin, and moderator roles
- **Resource Ownership Verification**: Users can only modify resources they own (admins can bypass)
- **Admin Email Whitelist**: Configurable admin emails via environment variables

### 🛡️ Input Validation

- **Pydantic Schema Validation**: All inputs validated with strict type checking
- **HTML Sanitization**: Using `bleach` library to strip dangerous HTML/JavaScript
- **String Length Limits**: All text fields have maximum length constraints
- **Array Size Limits**: Collections limited to prevent resource exhaustion
- **URL Validation**: External URLs validated with `HttpUrl` type
- **Email Validation**: Email addresses validated with `EmailStr` type
- **Regex Pattern Matching**: Slugs, types, and status fields validated with regex

### 🚦 Rate Limiting

Rate limiting implemented using `slowapi`:

- **Health Check**: 60 requests/minute
- **Analysis Submissions**: 10 requests/minute
- **General API**: 60 requests/minute (configurable per endpoint)

### 🔒 CORS & Headers

- **Strict CORS**: Only whitelisted origins allowed (no wildcards in production)
- **Security Headers**:
  - `X-Content-Type-Options: nosniff` - Prevent MIME sniffing
  - `X-Frame-Options: DENY` - Prevent clickjacking
  - `X-XSS-Protection: 1; mode=block` - XSS protection
  - `Strict-Transport-Security` - Enforce HTTPS (production only)
  - `Content-Security-Policy` - Restrict resource loading
- **Server Header Removed**: Hide server information

### 🏢 Environment Configuration

- **Type-Safe Configuration**: Using Pydantic Settings
- **Secret Management**: Secrets wrapped with `SecretStr` to prevent logging
- **Environment Validation**: Force `DEBUG=False` in production
- **Separate Dev/Prod Configuration**: Different security levels per environment

### 🔍 Row Level Security (RLS)

Comprehensive RLS policies implemented in Supabase:

- **Titles**: Public read for approved content, owner-only updates
- **Reviews**: Public read for approved, owner-only create/update/delete
- **Ratings**: Public read (anonymized), authenticated create
- **Watchlist**: Private per user
- **User Lists**: Public/private based on list settings
- **Festivals**: Public read for active, creator-only management
- **Profiles**: Public read, owner-only updates (except admins)

See `scripts/enable_rls.sql` for complete RLS setup.

### 📊 Logging & Monitoring

- **Request Tracking**: All requests logged with processing time
- **Slow Request Detection**: Requests >5s automatically flagged
- **Authentication Logging**: Failed auth attempts logged
- **Admin Action Logging**: All admin actions logged for audit trail

### 🔄 Additional Protections

- **Singleton Database Connections**: Prevents connection pool exhaustion
- **Request Timeout Middleware**: Tracks slow requests
- **Trusted Host Middleware**: Validates Host header (production only)
- **Extra Field Rejection**: Pydantic schemas reject unexpected fields
- **Auto-Slug Generation**: Prevents slug injection attacks

## Security Best Practices

### For Developers

1. **Never Commit Secrets**: Use environment variables for all secrets
2. **Use Type Hints**: Always use Python type hints for better validation
3. **Validate All Inputs**: Never trust user input, always validate
4. **Use Parameterized Queries**: Prevent SQL injection (already done via ORM)
5. **Check Authorization**: Always verify user permissions before operations
6. **Log Security Events**: Log authentication failures and admin actions
7. **Review Dependencies**: Regularly update and audit dependencies
8. **Test RLS Policies**: Thoroughly test RLS before production

### For Deployment

1. **Set Environment Variables Correctly**:
   ```bash
   ENV=production
   DEBUG=false
   CORS_ORIGINS=https://aicinedb.com,https://www.aicinedb.com
   ADMIN_EMAILS=admin1@example.com,admin2@example.com
   ```

2. **Use HTTPS Only**: Never run production over HTTP

3. **Enable All Security Features**:
   - RLS enabled on all tables
   - Rate limiting active
   - Security headers enabled
   - Trusted hosts configured

4. **Monitor Logs**: Watch for:
   - Failed authentication attempts
   - Rate limit violations
   - Slow requests
   - RLS policy violations

5. **Regular Updates**:
   - Keep dependencies updated
   - Monitor security advisories
   - Review and update RLS policies

### For API Consumers

1. **Use HTTPS Only**: Never send tokens over HTTP
2. **Store Tokens Securely**: Use httpOnly cookies or secure storage
3. **Implement Token Refresh**: Handle token expiration gracefully
4. **Respect Rate Limits**: Implement exponential backoff
5. **Validate Responses**: Don't trust response data blindly
6. **Handle Errors Gracefully**: Don't expose error details to end users

## Environment Variables

### Required

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# API Keys
GEMINI_API_KEY=your-gemini-key
```

### Security Configuration

```bash
# Environment
ENV=production  # development, staging, or production
DEBUG=false     # MUST be false in production

# Admin Access
ADMIN_EMAIL=admin@example.com
ADMIN_EMAILS=admin1@example.com,admin2@example.com

# CORS (comma-separated)
CORS_ORIGINS=https://aicinedb.com,https://www.aicinedb.com

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET=your-secret-here
```

## Vulnerability Reporting

### Reporting Process

If you discover a security vulnerability, please follow these steps:

1. **DO NOT** create a public GitHub issue
2. **DO NOT** disclose the vulnerability publicly
3. Email security details to: **security@aicinedb.com**
4. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Initial Response**: Within 48 hours
- **Status Updates**: Weekly until resolved
- **Resolution Timeline**: Depends on severity
  - Critical: 1-7 days
  - High: 7-14 days
  - Medium: 14-30 days
  - Low: 30-90 days

### Recognition

We appreciate security researchers and will:
- Publicly acknowledge responsible disclosures (with permission)
- Credit researchers in release notes
- Consider bug bounty rewards for critical findings (when program available)

## Security Checklist

### Pre-Deployment

- [ ] All environment variables configured correctly
- [ ] DEBUG set to false
- [ ] RLS enabled on all tables
- [ ] RLS policies tested and verified
- [ ] Admin emails configured
- [ ] CORS origins restricted to production domains
- [ ] HTTPS certificates installed
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] Logs configured and monitored

### Regular Maintenance

- [ ] Review dependencies monthly
- [ ] Update security patches weekly
- [ ] Review logs for suspicious activity
- [ ] Test authentication flows
- [ ] Verify RLS policies still effective
- [ ] Check rate limit effectiveness
- [ ] Review admin access list
- [ ] Audit API usage patterns

## Known Security Considerations

### Current Limitations

1. **No IP-Based Blocking**: Rate limiting by IP only, no permanent bans
2. **No 2FA Yet**: Two-factor authentication not implemented
3. **No Session Management**: JWT tokens only, no session revocation
4. **Basic Audit Logging**: Limited audit trail capabilities

### Planned Improvements

1. Implement 2FA for admin accounts
2. Add session management and revocation
3. Enhance audit logging with structured logs
4. Implement IP-based blocking for abuse
5. Add anomaly detection for suspicious patterns
6. Implement CAPTCHA for sensitive endpoints

## Compliance

This application implements security measures in line with:

- **OWASP Top 10** (2021)
- **OWASP API Security Top 10**
- **CWE/SANS Top 25**

## Security Audit History

- **2024-01**: Comprehensive security audit completed
  - Implemented singleton Supabase client
  - Added authentication dependencies
  - Hardened Pydantic schemas
  - Implemented rate limiting
  - Added security headers
  - Created RLS policies

## Contact

For security concerns: **security@aicinedb.com**

For general issues: [GitHub Issues](https://github.com/2800mhz/AIcineDB-backend/issues)

## License

This security policy is part of the AIcineDB Backend project.
