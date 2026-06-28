interface ArtifactPathLike {
  path?: unknown;
}

export function visibleArtifactsInArtifactRoot<T extends ArtifactPathLike>(
  artifacts: T[],
  projectId?: string | null,
): T[] {
  return artifacts.filter((artifact) => isArtifactPathInArtifactRoot(artifact.path, projectId));
}

export function isArtifactPathInArtifactRoot(path: unknown, projectId?: string | null): boolean {
  if (typeof path !== "string" || !path.trim()) {
    return false;
  }

  const normalized = path.trim().replace(/\\/g, "/").replace(/\/+/g, "/");
  if (normalized.startsWith("artifacts/") || normalized.startsWith("/artifacts/")) {
    return true;
  }

  const projectSegment = normalizedProjectId(projectId);
  if (projectSegment) {
    const projectArtifactPrefix = `.writeagent/projects/${projectSegment}/artifacts/`;
    return normalized.startsWith(projectArtifactPrefix)
      || normalized.startsWith(`/${projectArtifactPrefix}`)
      || normalized.includes(`/${projectArtifactPrefix}`);
  }

  return /(?:^|\/)\.writeagent\/projects\/[^/]+\/artifacts\//.test(normalized);
}

function normalizedProjectId(projectId?: string | null): string | null {
  if (typeof projectId !== "string") {
    return null;
  }
  const normalized = projectId.trim().replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
  return normalized && !normalized.includes("/") ? normalized : null;
}
