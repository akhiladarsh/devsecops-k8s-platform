# DevSecOps Kubernetes Platform

A full seven-stage delivery pipeline from code commit to production-running container, with security scanning, GitOps sync, and Prometheus observability. Built around the patterns I used running HIPAA-regulated infrastructure at Baxter International.

![CI](https://github.com/akhiladarsh/devsecops-k8s-platform/actions/workflows/ci.yml/badge.svg)
![Security Scan](https://github.com/akhiladarsh/devsecops-k8s-platform/actions/workflows/security.yml/badge.svg)
![License](https://img.shields.io/badge/license-MIT-blue)

## What this is

The app is a small Python Flask API. That is not the point. The point is everything around it: the pipeline that builds and scans it, the policies that control what can run in the cluster, the GitOps loop that deploys it, and the dashboards that tell you when something breaks.

This is the architecture I would have put around Baxter's connected-device workloads if we were starting fresh today.

## Architecture

```
Developer push -> GitHub Actions CI -> Trivy + Checkov scan
                                             |
                                   (fail on CRITICAL/HIGH)
                                             |
                                    Build & push image to GHCR
                                             |
                                Update manifest in Git (new image tag)
                                             |
                           ArgoCD detects drift -> sync to EKS cluster
                                             |
                          OPA Gatekeeper validates admission
                                             |
                   Falco monitors runtime -> alerts to Prometheus
                                             |
                          Grafana dashboards + alerting
```

## Seven-stage pipeline

1. **Containerisation** (Docker multi-stage, non-root, distroless base)
2. **Registry publication** (GitHub Container Registry with image signing via cosign)
3. **CI pipeline** (GitHub Actions: lint, test, build, scan, push)
4. **Security layer** (Trivy filesystem + image scan, Checkov IaC scan, OPA admission policies)
5. **Kubernetes deployment** (Kustomize base + dev/prod overlays, resource limits, NetworkPolicies, PodSecurityStandards)
6. **GitOps** (ArgoCD Application manifests with auto-sync and self-heal)
7. **Observability** (Prometheus + Grafana + Alertmanager, custom dashboards, SLO alerts)

## Security posture

| Control | Implementation |
|---|---|
| Image scanning | Trivy in CI, fail build on CRITICAL/HIGH CVEs |
| IaC scanning | Checkov on Kubernetes YAML and Dockerfiles |
| Supply chain | Cosign image signing with keyless OIDC |
| Runtime detection | Falco with custom rules for healthcare-style workloads |
| Admission control | OPA Gatekeeper constraints: no-privileged, required-labels, approved-registries |
| Network policy | Default-deny ingress, explicit egress rules |
| Secrets | Sealed Secrets (no plaintext in Git) |
| Pod security | Restricted PodSecurityStandard, readOnlyRootFilesystem |

## Repository layout

```
app/                     Python Flask application
docker/                  Dockerfile
k8s/base/                Deployment, Service, NetworkPolicy, HPA, PDB
k8s/overlays/dev/        Dev-specific patches (1 replica, debug logging)
k8s/overlays/prod/       Prod-specific patches (3 replicas, HPA, PDB)
.github/workflows/       CI pipeline, security scan
security/trivy/          Trivy config
security/opa/            OPA Gatekeeper constraint policies
security/falco/          Falco runtime detection rules
argocd/                  ArgoCD Application and Project manifests
monitoring/prometheus/   Prometheus alerting rules
monitoring/grafana/      Grafana dashboard JSON
docs/                    Design decisions and setup guide
```

## Running locally

```bash
# Build and run the container
docker build -t devsecops-platform:local -f docker/Dockerfile .
docker run -p 8080:8080 devsecops-platform:local

# Test health endpoint
curl http://localhost:8080/health
```

## Deploying to a cluster

Requires a Kubernetes cluster with kubectl configured. Works on EKS, minikube, kind, or k3s.

```bash
# Apply base manifests with dev overlay
kubectl apply -k k8s/overlays/dev

# Or bootstrap ArgoCD to manage it
kubectl apply -f argocd/application.yaml
```

## About the author

Akhil Adarsh Suryapagula. Senior Platform Engineer, 8 years AWS. Previously led a 13-engineer SRE team at Baxter International on HIPAA-regulated medical device infrastructure. Now moving into Cloud Security.

- Website: [akhiladarsh.com](https://akhiladarsh.com)
- LinkedIn: [linkedin.com/in/akhiladarsh](https://linkedin.com/in/akhiladarsh)
- Email: akhil@akhiladarsh.com

## License

MIT.
