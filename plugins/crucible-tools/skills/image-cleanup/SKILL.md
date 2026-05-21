---
description: Clean up local podman images (engine images, dangling images, local builds)
---

Clean up local podman images to reclaim disk space.

## Instructions

1. Read the registries configuration to determine the actual image URLs:
   - Controller URL: `jq -r '.controller.url' ${CRUCIBLE_HOME}/config/registries.json`
   - Public engine URL: `jq -r '.engines.public.url // empty' ${CRUCIBLE_HOME}/config/registries.json`
   - Private engine URL: `jq -r '.engines.private.url // empty' ${CRUCIBLE_HOME}/config/registries.json`

2. Run `crucible images` to get the current crucible image inventory, and `podman images` to find dangling and local builds.

3. Categorize and summarize the images in a markdown table with columns: Category, Count, Total Size. Categories:
   - Engine images (from the public and/or private engine URLs found in step 1)
   - Controller image (from the controller URL found in step 1)
   - Local controller builds (`localhost/workshop/...` or `localhost/controller-manifest`)
   - Base images (e.g., `registry.fedoraproject.org/fedora`)
   - Dangling images (`<none>`)

4. Ask the user which categories to remove. Common options:
   - Engine images (safe to remove — rebuilt/pulled as needed during benchmark runs)
   - Dangling images (always safe to remove)
   - Local controller builds (safe if not actively testing a local build)

5. Remove the selected categories using the URLs from step 1:
   - Engine images: `podman images --filter "reference=<engine-url>" --format "{{.ID}}" | xargs podman rmi -f` (repeat for each configured engine URL)
   - Dangling images: `podman image prune -f`
   - Local builds: `podman rmi -f <image-id>` for each selected image

6. Show the remaining images after cleanup with a summary of space reclaimed.
