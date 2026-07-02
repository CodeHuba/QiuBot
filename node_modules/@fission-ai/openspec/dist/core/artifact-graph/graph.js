import { loadSchema, parseSchema } from './schema.js';
/**
 * Represents an artifact dependency graph.
 * Provides methods for querying build order, ready artifacts, and completion status.
 */
export class ArtifactGraph {
    artifacts;
    schema;
    constructor(schema) {
        this.schema = schema;
        this.artifacts = new Map(schema.artifacts.map(a => [a.id, a]));
    }
    /**
     * Creates an ArtifactGraph from a YAML file path.
     */
    static fromYaml(filePath) {
        const schema = loadSchema(filePath);
        return new ArtifactGraph(schema);
    }
    /**
     * Creates an ArtifactGraph from YAML content string.
     */
    static fromYamlContent(yamlContent) {
        const schema = parseSchema(yamlContent);
        return new ArtifactGraph(schema);
    }
    /**
     * Creates an ArtifactGraph from a pre-validated schema object.
     */
    static fromSchema(schema) {
        return new ArtifactGraph(schema);
    }
    /**
     * Gets a single artifact by ID.
     */
    getArtifact(id) {
        return this.artifacts.get(id);
    }
    /**
     * Gets all artifacts in the graph.
     */
    getAllArtifacts() {
        return Array.from(this.artifacts.values());
    }
    /**
     * Gets the schema name.
     */
    getName() {
        return this.schema.name;
    }
    /**
     * Gets the schema version.
     */
    getVersion() {
        return this.schema.version;
    }
    /**
     * Computes the topological build order using Kahn's algorithm.
     * Returns artifact IDs in the order they should be built.
     */
    getBuildOrder() {
        const inDegree = new Map();
        const dependents = new Map();
        // Initialize all artifacts
        for (const artifact of this.artifacts.values()) {
            inDegree.set(artifact.id, artifact.requires.length);
            dependents.set(artifact.id, []);
        }
        // Build reverse adjacency (who depends on whom)
        for (const artifact of this.artifacts.values()) {
            for (const req of artifact.requires) {
                dependents.get(req).push(artifact.id);
            }
        }
        // Start with roots (in-degree 0), sorted for determinism
        const queue = [...this.artifacts.keys()]
            .filter(id => inDegree.get(id) === 0)
            .sort();
        const result = [];
        while (queue.length > 0) {
            const current = queue.shift();
            result.push(current);
            // Collect newly ready artifacts, then sort before adding
            const newlyReady = [];
            for (const dep of dependents.get(current)) {
                const newDegree = inDegree.get(dep) - 1;
                inDegree.set(dep, newDegree);
                if (newDegree === 0) {
                    newlyReady.push(dep);
                }
            }
            queue.push(...newlyReady.sort());
        }
        return result;
    }
    /**
     * Gets artifacts that are ready to be created (all dependencies completed).
     */
    getNextArtifacts(completed) {
        const ready = [];
        for (const artifact of this.artifacts.values()) {
            if (completed.has(artifact.id)) {
                continue; // Already completed
            }
            const allDepsCompleted = artifact.requires.every(req => completed.has(req));
            if (allDepsCompleted) {
                ready.push(artifact.id);
            }
        }
        // Sort for deterministic ordering
        return ready.sort();
    }
    /**
     * Checks if all artifacts in the graph are completed.
     */
    isComplete(completed) {
        for (const artifact of this.artifacts.values()) {
            if (!completed.has(artifact.id)) {
                return false;
            }
        }
        return true;
    }
    /**
     * Gets blocked artifacts and their unmet dependencies.
     */
    getBlocked(completed) {
        const blocked = {};
        for (const artifact of this.artifacts.values()) {
            if (completed.has(artifact.id)) {
                continue; // Already completed
            }
            const unmetDeps = artifact.requires.filter(req => !completed.has(req));
            if (unmetDeps.length > 0) {
                blocked[artifact.id] = unmetDeps.sort();
            }
        }
        return blocked;
    }
}
//# sourceMappingURL=graph.js.map