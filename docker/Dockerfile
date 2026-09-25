FROM node:22-slim AS frontend-build

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=${VITE_API_URL}
ARG VITE_APP_ENV=production
ENV VITE_APP_ENV=${VITE_APP_ENV}
RUN npm run build
RUN grep -q '/api/v1' dist/assets/*.js \
	&& grep -q '/auth/refresh' dist/assets/*.js \
	&& grep -q 'Authorization' dist/assets/*.js \
	&& grep -q 'Bearer' dist/assets/*.js

FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend .

COPY --from=frontend-build /app/dist ./frontend_dist

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
