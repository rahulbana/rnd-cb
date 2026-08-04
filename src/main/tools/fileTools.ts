import { promises as fs } from 'fs'
import { resolve, relative, join, isAbsolute, sep } from 'path'

const MAX_READ_BYTES = 200_000

/**
 * Resolve a user/agent-supplied path against the project root and ensure it
 * stays inside the root. Throws if the path escapes the sandbox.
 */
export function resolveInRoot(root: string, p: string): string {
  const abs = isAbsolute(p) ? resolve(p) : resolve(root, p)
  const rel = relative(root, abs)
  if (rel === '' ) return abs
  if (rel.startsWith('..') || (isAbsolute(rel))) {
    throw new Error(`Path "${p}" is outside the project directory.`)
  }
  return abs
}

const IGNORED_DIRS = new Set(['.git', 'node_modules', 'dist', 'out', '.next', '.venv', '__pycache__', '.cache'])

export async function listFiles(root: string, dir = '.', maxEntries = 500): Promise<string> {
  const start = resolveInRoot(root, dir)
  const results: string[] = []

  async function walk(current: string): Promise<void> {
    if (results.length >= maxEntries) return
    let entries
    try {
      entries = await fs.readdir(current, { withFileTypes: true })
    } catch {
      return
    }
    for (const entry of entries) {
      if (results.length >= maxEntries) break
      if (entry.name.startsWith('.git')) continue
      const full = join(current, entry.name)
      const rel = relative(root, full)
      if (entry.isDirectory()) {
        if (IGNORED_DIRS.has(entry.name)) continue
        results.push(rel + sep)
        await walk(full)
      } else {
        results.push(rel)
      }
    }
  }

  await walk(start)
  if (results.length === 0) return '(no files)'
  const header = results.length >= maxEntries ? `(showing first ${maxEntries} entries)\n` : ''
  return header + results.sort().join('\n')
}

export async function readFile(root: string, path: string): Promise<string> {
  const abs = resolveInRoot(root, path)
  const stat = await fs.stat(abs)
  if (stat.isDirectory()) throw new Error(`"${path}" is a directory.`)
  if (stat.size > MAX_READ_BYTES) {
    const fd = await fs.open(abs, 'r')
    try {
      const buf = Buffer.alloc(MAX_READ_BYTES)
      await fd.read(buf, 0, MAX_READ_BYTES, 0)
      return buf.toString('utf8') + `\n\n... [truncated: file is ${stat.size} bytes]`
    } finally {
      await fd.close()
    }
  }
  return fs.readFile(abs, 'utf8')
}

export async function writeFile(root: string, path: string, content: string): Promise<string> {
  const abs = resolveInRoot(root, path)
  await fs.mkdir(resolve(abs, '..'), { recursive: true })
  await fs.writeFile(abs, content, 'utf8')
  return `Wrote ${Buffer.byteLength(content, 'utf8')} bytes to ${relative(root, abs) || path}`
}
