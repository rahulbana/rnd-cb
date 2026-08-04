#!/usr/bin/env node
// Standalone helper to create the Postgres schema without launching the app.
// Usage: npm run db:init   (reads DATABASE_URL from .env or the environment)
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'
import { config as loadEnv } from 'dotenv'
import pg from 'pg'

loadEnv()

const __dirname = dirname(fileURLToPath(import.meta.url))
const schemaPath = join(__dirname, '..', 'src', 'main', 'db', 'schema.sql')

async function main() {
  const connectionString = process.env.DATABASE_URL
  if (!connectionString) {
    console.error('DATABASE_URL is not set. Add it to your .env file.')
    process.exit(1)
  }

  const schema = readFileSync(schemaPath, 'utf8')
  const client = new pg.Client({ connectionString })
  await client.connect()
  await client.query(schema)
  await client.end()
  console.log('✓ Schema created/verified successfully.')
}

main().catch((err) => {
  console.error('Failed to initialize database:', err.message)
  process.exit(1)
})
