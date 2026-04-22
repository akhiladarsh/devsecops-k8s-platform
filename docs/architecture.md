# Design Decisions

### Docker - multi-stage with distroless base

Most tutorials use `python:3.12-slim` for the final image. That image still contains pip, apt, bash, and several hundred utilities an attacker can use if they get inside the container.

Distroless `gcr.io/distroless/python3-debian12:nonroot` contains only the Python runtime and the glibc it needs. No shell. No package manager. Attack surface reduced by ~80% compared to slim.

The multi-stage build means the final image never contains the build tools (gcc, pip, etc.) used to compile dependencies.

**Implications for interviews:** You will be asked "why distroless over alpine?" Answer: distroless has no shell at all, not even /bin/sh, which eliminates an entire category of post-exploitation moves. Alpine has a shell (ash). The tradeoff is debugging - you can't exec into a distroless container interactively, which is a feature in prod and a nuisance in dev.

---

### Kustomize over Helm for this project

Helm is better for distributing third-party software where users need to configure many parameters. Kustomize is better for your own application manifests where you want the base to be directly readable YAML without template syntax.

The base directory contains valid, deployable Kubernetes YAML. The overlays patch only what differs per environment (replica count, log level, namespace). This makes PRs easy to review.

---

### NetworkPolicy - default deny

The `default-deny-ingress` policy blocks ALL inbound traffic to every pod in the namespace. The second policy explicitly allows only what we need: ingress-nginx for serving traffic, and Prometheus for scraping metrics.

If a compromised pod tries to call another service in the cluster that is not explicitly allowed, the kernel drops the packet before it leaves the node. This is critical for HIPAA technical safeguard 164.312(e)(1) which requires encryption and access controls on all data in transit.

---

### OPA Gatekeeper admission control

Kubernetes RBAC controls who can create resources. OPA Gatekeeper controls what those resources are allowed to look like. RBAC alone is not enough.

Without admission control: a developer with Deployment permissions could accidentally deploy a privileged container from Docker Hub. With admission control: that Deployment is rejected at the API server before it ever schedules.

The three policies here cover the 20% of misconfigurations that cause 80% of real incidents: privileged containers, untrusted registries, and missing labels.

---

### Falco for runtime detection

Trivy and Checkov catch problems before deployment. Falco catches problems at runtime, after an attacker or a bug has already bypassed your static checks.

Falco uses the Linux eBPF subsystem to monitor kernel syscalls. When a container makes a syscall that matches a rule - exec-ing a shell, opening a credential file, making an unexpected outbound connection - Falco fires an alert.

The five rules in `security/falco/rules.yaml` come from real patterns in regulated environments: unexpected shells inside containers, outbound connections to unknown addresses, writes to read-only filesystems.

---

### ArgoCD for GitOps

The traditional model: CI builds an image, CI runs `kubectl apply`, done. The problem: the cluster state is now the source of truth, not Git. Someone can `kubectl edit` a deployment in production and it silently diverges from what the repo says.

ArgoCD flips this. Git is the source of truth. ArgoCD continuously compares Git state to cluster state. If they drift (someone edits the cluster directly), ArgoCD either alerts or auto-heals depending on your `selfHeal` setting.

The CI pipeline's job is now different: build the image, push to GHCR, update the image tag in `kustomization.yaml`, push that commit. ArgoCD sees the new commit, syncs, rolls out. The humans who approve the Git commit are the last control point before production.

---

### Prometheus + Grafana

The Prometheus data model (labels + time series) is well-suited for Kubernetes because you can aggregate across pods using label matchers. A single `sum(rate(...)) by (pod)` query gives you per-pod breakdown for free.

The alerts in `monitoring/prometheus/rules.yaml` follow one rule: define the SLO first (99.9% availability, p99 < 500ms), then write the alert as a violation of that SLO. On-call alerts should say which SLO is burning, not just that a metric crossed a threshold.

---

## Running this locally (minikube)

```bash
# 1. Start minikube
minikube start --cpus 4 --memory 8192

# 2. Enable addons
minikube addons enable ingress
minikube addons enable metrics-server

# 3. Install ArgoCD
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 4. Install kube-prometheus-stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

# 5. Install OPA Gatekeeper
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.16/deploy/gatekeeper.yaml

# 6. Apply OPA policies
kubectl apply -f security/opa/

# 7. Install Falco
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm install falco falcosecurity/falco \
  --namespace falco --create-namespace \
  --set falco.rulesFile=/etc/falco/falco_rules.yaml \
  --set-file falco.customRulesFile=security/falco/rules.yaml

# 8. Apply ArgoCD manifests (bootstraps the app into the cluster)
kubectl apply -f argocd/application.yaml

# 9. Watch ArgoCD sync
kubectl -n argocd get applications -w
```
