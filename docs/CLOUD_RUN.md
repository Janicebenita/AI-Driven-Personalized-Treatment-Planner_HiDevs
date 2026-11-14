# Cloud Run deployment

Project created at the participant's request: `careweave-514715` in organization `615607503345`.

Status: the user authorized Cloud Shell access only and explicitly declined billable deployment. No Cloud Build job, Artifact Registry repository or Cloud Run service has been created by this workflow. The Docker image passed GitHub's Linux build, HTTP startup, shared Node safety-core and actual MiniLM/Chroma retrieval checks in [this verification run](https://github.com/Janicebenita/treatment_planner_hidevs/actions/runs/43612561526). Deployment remains a separate, unapproved action.

## Container

The Dockerfile includes Python 3.12, Node 22, CPU-only PyTorch, the Python requirements and the pinned public MiniLM model. It runs as an unprivileged user, listens on `0.0.0.0:$PORT`, and preserves Streamlit's default CORS/XSRF protections. Local virtual environments, runtime copies, `.env` files and Streamlit secrets are excluded from Docker and Google Cloud source uploads. No credentials are built into the image.

The initial proposal is service `careweave`, region `asia-south1`, 2 vCPU, 2 GiB memory, concurrency 8, minimum zero and maximum one instance, request timeout 3600 seconds, authenticated access. This is a small synthetic-case demo, not a clinical deployment. These settings limit resources; they are not a dollar spending cap. Cloud Run, Cloud Build and Artifact Registry may charge at the selected account's rates.

The container health check verifies HTTP startup. The container CI also checks the Node safety core and actual MiniLM/Chroma retrieval. See the workflow result for whether a particular image revision passed; a Dockerfile alone does not prove that a deployment works.

## Deploy after cloud access and billing approval

Use a Google Cloud environment with `gcloud`, select the intended account/project, and enable the Cloud Run, Cloud Build and Artifact Registry APIs if required. Do not grant broad IAM roles to bypass an organization-policy failure. Source deployment needs the roles documented by Google for the deployer and build service account.

```sh
git clone https://github.com/Janicebenita/treatment_planner_hidevs.git
cd treatment_planner_hidevs
bash deploy/cloud-run.sh careweave-514715 asia-south1
```

Before this branch is merged, check out the verified deployment branch explicitly. The command uses the Dockerfile through Cloud Build, so local Docker Desktop is not required. The initial service requires authentication. Public judge access is a separate decision and must be verified against the organization's policy.

Groq remains off until a server-side key is configured, preferably through a Secret Manager reference with a narrowly scoped service identity. Do not put keys in Git, command-line arguments, the container image or a screenshot. MongoDB is optional and remains off without configuration and user opt-in.

Cloud Run container filesystems are ephemeral. Public evidence embeddings may be rebuilt per instance; the model is already baked into the image. Session history is not a durable database. Streamlit uses WebSockets; long-lived connections consume resources and can be reset by the request timeout, deployments or instance replacement.

Verify the deployed revision's readiness, health endpoint, page load, a supported semantic plan, urgent withholding and provider-configuration disclosure before calling the deployment complete. The Google Cloud console link is not the HiDevs submission form.

References: [source deployment](https://docs.cloud.google.com/run/docs/deploying-source-code), [container port contract](https://docs.cloud.google.com/run/docs/configuring/services/containers), [WebSocket behavior](https://docs.cloud.google.com/run/docs/triggering/websockets).
