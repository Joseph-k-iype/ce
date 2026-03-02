# Compliance Engine Production Architecture

This document describes the production-grade deployment architecture for the Compliance Engine, focusing on containerization, orchestration, and security.

## Overview
The platform uses a microservices-like approach:
1. **Frontend**: React SPA served via Nginx.
2. **Backend**: FastAPI Python application handling business logic.
3. **Database**: FalkorDB for the graph dataset.
4. **API Gateway / Ingress**: Nginx Ingress Controller handling routing and JWT authentication.

## Dockerization

### 1. Frontend
The React frontend should be built into a static bundle and served using an Nginx alpine image.
```dockerfile
# Build stage
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# Include custom nginx.conf for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 2. Backend (FastAPI)
The backend containerizes the Python environment.
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Kubernetes Architecture

### 1. FalkorDB Deployment & Security
Deploying FalkorDB requires securing it using both network policies and internal authentication.

- **Storage**: Use StatefulSets with PersistentVolumeClaims for data persistence.
- **Authentication**: Set the `requirepass` directive in the Redis/FalkorDB configuration to force password authentication.
- **Secret Management**: Store the FalkorDB password in a Kubernetes Secret.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: falkordb-secret
type: Opaque
data:
  password: <base64-encoded-password>
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: falkordb
spec:
  serviceName: "falkordb"
  replicas: 1
  selector:
    matchLabels:
      app: falkordb
  template:
    metadata:
      labels:
        app: falkordb
    spec:
      containers:
      - name: falkordb
        image: falkordb/falkordb:latest
        command: ["/bin/sh", "-c", "redis-server --requirepass $FALKORDB_PASSWORD --loadmodule /usr/lib/redis/modules/falkordb.so"]
        env:
        - name: FALKORDB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: falkordb-secret
              key: password
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: falkordb-data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: falkordb-data
    spec:
      accessModes: [ "ReadWriteOnce" ]
      resources:
        requests:
          storage: 10Gi
```

### 2. Network Policies
Isolate FalkorDB so that only the backend pods can communicate with it.

```yaml
kind: NetworkPolicy
apiVersion: networking.k8s.io/v1
metadata:
  name: falkordb-allow-backend
spec:
  podSelector:
    matchLabels:
      app: falkordb
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: backend
    ports:
    - protocol: TCP
      port: 6379
```

## Nginx Ingress & JWT Authentication

To secure the entire application (and by extension the data in FalkorDB), we use an Nginx Ingress Controller to manage external access and validate JWT tokens before requests reach the FastAPI backend.

1. **Token Issuance**: The backend handles user login and issues a signed JWT (`Authorization: Bearer <token>`).
2. **Token Validation at Edge**:
   - The Nginx Ingress Controller handles incoming API traffic (`/api/*`).
   - Using Nginx Plus (or an Open Source alternative with `auth_request`), the Ingress Controller intercepts the request, validates the JWT's signature (using a mounted secret or JWKS), and checks claims (like expiry).
   - If invalid, Nginx returns `401 Unauthorized`.
   - If valid, Nginx strips or forwards the JWT to the FastAPI backend.

### Example Ingress Configuration (Nginx Plus)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: compliance-engine-ingress
  annotations:
    kubernetes.io/ingress.class: "nginx"
    # JWT Validation annotations (Nginx Plus syntax)
    nginx.org/jwt-key: "jwt-secret"
    nginx.org/jwt-realm: "Compliance Engine APIs"
    nginx.org/jwt-token: "$http_authorization"
spec:
  tls:
  - hosts:
    - app.compliance-engine.internal
    secretName: tls-secret
  rules:
  - host: app.compliance-engine.internal
    http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: backend-service
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: frontend-service
            port:
              number: 80
```

*Note: For open-source Nginx Ingress, you would deploy an auth service (e.g., `oauth2-proxy` or a custom auth pod) and use the `nginx.ingress.kubernetes.io/auth-url` annotation.*

## Summary of Data Flow Security
1. **Client -> Nginx Ingress**: Encrypted via TLS.
2. **Nginx Ingress**: Validates JWT. Rejects unauthorized traffic at the cluster perimeter.
3. **Nginx -> Backend**: Internal cluster traffic. Backend uses the JWT claims for role-based access control (RBAC).
4. **Backend -> FalkorDB**: The backend authenticates with FalkorDB using the secure password injected via Kubernetes Secrets. Internal traffic is restricted by Network Policies.
