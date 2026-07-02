import { execSync, execFileSync } from 'child_process';
import { createRequire } from 'module';
import os from 'os';
const require = createRequire(import.meta.url);
/**
 * Check if gh CLI is installed and available in PATH
 * Uses platform-appropriate command: 'where' on Windows, 'which' on Unix/macOS
 */
function isGhInstalled() {
    try {
        const command = process.platform === 'win32' ? 'where gh' : 'which gh';
        execSync(command, { stdio: 'pipe' });
        return true;
    }
    catch {
        return false;
    }
}
/**
 * Check if gh CLI is authenticated
 */
function isGhAuthenticated() {
    try {
        execSync('gh auth status', { stdio: 'pipe' });
        return true;
    }
    catch {
        return false;
    }
}
/**
 * Get OpenSpec version from package.json
 */
function getVersion() {
    try {
        const { version } = require('../../package.json');
        return version;
    }
    catch {
        return 'unknown';
    }
}
/**
 * Get platform name
 */
function getPlatform() {
    return os.platform();
}
/**
 * Get current timestamp in ISO format
 */
function getTimestamp() {
    return new Date().toISOString();
}
/**
 * Generate metadata footer for feedback
 */
function generateMetadata() {
    const version = getVersion();
    const platform = getPlatform();
    const timestamp = getTimestamp();
    return `---
Submitted via OpenSpec CLI
- Version: ${version}
- Platform: ${platform}
- Timestamp: ${timestamp}`;
}
/**
 * Format the feedback title
 */
function formatTitle(message) {
    return `Feedback: ${message}`;
}
/**
 * Format the full feedback body
 */
function formatBody(bodyText) {
    const parts = [];
    if (bodyText) {
        parts.push(bodyText);
        parts.push(''); // Empty line before metadata
    }
    parts.push(generateMetadata());
    return parts.join('\n');
}
/**
 * Generate a pre-filled GitHub issue URL for manual submission
 */
function generateManualSubmissionUrl(title, body) {
    const repo = 'Fission-AI/OpenSpec';
    const encodedTitle = encodeURIComponent(title);
    const encodedBody = encodeURIComponent(body);
    const encodedLabels = encodeURIComponent('feedback');
    return `https://github.com/${repo}/issues/new?title=${encodedTitle}&body=${encodedBody}&labels=${encodedLabels}`;
}
/**
 * Display formatted feedback content for manual submission
 */
function displayFormattedFeedback(title, body) {
    console.log('\n--- FORMATTED FEEDBACK ---');
    console.log(`Title: ${title}`);
    console.log(`Labels: feedback`);
    console.log('\nBody:');
    console.log(body);
    console.log('--- END FEEDBACK ---\n');
}
/**
 * Submit feedback via gh CLI
 * Uses execFileSync to prevent shell injection vulnerabilities
 */
function submitViaGhCli(title, body) {
    try {
        const result = execFileSync('gh', [
            'issue',
            'create',
            '--repo',
            'Fission-AI/OpenSpec',
            '--title',
            title,
            '--body',
            body,
            '--label',
            'feedback',
        ], { encoding: 'utf-8', stdio: 'pipe' });
        const issueUrl = result.trim();
        console.log(`\n✓ Feedback submitted successfully!`);
        console.log(`Issue URL: ${issueUrl}\n`);
    }
    catch (error) {
        // Display the error output from gh CLI
        if (error.stderr) {
            console.error(error.stderr.toString());
        }
        else if (error.message) {
            console.error(error.message);
        }
        // Exit with the same code as gh CLI
        process.exit(error.status ?? 1);
    }
}
/**
 * Handle fallback when gh CLI is not available or not authenticated
 */
function handleFallback(title, body, reason) {
    if (reason === 'missing') {
        console.log('⚠️  GitHub CLI not found. Manual submission required.');
    }
    else {
        console.log('⚠️  GitHub authentication required. Manual submission required.');
    }
    displayFormattedFeedback(title, body);
    const manualUrl = generateManualSubmissionUrl(title, body);
    console.log('Please submit your feedback manually:');
    console.log(manualUrl);
    if (reason === 'unauthenticated') {
        console.log('\nTo auto-submit in the future: gh auth login');
    }
    // Exit with success code (fallback is successful)
    process.exit(0);
}
/**
 * Feedback command implementation
 */
export class FeedbackCommand {
    async execute(message, options) {
        // Format title and body once for all code paths
        const title = formatTitle(message);
        const body = formatBody(options?.body);
        // Check if gh CLI is installed
        if (!isGhInstalled()) {
            handleFallback(title, body, 'missing');
            return;
        }
        // Check if gh CLI is authenticated
        if (!isGhAuthenticated()) {
            handleFallback(title, body, 'unauthenticated');
            return;
        }
        // Submit via gh CLI
        submitViaGhCli(title, body);
    }
}
//# sourceMappingURL=feedback.js.map