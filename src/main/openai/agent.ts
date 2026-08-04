import OpenAI from 'openai'
import { randomUUID } from 'crypto'
import type { AgentEvent, ChatMessage, ToolCallRecord } from '../../shared/types'
import { addMessage, getMessages, renameConversation, touchConversation } from '../db/repository'
import { executeTool, summarizeToolCall, toolDefinitions, SIDE_EFFECTING_TOOLS } from './tools'
import { getState } from '../settings'

const MAX_STEPS = 20

const SYSTEM_PROMPT = `You are an AI coding agent embedded in a desktop application.
You help the user build and modify software in their local project directory.

You have tools to list files, read files, write files, and run shell commands.
Guidelines:
- Explore the project with list_files and read_file before making changes.
- Make focused, correct edits. When writing a file, provide its complete new content.
- Prefer running tests or builds with run_command to verify your work.
- Explain what you did and why in clear, concise prose.
- Never touch files outside the project directory.`

export interface AgentDeps {
  // Ask the renderer for approval of a side-effecting tool call. Resolves to
  // true if approved. Only called when permission mode is "ask".
  requestApproval(req: { id: string; tool: string; summary: string; details: string }): Promise<boolean>
  // Emit an event to the renderer.
  emit(event: AgentEvent): void
}

export class AgentRunner {
  private client: OpenAI
  private cancelled = new Set<string>()

  constructor() {
    this.client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY })
  }

  cancel(conversationId: string): void {
    this.cancelled.add(conversationId)
  }

  async run(conversationId: string, deps: AgentDeps): Promise<void> {
    this.cancelled.delete(conversationId)
    const { projectPath, model } = getState()
    const root = projectPath || process.cwd()

    try {
      const history = await getMessages(conversationId)
      const messages = this.toOpenAiMessages(history)

      for (let step = 0; step < MAX_STEPS; step++) {
        if (this.cancelled.has(conversationId)) break

        const completion = await this.client.chat.completions.create({
          model,
          messages,
          tools: toolDefinitions,
          tool_choice: 'auto'
        })

        const choice = completion.choices[0]?.message
        if (!choice) break

        const toolCalls = choice.tool_calls ?? []
        const toolCallRecords: ToolCallRecord[] = toolCalls.map((tc) => ({
          id: tc.id,
          name: tc.function.name,
          arguments: tc.function.arguments
        }))

        // Persist and surface the assistant turn.
        if (choice.content) {
          deps.emit({ type: 'assistant_text', conversationId, content: choice.content })
        }
        await addMessage({
          conversationId,
          role: 'assistant',
          content: choice.content ?? '',
          toolCalls: toolCallRecords.length ? toolCallRecords : undefined
        })

        // Keep the assistant message (with tool_calls) in the model context.
        messages.push({
          role: 'assistant',
          content: choice.content ?? '',
          tool_calls: toolCalls.length
            ? toolCalls.map((tc) => ({
                id: tc.id,
                type: 'function' as const,
                function: { name: tc.function.name, arguments: tc.function.arguments }
              }))
            : undefined
        })

        if (toolCalls.length === 0) {
          break // model produced a final answer
        }

        // Execute each requested tool call.
        for (const call of toolCallRecords) {
          if (this.cancelled.has(conversationId)) break
          deps.emit({ type: 'tool_call', conversationId, call })
          const result = await this.executeWithApproval(root, call, deps)

          await addMessage({
            conversationId,
            role: 'tool',
            content: result,
            toolCallId: call.id,
            name: call.name
          })
          deps.emit({ type: 'tool_result', conversationId, toolCallId: call.id, name: call.name, content: result })

          messages.push({ role: 'tool', tool_call_id: call.id, content: result })
        }
      }

      await this.maybeAutoTitle(conversationId, history, model)
      await touchConversation(conversationId)
      deps.emit({ type: 'done', conversationId })
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err)
      deps.emit({ type: 'error', conversationId, message })
      deps.emit({ type: 'done', conversationId })
    }
  }

  private async executeWithApproval(
    root: string,
    call: ToolCallRecord,
    deps: AgentDeps
  ): Promise<string> {
    let args: Record<string, unknown> = {}
    try {
      args = call.arguments ? JSON.parse(call.arguments) : {}
    } catch {
      return `Error: could not parse arguments for ${call.name}: ${call.arguments}`
    }

    if (SIDE_EFFECTING_TOOLS.has(call.name) && getState().permissionMode === 'ask') {
      const { summary, details } = summarizeToolCall(call.name, args)
      const approved = await deps.requestApproval({ id: randomUUID(), tool: call.name, summary, details })
      if (!approved) {
        return `The user declined to run this ${call.name} operation.`
      }
    }

    try {
      return await executeTool(root, call.name, args)
    } catch (err) {
      return `Error running ${call.name}: ${err instanceof Error ? err.message : String(err)}`
    }
  }

  private toOpenAiMessages(history: ChatMessage[]): OpenAI.Chat.Completions.ChatCompletionMessageParam[] {
    const out: OpenAI.Chat.Completions.ChatCompletionMessageParam[] = [
      { role: 'system', content: SYSTEM_PROMPT }
    ]
    for (const m of history) {
      if (m.role === 'user') {
        out.push({ role: 'user', content: m.content })
      } else if (m.role === 'assistant') {
        out.push({
          role: 'assistant',
          content: m.content,
          tool_calls: m.toolCalls?.length
            ? m.toolCalls.map((tc) => ({
                id: tc.id,
                type: 'function' as const,
                function: { name: tc.name, arguments: tc.arguments }
              }))
            : undefined
        })
      } else if (m.role === 'tool' && m.toolCallId) {
        out.push({ role: 'tool', tool_call_id: m.toolCallId, content: m.content })
      }
    }
    return out
  }

  /** Give brand-new conversations a concise title based on the first user prompt. */
  private async maybeAutoTitle(conversationId: string, priorHistory: ChatMessage[], model: string): Promise<void> {
    const priorUserTurns = priorHistory.filter((m) => m.role === 'user').length
    if (priorUserTurns !== 1) return // only title after the very first exchange

    const firstUser = priorHistory.find((m) => m.role === 'user')
    if (!firstUser) return

    try {
      const res = await this.client.chat.completions.create({
        model,
        messages: [
          { role: 'system', content: 'Generate a short (max 6 words) title for this coding task. Reply with the title only, no quotes.' },
          { role: 'user', content: firstUser.content.slice(0, 500) }
        ],
        max_tokens: 20
      })
      const title = res.choices[0]?.message?.content?.trim()
      if (title) await renameConversation(conversationId, title.replace(/^["']|["']$/g, '').slice(0, 80))
    } catch {
      // Non-fatal: keep default title.
    }
  }
}
