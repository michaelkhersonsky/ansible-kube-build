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

- 2 independent VM's would be required for this infrastructure. They should be setup in one private network, with no firewall between them.
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

# 🗂️ Ansible Inventory File

[kube_master]
master-node ansible_host=<MASTER_IP> ansible_user=rocky

[kube_worker]
worker-node ansible_host=<WORKER_IP> ansible_user=rocky

[kube_all:children]
kube_master
kube_worker

Don't forget the key.
---
### 📋 Ansible Playbook Execution Order

The Kubernetes cluster is provisioned and configured using a series of Ansible playbooks located in the `/playbooks` directory. These playbooks must be executed in the following order to ensure a stable and functional setup.

---

#### 1. `prepare-system.yaml`

Prepares the Rocky Linux nodes for Kubernetes installation by:
- Disabling swap
- Loading required kernel modules
- Applying sysctl network parameters
- Installing dependencies such as `yum-utils` and `lvm2`
- Installing and configuring `containerd` as the container runtime (including generating `config.toml` with `SystemdCgroup = true`)

---

#### 2. `install-k8s.yaml`

Adds the official Kubernetes 1.33 repository and installs:
- `kubeadm`
- `kubelet`
- `kubectl`

It also enables and starts the `kubelet` service. SELinux is configured to permissive mode for compatibility.

---

#### 3. `initialize-master.yaml`

Runs `kubeadm init` on the master node with the defined pod CIDR (`192.168.0.0/16`), sets up the kube config for `kubectl`, and prepares the control plane for networking and worker node joining.


### ✅This step tries to initialize the cluster - it could be fragile in Ansible.

- If it fails, you can try Initializing the master node with:

```
kubeadm init --pod-network-cidr=192.168.0.0/16 
```
or simply
```
kubeadm init 
```

> ⚠️ **Important:** This playbook must complete successfully before applying any CNI plugin such as Calico.

---

#### 4. `install-calico.yaml`

Applies the Calico manifest using `kubectl apply`. This should only be run **after** the master node has been initialized and `kubectl get nodes` shows the master in a `Ready` or `NotReady` state. Running Calico too early may result in certificate errors or CRI-related issues.

---

#### 5. `join-workers.yaml` (optional, not currently implemented)

If managing worker nodes with Ansible, this playbook can execute the `kubeadm join` command on them. The join token and discovery hash must be retrieved from the master node (`kubeadm token create --print-join-command`) and passed to this playbook.

---

Following this order ensures a predictable and clean Kubernetes setup. The separation of responsibilities across playbooks also makes the process modular and easier to debug or extend.

---
### 🔄 Cluster Reset Procedure

To completely tear down and reset the Kubernetes cluster (e.g., for reinstallation or cleanup), use the following steps. This removes all Kubernetes configurations and reinitializes the system state.

---

#### 🧹 1. Reset Kubernetes components

Run on **all nodes** (master and workers):

```bash
kubeadm reset -f
```

---

#### 🗑️ 2. Remove residual configuration and CNI data

```bash
rm -rf /etc/cni/net.d
rm -rf /var/lib/cni/
rm -rf /var/lib/kubelet/*
rm -rf /etc/kubernetes
rm -rf ~/.kube
```

---

#### 🧼 3. Restart container runtime and kubelet

```bash
systemctl restart containerd
systemctl restart kubelet
```

---

#### 🔄 4. Optional: Remove Calico and network configs

```bash
ip link delete cni0
ip link delete flannel.1 2>/dev/null
```

Use `ip a` to inspect lingering interfaces if needed.

---

After resetting, the playbooks can be run again starting from `prepare-system.yaml`.

> ⚠️ Always confirm that no residual configurations remain, especially in `/etc/kubernetes` and `/var/lib/kubelet`, before re-initializing with `kubeadm init`.

---
### 🪵 Logging & Troubleshooting Summary

The Kubernetes installation and app deployment process relies on a combination of system logs, Kubernetes diagnostics, and application-level logging to identify and resolve issues effectively.

---

#### 🔧 System-Level Logging

- Use `journalctl` to investigate service failures:
  ```bash
  journalctl -xeu containerd
  journalctl -xeu kubelet
  ```
- `systemctl status` provided insights into why `kubeadm init` or containerd restarts were failing.
- Log errors helped us detect issues like missing `SystemdCgroup = true` in `containerd` configuration.

---

#### 🔍 Kubernetes Diagnostics

- `kubectl describe node` and `kubectl describe pod <pod> -n kube-system` were essential for identifying:
  - CNI plugin issues (e.g., Calico not ready)
  - TLS/certificate errors from Calico when API server trust wasn’t yet established
  - Pod status reasons (`CrashLoopBackOff`, `ImagePullBackOff`, etc.)
- Monitor system components using:
  ```bash
  kubectl get pods -n kube-system -o wide
  ```

- `kubectl logs <pod>` was used to stream and inspect logs for the game backend and for Calico troubleshooting.

---

#### 📜 Application-Level Logging

- The **Python backend** printed incoming requests:
  ```python
  print(f"GET {self.path} from {self.client_address[0]}")
  ```

- **Nginx** was configured with a custom access log format via ConfigMap:
  ```nginx
  log_format game_log '$remote_addr - $host [$time_local] "$request" $status $body_bytes_sent "$http_referer" "$http_user_agent"';
  access_log /var/log/nginx/access.log game_log;
  ```

- Requests to `/game`, `/api`, and `/metrics` were visible in the logs for both Nginx and the backend.

---

#### 🧠 Key Fixes Traced via Logging

- `kubeadm init` failure due to CRI socket errors led us to reconfigure and regenerate the containerd config.
- Calico startup failures were traced to premature application before kubeconfig setup; resolved by reapplying Calico with `--validate=false`.
- Node readiness and backend connectivity issues were caught via detailed inspection of `describe` and logs.

---

Together, these logging and troubleshooting practices enabled smooth debugging and helped build a robust, observable cluster environment.

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

- Use Docker Compose (optional) to **prebuild images** for the app backend and frontend.
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
