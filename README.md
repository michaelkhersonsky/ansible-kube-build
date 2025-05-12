# Ansible-Based Kubernetes Cluster with Calico CNI and App Deployment

This repository contains an automated Ansible setup to provision a near-production Kubernetes 1.33 cluster on **Rocky Linux**, using `containerd` as the container runtime and **Calico** as the CNI. It also includes a complete deployment of a sample **browser-based app** served via Nginx and Python HTTP backend, using Kubernetes manifests.

---

## 📁 Repository Structure

```
.
├── playbooks/          # Ansible playbooks for system prep and Kubernetes provisioning
├── deployments/         # Kubernetes YAML files for app deployment
├── README.md           # This file
```

---

## 🚀 Features

- Full Kubernetes 1.33 installation on Rocky Linux nodes via Ansible
- Secure container runtime setup with `containerd`
- Calico as the CNI provider
- Robust handling of edge cases (CRI errors, Calico startup issues)
- A single-container browser app with Nginx reverse proxy, request logging, and backend forwarding
- NodePort-based external service access
- Ready for additional workloads or extension with Ingress, metrics, etc.

---

## 📦 Kubernetes Installation via Ansible

All provisioning logic resides in `/playbooks`.

### ✅ Playbook Highlights:

- Disables swap and sets sysctl parameters
- Installs and configures `containerd` (including `SystemdCgroup = true`)
- Adds Kubernetes official repo and installs `kubeadm`, `kubelet`, `kubectl`
- Initializes the master node with:

```
kubeadm init --pod-network-cidr=192.168.0.0/16 
```
or simply
```
kubeadm init 
```

- Configures `kubectl` access via `/root/.kube/config`
- Installs Calico CNI with network policies and pod IP assignment
- Supports adding worker nodes using `kubeadm join`

---

## ⚠️ Common Errors and Solutions

### ❌ kubeadm init fails with CRI runtime error

```
rpc error: code = Unimplemented desc = unknown service runtime.v1.RuntimeService
```

**Cause:**  
`containerd` installed but misconfigured (`SystemdCgroup` missing or declared twice).

**Fix:**

```
containerd config default > /etc/containerd/config.toml
```

Then set `SystemdCgroup = true` and restart `containerd`.

---

### ❌ Calico fails to start due to certificate error

```
x509: certificate signed by unknown authority (possibly because of "crypto/rsa: verification error")
```

**Cause:**  
Calico tried to talk to the API server before `kubectl` was properly configured.

**Fix:**

```
kubectl delete -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.27.0/manifests/calico.yaml

```

---

## 🎮 App Deployment Overview

All manifests are under `/deployment`.

### 👾 Features:

- `/game`: Static HTML served by Nginx from ConfigMap
- `/api`: Backend endpoint proxied via Nginx to an internal Python server
- `/metrics`: Exposed via Nginx `stub_status`
- All served from a **single container**
- Configurable NodePort access (`30080`)

---

### 📄 Deployment Files

| File                          | Purpose                                     |
|-------------------------------|---------------------------------------------|
| `01-game-html-configmap.yaml` | HTML content for frontend UI                |
| `02-nginx-configmap.yaml`     | Nginx config with reverse proxy + logs      |
| `03-game-deployment.yaml`     | Single-container pod with Nginx + Python    |
| `04-game-service.yaml`        | NodePort service to expose the app         |

---

### 🔧 Deploy the App

From the root of the repo:

```
kubectl apply -f deployments/<example-type>/01-game-html-configmap.yaml
kubectl apply -f deployments/<example-type>/02-nginx-configmap.yaml
kubectl apply -f deployments/<example-type>/03-game-deployment.yaml
kubectl apply -f deploymens/<example-type>//04-game-service.yaml
```

---

### 🌐 Access the App

Once deployed, open in your browser:

```
http://<worker-node-ip>:30080/game/
http://<worker-node-ip>:30080/api/
http://<worker-node-ip>:30080/metrics
```

To get the IP of a node:

```
kubectl get nodes -o wide
```

✅ Ensure your security allows TCP ingress on port `30080`.

---

## 🐳 Docker & Image Building

- We use Docker Compose (optional) to **prebuild images** for the app backend and frontend.
- Docker was **not installed on Kubernetes nodes** to avoid conflict with `containerd`.
- Use a separate build host or CI runner for `docker-compose build`.

### Local build:

```
docker-compose build
```

### Load into a local `kind` cluster (if used):

```
kind load docker-image game-frontend:latest
kind load docker-image game-backend:latest
```

---

## ✅ Status

- Kubernetes master + worker fully functional
- Calico network ready and stable
- App served with clean routing and logs
- Easily extensible with Ingress, TLS, or additional services

---

## 📌 TODO / Improvements

- Add Helm support for app templating
- Add Ingress + cert-manager for real domains
- Push built images to ECR or Docker Hub
- Add CI/CD for build + deploy pipeline

---

## 🙌 Author

This setup was developed and debugged interactively to simulate real-world issues and solutions.
