# ---- Build frontend ----
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Build & run backend ----
FROM python:3.11-slim
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy frontend build output into Django's whitenoise root
COPY --from=frontend-build /app/frontend/dist ./frontend_build

# Collect Django static files
RUN python manage.py collectstatic --no-input

# Expose the port Railway provides
EXPOSE ${PORT:-8000}

# Run migrations then start gunicorn
CMD python manage.py migrate --no-input && gunicorn breathe.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120

