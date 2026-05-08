---
description: Clean up local podman images (engine images, dangling images, local builds)
---

Clean up local podman images to reclaim disk space.

## Instructions

1. Run `podman images --format "{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.Created}}"` to get the current image inventory.

2. Categorize and summarize the images in a markdown table with columns: Category, Count, Total Size. Categories:
   - Engine images (`quay.io/crucible/engines`)
   - Controller image (`quay.io/crucible/controller`)
   - Local controller builds (`localhost/workshop/...` or `localhost/controller-manifest`)
   - Base images (e.g., `registry.fedoraproject.org/fedora`)
   - Dangling images (`<none>`)

3. Ask the user which categories to remove. Common options:
   - Engine images (safe to remove — rebuilt/pulled as needed during benchmark runs)
   - Dangling images (always safe to remove)
   - Local controller builds (safe if not actively testing a local build)

4. Remove the selected categories:
   - Engine images: `podman images --filter "reference=quay.io/crucible/engines" --format "{{.ID}}" | xargs podman rmi -f`
   - Dangling images: `podman image prune -f`
   - Local builds: `podman rmi -f <image-id>` for each selected image

5. Show the remaining images after cleanup with a summary of space reclaimed.
