import { Pool } from 'pg'
import schemaSql from './schema.sql?raw'

let pool: Pool | null = null
let connected = false

/**
 * Initialize the Postgres pool and ensure the schema exists.
 * Persistence is optional: if DATABASE_URL is not set or the DB is
 * unreachable, the app still runs (in-memory, no history).
 */
export async function initDb(): Promise<boolean> {
  const connectionString = process.env.DATABASE_URL
  if (!connectionString) {
    console.warn('[db] DATABASE_URL not set — running without persistence.')
    connected = false
    return false
  }

  try {
    pool = new Pool({ connectionString, max: 5 })
    await pool.query(schemaSql)
    connected = true
    console.log('[db] Connected and schema ensured.')
    return true
  } catch (err) {
    console.error('[db] Failed to connect/initialize:', (err as Error).message)
    pool = null
    connected = false
    return false
  }
}

export function isDbConnected(): boolean {
  return connected
}

export function getPool(): Pool | null {
  return pool
}

export async function closeDb(): Promise<void> {
  if (pool) {
    await pool.end()
    pool = null
    connected = false
  }
}
