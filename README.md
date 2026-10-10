# ShipFast Status API

A tiny internal status-check API (Python standard library only), deployed to Kubernetes with Argo CD (GitOps).

`GET /health` returns `{"status":"ok"}`. Any other path returns a 404 JSON error.

## How it works

1. Code and manifests live in this one repo.
2. The image is built and pushed by hand to GitHub Container Registry (GHCR).
3. `argocd/application.yaml` tells Argo CD to watch the `k8s/` folder on `main`.
4. Every change to `k8s/` goes through a pull request. Argo CD applies it automatically. No `kubectl apply`, no manual Sync.

| Path | Purpose |
|---|---|
| `app/main.py` | The API |
| `app/Dockerfile` | Multi-stage build, non-root user, HEALTHCHECK |
| `k8s/deployment.yaml` | What runs: image tag, replicas, probes, resources, security |
| `k8s/service.yaml` | Stable internal address for the pods |
| `argocd/application.yaml` | What Argo CD watches (auto-sync, self-heal, prune) |

## Prune policy trade-off

`argocd/application.yaml` sets `prune: true`. Pruning means Argo CD **deletes** a cluster resource when its file is removed from `k8s/`.

- **Benefit:** the cluster always matches Git exactly. Nothing is left behind as an orphan.
- **Risk:** deleting or renaming a manifest in a merged pull request deletes the live resource. For example, removing `k8s/service.yaml` removes the Service. Check any deleted or renamed files closely when reviewing a pull request.
- **Why it's acceptable here:** the app is two small resources, and Argo CD only prunes resources it created and tracks.
- **Default behavior:** automated sync does not prune unless you turn it on, as a safety measure. See the Argo CD docs on [Automatic Pruning](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/#automatic-pruning).

## Build and push an image

```
docker build -t ghcr.io/kayla-marcus/shipfast-status-api:v1.0.0 app
docker login ghcr.io -u kayla-marcus      # paste your token at the prompt, in your own terminal only
docker push ghcr.io/kayla-marcus/shipfast-status-api:v1.0.0
```

Then make the package public in GitHub (Packages > package settings > Change visibility).

## One-time Argo CD setup

```
kubectl apply -f argocd/application.yaml
```

## Verify the deployment

```
kubectl get application shipfast-status-api -n argocd
kubectl get pods -n shipfast
kubectl port-forward -n shipfast svc/shipfast-status-api 8080:80
curl.exe -i http://localhost:8080/health
```

## Change workflow (GitOps demo)

1. Edit `app/main.py` (for example, add a `version` field), then build and push `v1.1.0`.
2. Create a branch, change only the image tag in `k8s/deployment.yaml`, open a pull request, and merge it.
3. Do not click Sync and do not run `kubectl apply`. Watch: `kubectl get pods -n shipfast -w`
4. Prove it was automatic (Argo CD checks Git about every 3 minutes):

```
git pull
git log -1 --oneline
kubectl get application shipfast-status-api -n argocd -o 'jsonpath={.status.sync.revision}'
kubectl get application shipfast-status-api -n argocd -o 'jsonpath={.status.operationState.operation.initiatedBy}'
kubectl get deployment shipfast-status-api -n shipfast -o 'jsonpath={.spec.template.spec.containers[0].image}'
```

The revision should start with your merge commit ID, `initiatedBy` should show `{"automated":true}`, and the image should be the new tag.

## Optional self-heal demo

```
kubectl scale deployment shipfast-status-api -n shipfast --replicas=5
kubectl get pods -n shipfast -w
```

Argo CD should return the Deployment to 2 replicas.
