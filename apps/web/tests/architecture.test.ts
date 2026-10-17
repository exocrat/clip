import { readdirSync, readFileSync } from 'node:fs';
import { dirname, extname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { matchRoutes, type RouteObject } from 'react-router';
import { describe, expect, it } from 'vitest';
import { approvedRoutes } from '../src/app/approvedRoutes';

const webRoot = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const sourceRoot = join(webRoot, 'src');
const approvedProductPaths = [
  '/sign-in',
  '/auth/callback',
  '/',
  '/listings/new',
  '/listings/:listingId',
  '/listings/:listingId/edit',
  '/my/listings',
  '/saved',
  '/my/conversations',
  '/my/conversations/:conversationId',
  '/account/contacts',
  '/wanted/:requestId',
];

function getRoutePaths(routes: RouteObject[]): string[] {
  return routes.flatMap((route) => [
    ...(route.path ? [route.path] : []),
    ...getRoutePaths(route.children ?? []),
  ]);
}

function getSourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return getSourceFiles(path);
    return ['.ts', '.tsx'].includes(extname(path)) ? [path] : [];
  });
}

function getImportedModules(filePath: string): string[] {
  const sourceText = readFileSync(filePath, 'utf8');
  const importPattern =
    /\b(?:import|export)\s+(?:type\s+)?(?:[^'";]*?\s+from\s+)?(['"])([^'"]+)\1/g;
  return [...sourceText.matchAll(importPattern)].map((match) => match[2]);
}

function featureReference(filePath: string, modulePath: string) {
  if (modulePath.startsWith('.')) {
    const resolvedImport = resolve(dirname(filePath), modulePath);
    const relativeImport = relative(join(sourceRoot, 'features'), resolvedImport);
    if (relativeImport !== '..' && !relativeImport.startsWith(`..${sep}`)) {
      const [domain, ...remainder] = relativeImport.replaceAll(sep, '/').split('/');
      if (['identity', 'listings', 'search', 'conversations'].includes(domain)) {
        return { domain, remainder };
      }
    }
  }

  const parts = modulePath.replaceAll('\\', '/').split('/');
  const featureIndex = parts.lastIndexOf('features');
  if (featureIndex < 0) return undefined;

  const domain = parts[featureIndex + 1];
  if (!['identity', 'listings', 'search', 'conversations'].includes(domain)) {
    return undefined;
  }

  return { domain, remainder: parts.slice(featureIndex + 2).filter(Boolean) };
}

function getBoundaryViolation(filePath: string, modulePath: string) {
  const relativePath = relative(sourceRoot, filePath).replaceAll(sep, '/');
  const pageFile = relativePath.startsWith('pages/');
  const featureMatch = relativePath.match(
    /^features\/(identity|listings|search|conversations)\//,
  );
  const ownDomain = featureMatch?.[1];
  const target = featureReference(filePath, modulePath);
  if (!target) return undefined;

  if (pageFile && target.remainder.some((segment) => segment !== 'index')) {
    return `${relative(join(sourceRoot, 'pages'), filePath)} imports private feature path ${modulePath}`;
  }

  if (
    ownDomain &&
    target.domain !== ownDomain &&
    target.remainder.some((segment) => segment !== 'index')
  ) {
    return `${relative(join(sourceRoot, 'features'), filePath)} imports another domain's private path ${modulePath}`;
  }

  return undefined;
}

describe('approved route structure', () => {
  it('contains exactly the approved product paths, with no duplicates', () => {
    const productPaths = getRoutePaths(approvedRoutes).filter((path) => path !== '*');
    expect(productPaths).toHaveLength(new Set(productPaths).size);
    expect([...productPaths].sort()).toEqual([...approvedProductPaths].sort());
  });

  it.each([
    ['/sign-in', '/sign-in'],
    ['/auth/callback', '/auth/callback'],
    ['/', '/'],
    ['/listings/new', '/listings/new'],
    ['/listings/item-123', '/listings/:listingId'],
    ['/listings/item-123/edit', '/listings/:listingId/edit'],
    ['/my/listings', '/my/listings'],
    ['/saved', '/saved'],
    ['/my/conversations', '/my/conversations'],
    ['/my/conversations/chat-123', '/my/conversations/:conversationId'],
    ['/account/contacts', '/account/contacts'],
    ['/wanted/request-123', '/wanted/:requestId'],
  ])('matches %s to its approved route', (url, expectedPath) => {
    const matches = matchRoutes(approvedRoutes, url);
    expect(matches?.at(-1)?.route.path).toBe(expectedPath);
  });

  it('sends unknown paths to the local catch-all route', () => {
    const matches = matchRoutes(approvedRoutes, '/this-is-not-a-product-route');
    expect(matches?.at(-1)?.route.path).toBe('*');
  });
});

describe('frontend feature import boundaries', () => {
  it('keeps page imports on public feature entry points and prevents private cross-domain imports', () => {
    const violations: string[] = [];

    for (const filePath of getSourceFiles(sourceRoot)) {
      for (const modulePath of getImportedModules(filePath)) {
        const violation = getBoundaryViolation(filePath, modulePath);
        if (violation) violations.push(violation);
      }
    }

    expect(violations).toEqual([]);
  });

  it('recognizes prohibited deep imports and allows public entry points', () => {
    const page = join(sourceRoot, 'pages', 'ExamplePage.tsx');
    const identityFeature = join(sourceRoot, 'features', 'identity', 'Example.tsx');

    expect(getBoundaryViolation(page, '../features/listings/PrivateCard')).toBeDefined();
    expect(getBoundaryViolation(identityFeature, '../listings/PrivateCard')).toBeDefined();
    expect(getBoundaryViolation(page, '../features/listings')).toBeUndefined();
    expect(getBoundaryViolation(identityFeature, '../listings')).toBeUndefined();
  });
});
