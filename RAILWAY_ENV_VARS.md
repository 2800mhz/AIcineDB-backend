# Railway Environment Variables Setup

This file lists all environment variables that need to be configured in Railway dashboard before deployment.

## Required Environment Variables

### Supabase Configuration
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
```

### AI Services
```
GEMINI_API_KEY=your-gemini-api-key
```

## Optional Environment Variables

### Redis (for Celery background tasks)
```
REDIS_URL=redis://default:password@redis-host:port
CELERY_BROKER_URL=redis://default:password@redis-host:port
CELERY_RESULT_BACKEND=redis://default:password@redis-host:port
```

### CORS Configuration
```
ALLOWED_ORIGINS=https://aicinedb.com,https://www.aicinedb.com
```

### Python Configuration
```
PYTHONUNBUFFERED=1
```

## How to Add Environment Variables in Railway

1. Go to your Railway project dashboard
2. Click on your service
3. Navigate to "Variables" tab
4. Click "New Variable"
5. Add each variable name and value
6. Click "Add" after each variable
7. Railway will automatically redeploy with new variables

## Where to Get These Values

### Supabase
1. Go to https://app.supabase.com
2. Select your project
3. Go to Settings → API
4. Copy:
   - Project URL → `SUPABASE_URL`
   - anon/public key → `SUPABASE_KEY`
   - service_role key → `SUPABASE_SERVICE_KEY` (keep this secret!)

### Gemini API
1. Go to https://makersuite.google.com/app/apikey
2. Create or copy your API key → `GEMINI_API_KEY`

### Redis (if using Railway Redis)
1. Add Redis database to your Railway project
2. Railway automatically creates `REDIS_URL`
3. Use the same URL for `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`

## Security Notes

⚠️ **NEVER commit these values to git!**
- All sensitive values should only be in Railway dashboard
- Use `.env` file locally (already in .gitignore)
- The `.env` file should never be committed to version control

## Verification

After adding all variables, verify in Railway:
1. Go to Variables tab
2. Ensure all required variables are listed
3. Click "Redeploy" to apply changes
4. Check deployment logs for any missing variable errors
