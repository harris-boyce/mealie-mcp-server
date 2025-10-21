# Kubernetes Deployment for Mealie MCP Server

This directory contains Kubernetes manifests for deploying the Mealie MCP Server with Caddy as a TLS-terminating reverse proxy.

## Architecture

```
Client → NodePort (30443) → Service → Pod:443 (Caddy) → localhost:8000 (MCP Server)
```

- **MCP Server**: Runs on port 8000 with SSE transport
- **Caddy Sidecar**: TLS termination and reverse proxy on port 443
- **NodePort Service**: Exposes Caddy on port 30443 for external access

## Components

### Files

- `namespace.yaml` - Creates the `mealie-mcp` namespace
- `secret.yaml` - Stores Mealie credentials (MUST be edited with your values)
- `pvc.yaml` - PersistentVolumeClaim for Caddy certificates and data
- `configmap-caddy-internal.yaml` - Caddy config for internal services (self-signed certs)
- `configmap-caddy-external.yaml` - Caddy config for external services (Let's Encrypt)
- `deployment.yaml` - Deployment with MCP server and Caddy sidecar
- `service.yaml` - NodePort Service for external access

## Deployment Scenarios

### Prerequisites

#### Image Pull Authentication

The deployment uses a private image from GitHub Container Registry. You have two options:

**Option A: Make Image Public (Recommended for non-sensitive code)**

```bash
# Make the GHCR package public
gh api \
  --method PATCH \
  -H "Accept: application/vnd.github+json" \
  /user/packages/container/boycivenga-iac%2Fmealie-mcp-server/visibility \
  -f visibility=public
```

No further authentication needed.

**Option B: Use Image Pull Secret (For private images)**

```bash
# Run the helper script to create the secret
./create-image-pull-secret.sh

# Then uncomment the imagePullSecrets section in deployment.yaml
```

Or create manually:
```bash
kubectl create secret docker-registry ghcr-secret \
  --namespace=mealie-mcp \
  --docker-server=ghcr.io \
  --docker-username=YOUR_GITHUB_USERNAME \
  --docker-password=YOUR_GITHUB_TOKEN \
  --docker-email=YOUR_EMAIL
```

Then uncomment these lines in `deployment.yaml`:
```yaml
imagePullSecrets:
- name: ghcr-secret
```

### Scenario 1: Internal Service (Self-Signed Certificate)

Use this for services accessed only within your network or when you manage your own certificates.

```bash
# Apply base resources
kubectl apply -f namespace.yaml
kubectl apply -f pvc.yaml

# Edit secret with your Mealie credentials
kubectl apply -f secret.yaml

# Apply internal Caddy configuration
kubectl apply -f configmap-caddy-internal.yaml

# Deploy the application
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

**Access**: `https://<node-ip>:30443`

**Note**: You'll need to accept the self-signed certificate warning in your browser/client.

### Scenario 2: External Service (Let's Encrypt)

Use this for publicly accessible services with automatic Let's Encrypt certificates.

**Prerequisites**:
- A valid domain name pointing to your Kubernetes node's external IP
- Port 80 accessible for HTTP-01 challenge
- Port 443 accessible for HTTPS traffic

```bash
# Apply base resources
kubectl apply -f namespace.yaml
kubectl apply -f pvc.yaml

# Edit secret with your Mealie credentials
kubectl apply -f secret.yaml

# Edit configmap-caddy-external.yaml:
# 1. Replace 'mcp.example.com' with your actual domain
# 2. Replace 'admin@example.com' with your email
kubectl apply -f configmap-caddy-external.yaml

# Deploy the application
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
```

**Access**: `https://mcp.example.com` (your domain)

## Configuration

### 1. Update Mealie Credentials

Edit `secret.yaml` and replace the placeholder values:

```yaml
stringData:
  MEALIE_BASE_URL: "https://your-mealie-instance.com"
  MEALIE_API_KEY: "your-mealie-api-key"
```

### 2. Customize NodePort (Optional)

Edit `service.yaml` to change the NodePort:

```yaml
ports:
  - name: https
    nodePort: 30443  # Change this (range: 30000-32767)
```

### 3. Adjust Resources (Optional)

Edit `deployment.yaml` to modify resource requests/limits:

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### 4. Storage Class (Optional)

Edit `pvc.yaml` to specify a storage class:

```yaml
spec:
  storageClassName: your-storage-class
```

## Switching Between Internal and External

To switch from internal to external (or vice versa):

```bash
# Delete the old ConfigMap
kubectl delete -f configmap-caddy-internal.yaml

# Apply the new ConfigMap
kubectl apply -f configmap-caddy-external.yaml

# Restart the deployment to pick up new config
kubectl rollout restart deployment/mealie-mcp-server -n mealie-mcp
```

## Verification

### Check Deployment Status

```bash
# Check pods
kubectl get pods -n mealie-mcp

# Check logs
kubectl logs -n mealie-mcp deployment/mealie-mcp-server -c mcp-server
kubectl logs -n mealie-mcp deployment/mealie-mcp-server -c caddy

# Check service
kubectl get svc -n mealie-mcp
```

### Test Connectivity

```bash
# Get node IP
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="ExternalIP")].address}')

# Test the endpoint (internal - accept self-signed cert)
curl -k https://${NODE_IP}:30443/health

# For external with Let's Encrypt
curl https://mcp.example.com/health
```

## Troubleshooting

### Pod Not Starting

```bash
# Describe pod for events
kubectl describe pod -n mealie-mcp -l app=mealie-mcp-server

# Check logs
kubectl logs -n mealie-mcp -l app=mealie-mcp-server --all-containers
```

### Certificate Issues

```bash
# Check Caddy logs
kubectl logs -n mealie-mcp -l app=mealie-mcp-server -c caddy

# Verify certificate data
kubectl exec -n mealie-mcp -c caddy deployment/mealie-mcp-server -- ls -la /data/caddy/certificates
```

### Let's Encrypt Not Working

Common issues:
- Domain DNS not pointing to node IP
- Firewall blocking ports 80 or 443
- NodePort service not accessible externally
- Email not configured in Caddyfile

```bash
# Verify DNS resolution
nslookup mcp.example.com

# Test port 80 accessibility (for HTTP-01 challenge)
curl http://${NODE_IP}:30080
```

### Connection Refused

```bash
# Check if MCP server is listening
kubectl exec -n mealie-mcp deployment/mealie-mcp-server -c mcp-server -- netstat -tlnp | grep 8000

# Check if Caddy can reach MCP server
kubectl exec -n mealie-mcp deployment/mealie-mcp-server -c caddy -- wget -O- http://localhost:8000/health
```

## Security Considerations

1. **Credentials**: The secret.yaml contains sensitive information. Consider using:
   - Sealed Secrets
   - External Secrets Operator
   - Vault integration

2. **Network Policies**: Implement NetworkPolicies to restrict traffic

3. **RBAC**: Apply appropriate RBAC rules for service accounts

4. **Image Security**: 
   - Use specific image tags instead of `:latest`
   - Scan images for vulnerabilities
   - Use private registries with pull secrets

## Maintenance

### Update Mealie Credentials

```bash
# Edit the secret
kubectl edit secret mealie-credentials -n mealie-mcp

# Restart deployment
kubectl rollout restart deployment/mealie-mcp-server -n mealie-mcp
```

### Update Application

```bash
# Update image in deployment.yaml, then:
kubectl apply -f deployment.yaml

# Or use kubectl set image
kubectl set image deployment/mealie-mcp-server mcp-server=ghcr.io/harris-boyce/boycivenga-iac/mealie-mcp-server:v1.0.0 -n mealie-mcp
```

### Scale Deployment

```bash
# Scale to multiple replicas (if needed)
kubectl scale deployment/mealie-mcp-server --replicas=2 -n mealie-mcp
```

## Uninstall

```bash
# Delete all resources
kubectl delete -f service.yaml
kubectl delete -f deployment.yaml
kubectl delete -f configmap-caddy-internal.yaml  # or configmap-caddy-external.yaml
kubectl delete -f secret.yaml
kubectl delete -f pvc.yaml
kubectl delete -f namespace.yaml
```

## Additional Resources

- [Caddy Documentation](https://caddyserver.com/docs/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes NodePort](https://kubernetes.io/docs/concepts/services-networking/service/#type-nodeport)
