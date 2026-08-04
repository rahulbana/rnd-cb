import { randomUUID } from 'crypto'
import { getPool, isDbConnected } from './client'
import type { ChatMessage, Conversation, Role, ToolCallRecord } from '../../shared/types'

// In-memory fallback so the app remains usable without Postgres.
const memConversations = new Map<string, Conversation>()
const memMessages = new Map<string, ChatMessage[]>()

function nowIso(): string {
  return new Date().toISOString()
}

export async function createConversation(projectPath: string | null, title = 'New conversation'): Promise<Conversation> {
  const id = randomUUID()
  const ts = nowIso()
  const conv: Conversation = { id, title, projectPath, createdAt: ts, updatedAt: ts }

  if (isDbConnected()) {
    await getPool()!.query(
      `INSERT INTO conversations (id, title, project_path, created_at, updated_at)
       VALUES ($1, $2, $3, now(), now())`,
      [id, title, projectPath]
    )
  } else {
    memConversations.set(id, conv)
    memMessages.set(id, [])
  }
  return conv
}

export async function renameConversation(id: string, title: string): Promise<void> {
  if (isDbConnected()) {
    await getPool()!.query(
      `UPDATE conversations SET title = $2, updated_at = now() WHERE id = $1`,
      [id, title]
    )
  } else {
    const c = memConversations.get(id)
    if (c) {
      c.title = title
      c.updatedAt = nowIso()
    }
  }
}

export async function touchConversation(id: string): Promise<void> {
  if (isDbConnected()) {
    await getPool()!.query(`UPDATE conversations SET updated_at = now() WHERE id = $1`, [id])
  } else {
    const c = memConversations.get(id)
    if (c) c.updatedAt = nowIso()
  }
}

export async function listConversations(): Promise<Conversation[]> {
  if (isDbConnected()) {
    const { rows } = await getPool()!.query(
      `SELECT id, title, project_path, created_at, updated_at
       FROM conversations ORDER BY updated_at DESC`
    )
    return rows.map(mapConversationRow)
  }
  return [...memConversations.values()].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
}

export async function deleteConversation(id: string): Promise<void> {
  if (isDbConnected()) {
    await getPool()!.query(`DELETE FROM conversations WHERE id = $1`, [id])
  } else {
    memConversations.delete(id)
    memMessages.delete(id)
  }
}

export interface NewMessage {
  conversationId: string
  role: Role
  content: string
  toolCalls?: ToolCallRecord[]
  toolCallId?: string
  name?: string
}

export async function addMessage(msg: NewMessage): Promise<ChatMessage> {
  const id = randomUUID()
  const createdAt = nowIso()
  const record: ChatMessage = { id, createdAt, ...msg }

  if (isDbConnected()) {
    await getPool()!.query(
      `INSERT INTO messages (id, conversation_id, role, content, tool_calls, tool_call_id, name, created_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, now())`,
      [
        id,
        msg.conversationId,
        msg.role,
        msg.content,
        msg.toolCalls ? JSON.stringify(msg.toolCalls) : null,
        msg.toolCallId ?? null,
        msg.name ?? null
      ]
    )
  } else {
    const arr = memMessages.get(msg.conversationId) ?? []
    arr.push(record)
    memMessages.set(msg.conversationId, arr)
  }
  return record
}

export async function getMessages(conversationId: string): Promise<ChatMessage[]> {
  if (isDbConnected()) {
    const { rows } = await getPool()!.query(
      `SELECT id, conversation_id, role, content, tool_calls, tool_call_id, name, created_at
       FROM messages WHERE conversation_id = $1 ORDER BY created_at ASC`,
      [conversationId]
    )
    return rows.map(mapMessageRow)
  }
  return memMessages.get(conversationId) ?? []
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function mapConversationRow(r: any): Conversation {
  return {
    id: r.id,
    title: r.title,
    projectPath: r.project_path,
    createdAt: new Date(r.created_at).toISOString(),
    updatedAt: new Date(r.updated_at).toISOString()
  }
}

function mapMessageRow(r: any): ChatMessage {
  return {
    id: r.id,
    conversationId: r.conversation_id,
    role: r.role,
    content: r.content,
    toolCalls: r.tool_calls ?? undefined,
    toolCallId: r.tool_call_id ?? undefined,
    name: r.name ?? undefined,
    createdAt: new Date(r.created_at).toISOString()
  }
}
