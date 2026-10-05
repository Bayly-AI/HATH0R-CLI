# Arize Phoenix Multi-Group Deployment Procedure

> Artifact: **Procedure** · Member of **Artifact Hexad** (`CR-CLI-FEATURE-STANDARD-001`)  
> Suite: `hath0r-opensource` / `bayly-ai` / `1-nation`  
> Date: 2026-10-05

## 1. Purpose & Scope

This procedure outlines the exact steps to provision, configure, and verify the Arize Phoenix observability container across all Docker group meshes (`hath0r`, `1-nation`, and `bai`).

---

## 2. Prerequisites & Port Allocation

| Group | Edge Container | Edge Host Port | Phoenix Container | Phoenix Direct Port | gRPC Port | HTTP Port |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Hath0r** | `HATH0R-NGINX` | `38000` | `HATH0R-Phoenix` | `36006` | `34317` | `34318` |
| **1-Nation** | `1NEDGE` | `58000` / `80` | `1NPHOENIX` | `6006` | `4317` | `4318` |
| **BaylyAI** | `BAI-NGINX` | `48000` | `BAI-Phoenix` | `46006` | `44317` | `44318` |

---

## 3. Deployment Procedure

### Step 1: Update Group Docker Compose
Add the `phoenix` service block to the target group's `docker-compose.yml`:
```yaml
  phoenix:
    image: arizephoenix/phoenix:latest
    container_name: HATH0R-Phoenix
    restart: unless-stopped
    ports:
      - "${HATH0R_PHOENIX_HOST_PORT:-36006}:6006"
      - "${HATH0R_PHOENIX_GRPC_PORT:-34317}:4317"
      - "${HATH0R_PHOENIX_HTTP_PORT:-34318}:4318"
    environment:
      PHOENIX_PORT: 6006
      PHOENIX_GRPC_PORT: 4317
      PHOENIX_WORKING_DIR: /data
    volumes:
      - hath0r_phoenix_data:/data
    networks:
      hath0r-net:
        aliases: [HATH0R-Phoenix, phoenix, hath0r-phoenix]
```

### Step 2: Configure Edge Nginx Reverse Proxy
Add the location blocks to `nginx/conf.d/default.conf`:
```nginx
  location /phoenix/ {
    proxy_pass http://HATH0R-Phoenix:6006/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
  }

  location /v1/traces {
    proxy_pass http://HATH0R-Phoenix:6006/v1/traces;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }

  location /v1/metrics {
    proxy_pass http://HATH0R-Phoenix:6006/v1/metrics;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  }
```

### Step 3: Launch via Hath0r CLI
Start the container using the Phoenix Manager Bot:
```bash
hath0r phoenix up --group hath0r
```

### Step 4: Verify Health and Connectivity
Validate that the collector and UI respond with HTTP 200:
```bash
hath0r phoenix status --group hath0r
```
Verify project routing and span tables:
```bash
hath0r phoenix projects --group hath0r
hath0r phoenix costs --group hath0r
```
