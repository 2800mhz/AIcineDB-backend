# Railway Deployment Guide

This guide covers deploying the AIcineDB Backend to Railway.

## Prerequisites

- Railway account (https://railway.app)
- GitHub repository connected to Railway
- Supabase account with database configured
- Gemini API key for AI features

## Quick Start

1. **Connect Repository to Railway**
   - Go to Railway dashboard
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose `2800mhz/AIcineDB-backend`

2. **Configure Environment Variables**
   
   Go to Settings → Variables in Railway dashboard and add:

   ```env
   # Supabase Configuration
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   SUPABASE_SERVICE_KEY=your-service-role-key

   # Gemini AI
   GEMINI_API_KEY=your-gemini-api-key

   # Redis (if using Celery)
   REDIS_URL=redis://...
   CELERY_BROKER_URL=redis://...
   CELERY_RESULT_BACKEND=redis://...

   # CORS Origins
   ALLOWED_ORIGINS=https://aicinedb.com,https://www.aicinedb.com

   # Python Configuration
   PYTHONUNBUFFERED=1
   ```

3. **Deploy**
   - Railway will automatically deploy when you push to the connected branch
   - Or click "Deploy" button in Railway dashboard

4. **Generate Public URL**
   - Go to Settings → Networking
   - Click "Generate Domain"
   - Your API will be available at: `https://your-app.up.railway.app`

## Configuration Files

### Procfile
Defines the web server command:
```
web: uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT
```

### railway.json
Railway-specific build and deploy configuration:
- Specifies Nixpacks builder
- Defines build and start commands
- Configures restart policy

### nixpacks.toml
Nixpacks configuration for Python environment:
- Python 3.11 runtime
- pip package manager
- Install dependencies from requirements.txt

### runtime.txt
Specifies exact Python version (3.11.9)

### .railwayignore
Excludes unnecessary files from deployment:
- Test files
- Development files
- Large media files
- Cache directories

## Manual Deployment via CLI

Install Railway CLI:
```bash
npm install -g @railway/cli
```

Deploy:
```bash
railway login
railway link
railway up
```

## Viewing Logs

### Via Dashboard
- Go to your project in Railway
- Click on "Deployments"
- Select a deployment to view logs

### Via CLI
```bash
railway logs
```

## Database Setup

### Adding PostgreSQL
If you need a PostgreSQL database on Railway:

1. Go to your project dashboard
2. Click "New" → "Database" → "PostgreSQL"
3. Railway automatically adds `DATABASE_URL` environment variable

### Using External Supabase
The backend is configured to use Supabase. Ensure you've added the required Supabase environment variables.

## Redis Setup (for Celery)

If you're using Celery for background tasks:

1. Go to your project dashboard
2. Click "New" → "Database" → "Redis"
3. Railway automatically adds `REDIS_URL`
4. Update `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` to use this URL

## Troubleshooting

### Build Fails

Check build logs in Railway dashboard. Common issues:
- Missing dependencies in requirements.txt
- Python version mismatch
- Out of memory during build

### Application Won't Start

- Verify `PORT` environment variable is used in start command
- Check application logs for startup errors
- Ensure all required environment variables are set

### Database Connection Issues

- Verify Supabase credentials are correct
- Check if Supabase allows connections from Railway IPs
- Confirm `SUPABASE_URL` and `SUPABASE_KEY` are set

### CORS Errors

- Ensure your frontend domain is in CORS configuration
- Check `ALLOWED_ORIGINS` environment variable
- Verify CORS middleware settings in `backend/api/main.py`

## Health Check

Once deployed, verify the API is running:
```bash
curl https://your-app.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "version": "2.0.0"
}
```

## API Documentation

Once deployed, access interactive API documentation:
- Swagger UI: `https://your-app.up.railway.app/docs`
- ReDoc: `https://your-app.up.railway.app/redoc`

## Scaling

Railway automatically scales based on resource usage. For manual scaling:
1. Go to Settings → Resources
2. Adjust CPU and Memory limits as needed

## Monitoring

- **Logs**: Railway dashboard → Deployments → Logs
- **Metrics**: Railway dashboard → Metrics (CPU, Memory, Network)
- **Health**: Use `/health` endpoint for uptime monitoring

## Environment-Specific Configuration

### Development
Uses environment variables from `.env` file locally.

### Production (Railway)
Uses environment variables configured in Railway dashboard.

## Security Best Practices

1. **Never commit secrets** to the repository
2. **Use environment variables** for all sensitive data
3. **Rotate API keys** regularly
4. **Enable Railway's built-in security features**
5. **Use HTTPS only** for production
6. **Configure CORS** to allow only trusted domains

## Cost Optimization

- Use `.railwayignore` to exclude unnecessary files
- Optimize Docker image size
- Use Railway's sleep feature for non-production environments
- Monitor resource usage in Railway dashboard

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Project Issues: https://github.com/2800mhz/AIcineDB-backend/issues
